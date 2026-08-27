<script>
  /**
   * One line per year, day-of-year × temperature, older years lighter; behind them the
   * 1951–1980 envelope for each date (10–90th band, 25–75th band, median). Canvas.
   */
  import { units } from '$lib/units.svelte.js';
  import { MONTHS } from '$lib/dates.js';
  import { DOY_MONTH_STARTS, isRealDay } from '$lib/ranks.js';
  import { HEAT_DARK, COOL_DARK, MUTED, INK } from '$lib/palette.js';

  let { daily, element = 'tmin', from = 1951, mode = 'all', smooth = 7, height = 300 } = $props();
  const W = 760, M = { top: 14, right: 12, bottom: 24, left: 40 };
  let canvas = $state(null);
  let hover = $state(null);
  const conv = (c) => (units.f ? c * 1.8 + 32 : c);
  const startDate = $derived(new Date(daily.start + 'T00:00:00Z'));
  const arr = $derived(daily[element]);

  // per-year DOY rows (366 slots, tenths °C or null), smoothed
  let years = $derived.by(() => {
    const out = new Map();
    const n = daily.n;
    for (let i = 0; i < n; i++) {
      const v = arr[i];
      if (v == null) continue;
      const dt = new Date(startDate.getTime() + i * 86400000);
      const y = dt.getUTCFullYear();
      if (y < from) continue;
      const m = dt.getUTCMonth(), d = dt.getUTCDate();
      const doy = DOY_MONTH_STARTS[m] + d - 1;
      if (!out.has(y)) out.set(y, new Array(366).fill(null));
      out.get(y)[doy] = v / 10;
    }
    const half = Math.floor(smooth / 2);
    const res = [];
    for (const [y, row] of [...out.entries()].sort((a, b) => a[0] - b[0])) {
      const sm = new Array(366).fill(null);
      for (let d = 0; d < 366; d++) {
        let s = 0, k = 0;
        for (let j = -half; j <= half; j++) {
          const v = row[(d + j + 366) % 366];
          if (v != null) { s += v; k++; }
        }
        sm[d] = k >= Math.max(1, smooth - 2) ? s / k : null;
      }
      const valid = row.filter((v) => v != null).length;
      if (valid >= 200) res.push({ y, v: sm });
    }
    return res;
  });
  let shown = $derived(mode === 'all' ? years : years.filter((r, i, a) => r.y % 5 === 0 || i >= a.length - 5));
  let band = $derived({
    p10: daily.doy[`${element}_p10`], p25: daily.doy[`${element}_p25`], p50: daily.doy[`${element}_p50`], p75: daily.doy[`${element}_p75`], p90: daily.doy[`${element}_p90`]
  });
  let ext = $derived.by(() => {
    let lo = Infinity, hi = -Infinity;
    for (const r of shown) for (const v of r.v) if (v != null) { if (v < lo) lo = v; if (v > hi) hi = v; }
    for (const k of ['p10', 'p90']) for (const v of band[k] ?? []) if (v != null) { if (v < lo) lo = v; if (v > hi) hi = v; }
    return [lo - 1, hi + 1];
  });
  const xs = (d) => M.left + ((d + 0.5) / 366) * (W - M.left - M.right);
  const ys = (c) => M.top + ((ext[1] - c) / (ext[1] - ext[0])) * (height - M.top - M.bottom);
  const mix = (a, b, t) => {
    const h = (c) => [parseInt(c.slice(1, 3), 16), parseInt(c.slice(3, 5), 16), parseInt(c.slice(5, 7), 16)];
    const A = h(a), B = h(b);
    return `rgb(${A.map((c, i) => Math.round(c + (B[i] - c) * t)).join(',')})`;
  };
  const dark = $derived(element === 'tmin' ? COOL_DARK : HEAT_DARK);
  const light = '#ece5d9';

  $effect(() => {
    if (!canvas) return;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = W * dpr; canvas.height = height * dpr;
    const ctx = canvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, height);
    // bands
    const fillBand = (lo, hi, color) => {
      if (!lo || !hi) return;
      ctx.beginPath();
      for (let d = 0; d < 366; d++) if (hi[d] != null) ctx.lineTo(xs(d), ys(hi[d]));
      for (let d = 365; d >= 0; d--) if (lo[d] != null) ctx.lineTo(xs(d), ys(lo[d]));
      ctx.closePath(); ctx.fillStyle = color; ctx.fill();
    };
    fillBand(band.p10, band.p90, 'rgba(120,110,95,0.16)');
    fillBand(band.p25, band.p75, 'rgba(120,110,95,0.20)');
    // grid
    ctx.strokeStyle = '#e8e1d5'; ctx.lineWidth = 1;
    for (let i = 0; i < 12; i++) { const x = xs(DOY_MONTH_STARTS[i]) - 0.5; ctx.beginPath(); ctx.moveTo(x, M.top); ctx.lineTo(x, height - M.bottom); ctx.stroke(); }
    // years
    const n = shown.length, y0 = shown[0]?.y ?? from, y1 = shown[n - 1]?.y ?? from;
    for (const r of shown) {
      const t = y1 === y0 ? 1 : (r.y - y0) / (y1 - y0);
      const isH = hover && hover.year === r.y;
      ctx.strokeStyle = isH ? INK : mix(light, dark, Math.pow(t, 1.6));
      ctx.lineWidth = isH ? 2.4 : mode === 'all' ? 0.9 : 1.5;
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
    if (band.p50) {
      ctx.beginPath(); ctx.strokeStyle = INK; ctx.lineWidth = 1.3; ctx.setLineDash([4, 3]);
      for (let d = 0; d < 366; d++) if (band.p50[d] != null) ctx.lineTo(xs(d), ys(band.p50[d]));
      ctx.stroke(); ctx.setLineDash([]);
    }
    // axes text
    ctx.fillStyle = MUTED; ctx.font = '10px system-ui, sans-serif'; ctx.textAlign = 'center';
    for (let i = 0; i < 12; i++) ctx.fillText(MONTHS[i], xs(DOY_MONTH_STARTS[i] + 15), height - 8);
    ctx.textAlign = 'right';
    const step = units.f ? 10 : 5;
    const lo = Math.ceil(conv(ext[0]) / step) * step, hi = Math.floor(conv(ext[1]) / step) * step;
    for (let t = lo; t <= hi; t += step) {
      const c = units.f ? (t - 32) / 1.8 : t;
      ctx.fillText(`${t}°`, M.left - 6, ys(c) + 3.5);
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
    const pct = band.p50?.[d] != null ? best.v[d] - band.p50[d] : null;
    hover = { year: best.y, doy: d, label: `${MONTHS[m]} ${d - DOY_MONTH_STARTS[m] + 1}`, v: best.v[d], dMed: pct };
  };
</script>

<div class="yc">
  <canvas bind:this={canvas} style="height:{height}px; aspect-ratio: {W} / {height}" onpointermove={onmove} onpointerleave={() => (hover = null)} aria-label="One line per year"></canvas>
  <div class="legend small">
    <span class="grad" style="background: linear-gradient(90deg, {light}, {dark})"></span>
    <span>{shown[0]?.y ?? from} → {shown[shown.length - 1]?.y ?? ''}</span>
    <span class="band">shaded: 1951–80 middle 80% and middle 50% for each date; dashed: its median</span>
  </div>
  <div class="tip small">
    {#if hover}
      <b>{hover.year}</b>, around {hover.label}: {smooth}-day mean {element === 'tmin' ? 'low' : 'high'} {units.f ? (hover.v * 1.8 + 32).toFixed(0) + '°F' : hover.v.toFixed(1) + '°C'}{hover.dMed != null ? `, ${hover.dMed > 0 ? '+' : ''}${(units.f ? hover.dMed * 1.8 : hover.dMed).toFixed(1)}° vs the 1951–80 median for that date` : ''}
    {:else}
      Each line is one year's {smooth}-day mean {element === 'tmin' ? 'daily low' : 'daily high'}, lighter = older. Lines that ride above the shaded 1951–80 band are {element === 'tmin' ? 'nights' : 'days'} warmer than almost any at that date in the baseline.
    {/if}
  </div>
</div>

<style>
  canvas {
    width: 100%;
    display: block;
    cursor: crosshair;
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
