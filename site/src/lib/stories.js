// The stories this site has told, newest first. Each has a permalink under /stories/<slug>
// that never changes; the front page shows the newest one. Dates are ISO (published is the
// day the story went live; the data date comes from the export at build time).
export const AUTHOR = { name: 'Stephen Sorkin', url: 'https://github.com/ssorkin' };

export const STORIES = [
  {
    slug: 'la-heat-waves',
    title: "Los Angeles heat waves haven't gotten hotter at their peak. Their nights have.",
    short: 'LA heat waves: flat peaks, warmer nights',
    dek: '80+ years of hourly NOAA records at LA-area weather stations. The hottest afternoon of a heat wave lands where it always did; the coolest night inside one is several degrees warmer, and a heat-wave night gives hours less relief under 70°F.',
    published: '2026-08-28',
    region: 'la'
  }
];

export const storyBySlug = (slug) => STORIES.find((s) => s.slug === slug) ?? null;
export const permalink = (story) => `/stories/${story.slug}`;
export const fmtLong = (iso) => {
  const [y, m, d] = iso.split('-').map(Number);
  return new Date(Date.UTC(y, m - 1, d)).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric', timeZone: 'UTC' });
};
