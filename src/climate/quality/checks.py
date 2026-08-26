"""Data-quality checks over the raw files, the Parquet store and the station config.

Severity: anomaly (blocks the nightly deploy under --strict), warning, info.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, timedelta
from itertools import pairwise

import polars as pl

from climate.acquire.base import sha256_file
from climate.analysis.metrics import f_whole_expr, today_utc
from climate.analysis.obs_time import segments
from climate.config import load_analysis_config, load_regions
from climate.ingest.store import load_daily_long, load_daily_wide, load_inventory, load_stations
from climate.paths import MANIFEST_DIR, RAW_DIR


@dataclass
class Finding:
    check: str
    severity: str  # anomaly | warning | info
    year: int | None
    entity: str
    message: str
    details: dict = field(default_factory=dict)


def _today() -> date:
    return today_utc()


def _stations() -> list[tuple[str, str]]:
    return [(s.id, s.short) for r in load_regions() for s in r.stations]


def check_manifests() -> list[Finding]:
    out = []
    for mpath in sorted(MANIFEST_DIR.glob("*.json")):
        manifest = json.loads(mpath.read_text())
        for fname, e in manifest.items():
            p = RAW_DIR / e["dataset"] / fname
            if not p.exists():
                out.append(
                    Finding("manifests", "anomaly", None, fname, f"{fname} missing from data/raw")
                )
            elif p.stat().st_size != e["size"] or sha256_file(p) != e["sha256"]:
                out.append(
                    Finding("manifests", "anomaly", None, fname, f"{fname} does not match manifest")
                )
    if not out:
        out.append(Finding("manifests", "info", None, "all", "all raw files match their manifest"))
    return out


def check_station_config() -> list[Finding]:
    out = []
    stations = load_stations()
    inv = load_inventory()
    year = _today().year
    for sid, short in _stations():
        if stations.filter(pl.col("id") == sid).is_empty():
            out.append(
                Finding("station_config", "anomaly", None, sid, f"{sid} not in ghcnd-stations")
            )
            continue
        for el in ("TMAX", "TMIN"):
            row = inv.filter((pl.col("id") == sid) & (pl.col("element") == el))
            if row.is_empty():
                out.append(
                    Finding(
                        "station_config", "anomaly", None, sid, f"{short}: no {el} in inventory"
                    )
                )
            elif row["last_year"][0] < year - 1:
                out.append(
                    Finding(
                        "station_config",
                        "warning",
                        int(row["last_year"][0]),
                        sid,
                        f"{short}: {el} inventory ends {row['last_year'][0]}",
                    )
                )
    if not out:
        out.append(
            Finding("station_config", "info", None, "all", "all stations present with TMAX/TMIN")
        )
    return out


def check_completeness() -> list[Finding]:
    cfg = load_analysis_config()
    frac = cfg["completeness"]["annual_min_frac"]
    year = _today().year
    out = []
    for sid, short in _stations():
        d = load_daily_wide(sid).with_columns(pl.col("date").dt.year().alias("year"))
        g = d.group_by("year").agg(
            pl.col("tmax").is_not_null().sum().alias("tmax"),
            pl.col("tmin").is_not_null().sum().alias("tmin"),
        )
        g = g.with_columns(
            pl.col("year")
            .map_elements(
                lambda y: 366 if y % 4 == 0 and (y % 100 != 0 or y % 400 == 0) else 365,
                return_dtype=pl.Int32,
            )
            .alias("n")
        ).sort("year")
        complete = g.filter(
            (pl.col("tmax") >= (pl.col("n") * frac).ceil())
            & (pl.col("tmin") >= (pl.col("n") * frac).ceil())
            & (pl.col("year") < year)
        )
        all_years = g.filter(pl.col("year") < year)
        gaps = all_years.filter(~pl.col("year").is_in(complete["year"]))["year"].to_list()
        out.append(
            Finding(
                "completeness",
                "info",
                None,
                sid,
                f"{short}: {complete.height} complete years of {all_years.height} "
                f"({all_years['year'].min()}-{all_years['year'].max()}); incomplete: "
                + (
                    ", ".join(str(y) for y in gaps[:40]) + (" …" if len(gaps) > 40 else "")
                    if gaps
                    else "none"
                ),
            )
        )
        recent = all_years.filter(pl.col("year") >= year - 5)
        for r in recent.iter_rows(named=True):
            if r["tmax"] < r["n"] * frac or r["tmin"] < r["n"] * frac:
                out.append(
                    Finding(
                        "completeness",
                        "warning",
                        r["year"],
                        sid,
                        f"{short}: {r['year']} has {r['tmax']}/{r['n']} TMAX and {r['tmin']}/{r['n']} TMIN days",
                    )
                )
    return out


def check_gaps(min_days: int = 30) -> list[Finding]:
    out = []
    for sid, short in _stations():
        d = load_daily_wide(sid).select("date", "tmax").sort("date")
        dates = d.filter(pl.col("tmax").is_not_null())["date"].to_list()
        examples = []
        for a, b in pairwise(dates):
            gap = (b - a).days - 1
            if gap >= min_days:
                examples.append(f"{a + timedelta(days=1)} → {b - timedelta(days=1)} ({gap} days)")
        if examples:
            out.append(
                Finding(
                    "gaps",
                    "info",
                    None,
                    sid,
                    f"{short}: {len(examples)} gap(s) of ≥{min_days} days without TMAX",
                    {"examples": examples[:8]},
                )
            )
    return out


def check_qflags() -> list[Finding]:
    out = []
    year = _today().year
    for sid, short in _stations():
        long = load_daily_long(sid).filter(pl.col("element").is_in(["TMAX", "TMIN"]))
        flagged = long.filter(pl.col("qflag") != "")
        counts = dict(flagged.group_by("qflag").len().sort("qflag").iter_rows())
        if counts:
            out.append(
                Finding(
                    "qflags",
                    "info",
                    None,
                    sid,
                    f"{short}: {flagged.height} flagged TMAX/TMIN values withheld "
                    + ", ".join(f"{k}={v}" for k, v in counts.items()),
                )
            )
        recent = long.filter(pl.col("date").dt.year() >= year - 5)
        if recent.height:
            share = recent.filter(pl.col("qflag") != "").height / recent.height
            if share > 0.005:
                out.append(
                    Finding(
                        "qflags",
                        "warning",
                        None,
                        sid,
                        f"{short}: {share:.1%} of the last 5 years' values are flagged",
                    )
                )
    return out


def check_obs_time_segments() -> list[Finding]:
    out = []
    cutoff = _today() - timedelta(days=730)
    for sid, short in _stations():
        segs = segments(load_daily_wide(sid), min_days=30)
        desc = "; ".join(f"{s['from']}→{s['to']} {s['hhmm'] or 'n/a'}" for s in segs)
        out.append(Finding("obs_time", "info", None, sid, f"{short}: {desc}"))
        for s in segs[1:]:
            if s["from"] >= cutoff:
                out.append(
                    Finding(
                        "obs_time",
                        "warning",
                        s["from"].year,
                        sid,
                        f"{short}: observation time changed to {s['hhmm'] or 'n/a'} on {s['from']}",
                    )
                )
    return out


def check_suspicious_values() -> list[Finding]:
    out = []
    recent_cutoff = _today() - timedelta(days=90)
    for sid, short in _stations():
        d = load_daily_wide(sid).sort("date")
        d = d.with_columns(
            (pl.col("tmax") < pl.col("tmin")).alias("inverted"),
            ((pl.col("tmax") - pl.col("tmin")) > 400).alias("wide_range"),
            ((pl.col("tmax") - pl.col("tmax").shift(1)).abs() > 250).alias("jump"),
            ((pl.col("tmax") > 550) | (pl.col("tmin") < -300)).alias("extreme"),
        )
        # runs of >= 7 identical TMAX values (stuck instrument)
        runs = d.filter(pl.col("tmax").is_not_null()).with_columns(
            (pl.col("tmax") != pl.col("tmax").shift(1)).cum_sum().alias("run")
        )
        stuck = (
            runs.group_by("run")
            .agg(pl.len().alias("n"), pl.col("date").min())
            .filter(pl.col("n") >= 7)
        )
        problems = []
        for kind in ("inverted", "wide_range", "jump", "extreme"):
            for r in (
                d.filter(pl.col(kind).fill_null(False)).select("date", "tmax", "tmin").iter_rows()
            ):
                problems.append((r[0], f"{kind} on {r[0]}: tmax={r[1]} tmin={r[2]}"))
        for r in stuck.iter_rows():
            problems.append((r[2], f"{r[1]} identical TMAX values from {r[2]}"))
        if problems:
            problems.sort()
            recent = [p for p in problems if p[0] >= recent_cutoff]
            sev = "anomaly" if recent else "warning"
            out.append(
                Finding(
                    "suspicious_values",
                    sev,
                    None,
                    sid,
                    f"{short}: {len(problems)} suspicious unflagged value(s)"
                    + (f", {len(recent)} in the last 90 days" if recent else ""),
                    {"examples": [p[1] for p in (recent or problems)[:8]]},
                )
            )
    return out


def check_whole_degree_f() -> list[Finding]:
    """US observers report whole °F; NOAA stores tenths °C. Check the conversion round-trips."""
    out = []
    for sid, short in _stations():
        d = load_daily_wide(sid).filter(pl.col("tmax").is_not_null())
        f = f_whole_expr(pl.col("tmax"))
        exact = (f - 32) * 50 / 9
        ok = (exact.round(0).cast(pl.Int64) == pl.col("tmax")) | (
            exact.cast(pl.Int64) == pl.col("tmax")
        )
        share = d.select(ok.mean()).item()
        if share < 0.995:
            out.append(
                Finding(
                    "whole_degree_f",
                    "warning",
                    None,
                    sid,
                    f"{short}: only {share:.2%} of TMAX values round-trip to whole °F",
                )
            )
    if not out:
        out.append(
            Finding(
                "whole_degree_f",
                "info",
                None,
                "all",
                "≥99.5% of values round-trip to whole °F everywhere",
            )
        )
    return out


def check_freshness() -> list[Finding]:
    out = []
    today = _today()
    ages = []
    for sid, short in _stations():
        d = load_daily_wide(sid).filter(pl.col("tmax").is_not_null())
        last = d["date"].max()
        age = (today - last).days
        ages.append(age)
        if age > 14:
            out.append(
                Finding(
                    "freshness",
                    "warning",
                    last.year,
                    sid,
                    f"{short}: last TMAX is {last} ({age} days ago)",
                )
            )
    if ages and min(ages) > 45:
        out.append(
            Finding(
                "freshness",
                "anomaly",
                None,
                "all",
                f"every station is stale (newest reading {min(ages)} days old) — feed problem?",
            )
        )
    return out


def check_duplicates() -> list[Finding]:
    out = []
    for sid, short in _stations():
        long = load_daily_long(sid)
        dup = long.group_by(["date", "element"]).len().filter(pl.col("len") > 1)
        if dup.height:
            out.append(
                Finding(
                    "duplicates",
                    "anomaly",
                    None,
                    sid,
                    f"{short}: {dup.height} duplicate (date, element) rows",
                )
            )
    if not out:
        out.append(Finding("duplicates", "info", None, "all", "no duplicate rows"))
    return out


ALL_CHECKS = [
    check_manifests,
    check_station_config,
    check_completeness,
    check_gaps,
    check_qflags,
    check_obs_time_segments,
    check_suspicious_values,
    check_whole_degree_f,
    check_freshness,
    check_duplicates,
]
