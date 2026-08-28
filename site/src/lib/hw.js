// Shared helpers for the heat-wave story components. Values arrive in whole °F (as
// observed); these convert for display when the °C toggle is on.
import { fToC } from '$lib/units.js';

export const tempF = (f, useF, digits = 0) => (f == null ? '—' : (useF ? f : fToC(f)).toFixed(digits) + '°');
export const deltaF = (d, useF, digits = 1) => {
  if (d == null) return '—';
  const v = useF ? d : d / 1.8;
  return (v >= 0 ? '+' : '−') + Math.abs(v).toFixed(digits) + '°';
};
export const unitName = (useF) => (useF ? '°F' : '°C');
// °F axis value -> display unit (for tick labels / domains).
export const axisT = (f, useF) => (useF ? f : fToC(f));

export const median = (arr) => {
  const a = arr.filter((v) => v != null && !Number.isNaN(v)).sort((x, y) => x - y);
  if (!a.length) return null;
  const n = a.length;
  return n % 2 ? a[(n - 1) / 2] : (a[n / 2 - 1] + a[n / 2]) / 2;
};

// Stations with both a baseline and a last-30 window (the ones "then vs now" can use).
export const comparable = (stations) => stations.filter((s) => s.windows?.baseline && s.windows?.last30);

// Per-wave objects from the columnar export.
export function waveRows(s) {
  const w = s.waves;
  return w.start.map((start, i) => ({
    start,
    year: Number(start.slice(0, 4)),
    month: Number(start.slice(5, 7)),
    days: w.days[i],
    peak: w.peak_f[i],
    low: w.low_f[i],
    meanLow: w.mean_low_f[i],
    after: w.after_low_f[i],
    relief: w.relief_h[i],
    complete: s.years.includes(Number(start.slice(0, 4)))
  }));
}

export const fmtDate = (iso) => {
  const [y, m, d] = iso.split('-').map(Number);
  return new Date(Date.UTC(y, m - 1, d)).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' });
};
