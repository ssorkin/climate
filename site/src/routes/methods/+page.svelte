<script>
  let { data } = $props();
  let ix = $derived(data.index);
  let coop = $derived(ix.stations.filter((s) => s.kind === 'coop'));
  let reg = $derived(data.regional);
  const EVAL_LABELS = { hot95: 'Days ≥ 95°F', hot100: 'Days ≥ 100°F', warm65: 'Nights ≥ 65°F', warm70: 'Nights ≥ 70°F', frost32: 'Frost nights' };
</script>

<svelte:head>
  <title>Methods · climate.sorkinlabs</title>
</svelte:head>

<h1>Methods and data</h1>
<p class="lede">Everything on this site is computed from NOAA's hourly station files by an open pipeline. This page says exactly what was done — and what was left out.</p>

<h2>Source</h2>
<p>
  Every number comes from NOAA's <a href="https://www.ncei.noaa.gov/products/global-historical-climatology-network-hourly">Global
  Historical Climatology Network – hourly</a> (GHCNh, version 1.1), the archive that replaced the Integrated Surface Database:
  hourly (in early decades sometimes 3-hourly) temperature and dew point from airports and other stations, with NOAA's quality
  checks applied after all sources are merged. We use the per-station, per-year Parquet files and keep only readings whose quality
  code passed; the URL and SHA-256 of every file is recorded in the repository's <code>manifests/</code>. Readings are converted
  to each station's local time. Earlier versions of this site used the daily max/min network (GHCN-Daily, mostly volunteer
  cooperative observers); that source has been retired here because its stations came with once-a-day observation-time
  quirks, undocumented moves, and gaps — though it still serves as a cross-check where both exist.
</p>

<h2>From hourly readings to a day's high and low</h2>
<p>
  A day's high and low are the highest and lowest readings among that local day's observations. A day counts only when it has at
  least 8 readings, no gap longer than 3 hours, a first reading by 3 am and a last after 9 pm — so 3-hourly synoptic years count,
  hourly years count, and a day with a 6-hour outage does not; small airports that don't observe overnight get no day counts at all.
  Because readings are samples, a day's true peak usually falls between them: compared with a max/min thermometer at the same
  airports, the hourly high reads about 0.5°C (0.9°F) low and the hourly low about 0.35°C high, and this gap has been steady
  since the 1940s — so counts are comparable across decades, but a "95°F day" here means a 95°F <i>reading</i>. Station pages
  that also have the retired daily record show the measured gap.
</p>

<h2>Stations</h2>
<p>
  The Los Angeles set is every station in the basin and its valleys with 20+ hourly years: {ix.stations.length} stations with
  usable day records, the oldest airports from 1940 (LAX, Long Beach, March Field) and 1943 (Burbank, Ontario, Van Nuys),
  closed ones included. The <a href="/us">national map</a> is not curated: it is every US station in GHCNh with 20+ hourly years
  since 1940 that actually reports temperature (verified station by station) —
  {ix.regions.find((r) => r.id === 'us')?.n_stations?.toLocaleString() ?? 'about 2,000'} of them — with the same rules.
  A year counts as "hourly" when it holds at least 2,700 observations. Station moves and instrument changes are still common
  in these records (the 1990s switch to automated ASOS sensors above all); look for agreement among neighbors.
</p>

<h2 id="civic-center">A note on downtown Los Angeles</h2>
<p>
  The famous "Los Angeles" record — downtown, since 1877 — was produced from eight different rooftop and street sites before
  moving to ground level at USC in 1999 (<a href="https://www.weather.gov/media/wrh/online_publications/TMs/TM-261.pdf">NWS TM-261</a>).
  Its hourly record begins with the USC site in 1999, and that is what appears here as Downtown LA (USC).
</p>

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

<h2 id="heatwaves">Heat waves</h2>
<p>
  The front page opens on heat waves because the question is simple and the answer is not what people expect. A
  <b>heat wave</b> is {ix.heat_waves?.min_days ?? 3} or more consecutive days whose high reaches the station's own
  {ix.heat_waves?.percentile ?? 95}th percentile of May–October daily highs, computed over its complete warm seasons
  (whole °F, the same round-trip as above). The rule is station-relative on purpose: the same definition gives 79°F at
  Point Mugu and 103°F in San Bernardino, and nothing else — humidity, nights, season — is tuned. A warm season counts
  when 90% of its May–October days have both a high and a low; a missing day breaks a run rather than being bridged.
