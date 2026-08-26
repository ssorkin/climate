<script>
  /** This summer so far, per station: mean high over the same Jun 1 -> through window, ranked. */
  import { units } from '$lib/units.svelte.js';
  import { fmtC } from '$lib/units.js';
  import { fmtISO } from '$lib/dates.js';
  let { stations = [] } = $props();
  const ordinal = (n) => n + (n % 10 === 1 && n % 100 !== 11 ? 'st' : n % 10 === 2 && n % 100 !== 12 ? 'nd' : n % 10 === 3 && n % 100 !== 13 ? 'rd' : 'th');
  let rows = $derived(
    stations
      .map((s) => ({ s, h: s.headline.summer_to_date }))
      .filter((r) => r.h?.ref_year)
      .sort((a, b) => (a.h.rank_tmax ?? 1e9) - (b.h.rank_tmax ?? 1e9))
  );
</script>

<div class="row">
  {#each rows as { s, h } (s.id)}
    <a class="card item" href="/station/{s.id}?year={h.ref_year}" class:top={h.rank_tmax === 1} class:na={h.rank_tmax == null}>
      <span class="nm">{s.short}</span>
      {#if h.rank_tmax != null}
        <span class="rank">{ordinal(h.rank_tmax)}<span class="of"> of {h.n_years}</span></span>
        <span class="sub">avg high {fmtC(h.tmax_mean_c, units.f)} · {h.warm70 ?? '—'} warm nights</span>
      {:else}
        <span class="rank na">not yet rankable</span>
        <span class="sub">{h.days_valid ?? 0} of {h.window_days} days reported</span>
      {/if}
      <span class="sub muted">Jun 1 – {fmtISO(h.through, { year: false })}</span>
    </a>
  {/each}
</div>

<style>
  .row {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: 0.6rem;
  }
  .item {
    display: grid;
    gap: 0.1rem;
    text-decoration: none;
    color: #2b2722;
    padding: 0.7rem 0.8rem;
  }
  .item:hover {
    border-color: #a89f8f;
  }
  .item.top {
    border-color: #c2410c;
    box-shadow: inset 0 0 0 1px #c2410c;
  }
  .nm {
    font-weight: 650;
    font-size: 0.95rem;
  }
  .rank {
    font-size: 1.7rem;
    font-weight: 800;
    line-height: 1.1;
    color: #1f1b16;
  }
  .rank.na {
    font-size: 0.95rem;
    font-weight: 600;
    color: #898781;
  }
  .of {
    font-size: 0.85rem;
    font-weight: 500;
    color: #52514e;
  }
  .sub {
    font-size: 0.78rem;
    color: #52514e;
  }
</style>
