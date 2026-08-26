"""clim export: data/analysis/<ID>/ -> site/static/data/ JSON.

Contract (see plan): index.json, stations/<ID>/summary.json, stations/<ID>/daily.json.
Temperatures are native tenths-°C ints in daily.json and °C floats in summaries;
threshold keys are whole °F. The site converts for display.
"""

from __future__ import annotations

import json
from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, date, datetime

import numpy as np
import polars as pl

from climate.acquire.base import load_manifest
from climate.acquire.ghcnd import meta_dataset, region_dataset, station_url
from climate.analysis import metrics as M
from climate.config import load_analysis_config, load_regions, unique_stations
from climate.ingest.store import load_daily_wide, load_stations
from climate.paths import ANALYSIS_DIR, RAW_DIR, SITE_DATA_DIR


def _clean(v):
    if v is None:
        return None
    if isinstance(v, float):
        return round(v, 2)
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    return v


def col(df: pl.DataFrame, name: str) -> list:
    return [_clean(v) for v in df[name].to_list()]


def dump(path, obj) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, separators=(",", ":"), allow_nan=False)
    path.write_text(text)
    return len(text)


def _family_block(df: pl.DataFrame, cfg: dict, prefix: str = "") -> dict:
    """Threshold counts by family, plus `<family>_lb`: the count over observed days
    (equal to the count for complete periods; a lower bound for incomplete ones)."""
    t = cfg["thresholds_f"]
    names = {
        "hot_days": "hot",
        "warm_nights": "warm",
        "cold_days": "coldday",
        "cold_nights": "coldnight",
    }
    out = {}
    for family, stem in names.items():
        block, lb, risk, exp = {}, {}, {}, {}
        for thr in t[family]:
            c = f"{prefix}{stem}_{thr}"
            if c in df.columns:
                block[str(thr)] = col(df, c)
            if f"{c}_lb" in df.columns:
                lb[str(thr)] = col(df, f"{c}_lb")
            if f"{c}_risk" in df.columns:
                risk[str(thr)] = col(df, f"{c}_risk")
            if f"{c}_exp" in df.columns:
                exp[str(thr)] = col(df, f"{c}_exp")
        if block:
            out[family] = block
        if lb:
            out[f"{family}_lb"] = lb
        if risk:
            out[f"{family}_risk"] = risk
        if exp:
            out[f"{family}_exp"] = exp
    return out


def ghcnd_version() -> str:
    p = RAW_DIR / meta_dataset() / "ghcnd-version.txt"
    if not p.exists():
        return ""
    text = p.read_text()
    marker = "GHCN Daily is "
    i = text.find(marker)
    return text[i + len(marker) :].split()[0] if i >= 0 else ""


