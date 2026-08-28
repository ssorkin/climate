<script>
  /** Author, publication date, data-through date and the story's permalink. */
  import { AUTHOR, permalink, fmtLong } from '$lib/stories.js';
  import { fmtISO } from '$lib/dates.js';
  let { story, dataThrough = null, onPermalink = false } = $props();
</script>

<p class="byline">
  By <a href={AUTHOR.url} rel="author">{AUTHOR.name}</a>
  <span class="sep">·</span> Published {fmtLong(story.published)}
  {#if dataThrough}<span class="sep">·</span> Data through {fmtISO(dataThrough)}{/if}
  <span class="sep">·</span>
  {#if onPermalink}
    <span class="perma">Permalink: <a href={permalink(story)}>climate.sorkinlabs.com{permalink(story)}</a></span>
  {:else}
    <a href={permalink(story)}>Permalink</a>
  {/if}
  <span class="sep">·</span> <a href="/stories">All stories</a>
</p>

<style>
  .byline {
    font-size: 0.9rem;
    color: #52514e;
    margin: 0 0 1rem;
  }
  .sep {
    color: #b8b2a7;
    margin: 0 0.3rem;
  }
  .byline a {
    color: #1c5cab;
  }
  .byline a[rel='author'] {
    color: inherit;
    font-weight: 600;
    text-decoration: none;
  }
</style>
