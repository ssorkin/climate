<script>
  /** Warming stripes: annual anomaly of the daily low vs 1951–1980, diverging blue–red. */
  import { units } from '$lib/units.svelte.js';
  import { fmtC } from '$lib/units.js';
  import { diverging, NEUTRAL } from '$lib/palette.js';
  let { years = [], anomalies = [], partial = [], label = 'daily low', baseline = [1951, 1980], amplitude = 2 } = $props();
  let hover = $state(null);
  const W = 860;
  const H = 110;
  let bw = $derived(W / years.length);
  let k = $derived(hover == null ? -1 : years.indexOf(hover));
</script>

<div class="stripes">
  <svg viewBox="0 0 {W} {H}" role="img" aria-label="Annual anomaly stripes" onpointermove={(e) => { const r = e.currentTarget.getBoundingClientRect(); hover = years[Math.max(0, Math.min(years.length - 1, Math.floor(((e.clientX - r.left) / r.width) * years.length)))]; }} onpointerleave={() => (hover = null)}>
    {#each years as y, i (y)}
      {@const a = anomalies[i]}
      <rect x={i * bw} y="0" width={bw + 0.3} height={H - 18} fill={a == null ? '#f3efe7' : diverging(a / amplitude)} opacity={partial[i] ? 0.5 : 1} />
      {#if y % 20 === 0}
        <text x={i * bw + bw / 2} y={H - 4} text-anchor="middle" font-size="11" fill="#898781">{y}</text>
      {/if}
    {/each}
    {#if k >= 0}<rect x={k * bw} y="0" width={bw} height={H - 18} fill="none" stroke="#1f1b16" stroke-width="1.5" />{/if}
  </svg>
  <div class="tip">
    {#if k >= 0}
      <b>{hover}</b>: average {label} {anomalies[k] == null ? 'incomplete year' : fmtC(anomalies[k], units.f, { sign: true, delta: true }) + ` vs ${baseline[0]}–${baseline[1]}`}{partial[k] ? ' (so far)' : ''}
    {:else}
      Each stripe is one year's average {label} compared with {baseline[0]}–{baseline[1]}: blue cooler, red warmer. Light gray = incomplete year.
    {/if}
  </div>
</div>

<style>
  .stripes svg {
    width: 100%;
    height: auto;
    display: block;
    cursor: crosshair;
  }
</style>
