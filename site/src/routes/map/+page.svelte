<script>
  import { onMount } from 'svelte';
  import { page } from '$app/state';
  import { browser } from '$app/environment';
  import { replaceState, afterNavigate, goto } from '$app/navigation';
    import { dataUrl } from '$lib/data.js';
  import { units } from '$lib/units.svelte.js';
  import { fmtThresholdF } from '$lib/units.js';
  import { FAMILIES, exportedAnnual, yearsOf } from '$lib/metrics.js';
  import StationMap from '$lib/StationMap.svelte';
  import YearScrubber from '$lib/YearScrubber.svelte';

  let { data } = $props();
  let region = $derived(data.index.regions[0]);
  let stations = $derived(data.index.stations.filter((s) => s.region === region.id));

  let family = $state('warm');
  let threshold = $state(70);
  let year = $state(2025);
  let restored = $state(false);
  let summaries = $state({});

  onMount(async () => {
    const q = page.url.searchParams;
    if (q.get('m') in FAMILIES) family = q.get('m');
    if (q.get('t')) threshold = Number(q.get('t'));
    if (q.get('year')) year = Number(q.get('year'));
    else year = Math.max(...stations.filter((s) => s.active).map((s) => s.last_complete_year ?? 0));
    const all = await Promise.all(stations.map((s) => fetch(dataUrl(`/data/stations/${s.id}/summary.json`)).then((r) => r.json())));
    const out = {};
    for (const s of all) out[s.id] = s;
    summaries = out;
  });
  afterNavigate(() => (restored = true));
  $effect(() => {
    if (!browser || !restored) return;
    const q = new URLSearchParams({ m: family, t: String(threshold), year: String(year) });
    if (!units.f) q.set('u', 'C');
    const target = '/map?' + q.toString();
    if (target !== window.location.pathname + window.location.search) replaceState(target, {});
  });
  function setFamily(f) {
    family = f;
    threshold = data.index.thresholds_f[FAMILIES[f].key][f === 'hot' || f === 'warm' ? 1 : 0];
  }
  let fam = $derived(FAMILIES[family]);
  let standard = $derived(data.index.thresholds_f[fam.key]);
  let allYears = $derived.by(() => {
    const y0 = Math.min(...stations.map((s) => s.first_year));
    const y1 = Math.max(...stations.map((s) => s.last_year));
    return Array.from({ length: y1 - y0 + 1 }, (_, i) => y0 + i);
  });
  let values = $derived.by(() => {
    const m = new Map();
    for (const s of stations) {
      const sm = summaries[s.id];
      if (!sm) {
        m.set(s.id, null);
        continue;
      }
      const series = exportedAnnual(sm, family, threshold);
      const ys = yearsOf(sm, family);
      const k = ys.indexOf(year);
      m.set(s.id, k < 0 || !series ? null : series[k]);
    }
    return m;
  });
  let loaded = $derived(Object.keys(summaries).length === stations.length);
  let ranked = $derived([...stations].map((s) => ({ s, v: values.get(s.id) })).sort((a, b) => (b.v ?? -1) - (a.v ?? -1)));
  const closedNote = (s) => (s.active ? '' : ` (closed ${s.last_year})`);
</script>

<svelte:head>
  <title>Stations · climate.sorkinlabs</title>
</svelte:head>

<h1 class="title">{fam.label} in {year}</h1>
<p class="lede">{fam.noun} with a {fam.unit} {fam.op === '>=' ? 'at least' : 'at most'} {fmtThresholdF(threshold, units.f)}, at each {region.name} station. Drag the year. Click a station for its full record.</p>

<div class="pillrow">
  {#each Object.entries(FAMILIES) as [k, f] (k)}
    <button class="pill" class:on={family === k} onclick={() => setFamily(k)}>{f.label}</button>
  {/each}
  <span class="sep"></span>
  {#each standard as t (t)}
    <button class="pill heat" class:on={threshold === t} onclick={() => (threshold = t)}>{fmtThresholdF(t, units.f)}</button>
  {/each}
</div>

<YearScrubber years={allYears} bind:value={year} playable />

<StationMap {stations} {values} unitLabel={fam.noun} cool={family === 'frost' || family === 'coldday'} center={region.center} zoom={region.zoom} onselect={(id) => goto(`/station/${id}?m=${family}&t=${threshold}&year=${year}`)} />
{#if !loaded}<p class="muted small">Loading station records…</p>{/if}

<div class="rank">
  {#each ranked as r (r.s.id)}
    <a class="row" href="/station/{r.s.id}?m={family}&t={threshold}&year={year}">
      <span class="nm">{r.s.short}<span class="muted small">{closedNote(r.s)}</span></span>
      <span class="bar"><i style:width="{r.v == null ? 0 : (100 * r.v) / Math.max(1, ranked[0].v ?? 1)}%"></i></span>
      <span class="vl">{r.v == null ? 'no complete data' : `${r.v} ${fam.noun}`}</span>
    </a>
  {/each}
</div>
<p class="small muted">Cold-night counts use July–June seasons labeled by the January year. A station shows "no complete data" when fewer than 90% of that year's days were observed.</p>

<style>
  .title {
    margin: 1.2rem 0 0.2rem;
  }
  .sep {
    width: 1px;
    height: 1.4rem;
    background: #d9d2c5;
    margin: 0 0.3rem;
  }
  .rank {
    display: grid;
    gap: 0.2rem;
    margin-top: 1.2rem;
  }
  .row {
    display: grid;
    grid-template-columns: 10rem 1fr 9rem;
    gap: 0.8rem;
    align-items: center;
    text-decoration: none;
    color: #2b2722;
    padding: 0.2rem 0.4rem;
    border-radius: 6px;
  }
  .row:hover {
    background: #fffdf9;
  }
  .bar {
    height: 10px;
    background: #f0ebe2;
    border-radius: 5px;
    overflow: hidden;
  }
  .bar i {
    display: block;
    height: 100%;
    background: #d94f22;
    border-radius: 5px;
  }
  .vl {
    font-variant-numeric: tabular-nums;
    color: #52514e;
    font-size: 0.9rem;
  }
  @media (max-width: 640px) {
    .row {
      grid-template-columns: 6rem 1fr 7rem;
    }
  }
</style>
