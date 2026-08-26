// Live threshold counts from daily.json, using the same completeness flags the
// pipeline exported (summary.annual / summary.monthly). Mirrors metrics.py.
import { fWhole } from './units.js';
import { dateToIdx, daysInMonth, parseISO } from './dates.js';

export const FAMILIES = {
  hot: { key: 'hot_days', elem: 'tmax', op: '>=', label: 'Hot days', noun: 'days', unit: 'high of' },
  warm: { key: 'warm_nights', elem: 'tmin', op: '>=', label: 'Warm nights', noun: 'nights', unit: 'low of' },
  coldday: { key: 'cold_days', elem: 'tmax', op: '<=', label: 'Cold days', noun: 'days', unit: 'high of' },
  frost: { key: 'cold_nights', elem: 'tmin', op: '<=', label: 'Frost & cold nights', noun: 'nights', unit: 'low of' }
};

export function passes(family, tenths, thr) {
  if (tenths == null) return false;
  const f = fWhole(tenths);
  return FAMILIES[family].op === '>=' ? f >= thr : f <= thr;
}

// Count qualifying days between two dates (inclusive) in daily.json arrays.
export function countRange(daily, family, thr, from, to) {
  const arr = daily[FAMILIES[family].elem];
  const a = Math.max(0, dateToIdx(daily.start, from));
  const b = Math.min(daily.n - 1, dateToIdx(daily.start, to));
  let n = 0;
  for (let i = a; i <= b; i++) if (passes(family, arr[i], thr)) n++;
  return n;
}

// Per-year counts, null where the exported completeness flag says the year is incomplete.
export function annualCounts(daily, summary, family, thr) {
  const fam = FAMILIES[family];
  const flags = fam.elem === 'tmax' ? summary.annual.complete_tmax : summary.annual.complete_tmin;
  return summary.annual.year.map((y, k) => {
    if (!flags[k]) return null;
    return countRange(daily, family, thr, new Date(Date.UTC(y, 0, 1)), new Date(Date.UTC(y, 11, 31)));
  });
}

// Per-(year, month) counts aligned with summary.monthly rows.
export function monthlyCounts(daily, summary, family, thr) {
  const fam = FAMILIES[family];
  const m = summary.monthly;
  const flags = fam.elem === 'tmax' ? m.complete_tmax : m.complete_tmin;
  return m.year.map((y, k) => {
    if (!flags[k]) return null;
    const mo = m.month[k];
    return countRange(daily, family, thr, new Date(Date.UTC(y, mo - 1, 1)), new Date(Date.UTC(y, mo - 1, daysInMonth(y, mo))));
  });
}

// Cold-season (Jul->Jun, labeled by January year) counts aligned with summary.cold_season rows.
export function seasonCounts(daily, summary, family, thr) {
  const cs = summary.cold_season;
  const flags = FAMILIES[family].elem === 'tmax' ? cs.complete_tmax : cs.complete_tmin;
  return cs.year.map((y, k) => {
    if (!flags[k]) return null;
    return countRange(daily, family, thr, new Date(Date.UTC(y - 1, 6, 1)), new Date(Date.UTC(y, 5, 30)));
  });
}

export const isStandard = (summary, family, thr) =>
  (summary.thresholds_f[FAMILIES[family].key] ?? []).includes(thr);

// Standard-threshold series straight from the export (the tested numbers).
export function exportedAnnual(summary, family, thr) {
  const key = FAMILIES[family].key;
  if (family === 'frost') return summary.cold_season[key]?.[String(thr)] ?? null;
  return summary.annual[key]?.[String(thr)] ?? null;
}
export function exportedMonthly(summary, family, thr) {
  return summary.monthly[FAMILIES[family].key]?.[String(thr)] ?? null;
}

export const yearsOf = (summary, family) =>
  family === 'frost' ? summary.cold_season.year : summary.annual.year;
export const partialOf = (summary, family) =>
  family === 'frost' ? summary.cold_season.partial : summary.annual.partial;

export { parseISO };
