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
  lows separately); a month needs {ix.completeness.monthly_min_days} days. Anything less is never shown as a low count: the chart shows a hollow "at least N" bar (the count over the days
  that were observed is a true lower bound) and the station page lists the missing dates. A missing January day can't
  hide a 95°F afternoon at Newport Beach, though — so for each threshold we also ask how often each missing date crosses
  it at that station (that calendar date ±3 days, over all years). If the missing days together are expected to add
  fewer than half a day to the count, and at least half the period was observed, the count is treated as exact and the
  year counts normally; the tooltip still says which days were missing. The current
  year is always "so far": it appears hatched and is compared with other years only over the same calendar window
  ("this summer through August 23" against every other summer through August 23). Cooperative-observer stations can
  report weeks late, so a station's latest date is always shown.
</p>

<h2>Baseline, decades, trends</h2>
<p>
  "Then" is {ix.baseline.start}–{ix.baseline.end}: every station has a complete record over it, it is the reference period used by
  NASA GISS and Berkeley Earth, and it predates most of the local warming. Decade averages use complete years only
  (at least {ix.completeness.decade_min_years}); the current decade is marked "so far". Trend labels are Theil–Sen slopes
  (a median-based fit that is robust to single extreme years) over complete years since {ix.baseline.start}; a slope is shown only
  when its 95% confidence interval excludes zero (Kendall p &lt; 0.05), otherwise the chart says "no clear trend". Count series that
  are almost all zeros — 95°F days at a beach station, frost nights at the coast — get no trend at all, because a median slope through
  zeros is meaningless. Daily
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

<h2 id="homogenization">Site and instrument changes — the Pasadena case</h2>
<p>
  A century-long station record is never one instrument in one spot. NOAA's station history for Pasadena (COOP 046719, a
  ground-level lawn site near Pasadena City Hall) records a switch to automated equipment around 2003–04, an upgrade to an
  electronic MMTS sensor with a 12-foot relocation and a change of reading time from 4 pm to 8 am in August 2015, and sensor
  replacements after that. NOAA's homogenization of the station's monthly record (USHCN v2.5, which compares each station with
  its neighbors) detects steps in exactly those years: nights jumped about 2.5°F relative to neighbors in 2003, dropped about
  3°F in 2015–16, and rose about 2.5°F again in 2020–21; daytime highs before 2015 were biased warm by the 4 pm reading time.
</p>
<p>
  Does that explain Pasadena's rise? No — it changes the shape, not the conclusion. Applying NOAA's adjustments and recounting,
  Pasadena's warm nights go from about 5 per year in 1951–1980 to about 18 in the last decade (raw: 3 → 15), and its 95°F days
  from about 11 to about 41 (raw: 20 → 42) — the homogenized rise in hot days is <i>steeper</i>, because the afternoon reading
  time inflated the old highs. Pasadena's night warming is also matched, in kind if not in size, at every other long-record
  station in the region, including airports with automated instruments. For the three USHCN stations here (Pasadena, Newport
  Beach, Tustin) each station page lists the detected changes and the raw-vs-homogenized counts; for the others no
  homogenized version exists, and we show the raw record with its observation-time history.
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
