export const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
export const MONTHS_LONG = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'
];

const DAY = 86400000;

export function parseISO(s) {
  const [y, m, d] = s.split('-').map(Number);
  return new Date(Date.UTC(y, m - 1, d));
}

// daily.json index <-> date (UTC, day granularity).
export function idxToDate(start, i) {
  return new Date(parseISO(start).getTime() + i * DAY);
}
export function dateToIdx(start, dt) {
  return Math.round((dt.getTime() - parseISO(start).getTime()) / DAY);
}
export function isoOf(dt) {
  return dt.toISOString().slice(0, 10);
}
export function fmtDate(dt, { year = true } = {}) {
  const m = MONTHS[dt.getUTCMonth()];
  return year ? `${m} ${dt.getUTCDate()}, ${dt.getUTCFullYear()}` : `${m} ${dt.getUTCDate()}`;
}
export function fmtISO(s, opts) {
  return s ? fmtDate(parseISO(s), opts) : '—';
}
export const isLeap = (y) => (y % 4 === 0 && y % 100 !== 0) || y % 400 === 0;
export const daysInYear = (y) => (isLeap(y) ? 366 : 365);
export function daysInMonth(y, m) {
  return new Date(Date.UTC(y, m, 0)).getUTCDate();
}
// Day-of-year slot in a leap-year calendar (Feb 29 = 60), matching metrics.doy366.
export function doy366(dt) {
  return Math.round((Date.UTC(2000, dt.getUTCMonth(), dt.getUTCDate()) - Date.UTC(2000, 0, 1)) / DAY) + 1;
}
// Observation time for a daily.json index, from the RLE `obs` list.
export function obsAt(obs, i) {
  let h = '';
  for (const [start, hhmm] of obs) {
    if (i >= start) h = hhmm;
    else break;
  }
  return h;
}
export function fmtObs(hhmm) {
  if (!hhmm) return 'calendar day';
  return `${hhmm.slice(0, 2)}:${hhmm.slice(2)}`;
}
