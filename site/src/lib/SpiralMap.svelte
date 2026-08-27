<script>
  /**
   * MapLibre map with one climate spiral per station at its location: angle = day of year,
   * radius = temperature (shared scale), one ring per year, palest = oldest, darkest = latest,
   * dashed = the 1951–80 median where the station has a baseline. Spirals that would overlap
   * are nudged apart and tethered to their true location by a thin line.
   */
  import { onMount } from 'svelte';
  import { drawSpiral, sharedRange } from '$lib/spiral.js';

  let { stations = [], curves = {}, element = 'tmax', center = [34.05, -118.3], zoom = 8.3, height = '620px', size = 108, onselect = null, year = null } = $props();

  let el;
  let map;
  let ready = $state(false);
  let markers = new Map(); // id -> {m, dot, box, canvas, leader}
  let maplibregl;

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
    map.on('zoomend', layout);
    map.on('load', () => { fit(); layout(); });
    ready = true;
    return () => map?.remove();
  });

  // (Re)create markers when the station/curve set changes.
  $effect(() => {
    if (!ready || !maplibregl) return;
    const ids = stations.filter((s) => curves[s.id]).map((s) => s.id);
    for (const [id, mk] of markers) if (!ids.includes(id)) { mk.m.remove(); mk.dot.remove(); markers.delete(id); }
    for (const s of stations) {
      if (!curves[s.id] || markers.has(s.id)) continue;
      const box = document.createElement('div');
      box.className = 'spiral';
      box.tabIndex = 0;
      box.setAttribute('role', 'button');
      const leader = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      leader.setAttribute('class', 'leader');
      const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      leader.append(line);
      const canvas = document.createElement('canvas');
      const nm = document.createElement('span');
      nm.className = 'nm';
      nm.textContent = s.short;
      box.append(leader, canvas, nm);
      box.addEventListener('click', () => onselect?.(s.id));
      box.addEventListener('keydown', (e) => e.key === 'Enter' && onselect?.(s.id));
      const dotEl = document.createElement('div');
      dotEl.className = 'spiral-dot';
      const dot = new maplibregl.Marker({ element: dotEl, anchor: 'center' }).setLngLat([s.lon, s.lat]).addTo(map);
      const m = new maplibregl.Marker({ element: box, anchor: 'center' }).setLngLat([s.lon, s.lat]).addTo(map);
      markers.set(s.id, { m, dot, box, canvas, line, s });
    }
    paint();
    if (map?.loaded()) fit();
    layout();
  });

  let fitted = false;
  function fit() {
    const pts = stations.filter((s) => curves[s.id]);
    if (!map || fitted || pts.length < 2) return;
    const lons = pts.map((s) => s.lon), lats = pts.map((s) => s.lat);
    map.fitBounds([[Math.min(...lons), Math.min(...lats)], [Math.max(...lons), Math.max(...lats)]], { padding: { top: size * 0.8, bottom: size * 0.9, left: size * 0.7, right: size * 0.7 }, duration: 0 });
    fitted = true;
  }

  // Redraw on element change.
  $effect(() => { element; curves; year; paint(); });

  function paint() {
    const list = stations.filter((s) => curves[s.id]).map((s) => curves[s.id]);
    if (!list.length) return;
    const tRange = sharedRange(list, element);
    for (const mk of markers.values()) drawSpiral(mk.canvas, curves[mk.s.id], element, { size, tRange, from: 1940, upTo: year, highlight: year });
  }

  // Push overlapping spirals apart in screen space; tether each to its true spot.
  function layout() {
    if (!map || !markers.size) return;
    const pts = [...markers.values()].map((mk) => ({ mk, o: map.project([mk.s.lon, mk.s.lat]) }));
    const pos = pts.map((p) => ({ x: p.o.x, y: p.o.y }));
    const minD = size + 8;
    for (let it = 0; it < 80; it++) {
      let moved = false;
      for (let i = 0; i < pos.length; i++)
        for (let j = i + 1; j < pos.length; j++) {
          let dx = pos[j].x - pos[i].x, dy = pos[j].y - pos[i].y;
          let d = Math.hypot(dx, dy);
          if (d >= minD) continue;
          if (d < 1e-3) { dx = 1; dy = 0; d = 1; }
          const push = (minD - d) / 2 + 0.5;
          pos[i].x -= (dx / d) * push; pos[i].y -= (dy / d) * push;
          pos[j].x += (dx / d) * push; pos[j].y += (dy / d) * push;
          moved = true;
        }
      // gentle pull back toward the true location
      for (let i = 0; i < pos.length; i++) { pos[i].x += (pts[i].o.x - pos[i].x) * 0.03; pos[i].y += (pts[i].o.y - pos[i].y) * 0.03; }
      if (!moved) break;
    }
    pts.forEach((p, i) => {
      const dx = pos[i].x - p.o.x, dy = pos[i].y - p.o.y;
      p.mk.m.setOffset([dx, dy]);
      const far = Math.hypot(dx, dy) > 4;
      p.mk.line.setAttribute('x1', size / 2); p.mk.line.setAttribute('y1', size / 2);
      p.mk.line.setAttribute('x2', size / 2 - dx); p.mk.line.setAttribute('y2', size / 2 - dy);
      p.mk.line.style.display = far ? '' : 'none';
      p.mk.dot.getElement().style.display = far ? '' : 'none';
    });
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
  :global(.spiral) {
    position: relative;
    cursor: pointer;
    text-align: center;
    line-height: 0;
  }
  :global(.spiral canvas) {
    display: block;
    border-radius: 50%;
    background: rgba(255, 253, 249, 0.82);
    box-shadow: 0 0 0 1px rgba(43, 39, 34, 0.12);
  }
  :global(.spiral:hover canvas) {
    box-shadow: 0 0 0 2px #2b2722;
  }
  :global(.spiral .nm) {
    position: absolute;
    left: 50%;
    top: 100%;
    transform: translate(-50%, 2px);
    font-size: 11px;
    line-height: 1.1;
    font-weight: 600;
    color: #2b2722;
    background: rgba(255, 253, 249, 0.85);
    padding: 1px 5px;
    border-radius: 6px;
    white-space: nowrap;
  }
  :global(.spiral .leader) {
    position: absolute;
    left: 0;
    top: 0;
    width: 100%;
    height: 100%;
    overflow: visible;
    pointer-events: none;
  }
  :global(.spiral .leader line) {
    stroke: #2b2722;
    stroke-width: 1;
    opacity: 0.6;
  }
  :global(.spiral-dot) {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #2b2722;
    border: 1.5px solid #fffdf9;
  }
</style>
