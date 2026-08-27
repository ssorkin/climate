<script>
  /**
   * Two numbers per station: the typical percentile of a night and of a day over the last ten
   * years, against that station's own 1951–1980 climate for the same date. 50 = unchanged.
   */
  import { linear } from '$lib/scales.js';
  import { GRID, AXIS, MUTED, INK, HEAT, COOL, SURFACE } from '$lib/palette.js';
  let { stations = [], rowH = 18 } = $props();
  let rows = $derived(
    stations
      .filter((s) => s.headline?.score?.tmin != null && s.headline?.score?.tmax != null)
      .map((s) => ({ s, n: s.headline.score.tmin, d: s.headline.score.tmax, span: s.headline.score.tmin_span, fb: !!s.headline.baseline_fallback, base: s.headline.base_period }))
      .sort((a, b) => b.n - a.n)
  );
  const W = 620, L = 170, R = 20;
  let H = $derived(rows.length * rowH + 34);
  let x = $derived(linear([20, 90], [L, W - R]));
  let hover = $state(null);
</script>

<div class="dots">
  <svg viewBox="0 0 {W} {H}" role="img" aria-label="Typical night and day percentile per station" onpointerleave={() => (hover = null)}>
    {#each [20, 30, 40, 50, 60, 70, 80, 90] as t (t)}
      <line x1={x(t)} x2={x(t)} y1={8} y2={H - 24} stroke={t === 50 ? AXIS : GRID} stroke-width={t === 50 ? 1.5 : 1} />
      <text x={x(t)} y={H - 10} text-anchor="middle" font-size="10" fill={MUTED}>{t}th</text>
    {/each}
    <text x={x(50)} y={H - 0} text-anchor="middle" font-size="9.5" fill={INK}>50th = same as 1951–80</text>
    {#each rows as r, i (r.s.id)}
      {@const y = 16 + i * rowH}
      <rect x="0" y={y - rowH / 2} width={W} height={rowH} fill="transparent" onpointerenter={() => (hover = r.s.id)} />
      <text x={L - 8} y={y + 3.5} text-anchor="end" font-size="10.5" fill={INK}>{r.s.short}{r.fb ? ' †' : ''}</text>
      <line x1={x(Math.min(r.n, r.d))} x2={x(Math.max(r.n, r.d))} y1={y} y2={y} stroke={AXIS} stroke-width="1.5" />
      <circle cx={x(r.d)} cy={y} r="5" fill={SURFACE} stroke={HEAT} stroke-width="1.8" />
      <circle cx={x(r.n)} cy={y} r="5" fill={COOL} stroke={SURFACE} stroke-width="1.2" />
    {/each}
  </svg>
  <div class="legend small"><span><i class="lo"></i> a typical night</span><span><i class="hi"></i> a typical day</span></div>
  <div class="tip small">
    {#if hover}
      {@const r = rows.find((q) => q.s.id === hover)}
      <b>{r.s.short}</b>, {r.span ? `${r.span[0]}–${r.span[1]}` : 'last ten years'}: a typical night is warmer than {Math.round(r.n)}% of {r.base ? `${r.base[0]}–${r.base[1]}` : 'baseline'} nights at the same date; a typical day, warmer than {Math.round(r.d)}% of days.{r.fb ? ' † Scored against its own first 30 years — no 1951–80 record.' : ''}
    {:else}
      Where a typical night (filled) and day (hollow) of each station's last ten complete years fall among 1951–1980 readings for the same time of year.{rows.some((r) => r.fb) ? ' † No 1951–80 record: scored against the station\'s own first 30 years.' : ''}
    {/if}
  </div>
</div>

<style>
  .dots svg {
    width: 100%;
    height: auto;
    display: block;
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
    border: 1.8px solid #d94f22;
  }
</style>
