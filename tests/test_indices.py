"""ETCCDI-style percentile indices: baseline reads ~10% by construction; a shift shows up."""

from datetime import date

import polars as pl

import climate.analysis.metrics as M
from tests.conftest import make_daily

SEED = 20260827


def _series(shift_after: int, shift_f: float):
    import random

    rng = random.Random(SEED)

    def tmax(d):
        return (
            75
            + 10 * (d.month in (6, 7, 8))
            + rng.gauss(0, 4)
            + (shift_f if d.year >= shift_after else 0)
        )

    def tmin(d):
        return (
            55
            + 8 * (d.month in (6, 7, 8))
            + rng.gauss(0, 3)
            + (shift_f if d.year >= shift_after else 0)
        )

    return make_daily(date(1951, 1, 1), date(2000, 12, 31), tmax_f=tmax, tmin_f=tmin)


def test_baseline_near_ten_percent_and_shift_detected(cfg):
    daily = _series(1990, 8.0)
    annual = M.annual_metrics(daily, cfg)
    doy = M.doy_climatology(daily, cfg)
    ix = M.percentile_indices(daily, doy, annual, cfg)
    base = ix.filter((ix["year"] >= 1951) & (ix["year"] <= 1980))
    for c in ("tx90p", "tn90p", "tx10p", "tn10p"):
        m = base[c].mean()
        assert 8 <= m <= 14, (c, m)  # wide window, no bootstrap -> slightly above 10
    late = ix.filter(ix["year"] >= 1990)
    assert late["tn90p"].mean() > 40 and late["tx90p"].mean() > 35
    assert late["tn10p"].mean() < 1 and late["tx10p"].mean() < 1
    assert abs(late["dtr_c"].mean() - 20.5 / 1.8) < 1.0  # highs sit ~20–22 °F above lows


def test_incomplete_years_are_null(cfg):
    daily = _series(3000, 0)
    missing = {date(1975, m, d) for m in range(1, 6) for d in range(1, 15)}
    daily = daily.with_columns(
        tmax=pl.when(pl.col("date").is_in(list(missing))).then(None).otherwise(pl.col("tmax"))
    )
    annual = M.annual_metrics(daily, cfg)
    doy = M.doy_climatology(daily, cfg)
    ix = M.percentile_indices(daily, doy, annual, cfg)
    row = ix.filter(ix["year"] == 1975).row(0, named=True)
    assert row["tx90p"] is None and row["dtr_c"] is None and row["tn90p"] is not None
