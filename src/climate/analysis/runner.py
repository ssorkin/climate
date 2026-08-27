"""clim analyze: per-station metrics -> data/analysis/<ID>/ (Parquet + meta.json)."""

from __future__ import annotations

import json
from concurrent.futures import ProcessPoolExecutor
from datetime import date

import numpy as np
import polars as pl

from climate.analysis import homogenized as H
from climate.analysis import metrics as M
from climate.analysis.obs_time import segments
from climate.config import (
    Region,
    Station,
    load_analysis_config,
    load_regions,
    region_ids_for,
    unique_stations,
)
from climate.ingest.store import load_daily_wide, load_inventory, load_stations
from climate.ingest.ushcn import load_ushcn
from climate.paths import ANALYSIS_DIR

OBS_SEGMENT_MIN_DAYS = 30
_REGIONS: list[Region] = []
_CTX: dict = {}


def _score(indices: pl.DataFrame) -> dict | None:
    """The station's score: mean percentile rank over its last ten complete years, taken from
    the last fifteen calendar years (at least five of them complete), for highs and lows
    separately, with the span those years cover. Anchored to complete years so a station with
    a few recent gaps still gets one; a station that has mostly gone dark does not."""
    out = {}
    last = int(indices["year"].max())
    for el in ("tmax", "tmin"):
        rows = (
            indices.filter(pl.col(f"rank_{el}").is_not_null() & (pl.col("year") > last - 15))
            .sort("year")
            .tail(10)
        )
        if rows.height < 5:  # fewer than five complete years in the last fifteen: no score
            return None
        out[el] = round(float(rows[f"rank_{el}"].mean()), 1)
        out[f"{el}_span"] = [int(rows["year"].min()), int(rows["year"].max())]
    return out


def _curated(sid: str) -> tuple[Region, Station] | None:
    for reg in _REGIONS:
        if getattr(reg, "generated", False):
            continue
        for st in reg.stations:
            if st.id == sid:
                return reg, st
    return None


def _curated_short(sid: str, default: str) -> str:
    """A curated region's short name wins over a generated list's, whichever region is run."""
    c = _curated(sid)
    return c[1].short if c else default


def _home_region(sid: str, default: str) -> str:
    """A station's home region is the curated one it belongs to, whichever region is run —
    otherwise a national run would relabel every LA station 'us' and the LA export lose it."""
    c = _curated(sid)
    return c[0].id if c else default


def station_meta(st: Station, reg: Region, stations: pl.DataFrame, inv: pl.DataFrame) -> dict:
    from climate.ghcnh import hourly_station

    hs = hourly_station(st.id)
    if hs is not None:
        return {
            "id": st.id,
            "short": _curated_short(st.id, st.short),
            "name": hs.name.title().replace("Airport", "Airport").replace("Afb", "AFB"),
            "noaa_name": hs.name,
            "region": _home_region(st.id, reg.id),
            "regions": region_ids_for(_REGIONS, st.id),
            "state": hs.state,
            "lat": hs.lat,
            "lon": hs.lon,
            "elev_m": hs.elev_m,
            "kind": "airport" if st.id[2] == "W" else "hourly",
            "source": "ghcnh",
            "icao": hs.icao,
            "tz": hs.tz,
            "ushcn": hs.hcn == "HCN",
            "inventory": {
                "TMAX": [hs.first_year, hs.last_year],
                "TMIN": [hs.first_year, hs.last_year],
            },
            "notable": list(st.notable),
        }
    row = stations.filter(pl.col("id") == st.id)
    if row.is_empty():
        raise SystemExit(f"analyze: {st.id} not in ghcnd-stations.txt")
    r = row.row(0, named=True)
    years = {
        e["element"]: (e["first_year"], e["last_year"])
        for e in inv.filter(pl.col("id") == st.id).iter_rows(named=True)
    }
    return {
        "id": st.id,
        "short": st.short,
        "name": r["name"].title().replace(" Ap", " Airport").replace("Ucla", "UCLA"),
        "noaa_name": r["name"],
        "region": reg.id,
        "regions": region_ids_for(_REGIONS, st.id),
        "state": r["state"],
        "lat": r["lat"],
        "lon": r["lon"],
        "elev_m": r["elev_m"],
        "kind": "airport" if st.id.startswith("USW") else "coop",
        "ushcn": st.ushcn or r["hcn_crn"] == "HCN",
        "inventory": {k: list(v) for k, v in years.items() if k in ("TMAX", "TMIN", "PRCP")},
        "notable": list(st.notable),
    }


