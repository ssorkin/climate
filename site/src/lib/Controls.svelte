<script>
  /** Metric family + threshold pills, with an "other…" whole-°F input computed live. */
  import { FAMILIES } from '$lib/metrics.js';
  import { units } from '$lib/units.svelte.js';
  import { fmtThresholdF } from '$lib/units.js';

  let { thresholds, family = $bindable('hot'), threshold = $bindable(95) } = $props();
  let custom = $state('');
  let standard = $derived(thresholds[FAMILIES[family].key] ?? []);
  let isCustom = $derived(!standard.includes(threshold));
  function setFamily(f) {
    family = f;
    threshold = thresholds[FAMILIES[f].key][f === 'hot' ? 1 : f === 'warm' ? 1 : 0];
    custom = '';
  }
  function applyCustom() {
    const v = Math.round(Number(custom));
    if (Number.isFinite(v) && v > -60 && v < 140) threshold = v;
  }
</script>

<div class="controls">
  <div class="pillrow">
    {#each Object.entries(FAMILIES) as [k, f] (k)}
      <button class="pill" class:on={family === k} onclick={() => setFamily(k)}>{f.label}</button>
    {/each}
  </div>
  <div class="pillrow">
    <span class="muted small">{FAMILIES[family].unit} {FAMILIES[family].op === '>=' ? 'at least' : 'at most'}</span>
    {#each standard as t (t)}
      <button class="pill heat" class:on={threshold === t} onclick={() => (threshold = t)}>{fmtThresholdF(t, units.f)}</button>
    {/each}
    <span class="custom" class:on={isCustom}>
      <input type="number" placeholder="other °F" bind:value={custom} onchange={applyCustom} onkeydown={(e) => e.key === 'Enter' && applyCustom()} aria-label="Custom threshold in °F" />
      {#if isCustom}<span class="small">{fmtThresholdF(threshold, units.f)} (computed live)</span>{/if}
    </span>
  </div>
</div>

<style>
  .controls {
    display: grid;
    gap: 0.5rem;
    margin: 0.6rem 0 1rem;
  }
  .custom input {
    width: 6.2rem;
    font: inherit;
    font-size: 0.9rem;
    padding: 0.25rem 0.6rem;
    border: 1px solid #d9d2c5;
    border-radius: 999px;
    background: #fffdf9;
  }
  .custom.on input {
    border-color: #c2410c;
  }
</style>
