<script>
  /** How much nights warmed, then -> now: ordinary warm-season nights (gray) against the
   * nights inside heat waves (blue), one pair per station. Same axis, same years. */
  import { linear, ticks } from '$lib/scales.js';
  import { COOL, NEUTRAL, GRID, MUTED, INK, INK2 } from '$lib/palette.js';
  import { units } from '$lib/units.svelte.js';
  import { deltaF } from '$lib/hw.js';

  let { stations = [] } = $props();
  let rows = $derived(
    stations.map((s) => ({
      label: s.short,
      ordinary: s.windows.last30.ordinary_low_f - s.windows.baseline.ordinary_low_f,
      wave: s.windows.last30.mean_low_f - s.windows.baseline.mean_low_f
    }))
  );
  const W = 920;
  const M = { left: 210, right: 80 };
  let H = $derived(36 + rows.length * 54);
  let max = $derived(Math.max(1, Math.ceil(Math.max(...rows.flatMap((r) => [r.ordinary, r.wave])) + 0.5)));
  let x = $derived(linear([0, max], [M.left, W - M.right]));
  let xt = $derived(ticks(0, max, 6));
  let hover = $state(null);
</script>

<div class="chart">
  <svg viewBox="0 0 {W} {H}" role="img" aria-label="Night warming, ordinary nights versus heat-wave nights" onpointerleave={() => (hover = null)}>
    {#each xt as v}
      <line x1={x(v)} x2={x(v)} y1="20" y2={H - 16} stroke={GRID} />
      <text x={x(v)} y="13" text-anchor="middle" font-size="12" fill={MUTED}>{deltaF(v, units.f, 0)}</text>
    {/each}
    {#each rows as r, i}
      {@const yy = 30 + i * 54}
      <text x={M.left - 12} y={yy + 16} text-anchor="end" font-size="13" fill={INK}>{r.label}</text>
      <g onpointerenter={() => (hover = i)}>
        <rect x={x(0)} y={yy} width={Math.max(0, x(r.ordinary) - x(0))} height="11" rx="2" fill={NEUTRAL} />
        <text x={x(Math.max(0, r.ordinary)) + 6} y={yy + 9} font-size="12" font-weight="600" fill={INK2}>{deltaF(r.ordinary, units.f)} ordinary nights</text>
        <rect x={x(0)} y={yy + 14} width={Math.max(0, x(r.wave) - x(0))} height="11" rx="2" fill={COOL} />
        <text x={x(Math.max(0, r.wave)) + 6} y={yy + 23} font-size="12" font-weight="600" fill={INK2}>{deltaF(r.wave, units.f)} heat-wave nights</text>
      </g>
    {/each}
  </svg>
  <div class="tip">{hover == null ? 'Change in the average overnight low, baseline → last 30 complete summers, May–October.' : `${rows[hover].label}: ordinary nights ${deltaF(rows[hover].ordinary, units.f)}, nights inside a heat wave ${deltaF(rows[hover].wave, units.f)}`}</div>
</div>

<style>
  .chart svg {
    width: 100%;
    height: auto;
    display: block;
  }
</style>
