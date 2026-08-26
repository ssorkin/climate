"""NOAA USHCN v2.5 monthly series: raw and fully homogenized (FLs.52j).

Used only to show, for the USHCN stations, where NOAA's pairwise homogenization
detects site/instrument changes and how much its adjustments move the counts.
"""

from __future__ import annotations

from climate.acquire.base import download

BASE = "https://www.ncei.noaa.gov/pub/data/ushcn/v2.5/"
FILES = [
    "ushcn.tmax.latest.raw.tar.gz",
    "ushcn.tmax.latest.FLs.52j.tar.gz",
    "ushcn.tmin.latest.raw.tar.gz",
    "ushcn.tmin.latest.FLs.52j.tar.gz",
]
DATASET = "ushcn"


def run_acquire_ushcn(refresh: bool = False, force: bool = False) -> list[str]:
    failed = []
    print("==> USHCN v2.5 monthly (raw + homogenized)")
    for name in FILES:
        if download(DATASET, BASE + name, refresh=refresh, force=force) is None:
            failed.append(name)
    return failed
