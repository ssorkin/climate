"""clim ingest: raw GHCN-Daily files -> Parquet store -> DuckDB views."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor

from climate.acquire.ghcnd import meta_dataset, region_dataset
from climate.config import load_regions, unique_stations
from climate.ingest import db
from climate.ingest.ghcnd import parse_inventory, parse_station_csv, parse_stations_txt
from climate.ingest.ushcn import ingest_ushcn
from climate.paths import PARQUET_DIR, RAW_DIR


def _ingest_one(args: tuple[str, str, str]) -> str:
    region_id, sid, short = args
    src = RAW_DIR / region_dataset(region_id) / f"{sid}.csv.gz"
    df = parse_station_csv(src)
    dest = PARQUET_DIR / "ghcnd_daily" / f"station={sid}" / "data.parquet"
    dest.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(dest)
    return f"  {sid} {short:<20} {df.height:>8,} rows  {df['date'].min()} .. {df['date'].max()}"


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

    regions = load_regions(region)
    todo = unique_stations(regions)
    print(f"==> {len(todo)} stations")
    missing = [
        st.id
        for reg, st in todo
        if not (RAW_DIR / region_dataset(reg.id) / f"{st.id}.csv.gz").exists()
    ]
    if missing:
        raise SystemExit(
            f"ingest: {len(missing)} raw files missing (e.g. {missing[0]}); run `clim acquire`"
        )
    with ProcessPoolExecutor() as pool:
        for i, line in enumerate(
            pool.map(_ingest_one, [(reg.id, st.id, st.short) for reg, st in todo], chunksize=8), 1
        ):
            if len(todo) <= 40 or i % 500 == 0:
                print(line if len(todo) <= 40 else f"  … {i}/{len(todo)}")

    ids = [st.id for _, st in todo]
    ush = ingest_ushcn(ids)
    print(
        f"==> USHCN monthly: {ush['id'].n_unique()} of {len(ids)} stations are USHCN ({ush.height:,} rows)"
    )

    db.build()
