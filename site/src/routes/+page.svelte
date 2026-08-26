<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { dataUrl } from '$lib/data.js';
  import { units } from '$lib/units.svelte.js';
  import { fmtC, fmtThresholdF } from '$lib/units.js';
  import { fmtISO } from '$lib/dates.js';
  import { FAMILIES, exportedAnnual, exportedAnnualLower, yearsOf, trendLabel } from '$lib/metrics.js';
  import { daysInYear } from '$lib/dates.js';
  import { HEAT, COOL } from '$lib/palette.js';
  import StatTile from '$lib/StatTile.svelte';
  import StationMap from '$lib/StationMap.svelte';
  import YearScrubber from '$lib/YearScrubber.svelte';
  import SummerRankRow from '$lib/SummerRankRow.svelte';
  import AnnualBars from '$lib/AnnualBars.svelte';
  import DecadeDots from '$lib/DecadeDots.svelte';
  import SummerMultiples from '$lib/SummerMultiples.svelte';
  import Stripes from '$lib/Stripes.svelte';
  import RegionalIndex from '$lib/RegionalIndex.svelte';

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
      const lb = exportedAnnualLower(sm, mapFamily, mapThr);
      const ys = yearsOf(sm, mapFamily);
      const k = ys.indexOf(mapYear);
      if (k < 0 || !series) m.set(s.id, null);
      else if (series[k] != null) m.set(s.id, series[k]);
      else m.set(s.id, lb?.[k] != null ? { lower: lb[k] } : null);
    }
    return m;
  });

  // Fixed color scale: the largest annual count of this metric at any station in any year.
  let mapVmax = $derived.by(() => {
    let top = 1;
    for (const s of allStations) {
      const sm = summaries[s.id];
      if (!sm) continue;
      for (const v of exportedAnnual(sm, mapFamily, mapThr) ?? []) if (v != null && v > top) top = v;
    }
    return top;
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
  let reg = $derived(data.regional);
  const regWin = (key, a, b) => {
    const m = reg?.metrics?.[key];
    if (!m) return null;
    const v = m.year.map((y, i) => (y >= a && y <= b ? m.mean[i] : null)).filter((q) => q != null);
    return v.length ? v.reduce((s, q) => s + q, 0) / v.length : null;
  };
  let regLast = $derived(reg?.metrics?.warm70 ? reg.metrics.warm70.year.at(-1) : null);
  let warmBase = $derived(regWin('warm70', ix.baseline.start, ix.baseline.end));
  let warmNow = $derived(regLast ? regWin('warm70', regLast - 9, regLast) : null);
  let hotBase = $derived(regWin('hot95', ix.baseline.start, ix.baseline.end));
  let hotNow = $derived(regLast ? regWin('hot95', regLast - 9, regLast) : null);
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
      Across {allStations.length} weather stations in Greater Los Angeles that have reported every hour or three since
      the 1940s — airports from the beach to the desert — the typical station now records
      {#if warmBase != null && warmNow != null}about <b>{n1(warmNow)}</b> nights a year that never drop below 70°F, up from
      <b>{n1(warmBase)}</b> in {ix.baseline.start}–{ix.baseline.end}{:else}far more nights that never drop below 70°F than it did in the mid-20th century{/if}
      — and {#if hotBase != null && hotNow != null}<b>{n1(hotNow)}</b> days at or above 95°F, up from <b>{n1(hotBase)}</b>{:else}more 95°F days too{/if}.
      Every number comes straight from NOAA's hourly station records.
    </p>
    <p class="small muted">
      Latest readings through {fmtISO(latest)}{#if closed}; {closed} closed {closed === 1 ? 'station is' : 'stations are'} included for history{/if}.
      Stations come and go, so the two charts use a model that fills each station's missing years from the others (<a href="/methods#regional">how</a>); they start in {reg?.display_from ?? 1930}, when the network had grown past a handful of inland sites.
      The famous downtown record has hourly data only since 1999 — <a href="/methods#civic-center">a note on that</a>.
    </p>
  </div>
  <div class="tiles">
    {#if reg?.metrics?.warm70}
      <RegionalIndex series={reg.metrics.warm70} from={reg.display_from} label="Nights ≥ 70°F per year, average station" unitLabel="nights" baseline={[ix.baseline.start, ix.baseline.end]} height={210} compact />
    {/if}
    {#if reg?.metrics?.hot95}
      <RegionalIndex series={reg.metrics.hot95} from={reg.display_from} label="Days ≥ 95°F per year, average station" unitLabel="days" baseline={[ix.baseline.start, ix.baseline.end]} height={210} compact />
    {/if}
    {#if !reg}
      <StatTile label="{heroIdx.short}: nights per year at or above 70°F, {hero.windows.baseline.years[0]}–{hero.windows.baseline.years[1]}" value={n1(h.warm70_baseline)} />
      <StatTile label="…and per year, {hero.windows.last10.years[0]}–{hero.windows.last10.years[1]}" value={n1(h.warm70_last10)} accent />
    {/if}
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
  <StationMap stations={allStations} values={mapValues} vmax={mapVmax} compact unitLabel={FAMILIES[mapFamily].noun} cool={mapFamily === 'frost'} center={region.center} zoom={region.zoom} height="460px" onselect={(id) => goto(`/station/${id}?m=${mapFamily}&t=${mapThr}&year=${mapYear}`)} />
  <p class="small muted">Press play, or drag the year. Each pill is one station's count for that year (hover for the name); “≥” means the year is incomplete there and the count is a lower bound; stations with no data that year are hidden. Colors use one scale for every year. <a href="/map">Open the full map →</a></p>
</section>

<section>
  <h2>This summer so far</h2>
  <p class="muted">Average daily high from June 1 through each station's latest reading, ranked against every other summer at that station over the same dates.</p>
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
  <AnnualBars years={bars.cold_season ? bars.annual.year : []} values={bars.annual.warm_nights['70']} lower={bars.annual.warm_nights_lb?.['70'] ?? []} daysValid={bars.annual.days_valid_tmin} daysTotal={bars.annual.year.map((y) => daysInYear(y))} partial={bars.annual.partial} decades={{ decade: bars.decades.decade, value: bars.decades.warm_nights['70'], partial: bars.decades.partial }} color={HEAT} unitLabel="nights" trendLabel={barsTrend} baseline={barsBaseline} annotations={(bars.notable ?? []).map((n) => ({ year: Number(String(n.date).slice(0, 4)), label: n.label }))} height={280} />
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
    <AnnualBars years={frost.cold_season.year} values={frost.cold_season.cold_nights['32']} lower={frost.cold_season.cold_nights_lb?.['32'] ?? []} daysValid={frost.cold_season.days_valid_tmin} daysTotal={frost.cold_season.year.map((y) => daysInYear(y))} partial={frost.cold_season.partial} decades={{ decade: frost.decades.decade, value: frost.decades.season_cold_nights['32'], partial: frost.decades.partial }} color={COOL} unitLabel="nights" trendLabel={frostTrend} baseline={frostBaseline} height={240} />
    <p class="small"><a href="/station/{frost.id}?m=frost&t=32">Explore {frostStation.short} →</a></p>
  </section>
{/if}

<section>
  <h2>The whole country</h2>
  <p class="muted">The same records exist for every long-running station in the United States — {data.usCount ? data.usCount.toLocaleString() : 'thousands of'} of them with 50+ years of daily readings. <a href="/us">Open the national map →</a></p>
</section>

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
    grid-template-columns: 1fr 1.15fr;
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
    grid-template-columns: 1fr;
    gap: 0.9rem;
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
