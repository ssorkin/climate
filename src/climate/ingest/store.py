"""Read access to the Parquet store (what analysis and checks consume)."""

from __future__ import annotations

import polars as pl

from climate.paths import PARQUET_DIR


def daily_path(station_id: str):
    return PARQUET_DIR / "ghcnd_daily" / f"station={station_id}" / "data.parquet"


def load_daily_long(station_id: str) -> pl.DataFrame:
    return pl.read_parquet(daily_path(station_id))


def load_daily_wide(station_id: str) -> pl.DataFrame:
    """One row per date: tmax, tmin, prcp (valid rows only, tenths), obs times, qflags.

    Flagged values are nulled in the value columns and their flag kept in *_qflag so
    the export can show "withheld (QFLAG X)" instead of a number.
    """
    long = load_daily_long(station_id)
    frames = []
    for el in ("TMAX", "TMIN", "PRCP"):
        sub = long.filter(pl.col("element") == el)
        lower = el.lower()
        frames.append(
            sub.select(
                "date",
                pl.when(pl.col("qflag") == "").then(pl.col("value")).otherwise(None).alias(lower),
                pl.col("qflag").alias(f"{lower}_qflag"),
                pl.col("value").alias(f"{lower}_raw"),
                pl.col("obs_time").alias(f"obs_{lower}"),
            ).unique(subset=["date"], keep="first")
        )
    out = frames[0]
    for f in frames[1:]:
        out = out.join(f, on="date", how="full", coalesce=True)
    return out.sort("date")


def load_stations() -> pl.DataFrame:
    return pl.read_parquet(PARQUET_DIR / "ghcnd_stations" / "data.parquet")


def load_inventory() -> pl.DataFrame:
    return pl.read_parquet(PARQUET_DIR / "ghcnd_inventory" / "data.parquet")
