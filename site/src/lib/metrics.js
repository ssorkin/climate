// Live threshold counts from daily.json, using the same completeness flags the
// pipeline exported (summary.annual / summary.monthly). Mirrors metrics.py.
import { fWhole } from './units.js';
import { doy366 } from './dates.js';
import { dateToIdx, idxToDate, daysInMonth, parseISO } from './dates.js';

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

// How often each calendar date (±3 days, all years) crosses the threshold at this station:
// the expected contribution of a missing day to the count. Mirrors metrics.doy_pass_rates.
export function doyPassRates(daily, family, thr, window = 3) {
  const arr = daily[FAMILIES[family].elem];
  const pass = new Array(367).fill(0);
  const n = new Array(367).fill(0);
  for (let i = 0; i < daily.n; i++) {
    if (arr[i] == null) continue;
    const k = doy366(idxToDate(daily.start, i));
    n[k]++;
    if (passes(family, arr[i], thr)) pass[k]++;
  }
  const rate = new Array(367).fill(null);
  for (let k = 1; k <= 366; k++) {
    let p = 0, m = 0;
    for (let off = -window; off <= window; off++) {
      const j = ((k - 1 + off + 366) % 366) + 1;
      p += pass[j];
      m += n[j];
    }
    rate[k] = m ? p / m : null;
  }
  return rate;
}

// Expected count contributed by the missing days in [from, to] (null rate -> 1, i.e. unknown).
export function expectedMissed(daily, family, thr, from, to, rates) {
  const arr = daily[FAMILIES[family].elem];
  const a = dateToIdx(daily.start, from);
  const b = dateToIdx(daily.start, to);
  let e = 0;
  for (let i = a; i <= b; i++) {
    if (i >= 0 && i < daily.n && arr[i] != null) continue;
    const r = rates[doy366(idxToDate(daily.start, i))];
    e += r == null ? 1 : r;
  }
  return e;
}

export const EXACT_MAX_EXPECTED = 0.5;

function promote(summary, elem, flags, partial, daysValid, daysTotal, lower, exp) {
  return lower.map((v, k) => {
    if (flags[k]) return v;
    if (partial[k]) return null;
    if (daysValid[k] < Math.ceil(daysTotal[k] * 0.5)) return null;
    return exp[k] < EXACT_MAX_EXPECTED ? v : null;
  });
}

// Per-year counts: `values` are exact counts (complete years, or incomplete years whose
// missing days are expected to add < 0.5 to the count); `lower` is the count over observed
// days for every year; `exp` the expected effect of the missing days.
export function annualCounts(daily, summary, family, thr) {
  const fam = FAMILIES[family];
  const a = summary.annual;
  const flags = fam.elem === 'tmax' ? a.complete_tmax : a.complete_tmin;
  const daysValid = fam.elem === 'tmax' ? a.days_valid_tmax : a.days_valid_tmin;
  const rates = doyPassRates(daily, family, thr);
  const lower = [], exp = [], total = [];
  for (const y of a.year) {
    const from = new Date(Date.UTC(y, 0, 1)), to = new Date(Date.UTC(y, 11, 31));
    lower.push(countRange(daily, family, thr, from, to));
    exp.push(expectedMissed(daily, family, thr, from, to, rates));
    total.push(Math.round((to - from) / 86400000) + 1);
  }
  return { values: promote(summary, fam.elem, flags, a.partial, daysValid, total, lower, exp), lower, exp };
}

