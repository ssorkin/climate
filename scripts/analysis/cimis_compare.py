"""Airports vs CIMIS over identical years.

For every CIMIS station with a heat-wave threshold, pair it with the nearest California
airport (stations/ca.yaml, heat-wave output present) within MAX_KM and |dElev| <= MAX_DELEV.
Over the years both have complete warm seasons, compare the first half with the second half
(each >= MIN_HALF years) for each wave metric, at both stations; also the ordinary
warm-season night. Then pool by network with the hierarchical summer/station bootstrap.
"""

import json
import math
import statistics as st
import sys
from pathlib import Path

import numpy as np
import polars as pl
import yaml

sys.path.insert(0, "src")
from climate.analysis import metrics as M

MAX_KM, MAX_DELEV, MIN_HALF = 40.0, 300.0, 10
METRICS = ("peak_f", "low_f", "after_low_f", "relief_h", "days", "waves_per_year")
ROOT = Path("data/analysis")


def km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = (
        math.sin((la2 - la1) / 2) ** 2
        + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    )
    return 6371 * 2 * math.asin(math.sqrt(h))


def load(sid):
    p = ROOT / sid / "meta.json"
    if not p.exists() or not (ROOT / sid / "heatwaves.parquet").exists():
        return None
    m = json.loads(p.read_text())
    if not m.get("heat_waves"):
        return None
    return m, pl.read_parquet(ROOT / sid / "heatwaves.parquet")


def wmean(w, yrs, m):
    if m == "waves_per_year":
        return w.filter(pl.col("year").is_in(yrs)).height / len(yrs)
    v = w.filter(pl.col("year").is_in(yrs))[m].drop_nulls()
    return float(v.mean()) if v.len() else None


def ordinary_low(sid, yrs, cfg):
    """mean warm-season low over the years, days outside waves+day after (whole °F)."""
    from climate.ingest.store import load_daily_wide

    d = load_daily_wide(sid)
    w = pl.read_parquet(ROOT / sid / "heatwaves.parquet")
    return M.heat_wave_window(w, d, cfg, yrs, min(yrs), max(yrs))


