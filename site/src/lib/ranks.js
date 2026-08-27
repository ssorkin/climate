// stations/<id>/ranks.bin: uint16 start_year, uint16 n_years, then two planes (tmax, tmin) of
// n_years × 366 uint8 percentile ranks (0–100; 255 = no reading / no such day).
import { dataUrl } from '$lib/data.js';

export const DOY_MONTH_STARTS = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]; // 366-day calendar
const MONTH_LEN = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];

export function doyToMonthDay(doy) {
  let m = 0;
  while (m < 11 && doy >= DOY_MONTH_STARTS[m + 1]) m++;
  return { month: m, day: doy - DOY_MONTH_STARTS[m] + 1 };
}

export function isRealDay(doy, year) {
  if (doy !== 59) return true;
  return (year % 4 === 0 && year % 100 !== 0) || year % 400 === 0;
}

export async function loadRanks(id) {
  const r = await fetch(dataUrl(`/data/stations/${id}/ranks.bin`));
  if (!r.ok) return null;
  const buf = await r.arrayBuffer();
  const head = new DataView(buf);
  const y0 = head.getUint16(0, true);
  const ny = head.getUint16(2, true);
  const n = ny * 366;
  return { y0, ny, tmax: new Uint8Array(buf, 4, n), tmin: new Uint8Array(buf, 4 + n, n) };
}

/** Mean rank of a year (row) for one element, or null if fewer than `min` days. */
export function yearMean(ranks, el, year, min = 300) {
  const row = year - ranks.y0;
  if (row < 0 || row >= ranks.ny) return null;
  const a = ranks[el];
  let s = 0, k = 0;
  for (let d = 0; d < 366; d++) {
    const v = a[row * 366 + d];
    if (v !== 255) { s += v; k++; }
  }
  return k >= min ? s / k : null;
}

/** Continuous 0–100 → color LUT over a diverging list (index 0 = coolest). */
export function rankLut(colors) {
  const hex = (c) => [parseInt(c.slice(1, 3), 16), parseInt(c.slice(3, 5), 16), parseInt(c.slice(5, 7), 16)];
  const rgb = colors.map(hex);
  const lut = [];
  for (let i = 0; i <= 100; i++) {
    const t = (i / 100) * (rgb.length - 1);
    const k = Math.min(rgb.length - 2, Math.floor(t)), f = t - k;
    lut.push(rgb[k].map((c, j) => Math.round(c + (rgb[k + 1][j] - c) * f)));
  }
  return lut;
}
