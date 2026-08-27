// Shared spiral-marker plumbing for the LA and national maps: build the marker DOM, paint it,
// and push overlapping spirals apart with leader lines back to their true location.
import { drawSpiral } from '$lib/spiral.js';

export function makeSpiralMarker(maplibregl, map, s, size, onselect) {
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
  nm.textContent = s.state ? `${s.short}, ${s.state}` : s.short;
  const badge = document.createElement('span');
  badge.className = 'score day';
  const badgeN = document.createElement('span');
  badgeN.className = 'score night';
  box.append(leader, canvas, nm, badge, badgeN);
  box.addEventListener('click', () => onselect?.(s.id));
  box.addEventListener('keydown', (e) => e.key === 'Enter' && onselect?.(s.id));
  const dotEl = document.createElement('div');
  dotEl.className = 'spiral-dot';
  const dot = new maplibregl.Marker({ element: dotEl, anchor: 'center' }).setLngLat([s.lon, s.lat]).addTo(map);
  const m = new maplibregl.Marker({ element: box, anchor: 'center' }).setLngLat([s.lon, s.lat]).addTo(map);
  return { m, dot, box, canvas, line, badge, badgeN, s, size };
}

export function removeSpiralMarker(mk) {
  mk.m.remove();
  mk.dot.remove();
}

/** score: {tmax, tmin, tmax_span, tmin_span} | null; base: [y0, y1] | null; fallback: bool */
export function paintSpiralMarker(mk, curves, element, year, { score = null, base = null, fallback = false } = {}) {
  drawSpiral(mk.canvas, curves, element, { size: mk.size, from: 1940, upTo: year, highlight: year });
  const baseTxt = base ? `${base[0]}–${base[1]}` : 'baseline';
  const set = (el, v, what) => {
    if (v == null) { el.style.display = 'none'; return ''; }
    el.style.display = '';
    el.textContent = `${Math.round(v)}${fallback ? '†' : ''}`;
    const span = score?.[`${what === 'day' ? 'tmax' : 'tmin'}_span`];
    return `a typical ${what} of ${span ? `${span[0]}–${span[1]}` : 'its last ten complete years'} is warmer than ${Math.round(v)}% of ${baseTxt} ${what}s at the same date`;
  };
  const td = set(mk.badge, score?.tmax, 'day');
  const tn = set(mk.badgeN, score?.tmin, 'night');
  mk.badge.classList.toggle('dim', element === 'tmin');
  mk.badgeN.classList.toggle('dim', element === 'tmax');
  const parts = [td, tn].filter(Boolean);
  const name = mk.s.state ? `${mk.s.short}, ${mk.s.state}` : mk.s.short;
  mk.box.title = parts.length ? `${name}: ${parts.join('; ')}${fallback ? ' (scored against its own earliest complete years; no 1951–80 record)' : ''}` : `${name}: no baseline to score against`;
}

/** Nudge overlapping markers apart in screen space; tether each to its true spot. */
export function layoutSpirals(map, markers, size) {
  const list = [...markers.values()];
  if (!list.length) return;
  const pts = list.map((mk) => ({ mk, o: map.project([mk.s.lon, mk.s.lat]) }));
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

/** Greedy pick of up to `max` stations inside the view that fit without overlapping. */
export function pickVisible(map, stations, size, max) {
  const b = map.getBounds();
  const inView = stations.filter((s) => s.lat >= b.getSouth() && s.lat <= b.getNorth() && s.lon >= b.getWest() && s.lon <= b.getEast());
  const chosen = [];
  const minD = size * 0.8;
  for (const s of inView) {
    const p = map.project([s.lon, s.lat]);
    if (chosen.every((c) => Math.hypot(c.p.x - p.x, c.p.y - p.y) >= minD)) chosen.push({ s, p });
    if (chosen.length >= max) break;
  }
  return chosen.map((c) => c.s);
}
