"""Sea-surface temperature next to the LA night record.

Sources (fetched ad hoc, not part of the pipeline): NDBC buoy 46025 (Santa Monica Basin,
hourly WTMP, 1982-) from https://www.ndbc.noaa.gov/data/historical/stdmet/46025h<year>.txt.gz
and NOAA ERSST v5 monthly 2-degree grid (cell 34N/118W and 32N/118W) from
https://www.ncei.noaa.gov/pub/data/cmb/ersst/v5/netcdf/ersst.v5.<yyyymm>.nc . Both are reduced
to a May-Oct mean per year (buoy: >= 120 days) and saved in data/analysis/scratch/
(sst_46025_mayoct.parquet, ersst_la_mayoct.parquet). la_yearly.npy holds, per LA airport, the
yearly mean coolest-wave-night low, wave-night dew point, ordinary-night low and dew point
(columns: year, low, wave_dewp, ord_low, ord_dewp, buoy_sst) built by humidity.py's night tables.

Findings 2026-08-29: buoy vs ERSST r = 0.87 (buoy runs +1.2 C warmer, nearshore). ERSST May-Oct
1951-80 -> 1996-2025: +0.65 F (34N) / +0.81 F (32N); buoy 1982-96 -> 2011-25: +1.2 F, +0.36 F/decade.
Yearly SST explains ordinary summer nights at the coast (r 0.5-0.6 over 1940-2025, 0.76-0.92 over
1982-2025, ~0.7-0.9 F per F, holds when detrended), coastal dew point moderately (r 0.5-0.6; ~0
inland), heat-wave nights weakly (r 0.1-0.4). The SST change x slope implies +0.4..+0.6 F of the
+1.3..+2.1 F ordinary-night change, and little of the +3..+4 F heat-wave-night change.
"""

import numpy as np, polars as pl
from pathlib import Path

SCRATCH = Path("data/analysis/scratch")


def series():
    buoy = pl.read_parquet(SCRATCH / "sst_46025_mayoct.parquet")
    ersst = pl.read_parquet(SCRATCH / "ersst_la_mayoct.parquet")
    return buoy, ersst


def correlations(since=1982):
    out = np.load(SCRATCH / "la_yearly.npy", allow_pickle=True).item()
    _, ersst = series()
    sst = dict(zip(ersst["year"].to_list(), (ersst["sst34"] * 1.8 + 32).to_list()))
    for name, A in out.items():
        s = np.array([sst.get(int(y), np.nan) for y in A[:, 0]])
        for col, label in (
            (3, "ordinary night"),
            (4, "ordinary dew point"),
            (1, "coolest wave night"),
        ):
            m = (A[:, 0] >= since) & ~np.isnan(A[:, col]) & ~np.isnan(s)
            r = np.corrcoef(A[m, col], s[m])[0, 1]
            b = np.polyfit(s[m], A[m, col], 1)[0]
            print(f"{name:<11} {label:<20} r {r:5.2f}  slope {b:5.2f} F/F  n={m.sum()}")


if __name__ == "__main__":
    correlations(1940)
