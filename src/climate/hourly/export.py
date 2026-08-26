"""Hourly tier -> site/static/data/hourly/<GHCN id or ISD id>.json, one file per station,
attached to the station page by the GHCN twin's id."""

from __future__ import annotations

import json

import polars as pl

from climate.analysis.export import col, dump
from climate.hourly.analyze import HI_THRESHOLDS_F, HOUR_THRESHOLDS_F, NIGHT_THRESHOLDS_F
from climate.isd import load_isd_stations
from climate.paths import ANALYSIS_DIR, SITE_DATA_DIR


def export_station(st) -> tuple[str, int] | None:
    d = ANALYSIS_DIR / "hourly" / st.id
    if not (d / "meta.json").exists():
        return None
    meta = json.loads((d / "meta.json").read_text())
    annual = pl.read_parquet(d / "annual.parquet")
    monthly = pl.read_parquet(d / "monthly.parquet")
    diurnal = pl.read_parquet(d / "diurnal.parquet")
    bias = pl.read_parquet(d / "ghcn_bias.parquet") if (d / "ghcn_bias.parquet").exists() else None
    complete = annual.filter(pl.col("complete") & ~pl.col("partial"))
    last = int(complete["year"].max()) if complete.height else None

    def win(y0, y1):
        s = annual.filter((pl.col("year") >= y0) & (pl.col("year") <= y1) & pl.col("complete"))
        n = annual.filter(
            (pl.col("year") >= y0) & (pl.col("year") <= y1) & pl.col("nights_complete")
        )
        out = {"years": [y0, y1], "n": s.height}
        for t in HOUR_THRESHOLDS_F:
            out[f"hours_{t}"] = round(float(s[f"hours_{t}"].mean()), 1) if s.height else None
        for t in HI_THRESHOLDS_F:
            out[f"hi_hours_{t}"] = round(float(s[f"hi_hours_{t}"].mean()), 1) if s.height else None
        for t in NIGHT_THRESHOLDS_F:
            out[f"norelief_{t}"] = round(float(n[f"norelief_{t}"].mean()), 1) if n.height else None
        return out

    first = int(complete["year"].min()) if complete.height else None
    windows = {}
    if last and first:
        windows = {"first10": win(first, first + 9), "last10": win(last - 9, last)}
    payload = {
        **meta,
        "thresholds_f": {
            "hours": list(HOUR_THRESHOLDS_F),
            "nights": list(NIGHT_THRESHOLDS_F),
            "heat_index": list(HI_THRESHOLDS_F),
        },
        "annual": {
            "year": col(annual, "year"),
            "complete": col(annual, "complete"),
            "nights_complete": col(annual, "nights_complete"),
            "partial": col(annual, "partial"),
            "days_complete": col(annual, "days_complete"),
            "tmax_h_mean_c": col(annual, "tmax_h_mean_c"),
            "tmin_h_mean_c": col(annual, "tmin_h_mean_c"),
            "hours": {str(t): col(annual, f"hours_{t}") for t in HOUR_THRESHOLDS_F},
            "hi_hours": {str(t): col(annual, f"hi_hours_{t}") for t in HI_THRESHOLDS_F},
            "norelief": {str(t): col(annual, f"norelief_{t}") for t in NIGHT_THRESHOLDS_F},
        },
        "monthly": {
            "year": col(monthly, "year"),
            "month": col(monthly, "month"),
            "complete": col(monthly, "complete"),
            "hours": {str(t): col(monthly, f"hours_{t}") for t in HOUR_THRESHOLDS_F},
            "norelief": {str(t): col(monthly, f"norelief_{t}") for t in NIGHT_THRESHOLDS_F},
        },
        "diurnal": {
            str(dec): [
                round(v / 10, 2) if v is not None else None
                for v in diurnal.filter(pl.col("decade") == dec).sort("hour")["t"].to_list()
            ]
            for dec in sorted(diurnal["decade"].unique().to_list())
        },
        "windows": windows,
        "ghcn_bias": (
            {
                "year": col(bias, "year"),
                "tmax_minus_hourly_c": col(bias, "tmax_minus_hourly_c"),
                "tmin_minus_hourly_c": col(bias, "tmin_minus_hourly_c"),
            }
            if bias is not None
            else None
        ),
    }
    key = st.ghcn or st.id
    n = dump(SITE_DATA_DIR / "hourly" / f"{key}.json", payload)
    return key, n


def run_export(only: list[str] | None = None) -> None:
    stations = load_isd_stations(only)
    print(f"==> exporting {len(stations)} hourly stations")
    index = []
    for st in stations:
        r = export_station(st)
        if r:
            key, n = r
            index.append(
                {
                    "id": key,
                    "isd": st.id,
                    "short": st.short,
                    "state": st.state,
                    "lat": st.lat,
                    "lon": st.lon,
                }
            )
            if len(stations) <= 20:
                print(f"  hourly/{key}.json {n / 1e3:.0f} KB")
    n = dump(SITE_DATA_DIR / "hourly" / "index.json", {"stations": index})
    print(f"  hourly/index.json {n / 1e3:.0f} KB ({len(index)} stations)")