def export_station(sid: str, cfg: dict, region_id: str) -> tuple[dict, int, dict]:
    d = ANALYSIS_DIR / sid
    meta = json.loads((d / "meta.json").read_text())
    annual = pl.read_parquet(d / "annual.parquet")
    monthly = pl.read_parquet(d / "monthly.parquet")
    cold = pl.read_parquet(d / "cold_season.parquet")
    decades = pl.read_parquet(d / "decades.parquet")
    doy = pl.read_parquet(d / "doy.parquet")
    records = pl.read_parquet(d / "records.parquet")
    summer = pl.read_parquet(d / "summer.parquet")
    manifest = load_manifest(region_dataset(region_id)).get(f"{sid}.csv.gz", {})

    b0, b1 = cfg["baseline"]["start"], cfg["baseline"]["end"]
    base = annual.filter((pl.col("year") >= b0) & (pl.col("year") <= b1))
    base_tmax = base["tmax_mean_c"].mean()
    base_tmin = base["tmin_mean_c"].mean()
    annual = annual.with_columns(
        (pl.col("tmax_mean_c") - base_tmax).alias("tmax_anom_c"),
        (pl.col("tmin_mean_c") - base_tmin).alias("tmin_anom_c"),
    )

    homog = None
    if meta.get("homogenized") and (d / "homogenized.parquet").exists():
        h = pl.read_parquet(d / "homogenized.parquet")
        homog = {
            **meta["homogenized"],
            "year": col(h, "year"),
            "tmax_offset_c": col(h, "tmax_off"),
            "tmin_offset_c": col(h, "tmin_off"),
            "hot_95_adj": col(h, "hot_95_adj"),
            "warm_70_adj": col(h, "warm_70_adj"),
        }
        hw = {}
        last = meta.get("last_complete_year")
        if last:
            for key, (y0, y1) in {
                "baseline": (b0, b1),
                "last10": (last - 9, last),
            }.items():
                sub = h.filter((pl.col("year") >= y0) & (pl.col("year") <= y1))
                hw[key] = {
                    "years": [y0, y1],
                    "hot_95_adj": _clean(sub["hot_95_adj"].mean()),
                    "warm_70_adj": _clean(sub["warm_70_adj"].mean()),
                }
        homog["windows"] = hw

    summary = {
        **{k: v for k, v in meta.items() if k not in ("inventory", "homogenized")},
        "homogenized": homog,
        "baseline": cfg["baseline"],
        "thresholds_f": cfg["thresholds_f"],
        "completeness": cfg["completeness"],
        "source_url": station_url(sid),
        "manifest": {
            k: manifest.get(k) for k in ("sha256", "size", "downloaded_at", "last_modified")
        },
        "baseline_means": {"tmax_mean_c": _clean(base_tmax), "tmin_mean_c": _clean(base_tmin)},
        "annual": {
            "year": col(annual, "year"),
            "complete_tmax": col(annual, "complete_tmax"),
            "complete_tmin": col(annual, "complete_tmin"),
            "partial": col(annual, "partial"),
            "days_valid_tmax": col(annual, "days_valid_tmax"),
            "days_valid_tmin": col(annual, "days_valid_tmin"),
            "tmax_mean_c": col(annual, "tmax_mean_c"),
            "tmin_mean_c": col(annual, "tmin_mean_c"),
            "tmax_anom_c": col(annual, "tmax_anom_c"),
            "tmin_anom_c": col(annual, "tmin_anom_c"),
            **_family_block(annual, cfg),
            "hottest_tenths": col(annual, "hottest_tenths"),
            "hottest_date": col(annual, "hottest_date"),
            "warmest_night_tenths": col(annual, "warmest_night_tenths"),
            "warmest_night_date": col(annual, "warmest_night_date"),
            "coldest_tenths": col(annual, "coldest_tenths"),
            "coldest_date": col(annual, "coldest_date"),
            "coldest_night_tenths": col(annual, "coldest_night_tenths"),
            "coldest_night_date": col(annual, "coldest_night_date"),
            "record_highs": col(annual, "record_highs"),
            "record_warm_nights": col(annual, "record_warm_nights"),
            "record_lows": col(annual, "record_lows"),
            "record_cold_days": col(annual, "record_cold_days"),
            "jja": {
                "complete_tmax": col(annual, "jja_complete_tmax"),
                "complete_tmin": col(annual, "jja_complete_tmin"),
                "tmax_mean_c": col(annual, "jja_tmax_mean_c"),
                "tmin_mean_c": col(annual, "jja_tmin_mean_c"),
                **_family_block(annual, cfg, prefix="jja_"),
            },
        },
        "cold_season": {
            "year": col(cold, "season"),
            "complete_tmin": col(cold, "complete_tmin"),
            "complete_tmax": col(cold, "complete_tmax"),
            "partial": col(cold, "partial"),
            **_family_block(cold, cfg),
            "coldest_night_tenths": col(cold, "coldest_night_tenths"),
            "coldest_night_date": col(cold, "coldest_night_date"),
            "coldest_tenths": col(cold, "coldest_tenths"),
            "coldest_date": col(cold, "coldest_date"),
        },
        "monthly": {
            "year": col(monthly, "year"),
            "month": col(monthly, "month"),
            "complete_tmax": col(monthly, "complete_tmax"),
            "complete_tmin": col(monthly, "complete_tmin"),
            "days_valid_tmax": col(monthly, "days_valid_tmax"),
            "days_valid_tmin": col(monthly, "days_valid_tmin"),
            "tmax_mean_c": col(monthly, "tmax_mean_c"),
            "tmin_mean_c": col(monthly, "tmin_mean_c"),
            **_family_block(monthly, cfg),
            "hottest_tenths": col(monthly, "hottest_tenths"),
            "warmest_night_tenths": col(monthly, "warmest_night_tenths"),
            "coldest_tenths": col(monthly, "coldest_tenths"),
            "coldest_night_tenths": col(monthly, "coldest_night_tenths"),
        },
        "decades": {
            "decade": col(decades, "decade"),
            "n_years_tmax": col(decades, "n_years_tmax"),
            "n_years_tmin": col(decades, "n_years_tmin"),
            "partial": col(decades, "partial"),
            "tmax_mean_c": col(decades, "tmax_mean_c"),
            "tmin_mean_c": col(decades, "tmin_mean_c"),
            **_family_block(decades, cfg),
            "season_cold_nights": {
                str(t): col(decades, f"season_coldnight_{t}")
                for t in cfg["thresholds_f"]["cold_nights"]
            },
        },
        "summer_to_date": {
            **meta["summer_to_date"],
            "year": col(summer, "year"),
            "days_valid_tmax": col(summer, "days_valid_tmax"),
            "days_valid_tmin": col(summer, "days_valid_tmin"),
            "tmax_mean_c": col(summer, "tmax_mean_c"),
            "tmin_mean_c": col(summer, "tmin_mean_c"),
            "rank_tmax": col(summer, "rank_tmax"),
            "rank_tmin": col(summer, "rank_tmin"),
            **_family_block(summer, cfg),
        },
    }
    n1 = dump(SITE_DATA_DIR / "stations" / sid / "summary.json", summary)

    # --- daily.json: compact arrays for in-browser drill-down ---
    daily = load_daily_wide(sid)
    start, end = daily["date"].min(), daily["date"].max()
    full = pl.DataFrame({"date": pl.date_range(start, end, "1d", eager=True)})
    daily = full.join(daily, on="date", how="left")
    flagged = []
    for el in ("tmax", "tmin", "prcp"):
        f = daily.with_row_index("i").filter(pl.col(f"{el}_qflag").fill_null("") != "")
        for i, v, q in f.select("i", f"{el}_raw", f"{el}_qflag").iter_rows():
            flagged.append([i, el.upper(), v, q])
    rec_idx = {}
    rec = records.with_columns(((pl.col("date") - start).dt.total_days()).alias("i"))
    for kind in M.RECORD_KINDS:
        rec_idx[kind] = rec.filter(pl.col(kind))["i"].cast(pl.Int64).to_list()
        rec_idx[f"{kind}_tie"] = rec.filter(pl.col(f"{kind}_tie"))["i"].cast(pl.Int64).to_list()
    obs = [[(date.fromisoformat(s["from"]) - start).days, s["hhmm"]] for s in meta["obs_time"]]
    daily_json = {
        "id": sid,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "n": daily.height,
        "unit": "tenths_c",
        "tmax": daily["tmax"].to_list(),
        "tmin": daily["tmin"].to_list(),
        "prcp": daily["prcp"].to_list(),
        "obs": obs,
        "flagged": sorted(flagged),
        "records": rec_idx,
        "doy": {
            **{c: col(doy, c) for c in doy.columns if c != "doy"},
        },
    }
    n2 = dump(SITE_DATA_DIR / "stations" / sid / "daily.json", daily_json)

    # index entry
    w = meta["windows"]
    st = meta["summer_to_date"]
    ref = summer.filter(pl.col("year") == st.get("ref_year"))
    ranked = summer.filter(pl.col("rank_tmax").is_not_null())
    dec = decades.filter(~pl.col("hot_95").is_null() | ~pl.col("warm_70").is_null())
    entry = {
        **{
            k: meta[k]
            for k in (
                "id",
                "short",
                "name",
                "region",
                "lat",
                "lon",
                "elev_m",
                "kind",
                "ushcn",
                "first_year",
                "last_year",
                "last_date",
                "last_complete_year",
                "complete_years",
                "obs_hhmm_now",
                "active",
                "state",
                "regions",
            )
        },
        "headline": {
            "hot95_baseline": w.get("baseline", {}).get("hot_95"),
            "hot95_last10": w.get("last10", {}).get("hot_95"),
            "warm70_baseline": w.get("baseline", {}).get("warm_70"),
            "warm70_last10": w.get("last10", {}).get("warm_70"),
            "frost_baseline": w.get("baseline", {}).get("season", {}).get("coldnight_32"),
            "frost_last10": w.get("last10", {}).get("season", {}).get("coldnight_32"),
            "tmax_trend_per_decade_c": meta["trends"]
            .get("tmax_mean_c", {})
            .get("slope_per_decade"),
            "tmin_trend_per_decade_c": meta["trends"]
            .get("tmin_mean_c", {})
            .get("slope_per_decade"),
            "summer_to_date": {
                "through": st.get("through"),
                "ref_year": st.get("ref_year"),
                "window_days": st.get("window_days"),
                "days_valid": int(ref["days_valid_tmax"][0]) if ref.height else None,
                "tmax_mean_c": _clean(ref["tmax_mean_c"][0]) if ref.height else None,
                "tmin_mean_c": _clean(ref["tmin_mean_c"][0]) if ref.height else None,
                "rank_tmax": _clean(ref["rank_tmax"][0]) if ref.height else None,
                "rank_tmin": _clean(ref["rank_tmin"][0]) if ref.height else None,
                "n_years": ranked.height,
                "hot95": _clean(ref["hot_95"][0]) if ref.height else None,
                "warm70": _clean(ref["warm_70"][0]) if ref.height else None,
            },
        },
        "decades": {
            "decade": col(dec, "decade"),
            "partial": col(dec, "partial"),
            "hot95": col(dec, "hot_95"),
            "warm70": col(dec, "warm_70"),
            "frost32": col(dec, "season_coldnight_32"),
        },
    }
    return entry, n1 + n2, summary


