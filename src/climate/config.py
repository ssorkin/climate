"""Station regions (stations/*.yaml) and analysis rules (config/analysis.yaml).

These two files are the only places station lists, baselines and thresholds live.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

from climate.paths import CONFIG_PATH, STATIONS_DIR

STATION_ID_RE = re.compile(r"^US[CW]\d{8}$")


@dataclass(frozen=True)
class Station:
    id: str
    short: str
    ushcn: bool = False
    notable: tuple[dict, ...] = ()


@dataclass(frozen=True)
class Excluded:
    id: str
    short: str
    reason: str
    source: str
    source_note: str = ""


@dataclass(frozen=True)
class Region:
    id: str
    name: str
    center: tuple[float, float]
    zoom: float
    default_station: str
    stations: tuple[Station, ...]
    excluded: tuple[Excluded, ...] = field(default_factory=tuple)

    @property
    def station_ids(self) -> list[str]:
        return [s.id for s in self.stations]


class ConfigError(ValueError):
    pass


def _parse_region(path: Path) -> Region:
    raw = yaml.safe_load(path.read_text())
    stations = tuple(
        Station(
            id=s["id"],
            short=s["short"],
            ushcn=bool(s.get("ushcn", False)),
            notable=tuple(s.get("notable", []) or []),
        )
        for s in raw["stations"]
    )
    excluded = tuple(
        Excluded(
            id=e["id"],
            short=e["short"],
            reason=" ".join(e["reason"].split()),
            source=e["source"],
            source_note=e.get("source_note", ""),
        )
        for e in raw.get("excluded", []) or []
    )
    region = Region(
        id=raw["region"],
        name=raw["name"],
        center=tuple(raw["center"]),
        zoom=float(raw["zoom"]),
        default_station=raw["default_station"],
        stations=stations,
        excluded=excluded,
    )
    ids = region.station_ids
    if len(set(ids)) != len(ids):
        raise ConfigError(f"{path.name}: duplicate station ids")
    for sid in ids + [e.id for e in excluded]:
        if not STATION_ID_RE.match(sid):
            raise ConfigError(f"{path.name}: bad station id {sid!r}")
    if region.default_station not in ids:
        raise ConfigError(f"{path.name}: default_station {region.default_station} not in list")
    if set(ids) & {e.id for e in excluded}:
        raise ConfigError(f"{path.name}: a station is both active and excluded")
    for e in excluded:
        if not e.reason or not e.source:
            raise ConfigError(f"{path.name}: excluded {e.id} needs reason and source")
    return region


def load_regions(region: str = "all", stations_dir: Path = STATIONS_DIR) -> list[Region]:
    """Load one region (by id) or all regions found in stations/."""
    paths = sorted(stations_dir.glob("*.yaml"))
    regions = [_parse_region(p) for p in paths]
    if region != "all":
        regions = [r for r in regions if r.id == region]
        if not regions:
            raise ConfigError(f"no region {region!r} in {stations_dir}")
    return regions


def all_stations(regions: list[Region]) -> list[tuple[Region, Station]]:
    return [(r, s) for r in regions for s in r.stations]


@lru_cache(maxsize=1)
def load_analysis_config(path: Path = CONFIG_PATH) -> dict:
    cfg = yaml.safe_load(path.read_text())
    cfg["thresholds_f"] = {k: [int(v) for v in vs] for k, vs in cfg["thresholds_f"].items()}
    return cfg
