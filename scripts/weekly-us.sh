#!/usr/bin/env bash
# Weekly refresh of every US station (~6,400 files, ~4.5 GB), then a full rebuild + deploy.
set -euo pipefail
exec 8>/tmp/climate-nightly.lock
flock 8

repo_root=$(cd "$(dirname "$0")/.." && pwd)
cd "$repo_root"
export PATH="$HOME/.local/bin:$PATH"

echo "==> $(date -u +%FT%TZ) weekly US refresh"
uv run clim acquire --refresh
uv run clim ingest
uv run clim check --strict
uv run clim analyze
uv run clim export
(cd site && npm run build)
scripts/deploy.sh
echo "==> $(date -u +%FT%TZ) done"
