"""Hourly metrics per station, from ISD-Lite in local time.

Day completeness: a local day counts when >= 18 of 24 hours have a temperature; a
year (or month) counts when >= 90% (25 days) of its days are complete. Nights run
18:00 -> 08:00 local and are labeled by the morning's date; a night counts when >= 10 of
its 14 hours are observed. Thresholds use the whole-°F round-trip like the daily tier.
"""

from __future__ import annotations

import calendar
import json
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import polars as pl

from climate.analysis.metrics import f_whole_expr
from climate.config import load_analysis_config
from climate.hourly.ingest import hourly_path
from climate.isd import IsdStation, load_isd_stations
from climate.paths import ANALYSIS_DIR

HOUR_THRESHOLDS_F = (90, 95, 100, 105)
NIGHT_THRESHOLDS_F = (65, 70, 75)
HI_THRESHOLDS_F = (100, 105, 110)
SUMMER = (6, 7, 8, 9)


def heat_index_f(t_f: np.ndarray, rh: np.ndarray) -> np.ndarray:
    """NWS heat index (Rothfusz regression with the standard adjustments), °F.
    Below 80°F the simple formula is used, as NWS does."""
    hi_simple = 0.5 * (t_f + 61.0 + (t_f - 68.0) * 1.2 + rh * 0.094)
    hi = (
        -42.379
        + 2.04901523 * t_f
        + 10.14333127 * rh
        - 0.22475541 * t_f * rh
        - 0.00683783 * t_f**2
        - 0.05481717 * rh**2
        + 0.00122874 * t_f**2 * rh
        + 0.00085282 * t_f * rh**2
        - 0.00000199 * t_f**2 * rh**2
    )
    adj1 = ((13 - rh) / 4) * np.sqrt(np.clip(17 - np.abs(t_f - 95.0), 0, None) / 17)
    adj2 = ((rh - 85) / 10) * ((87 - t_f) / 5)
    hi = np.where((rh < 13) & (t_f >= 80) & (t_f <= 112), hi - adj1, hi)
    hi = np.where((rh > 85) & (t_f >= 80) & (t_f <= 87), hi + adj2, hi)
    return np.where(hi_simple < 80, hi_simple, hi)


def rh_from_dewpoint(t_c: np.ndarray, td_c: np.ndarray) -> np.ndarray:
    a, b = 17.625, 243.04
    return np.clip(100 * np.exp(a * td_c / (b + td_c)) / np.exp(a * t_c / (b + t_c)), 0, 100)


