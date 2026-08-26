from datetime import date, timedelta

import polars as pl

from climate.analysis import metrics as M
from tests.conftest import make_daily

TODAY = date(2026, 8, 26)


def hot_summer(d: date) -> float:
    # 100°F every day of July, 80°F otherwise; nights 72°F in July else 55°F.
    return 100 if d.month == 7 else 80


def warm_july_nights(d: date) -> float:
    return 72 if d.month == 7 else 55


def test_counts_exact_on_complete_year(cfg):
    daily = make_daily(date(2000, 1, 1), date(2000, 12, 31), hot_summer, warm_july_nights)
    a = M.annual_metrics(daily, cfg, TODAY)
    row = a.row(0, named=True)
    assert row["days_valid_tmax"] == 366 and row["complete_tmax"] and not row["partial"]
    assert row["hot_95"] == 31 and row["hot_100"] == 31 and row["hot_105"] == 0
    assert row["warm_70"] == 31 and row["warm_65"] == 31 and row["warm_75"] == 0
    assert row["coldnight_32"] == 0
    assert row["hottest_tenths"] == 378 and row["hottest_date"] == date(2000, 7, 1)
    assert row["jja_hot_95"] == 31
    assert abs(row["tmax_mean_c"] - ((31 * 378 + 335 * 267) / 366 / 10)) < 0.01


def test_incomplete_year_is_null_never_zero(cfg):
    # 36 missing days in 2001 (365 - 36 = 329 < ceil(0.9*365) = 329?) -> exactly at the edge:
    # 329 valid is complete; 328 is not.
    gone = {date(2001, 1, 1) + timedelta(days=i) for i in range(37)}
    daily = make_daily(date(2001, 1, 1), date(2001, 12, 31), hot_summer, 55, missing=gone)
    a = M.annual_metrics(daily, cfg, TODAY)
    row = a.row(0, named=True)
    assert row["days_valid_tmax"] == 328
    assert not row["complete_tmax"]
    assert row["hot_95"] is None and row["tmax_mean_c"] is None and row["hottest_tenths"] is None

    gone = {date(2001, 1, 1) + timedelta(days=i) for i in range(36)}
    daily = make_daily(date(2001, 1, 1), date(2001, 12, 31), hot_summer, 55, missing=gone)
    row = M.annual_metrics(daily, cfg, TODAY).row(0, named=True)
    assert row["days_valid_tmax"] == 329 and row["complete_tmax"]
    assert row["hot_95"] == 31


def test_elements_complete_independently(cfg):
    gone = {date(2002, 3, 1) + timedelta(days=i) for i in range(60)}
    daily = make_daily(date(2002, 1, 1), date(2002, 12, 31), 80, 72, missing_tmin=gone)
    row = M.annual_metrics(daily, cfg, TODAY).row(0, named=True)
    assert row["complete_tmax"] and not row["complete_tmin"]
    assert row["hot_90"] == 0 and row["warm_70"] is None


def test_current_year_is_partial(cfg):
    daily = make_daily(date(2026, 1, 1), date(2026, 8, 20), 100, 72)
    row = M.annual_metrics(daily, cfg, TODAY).row(0, named=True)
    assert row["partial"] and not row["complete_tmax"] and row["hot_95"] is None


def test_flagged_values_are_not_data(cfg):
    q = {date(2003, 7, d): "I" for d in range(1, 11)}
    daily = make_daily(date(2003, 1, 1), date(2003, 12, 31), hot_summer, 55, qflags=q)
    row = M.annual_metrics(daily, cfg, TODAY).row(0, named=True)
    assert row["days_valid_tmax"] == 355 and row["hot_95"] == 21


def test_decades_and_partial_decade(cfg):
    daily = make_daily(date(1990, 1, 1), date(2005, 12, 31), hot_summer, 55)
    a = M.annual_metrics(daily, cfg, TODAY)
    dec = M.decade_means(a, cfg)
    d90 = dec.filter(pl.col("decade") == 1990).row(0, named=True)
    d00 = dec.filter(pl.col("decade") == 2000).row(0, named=True)
    assert d90["n_years_tmax"] == 10 and d90["hot_95"] == 31 and not d90["partial"]
    assert d00["n_years_tmax"] == 6 and d00["hot_95"] == 31 and d00["partial"]
    # fewer than decade_min_years complete years -> null
    daily = make_daily(date(1998, 1, 1), date(2001, 12, 31), hot_summer, 55)
    dec = M.decade_means(M.annual_metrics(daily, cfg, TODAY), cfg)
    assert dec.filter(pl.col("decade") == 1990).row(0, named=True)["hot_95"] is None
