<script>
  /**
   * A percentile index over time: thin per-station lines with the cross-station mean on top,
   * a 10% reference line (what a stationary climate would give), decade steps of the mean,
   * and a trend label. Percent of days/nights, 0–100.
   */
  import { linear, ticks } from '$lib/scales.js';
  import { GRID, AXIS, MUTED, INK, HIGHLIGHT } from '$lib/palette.js';

  let { series, perStation = {}, key = 'tn90p', label = '', color = '#d94f22', from = 1951, height = 250, reference = 10, trend = null, unit = '% of nights', trendNote = '' } = $props();

  const W = 620;
  const M = { top: 10, right: 14, bottom: 26, left: 34 };
  let idx = $derived(series.year.map((y, i) => i).filter((i) => series.year[i] >= from && series[key][i] != null));
  let years = $derived(idx.map((i) => series.year[i]));
  let vals = $derived(idx.map((i) => series[key][i]));
  let x = $derived(linear([years[0] - 0.5, years[years.length - 1] + 0.5], [M.left, W - M.right]));
  let vmax = $derived(Math.max(reference * 2, ...vals, ...Object.values(perStation).flatMap((s) => s[key] ?? []).filter((v) => v != null)));
  let yT = $derived(ticks(0, Math.min(100, vmax * 1.05), 5));
  let y = $derived(linear([0, yT[yT.length - 1]], [height - M.bottom, M.top]));
  const path = (ys, vs) => {
    if (!ys || !vs) return '';
    let s = '', pen = false;
    ys.forEach((yr, i) => {
      if (vs[i] == null || yr < from) { pen = false; return; }
      s += (pen ? 'L' : 'M') + x(yr).toFixed(1) + ' ' + y(vs[i]).toFixed(1);
      pen = true;
    });
    return s;
  };
  let decades = $derived.by(() => {
    const out = [];
    for (let d = Math.ceil(years[0] / 10) * 10; d <= years[years.length - 1]; d += 10) {
      const v = years.map((yr, i) => (yr >= d && yr <= d + 9 ? vals[i] : null)).filter((q) => q != null);
      if (v.length >= 5) out.push({ d, m: v.reduce((a, b) => a + b, 0) / v.length, partial: v.length < 10 });
    }
    return out;
  });
  let hover = $state(null);
  let k = $derived(hover == null ? -1 : years.indexOf(hover));
  let trendLabel = $derived.by(() => {
    if (!trend) return '';
    if (!trend.significant) return `no clear trend since ${trend.from}${trendNote}`;
    return `${trend.slope_per_decade > 0 ? '+' : ''}${trend.slope_per_decade.toFixed(1)} points per decade since ${trend.from}${trendNote}`;
  });
</script>

<div class="chart">
  <div class="head"><span class="lbl">{label}</span>{#if trendLabel}<span class="trend small">{trendLabel}</span>{/if}</div>
  <svg viewBox="0 0 {W} {height}" role="img" aria-label={label} onpointermove={(e) => { const r = e.currentTarget.getBoundingClientRect(); const yr = Math.round(x.invert(((e.clientX - r.left) / r.width) * W)); hover = years.includes(yr) ? yr : null; }} onpointerleave={() => (hover = null)}>
    {#each yT as t (t)}
      <line x1={M.left} x2={W - M.right} y1={y(t)} y2={y(t)} stroke={t === 0 ? AXIS : GRID} />
      <text x={M.left - 5} y={y(t) + 4} text-anchor="end" font-size="10" fill={MUTED}>{t}%</text>
    {/each}
    <line x1={M.left} x2={W - M.right} y1={y(reference)} y2={y(reference)} stroke={INK} stroke-dasharray="3 3" opacity="0.5" />
    {#each Object.entries(perStation) as [sid, s] (sid)}
      <path d={path(s.year, s[key])} fill="none" stroke={color} stroke-width="1" opacity="0.18" />
    {/each}
    <path d={path(years, vals)} fill="none" stroke={color} stroke-width="2.2" stroke-linejoin="round" />
    {#each decades as s (s.d)}
      <line x1={x(s.d)} x2={x(Math.min(s.d + 9, years[years.length - 1]))} y1={y(s.m)} y2={y(s.m)} stroke={HIGHLIGHT} stroke-width="2" stroke-dasharray={s.partial ? '3 3' : null} />
    {/each}
    {#if k >= 0}
      <line x1={x(hover)} x2={x(hover)} y1={M.top} y2={y(0)} stroke={INK} opacity="0.5" />
    {/if}
    {#each years.filter((yr) => yr % 10 === 0) as yr (yr)}
      <text x={x(yr)} y={height - 8} text-anchor="middle" font-size="10" fill={MUTED}>{yr}</text>
    {/each}
  </svg>
  <div class="tip small">
    {#if k >= 0}
      <b>{hover}</b>: {vals[k].toFixed(1)}{unit ? ' ' + unit : ''}{series.n ? ` (mean of ${series.n[series.year.indexOf(hover)]} stations)` : ''}
    {:else}
      {#if Object.keys(perStation).length}Thin lines: each station. Thick line: their average.{/if} Dashed: the {reference}% an unchanged climate would give. Dark steps: decade averages.
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
  .head {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 0.6rem;
    flex-wrap: wrap;
    margin-bottom: 0.2rem;
  }
  .head .trend {
    color: #52514e;
    white-space: nowrap;
  }
  .head .lbl {
    font-size: 0.9rem;
    font-weight: 650;
    color: #1f1b16;
  }
</style>
