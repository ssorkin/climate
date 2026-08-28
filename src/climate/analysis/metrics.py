"""Pure aggregation rules. Input: one station's wide daily frame (from ingest.store).

Columns expected: date, tmax, tmin, prcp (tenths, null when missing or flagged).
Every rule here is mirrored in site/src/lib/metrics.js for live thresholds; keep the
two in sync and covered by tests.
"""

from __future__ import annotations

import calendar
from datetime import UTC, date, datetime, timedelta

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


def _doy_expr() -> pl.Expr:
    """Leap-year day-of-year slot (Feb 29 = 60) for a date column."""
    return pl.struct(["date"]).map_elements(
        lambda r: doy366(r["date"].month, r["date"].day), return_dtype=pl.Int32
    )


def doy_window_extremes(daily: pl.DataFrame, window: int) -> pl.DataFrame:
    """Per calendar-date slot: the hottest/coldest values ever observed within ±window days."""
    d = daily.select("date", "tmax", "tmin").with_columns(_doy_expr().alias("doy"))
    per = d.group_by("doy").agg(
        pl.col("tmax").max().alias("mx"),
        pl.col("tmax").min().alias("mnx"),
        pl.col("tmin").max().alias("mn"),
        pl.col("tmin").min().alias("mnn"),
    )
    lookup = {r["doy"]: r for r in per.iter_rows(named=True)}
    rows = []
    for k in range(1, 367):
        vals = {"mx": [], "mnx": [], "mn": [], "mnn": []}
        for off in range(-window, window + 1):
            r = lookup.get((k - 1 + off) % 366 + 1)
            if r:
                for key, acc in vals.items():
                    if r[key] is not None:
                        acc.append(r[key])
        rows.append(
            {
                "doy": k,
                "ever_max_tmax": max(vals["mx"]) if vals["mx"] else None,
                "ever_min_tmax": min(vals["mnx"]) if vals["mnx"] else None,
                "ever_max_tmin": max(vals["mn"]) if vals["mn"] else None,
                "ever_min_tmin": min(vals["mnn"]) if vals["mnn"] else None,
            }
        )
    return pl.DataFrame(
        rows,
        schema={
            "doy": pl.Int32,
            "ever_max_tmax": pl.Int32,
            "ever_min_tmax": pl.Int32,
            "ever_max_tmin": pl.Int32,
            "ever_min_tmin": pl.Int32,
        },
    )


def doy_pass_rates(daily: pl.DataFrame, cfg: dict, window: int = 3) -> pl.DataFrame:
    """Per calendar-date slot and threshold: the share of observed days within ±window days
    (across all years) that crossed the threshold — how often this date counts here."""
    d = _with_flags(daily, cfg).with_columns(_doy_expr().alias("doy"))
    names = [c for cols in threshold_columns(cfg).values() for c in cols]
    per = d.group_by("doy").agg(
        pl.col("tmax").is_not_null().sum().alias("n_x"),
        pl.col("tmin").is_not_null().sum().alias("n_n"),
        *[pl.col(c).sum().alias(c) for c in names],
    )
    lookup = {r["doy"]: r for r in per.iter_rows(named=True)}
    rows = []
    for k in range(1, 367):
        acc = {c: 0 for c in names}
        n = {"n_x": 0, "n_n": 0}
        for off in range(-window, window + 1):
            r = lookup.get((k - 1 + off) % 366 + 1)
            if r:
                n["n_x"] += r["n_x"]
                n["n_n"] += r["n_n"]
                for c in names:
                    acc[c] += r[c] or 0
        row = {"doy": k}
        for c in names:
            nn = n["n_x"] if c.startswith(("hot", "coldday")) else n["n_n"]
            row[f"{c}_rate"] = (acc[c] / nn) if nn else None
        rows.append(row)
    return pl.DataFrame(rows, schema={"doy": pl.Int32, **{f"{c}_rate": pl.Float64 for c in names}})


