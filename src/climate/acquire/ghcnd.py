"""Download GHCN-Daily station files and metadata from NCEI.

Layout in data/raw/:
  ghcnd_meta/      ghcnd-stations.txt, ghcnd-inventory.txt, ghcnd-version.txt, readme.txt
  ghcnd_<region>/  by_station/<ID>.csv.gz for every station in stations/<region>.yaml

One manifest per region (manifests/ghcnd_<region>.json) so regions are additive.
"""

from __future__ import annotations

from climate.acquire.base import download
from climate.config import load_regions

BASE = "https://www.ncei.noaa.gov/pub/data/ghcn/daily/"
META_FILES = ["ghcnd-stations.txt", "ghcnd-inventory.txt", "ghcnd-version.txt", "readme.txt"]


def station_url(station_id: str) -> str:
    return f"{BASE}by_station/{station_id}.csv.gz"


def meta_dataset() -> str:
    return "ghcnd_meta"


def region_dataset(region_id: str) -> str:
    return f"ghcnd_{region_id}"


def run_acquire(region: str = "all", refresh: bool = False, force: bool = False) -> None:
    failed: list[str] = []
    print("==> GHCN-Daily metadata")
    for name in META_FILES:
        if download(meta_dataset(), BASE + name, refresh=refresh, force=force) is None:
            failed.append(name)

    for reg in load_regions(region):
        print(f"==> region {reg.id}: {len(reg.stations)} stations")
        for st in reg.stations:
            path = download(
                region_dataset(reg.id),
                station_url(st.id),
                note=st.short,
                refresh=refresh,
                force=force,
            )
            if path is None:
                failed.append(st.id)

    if failed:
        # Leave previous files and manifests intact; the nightly refresh must stop here
        # rather than rebuild the site from a partial pull.
        raise SystemExit(f"acquire: {len(failed)} download(s) failed: {', '.join(failed)}")
