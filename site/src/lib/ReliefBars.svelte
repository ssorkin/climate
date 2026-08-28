<script>
  /**
   * Overnight relief on a typical heat-wave night: of the 14 hours between 6 pm and 8 am,
   * how many were under the relief threshold — then and now, as two stacked bars.
   */
  import { COOL, GRID, MUTED, INK, INK2, HEAT_RAMP } from '$lib/palette.js';
  import { units } from '$lib/units.svelte.js';
  import { tempF } from '$lib/hw.js';

  let { rows = [], reliefF = 70, big = false } = $props(); // [{label, then:{relief_h, years}, now:{...}, change?: text}]
  const NIGHT = 14;
  const W = 920;
  let M = $derived({ left: 90, right: 24 });
  let ROW = $derived(big ? 110 : 76);
  let BAR = $derived(big ? 26 : 14);
  let H = $derived(28 + rows.length * ROW);
  let x = $derived((h) => M.left + (h / NIGHT) * (W - M.left - M.right));
  const hours = [0, 2, 4, 6, 8, 10, 12, 14];
  const f1 = (v) => (v == null ? '—' : v.toFixed(1));
</script>

<div class="chart">
  <svg viewBox="0 0 {W} {H}" role="img" aria-label="Hours under {tempF(reliefF, units.f)} on a heat-wave night, then and now">
    {#each hours as h}
      <line x1={x(h)} x2={x(h)} y1="20" y2={H - 4} stroke={GRID} />
      <text x={x(h)} y="13" text-anchor="middle" font-size="12" fill={MUTED}>{h} h</text>
    {/each}
    {#each rows as r, i}
      {@const top = 28 + i * ROW}
      <text x={x(0)} y={top + 10} font-size={big ? 15 : 13} font-weight="700" fill={INK}>{r.label}</text>
      {#each [['then', r.then], ['now', r.now]] as [k, e], j}
        {@const y = top + 18 + j * (BAR + 6)}
        <rect x={x(0)} y={y} width={x(NIGHT) - x(0)} height={BAR} fill={HEAT_RAMP[1]} rx="2" />
        <rect x={x(0)} y={y} width={Math.max(0, x(e.relief_h) - x(0))} height={BAR} fill={COOL} rx="2" />
        <text x={x(e.relief_h) + 8} y={y + BAR / 2 + 4} font-size={big ? 14 : 12} font-weight="700" fill={INK2}>{f1(e.relief_h)} h under {tempF(reliefF, units.f)}{k === 'now' && r.change ? ` (${r.change})` : ''}</text>
        <text x={x(0) - 6} y={y + BAR / 2 + 4} text-anchor="end" font-size="11" fill={MUTED}>{e.years.join('–')}</text>
      {/each}
    {/each}
  </svg>
</div>

<style>
  .chart svg {
    width: 100%;
    height: auto;
    display: block;
  }
</style>