// Per-(year, month) counts aligned with summary.monthly rows.
export function monthlyCounts(daily, summary, family, thr) {
  const fam = FAMILIES[family];
  const m = summary.monthly;
  const flags = fam.elem === 'tmax' ? m.complete_tmax : m.complete_tmin;
  const daysValid = fam.elem === 'tmax' ? m.days_valid_tmax : m.days_valid_tmin;
  const rates = doyPassRates(daily, family, thr);
  const lower = [], exp = [], total = [];
  m.year.forEach((y, k) => {
    const mo = m.month[k];
    const from = new Date(Date.UTC(y, mo - 1, 1)), to = new Date(Date.UTC(y, mo - 1, daysInMonth(y, mo)));
    lower.push(countRange(daily, family, thr, from, to));
    exp.push(expectedMissed(daily, family, thr, from, to, rates));
    total.push(daysInMonth(y, mo));
  });
  return { values: promote(summary, fam.elem, flags, m.year.map((y, k) => false), daysValid, total, lower, exp), lower, exp };
}

// Cold-season (Jul->Jun, labeled by January year) counts aligned with summary.cold_season rows.
export function seasonCounts(daily, summary, family, thr) {
  const cs = summary.cold_season;
  const flags = FAMILIES[family].elem === 'tmax' ? cs.complete_tmax : cs.complete_tmin;
  const fam = FAMILIES[family];
  const daysValid = fam.elem === 'tmax' ? cs.days_valid_tmax : cs.days_valid_tmin;
  const rates = doyPassRates(daily, family, thr);
  const lower = [], exp = [], total = [];
  for (const y of cs.year) {
    const from = new Date(Date.UTC(y - 1, 6, 1)), to = new Date(Date.UTC(y, 5, 30));
    lower.push(countRange(daily, family, thr, from, to));
    exp.push(expectedMissed(daily, family, thr, from, to, rates));
    total.push(Math.round((to - from) / 86400000) + 1);
  }
  return { values: promote(summary, fam.elem, flags, cs.partial, daysValid, total, lower, exp), lower, exp };
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
export function exportedAnnualLower(summary, family, thr) {
  const key = FAMILIES[family].key + '_lb';
  if (family === 'frost') return summary.cold_season[key]?.[String(thr)] ?? null;
  return summary.annual[key]?.[String(thr)] ?? null;
}
export function exportedMonthlyLower(summary, family, thr) {
  return summary.monthly[FAMILIES[family].key + '_lb']?.[String(thr)] ?? null;
}
export function exportedAnnualExpected(summary, family, thr) {
  const key = FAMILIES[family].key + '_exp';
  if (family === 'frost') return summary.cold_season[key]?.[String(thr)] ?? null;
  return summary.annual[key]?.[String(thr)] ?? null;
}
export function exportedMonthlyExpected(summary, family, thr) {
  return summary.monthly[FAMILIES[family].key + '_exp']?.[String(thr)] ?? null;
}

// Contiguous runs of missing (null) days for one element inside [from, to].
export function missingRanges(daily, elem, from, to) {
  const arr = daily[elem];
  const a = dateToIdx(daily.start, from);
  const b = dateToIdx(daily.start, to);
  const out = [];
  let run = null;
  for (let i = a; i <= b; i++) {
    const missing = i < 0 || i >= daily.n || arr[i] == null;
    if (missing) {
      if (!run) run = { from: i, to: i };
      else run.to = i;
    } else if (run) {
      out.push(run);
      run = null;
    }
  }
  if (run) out.push(run);
  return out.map((r) => ({ from: idxToDate(daily.start, r.from), to: idxToDate(daily.start, r.to), days: r.to - r.from + 1 }));
}

export const yearsOf = (summary, family) =>
  family === 'frost' ? summary.cold_season.year : summary.annual.year;
export const partialOf = (summary, family) =>
  family === 'frost' ? summary.cold_season.partial : summary.annual.partial;

export { parseISO };

// Trend label: a slope only when the Theil-Sen fit is significant; otherwise say so.
export function trendLabel(t, noun) {
  if (!t) return '';
  if (!t.significant) return `no clear trend since ${t.from}`;
  const sign = t.slope_per_decade > 0 ? '+' : '';
  return `${sign}${t.slope_per_decade.toFixed(1)} ${noun} per decade since ${t.from}`;
}
