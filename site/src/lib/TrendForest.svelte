<script>
  /**
   * One row per station: its own trend (Theil–Sen slope per decade over its complete years)
   * as a dot with a 90% whisker on a shared axis. Significant trends are filled; the rest are
   * hollow. Sorted by slope. Nothing here averages across stations.
   */
  import { linear, ticks } from '$lib/scales.js';
  import { GRID, AXIS, MUTED, INK, HEAT, COOL, NEUTRAL, SURFACE } from '$lib/palette.js';

  let { stations = [], key = 'trend_warm70', label = '', unitLabel = 'nights', color = HEAT, rowH = 15, compact = false } = $props();

  let rows = $derived(
    stations
      .map((s) => ({ s, t: s.headline?.[key] }))
      .filter((r) => r.t && r.t.slope_per_decade != null)
      .sort((a, b) => b.t.slope_per_decade - a.t.slope_per_decade)
  );
  let noTrend = $derived(stations.filter((s) => !s.headline?.[key]));
  const W = 620;
  const L = 178, R = 74;
  let H = $derived(rows.length * rowH + 30);
  let ext = $derived.by(() => {
    const v = rows.flatMap((r) => [r.t.ci[0], r.t.ci[1], r.t.slope_per_decade]);
    const lo = Math.min(0, ...v), hi = Math.max(0, ...v);
    const pad = (hi - lo) * 0.06;
    return [lo - pad, hi + pad];
  });
  let x = $derived(linear(ext, [L, W - R]));
  let xt = $derived(ticks(ext[0], ext[1], 5));
  let nSig = $derived(rows.filter((r) => r.t.significant && r.t.slope_per_decade > 0).length);
  let nSigDown = $derived(rows.filter((r) => r.t.significant && r.t.slope_per_decade < 0).length);
  let hover = $state(null);
  const f1 = (v) => (v > 0 ? '+' : '') + v.toFixed(1);
</script>

<div class="forest">
  <div class="head">
    <span class="lbl">{label}</span>
    <span class="sum muted small">rising at {nSig} of {rows.length}{nSigDown ? `, falling at ${nSigDown}` : ''}</span>
  </div>
  <svg viewBox="0 0 {W} {H}" role="img" aria-label={label} onpointerleave={() => (hover = null)}>
    {#each xt as t (t)}
      <line x1={x(t)} x2={x(t)} y1={8} y2={H - 22} stroke={t === 0 ? AXIS : GRID} stroke-width={t === 0 ? 1.5 : 1} />
      <text x={x(t)} y={H - 8} text-anchor="middle" font-size="10" fill={MUTED}>{f1(t)}</text>
    {/each}
    <text x={W - R} y={H - 8} text-anchor="start" font-size="10" fill={MUTED}>&nbsp;{unitLabel}/decade</text>
    {#each rows as r, i (r.s.id)}
      {@const y = 14 + i * rowH}
      {@const sig = r.t.significant}
      <rect x="0" y={y - rowH / 2} width={W} height={rowH} fill="transparent" onpointerenter={() => (hover = r.s.id)} />
      <text x={L - 8} y={y + 3.5} text-anchor="end" font-size={compact ? 10 : 10.5} fill={hover === r.s.id ? INK : sig ? INK : MUTED}>{r.s.short}</text>
      <line x1={x(r.t.ci[0])} x2={x(r.t.ci[1])} y1={y} y2={y} stroke={sig ? color : NEUTRAL} stroke-width="1.5" />
      <circle cx={x(r.t.slope_per_decade)} cy={y} r={rowH * 0.3} fill={sig ? color : SURFACE} stroke={sig ? color : MUTED} stroke-width="1.5" />
      <text x={W - R + 6} y={y + 3.5} font-size="10" fill={sig ? INK : MUTED}>{f1(r.t.slope_per_decade)} <tspan fill={MUTED}>{r.t.from}–{r.t.to}</tspan></text>
    {/each}
  </svg>
  <div class="tip small">
    {#if hover}
      {@const r = rows.find((q) => q.s.id === hover)}
      <b>{r.s.short}</b>: {f1(r.t.slope_per_decade)} {unitLabel} per decade over {r.t.from}–{r.t.to} ({r.t.n} complete years; 90% range {f1(r.t.ci[0])} to {f1(r.t.ci[1])}){r.t.significant ? '' : ' — not distinguishable from zero'}
    {:else if !compact}
      Each row is one station's own trend over its own complete years; filled dots are trends whose 90% range excludes zero.{#if noTrend.length} {noTrend.length} station{noTrend.length > 1 ? 's' : ''} with too few counting years ({noTrend.map((s) => s.short).join(', ')}) not shown.{/if}
    {/if}
  </div>
</div>

<style>
  .forest svg {
    width: 100%;
    height: auto;
    display: block;
  }
  .head {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 0.6rem;
    flex-wrap: wrap;
    margin-bottom: 0.1rem;
  }
  .lbl {
    font-size: 0.9rem;
    font-weight: 650;
    color: #1f1b16;
  }
  .tip {
    min-height: 1.2rem;
  }
</style>
