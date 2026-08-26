"""Pure aggregation rules. Input: one station's wide daily frame (from ingest.store).

Columns expected: date, tmax, tmin, prcp (tenths, null when missing or flagged).
Every rule here is mirrored in site/src/lib/metrics.js for live thresholds; keep the
two in sync and covered by tests.
"""

from __future__ import annotations

import calendar
from datetime import UTC, date, datetime

import numpy as np
import polars as pl

# --- units -----------------------------------------------------------------------------


def f_whole(tenths: int) -> int:
    """Whole °F as the observer recorded it, from NOAA's tenths-°C storage.

    US observers record whole °F; NOAA converts to tenths °C and truncates, so 90°F
    is stored as 322 (89.96°F). Integer arithmetic keeps this exact and identical to
    the JS version: floor((t*18 + 3250) / 100).
    """
    return (tenths * 18 + 3250) // 100


def f_whole_expr(col: pl.Expr) -> pl.Expr:
    # Polars integer // is floor division, matching Python for negatives.
    return (col.cast(pl.Int64) * 18 + 3250) // 100


def tenths_to_c(tenths: float | None) -> float | None:
    return None if tenths is None else round(tenths / 10, 1)


def today_utc() -> date:
    return datetime.now(UTC).date()


# --- helpers ---------------------------------------------------------------------------


def _threshold_exprs(cfg: dict) -> list[pl.Expr]:
    """Boolean day-flag columns for every configured threshold."""
    t = cfg["thresholds_f"]
    fmax = f_whole_expr(pl.col("tmax"))
    fmin = f_whole_expr(pl.col("tmin"))
    out = []
    for thr in t["hot_days"]:
        out.append((fmax >= thr).alias(f"hot_{thr}"))
    for thr in t["warm_nights"]:
        out.append((fmin >= thr).alias(f"warm_{thr}"))
    for thr in t["cold_days"]:
        out.append((fmax <= thr).alias(f"coldday_{thr}"))
    for thr in t["cold_nights"]:
        out.append((fmin <= thr).alias(f"coldnight_{thr}"))
    return out


def threshold_columns(cfg: dict) -> dict[str, list[str]]:
    t = cfg["thresholds_f"]
    return {
        "hot_days": [f"hot_{x}" for x in t["hot_days"]],
        "warm_nights": [f"warm_{x}" for x in t["warm_nights"]],
        "cold_days": [f"coldday_{x}" for x in t["cold_days"]],
        "cold_nights": [f"coldnight_{x}" for x in t["cold_nights"]],
    }


def _with_flags(daily: pl.DataFrame, cfg: dict) -> pl.DataFrame:
    return daily.with_columns(
        pl.col("date").dt.year().alias("year"),
        pl.col("date").dt.month().alias("month"),
        pl.col("date").dt.day().alias("day"),
        *_threshold_exprs(cfg),
    )


def _count_exprs(cfg: dict, elem_ok: dict[str, str]) -> list[pl.Expr]:
    """Sum of day flags, nulled when the element's completeness flag is false."""
    cols = threshold_columns(cfg)
    out = []
    for family, names in cols.items():
        elem = "tmax" if family in ("hot_days", "cold_days") else "tmin"
        for n in names:
            out.append(
                pl.when(pl.col(elem_ok[elem]).first())
                .then(pl.col(n).sum())
                .otherwise(None)
                .cast(pl.Int32)
                .alias(n)
            )
    return out


def _extreme_exprs(elem_ok: dict[str, str]) -> list[pl.Expr]:
    def ext(col: str, agg: str, name: str, ok: str) -> list[pl.Expr]:
        val = pl.col(col).max() if agg == "max" else pl.col(col).min()
        when_date = pl.col("date").filter(pl.col(col) == val).first()
        return [
            pl.when(pl.col(ok).first()).then(val).otherwise(None).alias(f"{name}_tenths"),
            pl.when(pl.col(ok).first()).then(when_date).otherwise(None).alias(f"{name}_date"),
        ]

    return [
        *ext("tmax", "max", "hottest", elem_ok["tmax"]),
        *ext("tmin", "max", "warmest_night", elem_ok["tmin"]),
        *ext("tmax", "min", "coldest", elem_ok["tmax"]),
        *ext("tmin", "min", "coldest_night", elem_ok["tmin"]),
    ]


# --- annual -----------------------------------------------------------------------------


