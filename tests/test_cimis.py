"""CIMIS tier: JSON parsing, QC handling, the hour convention and the shared day rule."""

from datetime import date, timedelta

import polars as pl

from climate import cimis


def rec(d: str, hh: int, temp: float | None, qc: str = " ") -> dict:
    return {
        "Date": d,
        "Hour": f"{hh:02d}00",
        "Station": "2",
        "HlyAirTmp": {"Value": None if temp is None else str(temp), "Qc": qc, "Unit": "(C)"},
        "HlyDewPnt": {"Value": "10.0", "Qc": " ", "Unit": "(C)"},
        "HlyRelHum": {"Value": "47", "Qc": " ", "Unit": "(%)"},
    }


def test_parse_hourly_places_hour_ending_reading_mid_hour_in_pst():
    df = cimis.parse_hourly([rec("2024-07-01", 1, 22.5), rec("2024-07-01", 24, 30.0)])
    assert df["h"].to_list() == [0.5, 23.5]
    assert df["hour"].to_list() == [0, 23]
    assert df["date"].to_list() == [date(2024, 7, 1)] * 2
    assert df["temp"].to_list() == [225, 300]
    assert df["rh"].to_list() == [47, 47]
    # 00:30 PST = 08:30 UTC
    assert df["ts_utc"][0].hour == 8 and df["ts_utc"][0].minute == 30


def test_qc_flags_keep_y_drop_severe_and_fills():
    df = cimis.parse_hourly(
        [
            rec("2024-07-01", 1, 40.0, "Y"),
            rec("2024-07-01", 2, 40.0, "R"),
            rec("2024-07-01", 3, 40.0, "S"),
            rec("2024-07-01", 4, None, "M"),
            rec("2024-07-01", 5, 20.0, "A"),
        ]
    )
    assert df["temp"].to_list() == [400, None, None, None, None]


def test_chunks_cover_the_span_without_overlap():
    c = cimis.chunks(date(2020, 1, 1), date(2020, 12, 31), 209)
    assert c[0] == (date(2020, 1, 1), date(2020, 7, 27))
    assert c[-1][1] == date(2020, 12, 31)
    assert all(c[i + 1][0] == c[i][1] + timedelta(days=1) for i in range(len(c) - 1))
    assert sum((e - s).days + 1 for s, e in c) == 366


def test_derive_days_applies_the_ghcnh_rule(tmp_path, monkeypatch):
    from climate.hourly import ingest as hi
    from climate.ingest import store

    monkeypatch.setattr(store, "PARQUET_DIR", tmp_path)
    monkeypatch.setattr(hi, "daily_path", lambda sid: tmp_path / sid / "data.parquet")
    monkeypatch.setattr(hi, "daily_meta_path", lambda sid: tmp_path / sid / "meta.parquet")
    full = [rec("2024-07-01", h, 20 + h / 2) for h in range(1, 25)]
    gappy = [rec("2024-07-02", h, 20.0) for h in (1, 2, 3, 10, 11, 12, 13, 22, 23, 24)]
    df = cimis.parse_hourly(full + gappy)
    day, good = hi.derive_days(df.select("date", "h", "temp"), "CIMIS002")
    assert day["complete"].to_list() == [True, False]
    assert good["tmax"][0] == 320 and good["tmin"][0] == 205
    long = pl.read_parquet(tmp_path / "CIMIS002" / "data.parquet")
    assert long.height == 2 and set(long["element"]) == {"TMAX", "TMIN"}