MATRIX_METRICS = ("hot95", "warm70", "frost32")
MATRIX_YEAR0 = 1880
NO_DATA = -1  # matrix sentinel; lower bounds are stored as -(lb + 2)


def _metric_series(summary: dict, metric: str) -> tuple[list, list, list]:
    if metric == "hot95":
        blk, lb = summary["annual"]["hot_days"]["95"], summary["annual"]["hot_days_lb"]["95"]
        years = summary["annual"]["year"]
    elif metric == "warm70":
        blk, lb = summary["annual"]["warm_nights"]["70"], summary["annual"]["warm_nights_lb"]["70"]
        years = summary["annual"]["year"]
    else:
        blk = summary["cold_season"]["cold_nights"]["32"]
        lb = summary["cold_season"]["cold_nights_lb"]["32"]
        years = summary["cold_season"]["year"]
    return years, blk, lb


def _export_one(args: tuple[str, str]) -> tuple[str, dict | None, str]:
    sid, region_id = args
    try:
        entry, _n, summary = export_station(sid, _CFG, region_id)
    except Exception as exc:  # noqa: BLE001
        return sid, None, f"  FAILED {sid}: {exc!r}"
    # compact per-metric rows for the national matrices
    rows = {}
    for m in MATRIX_METRICS:
        years, blk, lb = _metric_series(summary, m)
        rows[m] = [(y, v, l) for y, v, l in zip(years, blk, lb)]
    entry["_matrix"] = rows
    return sid, entry, ""


