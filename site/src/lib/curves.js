// stations/<id>/curves.bin — see analysis/export.py::write_curves_bin.
import { dataUrl } from '$lib/data.js';

export const MISSING = -32768;
const QS = ['p10', 'p25', 'p50', 'p75', 'p90'];

export async function loadCurves(id) {
  const r = await fetch(dataUrl(`/data/stations/${id}/curves.bin`));
  if (!r.ok) return null;
  const buf = await r.arrayBuffer();
  const h = new DataView(buf);
  const y0 = h.getUint16(0, true), ny = h.getUint16(2, true), hasBands = h.getUint8(4) === 1;
  const n = ny * 366;
  let off = 6;
  const tmax = new Int16Array(buf.slice(off, off + n * 2)); off += n * 2;
  const tmin = new Int16Array(buf.slice(off, off + n * 2)); off += n * 2;
  const bands = { tmax: null, tmin: null };
  if (hasBands) {
    for (const el of ['tmax', 'tmin']) {
      bands[el] = {};
      for (const q of QS) {
        bands[el][q] = new Int16Array(buf.slice(off, off + 366 * 2)); off += 366 * 2;
      }
    }
  }
  return { y0, ny, tmax, tmin, bands };
}

/** Smoothed (circular, k-day mean) °C rows for each year with ≥ minDays readings. */
export function yearRows(curves, el, { from = 0, smooth = 7, minDays = 200 } = {}) {
  const a = curves[el];
  const half = Math.floor(smooth / 2);
  const out = [];
  for (let r = 0; r < curves.ny; r++) {
    const y = curves.y0 + r;
    if (y < from) continue;
    const base = r * 366;
    let valid = 0;
    for (let d = 0; d < 366; d++) if (a[base + d] !== MISSING) valid++;
    if (valid < minDays) continue;
    const row = new Array(366).fill(null);
    for (let d = 0; d < 366; d++) {
      let s = 0, k = 0;
      for (let j = -half; j <= half; j++) {
        const v = a[base + ((d + j + 366) % 366)];
        if (v !== MISSING) { s += v; k++; }
      }
      row[d] = k >= Math.max(1, smooth - 2) ? s / k / 10 : null;
    }
    out.push({ y, v: row, valid });
  }
  return out;
}

export function bandRows(curves, el) {
  const b = curves.bands[el];
  if (!b) return null;
  const conv = (arr) => Array.from(arr, (v) => (v === MISSING ? null : v / 10));
  return { p10: conv(b.p10), p25: conv(b.p25), p50: conv(b.p50), p75: conv(b.p75), p90: conv(b.p90) };
}
