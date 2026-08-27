<script>
  /**
   * Greater Los Angeles stations: one row per station with its record span, day/night scores
   * against its baseline, warm nights and hot days then vs. now, and status. Sortable.
   */
  import { units } from '$lib/units.svelte.js';
  import { fmtThresholdF } from '$lib/units.js';

  let { data } = $props();
  let ix = $derived(data.index);
  let region = $derived(ix.regions[0]);
  let stations = $derived(ix.stations.filter((s) => s.region === region.id));
  let sortKey = $state('night');
  let sortDir = $state(-1);
  const val = (s, k) => {
    const h = s.headline ?? {};
    switch (k) {
      case 'name': return s.short.toLowerCase();
      case 'since': return s.first_year;
      case 'night': return h.score?.tmin ?? -1;
      case 'day': return h.score?.tmax ?? -1;
      case 'warm': return h.warm70_last10 ?? -1;
      case 'hot': return h.hot95_last10 ?? -1;
      default: return 0;
    }
  };
  let rows = $derived([...stations].sort((a, b) => { const x = val(a, sortKey), y = val(b, sortKey); return (x < y ? -1 : x > y ? 1 : 0) * sortDir || a.short.localeCompare(b.short); }));
  const sortBy = (k) => { if (sortKey === k) sortDir = -sortDir; else { sortKey = k; sortDir = k === 'name' || k === 'since' ? 1 : -1; } };
  const n0 = (v) => (v == null ? '—' : v.toFixed(v < 10 ? 1 : 0));
  const arrow = (a, b) => (a == null || b == null ? '' : b > a ? '↑' : b < a ? '↓' : '→');
  let nBase = $derived(stations.filter((s) => s.headline?.has_baseline).length);
</script>

<svelte:head>
  <title>Greater Los Angeles stations · climate.sorkinlabs</title>
</svelte:head>

<h1 class="title">Greater Los Angeles stations</h1>
<p class="lede">
  {stations.length} weather stations with hourly NOAA records in the basin, valleys and high desert — {stations.filter((s) => s.active).length} still reporting, the oldest since {Math.min(...stations.map((s) => s.first_year))}.
  Each station is judged only against its own history: the <b>score</b> is where a typical night or day of its last ten complete years falls among its baseline's readings for the same date (50 = no change; baseline 1951–1980 for {nBase} stations, † = the station's own earliest 20 complete years). Click a column to sort, a station for its full record.
</p>

<div class="tablewrap">
  <table>
    <thead>
      <tr>
        <th><button onclick={() => sortBy('name')}>Station</button></th>
        <th class="num"><button onclick={() => sortBy('since')}>Records</button></th>
        <th class="num"><button onclick={() => sortBy('night')}>Night score</button></th>
        <th class="num"><button onclick={() => sortBy('day')}>Day score</button></th>
        <th class="num"><button onclick={() => sortBy('warm')}>Nights ≥ {fmtThresholdF(70, units.f)} / yr</button></th>
        <th class="num"><button onclick={() => sortBy('hot')}>Days ≥ {fmtThresholdF(95, units.f)} / yr</button></th>
        <th>Status</th>
      </tr>
    </thead>
    <tbody>
      {#each rows as s (s.id)}
        {@const h = s.headline ?? {}}
        {@const fb = h.baseline_fallback ? '†' : ''}
        <tr>
          <td><a href="/station/{s.id}">{s.short}</a>{#if h.suspect_step}<span class="warn" title="suspected sensor or site change under this id">⚠</span>{/if}</td>
          <td class="num muted">{s.first_year}–{s.last_year}</td>
          <td class="num">{#if h.score?.tmin != null}<span class="score night">{Math.round(h.score.tmin)}{fb}</span>{:else}<span class="muted">—</span>{/if}</td>
          <td class="num">{#if h.score?.tmax != null}<span class="score day">{Math.round(h.score.tmax)}{fb}</span>{:else}<span class="muted">—</span>{/if}</td>
          <td class="num">{n0(h.warm70_baseline)} <span class="muted">{arrow(h.warm70_baseline, h.warm70_last10)}</span> <b>{n0(h.warm70_last10)}</b></td>
          <td class="num">{n0(h.hot95_baseline)} <span class="muted">{arrow(h.hot95_baseline, h.hot95_last10)}</span> <b>{n0(h.hot95_last10)}</b></td>
          <td class="muted small">{s.active ? `reporting · ${s.last_date}` : `closed ${s.last_year}`}</td>
        </tr>
      {/each}
    </tbody>
  </table>
</div>
<p class="small muted">
  Counts are per year: the 1951–1980 average, then the last ten complete years; "—" where the station has no complete years in a window. A day's high and low are the extremes of its hourly readings, which read about 0.5 °C below a thermometer's peak — the site's ≥ 95°F is "a 95°F reading" (<a href="/methods">Methods</a>).
  The famous downtown Los Angeles record is not here: its hourly record begins at USC in 1999 and is listed as Downtown LA (USC); the older Civic Center series moved between eight sites (<a href="/methods#downtown">why</a>).
</p>

<style>
  .title {
    margin-bottom: 0.3rem;
  }
  .tablewrap {
    overflow-x: auto;
    margin-top: 1rem;
  }
  table {
    border-collapse: collapse;
    width: 100%;
    font-size: 0.95rem;
  }
  th,
  td {
    padding: 0.4rem 0.6rem;
    border-bottom: 1px solid #e8e1d5;
    text-align: left;
    white-space: nowrap;
  }
  th button {
    border: 0;
    background: transparent;
    padding: 0;
    font: inherit;
    font-weight: 650;
    color: #2b2722;
    cursor: pointer;
  }
  .num {
    text-align: right;
  }
  .score {
    display: inline-block;
    min-width: 2.4em;
    padding: 0.05rem 0.45rem;
    border-radius: 999px;
    font-weight: 700;
    color: #fffdf9;
    text-align: center;
  }
  .score.day {
    background: #d94f22;
  }
  .score.night {
    background: #2a78d6;
  }
  .warn {
    margin-left: 0.3rem;
    color: #9a2f0c;
  }
</style>
