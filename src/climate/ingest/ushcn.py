"""Parse USHCN v2.5 monthly files for the configured stations into Parquet.

File format (readme.txt): station id (11) + element (4) + year (4), then 12 × (value
in hundredths °C, 3 flag chars). -9999 = missing. A USHCN id USH000xxxxx matches the
GHCN-Daily COOP id USC000xxxxx.
"""

from __future__ import annotations

import tarfile

import polars as pl

from climate.acquire.ushcn import DATASET, FILES
from climate.paths import PARQUET_DIR, RAW_DIR


def ushcn_id(ghcnd_id: str) -> str:
    return "USH" + ghcnd_id[3:]


def _parse(text: str, kind: str, element: str, sid: str) -> list[dict]:
    rows = []
    for line in text.splitlines():
        if len(line) < 16 + 12 * 9:
            continue
        year = int(line[12:16])
        for m in range(12):
            v = int(line[16 + m * 9 : 16 + m * 9 + 6])
            flag = line[16 + m * 9 + 6 : 16 + m * 9 + 9].strip()
            rows.append(
                {
                    "id": sid,
                    "year": year,
                    "month": m + 1,
                    "element": element,
                    "kind": kind,
                    "value_c": None if v == -9999 else v / 100,
                    "flag": flag,
                }
            )
    return rows


def ingest_ushcn(station_ids: list[str]) -> pl.DataFrame:
    wanted = {ushcn_id(s): s for s in station_ids}
    rows: list[dict] = []
    for name in FILES:
        path = RAW_DIR / DATASET / name
        if not path.exists():
            raise SystemExit(f"ingest: missing {path}; run `clim acquire`")
        element = "TMAX" if ".tmax." in name else "TMIN"
        kind = "raw" if ".raw." in name else "adj"
        with tarfile.open(path, "r:gz") as tar:
            for member in tar.getmembers():
                base = member.name.rsplit("/", 1)[-1]
                uid = base[:11]
                if uid in wanted and member.isfile():
                    text = tar.extractfile(member).read().decode("ascii", errors="replace")
                    rows.extend(_parse(text, kind, element, wanted[uid]))
    df = pl.DataFrame(
        rows,
        schema={
            "id": pl.Utf8,
            "year": pl.Int32,
            "month": pl.Int8,
            "element": pl.Utf8,
            "kind": pl.Utf8,
            "value_c": pl.Float64,
            "flag": pl.Utf8,
        },
    )
    out = PARQUET_DIR / "ushcn_monthly" / "data.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(out)
    return df


def load_ushcn() -> pl.DataFrame | None:
    p = PARQUET_DIR / "ushcn_monthly" / "data.parquet"
    return pl.read_parquet(p) if p.exists() else None
