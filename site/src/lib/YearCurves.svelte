<script>
  /**
   * One line per year, day-of-year × temperature, oldest years palest and the latest darkest
   * (the BBC "every year as a line" idiom); behind them, where the station has a baseline, the
   * 1951–1980 envelope for each date (10–90th and 25–75th bands, dashed median). Canvas.
   */
  import { units } from '$lib/units.svelte.js';
  import { MONTHS } from '$lib/dates.js';
  import { DOY_MONTH_STARTS, isRealDay } from '$lib/ranks.js';
  import { yearRows, bandRows } from '$lib/curves.js';
  import { HEAT_DARK, COOL_DARK, MUTED, INK } from '$lib/palette.js';

  let { curves, element = 'tmin', from = 0, mode = 'all', smooth = 7, height = 300, compact = false, label = '', sub = '' } = $props();
  const W = $derived(compact ? 360 : 760);
  const M = $derived(compact ? { top: 6, right: 6, bottom: 16, left: 26 } : { top: 14, right: 12, bottom: 24, left: 40 });
  let canvas = $state(null);
  let hover = $state(null);
  const conv = (c) => (units.f ? c * 1.8 + 32 : c);

  let years = $derived(yearRows(curves, element, { from, smooth }));
  let shown = $derived(mode === 'all' ? years : years.filter((r, i, a) => r.y % 5 === 0 || i >= a.length - 5));
  let band = $derived(bandRows(curves, element));
  let ext = $derived.by(() => {
    let lo = Infinity, hi = -Infinity;
    for (const r of shown) for (const v of r.v) if (v != null) { if (v < lo) lo = v; if (v > hi) hi = v; }
    if (band) for (const k of ['p10', 'p90']) for (const v of band[k]) if (v != null) { if (v < lo) lo = v; if (v > hi) hi = v; }
    return [lo - 1, hi + 1];
  });
  const xs = (d) => M.left + ((d + 0.5) / 366) * (W - M.left - M.right);
  const ys = (c) => M.top + ((ext[1] - c) / (ext[1] - ext[0])) * (height - M.top - M.bottom);
  const hex = (c) => [parseInt(c.slice(1, 3), 16), parseInt(c.slice(3, 5), 16), parseInt(c.slice(5, 7), 16)];
  const mix = (a, b, t) => { const A = hex(a), B = hex(b); return `rgb(${A.map((c, i) => Math.round(c + (B[i] - c) * t)).join(',')})`; };
  const dark = $derived(element === 'tmin' ? COOL_DARK : HEAT_DARK);
  const light = '#e6dfd3';
  let latest = $derived(shown[shown.length - 1]?.y);

  $effect(() => {
    if (!canvas) return;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = W * dpr; canvas.height = height * dpr;
    const ctx = canvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, height);
    const fillBand = (lo, hi, color) => {
      ctx.beginPath();
      for (let d = 0; d < 366; d++) if (hi[d] != null) ctx.lineTo(xs(d), ys(hi[d]));
      for (let d = 365; d >= 0; d--) if (lo[d] != null) ctx.lineTo(xs(d), ys(lo[d]));
      ctx.closePath(); ctx.fillStyle = color; ctx.fill();
    };
    if (band) { fillBand(band.p10, band.p90, 'rgba(120,110,95,0.16)'); fillBand(band.p25, band.p75, 'rgba(120,110,95,0.20)'); }
    ctx.strokeStyle = '#e8e1d5'; ctx.lineWidth = 1;
    for (let i = 0; i < 12; i++) { const x = xs(DOY_MONTH_STARTS[i]) - 0.5; ctx.beginPath(); ctx.moveTo(x, M.top); ctx.lineTo(x, height - M.bottom); ctx.stroke(); }
    const n = shown.length, y0 = shown[0]?.y ?? from, y1 = shown[n - 1]?.y ?? from;
    for (const r of shown) {
      const t = y1 === y0 ? 1 : (r.y - y0) / (y1 - y0);
      const isH = hover && hover.year === r.y;
      const isLatest = r.y === latest;
      ctx.strokeStyle = isH ? INK : mix(light, dark, Math.pow(t, 1.8));
      ctx.lineWidth = isH ? 2.4 : isLatest ? (compact ? 1.6 : 2.2) : mode === 'all' ? (compact ? 0.7 : 0.9) : 1.5;
      ctx.beginPath();
      let pen = false;
      for (let d = 0; d < 366; d++) {
        const v = r.v[d];
        if (v == null || !isRealDay(d, r.y)) { pen = false; continue; }
        if (pen) ctx.lineTo(xs(d), ys(v)); else ctx.moveTo(xs(d), ys(v));
        pen = true;
      }
      ctx.stroke();
    }
    if (band) {
      ctx.beginPath(); ctx.strokeStyle = INK; ctx.lineWidth = compact ? 0.9 : 1.3; ctx.setLineDash([4, 3]);
      for (let d = 0; d < 366; d++) if (band.p50[d] != null) ctx.lineTo(xs(d), ys(band.p50[d]));
      ctx.stroke(); ctx.setLineDash([]);
    }
    ctx.fillStyle = MUTED; ctx.font = `${compact ? 9 : 10}px system-ui, sans-serif`; ctx.textAlign = 'center';
    for (let i = 0; i < 12; i++) ctx.fillText(compact ? MONTHS[i][0] : MONTHS[i], xs(DOY_MONTH_STARTS[i] + 15), height - (compact ? 5 : 8));
    ctx.textAlign = 'right';
    const step = compact ? (units.f ? 20 : 10) : units.f ? 10 : 5;
    const lo = Math.ceil(conv(ext[0]) / step) * step, hi = Math.floor(conv(ext[1]) / step) * step;
    for (let t = lo; t <= hi; t += step) {
      const c = units.f ? (t - 32) / 1.8 : t;
      ctx.fillText(`${t}°`, M.left - 4, ys(c) + 3.5);
    }
  });
  const onmove = (e) => {
    const b = e.currentTarget.getBoundingClientRect();
    const px = ((e.clientX - b.left) / b.width) * W, py = ((e.clientY - b.top) / b.height) * height;
    const d = Math.max(0, Math.min(365, Math.floor(((px - M.left) / (W - M.left - M.right)) * 366)));
    const c = ext[1] - ((py - M.top) / (height - M.top - M.bottom)) * (ext[1] - ext[0]);
    let best = null, bd = Infinity;
    for (const r of shown) { const v = r.v[d]; if (v == null) continue; const dd = Math.abs(v - c); if (dd < bd) { bd = dd; best = r; } }
    if (!best || bd > (ext[1] - ext[0]) * 0.05) { hover = null; return; }
    const m = DOY_MONTH_STARTS.findLastIndex((s) => s <= d);
    const dMed = band?.p50?.[d] != null ? best.v[d] - band.p50[d] : null;
    hover = { year: best.y, label: `${MONTHS[m]} ${d - DOY_MONTH_STARTS[m] + 1}`, v: best.v[d], dMed };
  };
  const fmt = (c) => (units.f ? (c * 1.8 + 32).toFixed(0) + '°F' : c.toFixed(1) + '°C');
