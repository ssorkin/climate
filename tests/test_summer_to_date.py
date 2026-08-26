from datetime import date

import polars as pl

from climate.analysis import metrics as M
from tests.conftest import make_daily


def test_same_window_every_year(cfg):
    def tmax(d: date) -> float:
        return 100 if d.year == 2026 and d.month == 6 else 85

    daily = make_daily(date(2000, 1, 1), date(2026, 7, 15), tmax, 60)
    s = M.summer_to_date(daily, cfg, date(2026, 8, 26))
    assert s["ref_year"] == 2026 and s["through"] == date(2026, 7, 15) and s["window_days"] == 45
    t = s["table"]
    cur = t.filter(pl.col("year") == 2026).row(0, named=True)
    assert cur["days_valid_tmax"] == 45 and cur["rank_tmax"] == 1 and cur["hot_95"] == 30
    assert t.filter(pl.col("year") == 2010).row(0, named=True)["rank_tmax"] == 2
    assert t.filter(pl.col("year") == 2010).row(0, named=True)["days_valid_tmax"] == 45


def test_sparse_current_summer_is_not_ranked(cfg):
    gone = {date(2026, 6, d) for d in range(1, 25)}
    daily = make_daily(date(2000, 1, 1), date(2026, 7, 15), 85, 60, missing=gone)
    t = M.summer_to_date(daily, cfg, date(2026, 8, 26))["table"]
    cur = t.filter(pl.col("year") == 2026).row(0, named=True)
    assert cur["tmax_mean_c"] is None and cur["rank_tmax"] is None


def test_before_summer_uses_last_full_summer(cfg):
    daily = make_daily(date(2000, 1, 1), date(2026, 3, 1), 85, 60)
    s = M.summer_to_date(daily, cfg, date(2026, 3, 2))
    assert s["ref_year"] == 2025 and s["through"] == date(2025, 8, 31) and s["window_days"] == 92