def annual_metrics(daily: pl.DataFrame, cfg: dict, today: date | None = None) -> pl.DataFrame:
    """One row per calendar year. Incomplete years carry null metrics, never 0."""
    today = today or today_utc()
    d = _with_flags(daily, cfg)
    frac = cfg["completeness"]["annual_min_frac"]
    jja = cfg["summer_months"]
    ok = {"tmax": "complete_tmax", "tmin": "complete_tmin"}
    jja_ok = {"tmax": "jja_complete_tmax", "tmin": "jja_complete_tmin"}

    years = (
        d.group_by("year")
        .agg(
            pl.col("tmax").is_not_null().sum().cast(pl.Int32).alias("days_valid_tmax"),
            pl.col("tmin").is_not_null().sum().cast(pl.Int32).alias("days_valid_tmin"),
        )
        .with_columns(
            pl.col("year")
            .map_elements(lambda y: 366 if calendar.isleap(y) else 365, return_dtype=pl.Int32)
            .alias("days_in_year")
        )
        .with_columns(
            (pl.col("year") >= today.year).alias("partial"),
        )
        .with_columns(
            (
                (pl.col("days_valid_tmax") >= (pl.col("days_in_year") * frac).ceil())
                & ~pl.col("partial")
            ).alias("complete_tmax"),
            (
                (pl.col("days_valid_tmin") >= (pl.col("days_in_year") * frac).ceil())
                & ~pl.col("partial")
            ).alias("complete_tmin"),
        )
    )
    d = d.join(years, on="year")

    full = d.group_by("year").agg(
        pl.when(pl.col("complete_tmax").first())
        .then(pl.col("tmax").mean() / 10)
        .otherwise(None)
        .alias("tmax_mean_c"),
        pl.when(pl.col("complete_tmin").first())
        .then(pl.col("tmin").mean() / 10)
        .otherwise(None)
        .alias("tmin_mean_c"),
        *_count_exprs(cfg, {"tmax": "complete_tmax", "tmin": "complete_tmin"}),
        *_extreme_exprs(ok),
    )

    n_jja = sum(calendar.monthrange(2001, m)[1] for m in jja)
    summer = (
        d.filter(pl.col("month").is_in(jja))
        .group_by("year")
        .agg(
            pl.col("tmax").is_not_null().sum().cast(pl.Int32).alias("jja_days_valid_tmax"),
            pl.col("tmin").is_not_null().sum().cast(pl.Int32).alias("jja_days_valid_tmin"),
            pl.col("partial").first(),
            pl.col("tmax").mean().alias("_tmax"),
            pl.col("tmin").mean().alias("_tmin"),
            *[pl.col(c).sum().cast(pl.Int32).alias(c) for c in _jja_cols(cfg)],
        )
        .with_columns(
            (
                (pl.col("jja_days_valid_tmax") >= int(np.ceil(n_jja * frac))) & ~pl.col("partial")
            ).alias("jja_complete_tmax"),
            (
                (pl.col("jja_days_valid_tmin") >= int(np.ceil(n_jja * frac))) & ~pl.col("partial")
            ).alias("jja_complete_tmin"),
        )
        .with_columns(
            pl.when(pl.col("jja_complete_tmax"))
            .then(pl.col("_tmax") / 10)
            .otherwise(None)
            .alias("jja_tmax_mean_c"),
            pl.when(pl.col("jja_complete_tmin"))
            .then(pl.col("_tmin") / 10)
            .otherwise(None)
            .alias("jja_tmin_mean_c"),
            *[
                pl.when(pl.col(jja_ok["tmax" if c.startswith("hot") else "tmin"]))
                .then(pl.col(c))
                .otherwise(None)
                .alias(f"jja_{c}")
                for c in _jja_cols(cfg)
            ],
        )
        .drop("_tmax", "_tmin", "partial", *_jja_cols(cfg))
    )

    out = years.join(full, on="year", how="left").join(summer, on="year", how="left")
    return out.sort("year")


def _jja_cols(cfg: dict) -> list[str]:
    cols = threshold_columns(cfg)
    return cols["hot_days"] + cols["warm_nights"]


# --- monthly ----------------------------------------------------------------------------


