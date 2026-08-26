from datetime import date

import polars as pl

from climate.analysis import metrics as M
from tests.conftest import make_daily


def test_doy366_slots():
    assert M.doy366(1, 1) == 1 and M.doy366(2, 29) == 60 and M.doy366(3, 1) == 61
    assert M.doy366(12, 31) == 366


def test_climatology_bands(cfg):
    # Baseline 1951-1980, constant 80/55 -> all percentiles equal
    daily = make_daily(date(1951, 1, 1), date(1980, 12, 31), 80, 55)
    clim = M.doy_climatology(daily, cfg)
    assert clim.height == 366
    assert clim["tmax_p50"].unique().to_list() == [26.7]
    assert clim["tmin_p10"].unique().to_list() == [12.8]
    assert clim.filter(pl.col("doy") == 60)["rec_high_tenths"][0] == 267
