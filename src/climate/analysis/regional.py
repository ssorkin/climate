"""Regional index with imputation: a latent-variable model over a curated region's stations.

For one metric (e.g. days >= 95°F per year) and a region's stations, each observed
station-year count is modeled as

    y[s, t] ~ NegativeBinomial(mu = exp(c + a[s] + b[t]), alpha)

a[s] is the station's climate (a beach vs. a desert site), b[t] is the shared year effect —
the latent "how hot was this year across the region" variable — and alpha absorbs
overdispersion. Both effect sets carry ridge penalties (a random-effects approximation:
weak on stations, moderate on years) so a year seen only by two zero-count stations
keeps a finite, well-covered estimate. Held-out evaluation lives in evaluate_metric. Fitting uses only exact counts (complete years, or years whose missing
days could not have counted). Then:

- every missing station-year gets a predictive distribution (mean, 5th–95th percentile)
  from exp(a[s] + b[t]) and the NB noise, with parameter uncertainty from the fitted
  covariance;
- the regional series is the mean over ALL stations of observed-or-imputed counts, per
  year, summarized as mean and percentile bands — i.e. "what the average station would
  have counted had every station reported every year", immune to stations coming and
  going, honest about years with few observers (wide bands).
"""

from __future__ import annotations

import numpy as np
import polars as pl

N_DRAWS = 400
SEED = 20260826


LAM_STATION = 0.01  # ridge on station effects (log scale): stations differ a lot, shrink little
LAM_YEAR = 1.0  # ridge on year effects: a year seen by two zero-count stations must stay finite


def _design(s_idx: np.ndarray, y_idx: np.ndarray, n_s: int, n_y: int) -> np.ndarray:
    """[intercept | station one-hots | year one-hots]. Over-parameterized on purpose; the
    ridge penalties make it identifiable (a random-effects approximation)."""
    X = np.zeros((len(s_idx), 1 + n_s + n_y))
    X[:, 0] = 1.0
    X[np.arange(len(s_idx)), 1 + s_idx] = 1.0
    X[np.arange(len(s_idx)), 1 + n_s + y_idx] = 1.0
    return X


def _penalty(n_s: int, n_y: int) -> np.ndarray:
    return np.concatenate([[0.0], np.full(n_s, LAM_STATION), np.full(n_y, LAM_YEAR)])


