<script>
  /** The station's hourly (ISD) layer: hours above thresholds, no-relief nights, heat-index hours, diurnal curves. */
  import { units } from '$lib/units.svelte.js';
  import { fmtThresholdF, fmtC } from '$lib/units.js';
  import { daysInYear } from '$lib/dates.js';
  import { HEAT, COOL } from '$lib/palette.js';
  import AnnualBars from '$lib/AnnualBars.svelte';
  import DiurnalCurve from '$lib/DiurnalCurve.svelte';
  let { hourly, year = null, onselect = null, family = 'hot' } = $props();
  let a = $derived(hourly.annual);
  let metric = $state(family === 'warm' ? 'norelief' : 'hours');
  let thr = $state(family === 'warm' ? 70 : 95);
  let options = $derived(metric === 'hours' ? hourly.thresholds_f.hours : metric === 'norelief' ? hourly.thresholds_f.nights : hourly.thresholds_f.heat_index);
  $effect(() => {
    if (!options.includes(thr)) thr = options[metric === 'norelief' ? 1 : 1] ?? options[0];
  });
  let series = $derived(a[metric === 'hours' ? 'hours' : metric === 'norelief' ? 'norelief' : 'hi_hours'][String(thr)]);
  let complete = $derived(metric === 'norelief' ? a.nights_complete : a.complete);
  let label = $derived(metric === 'hours' ? `Hours at or above ${fmtThresholdF(thr, units.f)}` : metric === 'norelief' ? `Nights that never fell below ${fmtThresholdF(thr, units.f)} (6 pm–8 am)` : `Hours with a heat index at or above ${fmtThresholdF(thr, units.f)}`);
  let unit = $derived(metric === 'norelief' ? 'nights' : 'hours');
  let w = $derived(hourly.windows);
  const key = $derived(metric === 'hours' ? `hours_${thr}` : metric === 'norelief' ? `norelief_${thr}` : `hi_hours_${thr}`);
  let bias = $derived.by(() => {
    const b = hourly.ghcn_bias;
    if (!b) return null;
    const v = b.tmax_minus_hourly_c.filter((x) => x != null);
    const n = b.tmin_minus_hourly_c.filter((x) => x != null);
    return v.length ? { tmax: v.reduce((s, q) => s + q, 0) / v.length, tmin: n.reduce((s, q) => s + q, 0) / n.length } : null;
  });
</script>

<p class="muted">
  Automated hourly observations at this airport since {hourly.first_date.slice(0, 4)} (NOAA ISD, local time). Hours tell you how long
  the heat lasted; "no-relief nights" ask whether the air ever cooled below a threshold between 6 pm and 8 am — the question a bedroom
  asks. The heat index folds in humidity.
</p>
{#if w?.first10 && w?.last10}
  <div class="hero small-hero">
    <div class="stat"><span class="lbl">{label}, per year, {w.first10.years[0]}–{w.first10.years[1]}</span><span class="val">{w.first10[key] == null ? '—' : Math.round(w.first10[key])}</span></div>
    <div class="arrow">→</div>
    <div class="stat"><span class="lbl">per year, {w.last10.years[0]}–{w.last10.years[1]}</span><span class="val up">{w.last10[key] == null ? '—' : Math.round(w.last10[key])}</span></div>
  </div>
{/if}
<div class="pillrow" style="margin:0.5rem 0">
  <button class="pill" class:on={metric === 'hours'} onclick={() => (metric = 'hours')}>Hours above</button>
  <button class="pill" class:on={metric === 'norelief'} onclick={() => (metric = 'norelief')}>No-relief nights</button>
  <button class="pill" class:on={metric === 'hi'} onclick={() => (metric = 'hi')}>Heat-index hours</button>
  <span class="sep"></span>
  {#each options as t (t)}
    <button class="pill heat" class:on={thr === t} onclick={() => (thr = t)}>{fmtThresholdF(t, units.f)}</button>
  {/each}
</div>
<AnnualBars years={a.year} values={series} partial={a.partial} daysValid={a.days_complete} daysTotal={a.year.map((y) => daysInYear(y))} selected={year} {onselect} color={HEAT} unitLabel={unit} height={240} />

<h3>The shape of a summer day</h3>
<DiurnalCurve diurnal={hourly.diurnal} threshold={70} />

{#if bias}
  <p class="small muted">
    Cross-check: this airport's daily max/min thermometer (used for the day counts above) reads on average
    {fmtC(bias.tmax, units.f, { sign: true, delta: true })} above the hottest hourly reading and
    {fmtC(bias.tmin, units.f, { sign: true, delta: true })} vs. the coolest — the peak usually falls between hourly observations, which is why
    day counts here come from the thermometer's max/min, not from hourly samples.
  </p>
{/if}

<style>
  .small-hero {
    display: flex;
    gap: 1rem;
    align-items: center;
    flex-wrap: wrap;
    margin: 0.6rem 0;
  }
  .stat {
    display: grid;
  }
  .stat .lbl {
    font-size: 0.8rem;
    color: #52514e;
    max-width: 16rem;
    line-height: 1.3;
  }
  .stat .val {
    font-size: 2.2rem;
    font-weight: 750;
    line-height: 1;
    color: #1f1b16;
  }
  .stat .val.up {
    color: #c2410c;
  }
  .arrow {
    font-size: 1.6rem;
    color: #b8b2a7;
  }
  .sep {
    width: 1px;
    height: 1.4rem;
    background: #d9d2c5;
    margin: 0 0.3rem;
  }
  h3 {
    margin: 1.4rem 0 0.3rem;
    font-size: 1.05rem;
  }
</style>
