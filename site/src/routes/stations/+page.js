import { dataUrl } from '$lib/data.js';

export async function load({ fetch }) {
  return { index: await (await fetch(dataUrl('/data/index.json'))).json() };
}
