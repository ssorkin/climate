<script>
  let { label, value, sub = '', accent = false } = $props();
</script>

<div class="tile">
  <span class="lbl">{label}</span>
  <span class="val" class:accent>{value}</span>
  {#if sub}<span class="sub">{sub}</span>{/if}
</div>

<style>
  .tile {
    display: grid;
    gap: 0.15rem;
    align-content: start;
  }
  .lbl {
    font-size: 0.9rem;
    color: #52514e;
    line-height: 1.3;
  }
  .val {
    font-size: 3.4rem;
    font-weight: 800;
    line-height: 1;
    color: #1f1b16;
    letter-spacing: -0.02em;
  }
  .val.accent {
    color: #c2410c;
  }
  .sub {
    font-size: 0.85rem;
    color: #898781;
  }
</style>
