"""Parse GHCN-Daily station CSVs and the fixed-width metadata files.

Station CSV rows (no header): ID,YYYYMMDD,ELEMENT,VALUE,MFLAG,QFLAG,SFLAG,OBS-TIME.
VALUE is tenths of °C for temperatures, tenths of mm for PRCP. Rows with a non-empty
QFLAG failed one of NOAA's quality checks; they are kept here (so `clim check` can
count them) and excluded from every aggregate downstream.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

ELEMENTS = ("TMAX", "TMIN", "PRCP")

CSV_COLUMNS = ["id", "date_raw", "element", "value", "mflag", "qflag", "sflag", "obs_time"]


def parse_station_csv(path: Path, elements: tuple[str, ...] = ELEMENTS) -> pl.DataFrame:
    df = pl.read_csv(
        path,
        has_header=False,
        new_columns=CSV_COLUMNS,
        schema_overrides={
            "id": pl.Utf8,
            "date_raw": pl.Utf8,
            "element": pl.Utf8,
            "value": pl.Int32,
            "mflag": pl.Utf8,
            "qflag": pl.Utf8,
            "sflag": pl.Utf8,
            "obs_time": pl.Utf8,
        },
        empty_string_is_null=False,
    )
    return (
        df.filter(pl.col("element").is_in(elements))
        .with_columns(pl.col("date_raw").str.strptime(pl.Date, "%Y%m%d").alias("date"))
        .select(["id", "date", "element", "value", "mflag", "qflag", "sflag", "obs_time"])
        .sort(["element", "date"])
    )


def parse_stations_txt(path: Path) -> pl.DataFrame:
    """ghcnd-stations.txt: fixed-width columns per NOAA's readme.txt (1-based)."""
    rows = []
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            if len(line) < 71:
                continue
            rows.append(
                {
                    "id": line[0:11].strip(),
                    "lat": float(line[12:20]),
                    "lon": float(line[21:30]),
                    "elev_m": float(line[31:37]),
                    "state": line[38:40].strip(),
                    "name": line[41:71].strip(),
                    "gsn": line[72:75].strip(),
                    "hcn_crn": line[76:79].strip(),
                    "wmo": line[80:85].strip(),
                }
            )
    return pl.DataFrame(rows)


def parse_inventory(path: Path) -> pl.DataFrame:
    """ghcnd-inventory.txt: ID LAT LON ELEMENT FIRSTYEAR LASTYEAR (space separated)."""
    ids, elems, firsts, lasts = [], [], [], []
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            parts = line.split()
            if len(parts) != 6:
                continue
            ids.append(parts[0])
            elems.append(parts[3])
            firsts.append(int(parts[4]))
            lasts.append(int(parts[5]))
    return pl.DataFrame(
        {"id": ids, "element": elems, "first_year": firsts, "last_year": lasts},
        schema={"id": pl.Utf8, "element": pl.Utf8, "first_year": pl.Int32, "last_year": pl.Int32},
    )
