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
# Nightly: the curated LA region (26 files). The national set refreshes weekly (weekly-us.sh).
uv run clim acquire --region la --refresh
uv run clim ingest --region la
uv run clim check --strict
uv run clim analyze --region la
uv run clim export --region la
# Hourly layer for the LA airports (ISD-Lite updates daily; only the current year changes).
uv run clim hourly acquire --only 23174,23152,23130,23129,93110,03102,23119 --refresh
uv run clim hourly ingest --only 23174,23152,23130,23129,93110,03102,23119
uv run clim hourly analyze --only 23174,23152,23130,23129,93110,03102,23119
uv run clim hourly export
(cd site && npm run build)
scripts/deploy.sh
echo "==> $(date -u +%FT%TZ) done"
