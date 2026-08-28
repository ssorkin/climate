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
  import { comparable, median as med, tempF, deltaF } from '$lib/hw.js';
  import StatTile from '$lib/StatTile.svelte';
  import HeatWaveRange from '$lib/HeatWaveRange.svelte';
  import HeatWaveThresholds from '$lib/HeatWaveThresholds.svelte';
  import HeatWaveThenNow from '$lib/HeatWaveThenNow.svelte';
  import ReliefBars from '$lib/ReliefBars.svelte';

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
  let hwFull = $derived(hwCompare.filter((s) => s.windows.baseline.n >= 25 && s.windows.last30.n >= 25));
  let hwOthers = $derived(hwStations.filter((s) => !hwCompare.includes(s)));
  let hwStory = $state(null);
  let hwHero = $derived(hwStations.find((s) => s.id === (hwStory ?? region.story_station)) ?? hwCompare[0] ?? hwStations[0]);
  let nowYears = $derived(hwFull[0]?.windows.last30.years ?? hwCompare[0]?.windows.last30.years ?? null);

  const hwDelta = (set, key) => med(set.map((s) => s.windows.last30[key] - s.windows.baseline[key]));
  const hwMed = (set, win, key) => med(set.map((s) => s.windows[win][key]));
  const yrs = (w) => (w ? `${w[0]}–${w[1]}` : '');
  const n1 = (v, d = 1) => (v == null ? '—' : v.toFixed(d));
  const dF = (v) => deltaF(v, units.f);
  const tFU = (v) => tempF(v, units.f) + (units.f ? 'F' : 'C');
  let typical = $derived(
    hwFull.length
      ? [{ label: 'Typical station', then: { relief_h: hwMed(hwFull, 'baseline', 'relief_h'), years: [hwB.start, hwB.end] }, now: { relief_h: hwMed(hwFull, 'last30', 'relief_h'), years: nowYears } }]
      : []
  );
  let reliefRows = $derived(hwCompare.map((s) => ({ label: s.short, then: s.windows.baseline, now: s.windows.last30 })));
</script>

