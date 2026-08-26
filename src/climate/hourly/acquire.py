"""Download ISD-Lite files (one per station-year) for the hourly tier.

Manifests are sharded per year (manifests/isd_lite_<year>.json) — ~700 entries each.
The current and previous year are re-fetched on --refresh; older years never change.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

from climate.acquire.base import download, flush_manifests
from climate.isd import HISTORY_URL, ISD_META, LITE_BASE, LITE_FIRST_YEAR, load_isd_stations


def lite_url(usaf: str, wban: str, year: int) -> str:
    return f"{LITE_BASE}{year}/{usaf}-{wban}-{year}.gz"


def run_acquire(only: list[str] | None = None, refresh: bool = False) -> None:
    print("==> ISD history")
    download(ISD_META, HISTORY_URL, refresh=True, throttle_seconds=0)
    stations = load_isd_stations(only)
    this_year = datetime.now(UTC).year
    jobs = []
    for st in stations:
        for year in range(max(LITE_FIRST_YEAR, st.begin), this_year + 1):
            jobs.append((st, year))
    print(f"==> {len(stations)} stations, {len(jobs)} station-years")

    def fetch(job):
        st, year = job
        for usaf in st.usaf_for(year):
            path = download(
                f"isd_lite_{year}",
                lite_url(usaf, st.wban, year),
                filename=f"{usaf}-{st.wban}-{year}.gz",
                refresh=refresh and year >= this_year - 1,
                throttle_seconds=0.05,
                quiet=True,
            )
            if path is not None:
                return st.wban, year, path
        return st.wban, year, None

    missing = 0
    with ThreadPoolExecutor(max_workers=8) as pool:
        for i, (_w, _y, path) in enumerate(pool.map(fetch, jobs), 1):
            if path is None:
                missing += 1
            if i % 500 == 0:
                print(f"  … {i}/{len(jobs)}", flush=True)
    flush_manifests()
    print(f"  done; {missing} station-years unavailable (normal for early years)")
