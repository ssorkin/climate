<script>
  import { page } from '$app/state';
  import { onMount } from 'svelte';
  import { loadUnits } from '$lib/units.svelte.js';
  import UnitToggle from '$lib/UnitToggle.svelte';
  let { children } = $props();
  onMount(() => loadUnits(page.url.searchParams));
</script>

<div class="shell" class:wide={page.url.pathname === '/' || page.url.pathname.startsWith('/map') || page.url.pathname.startsWith('/us')}>
  <header>
    <a class="brand" href="/">climate<span>.sorkinlabs</span></a>
    <nav>
      <a href="/map">LA stations</a>
      <a href="/us">US map</a>
      <a href="/methods">Methods</a>
      <a href="/data">Data</a>
      <a href="https://github.com/ssorkin/climate">GitHub</a>
      <UnitToggle />
    </nav>
  </header>

  <main>
    {@render children()}
  </main>

  <footer>
    <p>
      Every number on this site is computed from NOAA's public daily station records by an
      <a href="https://github.com/ssorkin/climate">open-source pipeline</a>. Charts show what
      one thermometer recorded at one place — not a regional average. See
      <a href="/methods">Methods</a> for what is and isn't included.
    </p>
  </footer>
</div>

<style>
  :global(*) {
    box-sizing: border-box;
  }
  :global(body) {
    margin: 0;
    background: #faf7f2;
    color: #2b2722;
    font-family: system-ui, -apple-system, 'Segoe UI', sans-serif;
    line-height: 1.55;
  }
  :global(a) {
    color: #1c5cab;
  }
  :global(h1, h2, h3) {
    line-height: 1.2;
    color: #1f1b16;
    letter-spacing: -0.01em;
  }
  :global(h1) {
    font-size: 2.2rem;
    font-weight: 750;
  }
  :global(h2) {
    font-size: 1.45rem;
    font-weight: 700;
    margin: 2.4rem 0 0.6rem;
  }
  :global(p.lede) {
    font-size: 1.15rem;
    color: #52514e;
    max-width: 44rem;
  }
  :global(.muted) {
    color: #898781;
  }
  :global(.small) {
    font-size: 0.85rem;
  }
  :global(.card) {
    background: #fffdf9;
    border: 1px solid #e8e1d5;
    border-radius: 12px;
    padding: 1rem 1.1rem;
  }
  :global(.pill) {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    border: 1px solid #d9d2c5;
    background: #fffdf9;
    border-radius: 999px;
    padding: 0.28rem 0.8rem;
    font: inherit;
    font-size: 0.9rem;
    color: #2b2722;
    cursor: pointer;
    line-height: 1.2;
  }
  :global(.pill:hover) {
    border-color: #a89f8f;
  }
  :global(.pill.on) {
    background: #1f1b16;
    border-color: #1f1b16;
    color: #fff;
  }
  :global(.pill.heat.on) {
    background: #c2410c;
    border-color: #c2410c;
  }
  :global(.pillrow) {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    align-items: center;
  }
  :global(.tip) {
    min-height: 1.5rem;
    font-size: 0.9rem;
    color: #52514e;
    font-variant-numeric: tabular-nums;
  }
  :global(.tip b) {
    color: #1f1b16;
  }
  :global(table.data) {
    border-collapse: collapse;
    font-size: 0.9rem;
    font-variant-numeric: tabular-nums;
  }
  :global(table.data th) {
    text-align: left;
    font-weight: 600;
    color: #52514e;
    border-bottom: 1px solid #e8e1d5;
    padding: 0.35rem 0.6rem;
  }
  :global(table.data td) {
    padding: 0.3rem 0.6rem;
    border-bottom: 1px solid #f0ebe2;
  }
  :global(table.data td.num) {
    text-align: right;
  }
  .shell {
    max-width: 960px;
    margin: 0 auto;
    padding: 0 1.25rem;
  }
  .shell.wide {
    max-width: calc(1200px + 2.5rem);
  }
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 0.75rem;
    padding: 1.1rem 0 0.9rem;
    border-bottom: 1px solid #e8e1d5;
  }
  .brand {
    font-weight: 800;
    font-size: 1.25rem;
    color: #1f1b16;
    text-decoration: none;
    letter-spacing: -0.02em;
  }
  .brand span {
    color: #c2410c;
    font-weight: 600;
  }
  nav {
    display: flex;
    gap: 1.1rem;
    align-items: center;
    flex-wrap: wrap;
  }
  nav a {
    color: #52514e;
    text-decoration: none;
    font-size: 0.95rem;
  }
  nav a:hover {
    color: #1f1b16;
  }
  main {
    min-height: 60vh;
    padding-bottom: 3rem;
  }
  footer {
    border-top: 1px solid #e8e1d5;
    padding: 1.2rem 0 2rem;
    color: #52514e;
    font-size: 0.9rem;
  }
</style>
