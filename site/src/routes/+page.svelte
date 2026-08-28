<script>
  /** The front page shows the newest story; each story also has a permanent home under /stories. */
  import LaHeatWaves from '$lib/stories/LaHeatWaves.svelte';
  let { data } = $props();
</script>

<LaHeatWaves {data} />
