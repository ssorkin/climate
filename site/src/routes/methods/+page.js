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
  return { index, regional };
}
