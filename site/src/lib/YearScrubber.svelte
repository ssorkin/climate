<script>
  /**
   * Draggable year track with decade ticks. Keyboard: arrows step, PageUp/Down by 10.
   * `years` are the selectable years (in order); `disabled` is a Set of years to gray.
   */
  let { years = [], value = $bindable(), disabled = new Set(), label = 'Year' } = $props();
  let el;
  let dragging = $state(false);

  let idx = $derived(Math.max(0, years.indexOf(value)));
  let pct = $derived(years.length > 1 ? (idx / (years.length - 1)) * 100 : 0);
  let decades = $derived(years.filter((y) => y % 10 === 0));

  function pick(clientX) {
    const r = el.getBoundingClientRect();
    const t = Math.max(0, Math.min(1, (clientX - r.left) / r.width));
    value = years[Math.round(t * (years.length - 1))];
  }
  function down(e) {
    dragging = true;
    el.setPointerCapture(e.pointerId);
    pick(e.clientX);
  }
  function move(e) {
    if (dragging) pick(e.clientX);
  }
  function up() {
    dragging = false;
  }
  function key(e) {
    const step = e.key === 'PageUp' ? 10 : e.key === 'PageDown' ? -10 : e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0;
    if (!step) return;
    e.preventDefault();
    value = years[Math.max(0, Math.min(years.length - 1, idx + step))];
  }
</script>

<div class="scrub">
  <div class="readout"><span class="lbl">{label}</span> <b>{value}</b></div>
  <div
    class="track"
    bind:this={el}
    role="slider"
    tabindex="0"
    aria-valuemin={years[0]}
    aria-valuemax={years[years.length - 1]}
    aria-valuenow={value}
    aria-label={label}
    onpointerdown={down}
    onpointermove={move}
    onpointerup={up}
    onpointercancel={up}
    onkeydown={key}
  >
    <div class="rail"></div>
    {#each decades as d (d)}
      <div class="tick" style:left="{(years.indexOf(d) / (years.length - 1)) * 100}%">
        <span>{d}</span>
      </div>
    {/each}
    {#each years as y (y)}
      {#if disabled.has(y)}
        <div class="gap" style:left="{(years.indexOf(y) / (years.length - 1)) * 100}%"></div>
      {/if}
    {/each}
    <div class="thumb" class:dragging style:left="{pct}%"></div>
  </div>
</div>

<style>
  .scrub {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 1rem;
    align-items: center;
    padding: 0.4rem 0 1.4rem;
  }
  .readout {
    font-size: 1.05rem;
    min-width: 7.5rem;
  }
  .readout .lbl {
    color: #898781;
    font-size: 0.85rem;
  }
  .readout b {
    font-size: 1.5rem;
    font-weight: 750;
    color: #1f1b16;
    margin-left: 0.2rem;
  }
  .track {
    position: relative;
    height: 28px;
    cursor: ew-resize;
    touch-action: none;
    outline: none;
  }
  .track:focus-visible .thumb {
    box-shadow: 0 0 0 3px rgba(28, 92, 171, 0.35);
  }
  .rail {
    position: absolute;
    top: 12px;
    left: 0;
    right: 0;
    height: 4px;
    border-radius: 2px;
    background: #ddd5c8;
  }
  .tick {
    position: absolute;
    top: 8px;
    width: 1px;
    height: 12px;
    background: #b8b2a7;
  }
  .tick span {
    position: absolute;
    top: 14px;
    left: 0;
    transform: translateX(-50%);
    font-size: 0.68rem;
    color: #898781;
    white-space: nowrap;
  }
  .gap {
    position: absolute;
    top: 12px;
    width: 2px;
    height: 4px;
    background: #faf7f2;
  }
  .thumb {
    position: absolute;
    top: 3px;
    width: 22px;
    height: 22px;
    border-radius: 50%;
    background: #c2410c;
    border: 3px solid #fffdf9;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.25);
    transform: translateX(-50%);
    transition: transform 0.08s;
  }
  .thumb.dragging {
    transform: translateX(-50%) scale(1.15);
  }
  @media (max-width: 640px) {
    .scrub {
      grid-template-columns: 1fr;
      gap: 0.3rem;
    }
  }
</style>
