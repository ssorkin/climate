from datetime import date, timedelta

import polars as pl

from climate.analysis import metrics as M
from tests.conftest import make_daily, noaa_tenths


def _year(y: int, hot: dict[date, float], base_hi=80, base_lo=60):
    """A full year at base_hi/base_lo °F with the given days' highs overridden."""
    return make_daily(
        date(y, 1, 1),
        date(y, 12, 31),
        lambda d: hot.get(d, base_hi),
        lambda d: base_lo + (5 if d in hot else 0),
    )


def test_warm_season_years_need_both_elements(cfg):
    ok = _year(2000, {})
    gone = {date(2001, 7, 1) + timedelta(days=i) for i in range(30)}  # 30 of 184 days missing
    bad = make_daily(date(2001, 1, 1), date(2001, 12, 31), 80, 60, missing_tmin=gone)
    assert M.warm_season_years(pl.concat([ok, bad]), cfg) == [2000]


def test_threshold_is_whole_f_percentile(cfg):
    # 30 years: every warm-season day 80°F except one 100°F day per year -> p95 = 80.
    frames = [_year(y, {date(y, 7, 4): 100}) for y in range(1950, 1980)]
    daily = pl.concat(frames)
    yrs = M.warm_season_years(daily, cfg)
    assert len(yrs) == 30
    assert M.heat_wave_threshold(daily, cfg, yrs) == 80
    assert M.heat_wave_threshold(daily, cfg, yrs[:5]) is None  # below min_years


def test_runs_and_night_fields(cfg):
    hot = {date(2000, 7, k): 95 for k in (10, 11, 12, 13)}  # a 4-day wave
    hot.update({date(2000, 8, k): 95 for k in (1, 2)})  # 2 days: not a wave
    daily = _year(2000, hot)
    w = M.heat_waves(daily, cfg, 95)
    assert w.height == 1
    r = w.row(0, named=True)
    assert r["start"] == date(2000, 7, 10) and r["end"] == date(2000, 7, 13) and r["days"] == 4
    assert r["peak_f"] == 95 and r["mean_high_f"] == 95
    # nights inside the wave are the lows of days 2..4 (65°F); the night after is 60°F
    assert r["low_f"] == 65 and r["mean_low_f"] == 65 and r["after_low_f"] == 60


def test_missing_day_breaks_a_run(cfg):
    hot = {date(2000, 7, k): 95 for k in range(10, 16)}
    daily = _year(2000, hot).filter(pl.col("date") != date(2000, 7, 12))
    w = M.heat_waves(daily, cfg, 95)
    assert w["days"].to_list() == [3]  # 13,14,15; 10-11 alone are too short
    assert w["start"][0] == date(2000, 7, 13)


def test_threshold_uses_whole_f_round_trip(cfg):
    # 90°F stored as tenths (322 -> 89.96°F) must still count as >= 90.
    hot = {date(2000, 7, k): 90 for k in (10, 11, 12)}
    daily = _year(2000, hot)
    assert daily.filter(pl.col("date") == date(2000, 7, 10))["tmax"][0] == noaa_tenths(90)
    assert M.heat_waves(daily, cfg, 90).height == 1


def test_relief_hours_from_hourly(cfg):
    w = M.heat_waves(_year(2000, {date(2000, 7, k): 95 for k in (10, 11, 12)}), cfg, 95)
    rows = []
    for day in (date(2000, 7, 10), date(2000, 7, 11), date(2000, 7, 12), date(2000, 7, 13)):
        for hr in range(24):
            # evenings 18-23 at 75°F, small hours 0-8 at 65°F (relief), daytime hot
            f = 75 if hr >= 18 else 65 if hr <= 8 else 95
            rows.append({"date": day, "hour": hr, "temp": noaa_tenths(f)})
    hourly = pl.DataFrame(rows, schema={"date": pl.Date, "hour": pl.Int8, "temp": pl.Int32})
    rel = M.heat_wave_relief(hourly, w, 70)
    # each night: 6 evening readings warm + 9 morning readings cool -> 9/15 of 14 h
    assert abs(rel[0] - 14 * 9 / 15) < 1e-9


