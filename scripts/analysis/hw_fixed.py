import json
import statistics as st
import sys
from pathlib import Path

import polars as pl
import yaml

sys.path.insert(0, "src")
from climate.analysis import metrics as M

reg = sys.argv[1]
root = Path("data/analysis")
ca = yaml.safe_load(Path(reg).read_text())["stations"]
rows = []
boots = []
seen = set()
for s in ca:
    p = root / s["id"] / "meta.json"
    if not p.exists():
        continue
    m = json.loads(p.read_text())
    hw = m.get("heat_waves")
    if not hw:
        continue
    wb, wn = hw["windows"].get("baseline"), hw["windows"].get("last30")
    if not (wb and wn) or wn["years"][1] < 2015 or s["short"] in seen:
        continue
    seen.add(s["short"])
    d = lambda k: (wn[k] - wb[k]) if wn.get(k) is not None and wb.get(k) is not None else None
    r = dict(
        id=s["id"],
        short=s["short"],
        thr=hw["threshold_f"],
        nB=wb["n"],
        nN=wn["n"],
        now=wn["years"],
        peak=d("peak_f"),
        low=d("low_f"),
        after=d("after_low_f"),
        relief=d("relief_h"),
        days=d("mean_days"),
        waves=d("waves_per_year"),
        ohi=d("ordinary_high_f"),
        olo=d("ordinary_low_f"),
        lat=m["lat"],
        lon=m["lon"],
        elev=m.get("elev_m"),
        low_then=wb["low_f"],
        low_now=wn["low_f"],
        peak_then=wb["peak_f"],
        peak_now=wn["peak_f"],
    )
    rows.append(r)
    w = pl.read_parquet(root / s["id"] / "heatwaves.parquet")
    boots.append(
        M.heat_wave_bootstrap(
            w,
            [y for y in hw["years"] if 1951 <= y <= 1980],
            [y for y in hw["years"] if wn["years"][0] <= y <= wn["years"][1]],
        )
    )
pooled = M.pooled_bootstrap(boots)
f = lambda v, p=1: ("%5.*f" % (p, v)) if v is not None else "    -"
print(len(rows), "stations with 1951-80 vs last-30 windows (now ends >= 2015)")
print(
    "%-32s thr nB nN now        dPeak  dLow dAfter dRelf dDays dW/yr  dOrdHi dOrdLo  elev"
    % "station"
)
for r in sorted(rows, key=lambda r: r["low"]):
    print(
        "%-32s %3d %2d %2d %s %s %s %s %s %s %s  %s %s %5s"
        % (
            r["short"][:32],
            r["thr"],
            r["nB"],
            r["nN"],
            f"{r['now'][0]}-{r['now'][1]}",
            f(r["peak"]),
            f(r["low"]),
            f(r["after"]),
            f(r["relief"]),
            f(r["days"], 2),
            f(r["waves"], 2),
            f(r["ohi"]),
            f(r["olo"]),
            r["elev"],
        )
    )
for k in ["peak", "low", "after", "relief", "days", "waves", "ohi", "olo"]:
    v = [r[k] for r in rows if r[k] is not None]
    key = {
        "peak": "peak_f",
        "low": "low_f",
        "after": "after_low_f",
        "relief": "relief_h",
        "days": "days",
        "waves": "waves_per_year",
    }.get(k)
    pp = pooled.get(key, {}) if key else {}
    print(
        f"{k:7s} n={len(v)} median {st.median(v):+.2f} mean {st.mean(v):+.2f} share>0 {sum(x > 0 for x in v) / len(v):.2f}  pooled {pp.get('est')} [{pp.get('lo')}, {pp.get('hi')}]"
    )
v = [r["low"] - r["olo"] for r in rows if r["low"] is not None and r["olo"] is not None]
print(
    "wave coolest-night change minus ordinary-night change: median %+.2f mean %+.2f share>0 %.2f"
    % (st.median(v), st.mean(v), sum(x > 0 for x in v) / len(v))
)
v = [r["peak"] - r["ohi"] for r in rows if r["peak"] is not None and r["ohi"] is not None]
print(
    "wave peak change minus ordinary-high change: median %+.2f mean %+.2f"
    % (st.median(v), st.mean(v))
)
json.dump(rows, open("data/analysis/scratch/ca_fixed_rows.json", "w"))
