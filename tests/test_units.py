import polars as pl

from climate.analysis.metrics import f_whole, f_whole_expr
from tests.conftest import noaa_tenths


def test_f_whole_round_trips_every_whole_degree():
    for f in range(-40, 131):
        assert f_whole(noaa_tenths(f)) == f, f


def test_f_whole_known_traps():
    # 90°F is stored as 322 tenths = 89.96°F; a float compare would miss it.
    assert noaa_tenths(90) == 322
    assert 322 * 0.18 + 32 < 90
    assert f_whole(322) == 90
    assert f_whole(0) == 32
    assert f_whole(-178) == 0


def test_expr_matches_python():
    t = list(range(-500, 600))
    df = pl.DataFrame({"t": t}, schema={"t": pl.Int32})
    got = df.select(f_whole_expr(pl.col("t")))["t"].to_list()
    assert got == [f_whole(x) for x in t]
