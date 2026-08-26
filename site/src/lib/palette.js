// Chart chrome (warm neutrals shared with the page) and the three data ramps.
export const INK = '#2b2722';
export const INK2 = '#52514e';
export const MUTED = '#898781';
export const GRID = '#e8e1d5';
export const AXIS = '#c9c2b6';
export const SURFACE = '#fffdf9';
export const PAGE = '#faf7f2';

// Series colors: highs (heat) and lows (cool) — used for lines/bars, never text.
export const HEAT = '#d94f22';
export const HEAT_DARK = '#9a2f0c';
export const COOL = '#2a78d6';
export const COOL_DARK = '#0d366b';
export const NEUTRAL = '#b8b2a7';
export const HIGHLIGHT = '#1f1b16';

// Sequential, one hue, light -> dark (heat). Lightest = near zero, recedes to the surface.
export const HEAT_RAMP = ['#fdebdf', '#fbd1b8', '#f8b28a', '#f28f5c', '#e86b35', '#cc4a1c', '#a33612', '#732508'];
// Sequential blue for cold counts.
export const COOL_RAMP = ['#e4eefb', '#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5', '#256abf', '#184f95', '#0d366b'];
// Diverging for anomalies: blue <- gray -> red.
export const DIVERGING = ['#0d366b', '#256abf', '#6da7ec', '#b7d3f6', '#f0efec', '#f8b28a', '#e86b35', '#cc4a1c', '#732508'];

export function ramp(colors, t) {
  if (t == null || Number.isNaN(t)) return NEUTRAL;
  const x = Math.max(0, Math.min(1, t));
  return colors[Math.min(colors.length - 1, Math.floor(x * colors.length))];
}
// Diverging: v in [-1, 1] -> color; 0 = neutral midpoint.
export function diverging(v) {
  if (v == null || Number.isNaN(v)) return NEUTRAL;
  const x = Math.max(-1, Math.min(1, v));
  const k = Math.round(((x + 1) / 2) * (DIVERGING.length - 1));
  return DIVERGING[k];
}
