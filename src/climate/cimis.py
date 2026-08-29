"""CIMIS tier: California's irrigation-management weather stations, as a siting control.

CIMIS (DWR) stations sit over irrigated, mowed grass in open agricultural settings —
the reference-ET standard — so they are the closest thing California has to a
"properly sited" temperature network. They start in 1982, so they can only speak to
the recent decades; the comparison with airports is always made over the same years.

Stages mirror the GHCNh hourly tier: `stations` fetches the inventory into
stations/cimis.yaml; `acquire` pulls hourly air temperature / dew point / RH (and the
daily true max/min as a cross-check) through the CIMIS Web API into data/raw/cimis with
a manifest; `ingest` builds the same hourly Parquet + derived daily store the rest of the
pipeline reads, under ids CIMIS<nbr>; `analyze` runs the heat-wave block.

Conventions (CIMIS documentation): hourly values are hour-ending averages labeled
0100..2400 in Pacific Standard Time year-round; a reading is placed at the middle of its
hour. QC flags: blank = passed, Y = moderately outside historical limits (kept — the
hottest days are exactly that), R far out / S sensor / M missing / I ignore / Q untestable
/ A,E,T historical-average fill / H,N,P dropped.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import httpx
import polars as pl
import yaml

from climate.acquire.base import USER_AGENT, load_manifest, save_manifest
from climate.paths import ANALYSIS_DIR, RAW_DIR, STATIONS_DIR

API = "https://et.water.ca.gov"
STATIONS_URL = f"{API}/ApiWeb/GetAllStations"
DATA_URL = f"{API}/StationWeb/GetDataByStationNumber"
HOURLY_ITEMS = ("hly-air-tmp", "hly-dew-pnt", "hly-rel-hum")
DAILY_ITEMS = ("day-air-tmp-max", "day-air-tmp-min")
HOURLY_CHUNK_DAYS = 209  # the API caps a request at 5,020 hourly records
DAILY_CHUNK_DAYS = 1700  # and 1,750 daily ones
ORIGIN = date(1982, 6, 7)  # the API refuses earlier dates (ERR1011)
GOOD_QC = {" ", "", "Y"}
PST_OFFSET_H = 8
MIN_SPAN_YEARS = 20
DATASET = "cimis"
LIST_PATH = STATIONS_DIR / "cimis.yaml"


def station_id(nbr: int) -> str:
    return f"CIMIS{nbr:03d}"


@dataclass(frozen=True)
class CimisStation:
    nbr: int
    name: str
    county: str
    lat: float
    lon: float
    elev_m: float
    connect: date
    disconnect: date | None  # None while active
    ground_cover: str
    active: bool

    @property
    def id(self) -> str:
        return station_id(self.nbr)

    @property
    def short(self) -> str:
        return f"{self.name} (CIMIS {self.nbr})"

    @property
    def last(self) -> date:
        return self.disconnect or datetime.now(UTC).date()


def api_key() -> str:
    key = os.environ.get("CIMIS_API_KEY") or os.environ.get("CIMIS_APP_KEY")
    if not key:
        env = Path(__file__).resolve().parents[2] / ".env"
        if env.exists():
            for line in env.read_text().splitlines():
                if line.startswith(("CIMIS_API_KEY=", "CIMIS_APP_KEY=")):
                    key = line.split("=", 1)[1].strip().strip("\"'")
    if not key:
        raise SystemExit("CIMIS_API_KEY not set (put it in .env)")
    return key


def _client() -> httpx.Client:
    return httpx.Client(
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Ocp-Apim-Subscription-Key": api_key(),
        },
        timeout=httpx.Timeout(30.0, read=180.0),
    )


# --- station list --------------------------------------------------------------------------


def _parse_date(s: str | None) -> date | None:
    return date.fromisoformat(s[:10]) if s else None


def fetch_inventory() -> list[dict]:
    with _client() as c:
        r = c.get(STATIONS_URL)
        r.raise_for_status()
        return r.json()


def write_station_list(min_span_years: int = MIN_SPAN_YEARS) -> int:
    """stations/cimis.yaml: every station whose record spans min_span_years or more
    (closed ones included; a disconnect date of 2035+ means still running)."""
    rows = []
    today = datetime.now(UTC).date()
    for s in fetch_inventory():
        connect = _parse_date(s["ConnectDate"])
        disconnect = _parse_date(s["DisconnectDate"])
        if disconnect is None or disconnect > today:
            disconnect = None
        if connect is None or (disconnect or today).year - connect.year < min_span_years:
            continue
        rows.append(
            {
                "nbr": int(s["StationNbr"]),
                "name": s["StationName"].strip(),
                "county": s["County"],
                "lat": round(float(s["Latitude"]), 4),
                "lon": round(float(s["Longitude"]), 4),
                "elev_m": round(float(s["Elevation"]) * 0.3048, 1),  # CIMIS lists feet
                "connect": connect.isoformat(),
                "disconnect": disconnect.isoformat() if disconnect else None,
                "ground_cover": s.get("GroundCoverName") or "",
                "active": bool(s.get("Status")),
            }
        )
    rows.sort(key=lambda r: r["nbr"])
    lines = [
        "# Generated by `clim cimis stations`: every CIMIS station whose record spans",
        f"# {min_span_years}+ years (closed ones included). Ids are CIMIS<nbr>; this is a data",
        "# tier, not a region — CIMIS stations never enter stations/<region>.yaml.",
        "tier: cimis",
        f"source: {STATIONS_URL}",
        f"generated: {today.isoformat()}",
        "stations:",
    ]
    for r in rows:
        vals = ", ".join(
            f"{k}: {json.dumps(v) if isinstance(v, str) or v is None else v}" for k, v in r.items()
        )
        lines.append(f"  - {{{vals}}}")
    LIST_PATH.write_text("\n".join(lines) + "\n")
    return len(rows)


def load_cimis_stations(only: list[str] | None = None) -> list[CimisStation]:
    raw = yaml.safe_load(LIST_PATH.read_text())
    out = []
    for s in raw["stations"]:
        st = CimisStation(
            nbr=int(s["nbr"]),
            name=s["name"],
            county=s["county"],
            lat=float(s["lat"]),
            lon=float(s["lon"]),
            elev_m=float(s["elev_m"]),
            connect=date.fromisoformat(s["connect"]),
            disconnect=date.fromisoformat(s["disconnect"]) if s.get("disconnect") else None,
            ground_cover=s.get("ground_cover", ""),
            active=bool(s.get("active")),
        )
        if only and st.id not in only and str(st.nbr) not in only:
            continue
        out.append(st)
    return out


# --- acquire -------------------------------------------------------------------------------


def chunks(start: date, end: date, days: int) -> list[tuple[date, date]]:
    out, s = [], start
    while s <= end:
        e = min(s + timedelta(days=days - 1), end)
        out.append((s, e))
        s = e + timedelta(days=1)
    return out


def raw_path(st: CimisStation, scope: str, s: date, e: date) -> Path:
    return RAW_DIR / DATASET / st.id / f"{scope}_{s.isoformat()}_{e.isoformat()}.json.gz"


def _request_url(st: CimisStation, scope: str, s: date, e: date) -> str:
    items = HOURLY_ITEMS if scope == "hourly" else DAILY_ITEMS
    return (
        f"{DATA_URL}?stationNbrs={st.nbr}&startDate={s.isoformat()}&endDate={e.isoformat()}"
        f"&isHourly={'true' if scope == 'hourly' else 'false'}&unitOfMeasure=M"
        f"&dataItems={','.join(items)}"
    )


def _fetch_chunk(c: httpx.Client, st: CimisStation, scope: str, s: date, e: date) -> str | None:
    """One API page as text, or None after retries."""
    url = _request_url(st, scope, s, e)
    for attempt in range(4):
        try:
            r = c.get(url)
            if r.status_code == 200:
                body = r.text
                if body.startswith("<"):  # the WAF's HTML page, not an API answer
                    raise httpx.HTTPError("request rejected by the WAF")
                json.loads(body)
                return body
            if r.status_code == 400:
                print(f"  {st.id} {scope} {s}..{e}: {r.text[:160]}", flush=True)
                return None
            r.raise_for_status()
        except (httpx.HTTPError, ValueError) as exc:
            if attempt == 3:
                print(f"  FAILED {st.id} {scope} {s}..{e}: {exc!r}", flush=True)
                return None
            time.sleep(3 * (attempt + 1))
    return None


def run_acquire(only: list[str] | None = None, refresh: bool = False, workers: int = 4) -> None:
    stations = load_cimis_stations(only)
    today = datetime.now(UTC).date()
    jobs: list[tuple[CimisStation, str, date, date]] = []
    for st in stations:
        end = min(st.last, today)
        for scope, n in (("hourly", HOURLY_CHUNK_DAYS), ("daily", DAILY_CHUNK_DAYS)):
            jobs.extend((st, scope, s, e) for s, e in chunks(max(st.connect, ORIGIN), end, n))
    manifest = load_manifest(DATASET)
    todo = []
    for job in jobs:
        st, scope, s, e = job
        p = raw_path(st, scope, s, e)
        key = f"{st.id}/{p.name}"
        fresh = key in manifest and p.exists() and p.stat().st_size == manifest[key]["size"]
        # the chunk that contains today's date keeps growing; --refresh re-fetches it
        if fresh and not (refresh and e >= today - timedelta(days=1)):
            continue
        todo.append(job)
    print(f"==> CIMIS: {len(stations)} stations, {len(jobs)} chunks, {len(todo)} to fetch")
    n_ok = 0

    def work(job):
        st, scope, s, e = job
        with _client() as c:
            body = _fetch_chunk(c, st, scope, s, e)
        if body is None:
            return None
        p = raw_path(st, scope, s, e)
        p.parent.mkdir(parents=True, exist_ok=True)
        data = gzip.compress(body.encode())
        p.write_bytes(data)
        return (
            f"{st.id}/{p.name}",
            {
                "dataset": DATASET,
                "filename": f"{st.id}/{p.name}",
                "url": _request_url(st, scope, s, e),
                "sha256": hashlib.sha256(data).hexdigest(),
                "size": len(data),
                "downloaded_at": datetime.now(UTC).isoformat(timespec="seconds"),
                "last_modified": "",
                "note": "key sent as Ocp-Apim-Subscription-Key; gzip of the JSON body",
            },
        )

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for i, res in enumerate(pool.map(work, todo), 1):
            if res:
                manifest[res[0]] = res[1]
                n_ok += 1
            if i % 200 == 0:
                save_manifest(DATASET, manifest)
                print(f"  … {i}/{len(todo)}", flush=True)
    save_manifest(DATASET, manifest)
    print(f"  done; {n_ok} chunks fetched, {len(todo) - n_ok} failed")


# --- ingest --------------------------------------------------------------------------------


def _records(path: Path) -> list[dict]:
    d = json.loads(gzip.decompress(path.read_bytes()))
    provs = d.get("Data", {}).get("Providers") or []
    return provs[0].get("Records") or [] if provs else []


def _val(rec: dict, key: str, scale: float = 10.0) -> int | None:
    v = rec.get(key)
    if not v or v.get("Qc") not in GOOD_QC or v.get("Value") in (None, ""):
        return None
    try:
        return round(float(v["Value"]) * scale)
    except ValueError:
        return None


def parse_hourly(records: list[dict]) -> pl.DataFrame:
    """Hourly rows in the GHCNh Parquet layout: ts_utc, date, hour, h, temp, dewp, rh,
    wetbulb. Hour-ending label HHMM → reading at HH-0.5 local (PST); 2400 stays on its
    own date at 23.5."""
    rows = []
    for r in records:
        try:
            d = date.fromisoformat(r["Date"])
            hh = int(r["Hour"][:2])
        except (KeyError, ValueError):
            continue
        rows.append(
            {
                "date": d,
                "h": hh - 0.5,
                "hour": hh - 1,
                "temp": _val(r, "HlyAirTmp"),
                "dewp": _val(r, "HlyDewPnt"),
                "rh": _val(r, "HlyRelHum", 1.0),
            }
        )
    df = pl.DataFrame(
        rows,
        schema={
            "date": pl.Date,
            "h": pl.Float64,
            "hour": pl.Int8,
            "temp": pl.Int32,
            "dewp": pl.Int32,
            "rh": pl.Int16,
        },
    )
    if df.is_empty():
        return df
    local = pl.col("date").cast(pl.Datetime("us")) + pl.duration(
        minutes=(pl.col("h") * 60).cast(pl.Int64)
    )
    return (
        df.with_columns(
            (local + pl.duration(hours=PST_OFFSET_H)).dt.replace_time_zone("UTC").alias("ts_utc"),
            pl.lit(None, dtype=pl.Int32).alias("wetbulb"),
        )
        .unique(subset=["ts_utc"], keep="last")
        .sort("ts_utc")
    )


def parse_daily(records: list[dict]) -> pl.DataFrame:
    """CIMIS's own daily max/min (true extremes from 1-minute samples), tenths °C."""
    rows = [
        {
            "date": date.fromisoformat(r["Date"]),
            "tmax_true": _val(r, "DayAirTmpMax"),
            "tmin_true": _val(r, "DayAirTmpMin"),
        }
        for r in records
        if r.get("Date")
    ]
    return pl.DataFrame(
        rows, schema={"date": pl.Date, "tmax_true": pl.Int32, "tmin_true": pl.Int32}
    ).sort("date")


