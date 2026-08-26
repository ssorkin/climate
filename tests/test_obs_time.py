from datetime import date

import polars as pl

from climate.analysis.obs_time import segments
from tests.conftest import make_daily


def test_segments_and_merge():
    a = make_daily(date(2000, 1, 1), date(2000, 6, 30), obs="1600")
    b = make_daily(date(2000, 7, 1), date(2000, 7, 5), obs="0800")  # 5-day flicker
    c = make_daily(date(2000, 7, 6), date(2000, 12, 31), obs="1600")
    d = make_daily(date(2001, 1, 1), date(2001, 12, 31), obs="0800")
    daily = pl.concat([a, b, c, d])
    raw = segments(daily)
    assert [s["hhmm"] for s in raw] == ["1600", "0800", "1600", "0800"]
    merged = segments(daily, min_days=30)
    assert [s["hhmm"] for s in merged] == ["1600", "0800"]
    assert merged[0]["to"] == date(2000, 12, 31) and merged[0].get("mixed")
    assert merged[1]["from"] == date(2001, 1, 1)
