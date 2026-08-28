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
  import TrendForest from '$lib/TrendForest.svelte';
  import TrendPairs from '$lib/TrendPairs.svelte';
  import SpiralMap from '$lib/SpiralMap.svelte';
  import RankDots from '$lib/RankDots.svelte';
  import { loadCurves } from '$lib/curves.js';
  import { fToC } from '$lib/units.js';
  import { comparable, median as med, tempF, deltaF, axisT } from '$lib/hw.js';
  import HeatWaveRange from '$lib/HeatWaveRange.svelte';
  import HeatWaveThresholds from '$lib/HeatWaveThresholds.svelte';
  import HeatWaveCounts from '$lib/HeatWaveCounts.svelte';
  import Dumbbell from '$lib/Dumbbell.svelte';
  import NightPairBars from '$lib/NightPairBars.svelte';

  let { data } = $props();
  let ix = $derived(data.index);
  let region = $derived(ix.regions[0]);
  let allStations = $derived(ix.stations.filter((s) => s.region === region.id));
  let stations = $derived(allStations.filter((s) => s.active));
  let hero = $derived(data.hero); // default station summary (Pasadena)
  let heroIdx = $derived(allStations.find((s) => s.id === hero.id) ?? allStations[0]);

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
  const trendStats = (key) => {
    const ts = allStations.map((s) => s.headline?.[key]).filter((t) => t && t.slope_per_decade != null);
    const up = ts.filter((t) => t.significant && t.slope_per_decade > 0).length;
    const down = ts.filter((t) => t.significant && t.slope_per_decade < 0).length;
    const slopes = ts.map((t) => t.slope_per_decade).sort((a, b) => a - b);
    const median = slopes.length ? slopes[Math.floor(slopes.length / 2)] : null;
    return { n: ts.length, up, down, median };
  };
  let warmT = $derived(trendStats('trend_warm70'));
  let hotT = $derived(trendStats('trend_hot95'));
  let idx = $derived(data.indices);
  let curves = $state({});
  let rankEl = $state('tmax');
  let curveStations = $derived(allStations.filter((s) => s.first_year <= 1975 && s.complete_years >= 30));
  let spiralYears = $derived.by(() => {
    const y1 = Math.max(...curveStations.map((s) => s.last_year));
    return Array.from({ length: y1 - 1940 + 1 }, (_, i) => 1940 + i);
  });
  let spiralYear = $state(2025);
  onMount(() => (spiralYear = Math.max(...curveStations.map((s) => s.last_year))));
  onMount(async () => {
    const ids = curveStations.map((s) => s.id);
    const loaded = await Promise.all(ids.map((id) => loadCurves(id).catch(() => null)));
    const out = {};
    ids.forEach((id, i) => { if (loaded[i]) out[id] = loaded[i]; });
    curves = out;
  });
  const median = (arr) => { const a = arr.filter((v) => v != null).sort((x, y) => x - y); return a.length ? a[Math.floor(a.length / 2)] : null; };
  let nightRank = $derived(median(baseStations.map((s) => s.headline.score?.tmin)));
  let dayRank = $derived(median(baseStations.map((s) => s.headline.score?.tmax)));
  let baseStations = $derived(allStations.filter((s) => s.headline?.has_baseline));
  const idxMean = (key, a, b) => {
    if (!idx) return null;
    const v = idx.year.map((y, i) => (y >= a && y <= b ? idx[key][i] : null)).filter((q) => q != null);
    return v.length ? v.reduce((s, q) => s + q, 0) / v.length : null;
  };
  let tn90Now = $derived(idxMean('tn90p', 2016, 2025));
  let tx90Now = $derived(idxMean('tx90p', 2016, 2025));
  let tn10Now = $derived(idxMean('tn10p', 2016, 2025));
  let tx10Now = $derived(idxMean('tx10p', 2016, 2025));
  let tn90T = $derived(trendStats('trend_tn90p'));
  let tx90T = $derived(trendStats('trend_tx90p'));
  let nightsFaster = $derived(allStations.filter((s) => s.headline?.trend_jja_tmin && s.headline?.trend_jja_tmax && s.headline.trend_jja_tmin.slope_per_decade > s.headline.trend_jja_tmax.slope_per_decade).length);
  let nPairs = $derived(allStations.filter((s) => s.headline?.trend_jja_tmin && s.headline?.trend_jja_tmax).length);
  // the LA mean index trend: Theil–Sen is done in Python per station; for the mean line we show the station-median slope
  const medianTrend = (key) => {
    const ts = baseStations.map((s) => s.headline[key]).filter(Boolean);
    if (!ts.length) return null;
    const sl = ts.map((t) => t.slope_per_decade).sort((a, b) => a - b);
    const med = sl[Math.floor(sl.length / 2)];
    const sig = ts.filter((t) => t.significant && Math.sign(t.slope_per_decade) === Math.sign(med)).length;
    return { slope_per_decade: med, significant: sig > ts.length / 2, from: Math.max(...ts.map((t) => t.from)), n: ts.length };
  };
  let latest = $derived(stations.map((s) => s.last_date).sort().at(-1));

  // --- the heat-wave story -------------------------------------------------------------
  let hw = $derived(data.heatwaves);
  let hwRule = $derived(hw?.rule ?? { percentile: 95, min_days: 3, relief_f: 70 });
  // every station with a threshold, longest records first (the tabs on the hero chart)
  let hwStations = $derived([...(hw?.stations ?? [])].sort((a, b) => b.years.length - a.years.length));
  // then-vs-now needs both windows; "unbroken" records have 25+ complete summers in each
  let hwCompare = $derived([...comparable(hwStations)].sort((a, b) => a.threshold_f - b.threshold_f));
  let hwFull = $derived(hwCompare.filter((s) => s.windows.baseline.n >= 25 && s.windows.last30.n >= 25));
  let hwStory = $state(null);
  let hwHero = $derived(hwStations.find((s) => s.id === (hwStory ?? region.story_station)) ?? hwCompare[0] ?? hwStations[0]);
  const hwDelta = (set, key) => med(set.map((s) => s.windows.last30[key] - s.windows.baseline[key]));
  const hwMed = (set, win, key) => med(set.map((s) => s.windows[win][key]));
  let hwB = $derived(hw?.baseline ?? ix.baseline);
  let hwNowYears = $derived(hwFull[0]?.windows.last30.years ?? hwCompare[0]?.windows.last30.years ?? null);
  const yrs = (w) => `${w[0]}–${w[1]}`;
  const n2 = (v, d = 1) => (v == null ? '—' : v.toFixed(d));
  const sgn = (v, d = 1) => (v == null ? '—' : (v >= 0 ? '+' : '−') + Math.abs(v).toFixed(d));
  const dRows = (set, key, tipFmt) => set.map((s) => ({ label: s.short, a: s.windows.baseline[key], b: s.windows.last30[key], tipA: tipFmt(s.windows.baseline[key]), tipB: tipFmt(s.windows.last30[key]) }));
  const tF = (v) => tempF(v, units.f);
  const dF = (v) => deltaF(v, units.f);
  const tFU = (v) => tempF(v, units.f) + (units.f ? 'F' : 'C');
  let closed = $derived(allStations.length - stations.length);
