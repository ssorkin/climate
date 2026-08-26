"""What NOAA's homogenization says about a USHCN station.

USHCN v2.5 publishes each station's raw monthly means and a fully adjusted version
(FLs.52j: time-of-observation + pairwise homogenization + infilling). The difference
adj - raw is a step function whose jumps are the changes NOAA detected. We report:

- breaks: years where the annual mean offset moved by >= MIN_SHIFT_C in either element
  (two-step transitions across adjacent years are merged), with the size of the shift
- annual: per-year mean offsets, and hot-day / warm-night counts recomputed after
  applying the monthly offsets to the daily values — an *estimate* of what the
  homogenized daily record would count, not an official NOAA product
"""

from __future__ import annotations

from itertools import pairwise

import polars as pl

from climate.analysis.metrics import f_whole_expr

MIN_SHIFT_C = 0.25


def offsets(ush: pl.DataFrame, sid: str) -> pl.DataFrame | None:
    """Monthly (adj - raw) offsets in °C for one station: year, month, tmax_off, tmin_off."""
    s = ush.filter(pl.col("id") == sid)
    if s.is_empty():
        return None
    wide = s.pivot(on=["element", "kind"], index=["year", "month"], values="value_c")
    cols = {c for c in wide.columns}
    need = {'{"TMAX","raw"}', '{"TMAX","adj"}', '{"TMIN","raw"}', '{"TMIN","adj"}'}
    if not need <= cols:
        return None
    return wide.select(
        "year",
        "month",
        (pl.col('{"TMAX","adj"}') - pl.col('{"TMAX","raw"}')).alias("tmax_off"),
        (pl.col('{"TMIN","adj"}') - pl.col('{"TMIN","raw"}')).alias("tmin_off"),
    ).sort(["year", "month"])


def annual_offsets(off: pl.DataFrame) -> pl.DataFrame:
    return (
        off.group_by("year").agg(pl.col("tmax_off").mean(), pl.col("tmin_off").mean()).sort("year")
    )


def breaks(ann: pl.DataFrame, min_shift: float = MIN_SHIFT_C) -> list[dict]:
    """Years where the annual (adj - raw) offset moves by >= min_shift in either element.

    A transition spread over two adjacent years *in the same element* (the adjustment
    ramps through a partial year) is merged into one break dated at the later year.
    """
    out: list[dict] = []
    rows = ann.to_dicts()
    for prev, cur in pairwise(rows):
        dx = (cur["tmax_off"] or 0) - (prev["tmax_off"] or 0)
        dn = (cur["tmin_off"] or 0) - (prev["tmin_off"] or 0)
        big_x, big_n = abs(dx) >= min_shift, abs(dn) >= min_shift
        if not (big_x or big_n):
            continue
        # The raw series moved by -d relative to neighbors (the adjustment cancels it).
        entry = {"year": cur["year"], "tmax_c": round(-dx, 2) + 0.0, "tmin_c": round(-dn, 2) + 0.0}
        last = out[-1] if out else None
        same_element = last is not None and (
            (big_x and abs(last["tmax_c"]) >= min_shift)
            or (big_n and abs(last["tmin_c"]) >= min_shift)
        )
        if last is not None and cur["year"] - last["year"] <= 1 and same_element:
            last["tmax_c"] = round(last["tmax_c"] + entry["tmax_c"], 2) + 0.0
            last["tmin_c"] = round(last["tmin_c"] + entry["tmin_c"], 2) + 0.0
            last["year"] = cur["year"]
        else:
            out.append(entry)
    return out


def adjusted_counts(daily: pl.DataFrame, off: pl.DataFrame, annual: pl.DataFrame) -> pl.DataFrame:
    """Per-year hot_95 / warm_70 after adding each month's offset to the daily values."""
    d = daily.with_columns(
        pl.col("date").dt.year().alias("year"), pl.col("date").dt.month().alias("month")
    )
    o = off.with_columns(
        (pl.col("tmax_off") * 10).round().cast(pl.Int32).alias("ox"),
        (pl.col("tmin_off") * 10).round().cast(pl.Int32).alias("on"),
    ).select("year", "month", "ox", "on")
    d = d.join(o, on=["year", "month"], how="left").with_columns(
        (pl.col("tmax") + pl.col("ox")).alias("tmax_adj"),
        (pl.col("tmin") + pl.col("on")).alias("tmin_adj"),
    )
    g = (
        d.group_by("year")
        .agg(
            (f_whole_expr(pl.col("tmax_adj")) >= 95).sum().cast(pl.Int32).alias("hot_95_adj"),
            (f_whole_expr(pl.col("tmin_adj")) >= 70).sum().cast(pl.Int32).alias("warm_70_adj"),
            pl.col("ox").is_not_null().all().alias("has_off"),
        )
        .sort("year")
    )
    return (
        annual.select("year", "complete_tmax", "complete_tmin")
        .join(g, on="year", how="left")
        .with_columns(
            pl.when(pl.col("complete_tmax") & pl.col("has_off"))
            .then(pl.col("hot_95_adj"))
            .otherwise(None)
            .alias("hot_95_adj"),
            pl.when(pl.col("complete_tmin") & pl.col("has_off"))
            .then(pl.col("warm_70_adj"))
            .otherwise(None)
            .alias("warm_70_adj"),
        )
        .drop("has_off", "complete_tmax", "complete_tmin")
    )