def risk_days(daily: pl.DataFrame, cfg: dict) -> pl.DataFrame:
    """One row per calendar day of the record span. For each threshold:
    `<name>_risk`  — this day is missing AND the threshold has been reached on this calendar
                     date (±doy_window_days) at this station (a missing day that *could* count);
    `<name>_exp`   — if missing, how often this date crosses the threshold here (0..1), i.e.
                     the expected contribution of the missing day to the count."""
    start, end = daily["date"].min(), daily["date"].max()
    start, end = date(start.year, 1, 1), date(end.year, 12, 31)
    full = pl.DataFrame({"date": pl.date_range(start, end, "1d", eager=True)})
    d = full.join(daily.select("date", "tmax", "tmin"), on="date", how="left")
    d = (
        d.with_columns(_doy_expr().alias("doy"))
        .join(doy_window_extremes(daily, cfg["doy_window_days"]), on="doy", how="left")
        .join(doy_pass_rates(daily, cfg), on="doy", how="left")
    )
    t = cfg["thresholds_f"]
    miss_x, miss_n = pl.col("tmax").is_null(), pl.col("tmin").is_null()
    exprs = []

    def add(name: str, missing: pl.Expr, could: pl.Expr) -> None:
        exprs.append((missing & could.fill_null(True)).alias(f"{name}_risk"))
        exprs.append(
            pl.when(missing)
            .then(pl.col(f"{name}_rate").fill_null(1.0))
            .otherwise(0.0)
            .alias(f"{name}_exp")
        )

    for thr in t["hot_days"]:
        add(f"hot_{thr}", miss_x, f_whole_expr(pl.col("ever_max_tmax")) >= thr)
    for thr in t["warm_nights"]:
        add(f"warm_{thr}", miss_n, f_whole_expr(pl.col("ever_max_tmin")) >= thr)
    for thr in t["cold_days"]:
        add(f"coldday_{thr}", miss_x, f_whole_expr(pl.col("ever_min_tmax")) <= thr)
    for thr in t["cold_nights"]:
        add(f"coldnight_{thr}", miss_n, f_whole_expr(pl.col("ever_min_tmin")) <= thr)
    return d.select("date", *exprs).with_columns(
        pl.col("date").dt.year().alias("year"), pl.col("date").dt.month().alias("month")
    )


def risk_columns(cfg: dict) -> list[str]:
    return [f"{c}_risk" for names in threshold_columns(cfg).values() for c in names]


def exp_columns(cfg: dict) -> list[str]:
    return [f"{c}_exp" for names in threshold_columns(cfg).values() for c in names]


def _risk_aggs(cfg: dict) -> list[pl.Expr]:
    return [
        *[pl.col(c).sum().cast(pl.Int32).alias(c) for c in risk_columns(cfg)],
        *[pl.col(c).sum().round(2).alias(c) for c in exp_columns(cfg)],
    ]


# A lower bound is promoted to an exact count when the missing days are expected to add
# fewer than this many days to it (see doy_pass_rates).
EXACT_MAX_EXPECTED = 0.5


def _apply_risk(
    df: pl.DataFrame, cfg: dict, elem_ok: dict[str, str], min_frac: float = 0.5
) -> pl.DataFrame:
    """Promote a lower bound to an exact count when no missing day could have counted and at
    least min_frac of the period was observed. Requires <name>_lb, <name>_risk, days_valid_*,
    days_in_* and partial columns."""
    total = next(c for c in df.columns if c.startswith("days_in_"))
    exprs = []
    for family, names in threshold_columns(cfg).items():
        elem = "tmax" if family in ("hot_days", "cold_days") else "tmin"
        for n in names:
            if f"{n}_lb" not in df.columns:
                continue
            exact = pl.col(elem_ok[elem]) | (
                ((pl.col(f"{n}_risk") == 0) | (pl.col(f"{n}_exp") < EXACT_MAX_EXPECTED))
                & (pl.col(f"days_valid_{elem}") >= (pl.col(total) * min_frac).ceil())
                & ~pl.col("partial")
            )
            exprs.append(pl.when(exact).then(pl.col(f"{n}_lb")).otherwise(None).alias(n))
    return df.with_columns(exprs)