_CFG: dict = {}


def _init_export(cfg: dict) -> None:
    _CFG.update(cfg)


def run_export(region: str = "all") -> None:
    cfg = load_analysis_config()
    regions = load_regions(region)
    all_regions = load_regions()
    todo = [(st.id, reg.id) for reg, st in unique_stations(regions)]
    print(f"==> exporting {len(todo)} stations")
    entries: dict[str, dict] = {}
    with ProcessPoolExecutor(initializer=_init_export, initargs=(cfg,)) as pool:
        for i, (sid, entry, err) in enumerate(pool.map(_export_one, todo, chunksize=4), 1):
            if entry is None:
                print(err)
            else:
                entries[sid] = entry
            if len(todo) > 40 and i % 500 == 0:
                print(f"  … {i}/{len(todo)}")

    year1 = max(e["last_year"] for e in entries.values())
    n_years = year1 - MATRIX_YEAR0 + 1
    for reg in regions:
        ids = [sid for sid in reg.station_ids if sid in entries]
        if not ids:
            continue
        if not reg.generated:
            index = {
                "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
                "ghcnd_version": ghcnd_version(),
                "baseline": cfg["baseline"],
                "thresholds_f": cfg["thresholds_f"],
                "completeness": cfg["completeness"],
                "regions": [
                    {
                        "id": r.id,
                        "name": r.name,
                        "center": list(r.center),
                        "zoom": r.zoom,
                        "default_station": r.default_station,
                        "n_stations": len(r.stations),
                    }
                    for r in all_regions
                ],
                "stations": [
                    {k: v for k, v in entries[sid].items() if k != "_matrix"} for sid in ids
                ],
                "excluded": [
                    {"region": reg.id, **e.__dict__, **_excluded_geo(e.id)} for e in reg.excluded
                ],
            }
            path = SITE_DATA_DIR / ("index.json" if reg.id == "la" else f"{reg.id}/index.json")
            n = dump(path, index)
            print(f"  {path.relative_to(SITE_DATA_DIR)} {n / 1e3:.0f} KB ({len(ids)} stations)")
        else:
            # Compact index + per-metric year matrices (int16, station-major) for the big map.
            compact = []
            mats = {
                m: np.full((len(ids), n_years), NO_DATA, dtype=np.int16) for m in MATRIX_METRICS
            }
            for row, sid in enumerate(ids):
                e = entries[sid]
                h = e["headline"]
                compact.append(
                    [
                        sid,
                        e["short"],
                        e.get("state", ""),
                        round(e["lat"], 3),
                        round(e["lon"], 3),
                        e["first_year"],
                        e["last_year"],
                        1 if e["active"] else 0,
                        h.get("hot95_baseline"),
                        h.get("hot95_last10"),
                        h.get("warm70_baseline"),
                        h.get("warm70_last10"),
                        h.get("frost_baseline"),
                        h.get("frost_last10"),
                        h.get("tmin_trend_per_decade_c"),
                        h.get("tmax_trend_per_decade_c"),
                    ]
                )
                for m in MATRIX_METRICS:
                    for y, v, lb in e["_matrix"][m]:
                        k = y - MATRIX_YEAR0
                        if 0 <= k < n_years:
                            if v is not None:
                                mats[m][row, k] = min(v, 32000)
                            elif lb is not None and lb > 0:
                                mats[m][row, k] = -(min(lb, 32000) + 2)
            out_dir = SITE_DATA_DIR / reg.id
            out_dir.mkdir(parents=True, exist_ok=True)
            n = dump(
                out_dir / "index.json",
                {
                    "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
                    "region": {
                        "id": reg.id,
                        "name": reg.name,
                        "center": list(reg.center),
                        "zoom": reg.zoom,
                    },
                    "baseline": cfg["baseline"],
                    "columns": [
                        "id",
                        "short",
                        "state",
                        "lat",
                        "lon",
                        "first_year",
                        "last_year",
                        "active",
                        "hot95_baseline",
                        "hot95_last10",
                        "warm70_baseline",
                        "warm70_last10",
                        "frost_baseline",
                        "frost_last10",
                        "tmin_trend_per_decade_c",
                        "tmax_trend_per_decade_c",
                    ],
                    "stations": compact,
                    "matrix": {
                        "year0": MATRIX_YEAR0,
                        "n_years": n_years,
                        "metrics": list(MATRIX_METRICS),
                        "dtype": "int16",
                        "no_data": NO_DATA,
                        "lower_bound": "-(lb+2)",
                    },
                },
            )
            print(f"  {reg.id}/index.json {n / 1e3:.0f} KB ({len(ids)} stations)")
            for m in MATRIX_METRICS:
                (out_dir / f"matrix-{m}.bin").write_bytes(mats[m].tobytes())
            print(f"  {reg.id}/matrix-*.bin {mats['hot95'].nbytes / 1e3:.0f} KB each")


def _excluded_geo(sid: str) -> dict:
    row = load_stations().filter(pl.col("id") == sid)
    if row.is_empty():
        return {"lat": None, "lon": None, "name": ""}
    return {"lat": row["lat"][0], "lon": row["lon"][0], "name": row["name"][0]}
