<script>
  import { onMount } from 'svelte';
  import { page } from '$app/state';
  import { browser } from '$app/environment';
  import { replaceState, afterNavigate, goto } from '$app/navigation';
  import { dataUrl } from '$lib/data.js';
  import { units } from '$lib/units.svelte.js';
  import { fmtThresholdF, fmtC } from '$lib/units.js';
  import UsMap from '$lib/UsMap.svelte';
  import YearScrubber from '$lib/YearScrubber.svelte';

  let { data } = $props();
  let ix = $derived(data.index);
  let cols = $derived(ix.columns);
  const col = (r, name) => r[cols.indexOf(name)];
  let stations = $derived(
    ix.stations.map((r) => ({
      id: r[0], short: col(r, 'short'), state: col(r, 'state'), lat: col(r, 'lat'), lon: col(r, 'lon'),
      first_year: col(r, 'first_year'), last_year: col(r, 'last_year'), active: !!col(r, 'active'),
      hot95_baseline: col(r, 'hot95_baseline'), hot95_last10: col(r, 'hot95_last10'),
      warm70_baseline: col(r, 'warm70_baseline'), warm70_last10: col(r, 'warm70_last10'),
      frost_baseline: col(r, 'frost_baseline'), frost_last10: col(r, 'frost_last10'),
      tmin_trend: col(r, 'tmin_trend_per_decade_c'), tmax_trend: col(r, 'tmax_trend_per_decade_c'), suspect: !!col(r, 'suspect_step')
    }))
  );
  const METRICS = {
    warm70: { label: 'Nights ≥ 70°F', noun: 'nights', cool: false, m: 'warm', t: 70 },
    hot95: { label: 'Days ≥ 95°F', noun: 'days', cool: false, m: 'hot', t: 95 },
    frost32: { label: 'Frost nights', noun: 'nights', cool: true, m: 'frost', t: 32 }
  };
  let metric = $state('warm70');
  let year = $state(2025);
  let stateFilter = $state('');
  let activeOnly = $state(false);
  let restored = $state(false);
  let matrices = $state({});
  let mapRef;

  let years = $derived(Array.from({ length: ix.matrix.n_years }, (_, i) => ix.matrix.year0 + i).filter((y) => y >= 1890));
  let states = $derived([...new Set(stations.map((s) => s.state))].sort());

  async function loadMatrix(m) {
    if (matrices[m]) return;
    const buf = await (await fetch(dataUrl(`/data/us/matrix-${m}.bin`))).arrayBuffer();
    matrices = { ...matrices, [m]: new Int16Array(buf) };
  }
  onMount(async () => {
    const q = page.url.searchParams;
    if (q.get('m') in METRICS) metric = q.get('m');
    if (q.get('year')) year = Number(q.get('year'));
    else year = Math.max(...stations.filter((s) => s.active).map((s) => s.last_year)) - 1;
    if (q.get('state')) stateFilter = q.get('state');
    await loadMatrix(metric);
  });
  afterNavigate(() => (restored = true));
  $effect(() => {
    loadMatrix(metric);
  });
  $effect(() => {
    if (!browser || !restored) return;
    const q = new URLSearchParams({ m: metric, year: String(year) });
    if (stateFilter) q.set('state', stateFilter);
    if (!units.f) q.set('u', 'C');
    const target = '/us?' + q.toString();
    if (target !== window.location.pathname + window.location.search) replaceState(target, {});
  });

  let nY = $derived(ix.matrix.n_years);
  let values = $derived.by(() => {
    const mat = matrices[metric];
    if (!mat) return null;
    const k = year - ix.matrix.year0;
    const out = new Array(stations.length);
    for (let i = 0; i < stations.length; i++) {
      const v = k >= 0 && k < nY ? mat[i * nY + k] : -1;
      out[i] = activeOnly && !stations[i].active ? -1 : v;
    }
    return out;
  });
  // Fixed scale per metric: the 98th percentile of all station-years (extremes would wash out the map).
  let vmax = $derived.by(() => {
    const mat = matrices[metric];
    if (!mat) return 50;
    const vals = [];
    for (let i = 0; i < mat.length; i += 7) if (mat[i] >= 0) vals.push(mat[i]);
    vals.sort((a, b) => a - b);
    return Math.max(5, vals[Math.floor(vals.length * 0.98)] ?? 50);
  });
  let shown = $derived(stations.filter((s) => (!stateFilter || s.state === stateFilter) && (!activeOnly || s.active)));
  let ranked = $derived.by(() => {
    if (!values) return [];
    const rows = [];
    stations.forEach((s, i) => {
      if (stateFilter && s.state !== stateFilter) return;
      if (activeOnly && !s.active) return;
      const v = values[i];
      if (v == null || v === -1) return;
      rows.push({ s, v: v < -1 ? -v - 2 : v, lower: v < -1 });
    });
    rows.sort((a, b) => b.v - a.v);
    return rows;
  });
  let nWithData = $derived(ranked.length);
  let M = $derived(METRICS[metric]);
  function selectStation(id) {
    goto(`/station/${id}?m=${M.m}&t=${M.t}&year=${year}`);
  }
  let stateCenter = $derived.by(() => {
    if (!stateFilter) return null;
    const ss = stations.filter((s) => s.state === stateFilter);
    if (!ss.length) return null;
    return [ss.reduce((a, s) => a + s.lat, 0) / ss.length, ss.reduce((a, s) => a + s.lon, 0) / ss.length];
  });
  $effect(() => {
    if (stateCenter && mapRef) mapRef.flyTo(stateCenter[0], stateCenter[1], stateFilter === 'AK' ? 3.5 : 5.6);
  });