def _with_flags(daily: pl.DataFrame, cfg: dict) -> pl.DataFrame:
    return daily.with_columns(
        pl.col("date").dt.year().alias("year"),
        pl.col("date").dt.month().alias("month"),
        pl.col("date").dt.day().alias("day"),
        *_threshold_exprs(cfg),
    )


def _count_exprs(cfg: dict, elem_ok: dict[str, str]) -> list[pl.Expr]:
    """Sum of day flags, nulled when the element's completeness flag is false — plus the
    unconditional sum as `<name>_lb`: over observed days only, so it is a lower bound on
    the true count when days are missing."""
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
            out.append(pl.col(n).sum().cast(pl.Int32).alias(f"{n}_lb"))
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

    risk = risk_days(daily, cfg).group_by("year").agg(*_risk_aggs(cfg))
    out = (
        years.join(full, on="year", how="left")
        .join(summer, on="year", how="left")
        .join(risk, on="year", how="left")
    )
    out = _apply_risk(out, cfg, ok)
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
    risk = risk_days(daily, cfg).group_by(["year", "month"]).agg(*_risk_aggs(cfg))
    out = counts.join(agg, on=["year", "month"], how="left").join(
        risk, on=["year", "month"], how="left"
    )
    return _apply_risk(out, cfg, ok).sort(["year", "month"])


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
        *[pl.col(c).alias(f"{c}_lb") for c in night_cols + day_cols],
    )
    risk = (
        risk_days(daily, cfg)
        .with_columns(
            pl.when(pl.col("month") >= start_month)
            .then(pl.col("year") + 1)
            .otherwise(pl.col("year"))
            .alias("season")
        )
        .group_by("season")
        .agg(*_risk_aggs(cfg))
    )
    out = out.join(risk, on="season", how="left")
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
    out = _apply_risk(
        out.rename({"days_in_season": "days_in_period"}),
        cfg,
        {"tmax": "complete_tmax", "tmin": "complete_tmin"},
    ).rename({"days_in_period": "days_in_season"})
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


def doy_climatology(
    daily: pl.DataFrame, cfg: dict, baseline: tuple[int, int] | None = None
) -> pl.DataFrame:
    b0, b1 = baseline or (cfg["baseline"]["start"], cfg["baseline"]["end"])
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
                qs = np.percentile(arr, [10, 25, 50, 75, 90])
                for q, v in zip(("p10", "p25", "p50", "p75", "p90"), qs):
                    row[f"{name}_{q}"] = float(v) / 10
            else:
                for q in ("p10", "p25", "p50", "p75", "p90"):
                    row[f"{name}_{q}"] = None
        rows.append(row)
    schema = {"doy": pl.Int32}
    for name in ("tmax", "tmin"):
        for q in ("p10", "p25", "p50", "p75", "p90"):
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


