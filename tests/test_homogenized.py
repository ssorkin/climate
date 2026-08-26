from datetime import date

import polars as pl

from climate.analysis import homogenized as H
from climate.analysis import metrics as M
from tests.conftest import make_daily


def test_breaks_merge_adjacent_years_and_flip_sign():
    ann = pl.DataFrame(
        {
            "year": [2000, 2001, 2002, 2003, 2004, 2005],
            "tmax_off": [0.0, 0.0, 0.5, 1.0, 1.0, 1.0],  # raw dropped 1.0 across 2002-03
            "tmin_off": [0.0, 0.0, 0.0, 0.0, -0.6, -0.6],  # raw rose 0.6 in 2004
        }
    )
    b = H.breaks(ann)
    assert b == [
        {"year": 2003, "tmax_c": -1.0, "tmin_c": 0.0},
        {"year": 2004, "tmax_c": 0.0, "tmin_c": 0.6},
    ]
    assert all(str(x["tmin_c"]) != "-0.0" for x in b)


def test_adjusted_counts_apply_monthly_offsets(cfg):
    # Constant 94°F highs; a +1°C July offset lifts July to ~95.8°F -> 31 hot days.
    daily = make_daily(date(2000, 1, 1), date(2000, 12, 31), 94, 60)
    annual = M.annual_metrics(daily, cfg, date(2026, 8, 26))
    off = pl.DataFrame(
        {
            "year": [2000] * 12,
            "month": list(range(1, 13)),
            "tmax_off": [1.0 if m == 7 else 0.0 for m in range(1, 13)],
            "tmin_off": [0.0] * 12,
        },
        schema={"year": pl.Int32, "month": pl.Int8, "tmax_off": pl.Float64, "tmin_off": pl.Float64},
    )
    adj = H.adjusted_counts(daily, off, annual).row(0, named=True)
    assert adj["hot_95_adj"] == 31 and adj["warm_70_adj"] == 0
