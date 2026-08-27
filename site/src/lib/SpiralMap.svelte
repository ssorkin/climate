<script>
  /**
   * MapLibre map with one climate spiral per station at its location: angle = day of year,
   * radius = temperature (the station's own scale), one ring per year, palest = oldest,
   * darkest = latest, shaded = the baseline's middle 80% / 50%, dashed = its median. Spirals
   * that would overlap are nudged apart and tethered to their true location by a thin line.
   */
  import { onMount } from 'svelte';
  import '$lib/spiral.css';
  import { makeSpiralMarker, removeSpiralMarker, paintSpiralMarker, layoutSpirals } from '$lib/spiralMarker.js';

  let { stations = [], curves = {}, element = 'tmax', center = [34.05, -118.3], zoom = 8.3, height = '620px', size = 108, onselect = null, year = null } = $props();

  let el;
  let map;
  let ready = $state(false);
  let markers = new Map();
  let maplibregl;
  let fitted = false;

  onMount(async () => {
    maplibregl = (await import('maplibre-gl')).default;
    await import('maplibre-gl/dist/maplibre-gl.css');
    map = new maplibregl.Map({
      container: el,
      style: 'https://tiles.openfreemap.org/styles/positron',
      center: [center[1], center[0]],
      zoom,
      attributionControl: { compact: true },
      cooperativeGestures: true
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');
    map.on('error', (e) => console.warn('map:', e?.error?.message ?? e));
    map.on('zoomend', () => layoutSpirals(map, markers, size));
    map.on('load', () => { fit(); layoutSpirals(map, markers, size); });
    ready = true;
    return () => map?.remove();
  });

  function fit() {
    const pts = stations.filter((s) => curves[s.id]);
    if (!map || fitted || pts.length < 2) return;
    const lons = pts.map((s) => s.lon), lats = pts.map((s) => s.lat);
    map.fitBounds([[Math.min(...lons), Math.min(...lats)], [Math.max(...lons), Math.max(...lats)]], { padding: { top: size * 0.8, bottom: size * 0.9, left: size * 0.7, right: size * 0.7 }, duration: 0 });
    fitted = true;
  }

  $effect(() => {
    if (!ready || !maplibregl) return;
    const ids = stations.filter((s) => curves[s.id]).map((s) => s.id);
    for (const [id, mk] of markers) if (!ids.includes(id)) { removeSpiralMarker(mk); markers.delete(id); }
    for (const s of stations) {
      if (!curves[s.id] || markers.has(s.id)) continue;
      markers.set(s.id, makeSpiralMarker(maplibregl, map, s, size, onselect));
    }
    paint();
    if (map?.loaded()) fit();
    layoutSpirals(map, markers, size);
  });

  $effect(() => { element; curves; year; paint(); });

  function paint() {
    for (const mk of markers.values()) {
      const h = mk.s.headline ?? {};
      paintSpiralMarker(mk, curves[mk.s.id], element, year, { score: h.score, base: h.base_period, fallback: !!h.baseline_fallback });
    }
  }
</script>

<div class="map" bind:this={el} style="height:{height}"></div>

<style>
  .map {
    width: 100%;
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid #e8e1d5;
    background: #f2eee7;
  }
</style>
