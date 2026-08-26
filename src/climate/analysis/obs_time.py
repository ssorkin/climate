"""Observation-time segments: when did this station read its thermometer?"""

from __future__ import annotations

import polars as pl


def segments(daily: pl.DataFrame, col: str = "obs_tmax", min_days: int = 0) -> list[dict]:
    """Run-length encode the observation time over dates with a valid reading.

    Returns [{from, to, hhmm, days}]. Blank hhmm means NOAA has no observation time
    for that period (common for airport stations, which use calendar days).
    """
    d = daily.filter(pl.col("tmax").is_not_null()).select("date", pl.col(col).fill_null(""))
    if d.is_empty():
        return []
    out: list[dict] = []
    cur = None
    for row in d.iter_rows():
        dt, hhmm = row
        if cur is None or hhmm != cur["hhmm"]:
            if cur is not None:
                out.append(cur)
            cur = {"from": dt, "to": dt, "hhmm": hhmm, "days": 1}
        else:
            cur["to"] = dt
            cur["days"] += 1
    out.append(cur)
    if min_days > 0:
        merged: list[dict] = []
        for seg in out:
            if merged and seg["days"] < min_days:
                merged[-1]["to"] = seg["to"]
                merged[-1]["days"] += seg["days"]
                merged[-1]["mixed"] = True
            elif merged and merged[-1]["hhmm"] == seg["hhmm"]:
                merged[-1]["to"] = seg["to"]
                merged[-1]["days"] += seg["days"]
            else:
                merged.append(dict(seg))
        out = merged
    return out