def analyze_station(
    st: Station, reg: Region, cfg: dict, stations, inv, today: date, ush=None
) -> dict:
    out_dir = ANALYSIS_DIR / st.id
    out_dir.mkdir(parents=True, exist_ok=True)
    daily = load_daily_wide(st.id)
    annual = M.annual_metrics(daily, cfg, today)
    suspect_years = M.outlier_years(annual)
    annual = M.drop_years(annual, set(suspect_years))
    rec = M.records(daily, cfg)
    annual = annual.join(M.record_counts(rec, annual), on="year", how="left")
    monthly = M.drop_years(M.monthly_metrics(daily, cfg, today), set(suspect_years))
    cold = M.cold_season_metrics(daily, cfg, today)
    decades = M.decade_means(annual, cfg, cold)
    summer = M.summer_to_date(daily, cfg, today)
    b0, b1 = cfg["baseline"]["start"], cfg["baseline"]["end"]

    def n_complete(y0: int, y1: int) -> int:
        return annual.filter(
            (pl.col("year") >= y0)
            & (pl.col("year") <= y1)
            & pl.col("complete_tmax")
            & pl.col("complete_tmin")
        ).height

    base_years = n_complete(b0, b1)
    has_baseline = base_years >= 20  # the fixed 1951–1980 base every cross-station figure uses
    # A station without that record is scored against its own earliest complete years, clearly
    # marked, so it still gets ranks, bands and a score — never averaged with fixed-base stations.
    baseline_used: tuple[int, int] | None = (b0, b1) if has_baseline else None
    baseline_fallback = False
    if not has_baseline:
        comp = annual.filter(pl.col("complete_tmax") & pl.col("complete_tmin"))["year"].to_list()
        # its earliest 20 complete years (a gappy record may spread them over more than 30
        # calendar years), provided ten or more years follow them to be scored
        if len(comp) >= 20 and comp[-1] >= comp[19] + 10:
            baseline_used, baseline_fallback = (comp[0], comp[19]), True
    scored = baseline_used is not None
    doy = M.doy_climatology(daily, cfg, baseline_used)
    ranks = M.percentile_ranks(daily, cfg, baseline_used) if scored else None
    indices = M.percentile_indices(daily, doy, annual, cfg, ranks)
    if not scored:  # percentile indices need a base period; trends in means do not
        indices = indices.with_columns(
            pl.lit(None, dtype=pl.Float64).alias(c) for c in ("tx90p", "tn90p", "tx10p", "tn10p")
        )

    annual.write_parquet(out_dir / "annual.parquet")
    monthly.write_parquet(out_dir / "monthly.parquet")
    cold.write_parquet(out_dir / "cold_season.parquet")
    decades.write_parquet(out_dir / "decades.parquet")
    doy.write_parquet(out_dir / "doy.parquet")
    flag_cols = [c for c in rec.columns if c.startswith("record_")]
    rec.filter(pl.any_horizontal([pl.col(c) for c in flag_cols])).write_parquet(
        out_dir / "records.parquet"
    )
    summer["table"].write_parquet(out_dir / "summer.parquet")
    indices.write_parquet(out_dir / "indices.parquet")
    if ranks is not None:
        ranks.write_parquet(out_dir / "ranks.parquet")

    homog = None
    off = H.offsets(ush, st.id) if ush is not None else None
    if off is not None:
        ann_off = H.annual_offsets(off)
        adj = H.adjusted_counts(daily, off, annual)
        ann_off.join(adj, on="year", how="full", coalesce=True).sort("year").write_parquet(
            out_dir / "homogenized.parquet"
        )
        homog = {"breaks": H.breaks(ann_off), "source": "USHCN v2.5 FLs.52j vs raw"}

    complete_years = annual.filter(pl.col("complete_tmax") & pl.col("complete_tmin"))["year"]
    last_complete = int(complete_years.max()) if len(complete_years) else None
    cols = M.threshold_columns(cfg)
    metric_cols = [
        "tmax_mean_c",
        "tmin_mean_c",
        *cols["hot_days"],
        *cols["warm_nights"],
        *cols["cold_days"],
        *cols["cold_nights"],
    ]
    windows = {}
    if last_complete:
        windows = {
            "baseline": M.window_means(annual, metric_cols, b0, b1),
            "last30": M.window_means(annual, metric_cols, last_complete - 29, last_complete),
            "last10": M.window_means(annual, metric_cols, last_complete - 9, last_complete),
        }
        cold_cols = cols["cold_nights"]
        cold_named = cold.rename({"season": "year"})
        for key, (y0, y1) in {
            "baseline": (b0, b1),
            "last30": (last_complete - 29, last_complete),
            "last10": (last_complete - 9, last_complete),
        }.items():
            w = M.window_means(cold_named, cold_cols, y0, y1)
            windows[key]["season"] = {k: w[k] for k in w if k != "years"}

    trends = {}
    yrs = annual["year"].to_numpy()
    since = annual.filter(pl.col("year") >= b0)
    yrs = since["year"].to_numpy()
    for c in ["tmax_mean_c", "tmin_mean_c", "hot_95", "warm_70", "hot_100", "coldnight_40"]:
        if c in since.columns:
            t = M.trend(yrs, since[c].cast(pl.Float64).fill_null(np.nan).to_numpy())
            if t:
                trends[c] = t
    if True:
        since_i = indices.filter(pl.col("year") >= b0)
        yrs_i = since_i["year"].to_numpy()
        for c in (
            "tx90p",
            "tn90p",
            "tx10p",
            "tn10p",
            "dtr_c",
            "jja_tmax_c",
            "jja_tmin_c",
            "rank_tmax",
            "rank_tmin",
        ):
            t = M.trend(
                yrs_i, since_i[c].cast(pl.Float64).fill_null(np.nan).to_numpy(), min_nonzero=1
            )
            if t:
                trends[c] = t
    cn = cold.filter(pl.col("season") >= b0)
    t = M.trend(
        cn["season"].to_numpy(), cn["coldnight_32"].cast(pl.Float64).fill_null(np.nan).to_numpy()
    )
    if t:
        trends["frost_nights"] = t

    valid = daily.filter(pl.col("tmax").is_not_null() | pl.col("tmin").is_not_null())
    obs = segments(daily, min_days=OBS_SEGMENT_MIN_DAYS)
    last_valid = valid["date"].max()
    active = (today - last_valid).days <= 400
    meta = {
        **station_meta(st, reg, stations, inv),
        "first_date": str(valid["date"].min()),
        "last_date": str(valid["date"].max()),
        "first_year": int(valid["date"].min().year),
        "last_year": int(valid["date"].max().year),
        "active": bool(active),
        "homogenized": homog,
        "has_baseline": bool(has_baseline),
        "baseline_years": int(base_years),
        "baseline": list(baseline_used) if baseline_used else None,
        "baseline_fallback": bool(baseline_fallback),
        "score": _score(indices) if scored else None,
        "index_windows": (
            {
                key: M.window_means(
                    indices,
                    [
                        "tx90p",
                        "tn90p",
                        "tx10p",
                        "tn10p",
                        "dtr_c",
                        "jja_tmax_c",
                        "jja_tmin_c",
                        "rank_tmax",
                        "rank_tmin",
                    ],
                    y0,
                    y1,
                )
                for key, (y0, y1) in {
                    "baseline": baseline_used or (b0, b1),
                    "last30": (last_complete - 29, last_complete),
                    "last10": (last_complete - 9, last_complete),
                }.items()
            }
            if last_complete
            else {}
        ),
        "suspect_years": {str(y): msg for y, msg in sorted(suspect_years.items())},
        "last_complete_year": last_complete,
        "complete_years": len(complete_years),
        "obs_time": [
            {"from": str(s["from"]), "to": str(s["to"]), "hhmm": s["hhmm"], "days": s["days"]}
            for s in obs
        ],
        "obs_hhmm_now": obs[-1]["hhmm"] if obs else "",
        "windows": windows,
        "trends": trends,
        "summer_to_date": {
            k: (str(v) if isinstance(v, date) else v) for k, v in summer.items() if k != "table"
        },
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=1))
    return meta


