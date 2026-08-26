<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { dataUrl } from '$lib/data.js';
  import { units } from '$lib/units.svelte.js';
  import { fmtC, fmtThresholdF } from '$lib/units.js';
  import { fmtISO } from '$lib/dates.js';
  import { FAMILIES, exportedAnnual, yearsOf, trendLabel } from '$lib/metrics.js';
  import { HEAT, COOL } from '$lib/palette.js';
  import StatTile from '$lib/StatTile.svelte';
  import StationMap from '$lib/StationMap.svelte';
  import YearScrubber from '$lib/YearScrubber.svelte';
  import SummerRankRow from '$lib/SummerRankRow.svelte';
  import AnnualBars from '$lib/AnnualBars.svelte';
  import DecadeDots from '$lib/DecadeDots.svelte';
  import SummerMultiples from '$lib/SummerMultiples.svelte';
  import Stripes from '$lib/Stripes.svelte';

  let { data } = $props();
  let ix = $derived(data.index);
  let region = $derived(ix.regions[0]);
  let allStations = $derived(ix.stations.filter((s) => s.region === region.id));
  let stations = $derived(allStations.filter((s) => s.active));
  let hero = $derived(data.hero); // default station summary (Pasadena)
  let heroIdx = $derived(stations.find((s) => s.id === hero.id));

  // Lazy: every station summary (for the map + station switcher) and the hero's daily file.
  let summaries = $state({});
  let daily = $state(null);
  onMount(async () => {
    const all = await Promise.all(allStations.map((s) => fetch(dataUrl(`/data/stations/${s.id}/summary.json`)).then((r) => r.json())));
    const out = {};
    for (const s of all) out[s.id] = s;
    summaries = out;
    daily = await fetch(dataUrl(`/data/stations/${hero.id}/daily.json`)).then((r) => r.json());
  });

  // Map: warm nights >= 70 by default, scrubbable year.
  let mapFamily = $state('warm');
  let mapThr = $derived(mapFamily === 'warm' ? 70 : mapFamily === 'hot' ? 95 : 32);
  let mapYear = $state(2025);
  let mapYears = $derived.by(() => {
    const y0 = Math.min(...allStations.map((s) => s.first_year));
    const y1 = Math.max(...allStations.map((s) => s.last_year));
    return Array.from({ length: y1 - y0 + 1 }, (_, i) => y0 + i);
  });
  onMount(() => (mapYear = Math.max(...stations.map((s) => s.last_complete_year ?? 0))));
  let mapValues = $derived.by(() => {
    const m = new Map();
    for (const s of allStations) {
      const sm = summaries[s.id];
      if (!sm) {
        m.set(s.id, null);
        continue;
      }
      const series = exportedAnnual(sm, mapFamily, mapThr);
      const k = yearsOf(sm, mapFamily).indexOf(mapYear);
      m.set(s.id, k < 0 || !series ? null : series[k]);
    }
    return m;
  });

  // Warm-nights chart with a station switcher.
  let barStation = $state(null);
  let bars = $derived(summaries[barStation ?? hero.id] ?? hero);
  let barsTrend = $derived(trendLabel(bars.trends?.warm_70, 'nights'));
  let barsBaseline = $derived(bars.windows?.baseline?.warm_70 == null ? null : { years: bars.windows.baseline.years, value: bars.windows.baseline.warm_70 });

  // Frost chart: the station with the most baseline frost nights.
  let frostStation = $derived([...stations].sort((a, b) => (b.headline.frost_baseline ?? 0) - (a.headline.frost_baseline ?? 0))[0]);
  let frost = $derived(summaries[frostStation?.id]);
  let frostBaseline = $derived(frost?.windows?.baseline?.season?.coldnight_32 == null ? null : { years: frost.windows.baseline.years, value: frost.windows.baseline.season.coldnight_32 });
  let frostTrend = $derived(trendLabel(frost?.trends?.frost_nights, 'nights'));

  const h = $derived(heroIdx.headline);
  const n1 = (v) => (v == null ? '—' : v < 10 ? v.toFixed(1) : Math.round(v).toString());
  let latest = $derived(stations.map((s) => s.last_date).sort().at(-1));
  let closed = $derived(allStations.length - stations.length);
</script>

