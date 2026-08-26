<script>
  /**
   * Small multiples: one panel per station, a dot per decade (mean per year),
   * connected by a thin line; first and last decades direct-labeled. All panels
   * share the y-scale within the section so the eye can compare.
   */
  import { linear } from '$lib/scales.js';
  import { HEAT, COOL, GRID, MUTED, INK, AXIS, SURFACE, NEUTRAL } from '$lib/palette.js';

  let { stations = [], metric = 'warm70', unitLabel = 'nights', cool = false, sharedScale = true, cols = 4 } = $props();

  const W = 220;
  const H = 130;
  const M = { top: 22, right: 14, bottom: 22, left: 10 };
  let panels = $derived(
    stations.map((s) => {
      const d = s.decades;
      const pts = d.decade.map((dec, i) => ({ dec, v: d[metric][i], partial: d.partial[i] })).filter((p) => p.v != null);
      const first = pts[0], last = pts[pts.length - 1];
      return { s, pts, first, last, delta: first && last ? last.v - first.v : null };
    }).filter((p) => p.pts.length >= 3)
  );
  let sorted = $derived([...panels].sort((a, b) => (b.delta ?? -1e9) - (a.delta ?? -1e9)));
  let gmax = $derived(Math.max(1, ...panels.flatMap((p) => p.pts.map((q) => q.v))));
  let d0 = $derived(Math.min(...panels.flatMap((p) => p.pts.map((q) => q.dec))));
  let d1 = $derived(Math.max(...panels.flatMap((p) => p.pts.map((q) => q.dec))));
  let x = $derived(linear([d0, d1], [M.left + 18, W - M.right - 18]));
  let color = $derived(cool ? COOL : HEAT);
  let hover = $state(null);
</script>

<div class="grid" style:--cols={cols}>
  {#each sorted as p (p.s.id)}
    {@const ymax = sharedScale ? gmax : Math.max(1, ...p.pts.map((q) => q.v))}
    {@const y = linear([0, ymax * 1.15], [H - M.bottom, M.top])}
    <div class="panel">
      <div class="name"><a href="/station/{p.s.id}?m={metric.startsWith('hot') ? 'hot' : metric.startsWith('warm') ? 'warm' : 'frost'}">{p.s.short}</a> <span class="muted small">since {p.s.first_year}</span></div>
      <svg viewBox="0 0 {W} {H}" role="img" aria-label="{p.s.short}: {unitLabel} per year by decade" onpointerleave={() => (hover = null)}>
        <line x1={M.left} x2={W - M.right} y1={y(0)} y2={y(0)} stroke={AXIS} />
        <polyline points={p.pts.map((q) => `${x(q.dec)},${y(q.v)}`).join(' ')} fill="none" stroke={color} stroke-width="1.5" opacity="0.6" />
        {#each p.pts as q (q.dec)}
          <circle cx={x(q.dec)} cy={y(q.v)} r={q.partial ? 4 : 5} fill={q.partial ? SURFACE : color} stroke={color} stroke-width="2" />
          <rect x={x(q.dec) - 10} y={M.top - 10} width="20" height={H - M.top} fill="transparent" onpointerenter={() => (hover = { id: p.s.id, q })} />
        {/each}
        <text x={x(p.first.dec)} y={y(p.first.v) - 9} text-anchor="middle" font-size="11" fill={INK}>{p.first.v.toFixed(p.first.v < 10 ? 1 : 0)}</text>
        <text x={x(p.last.dec)} y={y(p.last.v) - 9} text-anchor="middle" font-size="11.5" font-weight="700" fill={INK}>{p.last.v.toFixed(p.last.v < 10 ? 1 : 0)}</text>
        <text x={x(p.first.dec)} y={H - 6} text-anchor="middle" font-size="10" fill={MUTED}>{p.first.dec}s</text>
        <text x={x(p.last.dec)} y={H - 6} text-anchor="middle" font-size="10" fill={MUTED}>{p.last.dec}s{p.last.partial ? '*' : ''}</text>
        {#if hover?.id === p.s.id}
          <text x={W / 2} y={12} text-anchor="middle" font-size="10.5" fill={INK}>{hover.q.dec}s: {hover.q.v.toFixed(1)} {unitLabel}/yr{hover.q.partial ? ' so far' : ''}</text>
        {/if}
      </svg>
    </div>
  {/each}
</div>
<p class="small muted">Each dot is the average per year over a decade (complete years only). * = current decade so far. Panels sorted by change; same vertical scale everywhere.</p>

<style>
  .grid {
    display: grid;
    grid-template-columns: repeat(var(--cols), 1fr);
    gap: 0.6rem 1rem;
  }
  .panel svg {
    width: 100%;
    height: auto;
    display: block;
  }
  .name {
    font-size: 0.9rem;
    font-weight: 600;
  }
  .name a {
    color: #1f1b16;
    text-decoration: none;
  }
  .name a:hover {
    text-decoration: underline;
  }
  @media (max-width: 900px) {
    .grid {
      grid-template-columns: repeat(2, 1fr);
    }
  }
</style>
