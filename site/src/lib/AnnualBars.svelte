<script>
  /**
   * One bar per year. null = incomplete year (drawn as a small gray tick at the
   * baseline, never as 0); `partial` years are hatched ("so far"). Decade means
   * overlay as short horizontal steps; the trend is a text label, not a fitted line
   * pretending to be data. Click a bar to select that year.
   */
  import { linear, ticks } from '$lib/scales.js';
  import { HEAT, COOL, GRID, AXIS, MUTED, INK, NEUTRAL, HIGHLIGHT, SURFACE } from '$lib/palette.js';

  let {
    years = [],
    values = [],
    lower = [], // count over observed days; drawn hollow when the year is incomplete
    daysValid = [],
    daysTotal = [],
    partial = [],
    decades = null, // {decade:[], value:[]} means per decade
    selected = null,
    onselect = null,
    color = HEAT,
    unitLabel = 'days',
    yFormat = (v) => String(v),
    trendLabel = '',
    annotations = [], // [{year, label}]
    baseline = null, // {years:[y0,y1], value}
    height = 300
  } = $props();

  const W = 860;
  const M = { top: 22, right: 16, bottom: 34, left: 40 };
  let H = $derived(height);
  let innerW = $derived(W - M.left - M.right);
  let innerH = $derived(H - M.top - M.bottom);

  let x = $derived(linear([years[0] - 0.5, years[years.length - 1] + 0.5], [M.left, W - M.right]));
  let bw = $derived(Math.max(1.5, Math.min(24, (innerW / years.length) * 0.78)));
  let vmax = $derived(Math.max(1, ...values.filter((v) => v != null), ...lower.filter((v) => v != null), ...(decades?.value ?? []).filter((v) => v != null)));
  let yTicks = $derived(ticks(0, vmax * 1.08, 5));
  let y = $derived(linear([0, yTicks[yTicks.length - 1]], [M.top + innerH, M.top]));

  let hover = $state(null);
  let hovered = $derived(hover == null ? null : years.indexOf(hover));

  function nearest(e) {
    const r = e.currentTarget.getBoundingClientRect();
    const px = ((e.clientX - r.left) / r.width) * W;
    const yr = Math.round(x.invert(px));
    hover = Math.max(years[0], Math.min(years[years.length - 1], yr));
  }
  let tip = $derived.by(() => {
    const k = hovered ?? years.indexOf(selected);
    if (k < 0) return '';
    const v = values[k];
    const yr = years[k];
    const obs = daysValid[k] != null && daysTotal[k] != null ? ` (${daysValid[k]} of ${daysTotal[k]} days observed)` : '';
    if (v == null) {
      if (partial[k] && lower[k] != null) return `${yr}: ${yFormat(lower[k])} ${unitLabel} so far${obs}`;
      if (lower[k] != null) return `${yr}: at least ${yFormat(lower[k])} ${unitLabel} — incomplete year${obs}`;
      return `${yr}: no data`;
    }
    return `${yr}: ${yFormat(v)} ${unitLabel}${partial[k] ? ' so far' : ''}${obs}`;
  });
  let decadeSegs = $derived(
    decades
      ? decades.decade.map((d, i) => ({ d, v: decades.value[i], partial: decades.partial?.[i] })).filter((s) => s.v != null)
      : []
  );
</script>

