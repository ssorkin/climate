"""Download GHCN-Daily station files and metadata from NCEI.

Layout in data/raw/:
  ghcnd_meta/      ghcnd-stations.txt, ghcnd-inventory.txt, ghcnd-version.txt, readme.txt
  ghcnd_<region>/  by_station/<ID>.csv.gz for every station in stations/<region>.yaml

One manifest per region (manifests/ghcnd_<region>.json) so regions are additive.
"""

from __future__ import annotations

from climate.acquire.base import download, flush_manifests
from climate.config import load_regions

BASE = "https://www.ncei.noaa.gov/pub/data/ghcn/daily/"
META_FILES = ["ghcnd-stations.txt", "ghcnd-inventory.txt", "ghcnd-version.txt", "readme.txt"]


def station_url(station_id: str) -> str:
    return f"{BASE}by_station/{station_id}.csv.gz"


def meta_dataset() -> str:
    return "ghcnd_meta"


def region_dataset(region_id: str) -> str:
    return "ghcnd_daily"


def run_acquire(region: str = "all", refresh: bool = False, force: bool = False) -> None:
    failed: list[str] = []
    print("==> GHCN-Daily metadata")
    for name in META_FILES:
        if download(meta_dataset(), BASE + name, refresh=refresh, force=force) is None:
            failed.append(name)

    from climate.config import unique_stations

    regions = load_regions(region)
    todo = unique_stations(regions)
    print(f"==> {len(todo)} stations across {', '.join(r.id for r in regions)}")
    from concurrent.futures import ThreadPoolExecutor

    def fetch(item):
        reg, st = item
        return st.id, download(
            region_dataset(reg.id),
            station_url(st.id),
            note=st.short,
            refresh=refresh,
            force=force,
            throttle_seconds=0.25 if len(todo) > 100 else 1.0,
        )

    workers = 6 if len(todo) > 100 else 1
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for i, (sid, path) in enumerate(pool.map(fetch, todo), 1):
            if path is None:
                failed.append(sid)
            if i % 250 == 0:
                print(f"  … {i}/{len(todo)}", flush=True)

    from climate.acquire.ushcn import run_acquire_ushcn

    failed += run_acquire_ushcn(refresh=refresh, force=force)
    flush_manifests()

    if failed:
        # Leave previous files and manifests intact; the nightly refresh must stop here
        # rather than rebuild the site from a partial pull.
        raise SystemExit(f"acquire: {len(failed)} download(s) failed: {', '.join(failed)}")
