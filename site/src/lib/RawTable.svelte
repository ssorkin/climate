<script>
  /**
   * The raw daily readings for one year, as NOAA published them (with withheld
   * values shown as withheld, not blank). CSV download + link to the source file.
   */
  import { units } from '$lib/units.svelte.js';
  import { fmtTenths } from '$lib/units.js';
  import { idxToDate, dateToIdx, isoOf, obsAt, fmtObs, isLeap } from '$lib/dates.js';
  import { downloadCsv } from '$lib/csv.js';

  let { daily, summary, year } = $props();
  let start = $derived(dateToIdx(daily.start, new Date(Date.UTC(year, 0, 1))));
  let nDays = $derived(isLeap(year) ? 366 : 365);
  let flagged = $derived.by(() => {
    const m = new Map();
    for (const [i, el, v, q] of daily.flagged) m.set(i + ':' + el, { v, q });
    return m;
  });
  let rows = $derived.by(() => {
    const out = [];
    for (let d = 0; d < nDays; d++) {
      const i = start + d;
      if (i < 0 || i >= daily.n) continue;
      out.push({
        i,
        date: isoOf(idxToDate(daily.start, i)),
        tmax: daily.tmax[i],
        tmin: daily.tmin[i],
        prcp: daily.prcp[i],
        obs: obsAt(daily.obs, i),
        fmax: flagged.get(i + ':TMAX'),
        fmin: flagged.get(i + ':TMIN')
      });
    }
    return out;
  });
  let showAll = $state(false);
  let shown = $derived(showAll ? rows : rows.slice(0, 31));
  function csv() {
    downloadCsv(
      `${summary.id}-${year}.csv`,
      ['date', 'tmax_tenths_c', 'tmin_tenths_c', 'prcp_tenths_mm', 'obs_time', 'tmax_qflag', 'tmin_qflag'],
      rows.map((r) => [r.date, r.fmax ? r.fmax.v : r.tmax, r.fmin ? r.fmin.v : r.tmin, r.prcp, r.obs, r.fmax?.q ?? '', r.fmin?.q ?? ''])
    );
  }
  const prcp = (t) => (t == null ? '—' : units.f ? (t / 254).toFixed(2) + ' in' : (t / 10).toFixed(1) + ' mm');
</script>

<div class="raw">
  <p class="small muted">
    Values as published in NOAA GHCN-Daily for station {summary.id}, stored in tenths of °C and shown
    here in whole °F as observed. Blank = no observation. "Withheld" = NOAA's quality check flagged the
    value; it is shown for transparency but excluded from every count.
    <a href={summary.source_url}>Source file</a> (sha256 {summary.manifest?.sha256?.slice(0, 12)}…, fetched {summary.manifest?.downloaded_at?.slice(0, 10)}).
  </p>
  <div class="actions">
    <button class="pill" onclick={csv}>Download {year} as CSV</button>
    <button class="pill" onclick={() => (showAll = !showAll)}>{showAll ? 'Show January only' : `Show all ${rows.length} days`}</button>
  </div>
  <div class="scroll">
    <table class="data">
      <thead>
        <tr><th>Date</th><th class="num">High</th><th class="num">Low</th><th class="num">Precip.</th><th>Observed at</th></tr>
      </thead>
      <tbody>
        {#each shown as r (r.i)}
          <tr>
            <td>{r.date}</td>
            <td class="num">{#if r.fmax}<span class="withheld" title="QFLAG {r.fmax.q}">withheld ({fmtTenths(r.fmax.v, units.f)})</span>{:else}{fmtTenths(r.tmax, units.f)}{/if}</td>
            <td class="num">{#if r.fmin}<span class="withheld" title="QFLAG {r.fmin.q}">withheld ({fmtTenths(r.fmin.v, units.f)})</span>{:else}{fmtTenths(r.tmin, units.f)}{/if}</td>
            <td class="num">{prcp(r.prcp)}</td>
            <td>{fmtObs(r.obs)}</td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
</div>

<style>
  .actions {
    display: flex;
    gap: 0.5rem;
    margin: 0.4rem 0 0.8rem;
    flex-wrap: wrap;
  }
  .scroll {
    overflow-x: auto;
  }
  .withheld {
    color: #898781;
    font-style: italic;
  }
</style>
