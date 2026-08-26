<script>
  import { units, setUnits } from '$lib/units.svelte.js';
</script>

<span class="toggle" role="group" aria-label="Temperature units">
  <button class:on={units.f} onclick={() => setUnits(true)} aria-pressed={units.f}>°F</button>
  <button class:on={!units.f} onclick={() => setUnits(false)} aria-pressed={!units.f}>°C</button>
</span>

<style>
  .toggle {
    display: inline-flex;
    border: 1px solid #d9d2c5;
    border-radius: 999px;
    overflow: hidden;
    background: #fffdf9;
  }
  button {
    font: inherit;
    font-size: 0.85rem;
    padding: 0.2rem 0.6rem;
    border: 0;
    background: transparent;
    color: #52514e;
    cursor: pointer;
  }
  button.on {
    background: #1f1b16;
    color: #fff;
  }
</style>