def analyze_station(st: IsdStation) -> str:
    p = hourly_path(st.id)
    if not p.exists():
        return f"  {st.id}: not ingested"
    cfg = load_analysis_config()
    h = pl.read_parquet(p).filter(pl.col("temp").is_not_null())
    fw = f_whole_expr(pl.col("temp"))
    # heat index per hour (needs dew point)
    t_c = h["temp"].to_numpy() / 10.0
    td = h["dewp"].to_numpy().astype(float)
    td_c = np.where(np.isnan(td), np.nan, td / 10.0)
    rh = rh_from_dewpoint(t_c, td_c)
    hi = heat_index_f(t_c * 1.8 + 32, rh)
    h = h.with_columns(pl.Series("hi_f", hi, dtype=pl.Float64).fill_nan(None))
    h = h.with_columns(
        pl.col("date").dt.year().alias("year"),
        pl.col("date").dt.month().alias("month"),
        *[(fw >= t).alias(f"hours_{t}") for t in HOUR_THRESHOLDS_F],
        *[(pl.col("hi_f") >= t).alias(f"hi_hours_{t}") for t in HI_THRESHOLDS_F],
    )
    # per local day
    day = (
        h.group_by("date")
        .agg(
            pl.len().alias("n_obs"),
            pl.col("temp").max().alias("tmax_h"),
            pl.col("temp").min().alias("tmin_h"),
            *[
                pl.col(f"hours_{t}").sum().cast(pl.Int32).alias(f"hours_{t}")
                for t in HOUR_THRESHOLDS_F
            ],
            *[
                pl.col(f"hi_hours_{t}").sum().cast(pl.Int32).alias(f"hi_hours_{t}")
                for t in HI_THRESHOLDS_F
            ],
        )
        .with_columns((pl.col("n_obs") >= 18).alias("complete"))
    )
    # nights 18:00 -> 08:00, labeled by the morning date
    night = h.with_columns(
        pl.when(pl.col("hour") >= 18)
        .then(pl.col("date") + pl.duration(days=1))
        .when(pl.col("hour") <= 8)
        .then(pl.col("date"))
        .otherwise(None)
        .alias("night")
    ).filter(pl.col("night").is_not_null())
    night = (
        night.group_by("night")
        .agg(pl.len().alias("n"), pl.col("temp").min().alias("night_min"))
        .with_columns(
            (pl.col("n") >= 10).alias("night_ok"),
            *[
                (f_whole_expr(pl.col("night_min")) >= t).alias(f"norelief_{t}")
                for t in NIGHT_THRESHOLDS_F
            ],
        )
        .rename({"night": "date"})
    )
    day = day.join(night, on="date", how="left")
    day = day.with_columns(
        pl.col("date").dt.year().alias("year"), pl.col("date").dt.month().alias("month")
    )

    frac = cfg["completeness"]["annual_min_frac"]

    def period(gcols: list[str], days_in):
        g = day.group_by(gcols).agg(
            pl.col("complete").sum().alias("days_complete"),
            pl.col("night_ok").sum().alias("nights_ok"),
            (pl.col("tmax_h").filter(pl.col("complete")).mean() / 10).alias("tmax_h_mean_c"),
            (pl.col("tmin_h").filter(pl.col("complete")).mean() / 10).alias("tmin_h_mean_c"),
            *[
                pl.col(f"hours_{t}")
                .filter(pl.col("complete"))
                .sum()
                .cast(pl.Int32)
                .alias(f"hours_{t}")
                for t in HOUR_THRESHOLDS_F
            ],
            *[
                pl.col(f"hi_hours_{t}")
                .filter(pl.col("complete"))
                .sum()
                .cast(pl.Int32)
                .alias(f"hi_hours_{t}")
                for t in HI_THRESHOLDS_F
            ],
            *[
                pl.col(f"norelief_{t}")
                .filter(pl.col("night_ok"))
                .sum()
                .cast(pl.Int32)
                .alias(f"norelief_{t}")
                for t in NIGHT_THRESHOLDS_F
            ],
        )
        g = g.with_columns(days_in.alias("days_in"))
        ok = pl.col("days_complete") >= (pl.col("days_in") * frac).ceil()
        cols = (
            [f"hours_{t}" for t in HOUR_THRESHOLDS_F]
            + [f"hi_hours_{t}" for t in HI_THRESHOLDS_F]
            + ["tmax_h_mean_c", "tmin_h_mean_c"]
        )
        g = g.with_columns(
            ok.alias("complete"),
            *[pl.when(ok).then(pl.col(c)).otherwise(None).alias(c) for c in cols],
        )
        nok = pl.col("nights_ok") >= (pl.col("days_in") * frac).ceil()
        g = g.with_columns(
            nok.alias("nights_complete"),
            *[
                pl.when(nok).then(pl.col(f"norelief_{t}")).otherwise(None).alias(f"norelief_{t}")
                for t in NIGHT_THRESHOLDS_F
            ],
        )
        return g.sort(gcols)

    annual = period(
        ["year"],
        pl.col("year").map_elements(
            lambda y: 366 if calendar.isleap(y) else 365, return_dtype=pl.Int32
        ),
    )
    monthly = period(
        ["year", "month"],
        pl.struct(["year", "month"]).map_elements(
            lambda s: calendar.monthrange(s["year"], s["month"])[1], return_dtype=pl.Int32
        ),
    )
    this_year = int(day["year"].max())
    annual = annual.with_columns((pl.col("year") >= this_year).alias("partial"))

    # diurnal curves: mean temp by local hour, Jun-Sep, per decade (complete days only)
    hh = h.join(day.select("date", "complete"), on="date").filter(
        pl.col("complete") & pl.col("month").is_in(SUMMER)
    )
    diurnal = (
        hh.with_columns((pl.col("year") // 10 * 10).alias("decade"))
        .group_by(["decade", "hour"])
        .agg(pl.col("temp").mean().alias("t"))
        .sort(["decade", "hour"])
    )

    # cross-check vs the GHCN twin: how much a hourly max/min under-reads the true extreme
    bias = None
    if st.ghcn:
        gp = __import__("climate.ingest.store", fromlist=["daily_path"]).daily_path(st.ghcn)
        if gp.exists():
            from climate.ingest.store import load_daily_wide

            g = load_daily_wide(st.ghcn).select("date", "tmax", "tmin")
            j = (
                day.filter(pl.col("complete"))
                .join(g, on="date")
                .filter(pl.col("tmax").is_not_null() & pl.col("tmin").is_not_null())
            )
            b = (
                j.group_by("year")
                .agg(
                    ((pl.col("tmax") - pl.col("tmax_h")).mean() / 10).alias("tmax_minus_hourly_c"),
                    ((pl.col("tmin") - pl.col("tmin_h")).mean() / 10).alias("tmin_minus_hourly_c"),
                    pl.len().alias("n"),
                )
                .sort("year")
            )
            bias = b

    out = ANALYSIS_DIR / "hourly" / st.id
    out.mkdir(parents=True, exist_ok=True)
    annual.write_parquet(out / "annual.parquet")
    monthly.write_parquet(out / "monthly.parquet")
    diurnal.write_parquet(out / "diurnal.parquet")
    if bias is not None:
        bias.write_parquet(out / "ghcn_bias.parquet")
    meta = {
        "id": st.id,
        "wban": st.wban,
        "ghcn": st.ghcn,
        "short": st.short,
        "name": st.name,
        "state": st.state,
        "lat": st.lat,
        "lon": st.lon,
        "elev_m": st.elev_m,
        "tz": st.tz,
        "first_date": str(day["date"].min()),
        "last_date": str(day["date"].max()),
        "complete_years": int(annual.filter(pl.col("complete") & ~pl.col("partial")).height),
    }
    (out / "meta.json").write_text(json.dumps(meta))
    a = annual.filter(pl.col("complete"))
    return f"  {st.id} {st.short:<32} {meta['first_date'][:4]}-{meta['last_date']}  complete years {meta['complete_years']:>3}  hours>=95F last10 {a.tail(10)['hours_95'].mean():.0f}"


def run_analyze(only: list[str] | None = None) -> None:
    stations = load_isd_stations(only)
    print(f"==> analyzing {len(stations)} hourly stations")
    with ProcessPoolExecutor() as pool:
        for i, line in enumerate(pool.map(analyze_station, stations, chunksize=2), 1):
            if len(stations) <= 20 or i % 100 == 0 or "not ingested" in line:
                print(line if len(stations) <= 20 else f"  … {i}/{len(stations)}", flush=True)
