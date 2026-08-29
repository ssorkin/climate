"""Era-agnostic heat-wave change summary for a set of station analysis dirs.
Usage: hw_summary.py <stations.yaml|'cimis'> ; reads data/analysis/<id>/{meta.json,heatwaves.parquet}."""

import json
import statistics as st
import sys
from pathlib import Path

import numpy as np
import polars as pl
import yaml

sys.path.insert(0, "src")
from climate.analysis import metrics as M

METRICS = ("peak_f", "low_f", "after_low_f", "relief_h", "days", "waves_per_year")


def window_mean(w, yrs, m):
    if m == "waves_per_year":
        return w.filter(pl.col("year").is_in(yrs)).height / len(yrs)
    v = w.filter(pl.col("year").is_in(yrs))[m].drop_nulls()
    return float(v.mean()) if v.len() else None


def theil_sen(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    ok = ~np.isnan(y)
    x, y = x[ok], y[ok]
    if len(x) < 8:
        return None
    s = [
        (y[j] - y[i]) / (x[j] - x[i])
        for i in range(len(x))
        for j in range(i + 1, len(x))
        if x[j] != x[i]
    ]
    return float(np.median(s)) * 10  # per decade


def summarize(entries, root=Path("data/analysis"), label="", k=15, y_from=None):
    """entries: [(id, short)]. Compares first k vs last k complete summers (>= y_from if given),
    plus a Theil-Sen trend per decade of each metric's yearly mean."""
    rows, boots = [], []
    for sid, short in entries:
        d = root / sid
        if not (d / "heatwaves.parquet").exists():
            continue
        meta = json.loads((d / "meta.json").read_text())
        hw = meta["heat_waves"]
        yrs = [y for y in hw["years"] if y_from is None or y >= y_from]
        if len(yrs) < 2 * k:
            continue
        w = pl.read_parquet(d / "heatwaves.parquet")
        early, late = yrs[:k], yrs[-k:]
        r = {
            "id": sid,
            "short": short,
            "thr": hw["threshold_f"],
            "years": f"{early[0]}-{early[-1]} vs {late[0]}-{late[-1]}",
            "n_waves": w.filter(pl.col("year").is_in(yrs)).height,
        }
        for m in METRICS:
            a, b = window_mean(w, early, m), window_mean(w, late, m)
            r[m] = (b - a) if a is not None and b is not None else None
            # trend of yearly means
            ys, vs = [], []
            for y in yrs:
                v = window_mean(w, [y], m)
                ys.append(y)
                vs.append(np.nan if v is None else v)
            r[m + "_trend"] = theil_sen(ys, vs)
        boots.append(M.heat_wave_bootstrap(w, early, late, metrics=METRICS))
        rows.append(r)
    pooled = M.pooled_bootstrap(boots) if boots else {}
    print(f"\n=== {label}: {len(rows)} stations, first {k} vs last {k} complete summers")
    print(
        "%-30s thr  %-20s  nW  dPeak  dLow dAfter dRelf dDays dW/yr | trends/decade: peak  low relief"
        % ("station", "windows")
    )
    f = lambda v, w=5, p=1: ("%*.*f" % (w, p, v)) if v is not None else " " * (w - 1) + "-"
    for r in sorted(rows, key=lambda r: (r["low_f"] is None, r["low_f"])):
        print(
            "%-30s %3d  %-20s %3d %s %s %s %s %s %s | %s %s %s"
            % (
                r["short"][:30],
                r["thr"],
                r["years"],
                r["n_waves"],
                f(r["peak_f"]),
                f(r["low_f"]),
                f(r["after_low_f"]),
                f(r["relief_h"]),
                f(r["days"], 5, 2),
                f(r["waves_per_year"], 5, 2),
                f(r["peak_f_trend"]),
                f(r["low_f_trend"]),
                f(r["relief_h_trend"]),
            )
        )
    for m in METRICS:
        v = [r[m] for r in rows if r[m] is not None]
        t = [r[m + "_trend"] for r in rows if r[m + "_trend"] is not None]
        p = pooled.get(m, {})
        print(
            f"{m:15s} n={len(v):3d} median {st.median(v):+.2f} mean {st.mean(v):+.2f} share>0 {np.mean([x > 0 for x in v]):.2f}  pooled {p.get('est')} [{p.get('lo')}, {p.get('hi')}] | trend/decade median {st.median(t):+.2f}"
            if v
            else f"{m}: none"
        )
    json.dump(
        rows,
        open("data/analysis/scratch/rows_" + label.split()[0].replace("/", "_") + ".json", "w"),
    )
    return rows, pooled


if __name__ == "__main__":
    arg = sys.argv[1]
    k = int(sys.argv[2]) if len(sys.argv) > 2 else 15
    y_from = int(sys.argv[3]) if len(sys.argv) > 3 else None
    ents = [(s["id"], s["short"]) for s in yaml.safe_load(Path(arg).read_text())["stations"]]
    summarize(ents, label=f"{arg} (from {y_from})", k=k, y_from=y_from)
