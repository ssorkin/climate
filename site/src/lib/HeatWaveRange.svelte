<script>
  /**
   * Every heat wave at one station: a thin line from its coolest night up to its hottest
   * afternoon, placed by date. Short bars mark the then/now averages of both ends. The
   * point of the chart is that the tops hold still while the bottoms climb.
   */
  import { linear } from '$lib/scales.js';
  import { HEAT, COOL, GRID, AXIS, MUTED, INK, INK2, SURFACE } from '$lib/palette.js';
  import { units } from '$lib/units.svelte.js';
  import { waveRows, tempF, deltaF, axisT, fmtDate } from '$lib/hw.js';

  let { station, height = 400 } = $props();

  const W = 920;
  const M = { top: 18, right: 150, bottom: 34, left: 44 };
  let H = $derived(height);
  let rows = $derived(waveRows(station).filter((w) => w.low != null));
  let x0 = $derived(station.first_year - 0.5);
  let x1 = $derived(station.last_year + 0.5);
  let x = $derived(linear([x0, x1], [M.left, W - M.right]));
  let vals = $derived(rows.flatMap((w) => [w.peak, w.low]));
  let y0 = $derived(Math.floor(Math.min(...vals) / 10) * 10 - 2);
  let y1 = $derived(Math.ceil(Math.max(...vals) / 10) * 10 + 2);
  let y = $derived(linear([y0, y1], [M.top + H - M.top - M.bottom, M.top]));
  let yTicks = $derived.by(() => { const t = []; for (let v = Math.ceil(y0 / 10) * 10; v <= y1; v += 10) t.push(v); return t; });
  let xTicks = $derived.by(() => { const t = []; for (let v = Math.ceil(x0 / 10) * 10; v <= x1; v += 10) t.push(v); return t; });
  let pos = $derived(rows.map((w) => x(w.year + (w.month - 0.5) / 12)));

  let base = $derived(station.windows?.baseline);
  let now = $derived(station.windows?.last30);
  let eras = $derived([base, now].filter(Boolean));

  let hover = $state(null);
  function nearest(e) {
    const r = e.currentTarget.getBoundingClientRect();
    const px = ((e.clientX - r.left) / r.width) * W;
    let best = null, bd = 9;
    pos.forEach((p, i) => { const d = Math.abs(p - px); if (d < bd) { bd = d; best = i; } });
    hover = best;
  }
  let tip = $derived.by(() => {
    if (hover == null) return '';
    const w = rows[hover];
    return `${fmtDate(w.start)} · ${w.days} days · hottest afternoon ${tempF(w.peak, units.f)} · coolest night ${tempF(w.low, units.f)}${w.relief != null ? ` · ${w.relief.toFixed(1)} h under ${tempF(station.rule?.relief_f ?? 70, units.f)} per night` : ''}${w.complete ? '' : ' · incomplete summer'}`;
  });
  const f1 = (v) => (v == null ? '—' : v);
</script>

<div class="chart">
  <svg viewBox="0 0 {W} {H}" role="img" aria-label="Every heat wave at {station.short}: hottest afternoon and coolest night of each" onpointermove={nearest} onpointerleave={() => (hover = null)}>
    {#each yTicks as v}
      <line x1={M.left} x2={W - M.right} y1={y(v)} y2={y(v)} stroke={GRID} />
      <text x={M.left - 8} y={y(v) + 4} text-anchor="end" font-size="12" fill={MUTED}>{Math.round(axisT(v, units.f))}°</text>
    {/each}
    {#each xTicks as v}
      <text x={x(v)} y={H - 10} text-anchor="middle" font-size="12" fill={MUTED}>{v}</text>
    {/each}
    {#each rows as w, i}
      {@const px = pos[i]}
      {@const on = hover === i}
      <line x1={px} x2={px} y1={y(w.peak)} y2={y(w.low)} stroke={on ? INK : AXIS} stroke-width={on ? 2 : 1.5} />
      <circle cx={px} cy={y(w.peak)} r={on ? 5 : 3.5} fill={w.complete ? HEAT : SURFACE} stroke={HEAT} stroke-width="1.5" />
      <circle cx={px} cy={y(w.low)} r={on ? 5 : 3.5} fill={w.complete ? COOL : SURFACE} stroke={COOL} stroke-width="1.5" />
    {/each}
    {#each eras as e}
      <line x1={x(e.years[0]) - 3} x2={x(e.years[1]) + 3} y1={y(e.peak_f)} y2={y(e.peak_f)} stroke={HEAT} stroke-width="3" stroke-linecap="round" />
      <line x1={x(e.years[0]) - 3} x2={x(e.years[1]) + 3} y1={y(e.low_f)} y2={y(e.low_f)} stroke={COOL} stroke-width="3" stroke-linecap="round" />
    {/each}
    {#if base && now}
      <text x={W - M.right + 10} y={y(now.peak_f) - 6} font-size="12.5" font-weight="600" fill={INK2}>hottest afternoon</text>
      <text x={W - M.right + 10} y={y(now.peak_f) + 9} font-size="12.5" font-weight="600" fill={INK2}>{tempF(base.peak_f, units.f)} → {tempF(now.peak_f, units.f)} ({deltaF(now.peak_f - base.peak_f, units.f)})</text>
      <text x={W - M.right + 10} y={y(now.low_f) - 6} font-size="12.5" font-weight="600" fill={INK2}>coolest night</text>
      <text x={W - M.right + 10} y={y(now.low_f) + 9} font-size="12.5" font-weight="700" fill={COOL}>{tempF(base.low_f, units.f)} → {tempF(now.low_f, units.f)} ({deltaF(now.low_f - base.low_f, units.f)})</text>
    {/if}
  </svg>
  <div class="tip">{tip || `${rows.length} heat waves over ${station.years.length} complete summers, ${station.first_year}–${station.last_year}. Threshold: ${tempF(station.threshold_f, units.f)}${units.f ? 'F' : 'C'}. Hover a wave.`}</div>
</div>

<style>
  .chart svg {
    width: 100%;
    height: auto;
    display: block;
  }
</style>
