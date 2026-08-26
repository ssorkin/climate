<script>
  /**
   * MapLibre map (OpenFreeMap tiles, no key) with one pill marker per station showing
   * `values` for the scrubbed year. maplibre is dynamically imported so pages
   * render their charts before the map bundle arrives.
   */
  import { onMount } from 'svelte';
  import { HEAT_RAMP, COOL_RAMP, ramp } from '$lib/palette.js';

  let {
    stations = [],
    values = new Map(), // id -> number|null
    unitLabel = '',
    cool = false,
    center = [34.05, -118.3],
    zoom = 8.3,
    height = '520px',
    onselect = null,
    selected = null
  } = $props();

  let el;
  let map;
  let markers = new Map();
  let ready = $state(false);

  onMount(async () => {
    const maplibregl = (await import('maplibre-gl')).default;
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
    // Markers don't need the style: add them now so the data shows even if tiles lag or fail.
    {
      for (const s of stations) {
        const d = document.createElement('div');
        d.className = 'stpill';
        d.tabIndex = 0;
        d.setAttribute('role', 'button');
        const name = document.createElement('span');
        name.className = 'nm';
        name.textContent = s.short;
        const val = document.createElement('span');
        val.className = 'vl';
        d.append(name, val);
        d.addEventListener('click', () => onselect?.(s.id));
        d.addEventListener('keydown', (e) => e.key === 'Enter' && onselect?.(s.id));
        const m = new maplibregl.Marker({ element: d, anchor: 'center' }).setLngLat([s.lon, s.lat]).addTo(map);
        markers.set(s.id, { m, d, val });
      }
      ready = true;
      paint();
    }
    return () => map?.remove();
  });

  function paint() {
    if (!ready) return;
    const vals = [...values.values()].filter((v) => v != null);
    const vmax = Math.max(1, ...vals);
    for (const s of stations) {
      const mk = markers.get(s.id);
      if (!mk) continue;
      const v = values.get(s.id);
      mk.val.textContent = v == null ? '—' : `${Math.round(v)}`;
      const t = v == null ? null : v / vmax;
      const dark = t != null && t > 0.55;
      mk.d.style.background = v == null ? '#efe9df' : ramp(cool ? COOL_RAMP : HEAT_RAMP, t);
      mk.d.style.color = dark ? '#fff' : '#1f1b16';
      mk.d.classList.toggle('sel', s.id === selected);
      mk.d.classList.toggle('nodata', v == null);
      mk.d.title = v == null ? `${s.short}: no complete data for this year` : `${s.short}: ${v} ${unitLabel}`;
    }
  }
  $effect(() => {
    values;
    selected;
    cool;
    paint();
  });
</script>

<div class="map" bind:this={el} style:height></div>

<style>
  .map {
    width: 100%;
    border-radius: 14px;
    overflow: hidden;
    border: 1px solid #e8e1d5;
    background: #efe9df;
  }
  :global(.stpill) {
    display: inline-flex;
    align-items: baseline;
    gap: 0.35rem;
    padding: 0.28rem 0.7rem;
    border-radius: 999px;
    background: #fffdf9;
    border: 2px solid #fffdf9;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.25);
    font: 600 0.82rem system-ui, sans-serif;
    color: #1f1b16;
    cursor: pointer;
    white-space: nowrap;
    transition: transform 0.1s;
  }
  :global(.stpill:hover) {
    transform: scale(1.06);
    z-index: 5;
  }
  :global(.stpill .vl) {
    font-size: 1.05rem;
    font-weight: 800;
  }
  :global(.stpill.sel) {
    border-color: #1f1b16;
  }
  :global(.stpill.nodata) {
    opacity: 0.75;
  }
  :global(.stpill.excluded) {
    background: transparent;
    border: 1.5px dashed #898781;
    color: #52514e;
    font-weight: 500;
    box-shadow: none;
  }
</style>