<div class="chart">
  <svg viewBox="0 0 {W} {H}" role="img" aria-label="Annual counts by year" onpointermove={nearest} onpointerleave={() => (hover = null)} onclick={() => hover != null && onselect?.(hover)}>
    <defs>
      <pattern id="hatch" width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
        <rect width="2" height="4" fill={color} />
      </pattern>
    </defs>
    {#each yTicks as t (t)}
      <line x1={M.left} x2={W - M.right} y1={y(t)} y2={y(t)} stroke={t === 0 ? AXIS : GRID} stroke-width="1" />
      <text x={M.left - 6} y={y(t) + 4} text-anchor="end" font-size="11" fill={MUTED}>{yFormat(t)}</text>
    {/each}
    {#each years as yr, k (yr)}
      {@const v = values[k]}
      {#if v == null && lower[k] != null && lower[k] > 0}
        <rect
          x={x(yr) - bw / 2}
          y={y(lower[k])}
          width={bw}
          height={Math.max(0, y(0) - y(lower[k]))}
          rx={Math.min(3, bw / 2)}
          fill={partial[k] ? 'url(#hatch)' : 'none'}
          stroke={color}
          stroke-width="1"
          stroke-dasharray={partial[k] ? null : '2 2'}
          opacity="0.8"
        />
      {:else if v == null}
        <rect x={x(yr) - bw / 2} y={y(0) - 3} width={bw} height="3" fill={NEUTRAL} opacity="0.7" />
      {:else}
        <rect
          x={x(yr) - bw / 2}
          y={y(v)}
          width={bw}
          height={Math.max(0, y(0) - y(v))}
          rx={Math.min(3, bw / 2)}
          fill={partial[k] ? 'url(#hatch)' : color}
          opacity={selected != null && yr !== selected && hover == null ? 0.75 : 1}
        />
      {/if}
    {/each}
    {#each decadeSegs as s (s.d)}
      <line x1={x(s.d) - bw / 2} x2={x(s.d + 9) + bw / 2} y1={y(s.v)} y2={y(s.v)} stroke={HIGHLIGHT} stroke-width="2" stroke-dasharray={s.partial ? '3 3' : null} />
    {/each}
    {#if baseline}
      <text x={x(baseline.years[0])} y={y(baseline.value) - 5} font-size="10.5" fill={INK}>avg {baseline.years[0]}–{baseline.years[1]}: {yFormat(baseline.value)}</text>
    {/if}
    {#each annotations as a (a.year + ':' + a.label)}
      {#if a.year >= years[0] && a.year <= years[years.length - 1]}
        {#if a.label}
          <line x1={x(a.year)} x2={x(a.year)} y1={M.top - 4} y2={y(0)} stroke={INK} stroke-width="1" opacity="0.35" />
          <text x={x(a.year) + (x(a.year) > W * 0.7 ? -4 : 4)} y={M.top + 6} text-anchor={x(a.year) > W * 0.7 ? 'end' : 'start'} font-size="10.5" fill={INK}>{a.label}</text>
        {:else}
          <line x1={x(a.year)} x2={x(a.year)} y1={M.top + 8} y2={y(0)} stroke={INK} stroke-width="1" stroke-dasharray="2 3" opacity="0.5" />
          <path d="M{x(a.year) - 4} {M.top} l8 0 l-4 6 z" fill={INK} opacity="0.6" />
        {/if}
      {/if}
    {/each}
    {#if selected != null && years.includes(selected)}
      <rect x={x(selected) - bw / 2 - 2} y={M.top} width={bw + 4} height={innerH} fill="none" stroke={HIGHLIGHT} stroke-width="1.5" rx="3" />
    {/if}
    {#if hover != null}
      <line x1={x(hover)} x2={x(hover)} y1={M.top} y2={y(0)} stroke={INK} stroke-width="1" opacity="0.5" />
    {/if}
    {#each years.filter((yr) => yr % 20 === 0) as yr (yr)}
      <text x={x(yr)} y={H - 12} text-anchor="middle" font-size="11" fill={MUTED}>{yr}</text>
    {/each}
    {#if trendLabel}
      <text x={W - M.right} y={M.top - 8} text-anchor="end" font-size="11.5" fill={INK}>{trendLabel}</text>
    {/if}
  </svg>
  <div class="tip">{tip}<span class="muted"> · bars: each year · dark steps: decade averages · hollow bars: incomplete years, at least this many{#if annotations.some((a) => !a.label)} · ▼ dotted: site/instrument change detected by NOAA{/if}</span></div>
</div>

<style>
  .chart svg {
    width: 100%;
    height: auto;
    display: block;
    cursor: crosshair;
    background: transparent;
  }
</style>
