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
