<script>
  /**
   * Per station: the trend in warm-season mean daily low (filled) and daily high (hollow),
   * °F per decade with 90% whiskers, longest records first. The gap between the two dots is
   * the diurnal-range story.
   */
  import { units } from '$lib/units.svelte.js';
  import { linear, ticks } from '$lib/scales.js';
  import { GRID, AXIS, MUTED, INK, HEAT, COOL, SURFACE } from '$lib/palette.js';
  let { stations = [], rowH = 16 } = $props();
  const conv = (c) => (units.f ? c * 1.8 : c);
  let rows = $derived(
    stations
      .map((s) => ({ s, n: s.headline?.trend_jja_tmin, d: s.headline?.trend_jja_tmax }))
      .filter((r) => r.n && r.d)
      .sort((a, b) => a.n.from - b.n.from || b.n.slope_per_decade - a.n.slope_per_decade)
  );
  const W = 620, L = 178, R = 84;
  let H = $derived(rows.length * rowH + 30);
  let ext = $derived.by(() => {
    const v = rows.flatMap((r) => [r.n.ci[0], r.n.ci[1], r.d.ci[0], r.d.ci[1]].map(conv));
    const lo = Math.min(0, ...v), hi = Math.max(0, ...v), pad = (hi - lo) * 0.06;
    return [lo - pad, hi + pad];
  });
  let x = $derived(linear(ext, [L, W - R]));
  let xt = $derived(ticks(ext[0], ext[1], 5));
  let hover = $state(null);
  const f = (c) => (conv(c) > 0 ? '+' : '') + conv(c).toFixed(2);
  let nFaster = $derived(rows.filter((r) => r.n.slope_per_decade > r.d.slope_per_decade).length);
</script>

<div class="pairs">
  <div class="head"><span class="lbl">Warm-season (Jun–Aug) mean daily low vs. high — trend at each station</span><span class="muted small">nights warming faster at {nFaster} of {rows.length}</span></div>
  <svg viewBox="0 0 {W} {H}" role="img" aria-label="Trend in mean low vs mean high per station" onpointerleave={() => (hover = null)}>
    {#each xt as t (t)}
      <line x1={x(t)} x2={x(t)} y1={8} y2={H - 22} stroke={t === 0 ? AXIS : GRID} stroke-width={t === 0 ? 1.5 : 1} />
      <text x={x(t)} y={H - 8} text-anchor="middle" font-size="10" fill={MUTED}>{t > 0 ? '+' : ''}{t.toFixed(1)}</text>
    {/each}
    <text x={W - R} y={H - 8} text-anchor="start" font-size="10" fill={MUTED}>&nbsp;°{units.f ? 'F' : 'C'}/decade</text>
    {#each rows as r, i (r.s.id)}
      {@const y = 14 + i * rowH}
      <rect x="0" y={y - rowH / 2} width={W} height={rowH} fill="transparent" onpointerenter={() => (hover = r.s.id)} />
      <text x={L - 8} y={y + 3.5} text-anchor="end" font-size="10.5" fill={INK}>{r.s.short}</text>
      <line x1={x(conv(r.d.ci[0]))} x2={x(conv(r.d.ci[1]))} y1={y - 3} y2={y - 3} stroke={HEAT} stroke-width="1" opacity="0.6" />
      <circle cx={x(conv(r.d.slope_per_decade))} cy={y - 3} r="4" fill={SURFACE} stroke={HEAT} stroke-width="1.6" />
      <line x1={x(conv(r.n.ci[0]))} x2={x(conv(r.n.ci[1]))} y1={y + 3} y2={y + 3} stroke={COOL} stroke-width="1" opacity="0.6" />
      <circle cx={x(conv(r.n.slope_per_decade))} cy={y + 3} r="4" fill={COOL} stroke={SURFACE} stroke-width="1.2" />
      <text x={W - R + 6} y={y + 3.5} font-size="10" fill={MUTED}>{r.n.from}–{r.n.to}</text>
    {/each}
  </svg>
  <div class="legend small"><span><i class="lo"></i> daily low (night)</span><span><i class="hi"></i> daily high (day)</span></div>
  <div class="tip small">
    {#if hover}
      {@const r = rows.find((q) => q.s.id === hover)}
      <b>{r.s.short}</b>: lows {f(r.n.slope_per_decade)}°/decade ({r.n.significant ? 'clear' : 'not clear'}), highs {f(r.d.slope_per_decade)}°/decade ({r.d.significant ? 'clear' : 'not clear'}), {r.n.from}–{r.n.to}
    {:else}
      Filled: the trend in June–August mean daily low. Hollow: mean daily high. Whiskers: 90% range. Nights lead almost everywhere.
    {/if}
  </div>
</div>

<style>
  .pairs svg {
    width: 100%;
    height: auto;
    display: block;
  }
  .head {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 0.6rem;
    flex-wrap: wrap;
  }
  .head .lbl {
    font-size: 0.9rem;
    font-weight: 650;
    color: #1f1b16;
  }
  .legend {
    display: flex;
    gap: 1rem;
    color: #52514e;
  }
  .legend i {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    vertical-align: middle;
    margin-right: 0.3rem;
  }
  .legend i.lo {
    background: #2a78d6;
  }
  .legend i.hi {
    background: #fffdf9;
    border: 1.6px solid #d94f22;
  }
</style>