def monthly_metrics(daily: pl.DataFrame, cfg: dict, today: date | None = None) -> pl.DataFrame:
    today = today or today_utc()
    d = _with_flags(daily, cfg)
    min_days = cfg["completeness"]["monthly_min_days"]
    ok = {"tmax": "complete_tmax", "tmin": "complete_tmin"}
    counts = (
        d.group_by(["year", "month"])
        .agg(
            pl.col("tmax").is_not_null().sum().cast(pl.Int32).alias("days_valid_tmax"),
            pl.col("tmin").is_not_null().sum().cast(pl.Int32).alias("days_valid_tmin"),
        )
        .with_columns(
            pl.struct(["year", "month"])
            .map_elements(
                lambda s: calendar.monthrange(s["year"], s["month"])[1], return_dtype=pl.Int32
            )
            .alias("days_in_month")
        )
        .with_columns(
            (
                (pl.col("year") == today.year) & (pl.col("month") == today.month)
                | (pl.col("year") > today.year)
            ).alias("partial")
        )
        .with_columns(
            (
                (pl.col("days_valid_tmax") >= pl.min_horizontal(min_days, pl.col("days_in_month")))
                & ~pl.col("partial")
            ).alias("complete_tmax"),
            (
                (pl.col("days_valid_tmin") >= pl.min_horizontal(min_days, pl.col("days_in_month")))
                & ~pl.col("partial")
            ).alias("complete_tmin"),
        )
    )
    d = d.join(counts, on=["year", "month"])
    agg = d.group_by(["year", "month"]).agg(
        pl.when(pl.col("complete_tmax").first())
        .then(pl.col("tmax").mean() / 10)
        .otherwise(None)
        .alias("tmax_mean_c"),
        pl.when(pl.col("complete_tmin").first())
        .then(pl.col("tmin").mean() / 10)
        .otherwise(None)
        .alias("tmin_mean_c"),
        *_count_exprs(cfg, ok),
        *_extreme_exprs(ok),
    )
    return counts.join(agg, on=["year", "month"], how="left").sort(["year", "month"])


# --- cold season (Jul -> Jun, labeled by the January year) ------------------------------


def cold_season_metrics(daily: pl.DataFrame, cfg: dict, today: date | None = None) -> pl.DataFrame:
    today = today or today_utc()
    start_month = cfg["cold_season"]["start_month"]
    frac = cfg["completeness"]["annual_min_frac"]
    d = _with_flags(daily, cfg).with_columns(
        pl.when(pl.col("month") >= start_month)
        .then(pl.col("year") + 1)
        .otherwise(pl.col("year"))
        .alias("season")
    )
    first_season = d["season"].min()
    cur_season = today.year + 1 if today.month >= start_month else today.year
    cols = threshold_columns(cfg)
    night_cols = cols["cold_nights"]
    day_cols = cols["cold_days"]
    out = (
        d.group_by("season")
        .agg(
            pl.col("tmax").is_not_null().sum().cast(pl.Int32).alias("days_valid_tmax"),
            pl.col("tmin").is_not_null().sum().cast(pl.Int32).alias("days_valid_tmin"),
            *[pl.col(c).sum().cast(pl.Int32).alias(c) for c in night_cols + day_cols],
            pl.col("tmin").min().alias("coldest_night_tenths"),
            pl.col("date").filter(pl.col("tmin") == pl.col("tmin").min()).first().alias("_cn_date"),
            pl.col("tmax").min().alias("coldest_tenths"),
            pl.col("date").filter(pl.col("tmax") == pl.col("tmax").min()).first().alias("_cd_date"),
        )
        .with_columns(
            pl.col("season")
            .map_elements(lambda y: 366 if calendar.isleap(y) else 365, return_dtype=pl.Int32)
            .alias("days_in_season"),
            (pl.col("season") >= cur_season).alias("partial"),
            (pl.col("season") == first_season).alias("first_partial"),
        )
        .with_columns(
            (
                (pl.col("days_valid_tmin") >= (pl.col("days_in_season") * frac).ceil())
                & ~pl.col("partial")
            ).alias("complete_tmin"),
            (
                (pl.col("days_valid_tmax") >= (pl.col("days_in_season") * frac).ceil())
                & ~pl.col("partial")
            ).alias("complete_tmax"),
        )
    )
    out = out.with_columns(
        *[
            pl.when(pl.col("complete_tmin")).then(pl.col(c)).otherwise(None).alias(c)
            for c in night_cols
        ],
        *[
            pl.when(pl.col("complete_tmax")).then(pl.col(c)).otherwise(None).alias(c)
            for c in day_cols
        ],
        pl.when(pl.col("complete_tmin"))
        .then(pl.col("coldest_night_tenths"))
        .otherwise(None)
        .alias("coldest_night_tenths"),
        pl.when(pl.col("complete_tmin"))
        .then(pl.col("_cn_date"))
        .otherwise(None)
        .alias("coldest_night_date"),
        pl.when(pl.col("complete_tmax"))
        .then(pl.col("coldest_tenths"))
        .otherwise(None)
        .alias("coldest_tenths"),
        pl.when(pl.col("complete_tmax"))
        .then(pl.col("_cd_date"))
        .otherwise(None)
        .alias("coldest_date"),
    ).drop("_cn_date", "_cd_date", "first_partial")
    return out.sort("season")


