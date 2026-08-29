# Analysis scripts (2026-08-29): California airports vs CIMIS heat waves

Exploratory scripts behind the statewide / siting follow-up to the LA heat-wave story. They read
`data/analysis/<id>/{meta.json,heatwaves.parquet}` written by `clim analyze --region ca` and
`clim cimis analyze`, and write intermediate JSON to `data/analysis/scratch/` (gitignored).

- `hw_fixed.py stations/ca.yaml` — then/now with the site's fixed windows (1951–80 vs last 30).
- `hw_summary.py <stations.yaml> [k] [from_year]` — first k vs last k complete summers + Theil–Sen
  trends, pooled with the hierarchical summer/station bootstrap (works for CIMIS via `summarize()`).
- `cimis_compare.py [CIMIS ids…]` — each CIMIS station paired with the airport within 40 km / 300 m
  sharing the most complete summers; first vs second half of the shared years; paired bootstrap.
- `ca_groups.py` — regional medians (SoCal basin, Central Valley, Bay/Coast, Desert, Mountain).

Run with `uv run python scripts/analysis/<script>` from the repo root after `mkdir -p data/analysis/scratch`.