def _analyze_one(args: tuple[str, str]) -> str:
    region_id, sid = args
    reg = next(r for r in _CTX["regions"] if r.id == region_id)
    st = next(x for x in reg.stations if x.id == sid)
    from climate.ingest.store import daily_path

    if not daily_path(sid).exists():
        return f"  SKIPPED {sid} {st.short}: not ingested"
    import polars as _pl

    if _pl.read_parquet(daily_path(sid)).height < 2 * 300:
        return f"  SKIPPED {sid} {st.short}: fewer than 300 complete days"
    try:
        meta = analyze_station(
            st, reg, _CTX["cfg"], _CTX["stations"], _CTX["inv"], _CTX["today"], _CTX["ush"]
        )
    except Exception as exc:  # noqa: BLE001 — one bad station must not sink the run
        return f"  FAILED {sid} {st.short}: {exc!r}"
    w = meta["windows"]
    b = w.get("baseline", {}).get("hot_95")
    l10 = w.get("last10", {}).get("hot_95")
    return (
        f"  {sid} {st.short:<20} {meta['first_year']}-{meta['last_date']}  "
        f"complete years {meta['complete_years']:>3}  hot95 baseline {b} -> last10 {l10}"
    )


def _init(ctx: dict) -> None:
    global _REGIONS
    _CTX.update(ctx)
    _REGIONS = ctx["regions"]


