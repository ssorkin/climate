import { dataUrl } from '$lib/data.js';

export async function load({ fetch }) {
  const index = await (await fetch(dataUrl('/data/index.json'))).json();
  const hero = await (await fetch(dataUrl(`/data/stations/${index.regions[0].default_station}/summary.json`))).json();
  let usCount = null;
  try {
    const us = await fetch(dataUrl('/data/us/index.json'));
    if (us.ok) usCount = (await us.json()).stations.length;
  } catch {
    /* no national index yet */
  }
  let regional = null;
  try {
    const r = await fetch(dataUrl('/data/regional/la.json'));
    if (r.ok) regional = await r.json();
  } catch {
    /* no regional model */
  }
  return { index, hero, usCount, regional };
}
