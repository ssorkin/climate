<script>
  /**
   * The story in five numbers, pooled across every station with a record in both windows:
   * the then->now change in the hottest afternoon, the coolest heat-wave night, overnight
   * relief, days per heat wave and heat waves per summer — each with a 95% interval from a
   * hierarchical bootstrap (stations, then whole summers within each station). A change
   * whose interval includes zero prints gray; the ones that don't carry the story.
   */
  import { HEAT, COOL, MUTED, GRID, AXIS } from '$lib/palette.js';
  import { units } from '$lib/units.svelte.js';

  let { pooled = {}, nStations = 0, baseline = [1951, 1980], reliefF = 70 } = $props();

  const ROWS = [
    { key: 'peak_f', label: 'Hottest afternoon', kind: 'temp', color: HEAT },
    { key: 'low_f', label: 'Coolest heat-wave night', kind: 'temp', color: COOL },
    { key: 'relief_h', label: `Overnight relief (hours under ${reliefF}°F)`, kind: 'hours', color: COOL },
    { key: 'days', label: 'Days per heat wave', kind: 'days', color: HEAT },
    { key: 'waves_per_year', label: 'Heat waves per summer', kind: 'count', color: HEAT }
  ];
  let rows = $derived(ROWS.map((r) => ({ ...r, ...(pooled?.[r.key] ?? {}) })).filter((r) => r.est != null));
  const conv = (r, v) => (r.kind === 'temp' && !units.f ? v / 1.8 : v);
  const fmt = (r, v, signed = true) => {
    if (v == null) return '—';
    const x = conv(r, v);
    const d = r.kind === 'count' ? 2 : 1;
    const a = Math.abs(x).toFixed(d);
    const sgn = !signed || Number(a) === 0 ? '' : x >= 0 ? '+' : '−';
    const u = r.kind === 'temp' ? '°' : r.kind === 'days' ? ' d' : r.kind === 'hours' ? ' h' : '/yr';
    return `${sgn}${a}${u}`;
  };
  // one small interval glyph per row on its own scale, zero at the centre
  const W = 110;
  const H = 14;
  const glyph = (r) => {
    const span = Math.max(Math.abs(r.lo), Math.abs(r.hi), Math.abs(r.est), 1e-6) * 1.1;
    const x = (v) => W / 2 + (v / span) * (W / 2 - 4);
    return { x0: x(0), lo: x(r.lo), hi: x(r.hi), c: x(r.est) };
  };
  const clear = (r) => r.lo > 0 || r.hi < 0;
</script>

<div class="panel card">
  <div class="head">Then → now, {nStations} stations</div>
  <div class="sub">{baseline[0]}–{baseline[1]} to the last 30 complete summers, pooled, with 95% intervals</div>
  {#each rows as r}
    {@const g = glyph(r)}
    <div class="row">
      <div class="lbl">{r.label}</div>
      <div class="val" style:color={clear(r) ? r.color : MUTED}>{fmt(r, r.est)}</div>
      <svg viewBox="0 0 {W} {H}" width={W} height={H} aria-label="95% interval {fmt(r, r.lo)} to {fmt(r, r.hi)}">
        <line x1="4" x2={W - 4} y1={H / 2} y2={H / 2} stroke={GRID} />
        <line x1={g.x0} x2={g.x0} y1="2" y2={H - 2} stroke={AXIS} />
        <line x1={g.lo} x2={g.hi} y1={H / 2} y2={H / 2} stroke={clear(r) ? r.color : MUTED} stroke-width="3" stroke-linecap="round" />
        <circle cx={g.c} cy={H / 2} r="4" fill={clear(r) ? r.color : MUTED} />
      </svg>
      <div class="ci">{fmt(r, r.lo)} to {fmt(r, r.hi)}</div>
    </div>
  {/each}
  <div class="foot">Intervals resample whole summers within each station, then stations. Gray: interval includes zero.</div>
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
    font-size: 0.75rem;
    color: #898781;
    min-width: 5.6rem;
    white-space: nowrap;
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
