import { dataUrl } from "$lib/data.js";

export async function load({ fetch }) {
  const index = await (await fetch(dataUrl("/data/index.json"))).json();
  const hero = await (
    await fetch(
      dataUrl(
        `/data/stations/${index.regions[0].default_station}/summary.json`,
      ),
    )
  ).json();
  let usCount = null;
  try {
    const us = await fetch(dataUrl("/data/us/index.json"));
    if (us.ok) usCount = (await us.json()).stations.length;
  } catch {
    /* no national index yet */
  }
  let heatwaves = null;
  try {
    const h = await fetch(dataUrl("/data/regional/la-heatwaves.json"));
    if (h.ok) heatwaves = await h.json();
  } catch {
    /* no heat-wave export */
  }
  let regional = null;
  let indices = null;
  try {
    const r = await fetch(dataUrl("/data/regional/la.json"));
    if (r.ok) regional = await r.json();
    const ri = await fetch(dataUrl("/data/regional/la-indices.json"));
    if (ri.ok) indices = await ri.json();
  } catch {
    /* no regional model */
  }
  return { index, hero, usCount, regional, indices, heatwaves };
}
