<script>
  import { STORIES, AUTHOR, permalink, fmtLong } from '$lib/stories.js';
</script>

<svelte:head>
  <title>Stories · climate.sorkinlabs</title>
  <meta property="og:title" content="Stories from the station records" />
  <meta property="og:description" content="Data stories from NOAA's hourly station records, each with a permanent link." />
</svelte:head>

<section class="hero">
  <h1>Stories</h1>
  <p class="lede">Each story asks one question of the station records and keeps its answer at a permanent link, so it can be checked against the record as it grows. The newest one is the front page.</p>
</section>

<section class="list">
  {#each STORIES as s (s.slug)}
    <article class="card">
      <h2><a href={permalink(s)}>{s.title}</a></h2>
      <p class="byline">By {AUTHOR.name} · {fmtLong(s.published)} · <a href={permalink(s)}>{permalink(s)}</a></p>
      <p>{s.dek}</p>
    </article>
  {/each}
</section>

<style>
  .hero {
    margin-top: 2rem;
    max-width: 44rem;
  }
  .list {
    display: grid;
    gap: 1rem;
    max-width: 44rem;
    margin-top: 1.5rem;
  }
  article h2 {
    margin: 0 0 0.3rem;
    font-size: 1.3rem;
  }
  article h2 a {
    color: inherit;
    text-decoration: none;
  }
  article h2 a:hover {
    text-decoration: underline;
  }
  .byline {
    font-size: 0.88rem;
    color: #52514e;
    margin: 0 0 0.5rem;
  }
  article p:last-child {
    margin: 0;
    color: #52514e;
  }
</style>
