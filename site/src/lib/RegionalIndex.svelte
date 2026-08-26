<script>
  /**
   * Regional index chart: the modeled average station count per year (median of the
   * model draws) as thin bars, with the 5–95% band behind them, plus decade steps and
   * baseline / last-decade labels. `n_observed` shows how many stations actually reported.
   */
  import { linear, ticks } from '$lib/scales.js';
  import { GRID, AXIS, MUTED, INK, HIGHLIGHT } from '$lib/palette.js';

  let { series: full, from = null, label = '', unitLabel = 'days', color = '#d94f22', baseline = [1951, 1980], height = 230, compact = false } = $props();
  // Slice the series at `from` (the front page starts at 1930: before that the network is too thin).
  let series = $derived.by(() => {
    if (from == null) return full;
    const keep = full.year.map((y) => y >= from);
    const pick = (arr) => (Array.isArray(arr) ? arr.filter((_, i) => keep[i]) : arr);
    return { ...full, year: pick(full.year), mean: pick(full.mean), p05: pick(full.p05), p25: pick(full.p25), p75: pick(full.p75), p95: pick(full.p95), n_observed: pick(full.n_observed) };
  });
  let trend = $derived(full.trend);
  let trendLabel = $derived.by(() => {
    if (!trend) return '';
    if (!trend.significant) return `no clear trend since ${trend.from}`;
    const s = trend.slope_per_decade;
    return `${s > 0 ? '+' : ''}${s.toFixed(1)} ${unitLabel} per decade since ${trend.from} (90% range ${trend.ci[0] > 0 ? '+' : ''}${trend.ci[0].toFixed(1)} to ${trend.ci[1] > 0 ? '+' : ''}${trend.ci[1].toFixed(1)})`;
  });

  const W = 620;
  const M = { top: 22, right: 12, bottom: 26, left: 32 };
  let years = $derived(series.year);
  let x = $derived(linear([years[0] - 0.5, years[years.length - 1] + 0.5], [M.left, W - M.right]));
  let vmax = $derived(Math.max(1, ...series.p95));
  let yTicks = $derived(ticks(0, vmax * 1.05, 4));
  let y = $derived(linear([0, yTicks[yTicks.length - 1]], [height - M.bottom, M.top]));
  let bw = $derived(Math.max(1, Math.min(10, ((W - M.left - M.right) / years.length) * 0.75)));

  let bandPath = $derived.by(() => {
    const up = years.map((yr, i) => `${x(yr).toFixed(1)} ${y(series.p95[i]).toFixed(1)}`);
    const dn = years.map((yr, i) => `${x(yr).toFixed(1)} ${y(series.p05[i]).toFixed(1)}`).reverse();
    return 'M' + up.join('L') + 'L' + dn.join('L') + 'Z';
  });
  let band50 = $derived.by(() => {
    const up = years.map((yr, i) => `${x(yr).toFixed(1)} ${y(series.p75[i]).toFixed(1)}`);
    const dn = years.map((yr, i) => `${x(yr).toFixed(1)} ${y(series.p25[i]).toFixed(1)}`).reverse();
    return 'M' + up.join('L') + 'L' + dn.join('L') + 'Z';
  });
  const meanOver = (arr, a, b) => {
    const v = years.map((yr, i) => (yr >= a && yr <= b ? arr[i] : null)).filter((q) => q != null);
    return v.length ? v.reduce((s, q) => s + q, 0) / v.length : null;
  };
  let last = $derived(years[years.length - 1]);
  let baseMean = $derived(meanOver(series.mean, baseline[0], baseline[1]));
  let lastMean = $derived(meanOver(series.mean, last - 9, last));
  let decades = $derived.by(() => {
    const out = [];
    for (let d = Math.ceil(years[0] / 10) * 10; d <= last; d += 10) {
      const m = meanOver(series.mean, d, d + 9);
      const n = years.filter((yr) => yr >= d && yr <= d + 9).length;
      if (m != null && n >= 5) out.push({ d, m, partial: n < 10 });
    }
    return out;
  });
  let hover = $state(null);
  function at(e) {
    const r = e.currentTarget.getBoundingClientRect();
    const px = ((e.clientX - r.left) / r.width) * W;
    const yr = Math.round(x.invert(px));
    hover = yr >= years[0] && yr <= last ? yr : null;
  }
  let k = $derived(hover == null ? -1 : years.indexOf(hover));
  const f1 = (v) => (v == null ? '—' : v < 10 ? v.toFixed(1) : Math.round(v).toString());
</script>

<div class="ri">
  <div class="head">
    <span class="lbl">{label}</span>
    <span class="nums"><b>{f1(baseMean)}</b><span class="muted"> {baseline[0]}–{baseline[1]}</span> → <b class="accent">{f1(lastMean)}</b><span class="muted"> {last - 9}–{last}</span></span>
  </div>
  <svg viewBox="0 0 {W} {height}" role="img" aria-label={label} onpointermove={at} onpointerleave={() => (hover = null)}>
    {#each yTicks as t (t)}
      <line x1={M.left} x2={W - M.right} y1={y(t)} y2={y(t)} stroke={t === 0 ? AXIS : GRID} />
      <text x={M.left - 5} y={y(t) + 4} text-anchor="end" font-size="10" fill={MUTED}>{t}</text>
    {/each}
    <path d={bandPath} fill={color} opacity="0.12" />
    <path d={band50} fill={color} opacity="0.16" />
    {#each years as yr, i (yr)}
      <rect x={x(yr) - bw / 2} y={y(series.mean[i])} width={bw} height={Math.max(0, y(0) - y(series.mean[i]))} rx={Math.min(2, bw / 2)} fill={color} opacity={series.n_observed[i] === 0 ? 0.35 : 0.9} />
    {/each}
    {#each decades as s (s.d)}
      <line x1={x(s.d) - bw / 2} x2={x(Math.min(s.d + 9, last)) + bw / 2} y1={y(s.m)} y2={y(s.m)} stroke={HIGHLIGHT} stroke-width="2" stroke-dasharray={s.partial ? '3 3' : null} />
    {/each}
    {#if k >= 0}
      <line x1={x(hover)} x2={x(hover)} y1={M.top} y2={y(0)} stroke={INK} opacity="0.5" />
    {/if}
    {#each years.filter((yr) => yr % 20 === 0) as yr (yr)}
      <text x={x(yr)} y={height - 8} text-anchor="middle" font-size="10" fill={MUTED}>{yr}</text>
    {/each}
    {#if trendLabel}
      <text x={M.left + 4} y={M.top - 8} font-size="10.5" fill={INK}>{trendLabel}</text>
    {/if}
  </svg>
  <div class="tip small">
    {#if k >= 0}
      <b>{hover}</b>: {f1(series.mean[k])} {unitLabel} per station (90% range {f1(series.p05[k])}–{f1(series.p95[k])}); {series.n_observed[k]} of {series.n_stations} stations reporting
    {:else if !compact}
      Average per station across all {series.n_stations} stations, with missing station-years filled in by the model. Band: 90% range. Dark steps: decade averages.
    {/if}
  </div>
</div>

<style>
  .ri svg {
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
    margin-bottom: 0.1rem;
  }
  .lbl {
    font-size: 0.9rem;
    font-weight: 650;
    color: #1f1b16;
  }
  .nums {
    font-size: 0.95rem;
    color: #52514e;
  }
  .nums b {
    font-size: 1.35rem;
    color: #1f1b16;
  }
  .nums b.accent {
    color: #c2410c;
  }
  .tip {
    min-height: 1.2rem;
  }
</style>