def test_window_summary_and_ordinary_nights(cfg):
    frames = []
    for y in range(1951, 1981):
        frames.append(_year(y, {date(y, 7, k): 95 for k in (10, 11, 12)}))
    daily = pl.concat(frames)
    yrs = M.warm_season_years(daily, cfg)
    w = M.heat_waves(daily, cfg, 95)
    win = M.heat_wave_window(w, daily, cfg, yrs, 1951, 1980)
    assert win["n"] == 30 and win["waves_per_year"] == 1.0 and win["days_per_year"] == 3.0
    assert win["mean_days"] == 3 and win["peak_f"] == 95 and win["low_f"] == 65
    assert win["after_low_f"] == 60 and win["ordinary_low_f"] == 60 and win["ordinary_high_f"] == 80
    assert win["peak_f_n"] == 30 and win["peak_f_sd"] == 0.0 and win["relief_h_n"] == 0
    assert win["days_n"] == 30 and win["days_sd"] == 0.0
    assert win["waves_per_year_n"] == 30 and win["waves_per_year_sd"] == 0.0
    assert M.heat_wave_window(w, daily, cfg, yrs, 1990, 2020) is None


def _two_eras(shift_now_f=0, late_now=False):
    """30 then-summers and 30 now-summers, one 3-day wave each; `shift_now_f` warms the
    now-era nights; `late_now` moves the now-era wave from July into late September."""
    frames = []
    for y in list(range(1951, 1981)) + list(range(1996, 2026)):
        now = y >= 1996
        m, d0 = (9, 20) if (now and late_now) else (7, 10)
        hot = {date(y, m, d0 + k): 95 for k in range(3)}
        base_lo = 60 + (shift_now_f if now else 0)
        # a seasonal cycle in nights: September nights run 6°F warmer than July's
        frames.append(
            make_daily(
                date(y, 1, 1),
                date(y, 12, 31),
                lambda d, hot=hot: hot.get(d, 80),
                lambda d, hot=hot, b=base_lo: b + (6 if d.month == 9 else 0) + (5 if d in hot else 0),
            )
        )
    return pl.concat(frames)


def test_bootstrap_recovers_a_shift_and_zero_change(cfg):
    daily = _two_eras(shift_now_f=4)
    yrs = M.warm_season_years(daily, cfg)
    w = M.heat_waves(daily, cfg, 95)
    bs = M.heat_wave_bootstrap(w, [y for y in yrs if y <= 1980], [y for y in yrs if y >= 1996], n_boot=200)
    assert bs["low_f"]["est"] == 4.0 and bs["low_f"]["lo"] == 4.0 and bs["low_f"]["hi"] == 4.0
    assert bs["peak_f"]["est"] == 0.0
    assert bs["waves_per_year"]["est"] == 0.0 and len(bs["low_f"]["reps"]) == 200
    pooled = M.pooled_bootstrap([bs, bs])
    assert pooled["low_f"]["est"] == 4.0 and pooled["low_f"]["n_stations"] == 2


def test_bootstrap_interval_widens_with_variable_summers(cfg):
    frames = []
    for y in range(1951, 1981):
        n = 1 if y % 2 else 3  # alternate summers with one wave and three
        hot = {}
        for k in range(n):
            hot.update({date(y, 6 + k, 10 + j): 95 for j in range(3)})
        frames.append(make_daily(date(y, 1, 1), date(y, 12, 31), lambda d, h=hot: h.get(d, 80), 60))
    daily = pl.concat(frames)
    yrs = M.warm_season_years(daily, cfg)
    w = M.heat_waves(daily, cfg, 95)
    bs = M.heat_wave_bootstrap(w, yrs[:15], yrs[15:], n_boot=300)
    assert bs["waves_per_year"]["lo"] < 0 < bs["waves_per_year"]["hi"]


def test_calendar_adjustment_removes_a_timing_shift(cfg):
    daily = _two_eras(late_now=True)  # same climate; modern waves just come in September
    yrs = M.warm_season_years(daily, cfg)
    w = M.heat_wave_anomalies(daily, M.heat_waves(daily, cfg, 95), cfg, yrs)
    then = w.filter(pl.col("year") <= 1980)
    now = w.filter(pl.col("year") >= 1996)
    assert now["low_f"].mean() - then["low_f"].mean() == 6.0  # raw: looks like +6°F
    assert abs(now["low_anom_f"].mean() - then["low_anom_f"].mean()) < 0.5  # adjusted: ~0
    assert then["start_doy"][0] < now["start_doy"][0]


def test_robustness_table_has_every_definition(cfg):
    daily = _two_eras(shift_now_f=3)
    yrs = M.warm_season_years(daily, cfg)
    rows = M.heat_wave_robustness(daily, cfg, yrs, (1951, 1980), (1996, 2025))
    labels = [r["definition"] for r in rows]
    assert any("calendar-day" in x for x in labels) and any("2+ days" in x for x in labels)
    for r in rows:
        assert r["low_f_change"] == 3.0 and r["peak_f_change"] == 0.0