def ingest_station(st: CimisStation) -> str:
    from climate.hourly.ingest import derive_days, hourly_path

    d = RAW_DIR / DATASET / st.id
    hourly_files = sorted(d.glob("hourly_*.json.gz"))
    if not hourly_files:
        return f"  {st.id} {st.short}: no files"
    frames = [parse_hourly(_records(p)) for p in hourly_files]
    frames = [f for f in frames if not f.is_empty()]
    if not frames:
        return f"  {st.id} {st.short}: no records"
    df = pl.concat(frames).unique(subset=["ts_utc"], keep="last").sort("ts_utc")
    out = hourly_path(st.id)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.select("ts_utc", "date", "hour", "temp", "dewp", "rh", "wetbulb").write_parquet(out)
    day, good = derive_days(df.select("date", "h", "temp"), st.id)
    daily_files = sorted(d.glob("daily_*.json.gz"))
    if daily_files:
        true = pl.concat([parse_daily(_records(p)) for p in daily_files]).unique(
            subset=["date"], keep="last"
        )
        true.sort("date").write_parquet(out.parent / "daily_true.parquet")
    return (
        f"  {st.id} {st.short:<34} {df.height:>9,} obs  {df['date'].min()} .. {df['date'].max()}"
        f"  complete days {good.height:>6,} of {day.height:,}"
    )


