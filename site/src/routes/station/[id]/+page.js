import { error } from '@sveltejs/kit';
import { browser } from '$app/environment';
import { dataUrl } from '$lib/data.js';

// The prerendered HTML is a light shell (the station's summary is ~150 KB and there are
// thousands of stations); the summary loads on the client. During prerender we only
// resolve the station's name from the region indexes for the <title>.
export async function load({ params, fetch }) {
  const id = params.id;
  if (!browser) {
    const ix = await (await fetch(dataUrl('/data/index.json'))).json();
    let short = ix.stations.find((s) => s.id === id)?.short;
    if (!short) {
      const us = await fetch(dataUrl('/data/us/index.json'));
      if (us.ok) {
        const j = await us.json();
        const cols = j.columns;
        const row = Array.isArray(j.stations[0])
          ? j.stations.find((r) => r[0] === id)
          : j.stations.find((s) => s.id === id);
        short = row ? (Array.isArray(row) ? row[cols.indexOf('short')] : row.short) : null;
      }
    }
    if (!short) error(404, 'station not found');
    return { id, short, summary: null, index: ix };
  }
  const [sum, idx] = await Promise.all([
    fetch(dataUrl(`/data/stations/${id}/summary.json`)),
    fetch(dataUrl('/data/index.json'))
  ]);
  if (!sum.ok) error(404, 'station not found');
  const summary = await sum.json();
  return { id, short: summary.short, summary, index: await idx.json() };
}
