<script>
  /**
   * Three temperatures from every heat wave, then vs now, one row per station on one
   * °F axis: the hottest afternoon (orange), the coolest heat-wave night (blue) and the
   * night after the wave ends (light blue). Hollow = baseline window, filled = last 30
   * complete summers; the whisker on the filled dot is the 95% interval of the change.
   */
  import { linear } from '$lib/scales.js';
  import { HEAT, COOL, COOL_RAMP, GRID, MUTED, INK, INK2, SURFACE } from '$lib/palette.js';
  import { units } from '$lib/units.svelte.js';
  import { tempF, deltaF, axisT, ci95 } from '$lib/hw.js';

  let { stations = [], baseline = null } = $props(); // baseline: [y0, y1] for the caption
  const SERIES = [
    { key: 'after_low_f', label: 'night after it ends', color: COOL_RAMP[3] },
    { key: 'low_f', label: 'coolest heat-wave night', color: COOL },
    { key: 'peak_f', label: 'hottest afternoon', color: HEAT }
  ];
  const W = 920;
  const M = { left: 190, right: 220, top: 52, bottom: 8 };
  const ROW = 34;
  let H = $derived(M.top + stations.length * ROW + M.bottom);
  let vals = $derived(stations.flatMap((s) => SERIES.flatMap((k) => [s.windows.baseline[k.key], s.windows.last30[k.key]])).filter((v) => v != null));
  let lo = $derived(Math.floor((Math.min(...vals) - 3) / 5) * 5);
  let hi = $derived(Math.ceil((Math.max(...vals) + 3) / 5) * 5);
  let x = $derived(linear([lo, hi], [M.left, W - M.right]));
  let xt = $derived.by(() => { const t = []; for (let v = lo; v <= hi; v += 10) t.push(v); return t; });
  const colX = [W - M.right + 14, W - M.right + 84, W - M.right + 158];
  let hover = $state(null);
  const dF = (v) => deltaF(v, units.f);
</script>

<div class="chart">
  <svg viewBox="0 0 {W} {H}" role="img" aria-label="Hottest afternoon, coolest heat-wave night and the night after, then versus now, by station" onpointerleave={() => (hover = null)}>
    {#each xt as v}
      <line x1={x(v)} x2={x(v)} y1={M.top - 6} y2={H - M.bottom} stroke={GRID} />
      <text x={x(v)} y={M.top - 12} text-anchor="middle" font-size="12" fill={MUTED}>{Math.round(axisT(v, units.f))}°</text>
    {/each}
    {#each SERIES as k, j}
      <text x={colX[j]} y={M.top - 30} font-size="11" font-weight="600" fill={k.color}>{k.key === 'peak_f' ? 'afternoon' : k.key === 'low_f' ? 'coolest night' : 'night after'}</text>
    {/each}
    {#each stations as s, i}
      {@const yy = M.top + i * ROW + 12}
      {@const b = s.windows.baseline}
      {@const n = s.windows.last30}
      <text x={M.left - 12} y={yy + 4} text-anchor="end" font-size="13" fill={INK}>{s.short}</text>
      <g onpointerenter={() => (hover = i)}>
        {#each SERIES as k, j}
          {@const a = b[k.key]}
          {@const c = n[k.key]}
          {#if a != null && c != null}
            {@const ci = ci95(b, n, k.key)}
            {#if ci != null}
              <line x1={x(c - ci)} x2={x(c + ci)} y1={yy} y2={yy} stroke={k.color} stroke-width="1" opacity="0.6" />
            {/if}
            <line x1={x(a)} x2={x(c)} y1={yy} y2={yy} stroke={k.color} stroke-width="3" stroke-linecap="round" />
            <circle cx={x(a)} cy={yy} r="5.5" fill={SURFACE} stroke={k.color} stroke-width="2" />
            <circle cx={x(c)} cy={yy} r="5.5" fill={k.color} stroke={SURFACE} stroke-width="2" />
            <text x={colX[j]} y={yy + 4} font-size="12.5" font-weight="700" fill={Math.abs(c - a) > (ci ?? 0) ? k.color : MUTED}>{dF(c - a)}</text>
          {/if}
        {/each}
        <rect x={M.left} y={yy - ROW / 2} width={W - M.left - M.right} height={ROW} fill="transparent" />
      </g>
    {/each}
  </svg>
  <div class="tip">
    {#if hover == null}
      Hollow: {baseline ? baseline.join('–') : 'baseline'}. Filled: the last 30 complete summers. Whisker: 95% interval of the change. Gray change = within that interval.
    {:else}
      {@const s = stations[hover]}
      {s.short}: hottest afternoon {tempF(s.windows.baseline.peak_f, units.f)} → {tempF(s.windows.last30.peak_f, units.f)} · coolest heat-wave night {tempF(s.windows.baseline.low_f, units.f)} → {tempF(s.windows.last30.low_f, units.f)} · night after {tempF(s.windows.baseline.after_low_f, units.f)} → {tempF(s.windows.last30.after_low_f, units.f)} ({s.windows.baseline.peak_f_n} then, {s.windows.last30.peak_f_n} now heat waves)
    {/if}
  </div>
</div>

<style>
  .chart svg {
    width: 100%;
    height: auto;
    display: block;
  }
</style>