<svelte:head>
  <title>LA heat waves aren't much hotter at their peak. The nights have changed. · climate.sorkinlabs</title>
  <meta property="og:title" content="Los Angeles heat waves aren't getting much hotter at their peak. But the nights aren't cooling down." />
  <meta property="og:description" content="80+ years of hourly NOAA records at {hwStations.length} LA-area weather stations: the hottest afternoon of a heat wave lands where it always did; the coolest night of one is {dF(hwDelta(hwFull, 'low_f'))} warmer, and overnight relief has roughly halved." />
  <meta property="og:type" content="article" />
  <meta property="article:published_time" content={story.published} />
  <meta property="article:author" content="Stephen Sorkin" />
  <meta property="og:url" content="https://climate.sorkinlabs.com{permalink(story)}" />
  {#if onPermalink}
    <link rel="canonical" href="https://climate.sorkinlabs.com{permalink(story)}" />
  {/if}
</svelte:head>

{#if hwHero && hwCompare.length}
  <section class="hero">
    <div class="text">
      <h1>{story.title}</h1>
      <Byline {story} dataThrough={latest} {onPermalink} />
      <p class="lede">
        Line up every heat wave an LA-area airport has recorded since the 1940s. The hottest afternoon of each one lands about where it
        always did: {dF(hwDelta(hwFull, 'peak_f'))} at the typical long-record station, {yrs([hwB.start, hwB.end])} to {yrs(nowYears)}. The coolest
        night inside each one is {dF(hwDelta(hwFull, 'low_f'))} warmer, the night after it ends {dF(hwDelta(hwFull, 'after_low_f'))} warmer — and a heat-wave
        night that once gave {n1(hwMed(hwFull, 'baseline', 'relief_h'))} hours under {tFU(hwRule.relief_f)} now gives {n1(hwMed(hwFull, 'last30', 'relief_h'))}.
      </p>
      <p class="small attribution">
        These are observed changes at individual weather stations. They include regional climate change, urbanization and changes around
        each station; this site does not attempt to attribute the causes. Every chart is one thermometer at one place, as NOAA published it.
      </p>
    </div>
  </section>

  <section>
    <div class="sechead">
      <h2>Every heat wave at {hwHero.short} since {hwHero.first_year}</h2>
      <div class="pillrow">
        {#each hwStations as s (s.id)}
          <button class="pill" class:on={hwHero.id === s.id} onclick={() => (hwStory = s.id)}>{s.short}</button>
        {/each}
      </div>
    </div>
    <p class="muted">One line per heat wave, from its <span class="night">coolest night</span> up to its <span class="day">hottest afternoon</span>. Short bars mark the averages of both ends for {yrs([hwB.start, hwB.end])} and the last 30 complete summers. Hollow dots are waves in a summer that is not yet complete.</p>
    <HeatWaveRange station={hwHero} />
  </section>

  <section>
    <h2>What counts as a heat wave here</h2>
    <p class="muted">There is no single temperature that means "heat wave" in Los Angeles: 83°F is a hot day at LAX and an ordinary one in Burbank. So the extreme is defined relative to each place's own climate.</p>
    <div class="def card"><b>A heat wave</b> is {hwRule.min_days} or more days in a row when the afternoon high reaches the hottest {100 - hwRule.percentile}% of that station's summer days (May–October, over its whole record).</div>
    <p class="muted">Nothing else is tuned — no humidity, no minimum night temperature, no adjustment for the season. What happens at night falls out of the data, not the definition. A day counts only when the hourly record covers it; a missing day breaks a run (<a href="/methods#heatwaves">how</a>). The result does not depend on the exact rule: the 90th percentile, a two-day minimum and the 98th percentile all give the same shape.</p>
    <details>
      <summary>The threshold at each station</summary>
      <HeatWaveThresholds stations={hwStations} />
    </details>
  </section>

  <section>
    <h2>Then vs now: three temperatures from every heat wave</h2>
    <p class="muted">For each station with a record in both windows: the average <span class="day">hottest afternoon</span> of a heat wave, the average <span class="night">coolest heat-wave night</span> (the lowest overnight temperature from the second night on — did you ever get a night the house could cool down?), and the <span class="night2">night after</span> the run broke. {yrs([hwB.start, hwB.end])} against the last 30 complete summers.</p>
    <div class="tiles3">
      <StatTile label="Hottest afternoon of the wave" value={dF(hwDelta(hwFull, 'peak_f'))} sub="median change across the {hwFull.length} unbroken records" />
      <StatTile label="Coolest heat-wave night" value={dF(hwDelta(hwFull, 'low_f'))} sub="the lowest overnight temperature inside the wave, median change" accent />
      <StatTile label="Night after it ends" value={dF(hwDelta(hwFull, 'after_low_f'))} sub="overnight low on the first night after the run breaks, median change" accent />
    </div>
    <HeatWaveThenNow stations={hwCompare} baseline={[hwB.start, hwB.end]} />
    <p class="small muted">The whisker on each filled dot is a 95% interval for the change, treating heat waves as independent draws; a gray number is a change within that interval. Heat waves also come about as often and run about as long as they did at the coast and in the basin — year-by-year counts are in the <a href="/explore#heatwaves">explorer</a>.</p>
  </section>

  <section>
    <h2>Overnight relief: hours under {tFU(hwRule.relief_f)} on a heat-wave night</h2>
    <p class="muted">A daily low of 69°F and one of 60°F both count as "under 70," but they are very different nights. The hourly readings can tell them apart: of the 14 hours between 6 pm and 8 am, how many were under {tFU(hwRule.relief_f)}?</p>
    <ReliefBars rows={typical} reliefF={hwRule.relief_f} big />
    <p class="muted">Station by station:</p>
    <ReliefBars rows={reliefRows} reliefF={hwRule.relief_f} />
    <p class="small muted">Share of 6 pm–8 am readings under {tFU(hwRule.relief_f)}, scaled to 14 hours so hourly and 3-hourly years compare; nights from the second night of the wave on. At March, in the Inland Empire, heat-wave nights have barely moved — and neither have its ordinary summer nights.</p>
  </section>

  <section>
    <h2>Not just one thermometer</h2>
    <p class="muted">The same picture at every station with a record in both windows, from the coast to the Inland Empire. Same chart as above, one per station: the orange bars stay level, the blue bars step up.</p>
    <div class="multiples">
      {#each hwCompare as s (s.id)}
        <div>
          <h3><a href="/station/{s.id}">{s.short}</a> <span class="muted small">threshold {tFU(s.threshold_f)} · {s.years.length} complete summers</span></h3>
          <HeatWaveRange station={s} height={230} />
        </div>
      {/each}
    </div>
    {#if hwOthers.length}
      <p class="small muted">
        {hwOthers.length} more stations have heat-wave records but no {yrs([hwB.start, hwB.end])} baseline to compare against:
        {#each hwOthers as s, i}<a href="/station/{s.id}">{s.short}</a>{i < hwOthers.length - 1 ? ', ' : '.'}{/each}
      </p>
    {/if}
  </section>

  <section class="card explore">
    <h2>Explore it yourself</h2>
    <ul>
      <li><a href="/explore">The explorer</a> — every year as a ring at every station, the animated map, warm nights and hot days by year, frost, the LA-wide modeled index, and heat waves per summer year by year.</li>
      <li><a href="/stations">LA stations</a> — all {allStations.length} stations as a table; each <a href="/station/{hwHero.id}">station page</a> has its full record, hour by hour.</li>
      <li><a href="/us">The whole country</a> — the same hourly records for {data.usCount ? data.usCount.toLocaleString() : 'thousands of'} US stations.</li>
      <li><a href="/methods">Methods</a> — definitions, completeness rules, what the charts can and can't say. Everything is open source: <a href="https://github.com/ssorkin/climate">github.com/ssorkin/climate</a>.</li>
    </ul>
  </section>

  <section class="about card">
    <b>Vocabulary.</b> A <b>warm night</b> is a night whose low never fell below 70°F. A <b>heat-wave night</b> is any night inside a defined heat wave. The
    <b>coolest heat-wave night</b> is the lowest overnight low from the second night of the wave on. <b>Overnight relief</b> is hours under 70°F between 6 pm
    and 8 am. Hourly readings miss a thermometer's true peak by about half a degree — consistently, in every decade — which is one more reason
    not to lean on the "hotter" question. "Then" is {yrs([hwB.start, hwB.end])}; "now" is each station's last 30 complete warm seasons.
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
    max-width: 60rem;
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
    grid-template-columns: 1fr;
    gap: 0.4rem;
  }
  .multiples h3 {
    font-size: 1.05rem;
    margin: 1rem 0 0;
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
    .hero h1 {
      font-size: 2.1rem;
    }
    .tiles3 {
      grid-template-columns: 1fr;
    }
  }
</style>
