<script>
  /** "Hot" is local: one dot per station on a °F axis — its own heat-wave threshold. */
  import { linear, ticks } from '$lib/scales.js';
  import { HEAT, GRID, MUTED, INK, INK2, SURFACE } from '$lib/palette.js';
  import { units } from '$lib/units.svelte.js';
  import { tempF, axisT } from '$lib/hw.js';

  let { stations = [] } = $props();
  let rows = $derived([...stations].sort((a, b) => a.threshold_f - b.threshold_f));
  const W = 920;
  const M = { left: 210, right: 60 };
  let H = $derived(40 + rows.length * 26);
  let lo = $derived(Math.floor((Math.min(...rows.map((s) => s.threshold_f)) - 4) / 5) * 5);
  let hi = $derived(Math.ceil((Math.max(...rows.map((s) => s.threshold_f)) + 4) / 5) * 5);
  let x = $derived(linear([lo, hi], [M.left, W - M.right]));
  let xt = $derived(ticks(lo, hi, 6));
  let hover = $state(null);
</script>

<div class="chart">
  <svg viewBox="0 0 {W} {H}" role="img" aria-label="Heat-wave threshold at each station">
    {#each xt as v}
      <line x1={x(v)} x2={x(v)} y1="20" y2={H - 20} stroke={GRID} />
      <text x={x(v)} y="14" text-anchor="middle" font-size="12" fill={MUTED}>{Math.round(axisT(v, units.f))}°</text>
    {/each}
    {#each rows as s, i}
      {@const yy = 34 + i * 26}
      <text x={M.left - 12} y={yy + 4} text-anchor="end" font-size="13" fill={INK}>{s.short}</text>
      <line x1={x(lo)} x2={x(s.threshold_f)} y1={yy} y2={yy} stroke={GRID} />
      <circle cx={x(s.threshold_f)} cy={yy} r="6" fill={HEAT} stroke={SURFACE} stroke-width="2" onpointerenter={() => (hover = i)} onpointerleave={() => (hover = null)} />
      <text x={x(s.threshold_f) + 12} y={yy + 4} font-size="13" font-weight="600" fill={INK2}>{tempF(s.threshold_f, units.f)}</text>
    {/each}
  </svg>
  <div class="tip">{hover == null ? 'The hottest 5% of each station’s May–October afternoons, over its complete summers.' : `${rows[hover].short}: a heat wave is 3+ days at ${tempF(rows[hover].threshold_f, units.f)} or more · ${rows[hover].years.length} complete summers, ${rows[hover].first_year}–${rows[hover].last_year}`}</div>
</div>

<style>
  .chart svg {
    width: 100%;
    height: auto;
    display: block;
  }
</style>