def main(pairs_only=None):
    from climate.config import load_analysis_config

    cfg = {**load_analysis_config()}
    cfg["heat_waves"] = {**cfg["heat_waves"], "window_min_years": MIN_HALF}
    airports = {}
    for s in yaml.safe_load(Path("stations/ca.yaml").read_text())["stations"]:
        r = load(s["id"])
        if r:
            airports[s["id"]] = (s["short"], *r)
    cim = [s for s in yaml.safe_load(Path("stations/cimis.yaml").read_text())["stations"]]
    rows, boots = [], {"cimis": [], "airport": []}
    for s in cim:
        cid = f"CIMIS{s['nbr']:03d}"
        if pairs_only and cid not in pairs_only:
            continue
        r = load(cid)
        if not r:
            continue
        cm, cw = r
        best = None
        for aid, (ashort, am, aw) in airports.items():
            dist = km((cm["lat"], cm["lon"]), (am["lat"], am["lon"]))
            de = abs((cm["elev_m"] or 0) - (am.get("elev_m") or 0))
            shared = len(set(cm["heat_waves"]["years"]) & set(am["heat_waves"]["years"]))
            # within reach: the airport sharing the most complete summers (nearest on ties)
            if (
                dist <= MAX_KM
                and de <= MAX_DELEV
                and (best is None or (shared, -dist) > (best[6], -best[0]))
            ):
                best = (dist, aid, ashort, am, aw, de, shared)
        if not best:
            continue
        dist, aid, ashort, am, aw, de, _ = best
        yrs = sorted(set(cm["heat_waves"]["years"]) & set(am["heat_waves"]["years"]))
        if len(yrs) < 2 * MIN_HALF:
            continue
        h = len(yrs) // 2
        early, late = yrs[:h], yrs[h:]
        row = {
            "cimis": cm["short"],
            "airport": ashort,
            "km": round(dist, 1),
            "delev": round(de),
            "years": f"{early[0]}-{early[-1]} vs {late[0]}-{late[-1]}",
            "n": len(yrs),
            "thr_c": cm["heat_waves"]["threshold_f"],
            "thr_a": am["heat_waves"]["threshold_f"],
        }
        for tag, w in (("c", cw), ("a", aw)):
            for m in METRICS:
                a, b = wmean(w, early, m), wmean(w, late, m)
                row[f"{m}_{tag}"] = (b - a) if a is not None and b is not None else None
        for tag, sid in (("c", cid), ("a", aid)):
            e, l = ordinary_low(sid, early, cfg), ordinary_low(sid, late, cfg)
            row[f"ord_low_{tag}"] = (l["ordinary_low_f"] - e["ordinary_low_f"]) if e and l else None
            row[f"ord_high_{tag}"] = (
                (l["ordinary_high_f"] - e["ordinary_high_f"]) if e and l else None
            )
        bc = M.heat_wave_bootstrap(cw, early, late, metrics=METRICS)
        ba = M.heat_wave_bootstrap(aw, early, late, metrics=METRICS)
        boots["cimis"].append(bc)
        boots["airport"].append(ba)
        n = min([len(v["reps"]) for v in list(bc.values()) + list(ba.values())] or [0])
        boots.setdefault("airport_minus_cimis", []).append(
            {
                m: {
                    "est": ba[m]["est"] - bc[m]["est"],
                    "reps": ba[m]["reps"][:n] - bc[m]["reps"][:n],
                }
                for m in METRICS
                if m in ba and m in bc
            }
        )
        rows.append(row)
    f = lambda v: ("%5.1f" % v) if v is not None else "    -"
    print(
        f"{len(rows)} pairs (<= {MAX_KM} km, |dElev| <= {MAX_DELEV} m, first vs second half of shared complete summers)"
    )
    print(
        "%-26s %-28s  km  %-20s   dLow  C/A    dPeak C/A   dRelief C/A   dWaves C/A   dOrdLow C/A"
        % ("CIMIS", "airport", "years")
    )
    for r in sorted(rows, key=lambda r: r["low_f_a"] if r["low_f_a"] is not None else -99):
        print(
            "%-26s %-28s %3.0f  %-20s %s %s  %s %s  %s %s  %s %s  %s %s"
            % (
                r["cimis"][:26],
                r["airport"][:28],
                r["km"],
                r["years"],
                f(r["low_f_c"]),
                f(r["low_f_a"]),
                f(r["peak_f_c"]),
                f(r["peak_f_a"]),
                f(r["relief_h_c"]),
                f(r["relief_h_a"]),
                f(r["waves_per_year_c"]),
                f(r["waves_per_year_a"]),
                f(r["ord_low_c"]),
                f(r["ord_low_a"]),
            )
        )
    print()
    for m in METRICS + ("ord_low", "ord_high"):
        c = [r[f"{m}_c"] for r in rows if r[f"{m}_c"] is not None]
        a = [r[f"{m}_a"] for r in rows if r[f"{m}_a"] is not None]
        d = [
            r[f"{m}_a"] - r[f"{m}_c"]
            for r in rows
            if r[f"{m}_a"] is not None and r[f"{m}_c"] is not None
        ]
        print(
            f"{m:15s} CIMIS median {st.median(c):+.2f} mean {st.mean(c):+.2f} | airport median {st.median(a):+.2f} mean {st.mean(a):+.2f} | airport-minus-CIMIS median {st.median(d):+.2f} (share>0 {np.mean([x > 0 for x in d]):.2f})"
        )
    for net in ("cimis", "airport", "airport_minus_cimis"):
        p = M.pooled_bootstrap(boots[net])
        print(net, "pooled:", {m: (p[m]["est"], p[m]["lo"], p[m]["hi"]) for m in METRICS if m in p})
    json.dump(rows, open("data/analysis/scratch/pairs.json", "w"))


if __name__ == "__main__":
    main(set(sys.argv[1:]) or None)
