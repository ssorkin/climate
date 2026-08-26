<script>
  let { summary, compact = false } = $props();
  let obs = $derived(summary.obs_time ?? []);
  let latest = $derived(obs[obs.length - 1]);
</script>

<div class="note card">
  <b>How to read this station.</b>
  Every count is what this one thermometer recorded, from NOAA's daily archive, with NOAA's quality-flagged
  values excluded. A year is shown only if at least 90% of its days were observed (a month, 25 days);
  missing years are gaps, never zeros. Thresholds are in whole °F exactly as the observer wrote them down.
  {#if summary.kind === 'coop'}
    This is a cooperative-observer station: the thermometer's 24-hour max and min are read once a day
    {#if latest?.hhmm}(currently at {latest.hhmm.slice(0, 2)}:{latest.hhmm.slice(2)}){/if} and logged on the
    reading date{#if latest?.hhmm && latest.hhmm < '1200'}, so a "high" here mostly happened the previous
    afternoon{/if}. Monthly and yearly counts are not affected by that one-day offset.
  {:else}
    This is an airport station with automated instruments and calendar-day readings.
  {/if}
  {#if !compact}
    {#if obs.length > 1}
      Observation time changed {obs.length - 1} time{obs.length > 2 ? 's' : ''}:
      {#each obs as s, i (s.from)}{s.from.slice(0, 4)}–{s.to.slice(0, 4)} {s.hhmm ? s.hhmm.slice(0, 2) + ':' + s.hhmm.slice(2) : 'unrecorded'}{i < obs.length - 1 ? '; ' : '.'}{/each}
    {/if}
    Station siting and surroundings can change over a century; see <a href="/methods">Methods</a>.
  {/if}
</div>

<style>
  .note {
    font-size: 0.9rem;
    color: #52514e;
    line-height: 1.5;
  }
</style>