def run_ingest(only: list[str] | None = None) -> None:
    stations = load_cimis_stations(only)
    print(f"==> ingesting {len(stations)} CIMIS stations (hourly + derived daily)")
    for st in stations:
        print(ingest_station(st), flush=True)


# --- analyze -------------------------------------------------------------------------------


def analyze_station(st: CimisStation, cfg: dict) -> dict | None:
    """The heat-wave block for one CIMIS station, in the same shape the GHCNh runner
    writes (heatwaves.parquet + meta.json under data/analysis/<id>/), plus per-year
    warm-season means so wave nights can be set against ordinary nights."""
    from climate.analysis import metrics as M
    from climate.hourly.ingest import hourly_path
    from climate.ingest.store import daily_path, load_daily_wide

    if not daily_path(st.id).exists():
        return None
    daily = load_daily_wide(st.id)
    if daily.height < 300:
        return None
    hw_years = M.warm_season_years(daily, cfg)
    thr = M.heat_wave_threshold(daily, cfg, hw_years)
    out_dir = ANALYSIS_DIR / st.id
    out_dir.mkdir(parents=True, exist_ok=True)
    heat_waves = None
    if thr is not None:
        waves = M.heat_waves(daily, cfg, thr)
        hourly = pl.read_parquet(hourly_path(st.id), columns=["date", "hour", "temp"])
        waves = waves.with_columns(M.heat_wave_relief(hourly, waves, cfg["heat_waves"]["relief_f"]))
        waves = M.heat_wave_anomalies(daily, waves, cfg, hw_years)
        waves.write_parquet(out_dir / "heatwaves.parquet")
        last = hw_years[-1]
        k = cfg["heat_waves"]["window_min_years"]
        windows = {
            "baseline": None,  # no 1951–80 record: CIMIS starts in 1982
            "last30": M.heat_wave_window(waves, daily, cfg, hw_years, last - 29, last),
            "first15": M.heat_wave_window(
                waves, daily, cfg, hw_years, hw_years[0], hw_years[min(k, len(hw_years)) - 1]
            ),
            "last15": M.heat_wave_window(
                waves, daily, cfg, hw_years, hw_years[max(0, len(hw_years) - k)], last
            ),
        }
        heat_waves = {
            "threshold_f": thr,
            "years": hw_years,
            "n_waves": int(waves.filter(pl.col("year").is_in(hw_years)).height),
            "windows": windows,
        }
    # warm-season means per year (both elements), for the ordinary-night comparison
    months = cfg["heat_waves"]["months"]
    season = (
        daily.with_columns(
            pl.col("date").dt.year().alias("year"), pl.col("date").dt.month().alias("month")
        )
        .filter(pl.col("month").is_in(months))
        .group_by("year")
        .agg(
            (pl.col("tmax").mean() / 10).alias("tmax_mean_c"),
            (pl.col("tmin").mean() / 10).alias("tmin_mean_c"),
            pl.col("tmax").is_not_null().sum().alias("n_days"),
        )
        .sort("year")
    )
    season.write_parquet(out_dir / "warm_season.parquet")
    valid = daily.filter(pl.col("tmax").is_not_null())
    meta = {
        "id": st.id,
        "short": st.short,
        "name": st.name,
        "network": "CIMIS",
        "county": st.county,
        "lat": st.lat,
        "lon": st.lon,
        "elev_m": st.elev_m,
        "ground_cover": st.ground_cover,
        "active": st.active,
        "connect": st.connect.isoformat(),
        "disconnect": st.disconnect.isoformat() if st.disconnect else None,
        "first_date": str(valid["date"].min()),
        "last_date": str(valid["date"].max()),
        "first_year": int(valid["date"].min().year),
        "last_year": int(valid["date"].max().year),
        "complete_warm_seasons": len(hw_years),
        "heat_waves": heat_waves,
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=1))
    return meta


