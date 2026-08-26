"""GHCNh (NOAA's Global Historical Climatology Network – hourly) as the primary source.

GHCNh replaces ISD (its README says so) and keeps GHCN station ids (USW000<WBAN> for
airports). Files: one Parquet per station-year under access/by-year/<YYYY>/parquet/.
The station list (stations/hourly.yaml) is generated from NOAA's inventory: a station
qualifies when, since FIRST_YEAR, it has >= min_years "hourly years" — years with at
least HOURLY_YEAR_MIN_RECORDS observations (about a reading every 3 hours or better).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass

import yaml

from climate.paths import RAW_DIR, STATIONS_DIR

META = "ghcnh_meta"
BASE = "https://www.ncei.noaa.gov/oa/global-historical-climatology-network/hourly/"
INVENTORY_URL = BASE + "doc/ghcnh-inventory.txt"
STATION_LIST_URL = BASE + "doc/ghcnh-station-list.csv"
DOC_URL = BASE + "doc/ghcnh_DOCUMENTATION.pdf"
FIRST_YEAR = 1940
HOURLY_YEAR_MIN_RECORDS = 2700  # ~3-hourly with >= 92% of the year present
LONG_YEARS = 50


def year_url(station_id: str, year: int) -> str:
    return f"{BASE}access/by-year/{year}/parquet/GHCNh_{station_id}_{year}.parquet"


@dataclass(frozen=True)
class HourlyStation:
    id: str
    name: str
    short: str
    state: str
    lat: float
    lon: float
    elev_m: float
    icao: str
    tz: str
    first_year: int  # first hourly year (>= FIRST_YEAR)
    last_year: int
    hourly_years: int
    active: bool
    long: bool
    hcn: str = ""
    probe_temps: int = 0

    @property
    def years(self) -> range:
        return range(self.first_year, self.last_year + 1)


def _read_inventory() -> dict[str, dict[int, int]]:
    """station -> {year: records}"""
    out: dict[str, dict[int, int]] = {}
    with (RAW_DIR / META / "ghcnh-inventory.txt").open() as f:
        next(f)
        for line in f:
            p = line.split()
            if len(p) < 14 or not p[0].startswith("US"):
                continue
            out.setdefault(p[0], {})[int(p[1])] = sum(int(x) for x in p[2:14])
    return out


def _read_station_list() -> dict[str, dict]:
    with (RAW_DIR / META / "ghcnh-station-list.csv").open(encoding="utf-8", errors="replace") as f:
        return {r["GHCN_ID"]: r for r in csv.DictReader(f) if r["GHCN_ID"].startswith("US")}


PROBE_MIN_TEMPS = 2000  # temperature readings in the probe year to count as a temperature station


def _probe(candidates: list[dict]) -> dict[str, int]:
    """Download one mid-record year per candidate and count hourly temperature readings.
    Hourly precipitation gauges have thousands of rows a year but no temperature."""
    from concurrent.futures import ThreadPoolExecutor

    import polars as pl

    from climate.acquire.base import download, flush_manifests

    def probe(e):
        year = e["_hourly"][len(e["_hourly"]) // 2]
        path = download(
            f"ghcnh_{year}",
            year_url(e["id"], year),
            filename=f"GHCNh_{e['id']}_{year}.parquet",
            throttle_seconds=0.02,
            quiet=True,
        )
        if path is None:
            return e["id"], -1
        try:
            df = pl.read_parquet(path, columns=["temperature"])
            return e["id"], int(
                df["temperature"].cast(pl.Float64, strict=False).is_not_null().sum()
            )
        except Exception:  # noqa: BLE001
            return e["id"], 0

    out = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        for i, (sid, n) in enumerate(pool.map(probe, candidates), 1):
            out[sid] = n
            if i % 500 == 0:
                print(f"  … probed {i}/{len(candidates)}", flush=True)
    flush_manifests()
    return out


def generate(min_years: int = 20) -> str:
    from timezonefinder import TimezoneFinder

    from climate.stations import short_name

    inv = _read_inventory()
    meta = _read_station_list()
    tf = TimezoneFinder()
    entries = []
    for sid, years in inv.items():
        m = meta.get(sid)
        if not m or not m.get("STATE"):
            continue
        hourly = sorted(
            y for y, n in years.items() if y >= FIRST_YEAR and n >= HOURLY_YEAR_MIN_RECORDS
        )
        if len(hourly) < min_years:
            continue
        try:
            lat, lon = float(m["LATITUDE"]), float(m["LONGITUDE"])
        except ValueError:
            continue
        last_any = max(y for y, n in years.items() if n > 0)
        name = " ".join(m["NAME"].split())
        entries.append(
            {
                "_hourly": hourly,
                "id": sid,
                "name": name,
                "short": short_name(name),
                "state": m["STATE"],
                "lat": lat,
                "lon": lon,
                "elev_m": float(m["ELEVATION"] or 0),
                "icao": m.get("ICAO", "") or "",
                "tz": tf.timezone_at(lat=lat, lng=lon) or "UTC",
                "first_year": hourly[0],
                "last_year": hourly[-1],
                "hourly_years": len(hourly),
                "active": last_any >= 2025 and hourly[-1] >= 2024,
                "long": len(hourly) >= LONG_YEARS,
                "hcn": m.get("(US)HCN_(US)CRN", "") or "",
            }
        )
    print(f"  {len(entries)} candidates; probing one year each for hourly temperature …")
    temps = _probe(entries)
    kept = []
    for e in entries:
        n = temps.get(e["id"], 0)
        e["probe_temps"] = n
        e.pop("_hourly")
        if n >= PROBE_MIN_TEMPS:
            kept.append(e)
    print(
        f"  {len(kept)} stations report hourly temperature ({len(entries) - len(kept)} dropped: precipitation-only or empty)"
    )
    entries = kept
    entries.sort(key=lambda e: (e["state"], e["name"]))
    n_long = sum(1 for e in entries if e["long"])
    head = (
        "# Generated by `clim stations --tier hourly` from NOAA's GHCNh inventory: US stations\n"
        f"# with >= {min_years} hourly years since {FIRST_YEAR} (a year counts with >= {HOURLY_YEAR_MIN_RECORDS}\n"
        f"# observations, ~3-hourly or better) that report hourly temperature (verified by probing\n"
        f"# one year per station). {len(entries)} stations; {n_long} have >= {LONG_YEARS} such\n"
        "# years -> `long`, used for the national region. Regenerate rather than edit.\n"
    )
    doc = {
        "tier": "hourly",
        "source": "GHCNh",
        "name": "Hourly observations (GHCNh)",
        "stations": entries,
    }
    return head + yaml.safe_dump(doc, sort_keys=False, width=200)


def write_list(min_years: int = 20) -> int:
    text = generate(min_years)
    (STATIONS_DIR / "hourly.yaml").write_text(text)
    return text.count("\n- id:")


_CACHE: list[HourlyStation] | None = None


def load_hourly_stations(only: list[str] | None = None) -> list[HourlyStation]:
    global _CACHE
    if _CACHE is None:
        p = STATIONS_DIR / "hourly.yaml"
        if not p.exists():
            return []
        doc = yaml.safe_load(p.read_text())
        _CACHE = [HourlyStation(**e) for e in doc["stations"]]
    if only is None:
        return list(_CACHE)
    want = set(only)
    return [s for s in _CACHE if s.id in want or s.icao in want or s.id[-5:] in want]


_BY_ID: dict[str, HourlyStation] | None = None


def hourly_station(station_id: str) -> HourlyStation | None:
    global _BY_ID
    if _BY_ID is None:
        _BY_ID = {s.id: s for s in load_hourly_stations()}
    return _BY_ID.get(station_id)
