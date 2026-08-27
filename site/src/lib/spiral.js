// NASA-style climate spiral for one station: angle = day of year (January at the top,
// clockwise), radius = temperature, one ring per year, palest = oldest, darkest = latest.
import { yearRows, bandRows } from '$lib/curves.js';
import { HEAT_DARK, COOL_DARK } from '$lib/palette.js';

const hex = (c) => [parseInt(c.slice(1, 3), 16), parseInt(c.slice(3, 5), 16), parseInt(c.slice(5, 7), 16)];
const mix = (a, b, t) => { const A = hex(a), B = hex(b); return `rgb(${A.map((c, i) => Math.round(c + (B[i] - c) * t)).join(',')})`; };
const LIGHT = '#ddd5c8';

/** Shared temperature range (°C) for a set of curves so spirals are comparable. */
export function sharedRange(curvesList, el, smooth = 15) {
  let lo = Infinity, hi = -Infinity;
  for (const c of curvesList) {
    for (const r of yearRows(c, el, { smooth })) for (const v of r.v) if (v != null) { if (v < lo) lo = v; if (v > hi) hi = v; }
  }
  return [lo, hi];
}

export function drawSpiral(canvas, curves, el, { size = 96, from = 0, smooth = 15, tRange = null, upTo = null, highlight = null } = {}) {
  const dpr = window.devicePixelRatio || 1;
  canvas.width = size * dpr; canvas.height = size * dpr;
  canvas.style.width = `${size}px`; canvas.style.height = `${size}px`;
  const ctx = canvas.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, size, size);
  const els = el === 'both' ? ['tmax', 'tmin'] : [el];
  const layers = els.map((e) => ({ e, all: yearRows(curves, e, { from, smooth }), band: bandRows(curves, e) }));
  if (!layers[0].all.length) return null;
  let [lo, hi] = tRange ?? [Infinity, -Infinity];
  if (!tRange) {
    for (const L of layers) {
      for (const r of L.all) for (const v of r.v) if (v != null) { if (v < lo) lo = v; if (v > hi) hi = v; }
      if (L.band) for (const k of ['p10', 'p90']) for (const v of L.band[k]) if (v != null) { if (v < lo) lo = v; if (v > hi) hi = v; }
    }
  }
  const cx = size / 2, cy = size / 2, r0 = size * 0.1, R = size / 2 - 3;
  const rad = (t) => r0 + (Math.max(lo, Math.min(hi, t)) - lo) / (hi - lo) * (R - r0);
  const ang = (d) => -Math.PI / 2 + (2 * Math.PI * (d + 0.5)) / 366;
  // the baseline's middle 80% and middle 50% for each date, as shaded rings
  const ring = (loB, hiB, color) => {
    ctx.beginPath();
    for (let d = 0; d < 366; d++) { const v = hiB[d]; if (v == null) continue; ctx.lineTo(cx + rad(v) * Math.cos(ang(d)), cy + rad(v) * Math.sin(ang(d))); }
    ctx.closePath();
    for (let d = 365; d >= 0; d--) { const v = loB[d]; if (v == null) continue; ctx.lineTo(cx + rad(v) * Math.cos(ang(d)), cy + rad(v) * Math.sin(ang(d))); }
    ctx.closePath();
    ctx.fillStyle = color; ctx.fill('evenodd');
  };
  for (const L of layers) if (L.band) { ring(L.band.p10, L.band.p90, 'rgba(120,110,95,0.16)'); ring(L.band.p25, L.band.p75, 'rgba(120,110,95,0.20)'); }
  // faint quarter ticks
  ctx.strokeStyle = 'rgba(0,0,0,0.10)'; ctx.lineWidth = 1;
  for (let q = 0; q < 4; q++) { const a = -Math.PI / 2 + (q * Math.PI) / 2; ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx + R * Math.cos(a), cy + R * Math.sin(a)); ctx.stroke(); }
  let meta = null;
  for (const L of layers) {
    const dark = L.e === 'tmin' ? COOL_DARK : HEAT_DARK;
    const all = L.all;
    const rows = upTo == null ? all : all.filter((r) => r.y <= upTo);
    if (!rows.length) continue;
    const y0 = all[0].y, y1 = all[all.length - 1].y; // shading keyed to the full record, not the scrubbed part
    const top = rows[rows.length - 1].y;
    const hl = highlight ?? top;
    meta ??= { y0, y1, top, lo, hi };
    const ordered = [...rows.filter((r) => r.y !== hl), ...rows.filter((r) => r.y === hl)];
    for (const r of ordered) {
      const t = y1 === y0 ? 1 : (r.y - y0) / (y1 - y0);
      const isH = r.y === hl;
      const trace = () => {
        ctx.beginPath();
        let pen = false;
        for (let d = 0; d < 366; d++) {
          const v = r.v[d];
          if (v == null) { pen = false; continue; }
          const x = cx + rad(v) * Math.cos(ang(d)), y = cy + rad(v) * Math.sin(ang(d));
          if (pen) ctx.lineTo(x, y); else ctx.moveTo(x, y);
          pen = true;
        }
        ctx.stroke();
      };
      if (isH) {
        ctx.globalAlpha = 1; ctx.strokeStyle = '#fffdf9'; ctx.lineWidth = 4; trace();
        ctx.strokeStyle = el === 'both' ? dark : '#1f1b16'; ctx.lineWidth = 2; trace();
      } else {
        ctx.strokeStyle = mix(LIGHT, dark, Math.pow(t, 1.8));
        ctx.lineWidth = 0.8; ctx.globalAlpha = 0.75; trace();
      }
    }
    ctx.globalAlpha = 1;
    if (L.band) {
      ctx.strokeStyle = 'rgba(31,27,22,0.9)'; ctx.lineWidth = 1; ctx.setLineDash([3, 2]);
      ctx.beginPath();
      let pen = false;
      for (let d = 0; d < 366; d++) {
        const v = L.band.p50[d];
        if (v == null) { pen = false; continue; }
        const x = cx + rad(v) * Math.cos(ang(d)), y = cy + rad(v) * Math.sin(ang(d));
        if (pen) ctx.lineTo(x, y); else ctx.moveTo(x, y);
        pen = true;
      }
      ctx.closePath(); ctx.stroke(); ctx.setLineDash([]);
    }
  }
  return meta;
}
