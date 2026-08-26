<script>
  /** Then vs. now: baseline, last 30 and last 10 complete years, every standard metric. */
  import { units } from '$lib/units.svelte.js';
  import { fmtC, fmtThresholdF } from '$lib/units.js';
  let { summary } = $props();
  let w = $derived(summary.windows);
  const keys = ['baseline', 'last30', 'last10'];
  let rows = $derived.by(() => {
    const t = summary.thresholds_f;
    const r = [
      { label: 'Average daily high', get: (x) => fmtC(x.tmax_mean_c, units.f) },
      { label: 'Average daily low', get: (x) => fmtC(x.tmin_mean_c, units.f) }
    ];
    for (const thr of t.hot_days) r.push({ label: `Days at or above ${fmtThresholdF(thr, units.f)}`, get: (x) => n(x[`hot_${thr}`]) });
    for (const thr of t.warm_nights) r.push({ label: `Nights at or above ${fmtThresholdF(thr, units.f)}`, get: (x) => n(x[`warm_${thr}`]) });
    for (const thr of t.cold_days) r.push({ label: `Days with a high at or below ${fmtThresholdF(thr, units.f)}`, get: (x) => n(x[`coldday_${thr}`]) });
    for (const thr of t.cold_nights) r.push({ label: `Nights at or below ${fmtThresholdF(thr, units.f)} (Jul–Jun season)`, get: (x) => n(x.season?.[`coldnight_${thr}`]) });
    return r;
  });
  const n = (v) => (v == null ? '—' : v.toFixed(1));
</script>

{#if w?.baseline}
  <div class="scroll">
    <table class="data">
      <thead>
        <tr>
          <th>Per year, averaged over</th>
          {#each keys as k (k)}
            <th class="num">{w[k].years[0]}–{w[k].years[1]}</th>
          {/each}
        </tr>
      </thead>
      <tbody>
        {#each rows as r (r.label)}
          <tr>
            <td>{r.label}</td>
            {#each keys as k (k)}<td class="num">{r.get(w[k])}</td>{/each}
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
  <p class="small muted">Only complete years count toward these averages (n = {w.baseline.n_tmax_mean_c} / {w.last30.n_tmax_mean_c} / {w.last10.n_tmax_mean_c} years with complete highs).</p>
{/if}

<style>
  .scroll {
    overflow-x: auto;
  }
</style>
