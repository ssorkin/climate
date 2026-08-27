# climate

Long-term weather-station records made explorable: how many days a year reach 95°F, how
many nights never cool below 70°F, how often it frosts, how many hours the heat lasts — at
each station, every year since the 1940s, down to the hourly readings. A curated Los
Angeles story, and a national map of every US station with 20+ years of hourly temperature
records in NOAA's GHCNh (about 2,000 of them).

**Every number on the site can be reproduced from public data.** The download
scripts, the aggregation rules, the data-quality findings, and the website are all
in this repository.

Website: [climate.sorkinlabs.com](https://climate.sorkinlabs.com)

## What this project does

- **Acquires** the hourly records of long-running stations from NOAA's
  [GHCNh](https://www.ncei.noaa.gov/products/global-historical-climatology-network-hourly)
  archive (one Parquet file per station-year), recording the URL and SHA-256 of every
  file in `manifests/`.
- **Ingests** them into Parquet, applying NOAA's quality codes, converting to local time,
  and deriving each day's high and low from the hourly readings.
- **Checks** the data — completeness by year, gaps, flagged values, observation-time
  changes, freshness — and publishes the findings in `DATA_QUALITY.md`.
- **Analyzes** each station: for every day, the percentile rank of its high and low within
  the station's own 1951–1980 readings for that time of year (the year × day heatmaps and
  the "typical night / typical day" numbers); the standard climate-extremes indices TX90p / TN90p /
  TX10p / TN10p (share of days and nights beyond the station's own 1951–1980
  calendar-day percentiles), warm-season mean high/low anomalies, the diurnal range,
  plus annual and monthly counts of days and nights past thresholds, frost nights,
  records and Theil–Sen trends.
- **Exports** compact JSON that the fully static SvelteKit site loads per station.

## Principles

1. **"How unusual is this temperature for this date?"** Every reading is ranked against
   the same station's 1951–1980 readings for the same time of year — nonparametric, no
   cutoffs, comparable between LAX and the desert. The answer for Los Angeles is
   asymmetric: a typical night now sits around the 65th percentile of the old climate,
   a typical day around the 55th; nights are warming much faster than days. Counts of
   ≥95°F days and ≥70°F nights stay on the site as the lived-experience layer.
2. **Stations, not regions.** Each chart is what one thermometer recorded at one
   place. We don't average stations into a "Los Angeles" number, and we don't chart
   the famous downtown record because its instruments moved eight times (see
   `stations/la.yaml` and the Methods page).
3. **Missing means missing.** A year with fewer than 90% of its days observed is
   shown as incomplete, never as a low count. The current year is "so far".
4. **Reproducibility.** Raw data is not committed; `manifests/` records exactly
   which NOAA files were used, and the pipeline rebuilds everything from them.

## Quick start

```bash
uv sync                        # install the pipeline (Python 3.12+, managed by uv)
uv run clim acquire --region la   # download the LA stations' GHCNh files (~1,600 station-years), record checksums
#   (`clim stations --tier hourly` regenerates stations/hourly.yaml; `clim acquire` with no region fetches all ~2,000 stations, ~40 GB)
uv run clim ingest --region la    # Parquet + DuckDB views
uv run clim check                 # data-quality report -> DATA_QUALITY.md
uv run clim analyze --region la   # per-station metrics
uv run clim export --region la    # site/static/data/ JSON
cd site && npm install && npm run dev
```

## Layout

| Path | Contents |
|---|---|
| `src/climate/` | pipeline: `acquire/`, `ingest/`, `quality/`, `analysis/`, `cli.py` |
| `stations/` | `hourly.yaml` (generated master list, GHCNh), `la.yaml` (curated), `us.yaml` (generated) |
| `config/analysis.yaml` | baseline period, thresholds, completeness rules |
| `manifests/` | provenance: URL, sha256, timestamps for every NOAA file |
| `known_issues/` | registry of documented problems and caveats in the source data |
| `site/` | the website (SvelteKit, fully static) |
| `scripts/` | `deploy.sh` (atomic static deploy), `nightly.sh` (refresh + deploy) |
| `DATA_QUALITY.md` | generated data-quality report (`clim check`) |

## Data and licensing

Code is MIT-licensed. Station data is NOAA GHCN-Daily, a US-government work in the
public domain; please cite NOAA NCEI (Menne et al., 2012) if you reuse it.
