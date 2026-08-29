"""Is the lost overnight relief a humidity story? Per heat wave, the mean night-time dew point
(18:00-08:00, nights 2..n) next to the coolest night; then-vs-now changes in both; a within-
station regression of the coolest night on the peak high and the night dew point; and the
then->now night change with the dew-point term removed.

Usage: humidity.py <region-or-yaml> [then0 then1 now_years]  e.g. humidity.py la 1951 1980 30
"""

import json, sys, statistics as st
from datetime import timedelta
from pathlib import Path
import numpy as np, polars as pl, yaml

sys.path.insert(0, "src")
from climate.analysis.metrics import f_whole

ROOT = Path("data/analysis")
MONTHS = [5, 6, 7, 8, 9, 10]


def c_to_f(tenths):
    return tenths / 10 * 1.8 + 32


def night_table(sid):
    h = pl.read_parquet(
        f"data/parquet/hourly/station={sid}/data.parquet",
        columns=["date", "hour", "temp", "dewp", "rh"],
    )
    n = (
        h.with_columns(
            pl.when(pl.col("hour") >= 18)
            .then(pl.col("date") + pl.duration(days=1))
            .when(pl.col("hour") <= 8)
            .then(pl.col("date"))
            .otherwise(None)
            .alias("night")
        )
        .filter(pl.col("night").is_not_null())
        .group_by("night")
        .agg(
            pl.col("temp").drop_nulls().len().alias("n"),
            pl.col("dewp").drop_nulls().len().alias("nd"),
            pl.col("temp").min().alias("tmin"),
            pl.col("dewp").mean().alias("dewp"),
            pl.col("rh").mean().alias("rh"),
        )
        .filter((pl.col("n") >= 5))
    )
    return {r["night"]: r for r in n.iter_rows(named=True)}


def station(sid, then, now_n, y_from=None, k=15):
    meta = json.loads((ROOT / sid / "meta.json").read_text())
    hw = meta.get("heat_waves")
    if not hw:
        return None
    waves = pl.read_parquet(ROOT / sid / "heatwaves.parquet")
    years = hw["years"]
    nights = night_table(sid)
    rows = []
    in_wave = set()
    for w in waves.iter_rows(named=True):
        ds = [w["start"] + timedelta(days=j) for j in range(1, w["days"] + 1)]
        in_wave.update([w["start"]] + ds + [w["end"] + timedelta(days=1)])
        ns = [nights[d] for d in ds if d in nights and nights[d]["nd"] >= 5]
        if not ns or w["low_f"] is None:
            continue
        rows.append(
            {
                "year": w["year"],
                "peak_f": w["peak_f"],
                "low_f": w["low_f"],
                "relief_h": w["relief_h"],
                "dewp_f": c_to_f(np.mean([x["dewp"] for x in ns])),
                "rh": float(np.mean([x["rh"] for x in ns if x["rh"] is not None] or [np.nan])),
            }
        )
    if len(rows) < 20:
        return None
    wv = pl.DataFrame(rows)
    # ordinary warm-season nights, per year
    ordn = {}
    for d, r in nights.items():
        if (
            d.month in MONTHS
            and d not in in_wave
            and r["nd"] >= 5
            and r["tmin"] is not None
            and r["dewp"] is not None
        ):
            ordn.setdefault(d.year, []).append((c_to_f(r["dewp"]), f_whole(r["tmin"])))
    # windows
    if y_from:
        ys = [y for y in years if y >= y_from]
        if len(ys) < 2 * k:
            return None
        w_then, w_now = ys[:k], ys[-k:]
    else:
        last = years[-1]
        w_then = [y for y in years if then[0] <= y <= then[1]]
        w_now = [y for y in years if last - now_n + 1 <= y <= last]
        if len(w_then) < 15 or len(w_now) < 15 or last < 2015:
            return None

    def wmean(col, yrs):
        v = wv.filter(pl.col("year").is_in(yrs))[col].drop_nulls()
        return float(v.mean()) if v.len() else None

    def ord_mean(idx, yrs):
        v = [x[idx] for y in yrs for x in ordn.get(y, [])]
        return float(np.mean(v)) if v else None

    # within-station regression: low_f ~ 1 + peak_f + dewp_f  (all waves with complete years)
    d = wv.filter(pl.col("year").is_in(years)).drop_nulls(["peak_f", "low_f", "dewp_f"])
    X = np.column_stack([np.ones(d.height), d["peak_f"].to_numpy(), d["dewp_f"].to_numpy()])
    y = d["low_f"].to_numpy()
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    r2 = 1 - resid.var() / y.var()
    # simple correlation, wave by wave
    rho = float(np.corrcoef(d["dewp_f"].to_numpy(), d["low_f"].to_numpy())[0, 1])
    dl = wmean("low_f", w_now) - wmean("low_f", w_then)
    dd = wmean("dewp_f", w_now) - wmean("dewp_f", w_then)
    dp = wmean("peak_f", w_now) - wmean("peak_f", w_then)
    dres = float(
        resid[d["year"].is_in(w_now).to_numpy()].mean()
        - resid[d["year"].is_in(w_then).to_numpy()].mean()
    )
    return {
        "id": sid,
        "short": meta.get("short", sid),
        "n_waves": d.height,
        "then": f"{w_then[0]}-{w_then[-1]}",
        "now": f"{w_now[0]}-{w_now[-1]}",
        "d_low": dl,
        "d_peak": dp,
        "d_dewp_wave": dd,
        "d_rh_wave": (wmean("rh", w_now) or np.nan) - (wmean("rh", w_then) or np.nan),
        "d_relief": (wmean("relief_h", w_now) or np.nan) - (wmean("relief_h", w_then) or np.nan),
        "d_dewp_ord": (ord_mean(0, w_now) or np.nan) - (ord_mean(0, w_then) or np.nan),
        "d_low_ord": (ord_mean(1, w_now) or np.nan) - (ord_mean(1, w_then) or np.nan),
        "beta_dewp": float(beta[2]),
        "beta_peak": float(beta[1]),
        "r2": float(r2),
        "rho": rho,
        "explained": float(beta[2] * dd),
        "d_low_adj": dres,
        "dewp_then": wmean("dewp_f", w_then),
        "low_then": wmean("low_f", w_then),
    }


