#!/usr/bin/env python3
"""Social card (1200x630) for the heat-wave story, drawn from the export so its numbers
stay current: headline, the story station's every-heat-wave chart, the three pooled
numbers. Writes site/static/og/la-heat-waves.svg and, when a headless Chromium is
available (Playwright's chrome-headless-shell or $CHROME_HEADLESS), the .png that
og:image points at. The PNG is committed, so a build without Chromium keeps the last one.

Usage: uv run python scripts/og_card.py [--no-png]
"""

from __future__ import annotations

import glob
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "site" / "static" / "data"
OUT = ROOT / "site" / "static" / "og"
W, H = 1200, 630
PAGE, INK, INK2, MUTED, GRID, AXIS = (
    "#faf7f2",
    "#1f1b16",
    "#52514e",
    "#898781",
    "#e8e1d5",
    "#c9c2b6",
)
HEAT, COOL = "#d94f22", "#2a78d6"
FONT = "'Noto Sans', 'Liberation Sans', 'DejaVu Sans', Arial, sans-serif"


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def sgn(v: float, d: int = 1, unit: str = "°") -> str:
    a = f"{abs(v):.{d}f}"
    return ("" if float(a) == 0 else "+" if v >= 0 else "−") + a + unit


def build_svg() -> str:
    hw = json.loads((DATA / "regional" / "la-heatwaves.json").read_text())
    ix = json.loads((DATA / "index.json").read_text())
    story_id = ix["regions"][0].get("story_station")
    stations = hw["stations"]
    st = next((s for s in stations if s["id"] == story_id), None) or next(
        s for s in stations if s["windows"]["baseline"] and s["windows"]["last30"]
    )
    pooled = hw.get("pooled") or {}
    b0, b1 = hw["baseline"]["start"], hw["baseline"]["end"]
    comp = [s for s in stations if s["windows"]["baseline"] and s["windows"]["last30"]]

    def win_mean(win: str, key: str) -> float:
        v = [s["windows"][win][key] for s in comp if s["windows"][win].get(key) is not None]
        return sum(v) / len(v)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
        f'<rect width="{W}" height="{H}" fill="{PAGE}"/>',
        f'<text x="56" y="86" font-family="{FONT}" font-size="46" font-weight="800" fill="{INK}" letter-spacing="-0.5">Los Angeles heat waves haven’t gotten hotter</text>',
        f'<text x="56" y="140" font-family="{FONT}" font-size="46" font-weight="800" fill="{INK}" letter-spacing="-0.5">at their peak. <tspan fill="{COOL}">Their nights have.</tspan></text>',
        f'<text x="56" y="178" font-family="{FONT}" font-size="19" fill="{INK2}">Every heat wave at {esc(st["short"])} since {st["first_year"]}, from NOAA’s hourly records — its <tspan fill="{COOL}" font-weight="700">coolest night</tspan> up to its <tspan fill="{HEAT}" font-weight="700">hottest afternoon</tspan></text>',
    ]
    # chart area
    cx0, cx1, cy0, cy1 = 100, 1150, 205, 470
    w = st["waves"]
    rows = [
        (w["start"][i], w["peak_f"][i], w["low_f"][i])
        for i in range(len(w["start"]))
        if w["low_f"][i] is not None and int(w["start"][i][:4]) in st["years"]
    ]
    x0, x1 = st["first_year"] - 0.5, st["last_year"] + 0.5
    vals = [v for _, p, lo in rows for v in (p, lo)]
    y0 = (min(vals) // 10) * 10 - 2
    y1 = -(-max(vals) // 10) * 10 + 2
    X = lambda yr: cx0 + (yr - x0) / (x1 - x0) * (cx1 - cx0)
    Y = lambda v: cy1 - (v - y0) / (y1 - y0) * (cy1 - cy0)
    for v in range(int(y0 // 10 * 10 + 10), int(y1) + 1, 10):
        if v < y0:
            continue
        parts.append(
            f'<line x1="{cx0}" x2="{cx1}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="{GRID}"/>'
        )
        parts.append(
            f'<text x="{cx0 - 10}" y="{Y(v) + 5:.1f}" text-anchor="end" font-family="{FONT}" font-size="15" fill="{MUTED}">{v}°</text>'
        )
    for yr in range(int(-(-x0 // 10) * 10), int(x1) + 1, 10):
        parts.append(
            f'<text x="{X(yr):.1f}" y="{cy1 + 26}" text-anchor="middle" font-family="{FONT}" font-size="15" fill="{MUTED}">{yr}</text>'
        )
    for start, peak, low in rows:
        yr, mo = int(start[:4]), int(start[5:7])
        px = X(yr + (mo - 0.5) / 12)
        parts.append(
            f'<line x1="{px:.1f}" x2="{px:.1f}" y1="{Y(peak):.1f}" y2="{Y(low):.1f}" stroke="{AXIS}" stroke-width="1.6"/>'
        )
        parts.append(f'<circle cx="{px:.1f}" cy="{Y(peak):.1f}" r="4" fill="{HEAT}"/>')
        parts.append(f'<circle cx="{px:.1f}" cy="{Y(low):.1f}" r="4" fill="{COOL}"/>')
    for win in ("baseline", "last30"):
        e = st["windows"][win]
        a, b = e["years"]
        for key, col in (("peak_f", HEAT), ("low_f", COOL)):
            parts.append(
                f'<line x1="{X(a) - 3:.1f}" x2="{X(b) + 3:.1f}" y1="{Y(e[key]):.1f}" y2="{Y(e[key]):.1f}" stroke="{col}" stroke-width="4" stroke-linecap="round"/>'
            )
    e0, e1 = st["windows"]["baseline"], st["windows"]["last30"]
    mid = (X(e1["years"][0]) + X(e1["years"][1])) / 2
    halo = 'paint-order="stroke" stroke="{PAGE}" stroke-width="7" stroke-linejoin="round"'
    parts.append(
        f'<text x="{mid:.1f}" y="{Y(e1["peak_f"]) - 14:.1f}" text-anchor="middle" font-family="{FONT}" font-size="17" font-weight="700" fill="{HEAT}" {halo}>hottest afternoon {e0["peak_f"]:.0f}° → {e1["peak_f"]:.0f}°</text>'
    )
    parts.append(
        f'<text x="{mid:.1f}" y="{Y(e1["low_f"]) + 30:.1f}" text-anchor="middle" font-family="{FONT}" font-size="17" font-weight="700" fill="{COOL}" {halo}>coolest night {e0["low_f"]:.0f}° → {e1["low_f"]:.0f}°</text>'
    )
    # pooled numbers
    n = pooled.get("low_f", {}).get("n_stations", len(comp))
    tiles = [
        ("Hottest afternoon", sgn(pooled["peak_f"]["est"]), INK2),
        ("Coolest heat-wave night", sgn(pooled["low_f"]["est"]), COOL),
        (
            "Overnight relief under 70°F",
            f"{win_mean('baseline', 'relief_h'):.1f} h → {win_mean('last30', 'relief_h'):.1f} h",
            COOL,
        ),
    ]
    parts.append(f'<line x1="56" x2="{W - 56}" y1="512" y2="512" stroke="{GRID}"/>')
    for i, (lab, val, col) in enumerate(tiles):
        x = 56 + i * 330
        parts.append(
            f'<text x="{x}" y="546" font-family="{FONT}" font-size="15" fill="{MUTED}" letter-spacing="1" style="text-transform:uppercase">{esc(lab.upper())}</text>'
        )
        parts.append(
            f'<text x="{x}" y="586" font-family="{FONT}" font-size="36" font-weight="800" fill="{col}">{esc(val)}</text>'
        )
    parts.append(
        f'<text x="{W - 56}" y="620" text-anchor="end" font-family="{FONT}" font-size="15" fill="{MUTED}"><tspan font-weight="700" fill="{INK}">climate.</tspan><tspan font-weight="700" fill="{HEAT}">sorkinlabs</tspan><tspan>.com · {n} stations, {b0}–{b1} vs the last 30 summers</tspan></text>'
    )
    parts.append("</svg>")
    return "\n".join(parts)


def chromium() -> str | None:
    if os.environ.get("CHROME_HEADLESS"):
        return os.environ["CHROME_HEADLESS"]
    for pat in (
        "~/.cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell",
        "~/.cache/ms-playwright/chromium-*/chrome-linux/chrome",
    ):
        hits = sorted(glob.glob(os.path.expanduser(pat)))
        if hits:
            return hits[-1]
    for name in ("chromium", "chromium-browser", "google-chrome"):
        if shutil.which(name):
            return shutil.which(name)
    return None


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    svg = build_svg()
    (OUT / "la-heat-waves.svg").write_text(svg)
    if "--no-png" in sys.argv:
        return 0
    chrome = chromium()
    if not chrome:
        print("og_card: no headless Chromium found; keeping the existing PNG", file=sys.stderr)
        return 0
    html = OUT / "la-heat-waves.html"
    html.write_text(
        f'<!doctype html><html><body style="margin:0;background:{PAGE}">{svg}</body></html>'
    )
    png = OUT / "la-heat-waves.png"
    subprocess.run(
        [
            chrome,
            "--headless",
            "--no-sandbox",
            "--disable-gpu",
            "--hide-scrollbars",
            f"--window-size={W},{H}",
            "--force-device-scale-factor=1",
            f"--screenshot={png}",
            html.as_uri(),
        ],
        check=True,
        capture_output=True,
        timeout=120,
    )
    html.unlink()
    print(f"og_card: wrote {png.relative_to(ROOT)} ({png.stat().st_size // 1000} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