def run_analyze(only: list[str] | None = None) -> None:
    from climate.config import load_analysis_config

    cfg = load_analysis_config()
    stations = load_cimis_stations(only)
    print(f"==> analyzing {len(stations)} CIMIS stations")
    for st in stations:
        try:
            meta = analyze_station(st, cfg)
        except Exception as exc:  # noqa: BLE001 — one station must not sink the run
            print(f"  FAILED {st.id} {st.short}: {exc!r}", flush=True)
            continue
        if meta is None:
            print(f"  {st.id} {st.short}: not ingested / too short", flush=True)
            continue
        hw = meta["heat_waves"]
        print(
            f"  {st.id} {st.short:<34} {meta['first_year']}-{meta['last_year']}  "
            f"warm seasons {meta['complete_warm_seasons']:>2}  "
            + (f"thr {hw['threshold_f']}°F waves {hw['n_waves']}" if hw else "no threshold"),
            flush=True,
        )


def run_stage(stage: str, only: list[str] | None = None, refresh: bool = False) -> None:
    only = only or None
    if stage == "stations":
        print(f"  wrote stations/cimis.yaml with {write_station_list()} stations")
    elif stage == "acquire":
        run_acquire(only=only, refresh=refresh)
    elif stage == "ingest":
        run_ingest(only=only)
    elif stage == "analyze":
        run_analyze(only=only)
    else:
        raise SystemExit(f"unknown stage {stage!r}")
