<script>
  import { onMount } from 'svelte';
  import { page } from '$app/state';
  import { browser } from '$app/environment';
  import { replaceState, afterNavigate } from '$app/navigation';
  import { dataUrl } from '$lib/data.js';
  import { units } from '$lib/units.svelte.js';
  import { fmtC, fmtTenths, fmtThresholdF } from '$lib/units.js';
  import { fmtISO, fmtDate, daysInYear, daysInMonth } from '$lib/dates.js';
  import { FAMILIES, annualCounts, monthlyCounts, seasonCounts, exportedAnnual, exportedMonthly, exportedAnnualLower, exportedMonthlyLower, exportedAnnualExpected, exportedMonthlyExpected, missingRanges, isStandard, yearsOf, partialOf, trendLabel as fmtTrend } from '$lib/metrics.js';
  import { HEAT, COOL } from '$lib/palette.js';
  import Controls from '$lib/Controls.svelte';
  import YearScrubber from '$lib/YearScrubber.svelte';
  import AnnualBars from '$lib/AnnualBars.svelte';
  import HeatCalendar from '$lib/HeatCalendar.svelte';
  import DailyRibbon from '$lib/DailyRibbon.svelte';
  import RawTable from '$lib/RawTable.svelte';
  import WindowsTable from '$lib/WindowsTable.svelte';
  import MethodsNote from '$lib/MethodsNote.svelte';
  import HourlyPanel from '$lib/HourlyPanel.svelte';
  import IndexLines from '$lib/IndexLines.svelte';
  import RankHeatmap from '$lib/RankHeatmap.svelte';
  import YearCurves from '$lib/YearCurves.svelte';
  import { loadRanks } from '$lib/ranks.js';

  let { data } = $props();
  let s = $derived(data.summary);
  // "Other stations" switcher: the curated region's list when this station belongs to one,
  // otherwise the stations of the same state from the national index (loaded lazily).
  let peers = $state([]);
  $effect(() => {
    if (!s) return;
    if (s.regions?.includes('la')) {
      peers = data.index.stations;
      return;
    }
    fetch(dataUrl('/data/us/index.json')).then((r) => r.json()).then((j) => {
      const c = j.columns;
      peers = j.stations
        .filter((r) => r[c.indexOf('state')] === s.state)
        .map((r) => ({ id: r[0], short: r[c.indexOf('short')], first_year: r[c.indexOf('first_year')], last_year: r[c.indexOf('last_year')], active: !!r[c.indexOf('active')] }))
        .sort((a, b) => a.short.localeCompare(b.short));
    });
  });
  let others = $derived(peers);

  // URL-driven state: ?m=hot&t=95&year=2024 (u= handled in the layout).
  let family = $state('hot');
  let threshold = $state(95);
  let year = $state(null);
  let restored = $state(false);

  let defaultYear = $derived.by(() => {
    const a = s.annual;
    const last = a.year[a.year.length - 1];
    const lastValid = a.days_valid_tmax[a.year.length - 1];
    return a.partial[a.year.length - 1] && lastValid >= s.completeness.partial_year_min_days ? last : s.last_complete_year ?? last;
  });

  onMount(() => {
    if (!s) return;
    const q = page.url.searchParams;
    if (q.get('m') in FAMILIES) family = q.get('m');
    const t = Number(q.get('t'));
    if (Number.isFinite(t) && q.get('t') !== null) threshold = Math.round(t);
    else threshold = s.thresholds_f[FAMILIES[family].key][family === 'hot' || family === 'warm' ? 1 : 0];
    const y = Number(q.get('year'));
    year = Number.isFinite(y) && s.annual.year.includes(y) ? y : defaultYear;
  });
  afterNavigate(() => (restored = true));
  $effect(() => {
    if (!browser || !restored) return;
    const q = new URLSearchParams();
    if (family !== 'hot') q.set('m', family);
    q.set('t', String(threshold));
    if (year != null) q.set('year', String(year));
    if (!units.f) q.set('u', 'C');
    const target = window.location.pathname + '?' + q.toString();
    if (target !== window.location.pathname + window.location.search) replaceState(target, {});
  });

  // hourly layer (ISD), if this station is an airport with one
  let hourly = $state(null);
  $effect(() => {
    if (!s) return;
    const id = s.id;
    hourly = null;
    fetch(dataUrl(`/data/hourly/${id}.json`)).then((r) => (r.ok ? r.json() : null)).then((h) => {
      if (h && h.ghcn === id) hourly = h;
    }).catch(() => {});
  });

  // daily.json is loaded lazily: needed for the daily explorer, raw table, and custom thresholds.
  let daily = $state(null);
  let ranks = $state(null);
  let rankEl = $state('tmin');
  let curveMode = $state('all');
  let rankSmooth = $state(false);
  $effect(() => {
    const id = s.id;
    ranks = null;
    if (s.has_baseline) loadRanks(id).then((r) => { if (s.id === id) ranks = r; }).catch(() => {});
  });
  $effect(() => {
    if (!s) return;
    const id = s.id;
    daily = null;
    fetch(dataUrl(`/data/stations/${id}/daily.json`)).then((r) => r.json()).then((d) => {
      if (d.id === id) daily = d;
    });
  });

  let fam = $derived(FAMILIES[family]);
  let standard = $derived(isStandard(s, family, threshold));
  let years = $derived(yearsOf(s, family));
  let partial = $derived(partialOf(s, family));
  let annualBoth = $derived.by(() => {
    if (standard) return { values: exportedAnnual(s, family, threshold), lower: exportedAnnualLower(s, family, threshold) ?? [], exp: exportedAnnualExpected(s, family, threshold) ?? [] };
    if (!daily) return { values: years.map(() => null), lower: [], exp: [] };
    return family === 'frost' ? seasonCounts(daily, s, family, threshold) : annualCounts(daily, s, family, threshold);
  });
  let annual = $derived(annualBoth.values);
  let annualLower = $derived(annualBoth.lower);
  let annualExp = $derived(annualBoth.exp);
  let monthlyBoth = $derived.by(() => {
    if (standard) return { values: exportedMonthly(s, family, threshold), lower: exportedMonthlyLower(s, family, threshold) ?? [], exp: exportedMonthlyExpected(s, family, threshold) ?? [] };
    if (!daily) return { values: s.monthly.year.map(() => null), lower: [], exp: [] };
    return monthlyCounts(daily, s, family, threshold);
  });
  let monthly = $derived(monthlyBoth.values);
  let monthlyLower = $derived(monthlyBoth.lower);
  let monthlyExp = $derived(monthlyBoth.exp);
  let daysValid = $derived(family === 'frost' ? (fam.elem === 'tmax' ? s.cold_season.days_valid_tmax : s.cold_season.days_valid_tmin) : fam.elem === 'tmax' ? s.annual.days_valid_tmax : s.annual.days_valid_tmin);
  let daysTotal = $derived(years.map((y) => daysInYear(y)));
  let monthlyDaysValid = $derived(fam.elem === 'tmax' ? s.monthly.days_valid_tmax : s.monthly.days_valid_tmin);
  let monthlyDaysTotal = $derived(s.monthly.year.map((y, k) => daysInMonth(y, s.monthly.month[k])));
  // Where the gaps are, for the selected year (calendar year; cold seasons use Jul-Jun).
  let gaps = $derived.by(() => {
    if (!daily || year == null) return [];
    const from = family === 'frost' ? new Date(Date.UTC(year - 1, 6, 1)) : new Date(Date.UTC(year, 0, 1));
    const to = family === 'frost' ? new Date(Date.UTC(year, 5, 30)) : new Date(Date.UTC(year, 11, 31));
    return missingRanges(daily, fam.elem, from, to);
  });
  const fmtGap = (g) => (g.days === 1 ? fmtDate(g.from, { year: false }) : `${fmtDate(g.from, { year: false })} – ${fmtDate(g.to, { year: false })} (${g.days} days)`);
  // Long runs are listed; scattered one- or two-day holes are summarized.
  let gapText = $derived.by(() => {
    const runs = gaps.filter((g) => g.days >= 3);
    const scattered = gaps.filter((g) => g.days < 3);
    const parts = runs.map(fmtGap);
    if (scattered.length) {
      const n = scattered.reduce((a, g) => a + g.days, 0);
      parts.push(`${n} scattered day${n === 1 ? '' : 's'} (${fmtDate(scattered[0].from, { year: false })} – ${fmtDate(scattered[scattered.length - 1].to, { year: false })})`);
    }
    return parts.join('; ');
  });
  let monthlyComplete = $derived(fam.elem === 'tmax' ? s.monthly.complete_tmax : s.monthly.complete_tmin);
  let decades = $derived.by(() => {
    if (!standard) return null;
    const d = s.decades;
    const block = family === 'frost' ? d.season_cold_nights : d[fam.key];
    return { decade: d.decade, value: block?.[String(threshold)] ?? d.decade.map(() => null), partial: d.partial };
  });
  const stem = { hot: 'hot', warm: 'warm', coldday: 'coldday', frost: 'coldnight' };
  let trendLabel = $derived.by(() => {
    if (!standard) return '';
    const t = s.trends?.[`${stem[family]}_${threshold}`] ?? (family === 'frost' && threshold === 32 ? s.trends?.frost_nights : null);
    return fmtTrend(t, fam.noun);
  });
  let baseline = $derived.by(() => {
    const w = s.windows?.baseline;
    if (!w || !standard) return null;
    const v = family === 'frost' ? w.season?.[`coldnight_${threshold}`] : w[`${stem[family]}_${threshold}`];
    return v == null ? null : { years: w.years, value: v };
  });
  let selectedCount = $derived.by(() => {
    const k = years.indexOf(year);
    return k < 0 ? null : annual[k];
  });
  let selectedLower = $derived.by(() => {
    const k = years.indexOf(year);
    return k < 0 ? null : annualLower[k];
  });
  let selectedMissing = $derived(gaps.reduce((n, g) => n + g.days, 0));
  let selectedExp = $derived.by(() => {
    const k = years.indexOf(year);
    return k < 0 ? null : annualExp[k];
  });
  let selectedComplete = $derived.by(() => {
    const k = years.indexOf(year);
    const flags = family === 'frost' ? (fam.elem === 'tmax' ? s.cold_season.complete_tmax : s.cold_season.complete_tmin) : fam.elem === 'tmax' ? s.annual.complete_tmax : s.annual.complete_tmin;
    return k < 0 ? true : flags[k];
  });
  let incompleteYears = $derived(new Set(years.filter((y, k) => annual[k] == null && !partial[k])));
  let thrLabel = $derived(fmtThresholdF(threshold, units.f));
  let title = $derived(`${fam.label} · ${s.short}`);
  let hero = $derived.by(() => {
    const w = s.windows;
    if (!w?.baseline || !standard) return null;
    const key = family === 'frost' ? null : `${stem[family]}_${threshold}`;
    const b = key ? w.baseline[key] : w.baseline.season?.[`coldnight_${threshold}`];
    const l = key ? w.last10[key] : w.last10.season?.[`coldnight_${threshold}`];
    return b == null || l == null ? null : { b, l };
  });
  // Only the large detected changes (>= 0.8 °C in either element) are marked on the chart;
  // the full list is in the table below.
  let breakAnnotations = $derived(
    (s.homogenized?.breaks ?? [])
      .filter((b) => Math.abs(b.tmax_c) >= 0.8 || Math.abs(b.tmin_c) >= 0.8)
      .map((b) => ({ year: b.year, label: '' }))
  );
  const modelKey = { hot: { 95: 'hot95', 100: 'hot100' }, warm: { 65: 'warm65', 70: 'warm70' }, frost: { 32: 'frost32' } };
  let modeled = $derived(standard ? (s.modeled?.[modelKey[family]?.[threshold]] ?? null) : null);
  let annotations = $derived([
    ...(s.notable ?? []).map((n) => ({ year: Number(String(n.date).slice(0, 4)), label: n.label })),
    ...breakAnnotations
  ]);
  let homog = $derived(s.homogenized);
  const shiftF = (c) => (c == null ? '—' : fmtC(c, units.f, { sign: true, delta: true }));
