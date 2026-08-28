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

  let { station, height = 400, compact = false } = $props();

  // compact: a small multiple (~1/3 page wide) — tighter margins, smaller marks, the
  // then/now summary as a caption under the chart instead of labels beside it
  let W = $derived(compact ? 440 : 920);
  let M = $derived(compact ? { top: 12, right: 14, bottom: 24, left: 34 } : { top: 18, right: 150, bottom: 34, left: 44 });
  let H = $derived(compact ? 250 : height);
  let R = $derived(compact ? 2.4 : 3.5);
  let FS = $derived(compact ? 11 : 12);
  let tickStep = $derived(compact ? 20 : 10);
  let rows = $derived(waveRows(station).filter((w) => w.low != null));
  let x0 = $derived(station.first_year - 0.5);
  let x1 = $derived(station.last_year + 0.5);
  let x = $derived(linear([x0, x1], [M.left, W - M.right]));
  let vals = $derived(rows.flatMap((w) => [w.peak, w.low]));
  let y0 = $derived(Math.floor(Math.min(...vals) / 10) * 10 - 2);
  let y1 = $derived(Math.ceil(Math.max(...vals) / 10) * 10 + 2);
  let y = $derived(linear([y0, y1], [M.top + H - M.top - M.bottom, M.top]));
  let yTicks = $derived.by(() => { const t = []; for (let v = Math.ceil(y0 / 10) * 10; v <= y1; v += 10) t.push(v); return t; });
  let xTicks = $derived.by(() => { const t = []; for (let v = Math.ceil(x0 / tickStep) * tickStep; v <= x1; v += tickStep) t.push(v); return t; });
  let pos = $derived(rows.map((w) => x(w.year + (w.month - 0.5) / 12)));

  let base = $derived(station.windows?.baseline);
  let now = $derived(station.windows?.last30);
  let eras = $derived([base, now].filter(Boolean));

  let hover = $state(null);
  function nearest(e) {
    const r = e.currentTarget.getBoundingClientRect();
    const px = ((e.clientX - r.left) / r.width) * W;
    let best = null, bd = compact ? 6 : 9;
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
      <text x={M.left - 6} y={y(v) + 4} text-anchor="end" font-size={FS} fill={MUTED}>{Math.round(axisT(v, units.f))}°</text>
    {/each}
    {#each xTicks as v}
      <text x={x(v)} y={H - 8} text-anchor="middle" font-size={FS} fill={MUTED}>{v}</text>
    {/each}
    {#each rows as w, i}
      {@const px = pos[i]}
      {@const on = hover === i}
      <line x1={px} x2={px} y1={y(w.peak)} y2={y(w.low)} stroke={on ? INK : AXIS} stroke-width={on ? 2 : compact ? 1 : 1.5} />
      <circle cx={px} cy={y(w.peak)} r={on ? R + 1.5 : R} fill={w.complete ? HEAT : SURFACE} stroke={HEAT} stroke-width={compact ? 1 : 1.5} />
      <circle cx={px} cy={y(w.low)} r={on ? R + 1.5 : R} fill={w.complete ? COOL : SURFACE} stroke={COOL} stroke-width={compact ? 1 : 1.5} />
    {/each}
    {#each eras as e}
      <line x1={x(e.years[0]) - 3} x2={x(e.years[1]) + 3} y1={y(e.peak_f)} y2={y(e.peak_f)} stroke={HEAT} stroke-width={compact ? 2.5 : 3} stroke-linecap="round" />
      <line x1={x(e.years[0]) - 3} x2={x(e.years[1]) + 3} y1={y(e.low_f)} y2={y(e.low_f)} stroke={COOL} stroke-width={compact ? 2.5 : 3} stroke-linecap="round" />
    {/each}
    {#if base && now && !compact}
      <text x={W - M.right + 10} y={y(now.peak_f) - 6} font-size="12.5" font-weight="600" fill={INK2}>hottest afternoon</text>
      <text x={W - M.right + 10} y={y(now.peak_f) + 9} font-size="12.5" font-weight="600" fill={INK2}>{tempF(base.peak_f, units.f)} → {tempF(now.peak_f, units.f)} ({deltaF(now.peak_f - base.peak_f, units.f)})</text>
      <text x={W - M.right + 10} y={y(now.low_f) - 6} font-size="12.5" font-weight="600" fill={INK2}>coolest night</text>
      <text x={W - M.right + 10} y={y(now.low_f) + 9} font-size="12.5" font-weight="700" fill={COOL}>{tempF(base.low_f, units.f)} → {tempF(now.low_f, units.f)} ({deltaF(now.low_f - base.low_f, units.f)})</text>
    {/if}
  </svg>
  {#if compact}
    <div class="tip small">
      {#if tip}{tip}{:else if base && now}<span class="day">{tempF(base.peak_f, units.f)} → {tempF(now.peak_f, units.f)} ({deltaF(now.peak_f - base.peak_f, units.f)})</span> · <span class="night">{tempF(base.low_f, units.f)} → {tempF(now.low_f, units.f)} ({deltaF(now.low_f - base.low_f, units.f)})</span> · {rows.length} waves{:else}{rows.length} heat waves, {station.first_year}–{station.last_year}{/if}
    </div>
  {:else}
    <div class="tip">{tip || `${rows.length} heat waves over ${station.years.length} complete summers, ${station.first_year}–${station.last_year}. Threshold: ${tempF(station.threshold_f, units.f)}${units.f ? 'F' : 'C'}. Hover a wave.`}</div>
  {/if}
</div>

<style>
  .tip.small {
    font-size: 0.8rem;
    min-height: 1.2rem;
  }
  .day {
    color: #c2410c;
    font-weight: 600;
  }
  .night {
    color: #1c5cab;
    font-weight: 600;
  }
  .chart svg {
    width: 100%;
    height: auto;
    display: block;
  }
</style>
