<script>
  /**
   * The story in four numbers, pooled across every station with a record in both windows:
   * the change from the baseline to the last 30 complete summers in the hottest afternoon,
   * the coolest heat-wave night, days per heat wave and heat waves per summer — each with
   * a 95% interval (station estimates combined as independent). A change whose interval
   * crosses zero prints gray; the two that don't carry the story.
   */
  import { HEAT, COOL, MUTED, INK, GRID, AXIS } from '$lib/palette.js';
  import { units } from '$lib/units.svelte.js';
  import { ci95 } from '$lib/hw.js';

  let { stations = [], baseline = [1951, 1980] } = $props();

  const ROWS = [
    { key: 'peak_f', label: 'Hottest afternoon', kind: 'temp', color: HEAT },
    { key: 'low_f', label: 'Coolest heat-wave night', kind: 'temp', color: COOL },
    { key: 'mean_days', sd: 'days', label: 'Days per heat wave', kind: 'days', color: HEAT },
    { key: 'waves_per_year', label: 'Heat waves per summer', kind: 'count', color: HEAT }
  ];
  // pooled change: mean of station changes; interval from the station intervals combined
  let rows = $derived(
    ROWS.map((r) => {
      const d = [], v = [];
      for (const s of stations) {
        const a = s.windows.baseline[r.key], b = s.windows.last30[r.key];
        if (a == null || b == null) continue;
        d.push(b - a);
        const ci = ci95(s.windows.baseline, s.windows.last30, r.sd ?? r.key);
        v.push(ci == null ? null : (ci / 1.96) ** 2);
      }
      if (!d.length) return { ...r, change: null };
      const mean = d.reduce((x, y) => x + y, 0) / d.length;
      const vv = v.filter((x) => x != null);
      const ci = vv.length === d.length ? (1.96 * Math.sqrt(vv.reduce((x, y) => x + y, 0))) / d.length : null;
      return { ...r, change: mean, ci, n: d.length };
    })
  );
  const conv = (r, v) => (r.kind === 'temp' && !units.f ? v / 1.8 : v);
  const fmt = (r, v) => {
    if (v == null) return '—';
    const x = conv(r, v);
    const d = r.kind === 'count' ? 2 : 1;
    const a = Math.abs(x).toFixed(d);
    const s = (Number(a) === 0 ? '' : x >= 0 ? '+' : '−') + a;
    return r.kind === 'temp' ? `${s}°` : r.kind === 'days' ? `${s} d` : `${s}/yr`;
  };
  // one small interval glyph per row on its own scale: ±max(|change|+ci) so zero sits mid
  const W = 110;
  const H = 14;
  const glyph = (r) => {
    const span = Math.max(Math.abs(r.change) + (r.ci ?? 0), 1e-6) * 1.1;
    const x = (v) => W / 2 + (v / span) * (W / 2 - 4);
    return { x0: x(0), lo: x(r.change - (r.ci ?? 0)), hi: x(r.change + (r.ci ?? 0)), c: x(r.change) };
  };
</script>

<div class="panel card">
  <div class="head">Then → now, {stations.length} stations</div>
  <div class="sub">{baseline[0]}–{baseline[1]} to the last 30 complete summers, pooled, with 95% intervals</div>
  {#each rows as r}
    {#if r.change != null}
      {@const g = glyph(r)}
      {@const clear = r.ci != null && Math.abs(r.change) > r.ci}
      <div class="row">
        <div class="lbl">{r.label}</div>
        <div class="val" style:color={clear ? r.color : MUTED}>{fmt(r, r.change)}</div>
        <svg viewBox="0 0 {W} {H}" width={W} height={H} aria-label="95% interval">
          <line x1="4" x2={W - 4} y1={H / 2} y2={H / 2} stroke={GRID} />
          <line x1={g.x0} x2={g.x0} y1="2" y2={H - 2} stroke={AXIS} />
          {#if r.ci != null}<line x1={g.lo} x2={g.hi} y1={H / 2} y2={H / 2} stroke={clear ? r.color : MUTED} stroke-width="3" stroke-linecap="round" />{/if}
          <circle cx={g.c} cy={H / 2} r="4" fill={clear ? r.color : MUTED} />
        </svg>
        <div class="ci">{r.ci == null ? '' : `± ${fmt(r, r.ci).replace(/^[+−]/, '')}`}</div>
      </div>
    {/if}
  {/each}
  <div class="foot">Gray: interval crosses zero. Tick = no change.</div>
</div>

<style>
  .panel {
    display: grid;
    gap: 0.45rem;
    align-content: start;
    font-variant-numeric: tabular-nums;
  }
  .head {
    font-weight: 700;
    color: #1f1b16;
  }
  .sub {
    font-size: 0.8rem;
    color: #898781;
    margin-bottom: 0.2rem;
  }
  .row {
    display: grid;
    grid-template-columns: 1fr auto auto auto;
    align-items: center;
    gap: 0.6rem;
    border-top: 1px solid #efe9df;
    padding-top: 0.45rem;
  }
  .lbl {
    font-size: 0.85rem;
    color: #52514e;
    line-height: 1.25;
  }
  .val {
    font-size: 1.25rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    min-width: 4.2rem;
    text-align: right;
  }
  .ci {
    font-size: 0.78rem;
    color: #898781;
    min-width: 3.4rem;
  }
  .foot {
    font-size: 0.75rem;
    color: #898781;
  }
  @media (max-width: 800px) {
    svg {
      display: none;
    }
  }
</style>