# --- decades ----------------------------------------------------------------------------


def decade_means(annual: pl.DataFrame, cfg: dict, cold: pl.DataFrame | None = None) -> pl.DataFrame:
    """Per-decade means over complete years only; decades with too few years are null."""
    min_years = cfg["completeness"]["decade_min_years"]
    cols = threshold_columns(cfg)
    tmax_cols = ["tmax_mean_c", *cols["hot_days"], *cols["cold_days"]]
    tmin_cols = ["tmin_mean_c", *cols["warm_nights"], *cols["cold_nights"]]
    a = annual.with_columns((pl.col("year") // 10 * 10).alias("decade"))
    g = a.group_by("decade").agg(
        pl.col("complete_tmax").sum().cast(pl.Int32).alias("n_years_tmax"),
        pl.col("complete_tmin").sum().cast(pl.Int32).alias("n_years_tmin"),
        *[pl.col(c).mean().alias(c) for c in tmax_cols + tmin_cols],
    )
    g = g.with_columns(
        *[
            pl.when(pl.col("n_years_tmax") >= min_years).then(pl.col(c)).otherwise(None).alias(c)
            for c in tmax_cols
        ],
        *[
            pl.when(pl.col("n_years_tmin") >= min_years).then(pl.col(c)).otherwise(None).alias(c)
            for c in tmin_cols
        ],
    )
    g = g.with_columns(
        (pl.max_horizontal("n_years_tmax", "n_years_tmin") < 10).alias("partial"),
    )
    if cold is not None:
        c = cold.with_columns((pl.col("season") // 10 * 10).alias("decade"))
        cg = c.group_by("decade").agg(
            pl.col("complete_tmin").sum().cast(pl.Int32).alias("n_seasons"),
            *[pl.col(x).mean().alias(f"season_{x}") for x in cols["cold_nights"]],
        )
        cg = cg.with_columns(
            *[
                pl.when(pl.col("n_seasons") >= min_years)
                .then(pl.col(f"season_{x}"))
                .otherwise(None)
                .alias(f"season_{x}")
                for x in cols["cold_nights"]
            ]
        )
        g = g.join(cg, on="decade", how="left")
    return g.sort("decade")


# --- records ----------------------------------------------------------------------------

RECORD_KINDS = {
    "record_high": ("tmax", "max"),  # hottest day for that calendar date
    "record_warm_night": ("tmin", "max"),  # warmest night
    "record_low": ("tmin", "min"),  # coldest night
    "record_cold_day": ("tmax", "min"),  # coldest daytime high
}


def records(daily: pl.DataFrame, cfg: dict) -> pl.DataFrame:
    """Per-day record flags: a value beats every prior year on the same calendar date,
    and that date already had >= record_min_prior_years valid prior years."""
    min_prior = cfg["completeness"]["record_min_prior_years"]
    d = daily.select("date", "tmax", "tmin").with_columns(
        pl.col("date").dt.year().alias("year"),
        pl.col("date").dt.month().alias("month"),
        pl.col("date").dt.day().alias("day"),
    )
    d = d.sort(["month", "day", "year"])
    exprs = []
    for name, (col, agg) in RECORD_KINDS.items():
        over = ["month", "day"]
        prior_n = pl.col(col).is_not_null().cast(pl.Int32).cum_sum().shift(1).over(over)
        cum = pl.col(col).cum_max() if agg == "max" else pl.col(col).cum_min()
        prior = cum.shift(1).over(over)
        cond = (pl.col(col) > prior) if agg == "max" else (pl.col(col) < prior)
        exprs.append(
            (pl.col(col).is_not_null() & (prior_n >= min_prior) & cond.fill_null(False)).alias(name)
        )
        exprs.append(
            (
                pl.col(col).is_not_null()
                & (prior_n >= min_prior)
                & (pl.col(col) == prior).fill_null(False)
            ).alias(f"{name}_tie")
        )
    return d.with_columns(exprs).sort("date").drop("month", "day")


def record_counts(rec: pl.DataFrame, annual: pl.DataFrame) -> pl.DataFrame:
    kinds = list(RECORD_KINDS)
    c = rec.group_by("year").agg(
        *[pl.col(k).sum().cast(pl.Int32).alias(f"{k}s") for k in kinds],
        *[pl.col(f"{k}_tie").sum().cast(pl.Int32).alias(f"{k}_ties") for k in kinds],
    )
    return annual.select("year").join(c, on="year", how="left").sort("year")


# --- daily climatology (366-day calendar) -----------------------------------------------


def doy366(month: int, day: int) -> int:
    """Day-of-year in a leap-year calendar (Feb 29 = 60), so every date has a fixed slot."""
    return date(2000, month, day).timetuple().tm_yday


def doy_climatology(daily: pl.DataFrame, cfg: dict) -> pl.DataFrame:
    b0, b1 = cfg["baseline"]["start"], cfg["baseline"]["end"]
    w = cfg["doy_window_days"]
    d = daily.select("date", "tmax", "tmin").with_columns(
        pl.col("date").dt.year().alias("year"),
        pl.struct(["date"])
        .map_elements(lambda s: doy366(s["date"].month, s["date"].day), return_dtype=pl.Int32)
        .alias("doy"),
    )
    base = d.filter((pl.col("year") >= b0) & (pl.col("year") <= b1))
    doy = base["doy"].to_numpy()
    tmax = base["tmax"].to_numpy().astype(float)
    tmin = base["tmin"].to_numpy().astype(float)
    rows = []
    for k in range(1, 367):
        dist = np.abs(doy - k)
        dist = np.minimum(dist, 366 - dist)
        sel = dist <= w
        x = tmax[sel]
        x = x[~np.isnan(x)]
        y = tmin[sel]
        y = y[~np.isnan(y)]
        row = {"doy": k}
        for name, arr in (("tmax", x), ("tmin", y)):
            if len(arr) >= 10:
                p10, p50, p90 = np.percentile(arr, [10, 50, 90])
                row[f"{name}_p10"] = float(p10) / 10
                row[f"{name}_p50"] = float(p50) / 10
                row[f"{name}_p90"] = float(p90) / 10
            else:
                row[f"{name}_p10"] = row[f"{name}_p50"] = row[f"{name}_p90"] = None
        rows.append(row)
    schema = {"doy": pl.Int32}
    for name in ("tmax", "tmin"):
        for q in ("p10", "p50", "p90"):
            schema[f"{name}_{q}"] = pl.Float64
    clim = pl.DataFrame(rows, schema=schema)

    # All-time per-date extremes (no window), with the year they happened.
    def ext(col: str, agg: str, name: str) -> pl.DataFrame:
        s = d.filter(pl.col(col).is_not_null()).sort(
            [col, "year"], descending=[agg == "max", False]
        )
        return s.group_by("doy").agg(
            pl.col(col).first().alias(f"{name}_tenths"),
            pl.col("year").first().alias(f"{name}_year"),
        )

    for col, agg, name in (
        ("tmax", "max", "rec_high"),
        ("tmin", "min", "rec_low"),
        ("tmin", "max", "rec_warm_night"),
        ("tmax", "min", "rec_cold_day"),
    ):
        clim = clim.join(ext(col, agg, name), on="doy", how="left")
    return clim.sort("doy")


# --- summer to date -------------------------------------------------------------------


def summer_to_date(daily: pl.DataFrame, cfg: dict, today: date | None = None) -> dict:
    """Same Jun 1 -> `through` window for every year, so a partial summer compares fairly."""
    today = today or today_utc()
    months = cfg["summer_months"]
    frac = cfg["completeness"]["annual_min_frac"]
    m0, m1 = months[0], months[-1]
    valid = daily.filter(pl.col("tmax").is_not_null() | pl.col("tmin").is_not_null())
    if valid.is_empty():
        return {}
    last = valid["date"].max()
    ref_year = last.year
    season_start = date(ref_year, m0, 1)
    season_end = date(ref_year, m1, calendar.monthrange(ref_year, m1)[1])
    if last < season_start:
        ref_year -= 1
        season_end = date(ref_year, m1, calendar.monthrange(ref_year, m1)[1])
        through = season_end
    else:
        through = min(last, season_end)
    window_days = (through - date(through.year, m0, 1)).days + 1
    thr_hot = cfg["thresholds_f"]["hot_days"]
    thr_warm = cfg["thresholds_f"]["warm_nights"]
    d = _with_flags(daily, cfg).filter(
        (pl.col("month") > m0) | ((pl.col("month") == m0) & (pl.col("day") >= 1))
    )
    d = d.filter(
        (pl.col("month") < through.month)
        | ((pl.col("month") == through.month) & (pl.col("day") <= through.day))
    ).filter(pl.col("month") >= m0)
    g = (
        d.group_by("year")
        .agg(
            pl.col("tmax").is_not_null().sum().cast(pl.Int32).alias("days_valid_tmax"),
            pl.col("tmin").is_not_null().sum().cast(pl.Int32).alias("days_valid_tmin"),
            (pl.col("tmax").mean() / 10).alias("tmax_mean_c"),
            (pl.col("tmin").mean() / 10).alias("tmin_mean_c"),
            *[pl.col(f"hot_{t}").sum().cast(pl.Int32).alias(f"hot_{t}") for t in thr_hot],
            *[pl.col(f"warm_{t}").sum().cast(pl.Int32).alias(f"warm_{t}") for t in thr_warm],
        )
        .sort("year")
    )
    need = int(np.ceil(window_days * frac))
    g = g.with_columns(
        (pl.col("days_valid_tmax") >= need).alias("ok_tmax"),
        (pl.col("days_valid_tmin") >= need).alias("ok_tmin"),
    )
    g = g.with_columns(
        pl.when(pl.col("ok_tmax")).then(pl.col("tmax_mean_c")).otherwise(None).alias("tmax_mean_c"),
        pl.when(pl.col("ok_tmin")).then(pl.col("tmin_mean_c")).otherwise(None).alias("tmin_mean_c"),
        *[
            pl.when(pl.col("ok_tmax")).then(pl.col(f"hot_{t}")).otherwise(None).alias(f"hot_{t}")
            for t in thr_hot
        ],
        *[
            pl.when(pl.col("ok_tmin")).then(pl.col(f"warm_{t}")).otherwise(None).alias(f"warm_{t}")
            for t in thr_warm
        ],
    )
    g = g.with_columns(
        pl.col("tmax_mean_c").rank(method="min", descending=True).cast(pl.Int32).alias("rank_tmax"),
        pl.col("tmin_mean_c").rank(method="min", descending=True).cast(pl.Int32).alias("rank_tmin"),
    )
    return {
        "ref_year": ref_year,
        "through": through,
        "window_days": window_days,
        "months": months,
        "table": g,
    }


# --- trends, anomalies, windows --------------------------------------------------------


def trend(years: np.ndarray, values: np.ndarray, min_nonzero: int = 10) -> dict | None:
    """Theil-Sen slope per decade with 95% CI and a Kendall tau p-value (complete years only).

    Count series that are almost all zeros (e.g. 95°F days at a beach station) make the
    median pairwise slope degenerate, so those return None rather than a misleading 0.0.
    `significant` is False when the CI spans zero or p >= 0.05; the site then says
    "no clear trend" instead of printing a slope.
    """
    from scipy import stats

    mask = ~np.isnan(values)
    x, y = years[mask].astype(float), values[mask].astype(float)
    if len(x) < 10 or np.count_nonzero(y) < min_nonzero:
        return None
    slope, _intercept, lo, hi = stats.theilslopes(y, x, alpha=0.95)
    _tau, p = stats.kendalltau(x, y)

    def dec(v: float) -> float:
        return round(float(v) * 10, 3) + 0.0  # + 0.0 turns -0.0 into 0.0

    lo10, hi10 = dec(lo), dec(hi)
    return {
        "slope_per_decade": dec(slope),
        "ci": [lo10, hi10],
        "p": round(float(p), 4),
        "significant": bool(p < 0.05 and not (lo10 <= 0 <= hi10)),
        "n": len(x),
        "from": int(x.min()),
        "to": int(x.max()),
    }


def window_means(annual: pl.DataFrame, cols: list[str], y0: int, y1: int) -> dict:
    sub = annual.filter((pl.col("year") >= y0) & (pl.col("year") <= y1))
    out = {"years": [y0, y1]}
    for c in cols:
        s = sub[c].drop_nulls()
        out[c] = round(float(s.mean()), 2) if len(s) else None
        out[f"n_{c}"] = len(s)
    return out