</p>
<p>
  For each wave we keep its length, its hottest high, the lowest low on nights 2 through <i>n</i> (the "coolest night
  of the wave"), the low on the day after it ends, and — from the hourly readings — the share of 6 pm–8 am readings
  under 70°F, scaled to 14 hours, so 3-hourly and hourly years are comparable. "Then" is 1951–1980 and "now" the last
  30 complete warm seasons; a window needs 15 of them. The conclusion (flat peaks, warmer nights) does not depend on
  the definition: the 90th percentile, a two-day minimum and the 98th percentile all give the same shape.
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
  ("this summer through August 23" against every other summer through August 23). A station's latest date is always shown.
</p>

<h2 id="ranks">How unusual is this temperature for this date? — percentile ranks</h2>
<p>
  The site's central measure is a rank, not a threshold. For each calendar date we gather every 1951–1980 reading at the
  station within ±7 days of that date (roughly 450 highs and 450 lows) and place each later reading within that pile: the
  percentile rank is the share of baseline readings it exceeds, ties counted half. A 65th-percentile night was warmer than
  65% of comparable baseline nights. It assumes nothing about the shape of the distribution — Los Angeles temperatures
  under marine layer, onshore flow and Santa Ana regimes are not normal — and it uses every observation, so a station's
  average rank over a year or a decade is far less noisy than a count of days past a cutoff. Under an unchanged climate
  the average rank is 50. The year × day heatmaps draw each day's rank; "typical night" and "typical day" are the average
  rank over the last ten complete years. Ranks are only computed for stations with at least 20 complete years in 1951–1980.
</p>

<h2 id="indices">Percentile indices: TN90p, TX90p, TN10p, TX10p, and the diurnal range</h2>
<p>
  A 95°F day means something different at LAX and in Van Nuys, and a 70°F night is rare at the beach and routine in the desert.
  The site's primary measures therefore normalize each station to its own climate, following the standard climate-extremes
  indices (ETCCDI, the family NOAA and the IPCC use): for every calendar day we take the 1951–1980 readings within ±7 days of
  that date and find the 90th and 10th percentiles of the daily high and low. TX90p is the share of a year's days whose high
  exceeds that day's 90th percentile; TN90p the same for nights; TX10p and TN10p the shares below the 10th percentile. In an
  unchanged climate each hovers near 10%. Two simplifications relative to the formal definition: a ±7-day window rather than
  ±2, and no in-base bootstrap, so the baseline years read a touch above 10% by construction. Stations lacking at least 20
  complete years in 1951–1980 get no percentile indices. Alongside them: the June–August mean daily high and low as anomalies
  from the baseline (they use every reading and are much less noisy than counts), and the daily temperature range (high minus
  low) — if nights warm faster than days, it narrows. Trends on all of these are Theil–Sen slopes since 1951 with the same
  significance rule as elsewhere. The fixed-°F counts (days ≥ 95°F, nights ≥ 70°F) remain on the site as the intuitive,
  impact-facing layer; they are not the statistical test.
</p>

<h2 id="trends">Baseline, decades, trends</h2>
<p>
  "Then" is {ix.baseline.start}–{ix.baseline.end}: every station has a complete record over it, it is the reference period used by
  NASA GISS and Berkeley Earth, and it predates most of the local warming. Decade averages use complete years only
  (at least {ix.completeness.decade_min_years}); the current decade is marked "so far". Trend labels are Theil–Sen slopes
  (a median-based fit that is robust to single extreme years) over each station's own complete years from {ix.baseline.start}, or from
  the station's first complete year if later — so stations are never pooled into one trend; a slope is shown only
  when its 95% confidence interval excludes zero (Kendall p &lt; 0.05), otherwise the chart says "no clear trend". Count series that
  are almost all zeros — 95°F days at a beach station, frost nights at the coast — get no trend at all, because a median slope through
  zeros is meaningless. Daily
  "typical range" bands are the 10th–90th percentile of the baseline years for each calendar date (±{ix.completeness.doy_window_days ?? 7} days).
  A daily record requires at least {ix.completeness.record_min_prior_years} prior years of data for that date. One more filter: a
  complete year whose mean high or low sits far off the station's own trend line — more than 3.5°C, or five times the
  station's typical year-to-year deviation — is excluded from every yearly statistic and listed on the station page; almost
  all such years are archive artifacts (a first year in the wrong units, a different feed under the same id). A station gets
  a visible warning when such a year is recent or repeated, or when its own 5-year means jump by more than 3°C.
</p>

<h2 id="hourly">Hour by hour</h2>
<p>
  The same hourly readings drive each station's "Hour by hour" section: hours at or above a threshold, "no-relief nights" (the
  air never fell below a threshold between 6 pm and 8 am), heat-index hours (NWS formula, using dew point), and the average
  temperature at each hour of a summer day by decade. There a day counts when at least 18 of its 24 hours were observed and a night
  when 10 of its 14; years and months follow the same 90% rule.
</p>

<h2 id="regional">The LA-wide index: filling in the blanks</h2>
<p>
  Stations come and go — the 1940s network was a handful of airfields, more joined through the decades, some closed — so a plain
  average of whatever stations exist each year says as much about the network as about the weather. The two charts at
  the top of the front page instead come from a model fitted to every station-year with an exact count: each count is
  treated as a negative-binomial draw whose expected value is exp(station effect + year effect). The station effect is
  that site's climate (Newport Beach vs. Palmdale); the year effect is the shared, latent "how hot was this year across
  Los Angeles" variable. Every missing station-year then gets a predictive distribution from those two effects and the
  fitted noise, with parameter uncertainty carried through 400 draws (each draw clipped to ±2.5 standard errors, and a
  station's imputed count capped at 1.5× its own record maximum). The chart shows, for each year, the average over all
  {ix.stations.length} stations of observed-or-imputed counts — what the typical station would have
  recorded had every station reported every year — as the median of the draws with a 5–95% band. Years with few
  observers get wide bands, as they should. On station pages, the same model's estimates appear as gray dots for years
  the station didn't observe. The model is a description of the network, not a substitute for it: no imputed value
  enters any per-station statistic.
</p>

<h2 id="attribution">What these charts can and can't say</h2>
<p>
  Each chart is one thermometer at one place. Nighttime temperatures in particular are sensitive to the urban heat island:
  pavement, buildings and waste heat release warmth after sunset, so a growing city warms its nights more than its days — the
  same asymmetry the wider climate produces. The site answers "what has happened at this station?", not "how much of it is
  global warming?"; separating urban growth from regional change needs reference sites and models this site does not attempt. Station surroundings change over a century — pavement, buildings,
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
