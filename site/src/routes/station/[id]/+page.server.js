import { readFileSync } from 'node:fs';

/** Prerender one page per station in the export index. */
export function entries() {
  const index = JSON.parse(readFileSync('static/data/index.json', 'utf-8'));
  return index.stations.map((s) => ({ id: s.id }));
}
