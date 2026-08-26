#!/usr/bin/env bash
# Atomic deploy of the static site to dronesclub.
#
# Procedure (see CLAUDE.md): rsync site/build/ into a fresh timestamped release
# dir under /var/www/climate-releases/, swap the /var/www/climate-current symlink
# atomically (ln -s + mv -T), prune to the last KEEP releases. Never rsync --delete
# into the live root — mid-deploy hydration breaks.
#
# Usage: scripts/deploy.sh [--build] [--no-verify]
#   --build       run `npm run build` in site/ first; otherwise deploys site/build as-is
#   --no-verify   skip the live-URL check (first deploy, before DNS/TLS exist)

set -euo pipefail

# Serialize deploys (and fail loudly on overlap): a concurrent build clearing
# site/build/ mid-rsync can ship a half-copied release.
exec 9>/tmp/climate-deploy.lock
if ! flock -n 9; then
  echo "another deploy is running (lock /tmp/climate-deploy.lock); waiting…" >&2
  flock 9
fi

HOST=dronesclub
RELEASES=/var/www/climate-releases
CURRENT=/var/www/climate-current
KEEP=3
SITE_URL=https://climate.sorkinlabs.com

repo_root=$(cd "$(dirname "$0")/.." && pwd)
build_dir="$repo_root/site/build"

verify=1
for arg in "$@"; do
  case "$arg" in
    --build) echo "==> building site"; (cd "$repo_root/site" && npm run build) ;;
    --no-verify) verify=0 ;;
    *) echo "unknown option $arg" >&2; exit 2 ;;
  esac
done

[[ -f "$build_dir/index.html" ]] || {
  echo "error: $build_dir/index.html not found — run with --build or build the site first" >&2
  exit 1
}
[[ -f "$build_dir/data/index.json" ]] || {
  echo "error: $build_dir/data/index.json missing — run \`uv run clim export\` before building" >&2
  exit 1
}

ts=$(date -u +%Y%m%d-%H%M%S)
echo "==> deploying release $ts"

# The releases dir is root-owned; create the release dir via sudo, owned by the
# deploy user so plain rsync can write into it.
ssh "$HOST" "sudo install -d -o \$(whoami) -g \$(whoami) $RELEASES/$ts"
# --link-dest hardlinks files unchanged since the live release (station JSON
# mostly), so successive releases cost little disk or transfer.
prev=$(ssh "$HOST" "readlink $CURRENT" || true)
rsync -a ${prev:+--link-dest="$prev"} "$build_dir/" "$HOST:$RELEASES/$ts/"

echo "==> swapping symlink"
ssh "$HOST" "set -e
  sudo ln -sfn $RELEASES/$ts $CURRENT.new
  sudo mv -T $CURRENT.new $CURRENT
  echo \"   current -> \$(readlink $CURRENT)\"
  cd $RELEASES
  ls -1d 2*/ | sort | head -n -$KEEP | while read -r old; do
    echo \"   pruning \$old\"
    sudo rm -rf \"$RELEASES/\$old\"
  done"

live=$(ssh "$HOST" "readlink $CURRENT")
[[ "$live" == "$RELEASES/$ts" ]] || { echo "error: symlink points at $live, expected $RELEASES/$ts" >&2; exit 1; }
if [[ $verify == 0 ]]; then
  echo "==> deployed $ts to $HOST:$CURRENT (live-URL check skipped)"
  exit 0
fi
echo "==> verifying"
code=$(curl -sS -o /dev/null -w '%{http_code}' "$SITE_URL/")
[[ "$code" == 200 ]] || { echo "error: $SITE_URL/ returned HTTP $code" >&2; exit 1; }
want=$(python3 -c "import json;print(json.load(open('$build_dir/data/index.json'))['generated_at'])")
got=$(curl -sS "$SITE_URL/data/index.json?v=$ts" | python3 -c "import json,sys;print(json.load(sys.stdin)['generated_at'])")
[[ "$want" == "$got" ]] || { echo "error: live index.json generated_at=$got, expected $want" >&2; exit 1; }
echo "==> deployed $ts ($SITE_URL live, HTTP $code, data $got)"
