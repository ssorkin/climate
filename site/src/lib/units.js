// Temperature helpers. NOAA stores tenths of °C; US observers record whole °F.
// fWhole mirrors climate.analysis.metrics.f_whole exactly (integer math):
// floor((t*18 + 3250) / 100) — so 90°F, stored as 322 (89.96°F), counts as 90.
export const fWhole = (t) => Math.floor((t * 18 + 3250) / 100);
export const tenthsToF = (t) => (t / 10) * 1.8 + 32;
export const tenthsToC = (t) => t / 10;
export const cToF = (c) => c * 1.8 + 32;
export const fToC = (f) => (f - 32) / 1.8;
// A °C *difference* (anomaly, trend) in °F.
export const dC = (c) => c * 1.8;

// Format a tenths-°C reading in the chosen unit. Whole °F (as observed); 0.1 °C.
export function fmtTenths(t, f, withUnit = true) {
  if (t == null) return '—';
  const v = f ? fWhole(t) : tenthsToC(t).toFixed(1);
  return withUnit ? `${v}°${f ? 'F' : 'C'}` : String(v);
}

// Format a °C mean/anomaly/slope in the chosen unit.
export function fmtC(c, f, { digits = 1, sign = false, unit = true, delta = false } = {}) {
  if (c == null) return '—';
  const v = f ? (delta ? dC(c) : cToF(c)) : c;
  const s = (sign && v > 0 ? '+' : '') + v.toFixed(digits);
  return unit ? `${s}°${f ? 'F' : 'C'}` : s;
}

// A whole-°F threshold shown in the chosen unit.
export function fmtThresholdF(thr, f) {
  return f ? `${thr}°F` : `${fToC(thr).toFixed(1)}°C`;
}
