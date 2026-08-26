<script>
  let { data } = $props();
  let ix = $derived(data.index);
  let coop = $derived(ix.stations.filter((s) => s.kind === 'coop'));
</script>

<svelte:head>
  <title>Methods · climate.sorkinlabs</title>
</svelte:head>

<h1>Methods and data</h1>
<p class="lede">Everything on this site is computed from NOAA's raw daily station files by an open pipeline. This page says exactly what was done — and what was left out.</p>

<h2>Source</h2>
<p>
  Daily maximum and minimum temperatures come from NOAA's <a href="https://www.ncei.noaa.gov/products/land-based-station/global-historical-climatology-network-daily">Global Historical Climatology Network – Daily</a>
  (GHCN-D), version {ix.ghcnd_version}, the same archive behind NOAA's own climate tools. We use the per-station files
  (<code>by_station/&lt;ID&gt;.csv.gz</code>) refreshed nightly, and keep only values that pass NOAA's quality checks —
  flagged values are shown as "withheld" in the raw tables and excluded from every count. The URL and SHA-256 of every
  file used is recorded in the repository's <code>manifests/</code>.
</p>

<h2>Stations</h2>
<p>
  We chose {ix.stations.length} {ix.regions[0].name} stations with long, still-active daily records and stable ground-level siting:
  {#each ix.stations as s, i (s.id)}{s.short} ({s.first_year}–){i < ix.stations.length - 1 ? ', ' : '.'}{/each}
  Two candidates were dropped for incompleteness (Big Tujunga Dam, Van Nuys Airport). Names and coordinates come from NOAA's station list.
</p>

<h2 id="civic-center">Why the famous downtown Los Angeles record isn't here</h2>
{#each ix.excluded as e (e.id)}
  <p>
    {e.reason} (<a href={e.source}>{e.source_note || 'source'}</a>.) The same memorandum names Pasadena, Long Beach and Burbank
    among the "first-rate, stable weather records" in the region, which is why those anchor this site. Downtown's
    current ground-level site at USC (since 1999) is excellent, but a chart of "Los Angeles since 1877" would be
    stitching together eight different thermometers on eight different rooftops.
  </p>
{/each}

<h2>What counts as a hot day or a warm night</h2>
<p>
  A <b>hot day</b> is a day whose maximum reached the threshold; a <b>warm night</b> is a day whose minimum never fell
  below it. Thresholds are whole °F because that is what the observer wrote down. NOAA stores readings in tenths of
  a degree Celsius, and 90°F is stored as 32.2°C — which converts back to 89.96°F. We recover the observer's whole
  degree exactly (<code>floor(t × 0.18 + 32.5)</code>) before testing a threshold, so 90°F days are 90°F days.
  Standard thresholds: highs ≥ {ix.thresholds_f.hot_days.join('/')}°F, lows ≥ {ix.thresholds_f.warm_nights.join('/')}°F,
  highs ≤ {ix.thresholds_f.cold_days.join('/')}°F, lows ≤ {ix.thresholds_f.cold_nights.join('/')}°F. Any other whole-°F threshold is
  computed live in your browser from the same daily data, with the same rules.
</p>

<h2>Missing data</h2>
<p>
  A year is counted only if at least {Math.round(ix.completeness.annual_min_frac * 100)}% of its days were observed (for highs and
  lows separately); a month needs {ix.completeness.monthly_min_days} days. Anything less is shown as a gap, never as a low count. The current
  year is always "so far": it appears hatched and is compared with other years only over the same calendar window
  ("this summer through August 23" against every other summer through August 23). Cooperative-observer stations can
  report weeks late, so a station's latest date is always shown.
</p>

<h2>Baseline, decades, trends</h2>
<p>
  "Then" is {ix.baseline.start}–{ix.baseline.end}: every station has a complete record over it, it is the reference period used by
  NASA GISS and Berkeley Earth, and it predates most of the local warming. Decade averages use complete years only
  (at least {ix.completeness.decade_min_years}); the current decade is marked "so far". Trend lines are Theil–Sen slopes
  (a median-based fit that is robust to single extreme years) over complete years since {ix.baseline.start}. Daily
  "typical range" bands are the 10th–90th percentile of the baseline years for each calendar date (±{ix.completeness.doy_window_days ?? 7} days).
  A daily record requires at least {ix.completeness.record_min_prior_years} prior years of data for that date, so a record set in 1895 over two prior years doesn't count.
</p>

<h2>Observation time</h2>
<p>
  {coop.length} of the stations are cooperative-observer stations (NOAA ids starting with USC): a volunteer reads a max/min
  thermometer once a day — typically at 8 am or 4 pm — and the 24-hour extremes are logged on the reading date. A high
  logged at 8 am mostly happened the previous afternoon. We never shift or adjust readings; the daily explorer shows
  the observation time and notes the offset. Monthly and yearly counts are essentially unaffected. Airport stations
  (USW) use automated instruments and calendar days.
</p>

<h2>What these charts can and can't say</h2>
<p>
  Each chart is one thermometer at one place. Station surroundings change over a century — pavement, buildings,
  irrigation, instrument upgrades — and that shows up in the record alongside regional climate change; we don't try to
  separate the two, and we don't average stations into a "Los Angeles" number. That the same shift in warm nights
  appears at a beach, a mountain, a desert town and a college campus is the reader's evidence, not ours. Cold-season
  metrics (frost nights) use July–June seasons so a winter is never split across two years.
</p>

<h2>Reproduce it</h2>
<p>
  The pipeline (<code>clim acquire → ingest → check → analyze → export</code>), the data-quality report, the station list and every
  rule above live at <a href="https://github.com/ssorkin/climate">github.com/ssorkin/climate</a> (MIT). The <a href="/data">Data</a> page links every
  file the site loads.
</p>