def window_means(
    annual: pl.DataFrame, cols: list[str], y0: int, y1: int, min_n: int | None = None
) -> dict:
    """Means over a window of years; null when fewer than min_n (default: half the
    window) years contribute — a 'last decade' built on one year is not a decade."""
    sub = annual.filter((pl.col("year") >= y0) & (pl.col("year") <= y1))
    need = min_n if min_n is not None else max(3, (y1 - y0 + 1) // 2)
    out = {"years": [y0, y1], "min_n": need}
    for c in cols:
        s = sub[c].drop_nulls()
        out[c] = round(float(s.mean()), 2) if len(s) >= need else None
        out[f"n_{c}"] = len(s)
    return out


# --- outlier years -----------------------------------------------------------------------

OUTLIER_MIN_C = 3.5
OUTLIER_MAD_MULT = 5.0
EARLY_BLOCK_JUMP_C = 3.0


def outlier_years(annual: pl.DataFrame) -> dict[int, str]:
    """Complete years to exclude from every yearly statistic, with the reason:
    - a year whose mean high or low sits more than max(OUTLIER_MIN_C, OUTLIER_MAD_MULT × the
      median absolute residual) off the station's own Theil–Sen trend line;
    - the record's first 5-year block when its mean sits more than EARLY_BLOCK_JUMP_C off the
      next block's (an early-archive artifact, common in 1940–45).
    Almost all such years are archive artifacts: a first year in the wrong units, a
    different feed under the same id."""
    from scipy import stats

    out: dict[int, str] = {}
    for k, label in (("tmax_mean_c", "highs"), ("tmin_mean_c", "lows")):
        a = annual.filter(pl.col(k).is_not_null() & ~pl.col("partial"))
        if a.height < 10:
            continue
        x = a["year"].to_numpy().astype(float)
        y = a[k].to_numpy().astype(float)
        # 1. early-record block test: the first 5-year block far off the next one
        blocks: dict[int, list[float]] = {}
        for yr, v in zip(x, y, strict=True):
            blocks.setdefault(int(yr) // 5 * 5, []).append(v)
        bl = sorted((bk, float(np.mean(v)), len(v)) for bk, v in blocks.items() if len(v) >= 3)
        early: set[int] = set()
        if len(bl) >= 2 and abs(bl[0][1] - bl[1][1]) > EARLY_BLOCK_JUMP_C:
            early = {int(yr) for yr in x if int(yr) // 5 * 5 == bl[0][0]}
            for yr in sorted(early):
                out.setdefault(
                    yr,
                    f"early record: mean daily {label} {bl[0][1] - bl[1][1]:+.1f} °C off the following years",
                )
        # 2. residual test on the rest, against a robust (Theil–Sen) trend line
        keep = np.array([int(v) not in early for v in x])
        if keep.sum() < 10:
            continue
        slope, intercept, _lo, _hi = stats.theilslopes(y[keep], x[keep])
        resid = y[keep] - (slope * x[keep] + intercept)
        mad = float(np.median(np.abs(resid)))
        thr = max(OUTLIER_MIN_C, OUTLIER_MAD_MULT * mad)
        for yr, r in zip(x[keep], resid, strict=True):
            if abs(r) > thr:
                out.setdefault(
                    int(yr), f"mean daily {label} {r:+.1f} °C off this station's trend line"
                )
    return out


def drop_years(df: pl.DataFrame, years: set[int], year_col: str = "year") -> pl.DataFrame:
    """Null every metric of the given years and mark them incomplete (both elements)."""
    if not years:
        return df
    keep = ~pl.col(year_col).is_in(list(years))
    exprs = []
    for c, dt in df.schema.items():
        if c in (year_col, "month", "days_in_year", "days_in_month", "days_in_season", "partial"):
            continue
        if c.startswith(("days_valid", "jja_days_valid")) or c.endswith(("_risk", "_exp")):
            continue
        if dt == pl.Boolean:
            exprs.append(pl.when(keep).then(pl.col(c)).otherwise(False).alias(c))
        else:
            exprs.append(pl.when(keep).then(pl.col(c)).otherwise(None).alias(c))
    return df.with_columns(exprs)


# --- distributional indices (ETCCDI-style) ----------------------------------------------


RANK_MIN_BASELINE = 100  # baseline readings in the window needed to rank a day


def percentile_ranks(
    daily: pl.DataFrame, cfg: dict, baseline: tuple[int, int] | None = None
) -> pl.DataFrame:
    """For every day: where its high / low falls (0–100) within the station's own baseline
    distribution for that calendar date (all baseline readings within ±doy_window_days).

    Rank = share of baseline readings below the value, ties counted half — nonparametric, no
    normality assumed. Under an unchanged climate the annual mean rank sits near 50.
    `baseline` overrides the configured period (a station's own first 30 years, when it has
    no 1951–1980 record).
    """
    b0, b1 = baseline or (cfg["baseline"]["start"], cfg["baseline"]["end"])
    w = cfg["doy_window_days"]
    d = daily.select("date", "tmax", "tmin").with_columns(
        pl.col("date").dt.year().alias("year"), _doy_expr().alias("doy")
    )
    doy_all = d["doy"].to_numpy()
    base_mask = (d["year"].to_numpy() >= b0) & (d["year"].to_numpy() <= b1)
    out = {}
    for el in ("tmax", "tmin"):
        vals = d[el].cast(pl.Float64).fill_null(np.nan).to_numpy()
        rank = np.full(len(vals), np.nan)
        for k in range(1, 367):
            dist = np.abs(doy_all - k)
            dist = np.minimum(dist, 366 - dist)
            ref = vals[base_mask & (dist <= w)]
            ref = np.sort(ref[~np.isnan(ref)])
            if len(ref) < RANK_MIN_BASELINE:
                continue
            sel = (doy_all == k) & ~np.isnan(vals)
            x = vals[sel]
            lo = np.searchsorted(ref, x, side="left")
            hi = np.searchsorted(ref, x, side="right")
            rank[sel] = 100 * (lo + hi) / (2 * len(ref))
        out[f"rank_{el}"] = rank
    return pl.DataFrame({"date": d["date"], **out}).with_columns(
        pl.col("rank_tmax").fill_nan(None), pl.col("rank_tmin").fill_nan(None)
    )


def percentile_indices(
    daily: pl.DataFrame,
    doy: pl.DataFrame,
    annual: pl.DataFrame,
    cfg: dict,
    ranks: pl.DataFrame | None = None,
) -> pl.DataFrame:
    """Per year: TX90p / TN90p / TX10p / TN10p — the share (%) of days whose high / low sits
    above the station's own baseline 90th percentile (or below the 10th) for that calendar
    date — plus the mean diurnal range (DTR, °C) and warm-season (JJA) mean high / low.

    Percentiles come from doy_climatology: baseline years, ±doy_window_days around each
    calendar date. Simplification vs. ETCCDI: a wider window (7 vs 2 days) and no in-base
    bootstrap, so baseline years read a touch above 10% by construction. Years follow the
    same completeness flags as the count metrics; anything else is null.
    """
    d = daily.select("date", "tmax", "tmin").with_columns(
        pl.col("date").dt.year().alias("year"),
        pl.col("date").dt.month().alias("month"),
        _doy_expr().alias("doy"),
    )
    d = d.join(
        doy.select("doy", "tmax_p10", "tmax_p90", "tmin_p10", "tmin_p90"), on="doy", how="left"
    )
    d = d.with_columns(
        (pl.col("tmax") / 10 > pl.col("tmax_p90")).alias("tx90"),
        (pl.col("tmax") / 10 < pl.col("tmax_p10")).alias("tx10"),
        (pl.col("tmin") / 10 > pl.col("tmin_p90")).alias("tn90"),
        (pl.col("tmin") / 10 < pl.col("tmin_p10")).alias("tn10"),
        ((pl.col("tmax") - pl.col("tmin")) / 10).alias("dtr"),
    )
    if ranks is not None:
        d = d.join(ranks, on="date", how="left")
    else:
        d = d.with_columns(
            pl.lit(None, dtype=pl.Float64).alias("rank_tmax"),
            pl.lit(None, dtype=pl.Float64).alias("rank_tmin"),
        )
    jja = cfg["summer_months"]
    g = d.group_by("year").agg(
        pl.col("rank_tmax").mean().alias("rank_tmax"),
        pl.col("rank_tmin").mean().alias("rank_tmin"),
        (100 * pl.col("tx90").filter(pl.col("tmax").is_not_null()).mean()).alias("tx90p"),
        (100 * pl.col("tx10").filter(pl.col("tmax").is_not_null()).mean()).alias("tx10p"),
        (100 * pl.col("tn90").filter(pl.col("tmin").is_not_null()).mean()).alias("tn90p"),
        (100 * pl.col("tn10").filter(pl.col("tmin").is_not_null()).mean()).alias("tn10p"),
        pl.col("dtr").mean().alias("dtr_c"),
        (pl.col("tmax").filter(pl.col("month").is_in(jja)).mean() / 10).alias("jja_tmax_c"),
        (pl.col("tmin").filter(pl.col("month").is_in(jja)).mean() / 10).alias("jja_tmin_c"),
    )
    out = annual.select(
        "year", "complete_tmax", "complete_tmin", "jja_complete_tmax", "jja_complete_tmin"
    ).join(g, on="year", how="left")
    both = pl.col("complete_tmax") & pl.col("complete_tmin")
    return (
        out.with_columns(
            pl.when(pl.col("complete_tmax"))
            .then(pl.col("rank_tmax"))
            .otherwise(None)
            .alias("rank_tmax"),
            pl.when(pl.col("complete_tmin"))
            .then(pl.col("rank_tmin"))
            .otherwise(None)
            .alias("rank_tmin"),
            pl.when(pl.col("complete_tmax")).then(pl.col("tx90p")).otherwise(None).alias("tx90p"),
            pl.when(pl.col("complete_tmax")).then(pl.col("tx10p")).otherwise(None).alias("tx10p"),
            pl.when(pl.col("complete_tmin")).then(pl.col("tn90p")).otherwise(None).alias("tn90p"),
            pl.when(pl.col("complete_tmin")).then(pl.col("tn10p")).otherwise(None).alias("tn10p"),
            pl.when(both).then(pl.col("dtr_c")).otherwise(None).alias("dtr_c"),
            pl.when(pl.col("jja_complete_tmax"))
            .then(pl.col("jja_tmax_c"))
            .otherwise(None)
            .alias("jja_tmax_c"),
            pl.when(pl.col("jja_complete_tmin"))
            .then(pl.col("jja_tmin_c"))
            .otherwise(None)
            .alias("jja_tmin_c"),
        )
        .drop("complete_tmax", "complete_tmin", "jja_complete_tmax", "jja_complete_tmin")
        .sort("year")
    )


# --- heat waves ----------------------------------------------------------------------------


def _season_days(year: int, months: list[int]) -> int:
    return sum(calendar.monthrange(year, m)[1] for m in months)


def warm_season_years(daily: pl.DataFrame, cfg: dict) -> list[int]:
    """Years whose warm-season days (cfg heat_waves.months) are >= annual_min_frac valid for
    *both* the high and the low. Heat waves are only counted in these years."""
    hw = cfg["heat_waves"]
    frac = cfg["completeness"]["annual_min_frac"]
    d = daily.select("date", "tmax", "tmin").with_columns(
        pl.col("date").dt.year().alias("year"), pl.col("date").dt.month().alias("month")
    )
    g = (
        d.filter(pl.col("month").is_in(hw["months"]))
        .group_by("year")
        .agg(
            pl.col("tmax").is_not_null().sum().alias("n_max"),
            pl.col("tmin").is_not_null().sum().alias("n_min"),
        )
    )
    out = []
    for r in g.iter_rows(named=True):
        need = int(np.ceil(frac * _season_days(r["year"], hw["months"])))
        if r["n_max"] >= need and r["n_min"] >= need:
            out.append(int(r["year"]))
    return sorted(out)


def heat_wave_threshold(daily: pl.DataFrame, cfg: dict, years: list[int]) -> int | None:
    """The station's heat-wave threshold in whole °F: the configured percentile of its
    warm-season daily highs over the given complete years (None below min_years)."""
    hw = cfg["heat_waves"]
    if len(years) < hw["min_years"]:
        return None
    d = daily.select("date", "tmax").with_columns(
        pl.col("date").dt.year().alias("year"), pl.col("date").dt.month().alias("month")
    )
    vals = (
        d.filter(pl.col("month").is_in(hw["months"]) & pl.col("year").is_in(years))["tmax"]
        .drop_nulls()
        .to_numpy()
    )
    if len(vals) == 0:
        return None
    return f_whole(int(np.percentile(vals, hw["percentile"])))


def heat_waves(daily: pl.DataFrame, cfg: dict, thr_f: int) -> pl.DataFrame:
    """Every run of >= min_days consecutive calendar days with f_whole(tmax) >= thr_f.

    One row per wave: start, end, year (of the start), days, peak_f (hottest high),
    mean_high_f, low_f (the coolest night *inside* the wave: the lowest low on days 2..n),
    mean_low_f, after_low_f (the low on the day after the run ends, when that day was
    observed). A missing day breaks a run — it is never bridged.
    """
    min_days = cfg["heat_waves"]["min_days"]
    d = daily.select("date", "tmax", "tmin").sort("date")
    dates = d["date"].to_list()
    hi = [f_whole(v) if v is not None else None for v in d["tmax"].to_list()]
    lo = [f_whole(v) if v is not None else None for v in d["tmin"].to_list()]
    rows = []
    i, n = 0, len(dates)
    while i < n:
        if hi[i] is None or hi[i] < thr_f:
            i += 1
            continue
        j = i
        while (
            j + 1 < n
            and hi[j + 1] is not None
            and hi[j + 1] >= thr_f
            and (dates[j + 1] - dates[j]).days == 1
        ):
            j += 1
        days = j - i + 1
        if days >= min_days:
            highs = hi[i : j + 1]
            lows = [v for v in lo[i + 1 : j + 1] if v is not None]
            after = lo[j + 1] if j + 1 < n and (dates[j + 1] - dates[j]).days == 1 else None
            rows.append(
                {
                    "start": dates[i],
                    "end": dates[j],
                    "year": dates[i].year,
                    "days": days,
                    "peak_f": max(highs),
                    "mean_high_f": float(np.mean(highs)),
                    "low_f": min(lows) if lows else None,
                    "mean_low_f": float(np.mean(lows)) if lows else None,
                    "after_low_f": after,
                }
            )
        i = j + 1
    schema = {
        "start": pl.Date,
        "end": pl.Date,
        "year": pl.Int32,
        "days": pl.Int32,
        "peak_f": pl.Int32,
        "mean_high_f": pl.Float64,
        "low_f": pl.Int32,
        "mean_low_f": pl.Float64,
        "after_low_f": pl.Int32,
    }
    return pl.DataFrame(rows, schema=schema)


def heat_wave_relief(hourly: pl.DataFrame, waves: pl.DataFrame, relief_f: int) -> pl.Series:
    """Per wave: hours per night under relief_f, from the hourly readings.

    A night runs 18:00–08:00 local and is labeled by its morning date; nights 2..n of the
    wave count (the same nights as low_f). Hours = share of the night's readings under the
    threshold x 14 h, so 3-hourly years are on the same footing as hourly ones; a night
    needs 5+ readings. Null when the wave has no usable night.
    """
    if waves.is_empty():
        return pl.Series("relief_h", [], dtype=pl.Float64)
    h = hourly.select("date", "hour", "temp").filter(pl.col("temp").is_not_null())
    night = (
        h.with_columns(
            pl.when(pl.col("hour") >= 18)
            .then(pl.col("date") + pl.duration(days=1))
            .when(pl.col("hour") <= 8)
            .then(pl.col("date"))
            .otherwise(None)
            .alias("night"),
            (f_whole_expr(pl.col("temp")) < relief_f).alias("cool"),
        )
        .filter(pl.col("night").is_not_null())
        .group_by("night")
        .agg(pl.len().alias("n"), pl.col("cool").mean().alias("frac"))
        .filter(pl.col("n") >= 5)
    )
    frac = dict(zip(night["night"].to_list(), night["frac"].to_list()))
    out = []
    for s, e in zip(waves["start"].to_list(), waves["end"].to_list()):
        nights = [frac.get(s + timedelta(days=k)) for k in range(1, (e - s).days + 1)]
        nights = [v for v in nights if v is not None]
        out.append(14 * float(np.mean(nights)) if nights else None)
    return pl.Series("relief_h", out, dtype=pl.Float64)


def heat_wave_window(
    waves: pl.DataFrame, daily: pl.DataFrame, cfg: dict, years: list[int], y0: int, y1: int
) -> dict | None:
    """Then/now summary over the complete warm seasons in [y0, y1]: how often, how long,
    how hot, how warm the nights — and the ordinary (non-wave) warm-season high and low for
    the same years, so wave nights can be compared with the nights around them."""
    hw = cfg["heat_waves"]
    yrs = [y for y in years if y0 <= y <= y1]
    if len(yrs) < hw["window_min_years"]:
        return None
    w = waves.filter(pl.col("year").is_in(yrs))
    n = len(yrs)

    def mean_of(col: str) -> float | None:
        if col not in w.columns:
            return None
        v = w[col].drop_nulls()
        return round(float(v.mean()), 2) if v.len() else None

    def spread(col: str) -> dict:
        """Sample sd and count, so a then-vs-now difference can carry a 95% interval
        (waves treated as independent draws)."""
        if col not in w.columns:
            return {f"{col}_sd": None, f"{col}_n": 0}
        v = w[col].drop_nulls()
        sd = round(float(v.std()), 3) if v.len() >= 2 else None
        return {f"{col}_sd": sd, f"{col}_n": int(v.len())}

    # ordinary days: warm-season days in these years that are not inside a wave or the day after
    in_wave: set[date] = set()
    for s, e in zip(w["start"].to_list(), w["end"].to_list()):
        for k in range((e - s).days + 2):
            in_wave.add(s + timedelta(days=k))
    d = daily.select("date", "tmax", "tmin").with_columns(
        pl.col("date").dt.year().alias("year"), pl.col("date").dt.month().alias("month")
    )
    ordinary = d.filter(
        pl.col("month").is_in(hw["months"])
        & pl.col("year").is_in(yrs)
        & ~pl.col("date").is_in(list(in_wave))
    )
    ord_hi = ordinary["tmax"].drop_nulls()
    ord_lo = ordinary["tmin"].drop_nulls()
    per_year = [int(w.filter(pl.col("year") == y).height) for y in yrs]
    return {
        "years": [yrs[0], yrs[-1]],
        "n": n,
        "waves_per_year": round(w.height / n, 2),
        "waves_per_year_sd": round(float(np.std(per_year, ddof=1)), 3) if n >= 2 else None,
        "waves_per_year_n": n,
        "days_per_year": round(float(w["days"].sum()) / n, 2) if w.height else 0.0,
        "mean_days": mean_of("days"),
        "max_days": int(w["days"].max()) if w.height else None,
        "peak_f": mean_of("peak_f"),
        "mean_high_f": mean_of("mean_high_f"),
        "low_f": mean_of("low_f"),
        "mean_low_f": mean_of("mean_low_f"),
        "after_low_f": mean_of("after_low_f"),
        "relief_h": mean_of("relief_h"),
        **spread("days"),
        **spread("peak_f"),
        **spread("low_f"),
        **spread("mean_low_f"),
        **spread("after_low_f"),
        **spread("relief_h"),
        "ordinary_high_f": (
            round(float(np.mean([f_whole(v) for v in ord_hi.to_list()])), 2)
            if ord_hi.len()
            else None
        ),
        "ordinary_low_f": (
            round(float(np.mean([f_whole(v) for v in ord_lo.to_list()])), 2)
            if ord_lo.len()
            else None
        ),
    }
