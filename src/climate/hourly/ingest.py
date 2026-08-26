"""ISD-Lite -> Parquet per station, in local time.

Rows: ts_utc, date (local), hour (local clock, DST-aware), temp, dewp (tenths °C, null
when missing). Local time matters for "night" and "afternoon"; the tz comes from the
station coordinates (stations/isd.yaml).
"""

from __future__ import annotations

import gzip
from concurrent.futures import ProcessPoolExecutor

import polars as pl

from climate.isd import IsdStation, load_isd_stations
from climate.paths import PARQUET_DIR, RAW_DIR


def hourly_path(station_id: str):
    return PARQUET_DIR / "isd_hourly" / f"station={station_id}" / "data.parquet"


def _parse_file(path) -> list[tuple]:
    rows = []
    with gzip.open(path, "rt") as f:
        for line in f:
            p = line.split()
            if len(p) < 6:
                continue
            y, m, d, h = int(p[0]), int(p[1]), int(p[2]), int(p[3])
            t, td = int(p[4]), int(p[5])
            rows.append((y, m, d, h, None if t == -9999 else t, None if td == -9999 else td))
    return rows


def ingest_station(st: IsdStation) -> str:
    rows = []
    for year_dir in sorted(RAW_DIR.glob("isd_lite_*")):
        year = int(year_dir.name.rsplit("_", 1)[1])
        for usaf in st.usaf_for(year):
            f = year_dir / f"{usaf}-{st.wban}-{year}.gz"
            if f.exists():
                rows.extend(_parse_file(f))
                break
    if not rows:
        return f"  {st.id} {st.short}: no files"
    df = pl.DataFrame(
        rows,
        schema={
            "y": pl.Int32,
            "m": pl.Int8,
            "d": pl.Int8,
            "h": pl.Int8,
            "temp": pl.Int32,
            "dewp": pl.Int32,
        },
        orient="row",
    )
    df = df.with_columns(
        pl.datetime(pl.col("y"), pl.col("m"), pl.col("d"), pl.col("h"), time_zone="UTC").alias(
            "ts_utc"
        )
    ).drop("y", "m", "d", "h")
    df = df.unique(subset=["ts_utc"], keep="last").sort("ts_utc")
    local = df["ts_utc"].dt.convert_time_zone(st.tz)
    df = df.with_columns(local.dt.date().alias("date"), local.dt.hour().cast(pl.Int8).alias("hour"))
    out = hourly_path(st.id)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.select("ts_utc", "date", "hour", "temp", "dewp").write_parquet(out)
    return f"  {st.id} {st.short:<32} {df.height:>9,} obs  {df['date'].min()} .. {df['date'].max()}"


def run_ingest(only: list[str] | None = None) -> None:
    stations = load_isd_stations(only)
    print(f"==> ingesting {len(stations)} hourly stations")
    with ProcessPoolExecutor() as pool:
        for i, line in enumerate(pool.map(ingest_station, stations, chunksize=2), 1):
            if len(stations) <= 20 or i % 100 == 0:
                print(line if len(stations) <= 20 else f"  … {i}/{len(stations)}", flush=True)
