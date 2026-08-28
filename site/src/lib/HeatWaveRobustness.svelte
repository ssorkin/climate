<script>
  /** "Does the definition matter?" — the then->now change under alternative definitions,
   * averaged over the comparable stations, with the calendar-date-adjusted night change. */
  import { units } from '$lib/units.svelte.js';
  import { deltaF } from '$lib/hw.js';
  let { rows = [], pooled = null } = $props();
  const dF = (v) => deltaF(v, units.f);
  const sg = (v, d) => { if (v == null) return '—'; const a = Math.abs(v).toFixed(d); return (Number(a) === 0 ? '' : v >= 0 ? '+' : '−') + a; };
</script>

<div class="wrap">
  <table>
    <thead>
      <tr><th>Definition</th><th>Events / station / summer</th><th>Hottest afternoon</th><th>Coolest heat-wave night</th><th>Days per event</th><th>Stations</th></tr>
    </thead>
    <tbody>
      {#each rows as r}
        <tr class:main={r.definition.includes('this page')}>
          <td>{r.definition}</td>
          <td>{r.waves_per_year_then == null ? '—' : `${r.waves_per_year_then.toFixed(1)} → ${r.waves_per_year_now.toFixed(1)}`}</td>
          <td>{dF(r.peak_f_change)}</td>
          <td class="night">{dF(r.low_f_change)}</td>
          <td>{sg(r.days_change, 1)}</td>
          <td>{r.n_stations}</td>
        </tr>
      {/each}
      {#if pooled?.low_anom_f}
        <tr>
          <td>Page definition — nights adjusted for their calendar date</td>
          <td>—</td>
          <td>{dF(pooled.peak_anom_f?.est)}</td>
          <td class="night">{dF(pooled.low_anom_f.est)} <span class="muted">({dF(pooled.low_anom_f.lo)} to {dF(pooled.low_anom_f.hi)})</span></td>
          <td>—</td>
          <td>{pooled.low_anom_f.n_stations}</td>
        </tr>
      {/if}
    </tbody>
  </table>
</div>

<style>
  .wrap {
    overflow-x: auto;
  }
  table {
    border-collapse: collapse;
    font-size: 0.88rem;
    width: 100%;
    font-variant-numeric: tabular-nums;
  }
  th,
  td {
    text-align: right;
    padding: 0.35rem 0.6rem;
    border-bottom: 1px solid #e8e1d5;
    white-space: nowrap;
  }
  th:first-child,
  td:first-child {
    text-align: left;
    white-space: normal;
  }
  th {
    font-size: 0.75rem;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: #898781;
    font-weight: 600;
  }
  tr.main td {
    font-weight: 700;
  }
  .night {
    color: #1c5cab;
    font-weight: 600;
  }
  .muted {
    color: #898781;
    font-weight: 400;
  }
</style>
