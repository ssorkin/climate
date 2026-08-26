"""Download GHCNh station-year Parquet files for the hourly tier.

Manifests are sharded per year (manifests/ghcnh_<year>.json). The current and previous
year are re-fetched on --refresh; older years never change.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

from climate.acquire.base import download, flush_manifests
from climate.ghcnh import (
    DOC_URL,
    INVENTORY_URL,
    META,
    STATION_LIST_URL,
    load_hourly_stations,
    year_url,
)


def run_acquire(only: list[str] | None = None, refresh: bool = False) -> None:
    print("==> GHCNh metadata")
    for url in (INVENTORY_URL, STATION_LIST_URL, DOC_URL):
        download(META, url, refresh=refresh, throttle_seconds=0)
    stations = load_hourly_stations(only)
    this_year = datetime.now(UTC).year
    jobs = [(st, year) for st in stations for year in st.years if year <= this_year]
    print(f"==> {len(stations)} stations, {len(jobs)} station-years")

    def fetch(job):
        st, year = job
        return download(
            f"ghcnh_{year}",
            year_url(st.id, year),
            filename=f"GHCNh_{st.id}_{year}.parquet",
            refresh=refresh and year >= this_year - 1,
            throttle_seconds=0.02,
            quiet=True,
        )

    missing = 0
    with ThreadPoolExecutor(max_workers=20) as pool:
        for i, path in enumerate(pool.map(fetch, jobs), 1):
            if path is None:
                missing += 1
            if i % 1000 == 0:
                print(f"  … {i}/{len(jobs)}", flush=True)
    flush_manifests()
    print(f"  done; {missing} station-years unavailable")