def _fit(y: np.ndarray, X: np.ndarray, lam: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    """Penalized NB2 regression: minimize -loglik + ½ Σ lam_j β_j², profiling the
    dispersion alpha. Returns (params, covariance = inverse penalized Hessian, alpha)."""
    from scipy.optimize import minimize, minimize_scalar
    from scipy.special import gammaln

    def nll_eta(beta, r):
        eta = X @ beta
        mu = np.exp(np.clip(eta, -20, 7))
        ll = (
            gammaln(y + r)
            - gammaln(r)
            - gammaln(y + 1)
            + r * np.log(r / (r + mu))
            + y * np.log(mu / (r + mu))
        )
        grad = X.T @ ((y - mu) * r / (r + mu)) - lam * beta
        return -(ll.sum() - 0.5 * np.sum(lam * beta**2)), -grad

    def nll_alpha(log_alpha, beta):
        r = 1.0 / np.exp(log_alpha)
        return nll_eta(beta, r)[0]

    beta = np.zeros(X.shape[1])
    beta[0] = np.log(max(y.mean(), 0.05))
    log_alpha = np.log(0.3)
    for _ in range(4):
        r = 1.0 / np.exp(log_alpha)
        res = minimize(
            nll_eta, beta, args=(r,), jac=True, method="L-BFGS-B", options={"maxiter": 500}
        )
        beta = res.x
        log_alpha = minimize_scalar(
            nll_alpha, args=(beta,), bounds=(np.log(1e-3), np.log(20)), method="bounded"
        ).x
    alpha = float(np.exp(log_alpha))
    r = 1.0 / alpha
    mu = np.exp(np.clip(X @ beta, -20, 7))
    w = mu * r * (r + y) / (r + mu) ** 2
    H = X.T @ (X * w[:, None]) + np.diag(lam)
    try:
        cov = np.linalg.inv(H)
    except np.linalg.LinAlgError:
        cov = np.linalg.pinv(H)
    cov = (cov + cov.T) / 2
    return beta, cov, alpha


def _draw_params(params, cov, rng, n=N_DRAWS):
    sd = np.sqrt(np.clip(np.diag(cov), 0, None))
    try:
        draws = rng.multivariate_normal(params, cov, size=n, method="cholesky")
    except np.linalg.LinAlgError:
        draws = params[None, :] + rng.standard_normal((n, len(params))) * sd
    return params[None, :] + np.clip(draws - params[None, :], -2.5 * sd, 2.5 * sd)


def evaluate_metric(
    table: pl.DataFrame, years: list[int], station_ids: list[str], rng: np.random.Generator
) -> dict | None:
    """Held-out evaluation of the model on this metric.

    random: 5 folds, 20% of observed station-years each, held out at random.
    blocks: for each station, one random 10-year run of its observed years held out
            (the shape of real gaps), in 5 rounds.
    Reports MAE/RMSE/bias of the predictive median, coverage of the 90% interval, and the
    same for a station-climatology baseline (the station's mean over the training years).
    """
    obs = table.filter(pl.col("value").is_not_null() & pl.col("year").is_in(years))
    if obs.height < 60:
        return None
    ids = [s for s in station_ids if s in set(obs["id"].to_list())]
    yrs = sorted(set(obs["year"].to_list()))
    si = {s: k for k, s in enumerate(ids)}
    yi = {y: k for k, y in enumerate(yrs)}
    n_s, n_y = len(ids), len(yrs)
    s_all = np.array([si[s] for s in obs["id"].to_list()])
    y_all = np.array([yi[y] for y in obs["year"].to_list()])
    v_all = obs["value"].to_numpy().astype(float)

    lam = _penalty(n_s, n_y)

    def run(test_mask):
        train = ~test_mask
        # every station and year must remain in the training set for its effect to exist
        ok_s = np.isin(s_all[test_mask], s_all[train])
        ok_y = np.isin(y_all[test_mask], y_all[train])
        keep = ok_s & ok_y
        te = np.where(test_mask)[0][keep]
        if not len(te):
            return None
        params, cov, alpha = _fit(v_all[train], _design(s_all[train], y_all[train], n_s, n_y), lam)
        draws = _draw_params(params, cov, rng, 200)
        Xt = _design(s_all[te], y_all[te], n_s, n_y)
        cap = np.array(
            [min(366.0, 1.5 * v_all[train][s_all[train] == s].max() + 5.0) for s in s_all[te]]
        )
        with np.errstate(over="ignore"):
            mu = np.minimum(np.exp(np.clip(Xt @ draws.T, -20, 7)), cap[:, None])
        shape = 1.0 / alpha
        counts = np.minimum(rng.poisson(rng.gamma(shape, mu / shape)), cap[:, None])
        med = np.median(counts, axis=1)
        lo, hi = np.percentile(counts, [5, 95], axis=1)
        truth = v_all[te]
        # baseline: the station's training-set mean
        smean = np.array([v_all[train][s_all[train] == s].mean() for s in s_all[te]])
        return truth, med, lo, hi, smean

    def summarize(parts):
        t = np.concatenate([p[0] for p in parts])
        m = np.concatenate([p[1] for p in parts])
        lo = np.concatenate([p[2] for p in parts])
        hi = np.concatenate([p[3] for p in parts])
        b = np.concatenate([p[4] for p in parts])
        return {
            "n": len(t),
            "mae": round(float(np.mean(np.abs(t - m))), 2),
            "rmse": round(float(np.sqrt(np.mean((t - m) ** 2))), 2),
            "bias": round(float(np.mean(m - t)), 2),
            "coverage90": round(float(np.mean((t >= lo) & (t <= hi))), 3),
            "r2": round(
                float(1 - np.sum((t - m) ** 2) / max(np.sum((t - t.mean()) ** 2), 1e-9)), 3
            ),
            "baseline_mae": round(float(np.mean(np.abs(t - b))), 2),
            "baseline_rmse": round(float(np.sqrt(np.mean((t - b) ** 2))), 2),
            "truth_mean": round(float(t.mean()), 2),
        }

    n = len(v_all)
    # random cells, 5 folds
    perm = rng.permutation(n)
    parts = []
    for f in range(5):
        mask = np.zeros(n, bool)
        mask[perm[f::5]] = True
        r = run(mask)
        if r:
            parts.append(r)
    random_eval = summarize(parts) if parts else None
    # 10-year blocks per station, 5 rounds
    parts = []
    for _round in range(5):
        mask = np.zeros(n, bool)
        for s in range(n_s):
            idx = np.where(s_all == s)[0]
            if len(idx) < 25:
                continue
            idx = idx[np.argsort(y_all[idx])]
            start = rng.integers(0, len(idx) - 10)
            mask[idx[start : start + 10]] = True
        r = run(mask)
        if r:
            parts.append(r)
    block_eval = summarize(parts) if parts else None
    return {"random": random_eval, "blocks": block_eval}


def fit_metric(
    table: pl.DataFrame, years: list[int], station_ids: list[str], rng: np.random.Generator
) -> dict | None:
    """table: columns id, year, value (exact counts only). Returns per-station-year
    predictive summaries and the regional series."""
    obs = table.filter(pl.col("value").is_not_null() & pl.col("year").is_in(years))
    if obs.height < 30 or obs["id"].n_unique() < 2:
        return None
    ids = [s for s in station_ids if s in set(obs["id"].to_list())]
    yrs = sorted(set(obs["year"].to_list()))
    si = {s: k for k, s in enumerate(ids)}
    yi = {y: k for k, y in enumerate(yrs)}
    n_s, n_y = len(ids), len(yrs)

    s_obs = np.array([si[s] for s in obs["id"].to_list()])
    y_obs = np.array([yi[y] for y in obs["year"].to_list()])
    X = _design(s_obs, y_obs, n_s, n_y)
    y = obs["value"].to_numpy().astype(float)

    params, cov, alpha = _fit(y, X, _penalty(n_s, n_y))
    # Parameter draws, each coordinate clipped to ±2.5 sd: with a handful of early
    # observers a year effect can be nearly unidentified, and exp() of an unbounded draw
    # is not a credible count.
    draws = _draw_params(params, cov, rng)

    # Full grid of station × year.
    grid_s = np.repeat(np.arange(n_s), n_y)
    grid_y = np.tile(np.arange(n_y), n_s)
    Xg = _design(grid_s, grid_y, n_s, n_y)
    observed = np.full((n_s, n_y), np.nan)
    for s, yv, v in zip(obs["id"].to_list(), obs["year"].to_list(), y):
        observed[si[s], yi[yv]] = v
    obs_mask = ~np.isnan(observed)

    # Predictive draws for every cell: NB(mu, alpha) via Gamma-Poisson mixture. A station's
    # imputed mean is capped at a plausible ceiling: 1.5× its own record maximum (+5), never
    # more days than a year has.
    with np.errstate(over="ignore"):
        mu_draws = np.exp(np.clip(Xg @ draws.T, -20, 7)).reshape(n_s, n_y, N_DRAWS)
    cap = np.array([min(366.0, 1.5 * np.nanmax(observed[k]) + 5.0) for k in range(n_s)])
    mu_draws = np.minimum(mu_draws, cap[:, None, None])
    shape = 1.0 / alpha
    lam = rng.gamma(shape, mu_draws / shape)
    counts = np.minimum(rng.poisson(lam).astype(float), cap[:, None, None])

    # Regional mean per year: observed where observed, imputed draws elsewhere.
    filled = np.where(obs_mask[:, :, None], observed[:, :, None], counts)
    regional = filled.mean(axis=0)  # (n_y, draws)
    q = np.percentile(regional, [5, 25, 50, 75, 95], axis=1)
    mean_mu = np.median(mu_draws, axis=2)
    lo = np.percentile(counts, 5, axis=2)
    hi = np.percentile(counts, 95, axis=2)

    return {
        "years": yrs,
        "station_ids": ids,
        "alpha": alpha,
        "regional": {
            "year": yrs,
            "mean": [round(float(v), 2) for v in q[2]],  # median of the draws
            "p05": [round(float(v), 2) for v in q[0]],
            "p25": [round(float(v), 2) for v in q[1]],
            "p50": [round(float(v), 2) for v in q[2]],
            "p75": [round(float(v), 2) for v in q[3]],
            "p95": [round(float(v), 2) for v in q[4]],
            "n_observed": [int(obs_mask[:, k].sum()) for k in range(n_y)],
            "n_stations": n_s,
        },
        "per_station": {
            s: {
                "mean": [round(float(mean_mu[si[s], k]), 2) for k in range(n_y)],
                "lo": [int(lo[si[s], k]) for k in range(n_y)],
                "hi": [int(hi[si[s], k]) for k in range(n_y)],
                "observed": [
                    None if np.isnan(observed[si[s], k]) else int(observed[si[s], k])
                    for k in range(n_y)
                ],
            }
            for s in ids
        },
    }


REGIONAL_METRICS = {
    # key: (parquet file, value column, year column)
    "hot95": ("annual", "hot_95", "year"),
    "hot100": ("annual", "hot_100", "year"),
    "warm65": ("annual", "warm_65", "year"),
    "warm70": ("annual", "warm_70", "year"),
    "frost32": ("cold_season", "coldnight_32", "season"),
}


def run_regional(region, analysis_dir, last_complete_year: int) -> dict:
    rng = np.random.default_rng(SEED)
    out = {"region": region.id, "metrics": {}}
    ids = region.station_ids
    for key, (file, col, ycol) in REGIONAL_METRICS.items():
        frames = []
        for sid in ids:
            p = analysis_dir / sid / f"{file}.parquet"
            if not p.exists():
                continue
            df = pl.read_parquet(p).select(pl.col(ycol).alias("year"), pl.col(col).alias("value"))
            frames.append(df.with_columns(pl.lit(sid).alias("id")))
        if not frames:
            continue
        table = pl.concat(frames)
        years = [y for y in sorted(set(table["year"].to_list())) if y <= last_complete_year]
        res = fit_metric(table, years, ids, rng)
        if res:
            res["evaluation"] = evaluate_metric(table, years, ids, rng)
            out["metrics"][key] = res
    return out
