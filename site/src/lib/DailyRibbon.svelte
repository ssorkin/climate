<script>
  /**
   * One year, day by day: the daily high and low (2px lines) over the 1951–1980
   * band (10th–90th percentile of that calendar date), record days as dots.
   * Missing days are gaps. Crosshair tooltip reads the day + observation time.
   */
  import { linear, ticks } from '$lib/scales.js';
  import { units } from '$lib/units.svelte.js';
  import { fmtTenths, tenthsToF, tenthsToC, fWhole, fToC } from '$lib/units.js';
  import { idxToDate, dateToIdx, doy366, fmtDate, MONTHS, obsAt, fmtObs, isLeap } from '$lib/dates.js';
  import { HEAT, COOL, HEAT_DARK, COOL_DARK, GRID, AXIS, MUTED, INK, SURFACE } from '$lib/palette.js';

  let { daily, year, family = 'hot', threshold = null, obsCaveat = true } = $props();

  const W = 860;
  const H = 340;
  const M = { top: 16, right: 14, bottom: 30, left: 40 };

  let start = $derived(dateToIdx(daily.start, new Date(Date.UTC(year, 0, 1))));
  let nDays = $derived(isLeap(year) ? 366 : 365);
  let recIdx = $derived.by(() => {
    const s = new Set();
    for (const k of ['record_high', 'record_warm_night', 'record_low', 'record_cold_day']) for (const i of daily.records[k] ?? []) s.add(i * 4 + ['record_high', 'record_warm_night', 'record_low', 'record_cold_day'].indexOf(k));
    return s;
  });
  let days = $derived.by(() => {
    const out = [];
    for (let d = 0; d < nDays; d++) {
      const i = start + d;
      const dt = idxToDate(daily.start, i);
      const slot = doy366(dt) - 1;
      out.push({
        d,
        i,
        dt,
        tmax: i >= 0 && i < daily.n ? daily.tmax[i] : null,
        tmin: i >= 0 && i < daily.n ? daily.tmin[i] : null,
        p10x: daily.doy.tmax_p10[slot],
        p90x: daily.doy.tmax_p90[slot],
        p10n: daily.doy.tmin_p10[slot],
        p90n: daily.doy.tmin_p90[slot],
        recHigh: recIdx.has(i * 4),
        recWarm: recIdx.has(i * 4 + 1),
        recLow: recIdx.has(i * 4 + 2),
        recCold: recIdx.has(i * 4 + 3)
      });
    }
    return out;
  });
  const conv = (t) => (t == null ? null : units.f ? tenthsToF(t) : tenthsToC(t));
  const convC = (c) => (c == null ? null : units.f ? c * 1.8 + 32 : c);

  let allVals = $derived(days.flatMap((r) => [conv(r.tmax), conv(r.tmin), convC(r.p10n), convC(r.p90x)]).filter((v) => v != null));
  let lo = $derived(Math.floor(Math.min(...allVals) / 10) * 10 - (units.f ? 5 : 2));
  let hi = $derived(Math.ceil(Math.max(...allVals) / 10) * 10 + (units.f ? 5 : 2));
  let x = $derived(linear([0, nDays - 1], [M.left, W - M.right]));
  let y = $derived(linear([lo, hi], [H - M.bottom, M.top]));
  let yTicks = $derived(ticks(lo, hi, 6));

  function path(key, convf) {
    let s = '';
    let pen = false;
    for (const r of days) {
      const v = convf(r[key]);
      if (v == null) {
        pen = false;
        continue;
      }
      s += (pen ? 'L' : 'M') + x(r.d).toFixed(1) + ' ' + y(v).toFixed(1);
      pen = true;
    }
    return s;
  }
  function band(k10, k90) {
    const up = [], down = [];
    for (const r of days) {
      if (r[k10] == null || r[k90] == null) continue;
      up.push(x(r.d).toFixed(1) + ' ' + y(convC(r[k90])).toFixed(1));
      down.push(x(r.d).toFixed(1) + ' ' + y(convC(r[k10])).toFixed(1));
    }
    if (!up.length) return '';
    return 'M' + up.join('L') + 'L' + down.reverse().join('L') + 'Z';
  }
  let monthStarts = $derived(
    MONTHS.map((m, k) => ({ m, d: Math.round((Date.UTC(year, k, 1) - Date.UTC(year, 0, 1)) / 86400000) }))
  );
  let thrY = $derived(threshold == null ? null : y(units.f ? threshold : fToC(threshold)));

  let hover = $state(null);
  function at(e) {
    const r = e.currentTarget.getBoundingClientRect();
    const px = ((e.clientX - r.left) / r.width) * W;
    hover = Math.max(0, Math.min(nDays - 1, Math.round(x.invert(px))));
  }
  let tipRow = $derived(hover == null ? null : days[hover]);
  let tipObs = $derived(tipRow ? obsAt(daily.obs, tipRow.i) : '');
</script>

