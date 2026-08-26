"""GHCNh -> hourly Parquet per station (local time) -> derived daily max/min store.

Hourly rows: ts_utc, date (local), hour (local clock), temp, dewp (tenths °C), rh (%),
wetbulb (tenths °C). Values whose quality code marks a failed check are dropped.

Daily rows (the store the rest of the pipeline reads, in GHCN-Daily's long layout):
TMAX/TMIN per local day from the hourly samples, obs_time "2400", empty QFLAG. A day
counts when it has >= 8 readings, no gap longer than 3 h, a first reading by 03:00 and
a last one after 21:00 — so 3-hourly synoptic years count, hourly years count, and a day
with a 6-hour outage doesn't. Per-day n_obs and max_gap_h are kept in meta.parquet.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor

import polars as pl

from climate.ghcnh import HourlyStation, load_hourly_stations
from climate.ingest.store import daily_path
from climate.paths import PARQUET_DIR, RAW_DIR

# Legacy numeric codes that passed (0/1/4/5/9) and validator letters that keep the value.
# Anything else — 2/3/6/7 (suspect/erroneous) or a lower-case letter naming a failed
# GHCNh check — drops the value. Missing code = not checked = keep.
GOOD_Q = {None, "", "0", "1", "4", "5", "9", "A", "U", "P", "I", "M", "R"}
COLS = [
    "DATE",
    "temperature",
    "temperature_Quality_Code",
    "dew_point_temperature",
    "dew_point_temperature_Quality_Code",
    "relative_humidity",
    "wet_bulb_temperature",
]


def hourly_path(station_id: str):
    return PARQUET_DIR / "hourly" / f"station={station_id}" / "data.parquet"


def daily_meta_path(station_id: str):
    return PARQUET_DIR / "daily" / f"station={station_id}" / "meta.parquet"


def _files_for(st: HourlyStation):
    return [
        f
        for year in st.years
        if (f := RAW_DIR / f"ghcnh_{year}" / f"GHCNh_{st.id}_{year}.parquet").exists()
    ]


def _read(path) -> pl.DataFrame | None:
    try:
        df = pl.read_parquet(path, columns=COLS)
    except Exception:  # noqa: BLE001 — a few early files lack some columns
        df = pl.read_parquet(path)
        for c in COLS:
            if c not in df.columns:
                df = df.with_columns(pl.lit(None).alias(c))
        df = df.select(COLS)
    okq = list(GOOD_Q - {None})
    t = pl.col("temperature").cast(pl.Float64, strict=False)
    d = pl.col("dew_point_temperature").cast(pl.Float64, strict=False)
    rh = pl.col("relative_humidity").cast(pl.Float64, strict=False)
    wb = pl.col("wet_bulb_temperature").cast(pl.Float64, strict=False)
    tq = pl.col("temperature_Quality_Code")
    dq = pl.col("dew_point_temperature_Quality_Code")
    return df.select(
        pl.col("DATE")
        .str.strptime(pl.Datetime("us"), "%Y-%m-%dT%H:%M:%S", strict=False)
        .alias("ts"),
        pl.when((tq.is_in(okq) | tq.is_null()) & t.is_between(-70, 60))
        .then((t * 10).round())
        .otherwise(None)
        .cast(pl.Int32, strict=False)
        .alias("temp"),
        pl.when((dq.is_in(okq) | dq.is_null()) & d.is_between(-70, 60))
        .then((d * 10).round())
        .otherwise(None)
        .cast(pl.Int32, strict=False)
        .alias("dewp"),
        pl.when(rh.is_between(0, 100))
        .then(rh.round())
        .otherwise(None)
        .cast(pl.Int16, strict=False)
        .alias("rh"),
        pl.when(wb.is_between(-60, 60))
        .then((wb * 10).round())
        .otherwise(None)
        .cast(pl.Int32, strict=False)
        .alias("wetbulb"),
    ).filter(pl.col("ts").is_not_null())


def ingest_station(st: HourlyStation) -> str:
    frames = [f for f in (_read(p) for p in _files_for(st)) if f is not None and f.height]
    if not frames:
        return f"  {st.id} {st.short}: no files"
    df = pl.concat(frames).filter(pl.col("temp").is_not_null() | pl.col("dewp").is_not_null())
    df = df.with_columns(pl.col("ts").dt.replace_time_zone("UTC").alias("ts_utc")).drop("ts")
    df = df.unique(subset=["ts_utc"], keep="last").sort("ts_utc")
    local = df["ts_utc"].dt.convert_time_zone(st.tz)
    df = df.with_columns(
        local.dt.date().alias("date"),
        local.dt.hour().cast(pl.Int8).alias("hour"),
        (local.dt.hour().cast(pl.Float64) + local.dt.minute().cast(pl.Float64) / 60).alias("h"),
    )
    out = hourly_path(st.id)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.select("ts_utc", "date", "hour", "temp", "dewp", "rh", "wetbulb").write_parquet(out)

    t = df.filter(pl.col("temp").is_not_null()).sort("ts_utc")
    day = (
        t.group_by("date")
        .agg(
            pl.len().alias("n_obs"),
            pl.col("temp").max().alias("tmax"),
            pl.col("temp").min().alias("tmin"),
            pl.col("h").min().alias("first_h"),
            pl.col("h").max().alias("last_h"),
            pl.col("h").diff().max().alias("max_gap_h"),
        )
        .with_columns(
            (
                (pl.col("n_obs") >= 8)
                & (pl.col("max_gap_h").fill_null(24) <= 3.05)
                & (pl.col("first_h") <= 3.0)
                & (pl.col("last_h") >= 21.0)
            ).alias("complete")
        )
        .sort("date")
    )
    good = day.filter(pl.col("complete"))
    long = (
        pl.concat(
            [
                good.select(
                    pl.lit(st.id).alias("id"),
                    "date",
                    pl.lit("TMAX").alias("element"),
                    pl.col("tmax").alias("value"),
                ),
                good.select(
                    pl.lit(st.id).alias("id"),
                    "date",
                    pl.lit("TMIN").alias("element"),
                    pl.col("tmin").alias("value"),
                ),
            ]
        )
        .with_columns(
            pl.lit("").alias("mflag"),
            pl.lit("").alias("qflag"),
            pl.lit("H").alias("sflag"),
            pl.lit("2400").alias("obs_time"),
        )
        .sort(["element", "date"])
    )
    dp = daily_path(st.id)
    dp.parent.mkdir(parents=True, exist_ok=True)
    long.write_parquet(dp)
    day.select("date", "n_obs", "max_gap_h", "complete").write_parquet(daily_meta_path(st.id))
    return (
        f"  {st.id} {st.short:<38} {df.height:>9,} obs  {df['date'].min()} .. {df['date'].max()}"
        f"  complete days {good.height:>6,} of {day.height:,}"
    )


def run_ingest(only: list[str] | None = None) -> None:
    stations = load_hourly_stations(only)
    print(f"==> ingesting {len(stations)} GHCNh stations (hourly + derived daily)")
    with ProcessPoolExecutor() as pool:
        for i, line in enumerate(pool.map(ingest_station, stations, chunksize=2), 1):
            if len(stations) <= 30 or i % 100 == 0:
                print(line if len(stations) <= 30 else f"  … {i}/{len(stations)}", flush=True)
