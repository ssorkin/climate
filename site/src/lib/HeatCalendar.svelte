<script>
  /**
   * Year (columns) × month (rows) grid of days-past-threshold. One-hue sequential
   * color; incomplete months as a light hatch; hover reads the cell; click selects
   * the year. Sequential = magnitude, so the legend is a scale bar, not names.
   */
  import { MONTHS } from '$lib/dates.js';
  import { HEAT_RAMP, COOL_RAMP, ramp, MUTED, INK, HIGHLIGHT } from '$lib/palette.js';

  let { years = [], months = [], values = [], lower = [], expected = [], daysValid = [], daysTotal = [], complete = [], cool = false, selected = null, onselect = null, unitLabel = 'days' } = $props();

  const W = 860;
  const LEFT = 34;
  const TOP = 18;
  let y0 = $derived(Math.min(...years));
  let y1 = $derived(Math.max(...years));
  let nY = $derived(y1 - y0 + 1);
  let cw = $derived((W - LEFT - 8) / nY);
  let ch = $derived(Math.max(9, Math.min(18, cw * 2.2)));
  let H = $derived(TOP + ch * 12 + 26);
  let vmax = $derived(Math.max(1, ...values.filter((v) => v != null)));
  let colors = $derived(cool ? COOL_RAMP : HEAT_RAMP);

  let grid = $derived.by(() => {
    const g = new Map();
    for (let k = 0; k < years.length; k++) g.set(years[k] * 100 + months[k], { v: values[k], lb: lower[k], ex: expected[k], ok: complete[k], nv: daysValid[k], nt: daysTotal[k] });
    return g;
  });
  let hover = $state(null);
  function at(e) {
    const r = e.currentTarget.getBoundingClientRect();
    const px = ((e.clientX - r.left) / r.width) * W;
    const py = ((e.clientY - r.top) / r.height) * H;
    const yr = y0 + Math.floor((px - LEFT) / cw);
    const mo = Math.floor((py - TOP) / ch) + 1;
    hover = yr >= y0 && yr <= y1 && mo >= 1 && mo <= 12 ? { yr, mo } : null;
  }
  let tip = $derived.by(() => {
    if (!hover) return '';
    const c = grid.get(hover.yr * 100 + hover.mo);
    if (!c) return `${MONTHS[hover.mo - 1]} ${hover.yr}: no data`;
    const obs = c.nv != null && c.nt != null ? ` (${c.nv} of ${c.nt} days observed)` : '';
    if (c.v == null) return c.lb != null && c.nv > 0 ? `${MONTHS[hover.mo - 1]} ${hover.yr}: at least ${c.lb} ${unitLabel} — incomplete${obs}${c.ex != null ? `, missing days expected to add ~${c.ex.toFixed(1)}` : ''}` : `${MONTHS[hover.mo - 1]} ${hover.yr}: no data`;
    return `${MONTHS[hover.mo - 1]} ${hover.yr}: ${c.v} ${unitLabel}${obs}${!c.ok ? ', missing days on dates that rarely count here' : ''}`;
  });
</script>

<div class="chart">
  <svg viewBox="0 0 {W} {H}" role="img" aria-label="Days past threshold by month and year" onpointermove={at} onpointerleave={() => (hover = null)} onclick={() => hover && onselect?.(hover.yr)}>
    <defs>
      <pattern id="hatch-gray" width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
        <rect width="1" height="4" fill="#cfc8bb" />
      </pattern>
    </defs>
    {#each MONTHS as m, i (m)}
      <text x={LEFT - 6} y={TOP + i * ch + ch / 2 + 3.5} text-anchor="end" font-size="10" fill={MUTED}>{m}</text>
    {/each}
    {#each years as yr, k (yr * 100 + months[k])}
      {@const mo = months[k]}
      {@const v = values[k]}
      {@const lb = lower[k]}
      {#if v != null}
        <rect x={LEFT + (yr - y0) * cw} y={TOP + (mo - 1) * ch} width={Math.max(0.5, cw - 0.6)} height={ch - 1} fill={v === 0 ? '#f3efe7' : ramp(colors, v / vmax)} />
      {:else}
        <rect x={LEFT + (yr - y0) * cw} y={TOP + (mo - 1) * ch} width={Math.max(0.5, cw - 0.6)} height={ch - 1} fill={lb > 0 ? ramp(colors, lb / vmax) : '#f3efe7'} opacity={lb > 0 ? 0.55 : 1} />
        <rect x={LEFT + (yr - y0) * cw} y={TOP + (mo - 1) * ch} width={Math.max(0.5, cw - 0.6)} height={ch - 1} fill="url(#hatch-gray)" />
      {/if}
    {/each}
    {#each Array.from({ length: Math.floor(y1 / 10) - Math.ceil(y0 / 10) + 1 }, (_, i) => Math.ceil(y0 / 10) * 10 + i * 10) as d (d)}
      {#if d % 20 === 0}
        <text x={LEFT + (d - y0) * cw + cw / 2} y={H - 8} text-anchor="middle" font-size="10.5" fill={MUTED}>{d}</text>
      {/if}
    {/each}
    {#if selected != null && selected >= y0 && selected <= y1}
      <rect x={LEFT + (selected - y0) * cw - 1} y={TOP - 2} width={cw + 1.5} height={ch * 12 + 3} fill="none" stroke={HIGHLIGHT} stroke-width="1.5" />
    {/if}
    {#if hover}
      <rect x={LEFT + (hover.yr - y0) * cw - 0.5} y={TOP + (hover.mo - 1) * ch - 0.5} width={cw + 0.5} height={ch} fill="none" stroke={INK} stroke-width="1.5" />
    {/if}
  </svg>
  <div class="legend">
    <span class="tip">{tip}</span>
    <span class="scale"><span>0</span>{#each colors as c, i (i)}<i style:background={c}></i>{/each}<span>{vmax} {unitLabel}</span><i class="hatch"></i><span>incomplete (color = at least)</span></span>
  </div>
</div>

<style>
  .chart svg {
    width: 100%;
    height: auto;
    display: block;
    cursor: crosshair;
  }
  .legend {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
    flex-wrap: wrap;
    font-size: 0.85rem;
    color: #52514e;
  }
  .scale {
    display: inline-flex;
    align-items: center;
    gap: 2px;
    white-space: nowrap;
  }
  .scale i {
    display: inline-block;
    width: 14px;
    height: 12px;
  }
  .scale span {
    margin: 0 0.3rem;
  }
  .scale i.hatch {
    margin-left: 0.6rem;
    background: repeating-linear-gradient(45deg, #cfc8bb 0 1px, transparent 1px 4px);
  }
</style>