def run_analysis(region: str = "all", today: date | None = None) -> None:
    global _REGIONS
    today = today or M.today_utc()
    regions = load_regions(region)
    _REGIONS = load_regions()  # membership is judged against every region
    ctx = {
        "regions": _REGIONS,
        "cfg": load_analysis_config(),
        "stations": load_stations(),
        "inv": load_inventory(),
        "today": today,
        "ush": load_ushcn(),
    }
    todo = [(reg.id, st.id) for reg, st in unique_stations(regions)]
    print(f"==> analyzing {len(todo)} stations")
    failed = skipped = 0
    with ProcessPoolExecutor(initializer=_init, initargs=(ctx,)) as pool:
        for i, line in enumerate(pool.map(_analyze_one, todo, chunksize=4), 1):
            if "SKIPPED" in line:
                skipped += 1
            elif "FAILED" in line:
                failed += 1
                print(line)
            elif len(todo) <= 40:
                print(line)
            elif i % 500 == 0:
                print(f"  … {i}/{len(todo)}")
    if skipped:
        print(f"  {skipped} station(s) not ingested yet — skipped")
    if failed:
        print(f"  {failed} station(s) failed")

    from climate.analysis.regional import run_regional
    from climate.ghcnh import hourly_station
    from climate.hourly.analyze import run_analyze as run_analyze_hourly

    hourly_ids = [sid for _r, sid in todo if hourly_station(sid) is not None]
    if hourly_ids:
        run_analyze_hourly(only=hourly_ids)

    cfg = load_analysis_config()

    for reg in regions:
        if reg.generated:
            continue
        last_complete = max(
            (
                json.loads((ANALYSIS_DIR / st.id / "meta.json").read_text()).get(
                    "last_complete_year"
                )
                or 0
            )
            for st in reg.stations
            if (ANALYSIS_DIR / st.id / "meta.json").exists()
        )
        res = run_regional(
            reg, ANALYSIS_DIR, last_complete, int(cfg.get("regional_display_from", 1930))
        )
        out = ANALYSIS_DIR / "regional" / f"{reg.id}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(res))
        print(
            f"  regional model for {reg.id}: {', '.join(res['metrics'])} (through {last_complete})"
        )
