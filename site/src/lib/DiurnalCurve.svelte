<script>
  /** Average temperature by local hour (Jun–Sep), one line per decade; earliest and latest labeled. */
  import { units } from '$lib/units.svelte.js';
  import { cToF } from '$lib/units.js';
  import { linear, ticks } from '$lib/scales.js';
  import { GRID, AXIS, MUTED, INK, HEAT, COOL } from '$lib/palette.js';
  let { diurnal, threshold = 70 } = $props();
  const W = 620, H = 260, M = { top: 18, right: 60, bottom: 28, left: 34 };
  let decades = $derived(Object.keys(diurnal).map(Number).sort());
  const conv = (c) => (c == null ? null : units.f ? cToF(c) : c);
  let all = $derived(decades.flatMap((d) => diurnal[d].map(conv)).filter((v) => v != null));
  let lo = $derived(Math.floor(Math.min(...all) / 5) * 5);
  let hi = $derived(Math.ceil(Math.max(...all) / 5) * 5);
  let x = $derived(linear([0, 23], [M.left, W - M.right]));
  let y = $derived(linear([lo, hi], [H - M.bottom, M.top]));
  let yTicks = $derived(ticks(lo, hi, 5));
  const path = (arr) => arr.map((c, h) => (c == null ? null : `${x(h).toFixed(1)} ${y(conv(c)).toFixed(1)}`)).filter(Boolean).join('L');
  const shade = (i, n) => {
    const t = n <= 1 ? 1 : i / (n - 1);
    const a = [0x9e, 0xc5, 0xf4], b = [0x99, 0x2f, 0x0c];
    return `rgb(${a.map((v, k) => Math.round(v + (b[k] - v) * t)).join(',')})`;
  };
  let thrY = $derived(y(units.f ? threshold : (threshold - 32) / 1.8));
  let hover = $state(null);
</script>

<div class="chart">
  <svg viewBox="0 0 {W} {H}" role="img" aria-label="Average temperature by hour of day" onpointermove={(e) => { const r = e.currentTarget.getBoundingClientRect(); hover = Math.max(0, Math.min(23, Math.round(x.invert(((e.clientX - r.left) / r.width) * W)))); }} onpointerleave={() => (hover = null)}>
    {#each yTicks as t (t)}
      <line x1={M.left} x2={W - M.right} y1={y(t)} y2={y(t)} stroke={GRID} />
      <text x={M.left - 5} y={y(t) + 4} text-anchor="end" font-size="10" fill={MUTED}>{t}°</text>
    {/each}
    {#each [0, 6, 12, 18, 23] as h (h)}
      <text x={x(h)} y={H - 10} text-anchor="middle" font-size="10" fill={MUTED}>{h === 0 ? 'midnight' : h === 12 ? 'noon' : h === 23 ? '11pm' : h < 12 ? h + 'am' : h - 12 + 'pm'}</text>
    {/each}
    {#if thrY > M.top && thrY < H - M.bottom}
      <line x1={M.left} x2={W - M.right} y1={thrY} y2={thrY} stroke={INK} stroke-dasharray="3 3" opacity="0.5" />
      <text x={W - M.right} y={thrY - 4} text-anchor="end" font-size="10" fill={INK}>{threshold}°F</text>
    {/if}
    {#each decades as d, i (d)}
      <path d={'M' + path(diurnal[d])} fill="none" stroke={shade(i, decades.length)} stroke-width={i === 0 || i === decades.length - 1 ? 2.5 : 1.2} opacity={i === 0 || i === decades.length - 1 ? 1 : 0.55} />
      {#if i === 0 || i === decades.length - 1}
        <text x={W - M.right + 4} y={y(conv(diurnal[d][23])) + 4} font-size="10.5" fill={INK}>{d}s</text>
      {/if}
    {/each}
    {#if hover != null}
      <line x1={x(hover)} x2={x(hover)} y1={M.top} y2={H - M.bottom} stroke={INK} opacity="0.4" />
    {/if}
  </svg>
  <div class="tip small">
    {#if hover != null}
      <b>{hover === 0 ? 'midnight' : hover < 12 ? hover + ' am' : hover === 12 ? 'noon' : hover - 12 + ' pm'}</b>: {#each [decades[0], decades[decades.length - 1]] as d (d)}{d}s {conv(diurnal[d][hover])?.toFixed(1)}° {/each}
    {:else}
      June–September average temperature at each hour of the day, one line per decade (light = earliest, dark = latest).
    {/if}
  </div>
</div>

<style>
  .chart svg {
    width: 100%;
    height: auto;
    display: block;
    cursor: crosshair;
  }
</style>
