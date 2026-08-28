#!/usr/bin/env bash
# Nightly refresh: pull updated NOAA files, rebuild everything, deploy.
# Fails closed: any failing stage (including `clim check --strict` anomalies)
# leaves the previous release live. Does not commit — manifests/ and
# DATA_QUALITY.md change on disk; commit them when convenient.
#
# Usage: scripts/nightly.sh   (run by contrib/systemd/climate-nightly.timer)

set -euo pipefail
exec 8>/tmp/climate-nightly.lock
flock -n 8 || { echo "nightly already running" >&2; exit 0; }

repo_root=$(cd "$(dirname "$0")/.." && pwd)
cd "$repo_root"
export PATH="$HOME/.local/bin:$PATH"

echo "==> $(date -u +%FT%TZ) nightly refresh"
# Nightly: the curated LA region (GHCNh hourly files for the current year). The national set refreshes weekly.
uv run clim acquire --region la --refresh
uv run clim ingest --region la
uv run clim check --strict
uv run clim analyze --region la
uv run clim export --region la
uv run python scripts/og_card.py || echo "og card not regenerated" >&2
