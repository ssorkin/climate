<script>
  /**
   * Every summer at one station: rows = years (newest on top), columns = days
   * Jun 1 – Sep 30, cell = that day's high on a one-hue heat scale. Missing days
   * are blank. Canvas for speed; hover is computed from pointer position.
   */
  import { units } from '$lib/units.svelte.js';
  import { fmtTenths, fWhole } from '$lib/units.js';
  import { dateToIdx, fmtDate, isLeap } from '$lib/dates.js';
  import { HEAT_RAMP } from '$lib/palette.js';

  let { daily, summary, since = null, threshold = 95 } = $props();

  const NDAYS = 122; // Jun 1 .. Sep 30
  const CW = 6;
  let canvas;
  let years = $derived.by(() => {
    const y0 = since ?? summary.first_year;
    const ys = [];
    for (let y = summary.last_year; y >= y0; y--) ys.push(y);
    return ys;
  });
  let rowH = $derived(years.length > 80 ? 5 : 7);
  let W = $derived(NDAYS * CW);
  let H = $derived(years.length * rowH);

  // Color domain: fixed in °F so summers compare across stations too.
  const LO = 60, HI = 110;
  function colorFor(t) {
    if (t == null) return null;
    const f = fWhole(t);
    const k = Math.min(HEAT_RAMP.length - 1, Math.max(0, Math.floor(((f - LO) / (HI - LO)) * HEAT_RAMP.length)));
    return HEAT_RAMP[k];
  }
  function cell(y, d) {
    const i = dateToIdx(daily.start, new Date(Date.UTC(y, 5, 1))) + d;
    return i >= 0 && i < daily.n ? daily.tmax[i] : null;
  }
  $effect(() => {
    if (!canvas) return;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = W * dpr;
    canvas.height = H * dpr;
    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);
    ctx.fillStyle = '#f3efe7';
    ctx.fillRect(0, 0, W, H);
    years.forEach((y, r) => {
      for (let d = 0; d < NDAYS; d++) {
        const c = colorFor(cell(y, d));
        if (!c) continue;
        ctx.fillStyle = c;
        ctx.fillRect(d * CW, r * rowH, CW - 0.5, rowH - 0.5);
      }
    });
  });
  let hover = $state(null);
  function at(e) {
    const r = e.currentTarget.getBoundingClientRect();
    const d = Math.floor(((e.clientX - r.left) / r.width) * NDAYS);
    const row = Math.floor(((e.clientY - r.top) / r.height) * years.length);
    if (d < 0 || d >= NDAYS || row < 0 || row >= years.length) return (hover = null);
    const y = years[row];
    const dt = new Date(Date.UTC(y, 5, 1) + d * 86400000);
    hover = { y, dt, t: cell(y, d) };
  }
  const months = [['Jun', 0], ['Jul', 30], ['Aug', 61], ['Sep', 92]];
  let decadeRows = $derived(years.map((y, r) => ({ y, r })).filter((o) => o.y % 10 === 0));
</script>

<div class="wrap">
  <div class="axis-x" style:width="{W}px">
    {#each months as [m, d] (m)}<span style:left="{d * CW}px">{m}</span>{/each}
  </div>
  <div class="body">
    <div class="axis-y" style:height="{H}px">
      {#each decadeRows as o (o.y)}<span style:top="{o.r * rowH}px">{o.y}</span>{/each}
    </div>
    <canvas bind:this={canvas} style:width="{W}px" style:height="{H}px" onpointermove={at} onpointerleave={() => (hover = null)}></canvas>
  </div>
  <div class="legend">
    <span class="tip">{#if hover}<b>{fmtDate(hover.dt)}</b>: high {fmtTenths(hover.t, units.f)}{#if hover.t != null && fWhole(hover.t) >= threshold} · ≥ {threshold}°F{/if}{:else}Hover a day. Each row is one summer, newest at the top.{/if}</span>
    <span class="scale">{fmtTenths(Math.round((LO - 32) * 50 / 9), units.f)} {#each HEAT_RAMP as c, i (i)}<i style:background={c}></i>{/each} {fmtTenths(Math.round((HI - 32) * 50 / 9), units.f)}+</span>
  </div>
</div>

<style>
  .wrap {
    overflow-x: auto;
  }
  .axis-x {
    position: relative;
    height: 16px;
    margin-left: 40px;
    font-size: 0.72rem;
    color: #898781;
  }
  .axis-x span {
    position: absolute;
    top: 0;
  }
  .body {
    display: flex;
  }
  .axis-y {
    position: relative;
    width: 40px;
    font-size: 0.72rem;
    color: #898781;
    flex: none;
  }
  .axis-y span {
    position: absolute;
    right: 6px;
    line-height: 1;
  }
  canvas {
    display: block;
    cursor: crosshair;
    flex: none;
  }
  .legend {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
    flex-wrap: wrap;
    font-size: 0.85rem;
    color: #52514e;
    margin-top: 0.3rem;
    margin-left: 40px;
  }
  .scale i {
    display: inline-block;
    width: 14px;
    height: 12px;
    vertical-align: middle;
  }
</style>
