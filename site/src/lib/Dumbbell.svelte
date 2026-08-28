<script>
  /**
   * Then -> now per station: a hollow dot for the baseline window, a filled one for the
   * last 30 years, joined by a line, with the change printed at the right (colored when it
   * clears `big`, muted otherwise). One measure per chart; axis in the chosen unit.
   */
  import { linear, ticks } from '$lib/scales.js';
  import { GRID, MUTED, INK, SURFACE } from '$lib/palette.js';

  let {
    rows = [], // [{label, a, b, tipA, tipB}]
    color,
    format = (v) => String(v),
    delta = (d) => (d >= 0 ? '+' : '−') + Math.abs(d).toFixed(1),
    axis = (v) => v, // axis value -> display value (unit conversion)
    domain = null,
    big = 0,
    tickCount = 5,
    empty = ''
  } = $props();
  const W = 920;
  const M = { left: 210, right: 90 };
  let H = $derived(36 + rows.length * 30);
  let dom = $derived(domain ?? (() => { const v = rows.flatMap((r) => [r.a, r.b]); const lo = Math.min(...v), hi = Math.max(...v); const pad = (hi - lo) * 0.15 || 1; return [lo - pad, hi + pad]; })());
  let x = $derived(linear(dom, [M.left, W - M.right]));
  let xt = $derived(ticks(dom[0], dom[1], tickCount));
  let hover = $state(null);
</script>

<div class="chart">
  <svg viewBox="0 0 {W} {H}" role="img" onpointerleave={() => (hover = null)}>
    {#each xt as v}
      <line x1={x(v)} x2={x(v)} y1="20" y2={H - 16} stroke={GRID} />
      <text x={x(v)} y="13" text-anchor="middle" font-size="12" fill={MUTED}>{format(axis(v))}</text>
    {/each}
    {#each rows as r, i}
      {@const yy = 36 + i * 30}
      {@const d = r.b - r.a}
      <text x={M.left - 12} y={yy + 4} text-anchor="end" font-size="13" fill={INK}>{r.label}</text>
      <g onpointerenter={() => (hover = i)}>
        <line x1={x(r.a)} x2={x(r.b)} y1={yy} y2={yy} stroke={color} stroke-width="3" stroke-linecap="round" />
        <circle cx={x(r.a)} cy={yy} r="6" fill={SURFACE} stroke={color} stroke-width="2" />
        <circle cx={x(r.b)} cy={yy} r="6" fill={color} stroke={SURFACE} stroke-width="2" />
        <text x={W - M.right + 10} y={yy + 4} font-size="13" font-weight="600" fill={Math.abs(d) >= big ? color : MUTED}>{delta(d)}</text>
        <rect x={Math.min(x(r.a), x(r.b)) - 8} y={yy - 10} width={Math.abs(x(r.b) - x(r.a)) + 16} height="20" fill="transparent" />
      </g>
    {/each}
  </svg>
  <div class="tip">{hover == null ? empty : `${rows[hover].label}: ${rows[hover].tipA} → ${rows[hover].tipB}`}</div>
</div>

<style>
  .chart svg {
    width: 100%;
    height: auto;
    display: block;
  }
</style>
