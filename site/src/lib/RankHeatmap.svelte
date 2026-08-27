<script>
  /**
   * Year × day-of-year heatmap of percentile ranks: each day's high or low placed within the
   * station's own 1951–1980 distribution for that calendar date. Rows run old → recent,
   * top → bottom; blue = cooler than most such days then, red = warmer. Canvas, 1 px per day.
   */
  import { DIVERGING, MUTED, INK, PAGE } from '$lib/palette.js';
  import { MONTHS } from '$lib/dates.js';
  import { DOY_MONTH_STARTS, doyToMonthDay, rankLut, yearMean } from '$lib/ranks.js';

  let { ranks, element = 'tmin', from = 1951, to = null, label = '', compact = false, rowPx = 3, smooth = 1 } = $props();
  const LUT = rankLut(DIVERGING);
  const pageRgb = [250, 247, 242];
  let canvas = $state(null);
  let hover = $state(null);
  let y0 = $derived(Math.max(from, ranks.y0));
  let y1 = $derived(Math.min(to ?? ranks.y0 + ranks.ny - 1, ranks.y0 + ranks.ny - 1));
  let nRows = $derived(y1 - y0 + 1);

  $effect(() => {
    if (!canvas || !ranks) return;
    const a = ranks[element];
    const ctx = canvas.getContext('2d');
    canvas.width = 366;
    canvas.height = nRows;
    const img = ctx.createImageData(366, nRows);
    const half = Math.floor(smooth / 2);
    for (let r = 0; r < nRows; r++) {
      const row = y0 - ranks.y0 + r;
      for (let d = 0; d < 366; d++) {
        let v = a[row * 366 + d];
        if (half > 0 && v !== 255) {
          let sum = 0, k = 0;
          for (let j = -half; j <= half; j++) {
            const q = a[row * 366 + ((d + j + 366) % 366)];
            if (q !== 255) { sum += q; k++; }
          }
          v = Math.round(sum / k);
        }
        const c = v === 255 ? pageRgb : LUT[v];
        const o = (r * 366 + d) * 4;
        img.data[o] = c[0]; img.data[o + 1] = c[1]; img.data[o + 2] = c[2]; img.data[o + 3] = 255;
      }
    }
    ctx.putImageData(img, 0, 0);
  });
  const onmove = (e) => {
    const b = e.currentTarget.getBoundingClientRect();
    const d = Math.floor(((e.clientX - b.left) / b.width) * 366);
    const r = Math.floor(((e.clientY - b.top) / b.height) * nRows);
    if (d < 0 || d > 365 || r < 0 || r >= nRows) { hover = null; return; }
    const v = ranks[element][(y0 - ranks.y0 + r) * 366 + d];
    const md = doyToMonthDay(d);
    hover = { year: y0 + r, date: `${MONTHS[md.month]} ${md.day}`, v: v === 255 ? null : v };
  };
  let decades = $derived.by(() => { const out = []; for (let y = Math.ceil(y0 / 10) * 10; y <= y1; y += 10) out.push(y); return out; });
  let lastMean = $derived.by(() => {
    const v = []; for (let y = y1 - 9; y <= y1; y++) { const m = yearMean(ranks, element, y); if (m != null) v.push(m); }
    return v.length ? v.reduce((s, q) => s + q, 0) / v.length : null;
  });
</script>

<div class="hm" class:compact>
  {#if label}<div class="head"><span class="lbl">{label}</span>{#if lastMean != null}<span class="small muted">typical {element === 'tmin' ? 'night' : 'day'} now: {Math.round(lastMean)}th percentile</span>{/if}</div>{/if}
  <div class="grid" style="grid-template-columns: {compact ? 28 : 40}px 1fr;">
    <div class="years" style="height:{nRows * rowPx}px">
      {#each decades as y (y)}
        <span style="top:{((y - y0) / nRows) * 100}%">{compact ? "'" + String(y).slice(2) : y}</span>
      {/each}
    </div>
    <canvas bind:this={canvas} style="height:{nRows * rowPx}px" onpointermove={onmove} onpointerleave={() => (hover = null)} aria-label={label}></canvas>
    <div></div>
    <div class="months">
      {#each MONTHS as m, i (m)}
        <span style="left:{(DOY_MONTH_STARTS[i] / 366) * 100}%">{compact ? m[0] : m}</span>
      {/each}
    </div>
  </div>
  {#if !compact}
    <div class="tip small">
      {#if hover}
        <b>{hover.date}, {hover.year}</b>: {hover.v == null ? 'no reading' : `${element === 'tmin' ? 'low' : 'high'} at the ${hover.v}th percentile of 1951–80 ${element === 'tmin' ? 'nights' : 'days'} for this date`}
      {:else}
        One row per year (top = {y0}, bottom = {y1}), one column per day{smooth > 1 ? `, each a ${smooth}-day mean` : ''}. Blue: cooler than most {element === 'tmin' ? 'nights' : 'days'} at that date in 1951–1980; red: warmer than most.
      {/if}
    </div>
  {/if}
</div>

<style>
  .head {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 0.6rem;
    flex-wrap: wrap;
    margin-bottom: 0.25rem;
  }
  .head .lbl {
    font-size: 0.9rem;
    font-weight: 650;
    color: #1f1b16;
  }
  .compact .head {
    flex-direction: column;
    align-items: flex-start;
    gap: 0;
  }
  .compact .head .lbl {
    font-size: 0.85rem;
  }
  .grid {
    display: grid;
    gap: 0 4px;
  }
  canvas {
    width: 100%;
    display: block;
    image-rendering: pixelated;
    cursor: crosshair;
    border: 1px solid #e8e1d5;
  }
  .years {
    position: relative;
    font-size: 10px;
    color: #898781;
  }
  .years span {
    position: absolute;
    right: 0;
    transform: translateY(-50%);
  }
  .months {
    position: relative;
    height: 14px;
    font-size: 10px;
    color: #898781;
  }
  .months span {
    position: absolute;
  }
</style>
