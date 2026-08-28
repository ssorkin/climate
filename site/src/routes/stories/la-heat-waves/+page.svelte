<script>
  import LaHeatWaves from '$lib/stories/LaHeatWaves.svelte';
  let { data } = $props();
</script>

<LaHeatWaves {data} onPermalink />
