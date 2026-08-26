from datetime import date

import polars as pl

from climate.analysis import metrics as M
from tests.conftest import make_daily

TODAY = date(2026, 8, 26)


def test_records_need_prior_years(cfg):
    # Each year is 1°F hotter than the last, every day.
    def tmax(d: date) -> float:
        return 60 + (d.year - 1950)

    daily = make_daily(date(1950, 1, 1), date(1985, 12, 31), tmax, 40)
    rec = M.records(daily, cfg)
    by_year = (
        rec.group_by(pl.col("date").dt.year().alias("y")).agg(pl.col("record_high").sum()).sort("y")
    )
    counts = dict(by_year.iter_rows())
    assert counts[1979] == 0  # only 29 prior years
    assert counts[1980] == 365  # 30 prior years; Feb 29 has only 7 prior leap years
    assert counts[1985] == 365


def test_ties_are_not_records(cfg):
    def tmax(d: date) -> float:
        return 70 + (d.year - 1900) if d.year < 1935 else 104  # 1934 = 104; 1935 ties

    daily = make_daily(date(1900, 1, 1), date(1936, 12, 31), tmax, 40)
    rec = M.records(daily, cfg)
    y35 = rec.filter(pl.col("date").dt.year() == 1935)
    assert y35["record_high"].sum() == 0 and y35["record_high_tie"].sum() == 365
