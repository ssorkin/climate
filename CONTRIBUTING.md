# Contributing

Everything here — pipeline, site, and data-quality findings — is open, and every
number on the site must be reproducible from this repository.

## Setup

```bash
git clone https://github.com/ssorkin/climate
cd climate
uv sync --extra dev          # Python 3.12+ pipeline (managed by uv)
cd site && npm install       # SvelteKit site (Node 20+)
```

Pipeline (repo root): `uv run clim acquire | ingest | check | analyze | export`,
`uv run pytest`, `uv run ruff check src tests`.
Site (`site/`): `npm run dev`, `npm run build`. The site is fully static; all data
comes from the JSON that `clim export` writes to `site/static/data/`.

## Adding stations or regions

Add a `stations/<region>.yaml` (see `stations/la.yaml`). Only the GHCN id, a short
display name and optional flags go there — names and coordinates come from NOAA's
`ghcnd-stations.txt` at ingest. Pick stations with long, still-active TMAX/TMIN
records (`ghcnd-inventory.txt`) and stable siting; document exclusions with a source.

## Rules

See `CLAUDE.md` for the data-integrity rules (they apply to humans too).
