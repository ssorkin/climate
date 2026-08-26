import { readFileSync, existsSync } from 'node:fs';

/** Prerender one page per station in every region index (curated and generated). */
export function entries() {
  const ids = new Set();
  for (const f of ['static/data/index.json', 'static/data/us/index.json']) {
    if (!existsSync(f)) continue;
    const ix = JSON.parse(readFileSync(f, 'utf-8'));
    for (const s of ix.stations) ids.add(Array.isArray(s) ? s[0] : s.id);
  }
  return [...ids].map((id) => ({ id }));
}
