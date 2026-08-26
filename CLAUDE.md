# climate — project conventions

Open-source pipeline + static site for long-term NOAA GHCN-Daily station records
(Los Angeles area first). Plan of record: `acquire → ingest → check → analyze → export`
in Python, fully static SvelteKit site at climate.sorkinlabs.com.

## Commands

- `uv sync` — install; `uv run clim --help` — pipeline CLI (`acquire [--refresh]`,
  `ingest`, `check [--strict]`, `analyze`, `export`; all take `--region la|all`)
- `uv run pytest` — tests; `uv run ruff check src tests` — lint
- Site: `cd site && npm run dev` / `npm run build` (static; data from `clim export`)
- Deploy (atomic): `scripts/deploy.sh [--build]` — rsync `site/build/` to dronesclub
  `/var/www/climate-releases/<ts>/`, swap symlink `/var/www/climate-current` via
  `ln -s` + `mv -T`, prune to last 3. NEVER `rsync --delete` into the live root.
- Nightly refresh: `scripts/nightly.sh` (acquire --refresh → … → export → build →
  deploy; `check --strict` blocks the deploy on anomalies).

## Hard rules (data integrity)

- **Only rows with an empty QFLAG are data.** Flagged rows stay in Parquet and are
  counted in the DQ report, but never enter any aggregate.
- **Missing days are null, never 0.** A year counts only with ≥ 90% valid days *per
  element* (TMAX and TMIN separately); a month with ≥ 25. Incomplete periods export
  as `null`; the current year is `partial` and compared only in a same-window
  "so far" block — otherwise a data lag looks like a cool year.
- **Thresholds use the whole-°F round-trip** (`f_whole`: `floor(tenths*0.18+32+0.5)`),
  identically in Python and JS. Observers record whole °F; NOAA stores tenths °C, so
  90°F is stored as 322 → 89.96 and a naive float compare misses it.
- **Observation times are never shifted**, always displayed. COOP stations read at
  0800/1600 and log on the reading date; the site says so rather than adjusting.
- **Civic Center (USW00093134) is excluded** and the site explains why (TM-261).
  Exclusions live in `stations/*.yaml` with a `reason` and `source`.
- Station lists live only in `stations/*.yaml`; baseline, thresholds and completeness
  rules only in `config/analysis.yaml`, echoed into every export. No duplicates in JS.
- **Charts show the raw record.** NOAA's USHCN homogenization (3 stations) is used only to
  mark detected site/instrument changes and to show an *estimated* homogenized count next
  to the raw one — never to replace it.
- Data problems go in `known_issues/` and the DQ report — never silently patched.
- `data/` is gitignored; provenance lives in `manifests/` (URL, sha256, dates).

## Style

- Python 3.12+, ruff (line length 100), typer CLI, polars for ingest, DuckDB views over
  Parquet, pure-function metrics in `analysis/metrics.py` with tests.
- Site: Svelte 5 runes, plain JS, inline-SVG charts in scoped-style components, °F
  default with °C toggle, direct labels over legends, sequential palettes for
  magnitudes and diverging only for anomalies.
- Copy describes what was observed *at this station*; no regional-climate or causal
  claims, and the siting/urbanization caveat stays on the Methods page.