<svelte:head>
  <title>Los Angeles heat, night by night, since 1893 · climate.sorkinlabs</title>
  <meta property="og:title" content="Los Angeles nights aren't cooling off like they used to" />
  <meta property="og:description" content="Hot days, warm nights and frost at {stations.length} LA-area weather stations, every year since 1893, from NOAA's raw daily records." />
</svelte:head>

<section class="hero">
  <div class="text">
    <h1>Los Angeles nights aren't cooling off like they used to.</h1>
    <p class="lede">
      The heat you feel isn't only the afternoon high — it's whether the night gives you a break.
      At {stations.length} weather stations across the LA area, from the beach to the mountains to the desert,
      the number of nights that never drop below 70°F has climbed for decades. Here is every one of those
      nights since {heroIdx.first_year}, straight from NOAA's daily records.
    </p>
    <p class="small muted">
      Latest readings through {fmtISO(latest)}{#if closed}; {closed} further stations with 50+ year records that have since closed are included for history{/if}. This site does not chart the famous downtown "Civic Center" record —
      <a href="/methods#civic-center">here's why</a>.
    </p>
  </div>
  <div class="tiles">
    <StatTile label="{heroIdx.short}: nights per year that stayed at or above 70°F, {hero.windows.baseline.years[0]}–{hero.windows.baseline.years[1]}" value={n1(h.warm70_baseline)} />
    <StatTile label="…and per year, {hero.windows.last10.years[0]}–{hero.windows.last10.years[1]}" value={n1(h.warm70_last10)} accent />
    <StatTile label="{heroIdx.short}: days per year at or above 95°F, then" value={n1(h.hot95_baseline)} />
    <StatTile label="…and now" value={n1(h.hot95_last10)} accent />
  </div>
</section>

<section>
  <div class="sechead">
    <h2>Every station, any year</h2>
    <div class="pillrow">
      <button class="pill" class:on={mapFamily === 'warm'} onclick={() => (mapFamily = 'warm')}>Nights ≥ {fmtThresholdF(70, units.f)}</button>
      <button class="pill" class:on={mapFamily === 'hot'} onclick={() => (mapFamily = 'hot')}>Days ≥ {fmtThresholdF(95, units.f)}</button>
      <button class="pill" class:on={mapFamily === 'frost'} onclick={() => (mapFamily = 'frost')}>Frost nights</button>
    </div>
  </div>
  <YearScrubber years={mapYears} bind:value={mapYear} playable />
  <StationMap stations={allStations} values={mapValues} unitLabel={FAMILIES[mapFamily].noun} cool={mapFamily === 'frost'} center={region.center} zoom={region.zoom} height="460px" onselect={(id) => goto(`/station/${id}?m=${mapFamily}&t=${mapThr}&year=${mapYear}`)} />
  <p class="small muted">Press play, or drag the year. Numbers are that year's count at each station; a dash means the year is incomplete there. The downtown Civic Center record is deliberately absent (<a href="/methods#civic-center">why</a>). <a href="/map">Open the full map →</a></p>
</section>

<section>
  <h2>This summer so far</h2>
  <p class="muted">Average daily high from June 1 through each station's latest reading, ranked against every other summer over the same dates. Volunteer-run stations report with a lag, so some aren't rankable yet.</p>
  <SummerRankRow {stations} />
</section>

<section>
  <div class="sechead">
    <h2>Warm nights, year by year</h2>
    <div class="pillrow">
      {#each allStations as s (s.id)}
        <button class="pill" class:on={(barStation ?? hero.id) === s.id} onclick={() => (barStation = s.id)} disabled={!summaries[s.id]}>{s.short}</button>
      {/each}
    </div>
  </div>
  <p class="muted">Nights at {bars.short} whose low never fell below {fmtThresholdF(70, units.f)}. Dark steps are decade averages.</p>
  <AnnualBars years={bars.cold_season ? bars.annual.year : []} values={bars.annual.warm_nights['70']} partial={bars.annual.partial} decades={{ decade: bars.decades.decade, value: bars.decades.warm_nights['70'], partial: bars.decades.partial }} color={HEAT} unitLabel="nights" trendLabel={barsTrend} baseline={barsBaseline} annotations={(bars.notable ?? []).map((n) => ({ year: Number(String(n.date).slice(0, 4)), label: n.label }))} height={280} />
  <p class="small"><a href="/station/{bars.id}?m=warm&t=70">Explore {bars.short} in full →</a></p>
</section>

<section>
  <h2>The same shift, at the beach, in the valleys, on the mountain, in the desert</h2>
  <p class="muted">Nights per year at or above {fmtThresholdF(70, units.f)}, averaged by decade, at every station.</p>
  <DecadeDots stations={allStations} metric="warm70" unitLabel="nights" cols={5} />
  <h2>Hot days: up inland, flat at the coast</h2>
  <p class="muted">Days per year at or above {fmtThresholdF(95, units.f)}. The marine layer keeps coastal afternoons in check; the valleys and the desert get the extra heat.</p>
  <DecadeDots stations={allStations} metric="hot95" unitLabel="days" cols={5} />
</section>

<section>
  <h2>Every summer at {heroIdx.short} since {heroIdx.first_year}</h2>
  <p class="muted">One row per summer, newest at the top; one square per day, colored by that day's high. Look for the dark streaks.</p>
  {#if daily}
    <SummerMultiples {daily} summary={hero} />
  {:else}
    <p class="muted small">Loading {(hero.last_year - hero.first_year + 1).toLocaleString()} summers…</p>
  {/if}
</section>

<section>
  <h2>{heroIdx.short}'s nights, as stripes</h2>
  <Stripes years={hero.annual.year} anomalies={hero.annual.tmin_anom_c} partial={hero.annual.partial} baseline={[hero.baseline.start, hero.baseline.end]} />
  <p class="small muted">Nights have warmed about {fmtC(h.tmin_trend_per_decade_c, units.f, { delta: true })} per decade at {heroIdx.short} since {hero.baseline.start} (days: {fmtC(h.tmax_trend_per_decade_c, units.f, { delta: true })} per decade).</p>
</section>

{#if frost && frostStation}
  <section>
    <h2>The other end: frost is disappearing</h2>
    <p class="muted">Nights at or below {fmtThresholdF(32, units.f)} at {frostStation.short}, per July–June season. {frostStation.short} averaged {n1(frostStation.headline.frost_baseline)} frost nights a year in {frost.windows.baseline.years[0]}–{frost.windows.baseline.years[1]} and {n1(frostStation.headline.frost_last10)} in the last ten seasons.</p>
    <AnnualBars years={frost.cold_season.year} values={frost.cold_season.cold_nights['32']} partial={frost.cold_season.partial} decades={{ decade: frost.decades.decade, value: frost.decades.season_cold_nights['32'], partial: frost.decades.partial }} color={COOL} unitLabel="nights" trendLabel={frostTrend} baseline={frostBaseline} height={240} />
    <p class="small"><a href="/station/{frost.id}?m=frost&t=32">Explore {frostStation.short} →</a></p>
  </section>
{/if}

<section class="about card">
  <b>How this was made.</b> Daily highs and lows from NOAA's GHCN-Daily archive for {stations.length} long-running stations,
  quality-flagged values removed, years with missing data shown as gaps rather than zeros, thresholds in whole °F as the
  observers recorded them, "then" = {ix.baseline.start}–{ix.baseline.end}. Every chart is one thermometer at one place, raw as NOAA published it; instrument and site changes NOAA
  has detected are marked on the station pages. Details, caveats, the Pasadena instrument history and the
  excluded downtown record: <a href="/methods">Methods</a>. Everything is open source: <a href="https://github.com/ssorkin/climate">github.com/ssorkin/climate</a>.
</section>

<style>
  section {
    margin-top: 2.2rem;
  }
  .hero {
    display: grid;
    grid-template-columns: 1.3fr 1fr;
    gap: 2rem;
    align-items: center;
    margin-top: 2rem;
  }
  .hero h1 {
    font-size: 2.8rem;
    margin: 0 0 0.8rem;
    max-width: 16ch;
  }
  .tiles {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1.2rem 1.5rem;
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
  .about {
    font-size: 0.92rem;
    color: #52514e;
  }
  @media (max-width: 800px) {
    .hero {
      grid-template-columns: 1fr;
    }
    .hero h1 {
      font-size: 2.1rem;
    }
  }
</style>