<div class="chart">
  <svg viewBox="0 0 {W} {H}" role="img" aria-label="Daily highs and lows for {year}" onpointermove={at} onpointerleave={() => (hover = null)}>
    {#each yTicks as t (t)}
      <line x1={M.left} x2={W - M.right} y1={y(t)} y2={y(t)} stroke={GRID} />
      <text x={M.left - 6} y={y(t) + 4} text-anchor="end" font-size="11" fill={MUTED}>{t}°</text>
    {/each}
    {#each monthStarts as ms (ms.m)}
      <line x1={x(ms.d)} x2={x(ms.d)} y1={M.top} y2={H - M.bottom} stroke={GRID} />
      <text x={x(ms.d) + 4} y={H - 10} font-size="11" fill={MUTED}>{ms.m}</text>
    {/each}
    <path d={band('p10x', 'p90x')} fill={HEAT} opacity="0.13" />
    <path d={band('p10n', 'p90n')} fill={COOL} opacity="0.13" />
    {#if thrY != null && thrY > M.top && thrY < H - M.bottom}
      <line x1={M.left} x2={W - M.right} y1={thrY} y2={thrY} stroke={INK} stroke-width="1" opacity="0.6" />
      <text x={W - M.right} y={thrY - 4} text-anchor="end" font-size="10.5" fill={INK}>{threshold}°F threshold</text>
    {/if}
    <path d={path('tmax', conv)} fill="none" stroke={HEAT} stroke-width="2" stroke-linejoin="round" stroke-linecap="round" />
    <path d={path('tmin', conv)} fill="none" stroke={COOL} stroke-width="2" stroke-linejoin="round" stroke-linecap="round" />
    {#each days as r (r.d)}
      {#if r.recHigh && r.tmax != null}
        <circle cx={x(r.d)} cy={y(conv(r.tmax))} r="4.5" fill={HEAT_DARK} stroke={SURFACE} stroke-width="2" />
      {/if}
      {#if r.recWarm && r.tmin != null}
        <circle cx={x(r.d)} cy={y(conv(r.tmin))} r="4.5" fill={HEAT_DARK} stroke={SURFACE} stroke-width="2" />
      {/if}
      {#if r.recLow && r.tmin != null}
        <circle cx={x(r.d)} cy={y(conv(r.tmin))} r="4.5" fill={COOL_DARK} stroke={SURFACE} stroke-width="2" />
      {/if}
      {#if r.recCold && r.tmax != null}
        <circle cx={x(r.d)} cy={y(conv(r.tmax))} r="4.5" fill={COOL_DARK} stroke={SURFACE} stroke-width="2" />
      {/if}
    {/each}
    {#if hover != null}
      <line x1={x(hover)} x2={x(hover)} y1={M.top} y2={H - M.bottom} stroke={INK} opacity="0.5" />
      {#if tipRow?.tmax != null}<circle cx={x(hover)} cy={y(conv(tipRow.tmax))} r="4" fill={HEAT} stroke={SURFACE} stroke-width="2" />{/if}
      {#if tipRow?.tmin != null}<circle cx={x(hover)} cy={y(conv(tipRow.tmin))} r="4" fill={COOL} stroke={SURFACE} stroke-width="2" />{/if}
    {/if}
  </svg>
  <div class="legend">
    <span class="key"><i style:background={HEAT}></i> daily high</span>
    <span class="key"><i style:background={COOL}></i> daily low</span>
    <span class="key"><i class="band" style:background={HEAT} ></i> 1951–1980 typical range (10th–90th pct.)</span>
    <span class="key"><i class="dot" style:background={HEAT_DARK}></i> record high / warm night</span>
    <span class="key"><i class="dot" style:background={COOL_DARK}></i> record low / cold day</span>
  </div>
  <div class="tip">
    {#if tipRow}
      <b>{fmtDate(tipRow.dt)}</b> · high <b>{fmtTenths(tipRow.tmax, units.f)}</b> · low <b>{fmtTenths(tipRow.tmin, units.f)}</b>
      {#if tipRow.tmax == null && tipRow.tmin == null}(not observed){/if}
      {#if tipRow.recHigh}· <b>record high</b> for this date{/if}{#if tipRow.recWarm}· <b>record warm night</b>{/if}{#if tipRow.recLow}· <b>record low</b>{/if}{#if tipRow.recCold}· <b>record cold day</b>{/if}
      · observed at {fmtObs(tipObs)}{#if obsCaveat && tipObs && tipObs < '1200'} <span class="muted">(a morning reading: this high mostly happened the previous afternoon)</span>{/if}
    {:else}
      Hover or tap a day.
    {/if}
  </div>
</div>

<style>
  .chart svg {
    width: 100%;
    height: auto;
    display: block;
    cursor: crosshair;
  }
  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem 1rem;
    font-size: 0.82rem;
    color: #52514e;
    margin: 0.3rem 0;
  }
  .key i {
    display: inline-block;
    width: 16px;
    height: 3px;
    vertical-align: middle;
    margin-right: 0.3rem;
    border-radius: 2px;
  }
  .key i.band {
    height: 10px;
    opacity: 0.2;
  }
  .key i.dot {
    width: 9px;
    height: 9px;
    border-radius: 50%;
  }
</style>
