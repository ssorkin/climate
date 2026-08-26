"""Synthetic-station builder shared by the metric tests."""

from __future__ import annotations

from datetime import date, timedelta

import polars as pl
import pytest

from climate.config import load_analysis_config


def noaa_tenths(f: float) -> int:
    """NOAA stores whole-°F observations as round((F-32)*50/9) tenths of °C (verified)."""
    return round((f - 32) * 50 / 9)


def make_daily(
    start: date,
    end: date,
    tmax_f=80,
    tmin_f=55,
    missing: set[date] | None = None,
    missing_tmin: set[date] | None = None,
    qflags: dict[date, str] | None = None,
    obs: str = "1600",
) -> pl.DataFrame:
    """Wide daily frame like ingest.store.load_daily_wide produces.

    tmax_f / tmin_f: constant °F or callable(date) -> °F (None = missing that day).
    """
    missing = missing or set()
    missing_tmin = missing_tmin or set()
    qflags = qflags or {}
    rows = []
    d = start
    while d <= end:
        fx = tmax_f(d) if callable(tmax_f) else tmax_f
        fn = tmin_f(d) if callable(tmin_f) else tmin_f
        q = qflags.get(d, "")
        raw_max = None if fx is None or d in missing else noaa_tenths(fx)
        raw_min = None if fn is None or d in missing or d in missing_tmin else noaa_tenths(fn)
        rows.append(
            {
                "date": d,
                "tmax": None if q else raw_max,
                "tmax_qflag": q if raw_max is not None else None,
                "tmax_raw": raw_max,
                "obs_tmax": obs if raw_max is not None else None,
                "tmin": None if q else raw_min,
                "tmin_qflag": q if raw_min is not None else None,
                "tmin_raw": raw_min,
                "obs_tmin": obs if raw_min is not None else None,
                "prcp": 0,
                "prcp_qflag": "",
                "prcp_raw": 0,
                "obs_prcp": obs,
            }
        )
        d += timedelta(days=1)
    df = pl.DataFrame(
        rows,
        schema={
            "date": pl.Date,
            "tmax": pl.Int32,
            "tmax_qflag": pl.Utf8,
            "tmax_raw": pl.Int32,
            "obs_tmax": pl.Utf8,
            "tmin": pl.Int32,
            "tmin_qflag": pl.Utf8,
            "tmin_raw": pl.Int32,
            "obs_tmin": pl.Utf8,
            "prcp": pl.Int32,
            "prcp_qflag": pl.Utf8,
            "prcp_raw": pl.Int32,
            "obs_prcp": pl.Utf8,
        },
    )
    # Days with no reading at all are absent from the store (like the real files).
    return df.filter(pl.col("tmax_raw").is_not_null() | pl.col("tmin_raw").is_not_null())


@pytest.fixture
def cfg() -> dict:
    return load_analysis_config()
