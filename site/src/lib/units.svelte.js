// Global unit preference (°F default). URL `u=` wins over localStorage; both are
// read on the client only so the prerendered HTML is deterministic.
export const units = $state({ f: true });

export function loadUnits(searchParams) {
  const u = searchParams?.get('u');
  if (u === 'C' || u === 'F') {
    units.f = u === 'F';
    return;
  }
  try {
    const saved = localStorage.getItem('climate.units');
    if (saved === 'C' || saved === 'F') units.f = saved === 'F';
  } catch {
    /* storage unavailable */
  }
}

export function setUnits(f) {
  units.f = f;
  try {
    localStorage.setItem('climate.units', f ? 'F' : 'C');
  } catch {
    /* storage unavailable */
  }
}
