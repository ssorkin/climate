"""clim ingest: raw GHCN-Daily files -> Parquet store -> DuckDB views."""

from __future__ import annotations

from climate.acquire.ghcnd import meta_dataset, region_dataset
from climate.config import load_regions
from climate.ingest import db
from climate.ingest.ghcnd import parse_inventory, parse_station_csv, parse_stations_txt
from climate.paths import PARQUET_DIR, RAW_DIR


def run_ingest(region: str = "all") -> None:
    meta_dir = RAW_DIR / meta_dataset()
    print("==> station metadata")
    stations = parse_stations_txt(meta_dir / "ghcnd-stations.txt")
    out = PARQUET_DIR / "ghcnd_stations" / "data.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    stations.write_parquet(out)
    inventory = parse_inventory(meta_dir / "ghcnd-inventory.txt")
    out = PARQUET_DIR / "ghcnd_inventory" / "data.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    inventory.write_parquet(out)
    print(f"  {stations.height:,} stations, {inventory.height:,} inventory rows")

    for reg in load_regions(region):
        print(f"==> region {reg.id}")
        raw_dir = RAW_DIR / region_dataset(reg.id)
        for st in reg.stations:
            src = raw_dir / f"{st.id}.csv.gz"
            if not src.exists():
                raise SystemExit(f"ingest: missing {src}; run `clim acquire --region {reg.id}`")
            df = parse_station_csv(src)
            dest = PARQUET_DIR / "ghcnd_daily" / f"station={st.id}" / "data.parquet"
            dest.parent.mkdir(parents=True, exist_ok=True)
            df.write_parquet(dest)
            first, last = df["date"].min(), df["date"].max()
            print(f"  {st.id} {st.short:<20} {df.height:>8,} rows  {first} .. {last}")

    db.build()
