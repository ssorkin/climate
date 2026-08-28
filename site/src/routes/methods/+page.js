import { dataUrl } from '$lib/data.js';

export async function load({ fetch }) {
  const index = await (await fetch(dataUrl('/data/index.json'))).json();
  let regional = null;
  try {
    const r = await fetch(dataUrl('/data/regional/la.json'));
    if (r.ok) regional = await r.json();
  } catch {
    /* no regional model */
  }
  let heatwaves = null;
  try {
    const h = await fetch(dataUrl('/data/regional/la-heatwaves.json'));
    if (h.ok) heatwaves = await h.json();
  } catch {
    /* no heat-wave export */
  }
  return { index, regional, heatwaves };
}
