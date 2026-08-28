<script>
  /**
   * Heat waves per summer, one small bar chart per station, with the then/now averages
   * as short lines. Summers that are not complete draw as a faint tick, never as zero.
   */
  import { linear } from '$lib/scales.js';
  import { HEAT, GRID, AXIS, MUTED, INK, INK2 } from '$lib/palette.js';
  import { waveRows } from '$lib/hw.js';

  let { stations = [], rowHeight = 78 } = $props();
  const W = 920;
  const M = { left: 210, right: 130, top: 18, bottom: 22 };
  let x0 = $derived(Math.min(...stations.map((s) => s.years[0])) - 0.5);
  let x1 = $derived(Math.max(...stations.map((s) => s.years.at(-1))) + 0.5);
  let x = $derived(linear([x0, x1], [M.left, W - M.right]));
  let bw = $derived((W - M.left - M.right) / (x1 - x0) - 1.5);
  let H = $derived(M.top + stations.length * rowHeight + M.bottom);
  let xTicks = $derived.by(() => { const t = []; for (let v = Math.ceil(x0 / 10) * 10; v <= x1; v += 10) t.push(v); return t; });
  let counts = $derived(
    stations.map((s) => {
      const c = {};
      for (const w of waveRows(s)) c[w.year] = (c[w.year] ?? 0) + 1;
      return c;
    })
  );
  let ymax = $derived(Math.max(4, ...counts.flatMap((c) => Object.values(c))));
  let hover = $state(null);
</script>

<div class="chart">
  <svg viewBox="0 0 {W} {H}" role="img" aria-label="Heat waves per summer by station and year" onpointerleave={() => (hover = null)}>
    {#each xTicks as v}
      <line x1={x(v)} x2={x(v)} y1={M.top} y2={H - M.bottom} stroke={GRID} />
      <text x={x(v)} y={H - 6} text-anchor="middle" font-size="12" fill={MUTED}>{v}</text>
    {/each}
    {#each stations as s, i}
      {@const top = M.top + i * rowHeight}
      {@const base = top + rowHeight - 14}
      {@const y = (v) => base - (v / ymax) * (rowHeight - 24)}
      <line x1={M.left} x2={W - M.right} y1={base} y2={base} stroke={AXIS} />
      <text x={M.left - 12} y={top + rowHeight / 2} text-anchor="end" font-size="13" fill={INK}>{s.short}</text>
      {#each s.years as yr}
        {@const c = counts[i][yr] ?? 0}
        <rect x={x(yr) - bw / 2} y={c ? y(c) : base - 1.5} width={bw} height={c ? base - y(c) : 1.5} fill={c ? HEAT : AXIS} rx="1" />
        <rect x={x(yr) - bw / 2 - 1} y={top} width={bw + 2} height={rowHeight - 14} fill="transparent" onpointerenter={() => (hover = { s, yr, c })} />
      {/each}
      {#each [['baseline', s.windows?.baseline], ['last30', s.windows?.last30]] as [key, e], k}
        {#if e}
          <line x1={x(e.years[0]) - bw / 2} x2={x(e.years[1]) + bw / 2} y1={y(e.waves_per_year)} y2={y(e.waves_per_year)} stroke={INK} stroke-width="2" />
          <text x={W - M.right + 8} y={top + 22 + k * 15} font-size="12" fill={INK2}>{e.years[0]}–{String(e.years[1]).slice(key === 'baseline' ? 2 : 0)}: <tspan font-weight="700" fill={INK}>{e.waves_per_year.toFixed(1)}/yr</tspan></text>
        {/if}
      {/each}
    {/each}
  </svg>
  <div class="tip">{hover ? `${hover.s.short}, ${hover.yr}: ${hover.c} heat wave${hover.c === 1 ? '' : 's'}` : 'One bar per complete summer; a flat tick is a summer with too few valid days. Hover a bar.'}</div>
</div>

<style>
  .chart svg {
    width: 100%;
    height: auto;
    display: block;
  }
</style>
