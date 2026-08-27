<script>
  /**
   * National map: one circle per station (a MapLibre GeoJSON layer, not HTML markers —
   * thousands of points), colored by the scrubbed year's count on a fixed scale. Counts
   * appear as labels once zoomed in. Lower bounds get a dashed-looking lighter ring.
   */
  import { onMount } from 'svelte';
  import { HEAT_RAMP, COOL_RAMP } from '$lib/palette.js';
  import '$lib/spiral.css';
  import { loadCurves } from '$lib/curves.js';
  import { makeSpiralMarker, removeSpiralMarker, paintSpiralMarker, layoutSpirals, pickVisible } from '$lib/spiralMarker.js';

  let {
    stations = [], // [{id, short, state, lat, lon, ...}]
    values = null, // Float32Array/Array aligned with stations: count, -1 no data; lower bounds negative -(lb+2)
    vmax = 50,
    cool = false,
    unitLabel = '',
    onselect = null,
    height = '560px',
    center = [39.5, -98],
    zoom = 3.6,
    stateFilter = '',
    spirals = 'off', // 'off' | 'tmax' | 'tmin' | 'both': climate spirals for the longest records in view
    year = null,
    spiralSize = 96,
    maxSpirals = 24
  } = $props();

  let maplibregl;
  let spiralMarkers = new Map();
  const curveCache = new Map();
  let spiralGen = 0;

  let el;
  let map;
  let ready = $state(false);

  function decode(v) {
    if (v == null || v === -1 || v === -32768) return { v: null, lower: false };
    if (v < -1) return { v: -v - 2, lower: true };
    return { v, lower: false };
  }
  function geojson() {
    return {
      type: 'FeatureCollection',
      features: stations.map((s, i) => {
        const d = decode(values?.[i]);
        return {
          type: 'Feature',
          id: i,
          geometry: { type: 'Point', coordinates: [s.lon, s.lat] },
          properties: {
            id: s.id,
            short: s.short,
            state: s.state,
            v: d.v == null ? -1 : d.v,
            t: d.v == null ? -1 : Math.min(1, d.v / vmax),
            lower: d.lower ? 1 : 0,
            label: d.v == null ? '' : (d.lower ? '≥' : '') + d.v,
            hidden: (stateFilter && s.state !== stateFilter) || d.v == null ? 1 : 0
          }
        };
      })
    };
  }
  function rampExpr(ramp) {
    const stops = [];
    ramp.forEach((c, i) => stops.push(i / (ramp.length - 1), c));
    return ['interpolate', ['linear'], ['get', 't'], ...stops];
  }
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
    const setup = () => {
      if (map.getSource('st')) return;
      map.addSource('st', { type: 'geojson', data: geojson() });
      map.addLayer({
        id: 'st-circles',
        type: 'circle',
        source: 'st',
        filter: ['==', ['get', 'hidden'], 0],
        paint: {
          'circle-radius': ['interpolate', ['linear'], ['zoom'], 3, 3.2, 6, 7, 9, 14],
          'circle-color': rampExpr(cool ? COOL_RAMP : HEAT_RAMP),
          'circle-stroke-color': ['case', ['==', ['get', 'lower'], 1], '#898781', '#fffdf9'],
          'circle-stroke-width': ['interpolate', ['linear'], ['zoom'], 3, 0.6, 7, 1.5],
          'circle-opacity': 0.92
        }
      });
      map.addLayer({
        id: 'st-labels',
        type: 'symbol',
        source: 'st',
        minzoom: 6.5,
        filter: ['==', ['get', 'hidden'], 0],
        layout: {
          'text-field': ['get', 'label'],
          'text-size': 11,
          'text-font': ['Noto Sans Bold'],
          'text-allow-overlap': false
        },
        paint: {
          'text-color': ['case', ['>', ['get', 't'], 0.55], '#ffffff', '#1f1b16']
        }
      });
      map.addLayer({
        id: 'st-names',
        type: 'symbol',
        source: 'st',
        minzoom: 8,
        filter: ['==', ['get', 'hidden'], 0],
        layout: {
          'text-field': ['get', 'short'],
          'text-size': 10.5,
          'text-font': ['Noto Sans Regular'],
          'text-offset': [0, 1.6],
          'text-anchor': 'top',
          'text-optional': true
        },
        paint: { 'text-color': '#52514e', 'text-halo-color': '#fffdf9', 'text-halo-width': 1.2 }
      });
      map.on('click', 'st-circles', (e) => {
        const f = e.features?.[0];
        if (f) onselect?.(f.properties.id);
      });
      map.on('mouseenter', 'st-circles', () => (map.getCanvas().style.cursor = 'pointer'));
      map.on('mouseleave', 'st-circles', () => (map.getCanvas().style.cursor = ''));
      const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 10 });
      map.on('mousemove', 'st-circles', (e) => {
        const p = e.features?.[0]?.properties;
        if (!p) return;
        const txt = p.v < 0 ? `${p.short}, ${p.state}: no data` : `${p.short}, ${p.state}: ${p.lower ? 'at least ' : ''}${p.v} ${unitLabel}`;
        popup.setLngLat(e.lngLat).setText(txt).addTo(map);
      });
      map.on('mouseleave', 'st-circles', () => popup.remove());
      map.on('moveend', () => refreshSpirals());
      ready = true;
    };
    // The style may already be loaded (cached) — or fail (offline); add the data layer either way.
    if (map.isStyleLoaded()) setup();
    else map.once('load', setup);
    map.once('error', () => setTimeout(() => { try { setup(); } catch (e) { /* no style */ } }, 500));
    return () => map?.remove();
  });
  $effect(() => {
    values;
    stateFilter;
    vmax;
    cool;
    if (!ready) return;
    map.getSource('st')?.setData(geojson());
    map.setPaintProperty('st-circles', 'circle-color', rampExpr(cool ? COOL_RAMP : HEAT_RAMP));
  });
  // Spirals: pick the longest records in view that fit, load their curves, draw.
  $effect(() => { spirals; stateFilter; if (ready) refreshSpirals(); });
  $effect(() => { year; spirals; if (ready) paintSpirals(); });

  async function refreshSpirals() {
    if (!map) return;
    const gen = ++spiralGen;
    if (spirals === 'off') {
      for (const mk of spiralMarkers.values()) removeSpiralMarker(mk);
      spiralMarkers.clear();
      return;
    }
    const pool = stations
      .filter((s) => (s.complete_years ?? 0) >= 30 && (!stateFilter || s.state === stateFilter))
      .sort((a, b) => (b.complete_years ?? 0) - (a.complete_years ?? 0));
    const chosen = pickVisible(map, pool, spiralSize, maxSpirals);
    const ids = new Set(chosen.map((s) => s.id));
    for (const [id, mk] of spiralMarkers) if (!ids.has(id)) { removeSpiralMarker(mk); spiralMarkers.delete(id); }
    await Promise.all(chosen.map(async (s) => {
      if (!curveCache.has(s.id)) curveCache.set(s.id, await loadCurves(s.id).catch(() => null));
    }));
    if (gen !== spiralGen) return;
    for (const s of chosen) {
      if (!curveCache.get(s.id) || spiralMarkers.has(s.id)) continue;
      spiralMarkers.set(s.id, makeSpiralMarker(maplibregl, map, s, spiralSize, onselect));
    }
    paintSpirals();
    layoutSpirals(map, spiralMarkers, spiralSize);
  }
  function paintSpirals() {
    if (spirals === 'off') return;
    for (const mk of spiralMarkers.values()) {
      const c = curveCache.get(mk.s.id);
      if (!c) continue;
      const score = mk.s.score_tmax != null || mk.s.score_tmin != null ? { tmax: mk.s.score_tmax, tmin: mk.s.score_tmin } : null;
      paintSpiralMarker(mk, c, spirals, year, { score, base: null, fallback: !!mk.s.base_fallback });
    }
  }

  export function flyTo(lat, lon, z = 8) {
    map?.flyTo({ center: [lon, lat], zoom: z });
  }
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
</style>
