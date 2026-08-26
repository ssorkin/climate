import { error } from '@sveltejs/kit';
import { dataUrl } from '$lib/data.js';

export async function load({ params, fetch }) {
  const [sum, idx] = await Promise.all([
    fetch(dataUrl(`/data/stations/${params.id}/summary.json`)),
    fetch(dataUrl('/data/index.json'))
  ]);
  if (!sum.ok) error(404, 'station not found');
  return { summary: await sum.json(), index: await idx.json() };
}