def main():
    arg = sys.argv[1]
    then = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (1951, 1980)
    now_n = int(sys.argv[4]) if len(sys.argv) > 4 else 30
    y_from = int(sys.argv[5]) if len(sys.argv) > 5 else None
    path = Path(arg) if arg.endswith(".yaml") else Path(f"stations/{arg}.yaml")
    raw = yaml.safe_load(path.read_text())["stations"]
    ids = [f"CIMIS{s['nbr']:03d}" if "nbr" in s else s["id"] for s in raw]
    out = []
    for sid in ids:
        try:
            r = station(sid, then, now_n, y_from)
        except FileNotFoundError:
            r = None
        if r:
            out.append(r)
    f = lambda v, p=1: ("%6.*f" % (p, v)) if v is not None and not np.isnan(v) else "     -"
    print(
        f"{len(out)} stations; windows {then if not y_from else f'first15/last15 from {y_from}'} vs last {now_n}"
    )
    print(
        "%-30s  nW  dLow dPeak | dDewp(wave) dRH  dDewp(ord) dLow(ord) | beta_dewp  rho   R2 | explained  dLow_adj"
        % "station"
    )
    for r in sorted(out, key=lambda r: r["d_low"]):
        print(
            "%-30s %3d %s %s | %s %s %s %s | %s %s %s | %s %s"
            % (
                r["short"][:30],
                r["n_waves"],
                f(r["d_low"]),
                f(r["d_peak"]),
                f(r["d_dewp_wave"]),
                f(r["d_rh_wave"]),
                f(r["d_dewp_ord"]),
                f(r["d_low_ord"]),
                f(r["beta_dewp"], 2),
                f(r["rho"], 2),
                f(r["r2"], 2),
                f(r["explained"]),
                f(r["d_low_adj"]),
            )
        )
    for k in (
        "d_low",
        "d_peak",
        "d_dewp_wave",
        "d_rh_wave",
        "d_dewp_ord",
        "d_low_ord",
        "beta_dewp",
        "rho",
        "r2",
        "explained",
        "d_low_adj",
    ):
        v = [r[k] for r in out if r[k] is not None and not np.isnan(r[k])]
        print(
            f"{k:12s} median {st.median(v):+.2f}  mean {st.mean(v):+.2f}  share>0 {np.mean([x > 0 for x in v]):.2f}"
        )
    Path("data/analysis/scratch").mkdir(parents=True, exist_ok=True)
    json.dump(out, open(f"data/analysis/scratch/humidity_{path.stem}.json", "w"))


if __name__ == "__main__":
    main()