</script>

<svelte:head>
  <title>Los Angeles heat waves aren't hotter. They just don't cool off. · climate.sorkinlabs</title>
  <meta property="og:title" content="Los Angeles heat waves aren't hotter than they used to be. They just don't cool off." />
  <meta property="og:description" content="Every heat wave at {hwStations.length} LA-area weather stations since the 1940s, from NOAA's hourly records: the hottest afternoons hold still, the coolest nights climb." />
</svelte:head>

{#if hwHero && hwCompare.length}
  <section class="hero">
    <div class="text">
      <h1>Los Angeles heat waves aren't hotter than they used to be. They just don't cool off.</h1>
      <p class="lede">
        Pick any airport in the basin and line up every heat wave it has recorded since the 1940s. The hottest afternoon of each one lands
        about where it always did ({sgn(hwDelta(hwFull, 'peak_f') == null ? null : units.f ? hwDelta(hwFull, 'peak_f') : hwDelta(hwFull, 'peak_f') / 1.8)}° at the typical station, {yrs(hwB ? [hwB.start, hwB.end] : [0, 0])} to {hwNowYears ? yrs(hwNowYears) : 'now'}). The coolest night of each one is
        {dF(hwDelta(hwFull, 'low_f'))} warmer — and the hours of relief under {tFU(hwRule.relief_f)} on a heat-wave night have gone from
        {n2(hwMed(hwFull, 'baseline', 'relief_h'))} to {n2(hwMed(hwFull, 'last30', 'relief_h'))}.
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
    <h2>First, what counts as a heat wave</h2>
    <p class="muted">There is no single temperature that means "heat wave" in Los Angeles: 83°F is a hot day at LAX and an ordinary one in Burbank. So the definition is local to each station and comes from its own history.</p>
    <div class="def card"><b>A heat wave</b> is {hwRule.min_days} or more days in a row when the afternoon high reaches the hottest {100 - hwRule.percentile}% of that station's summer days (May–October, over its whole record).</div>
    <p class="muted">Nothing else is tuned — no humidity, no minimum night temperature, no adjustment for the season. The night side of the story below falls out of the data, not the definition. A day counts only when the hourly record covers it (<a href="/methods#heatwaves">how</a>).</p>
    <HeatWaveThresholds stations={hwStations} />
  </section>

  <section>
    <h2>What has stayed the same</h2>
    <p class="muted">Compare {yrs([hwB.start, hwB.end])} with the last 30 complete summers at the {hwFull.length} stations with unbroken records. Heat waves come about as often as they did, run about as long, and peak about as high — the differences are within a degree or a fraction of a day, and they don't all point the same way.</p>
    <div class="tiles3">
      <StatTile label="How often" value="{sgn(hwDelta(hwFull, 'waves_per_year'), 1)} / summer" sub="heat waves per summer, median change across the {hwFull.length} stations" />
      <StatTile label="How long" value="{sgn(hwDelta(hwFull, 'mean_days'), 1)} days" sub="days per heat wave, median change" />
      <StatTile label="How hot" value="{dF(hwDelta(hwFull, 'peak_f'))}" sub="hottest afternoon of the wave, median change" />
    </div>
    <div class="three">
      <div><h3>Heat waves per summer</h3><Dumbbell rows={dRows(hwCompare, 'waves_per_year', (v) => n2(v, 2))} color={HEAT} domain={[0, 4]} format={(v) => n2(v, 0)} delta={(d) => sgn(d, 2)} big={0.5} empty="{yrs([hwB.start, hwB.end])} (hollow) → last 30 summers (filled)" /></div>
      <div><h3>Days per heat wave</h3><Dumbbell rows={dRows(hwCompare, 'mean_days', (v) => n2(v, 1))} color={HEAT} domain={[3, 5]} format={(v) => n2(v, 1)} big={0.5} empty="Average length; every wave is at least {hwRule.min_days} days" /></div>
      <div><h3>Hottest afternoon of the wave</h3><Dumbbell rows={dRows(hwCompare, 'peak_f', tF)} color={HEAT} domain={[88, 110]} axis={(v) => axisT(v, units.f)} format={(v) => Math.round(v) + '°'} delta={dF} big={2} empty="Average of each wave's hottest high" /></div>
    </div>
    <h3>Heat waves per summer, year by year</h3>
    <HeatWaveCounts stations={hwCompare} />
    <p class="small muted">The count swings from year to year and decade to decade — the 2000s were quiet at every station, the 1950s busy at the coast — but at the coast and in the basin the recent average sits where the mid-century one did. Inland stations are the exception: March, San Bernardino and Victorville run about half a day longer per wave and about one extra heat wave a year.</p>
  </section>

  <section>
    <h2>What has changed: the nights</h2>
    <p class="muted">Every night inside a heat wave is warmer now, and so is the first night after it ends. The coolest night a heat wave offers — the one that used to break the spell — is {dF(hwDelta(hwFull, 'low_f'))} warmer at the typical station. Measured in hours, the relief has shrunk faster than the degrees suggest.</p>
    <div class="tiles3">
      <StatTile label="Coolest night of the wave" value={dF(hwDelta(hwFull, 'low_f'))} sub="the lowest overnight temperature during a heat wave, median change" accent />
      <StatTile label="Night after it ends" value={dF(hwDelta(hwFull, 'after_low_f'))} sub="overnight low on the first night after the run breaks" accent />
      <StatTile label="Relief under {tFU(hwRule.relief_f)}" value="{n2(hwMed(hwFull, 'baseline', 'relief_h'))} h → {n2(hwMed(hwFull, 'last30', 'relief_h'))} h" sub="hours per heat-wave night below {tFU(hwRule.relief_f)}, 6 pm–8 am, median" accent />
    </div>
    <h3>The coolest night of a heat wave, then and now</h3>
    <Dumbbell rows={dRows(hwCompare, 'low_f', tF)} color={COOL} domain={[50, 75]} axis={(v) => axisT(v, units.f)} format={(v) => Math.round(v) + '°'} delta={dF} big={2} empty="Average of each wave's lowest overnight temperature, {yrs([hwB.start, hwB.end])} (hollow) → last 30 summers (filled)" />
    <h3>Hours of relief under {tFU(hwRule.relief_f)} on a heat-wave night</h3>
    <Dumbbell rows={dRows(hwCompare, 'relief_h', (v) => n2(v, 1) + ' h')} color={COOL} domain={[0, 12]} format={(v) => n2(v, 0) + ' h'} delta={(d) => sgn(d, 1) + ' h'} big={1} empty="Between 6 pm and 8 am, from the hourly readings; nights inside the wave" />
  </section>

  <section>
    <h2>Heat-wave nights warmed faster than ordinary nights</h2>
    <p class="muted">Summer nights in general are warmer in Los Angeles — that is the rest of this page. But at the basin airports, the nights inside heat waves have warmed <i>more</i> than the ordinary nights around them: the gap between "a warm summer night" and "a night you can't sleep" has opened at exactly the moment it matters. Inland, at March, neither has moved much.</p>
    <NightPairBars stations={hwCompare} />
  </section>

  <section class="card about">
    <b>What this is not saying.</b> These are readings at airports, taken hourly, and nothing has been adjusted. Every one of these stations has changed
    instruments at least once since the 1940s, and several sit in neighborhoods that have paved over. This page describes what each thermometer
    recorded; it does not explain why, and it says nothing about Los Angeles beyond these places. Hourly readings also miss a thermometer's true
    peak by about half a degree — consistently, in every decade — one more reason not to lean on the "hotter" question. Definition, completeness
    rules and the sensitivity to the definition: <a href="/methods#heatwaves">Methods</a>.
  </section>

  <h2 class="divider">Behind the story: nights across the whole year, at every station</h2>
{/if}

<section class="hero evidence" id="nights">
  <div class="text">
    <h2 class="big">A typical Los Angeles night is now warmer than {nightRank == null ? '—' : Math.round(nightRank)}% of the nights people had at that time of year in 1951–1980.</h2>
    <p class="lede">
      A typical day: warmer than {dayRank == null ? '—' : Math.round(dayRank)}%. If nothing had changed, both numbers would be 50. That is the whole
      site in one idea — take every reading from NOAA's hourly station records, ask <i>how unusual is this for this date, at this station?</i>,
      and watch the answer drift. The drift is much larger at night than by day.
    </p>
    <p class="small muted">
      Latest readings through {fmtISO(latest)}. "Typical" is the median station's average percentile over its last ten complete years, each day judged
      against that station's own 1951–1980 readings within a week of the same date (<a href="/methods#ranks">how</a>). Each chart is one
      thermometer at one place: it records the city growing around the station as well as the wider climate (<a href="/methods#attribution">more</a>).
    </p>
  </div>
</section>

{#if curveStations.length}
  <section>
    <div class="sechead">
      <h2>Every year as a ring, at every long-running station</h2>
      <div class="pillrow">
        <button class="pill" class:on={rankEl === 'tmax'} onclick={() => (rankEl = 'tmax')}>Days (daily high)</button>
        <button class="pill" class:on={rankEl === 'tmin'} onclick={() => (rankEl = 'tmin')}>Nights (daily low)</button>
        <button class="pill" class:on={rankEl === 'both'} onclick={() => (rankEl = 'both')}>Both</button>
      </div>
    </div>
    <p class="muted">Each spiral is one station: January at the top, the year running clockwise, and the distance from the centre the {rankEl === 'tmin' ? 'daily low' : rankEl === 'tmax' ? 'daily high' : 'daily high (outer, red) and low (inner, blue)'}, 15-day means on the station's own scale. One ring per year — the palest from the 1940s and 50s, the darkest the last few years, the bold one the year on the slider. The shaded rings are the middle 80% and middle 50% of the station's baseline years for each date and the dashed ring their median: a bold ring outside the shading is warmer than almost any baseline year at that date. The two badges are the station's <b>scores</b> — where a typical <span class="day">day</span> (red, top right) and a typical <span class="night">night</span> (blue, top left) of its last ten complete years fall among the baseline's for the same date; 50 would mean no change, 70 that a typical night now is warmer than 70% of the baseline's. Baseline is 1951–1980; † marks a station without that record, scored against its own earliest 20 complete years. Click a spiral for the station.</p>
    <YearScrubber years={spiralYears} bind:value={spiralYear} playable />
    <SpiralMap stations={curveStations} {curves} element={rankEl} year={spiralYear} center={region.center} zoom={region.zoom} onselect={(id) => goto(`/station/${id}#ranks`)} />
    <p class="small muted">Press play to watch the rings accumulate; drag the year to pick out one ring (drawn dark) against everything before it.</p>
  </section>

  <section>
    <h2>Two numbers per station</h2>
    <p class="muted">The same idea averaged over each station's last ten complete years: where a typical night and a typical day at each station now fall among 1951–1980 readings for the same time of year.</p>
    <div class="punch"><RankDots stations={allStations} /></div>
  </section>
{/if}

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
  <p class="small muted">Press play, or drag the year. Each pill is one station's count for that year (hover for the name); “≥” means the year is incomplete there and the count is a lower bound; stations with no data that year are hidden. Colors use one scale for every year. <a href="/stations">All LA stations, as a table →</a></p>
</section>

<section>
  <h2>What it feels like: nights that never cool below 70°F, days that reach 95°F</h2>
  <p class="muted">Percentiles are the fair comparison; these fixed thresholds are the lived experience — and a 70°F night means something different at the beach than in the valley. One row per station, longest records first: its own trend over its own complete years, with a 90% range. Filled dots are trends clearly different from zero.</p>
  <div class="two">
    <TrendForest stations={allStations} key="trend_warm70" label="Nights ≥ 70°F per year" unitLabel="nights" />
    <TrendForest stations={allStations} key="trend_hot95" label="Days ≥ 95°F per year" unitLabel="days" />
  </div>
</section>

<section>
  <h2>Why nights and days differ: the trend at each station</h2>
  <p class="muted">For every station, the trend in its June–August mean daily low (filled) against its mean daily high (hollow), over the station's own complete years. Nights lead at most stations; at a few inland and coastal-military sites, days do.</p>
  <div class="punch"><TrendPairs stations={allStations} /></div>
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

{#if reg?.metrics?.warm70 && reg?.metrics?.hot95}
  <section>
    <h2>Los Angeles as a whole — a model, not an average</h2>
    <p class="muted">Stations come and go, so a plain average of whatever stations exist each year would mostly track the network. These two charts come from a model that treats each station's missing years as unknowns and estimates what the typical station would have counted had every station reported every year, with a 90% band (<a href="/methods#regional">how, and how well it predicts held-out data</a>).</p>
    <div class="two">
      <RegionalIndex series={reg.metrics.warm70} from={reg.display_from} label="Nights ≥ 70°F per year, average station (modeled)" unitLabel="nights" baseline={[ix.baseline.start, ix.baseline.end]} height={210} compact />
      <RegionalIndex series={reg.metrics.hot95} from={reg.display_from} label="Days ≥ 95°F per year, average station (modeled)" unitLabel="days" baseline={[ix.baseline.start, ix.baseline.end]} height={210} compact />
    </div>
  </section>
{/if}

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
    margin-top: 2rem;
    max-width: 60rem;
  }
  .hero h1,
  .hero h2.big {
    font-size: 2.8rem;
    margin: 0 0 0.8rem;
    max-width: 26ch;
  }
  .hero.evidence h2.big {
    font-size: 2rem;
    max-width: 26ch;
  }
  .tiles3 {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1rem;
    margin: 1rem 0 1.4rem;
  }
  .three {
    display: grid;
    grid-template-columns: 1fr;
    gap: 0.6rem;
  }
  h3 {
    font-size: 1.05rem;
    margin: 1.2rem 0 0.2rem;
  }
  .def {
    font-size: 1.15rem;
    border-left: 4px solid #d94f22;
    margin: 0.8rem 0;
  }
  .divider {
    margin-top: 4rem;
    padding-top: 1.5rem;
    border-top: 1px solid #e8e1d5;
  }
  .day {
    color: #c2410c;
    font-weight: 600;
  }
  .night {
    color: #1c5cab;
    font-weight: 600;
  }
  @media (max-width: 800px) {
    .tiles3 {
      grid-template-columns: 1fr;
    }
  }
  .tiles {
    display: grid;
    grid-template-columns: 1fr;
    gap: 0.9rem;
  }
  .punch {
    max-width: 760px;
  }

  .panel {
    color: inherit;
    text-decoration: none;
  }

  .two {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1.2rem;
  }
  @media (max-width: 800px) {
    .two {
      grid-template-columns: 1fr;
    }
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
