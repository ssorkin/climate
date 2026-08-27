import { redirect } from '@sveltejs/kit';

// The original full-bleed map lived here; the stations directory replaced it.
export const prerender = true;
export function load() {
  redirect(301, '/stations');
}