</script>

<svelte:head>
  <title>{data.short} — hot days, warm nights and frost · climate.sorkinlabs</title>
  <meta name="description" content="{data.short}: days above 95°F, warm nights and frost nights every year, from NOAA's raw daily station records." />
</svelte:head>

{#if !s}
  <div class="head"><div><p class="crumb"><a href="/us">Stations</a></p><h1>{data.short}</h1><p class="meta muted">Loading the station record…</p></div></div>
{:else}

<div class="head">
  <div>
    <p class="crumb"><a href={s.regions?.includes('la') ? '/map' : '/us'}>Stations</a> · {s.regions?.includes('la') ? 'Greater Los Angeles' : s.state}</p>
    <h1>{s.short}</h1>
    <p class="meta muted">
      {s.name} · NOAA {s.id}{#if s.icao} · {s.icao}{/if} · {Math.round(s.elev_m * 3.281)} ft · hourly readings ·
      {#if s.active}records since {s.first_year} · latest reading {fmtISO(s.last_date)}{:else}records {s.first_year}–{s.last_year} · <b>station closed</b> (last reading {fmtISO(s.last_date)}){/if}
    </p>
  </div>
  <div class="switch">
    <label class="small muted" for="st">Other stations</label>
    <select id="st" onchange={(e) => (window.location.href = `/station/${e.target.value}${window.location.search}`)}>
      {#each others as o (o.id)}
        <option value={o.id} selected={o.id === s.id}>{o.short} ({o.first_year}–{o.active ? '' : o.last_year})</option>
      {/each}
    </select>
  </div>
</div>

{#if s.suspect_step}
  <p class="warn">⚠ Suspected sensor or site change: {s.suspect_step}. Treat trends and then-vs-now figures here with caution.</p>
{/if}

{#if hero}
  <div class="hero">
    <div class="stat">
      <span class="lbl">{fam.label} ({fam.unit} {fam.op === '>=' ? '≥' : '≤'} {thrLabel}) per year, {s.windows.baseline.years[0]}–{s.windows.baseline.years[1]}</span>
      <span class="val">{hero.b.toFixed(hero.b < 10 ? 1 : 0)}</span>
    </div>
    <div class="arrow">→</div>
    <div class="stat">
      <span class="lbl">per year, {s.windows.last10.years[0]}–{s.windows.last10.years[1]}</span>
      <span class="val" class:up={hero.l > hero.b && family !== 'frost' && family !== 'coldday'} class:down={hero.l < hero.b && (family === 'frost' || family === 'coldday')}>{hero.l.toFixed(hero.l < 10 ? 1 : 0)}</span>
    </div>
    <div class="stat">
      <span class="lbl">daily lows, trend since {s.baseline.start}</span>
      <span class="val small-val">{fmtC(s.trends?.tmin_mean_c?.slope_per_decade, units.f, { sign: true, delta: true })}<span class="per"> / decade</span></span>
    </div>
    <div class="stat">
      <span class="lbl">daily highs, trend since {s.baseline.start}</span>
      <span class="val small-val">{fmtC(s.trends?.tmax_mean_c?.slope_per_decade, units.f, { sign: true, delta: true })}<span class="per"> / decade</span></span>
    </div>
  </div>
{/if}

<Controls thresholds={s.thresholds_f} bind:family bind:threshold />

<h2>{fam.label} per year — {fam.unit} {fam.op === '>=' ? 'at least' : 'at most'} {thrLabel}</h2>
<p class="muted small">
  {#if family === 'frost'}Cold seasons run July–June and are labeled by the January year.{/if}
  {#if !standard && !daily}Computing from the daily record…{/if}
  {#if selectedCount != null}<b>{year}: {selectedCount} {fam.noun}{partial[years.indexOf(year)] ? ' so far' : ''}.</b>{#if !selectedComplete && selectedMissing} {selectedMissing} days not observed, but on dates that {selectedExp === 0 ? 'have never' : 'rarely'} reach {thrLabel} here (expected effect {selectedExp?.toFixed(1)} {fam.noun}){#if gaps.length}: {gapText}{/if}.{/if}{:else if selectedLower != null && year != null}<b>{year}: at least {selectedLower} {fam.noun}</b> — {selectedMissing} days not observed, expected to add about {selectedExp?.toFixed(1)} {fam.noun}{#if gaps.length}: {gapText}{/if}.{/if}
</p>
{#if s.suspect_years && Object.keys(s.suspect_years).length}
  <p class="small muted">Excluded as far off this station's own trend line (likely archive or sensor artifacts): {Object.entries(s.suspect_years).map(([y, m]) => `${y} (${m})`).join('; ')}.</p>
{/if}
<AnnualBars {years} values={annual} lower={annualLower} expected={annualExp} {modeled} {daysValid} {daysTotal} {partial} {decades} selected={year} onselect={(y) => (year = y)} color={family === 'hot' || family === 'warm' ? HEAT : COOL} unitLabel={fam.noun} {trendLabel} {baseline} {annotations} />

{#if year != null}
  <YearScrubber years={s.annual.year} bind:value={year} disabled={incompleteYears} />
{/if}

<h2>By month</h2>
<HeatCalendar years={s.monthly.year} months={s.monthly.month} values={monthly} lower={monthlyLower} expected={monthlyExp} daysValid={monthlyDaysValid} daysTotal={monthlyDaysTotal} complete={monthlyComplete} cool={family === 'frost' || family === 'coldday'} selected={year} onselect={(y) => (year = y)} unitLabel={fam.noun} />

{#if s.has_baseline}
  <h2 id="ranks">Every {rankEl === 'tmin' ? 'night' : 'day'} since 1951, ranked against the same date in 1951–1980</h2>
  <div class="row">
    <p class="muted">
      Each reading placed within this station's own 1951–1980 readings for the same time of year: blue, cooler than most; red, warmer than most.
      {#if s.indices?.windows?.last10?.rank_tmin != null}Over the last ten years a typical night here sits at the <b>{Math.round(s.indices.windows.last10.rank_tmin)}th</b> percentile of those baseline nights and a typical day at the <b>{Math.round(s.indices.windows.last10.rank_tmax)}th</b>; 50 would mean no change.{/if}
    </p>
    <div class="ctl">
      <div class="seg" role="tablist" aria-label="Nights or days">
        <button class:on={rankEl === 'tmin'} onclick={() => (rankEl = 'tmin')}>Nights</button>
        <button class:on={rankEl === 'tmax'} onclick={() => (rankEl = 'tmax')}>Days</button>
      </div>
      <label class="small"><input type="checkbox" bind:checked={rankSmooth} /> 7-day means</label>
    </div>
  </div>
  {#if ranks}
    <RankHeatmap {ranks} element={rankEl} rowPx={4} smooth={rankSmooth ? 7 : 1} />
  {/if}
  {#if daily}
    <h3>The same years as lines</h3>
    <div class="row">
      <p class="muted small">One line per year, lighter = older, over the 1951–1980 envelope for each date. {rankEl === 'tmin' ? 'Nights' : 'Days'} that ride above the band are warmer than almost any at that date in the baseline.</p>
      <div class="seg" role="tablist" aria-label="Which years">
        <button class:on={curveMode === 'all'} onclick={() => (curveMode = 'all')}>All years</button>
        <button class:on={curveMode === 'selected'} onclick={() => (curveMode = 'selected')}>Every 5th + last 5</button>
      </div>
    </div>
    <YearCurves {daily} element={rankEl} mode={curveMode} />
  {/if}
{/if}

{#if s.indices}
  <h2 id="distribution">How this station's temperatures have shifted</h2>
  <p class="muted">
    Against this station's own 1951–1980 calendar-day percentiles: the share of nights and days in the warmest tenth
    (TN90p, TX90p) and the coolest tenth (TN10p, TX10p). In an unchanged climate each would stay near 10%.
    {#if s.trends?.dtr_c}The daily temperature range (high minus low) is {s.trends.dtr_c.significant ? (s.trends.dtr_c.slope_per_decade < 0 ? 'narrowing' : 'widening') : 'not clearly changing'}{s.trends.dtr_c.significant ? ` by ${fmtC(Math.abs(s.trends.dtr_c.slope_per_decade), units.f, { delta: true })} per decade` : ''}.{/if}
  </p>
  <div class="two">
    <IndexLines series={s.indices} key="tn90p" label="Unusually warm nights (TN90p)" color="#2a78d6" trend={s.trends?.tn90p} unit="% of nights" height={200} />
    <IndexLines series={s.indices} key="tx90p" label="Unusually warm days (TX90p)" color="#d94f22" trend={s.trends?.tx90p} unit="% of days" height={200} />
    <IndexLines series={s.indices} key="tn10p" label="Unusually cool nights (TN10p)" color="#2a78d6" trend={s.trends?.tn10p} unit="% of nights" height={200} />
    <IndexLines series={s.indices} key="tx10p" label="Unusually cool days (TX10p)" color="#d94f22" trend={s.trends?.tx10p} unit="% of days" height={200} />
  </div>
{/if}

<h2>Then and now</h2>
<WindowsTable summary={s} />

{#if hourly}
  <h2 id="hourly">Hour by hour</h2>
  <HourlyPanel {hourly} {year} {family} onselect={(y) => (year = y)} />
{/if}

<h2 id="daily">{year}, day by day</h2>
{#if daily && year != null}
  {#if gaps.length}
    <p class="muted small">Not observed in {year}{family === 'frost' ? ' (Jul–Jun season)' : ''}: {gapText} — {selectedMissing} days in all.</p>
  {/if}
  <DailyRibbon {daily} {year} {family} {threshold} />
  <details class="raw">
    <summary>Raw readings for {year}</summary>
    <RawTable {daily} summary={s} {year} />
  </details>
{:else}
  <p class="muted">Loading the daily record…</p>
{/if}

{#if homog}
  <h2>What NOAA's homogenization says about this station</h2>
  <p class="muted">
    This is a US Historical Climatology Network station, so NOAA also publishes a homogenized version of its monthly record
    (USHCN v2.5), adjusted by comparison with neighboring stations for observation-time changes, instrument changes and moves.
    The steps NOAA detected in the raw record — and how much the raw values shifted relative to neighbors — are:
  </p>
  <div class="scroll">
    <table class="data">
      <thead><tr><th>Year</th><th class="num">Daily highs shifted by</th><th class="num">Daily lows shifted by</th></tr></thead>
      <tbody>
        {#each homog.breaks as b (b.year)}
          <tr><td>{b.year}</td><td class="num">{shiftF(b.tmax_c)}</td><td class="num">{shiftF(b.tmin_c)}</td></tr>
        {/each}
      </tbody>
    </table>
  </div>
  {#if homog.windows?.baseline}
    <p class="muted">
      Applying NOAA's monthly adjustments to the daily readings and recounting (an estimate — NOAA does not publish homogenized daily data):
    </p>
    <div class="scroll">
      <table class="data">
        <thead><tr><th>Per year</th><th class="num">{homog.windows.baseline.years[0]}–{homog.windows.baseline.years[1]} raw</th><th class="num">homogenized</th><th class="num">{homog.windows.last10.years[0]}–{homog.windows.last10.years[1]} raw</th><th class="num">homogenized</th></tr></thead>
        <tbody>
          <tr><td>Days at or above {fmtThresholdF(95, units.f)}</td><td class="num">{s.windows.baseline.hot_95?.toFixed(1)}</td><td class="num">{homog.windows.baseline.hot_95_adj?.toFixed(1) ?? '—'}</td><td class="num">{s.windows.last10.hot_95?.toFixed(1)}</td><td class="num">{homog.windows.last10.hot_95_adj?.toFixed(1) ?? '—'}</td></tr>
          <tr><td>Nights at or above {fmtThresholdF(70, units.f)}</td><td class="num">{s.windows.baseline.warm_70?.toFixed(1)}</td><td class="num">{homog.windows.baseline.warm_70_adj?.toFixed(1) ?? '—'}</td><td class="num">{s.windows.last10.warm_70?.toFixed(1)}</td><td class="num">{homog.windows.last10.warm_70_adj?.toFixed(1) ?? '—'}</td></tr>
        </tbody>
      </table>
    </div>
  {/if}
  <p class="small muted">The charts on this page show the raw record; changes of at least {fmtC(0.8, units.f, { delta: true })} are marked ▼ on the yearly chart. See <a href="/methods#homogenization">Methods</a>.</p>
{/if}

<h2>About this record</h2>
<MethodsNote summary={s} />
{/if}

<style>
  .head {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    gap: 1rem;
    flex-wrap: wrap;
    margin-top: 1.2rem;
  }
  .crumb {
    margin: 0;
    font-size: 0.85rem;
    color: #898781;
  }
  h1 {
    margin: 0.1rem 0 0.2rem;
  }
  .meta {
    margin: 0;
    font-size: 0.9rem;
  }
  .switch {
    display: grid;
    gap: 0.2rem;
  }
  select {
    font: inherit;
    font-size: 0.9rem;
    padding: 0.3rem 0.6rem;
    border-radius: 8px;
    border: 1px solid #d9d2c5;
    background: #fffdf9;
  }
  .hero {
    display: flex;
    gap: 1.2rem;
    align-items: center;
    flex-wrap: wrap;
    margin: 1.4rem 0 0.8rem;
  }
  .stat {
    display: grid;
    gap: 0.1rem;
  }
  .stat .lbl {
    font-size: 0.8rem;
    color: #52514e;
    max-width: 14rem;
    line-height: 1.3;
  }
  .stat .val {
    font-size: 2.6rem;
    font-weight: 750;
    line-height: 1;
    color: #1f1b16;
  }
  .stat .val.up {
    color: #c2410c;
  }
  .stat .val.down {
    color: #1c5cab;
  }
  .stat .small-val {
    font-size: 1.7rem;
  }
  .per {
    font-size: 0.9rem;
    font-weight: 500;
    color: #52514e;
  }
  .arrow {
    font-size: 2rem;
    color: #b8b2a7;
  }
  .raw {
    margin-top: 1rem;
  }
  .two {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem 1.4rem;
  }
  .row {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1rem;
    flex-wrap: wrap;
  }
  .ctl {
    display: flex;
    gap: 0.8rem;
    align-items: center;
    flex: none;
  }
  .seg {
    display: inline-flex;
    border: 1px solid #c9c2b6;
    border-radius: 999px;
    overflow: hidden;
    flex: none;
  }
  .seg button {
    border: 0;
    background: transparent;
    padding: 0.3rem 0.8rem;
    font: inherit;
    font-size: 0.85rem;
    color: #52514e;
    cursor: pointer;
  }
  .seg button.on {
    background: #2b2722;
    color: #fffdf9;
  }
  @media (max-width: 800px) {
    .two {
      grid-template-columns: 1fr;
    }
  }
  .warn {
    background: #fff4e5;
    border: 1px solid #f0c98a;
    border-radius: 10px;
    padding: 0.6rem 0.9rem;
    font-size: 0.92rem;
    margin: 1rem 0 0;
  }
  .raw summary {
    cursor: pointer;
    font-weight: 600;
  }
</style>
