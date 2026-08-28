<script>
  /**
   * Story: at LA-area stations, heat waves still peak at about the same temperature, but the
   * nights inside them no longer cool down. Rendered on the front page (while it is the
   * newest story) and at its permalink, /stories/la-heat-waves. Everything else the site
   * computes lives in /explore, /stations and the station pages.
   */
  import { units } from '$lib/units.svelte.js';
  import { storyBySlug, permalink } from '$lib/stories.js';
  import Byline from '$lib/Byline.svelte';
  import { fmtISO } from '$lib/dates.js';
  import { comparable, tempF, deltaF, diffOf } from '$lib/hw.js';
  import StatTile from '$lib/StatTile.svelte';
  import HeatWaveRange from '$lib/HeatWaveRange.svelte';
  import HeatWaveThresholds from '$lib/HeatWaveThresholds.svelte';
  import HeatWaveThenNow from '$lib/HeatWaveThenNow.svelte';
  import ReliefBars from '$lib/ReliefBars.svelte';
  import HeadlineTrends from '$lib/HeadlineTrends.svelte';
  import HeatWaveRobustness from '$lib/HeatWaveRobustness.svelte';

  let { data, onPermalink = false } = $props();
  const story = storyBySlug('la-heat-waves');
  let ix = $derived(data.index);
  let region = $derived(ix.regions[0]);
  let allStations = $derived(ix.stations.filter((s) => s.region === region.id));
  let latest = $derived(allStations.filter((s) => s.active).map((s) => s.last_date).sort().at(-1));

  let hw = $derived(data.heatwaves);
  let hwRule = $derived(hw?.rule ?? ix.heat_waves ?? { percentile: 95, min_days: 3, relief_f: 70 });
  let hwB = $derived(hw?.baseline ?? ix.baseline);
  // every station with a threshold, longest records first (the tabs on the big chart)
  let hwStations = $derived([...(hw?.stations ?? [])].sort((a, b) => b.years.length - a.years.length));
  // then-vs-now needs both windows; "unbroken" records have 25+ complete summers in each
  let hwCompare = $derived([...comparable(hwStations)].sort((a, b) => a.threshold_f - b.threshold_f));
  let hwOthers = $derived(hwStations.filter((s) => !hwCompare.includes(s)));
  // small multiples: the stations where the nights moved most relative to the afternoons, first
  const gap = (s) => (s.windows.last30.low_f - s.windows.baseline.low_f) - (s.windows.last30.peak_f - s.windows.baseline.peak_f);
  let hwRanked = $derived([...hwCompare].sort((a, b) => gap(b) - gap(a)));
  let otherPick = $state(null);
  let hwOther = $derived(hwOthers.find((s) => s.id === otherPick) ?? hwOthers[0]);
  let hwHero = $derived(hwStations.find((s) => s.id === region.story_station) ?? hwCompare[0] ?? hwStations[0]);
  let nowYears = $derived([...hwCompare].sort((a, b) => b.windows.last30.n - a.windows.last30.n)[0]?.windows.last30.years ?? null);

  let pooled = $derived(hw?.pooled ?? {});
  let nPooled = $derived(pooled.low_f?.n_stations ?? hwCompare.length);
  const winMean = (set, win, key) => { const v = set.map((s) => s.windows[win][key]).filter((x) => x != null); return v.length ? v.reduce((x, y) => x + y, 0) / v.length : null; };
  const est = (key) => pooled[key]?.est ?? null;
  const range = (key) => (pooled[key] ? `${dF(pooled[key].lo)} to ${dF(pooled[key].hi)}` : '');
  const WORDS = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten'];
  const word = (n) => WORDS[n] ?? String(n);
  // stations where the coolest-night interval includes zero: the exceptions, named on the page
  let exceptions = $derived(hwCompare.filter((s) => { const d = diffOf(s, 'low_f'); return d && d.lo <= 0 && d.hi >= 0; }));
  const yrs = (w) => (w ? `${w[0]}–${w[1]}` : '');
  const n1 = (v, d = 1) => (v == null ? '—' : v.toFixed(d).replace('-', '−'));
  const dF = (v) => deltaF(v, units.f);
  const tFU = (v) => tempF(v, units.f) + (units.f ? 'F' : 'C');
  let typical = $derived(
    hwCompare.length
      ? [{ label: `Average of ${nPooled} stations`, then: { relief_h: winMean(hwCompare, 'baseline', 'relief_h'), years: [hwB.start, hwB.end] }, now: { relief_h: winMean(hwCompare, 'last30', 'relief_h'), years: nowYears }, change: pooled.relief_h ? `${n1(pooled.relief_h.est)} h, 95%: ${n1(pooled.relief_h.lo)} to ${n1(pooled.relief_h.hi)}` : '' }]
      : []
  );
  let reliefRows = $derived(hwCompare.map((s) => ({ label: s.short, then: s.windows.baseline, now: s.windows.last30 })));
