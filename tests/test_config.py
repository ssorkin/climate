import pytest

from climate.config import ConfigError, load_analysis_config, load_regions


def test_la_region_loads():
    regs = load_regions("la")
    assert len(regs) == 1
    la = regs[0]
    assert la.default_station in la.station_ids
    assert all(e.reason and e.source for e in la.excluded)
    assert "USW00093134" in {e.id for e in la.excluded}
    assert "USW00093134" not in la.station_ids


def test_unknown_region():
    with pytest.raises(ConfigError):
        load_regions("atlantis")


def test_analysis_config_shape():
    cfg = load_analysis_config()
    assert cfg["baseline"]["start"] < cfg["baseline"]["end"]
    assert 95 in cfg["thresholds_f"]["hot_days"] and 70 in cfg["thresholds_f"]["warm_nights"]
    assert 0 < cfg["completeness"]["annual_min_frac"] <= 1
