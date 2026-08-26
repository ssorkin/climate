"""clim analyze: per-station metrics -> data/analysis/<ID>/ (Parquet + meta.json)."""

from __future__ import annotations

import json
from datetime import date

import numpy as np
import polars as pl

from climate.analysis import homogenized as H
from climate.analysis import metrics as M
from climate.analysis.obs_time import segments
from climate.config import Region, Station, load_analysis_config, load_regions
from climate.ingest.store import load_daily_wide, load_inventory, load_stations
from climate.ingest.ushcn import load_ushcn
from climate.paths import ANALYSIS_DIR

OBS_SEGMENT_MIN_DAYS = 30


def station_meta(st: Station, reg: Region, stations: pl.DataFrame, inv: pl.DataFrame) -> dict:
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
    rec = M.records(daily, cfg)
    annual = annual.join(M.record_counts(rec, annual), on="year", how="left")
    monthly = M.monthly_metrics(daily, cfg, today)
    cold = M.cold_season_metrics(daily, cfg, today)
    decades = M.decade_means(annual, cfg, cold)
    doy = M.doy_climatology(daily, cfg)
    summer = M.summer_to_date(daily, cfg, today)

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

    homog = None
    off = H.offsets(ush, st.id) if ush is not None else None
    if off is not None:
        ann_off = H.annual_offsets(off)
        adj = H.adjusted_counts(daily, off, annual)
        ann_off.join(adj, on="year", how="full", coalesce=True).sort("year").write_parquet(
            out_dir / "homogenized.parquet"
        )
        homog = {"breaks": H.breaks(ann_off), "source": "USHCN v2.5 FLs.52j vs raw"}

    b0, b1 = cfg["baseline"]["start"], cfg["baseline"]["end"]
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


def run_analysis(region: str = "all", today: date | None = None) -> None:
    today = today or M.today_utc()
    cfg = load_analysis_config()
    stations = load_stations()
    inv = load_inventory()
    ush = load_ushcn()
    for reg in load_regions(region):
        print(f"==> region {reg.id}")
        for st in reg.stations:
            meta = analyze_station(st, reg, cfg, stations, inv, today, ush)
            w = meta["windows"]
            b = w.get("baseline", {}).get("hot_95")
            l10 = w.get("last10", {}).get("hot_95")
            print(
                f"  {st.id} {st.short:<20} {meta['first_year']}-{meta['last_date']}  "
                f"complete years {meta['complete_years']:>3}  "
                f"hot95 baseline {b} -> last10 {l10}"
            )