</script>

<svelte:head>
  <title>{story.title} · climate.sorkinlabs</title>
  <meta property="og:title" content={story.title} />
  <meta property="og:description" content="80+ years of hourly NOAA records at {hwStations.length} LA-area weather stations: the hottest afternoon of a heat wave lands where it always did; the coolest night inside one is {dF(est('low_f'))} warmer, and a heat-wave night gives {n1(-est('relief_h'))} fewer hours under 70°F." />
  <meta property="og:type" content="article" />
  <meta property="article:published_time" content={story.published} />
  <meta property="article:author" content="Stephen Sorkin" />
  <meta property="og:url" content="https://climate.sorkinlabs.com{permalink(story)}" />
  <meta property="og:image" content="https://climate.sorkinlabs.com{story.image}" />
  <meta property="og:image:width" content="1200" />
  <meta property="og:image:height" content="630" />
  <meta property="og:image:alt" content="Every heat wave at an LA-area station since the 1940s: the hottest afternoons hold level while the coolest nights climb." />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content={story.title} />
  <meta name="twitter:image" content="https://climate.sorkinlabs.com{story.image}" />
  {#if onPermalink}
    <link rel="canonical" href="https://climate.sorkinlabs.com{permalink(story)}" />
  {/if}
</svelte:head>

{#if hwHero && hwCompare.length && pooled.low_f}
  <section class="hero">
    <div class="text">
      <h1>{story.title}</h1>
      <Byline {story} dataThrough={latest} {onPermalink} />
      <p class="lede">
        Line up every heat wave a long-record LA-area station has recorded since the 1940s. The hottest afternoon of each one lands about where it
        always did: {dF(est('peak_f'))} across {nPooled} stations, {yrs([hwB.start, hwB.end])} to {yrs(nowYears)}. The coolest night inside each one is
        {dF(est('low_f'))} warmer and the night after it ends {dF(est('after_low_f'))} warmer — and a heat-wave night that once gave
        {n1(winMean(hwCompare, 'baseline', 'relief_h'))} hours under {tFU(hwRule.relief_f)} now gives {n1(winMean(hwCompare, 'last30', 'relief_h'))}.
        The waves aren't longer, and they aren't clearly more frequent. The nights are hotter.
      </p>
      <p class="small attribution">
        These are observed changes at individual weather stations. They include regional climate change, urbanization and changes around
        each station; this site does not attempt to attribute the causes. Every chart is one thermometer at one place, as NOAA published it.
      </p>
    </div>
    <HeadlineTrends {pooled} stations={hwCompare} nStations={nPooled} baseline={[hwB.start, hwB.end]} reliefF={hwRule.relief_f} />
  </section>

  <section>
    <h2>What counts as a heat wave here</h2>
    <p class="muted">There is no single temperature that means "heat wave" in Los Angeles: 83°F is a hot day at LAX and an ordinary one in Burbank. So the extreme is defined relative to each place's own climate.</p>
    <div class="def card"><b>A heat wave</b> is {hwRule.min_days} or more days in a row when the afternoon high reaches the hottest {100 - hwRule.percentile}% of that station's summer days (May–October, over its whole record).</div>
    <p class="muted">That makes it {tFU(hwStations.find((s) => s.short === 'LAX')?.threshold_f ?? 83)} at LAX and {tFU(hwStations.find((s) => s.short === 'Burbank Airport')?.threshold_f ?? 98)} in Burbank. Nothing else is tuned — no humidity, no minimum night temperature, no adjustment for the season. What happens at night falls out of the data, not the definition. A day counts only when the hourly record covers it; a missing day breaks a run (<a href="/methods#heatwaves">how</a>). <a href="#robustness">Does the definition matter?</a> — no; the table is below.</p>
    <details>
      <summary>The threshold at each station</summary>
      <HeatWaveThresholds stations={hwStations} />
    </details>
  </section>

  <section>
    <h2>Every heat wave at {word(hwRanked.length)} long-record LA-area stations</h2>
    <p class="muted">One line per heat wave, from its <span class="night">coolest night</span> up to its <span class="day">hottest afternoon</span>. Short bars mark the averages of both ends for {yrs([hwB.start, hwB.end])} and the last 30 complete summers. Stations where the nights moved most relative to the afternoons come first; hollow dots are waves in a summer that is not yet complete.</p>
    <div class="multiples">
      {#each hwRanked as s (s.id)}
        <div>
          <h3><a href="/station/{s.id}">{s.short}</a> <span class="muted small">≥ {tFU(s.threshold_f)} · {s.years.length} summers</span></h3>
          <HeatWaveRange station={s} compact />
        </div>
      {/each}
    </div>
  </section>

  <section>
    <h2>Then vs now: three temperatures from every heat wave</h2>
    <p class="muted">For each of the {nPooled} stations with a record in both windows: the average <span class="day">hottest afternoon</span> of a heat wave, the average <span class="night">coolest heat-wave night</span> (the lowest overnight temperature from the second night on — did the outdoor air ever substantially cool overnight?), and the <span class="night2">night after</span> the run broke. {yrs([hwB.start, hwB.end])} against the last 30 complete summers.</p>
    <div class="tiles3">
      <StatTile label="Hottest afternoon of the wave" value={dF(est('peak_f'))} sub="pooled change, 95%: {range('peak_f')}" />
      <StatTile label="Coolest heat-wave night" value={dF(est('low_f'))} sub="pooled change, 95%: {range('low_f')}" accent />
      <StatTile label="Night after it ends" value={dF(est('after_low_f'))} sub="pooled change, 95%: {range('after_low_f')}" accent />
    </div>
    <HeatWaveThenNow stations={hwCompare} baseline={[hwB.start, hwB.end]} />
    <p class="small muted">95% intervals bootstrap entire summers, so several heat waves in one year aren't treated as independent observations; the pooled numbers resample stations as well (<a href="/methods#heatwaves">how</a>). Heat waves also come about as often and run about as long as they did — year-by-year counts are in the <a href="/explore#heatwaves">explorer</a>.</p>
  </section>

  <section>
    <h2>Overnight relief: hours under {tFU(hwRule.relief_f)} on a heat-wave night</h2>
    <p class="muted">A daily low of 69°F and one of 60°F both count as "under 70," but they are very different nights. The hourly readings can tell them apart: of the 14 hours between 6 pm and 8 am, how many were under {tFU(hwRule.relief_f)}? That is the number that decides whether windows can be opened, whether a building sheds the day's heat, whether people sleep.</p>
    <ReliefBars rows={typical} reliefF={hwRule.relief_f} big />
    <p class="muted">Station by station:</p>
    <ReliefBars rows={reliefRows} reliefF={hwRule.relief_f} />
    <p class="small muted">Share of 6 pm–8 am readings under {tFU(hwRule.relief_f)}, scaled to 14 hours so hourly and 3-hourly years compare; nights from the second night of the wave on.</p>
    {#if exceptions.length}
      <h3>Not everywhere: {exceptions.map((s) => s.short).join(' and ')} {exceptions.length === 1 ? 'is' : 'are'} the exception</h3>
      <p class="muted">
        {#each exceptions as s, i}{s.short}{i < exceptions.length - 1 ? '; ' : ''}: the coolest heat-wave night moved {dF(diffOf(s, 'low_f')?.est)} ({dF(diffOf(s, 'low_f')?.lo)} to {dF(diffOf(s, 'low_f')?.hi)}), and its ordinary summer nights moved {dF(s.windows.last30.ordinary_low_f - s.windows.baseline.ordinary_low_f)}.{/each}
        That is a real difference between places, not noise in the headline: inland, away from the marine layer, heat-wave nights have barely changed — and neither have ordinary summer nights. This is a regional pattern with heterogeneous stations, not every thermometer proving one headline.
      </p>
    {/if}
  </section>

  <section id="robustness">
    <details>
      <summary><b>Does the definition matter?</b> The same then-vs-now changes under other definitions</summary>
      <p class="small muted">Pooled over the {nPooled} comparable stations (plain means; the front-page rows carry intervals). The last row keeps the page's definition but expresses each heat-wave night as a departure from the normal low for its calendar date, so a shift in <i>when</i> heat waves occur cannot masquerade as warmer nights{pooled.start_doy ? ` — modern heat waves start on average ${Math.abs(pooled.start_doy.est).toFixed(0)} days ${pooled.start_doy.est >= 0 ? 'later' : 'earlier'} than in the baseline` : ''}.</p>
      <HeatWaveRobustness rows={hw.robustness ?? []} {pooled} />
    </details>
  </section>

  {#if hwOther}
    <section>
      <div class="sechead">
        <h2>Stations without a {yrs([hwB.start, hwB.end])} baseline</h2>
        <div class="pillrow">
          {#each hwOthers as s (s.id)}
            <button class="pill" class:on={hwOther.id === s.id} onclick={() => (otherPick = s.id)}>{s.short}</button>
          {/each}
        </div>
      </div>
      <p class="muted">{hwOthers.length} more stations have heat-wave records but too few mid-century summers to compare then with now. Their waves, same chart: <a href="/station/{hwOther.id}">{hwOther.short}</a>, {hwOther.years.length} complete summers.</p>
      <HeatWaveRange station={hwOther} height={260} />
    </section>
  {/if}

  <section class="card explore">
    <h2>Explore it yourself</h2>
    <ul>
      <li><a href="/explore">The explorer</a> — every year as a ring at every station, the animated map, warm nights and hot days by year, frost, the LA-wide modeled index, and heat waves per summer year by year.</li>
      <li><a href="/stations">LA stations</a> — all {allStations.length} stations as a table; each <a href="/station/{hwHero.id}">station page</a> has its full record, hour by hour.</li>
      <li><a href="/us">The whole country</a> — the same hourly records for {data.usCount ? data.usCount.toLocaleString() : 'thousands of'} US stations.</li>
      <li><a href="/methods">Methods</a> — definitions, completeness rules, the bootstrap, what the charts can and can't say. Everything is open source: <a href="https://github.com/ssorkin/climate">github.com/ssorkin/climate</a>.</li>
    </ul>
  </section>

  <section class="about card">
    <b>Vocabulary.</b> A <b>warm night</b> is a night whose low never fell below 70°F. A <b>heat-wave night</b> is any night inside a defined heat wave. The
    <b>coolest heat-wave night</b> is the lowest overnight low from the second night of the wave on. <b>Overnight relief</b> is hours under 70°F between 6 pm
    and 8 am. Hourly readings miss a thermometer's true peak by about half a degree — consistently, in every decade — which is one more reason
    not to lean on the "hotter" question. "Then" is {yrs([hwB.start, hwB.end])}; "now" is each station's last 30 complete warm seasons. {nPooled} stations have
    15+ complete summers in both windows and are the ones compared; {hwStations.length - nPooled} more have heat-wave records but no mid-century baseline.
  </section>
{:else}
  <section class="hero">
    <h1>Los Angeles heat, station by station</h1>
    <p class="lede">The heat-wave story needs the regional export; meanwhile, <a href="/explore">explore every station</a>.</p>
  </section>
{/if}

<style>
  section {
    margin-top: 2.4rem;
  }
  .hero {
    margin-top: 2rem;
    display: grid;
    grid-template-columns: minmax(0, 1fr) 27rem;
    gap: 2rem;
    align-items: start;
  }
  .hero h1 {
    font-size: 2.8rem;
    margin: 0 0 0.8rem;
    max-width: 26ch;
  }
  .attribution {
    color: #52514e;
    max-width: 44rem;
    border-left: 3px solid #e8e1d5;
    padding-left: 0.8rem;
  }
  .sechead {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    gap: 1rem;
    flex-wrap: wrap;
  }
  .sechead h2 {
    margin-bottom: 0.3rem;
  }
  .tiles3 {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1rem;
    margin: 1rem 0 1.4rem;
  }
  .def {
    font-size: 1.15rem;
    border-left: 4px solid #d94f22;
    margin: 0.8rem 0;
  }
  details {
    margin: 0.6rem 0;
  }
  summary {
    cursor: pointer;
    color: #52514e;
    font-size: 0.95rem;
  }
  .multiples {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.6rem 1.4rem;
  }
  section h3 {
    font-size: 1.05rem;
    margin: 1.4rem 0 0.2rem;
  }
  #robustness summary {
    font-size: 1rem;
    color: #2b2722;
  }
  .multiples h3 {
    font-size: 0.98rem;
    margin: 0.6rem 0 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  @media (max-width: 1000px) {
    .multiples {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }
  @media (max-width: 640px) {
    .multiples {
      grid-template-columns: 1fr;
    }
  }
  .multiples h3 a {
    color: inherit;
    text-decoration: none;
  }
  .explore ul {
    margin: 0.4rem 0 0;
    padding-left: 1.2rem;
  }
  .explore li {
    margin: 0.35rem 0;
  }
  .explore h2 {
    margin-top: 0.2rem;
  }
  .about {
    font-size: 0.92rem;
    color: #52514e;
  }
  .day {
    color: #c2410c;
    font-weight: 600;
  }
  .night {
    color: #1c5cab;
    font-weight: 600;
  }
  .night2 {
    color: #4f8fd6;
    font-weight: 600;
  }
  @media (max-width: 800px) {
    .hero {
      grid-template-columns: 1fr;
    }
    .hero h1 {
      font-size: 2.1rem;
    }
    .tiles3 {
      grid-template-columns: 1fr;
    }
  }
</style>
