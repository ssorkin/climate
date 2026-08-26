from datetime import date

import polars as pl

from climate.analysis import metrics as M
from tests.conftest import make_daily

TODAY = date(2026, 8, 26)


def test_month_needs_25_days(cfg):
    gone = {date(2000, 3, d) for d in range(1, 8)}  # 31 - 7 = 24 valid -> incomplete
    daily = make_daily(date(2000, 1, 1), date(2000, 12, 31), 95, 55, missing=gone)
    m = M.monthly_metrics(daily, cfg, TODAY)
    mar = m.filter(pl.col("month") == 3).row(0, named=True)
    feb = m.filter(pl.col("month") == 2).row(0, named=True)
    assert mar["days_valid_tmax"] == 24 and not mar["complete_tmax"] and mar["hot_95"] is None
    assert feb["days_valid_tmax"] == 29 and feb["complete_tmax"] and feb["hot_95"] == 29


def test_february_with_three_missing_is_complete(cfg):
    gone = {date(2001, 2, d) for d in (1, 2, 3)}  # 28 - 3 = 25
    daily = make_daily(date(2001, 1, 1), date(2001, 12, 31), 95, 55, missing=gone)
    feb = M.monthly_metrics(daily, cfg, TODAY).filter(pl.col("month") == 2).row(0, named=True)
    assert feb["complete_tmax"] and feb["hot_95"] == 25


def test_current_month_is_partial(cfg):
    daily = make_daily(date(2026, 1, 1), date(2026, 8, 20), 95, 55)
    m = M.monthly_metrics(daily, cfg, TODAY)
    aug = m.filter(pl.col("month") == 8).row(0, named=True)
    jul = m.filter(pl.col("month") == 7).row(0, named=True)
    assert aug["partial"] and not aug["complete_tmax"]
    assert not jul["partial"] and jul["hot_95"] == 31


def test_cold_season_spans_new_year(cfg):
    def frosty(d: date) -> float:
        return 30 if d.month in (12, 1) else 50

    daily = make_daily(date(1999, 7, 1), date(2002, 6, 30), 60, frosty)
    cs = M.cold_season_metrics(daily, cfg, TODAY)
    s2000 = cs.filter(pl.col("season") == 2000).row(0, named=True)
    assert s2000["complete_tmin"] and s2000["coldnight_32"] == 31 + 31
    assert s2000["coldest_night_tenths"] == -11 and s2000["coldest_night_date"] == date(1999, 12, 1)
    # season 2002 (Jul 2001 - Jun 2002) is complete; 2003 does not exist here
    assert cs["season"].to_list() == [2000, 2001, 2002]