</script>

<svelte:head>
  <title>Every US station, any year · climate.sorkinlabs</title>
</svelte:head>

<h1 class="title">{M.label} in {year}, across the United States</h1>
<p class="lede">{stations.length.toLocaleString()} weather stations with 20+ years of hourly records since 1940 — {stations.filter((s) => s.active).length.toLocaleString()} still reporting. Press play to watch the decades go by; zoom in for counts; click a station for its full record.</p>

<div class="pillrow controls">
  {#each Object.entries(METRICS) as [k, m] (k)}
    <button class="pill" class:on={metric === k} onclick={() => (metric = k)}>{m.label}</button>
  {/each}
  <span class="sep"></span>
  <select bind:value={stateFilter} aria-label="State">
    <option value="">All states</option>
    {#each states as st (st)}<option value={st}>{st}</option>{/each}
  </select>
  <label class="small"><input type="checkbox" bind:checked={activeOnly} /> still reporting only</label>
</div>

<YearScrubber {years} bind:value={year} playable stepMs={180} />

<UsMap bind:this={mapRef} {stations} {values} {vmax} cool={M.cool} unitLabel={M.noun} onselect={selectStation} center={ix.region.center} zoom={ix.region.zoom} {stateFilter} />
<p class="small muted">
  {#if values}{nWithData.toLocaleString()} stations have data for {year}{stateFilter ? ` in ${stateFilter}` : ''}. Color scale is fixed across years (top = {vmax} {M.noun}, the 98th percentile of all station-years); gray-ringed circles are lower bounds from incomplete years.{:else}Loading…{/if}
</p>

{#if ranked.length}
  <div class="lists">
    <div>
      <h2>Most {M.noun} in {year}</h2>
      <ol>
        {#each ranked.slice(0, 15) as r (r.s.id)}
          <li><a href="/station/{r.s.id}?m={M.m}&t={M.t}&year={year}">{r.s.short}, {r.s.state}</a> <span class="muted">{r.lower ? '≥ ' : ''}{r.v}</span></li>
        {/each}
      </ol>
    </div>
    <div>
      <h2>Biggest change since {ix.baseline.start}–{ix.baseline.end}</h2>
      <ol>
        {#each shown.filter((s) => s.active && !s.suspect && s[metric === 'frost32' ? 'frost_baseline' : metric + '_baseline'] != null).sort((a, b) => {
          const key = metric === 'frost32' ? 'frost' : metric;
          const da = a[key + '_last10'] - a[key + '_baseline'];
          const db = b[key + '_last10'] - b[key + '_baseline'];
          return metric === 'frost32' ? da - db : db - da;
        }).slice(0, 15) as s (s.id)}
          {@const key = metric === 'frost32' ? 'frost' : metric}
          <li><a href="/station/{s.id}?m={M.m}&t={M.t}">{s.short}, {s.state}</a> <span class="muted">{s[key + '_baseline'].toFixed(0)} → {s[key + '_last10'].toFixed(0)} per year</span></li>
        {/each}
      </ol>
    </div>
  </div>
  {#if shown.some((s) => s.suspect)}
    <p class="small muted">Excluded from the change ranking as suspected sensor/site changes under one station id (their own 5-year mean jumped more than 2.5 °C): {shown.filter((s) => s.suspect).map((s) => `${s.short}, ${s.state}`).join('; ')}.</p>
  {/if}
{/if}

<style>
  .title {
    margin: 1.2rem 0 0.2rem;
  }
  .controls {
    margin-bottom: 0.4rem;
  }
  .sep {
    width: 1px;
    height: 1.4rem;
    background: #d9d2c5;
    margin: 0 0.3rem;
  }
  select {
    font: inherit;
    font-size: 0.9rem;
    padding: 0.28rem 0.6rem;
    border-radius: 999px;
    border: 1px solid #d9d2c5;
    background: #fffdf9;
  }
  .lists {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1.5rem;
  }
  .lists h2 {
    font-size: 1.1rem;
    margin-top: 1.4rem;
  }
  ol {
    padding-left: 1.4rem;
    margin: 0;
    font-size: 0.95rem;
  }
  li {
    padding: 0.1rem 0;
  }
  @media (max-width: 720px) {
    .lists {
      grid-template-columns: 1fr;
    }
  }
</style>
