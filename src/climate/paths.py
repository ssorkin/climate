"""Canonical repository paths."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PARQUET_DIR = DATA_DIR / "parquet"
ANALYSIS_DIR = DATA_DIR / "analysis"
DUCKDB_PATH = DATA_DIR / "climate.duckdb"
MANIFEST_DIR = REPO_ROOT / "manifests"
KNOWN_ISSUES_DIR = REPO_ROOT / "known_issues"
STATIONS_DIR = REPO_ROOT / "stations"
CONFIG_PATH = REPO_ROOT / "config" / "analysis.yaml"
SITE_DATA_DIR = REPO_ROOT / "site" / "static" / "data"
