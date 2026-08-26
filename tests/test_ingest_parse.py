import gzip

from climate.ingest.ghcnd import parse_station_csv

ROWS = """USC00046719,18930101,TMAX,244,,,6,
USC00046719,18930101,TMIN,89,,,6,
USC00046719,18930101,PRCP,0,,,6,
USC00046719,18930102,TMAX,272,,I,6,
USC00046719,18930102,SNOW,0,,,6,
USC00046719,20260728,TMAX,339,,,H,0800
"""


def test_parse_station_csv(tmp_path):
    p = tmp_path / "x.csv.gz"
    with gzip.open(p, "wt") as f:
        f.write(ROWS)
    df = parse_station_csv(p)
    assert df.height == 5  # SNOW dropped
    assert df.filter(df["element"] == "TMAX").height == 3
    flagged = df.filter(df["qflag"] != "")
    assert flagged.height == 1 and flagged["value"][0] == 272
    assert df.filter(df["obs_time"] == "0800").height == 1
    assert str(df["date"].min()) == "1893-01-01"