</script>

<div class="yc" class:compact>
  {#if label}<div class="head"><span class="lbl">{label}</span>{#if sub}<span class="sub small muted">{sub}</span>{/if}</div>{/if}
  <canvas bind:this={canvas} style="aspect-ratio: {W} / {height}" onpointermove={onmove} onpointerleave={() => (hover = null)} aria-label={label || 'One line per year'}></canvas>
  {#if compact}
    <div class="tip small">
      {#if hover}<b>{hover.year}</b>, {hover.label}: {fmt(hover.v)}{hover.dMed != null ? ` (${hover.dMed > 0 ? '+' : ''}${(units.f ? hover.dMed * 1.8 : hover.dMed).toFixed(1)}° vs baseline)` : ''}{:else}{shown[0]?.y ?? ''} → <b>{latest ?? ''}</b>{/if}
    </div>
  {:else}
    <div class="legend small">
      <span class="grad" style="background: linear-gradient(90deg, {light}, {dark})"></span>
      <span>{shown[0]?.y ?? from} → {latest ?? ''} (thick line)</span>
      {#if band}<span class="band">shaded: the baseline's middle 80% and middle 50% for each date; dashed: its median</span>{/if}
    </div>
    <div class="tip small">
      {#if hover}
        <b>{hover.year}</b>, around {hover.label}: {smooth}-day mean {element === 'tmin' ? 'low' : 'high'} {fmt(hover.v)}{hover.dMed != null ? `, ${hover.dMed > 0 ? '+' : ''}${(units.f ? hover.dMed * 1.8 : hover.dMed).toFixed(1)}° vs the baseline median for that date` : ''}
      {:else}
        Each line is one year's {smooth}-day mean {element === 'tmin' ? 'daily low' : 'daily high'}, palest = oldest, darkest = most recent.{#if band} Lines riding above the shaded band are {element === 'tmin' ? 'nights' : 'days'} warmer than almost any baseline year at that date.{/if}
      {/if}
    </div>
  {/if}
</div>

<style>
  canvas {
    width: 100%;
    display: block;
    cursor: crosshair;
  }
  .head {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 0.5rem;
    flex-wrap: wrap;
    margin-bottom: 0.15rem;
  }
  .head .lbl {
    font-size: 0.88rem;
    font-weight: 650;
    color: #1f1b16;
  }
  .compact .head .lbl {
    font-size: 0.82rem;
  }
  .compact .tip {
    min-height: 1.2em;
    color: #898781;
  }
  .legend {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    color: #52514e;
    margin-top: 0.3rem;
    flex-wrap: wrap;
  }
  .grad {
    display: inline-block;
    width: 80px;
    height: 8px;
    border-radius: 4px;
  }
  .band {
    color: #898781;
  }
</style>
