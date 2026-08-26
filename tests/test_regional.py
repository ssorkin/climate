import numpy as np
import polars as pl

from climate.analysis import regional as R


def synthetic(rng, n_s=8, years=range(1950, 2020), missing_frac=0.3):
    a = rng.normal(2.5, 1.0, n_s)  # station climates (log scale)
    b = np.linspace(-0.3, 0.3, len(years))  # a gentle upward year effect
    rows = []
    for s in range(n_s):
        for k, y in enumerate(years):
            if rng.random() < missing_frac:
                continue
            mu = np.exp(a[s] + b[k])
            rows.append(
                {
                    "id": f"S{s:02d}",
                    "year": y,
                    "value": int(rng.negative_binomial(20, 20 / (20 + mu))),
                }
            )
    return pl.DataFrame(rows), a, b


def test_model_recovers_trend_and_covers():
    rng = np.random.default_rng(1)
    table, a, b = synthetic(rng)
    ids = sorted(table["id"].unique())
    res = R.fit_metric(table, list(range(1950, 2020)), ids, np.random.default_rng(2))
    reg = res["regional"]
    early = np.mean(reg["mean"][:10])
    late = np.mean(reg["mean"][-10:])
    assert late > early * 1.3  # the upward year effect is recovered
    assert reg["n_stations"] == 8 and all(0 < n <= 8 for n in reg["n_observed"])
    # imputed cells: the predictive 90% interval brackets the true expected count most of the time
    ok = tot = 0
    for s, sid in enumerate(ids):
        ps = res["per_station"][sid]
        for k in range(len(reg["year"])):
            if ps["observed"][k] is None:
                truth = np.exp(a[s] + b[k])
                ok += ps["lo"][k] <= truth <= ps["hi"][k]
                tot += 1
    assert tot > 50 and ok / tot > 0.8


def test_evaluation_is_calibrated_on_synthetic_data():
    rng = np.random.default_rng(3)
    table, _a, _b = synthetic(rng, missing_frac=0.1)
    ids = sorted(table["id"].unique())
    ev = R.evaluate_metric(table, list(range(1950, 2020)), ids, np.random.default_rng(4))
    for kind in ("random", "blocks"):
        e = ev[kind]
        assert 0.8 <= e["coverage90"] <= 0.98
        assert e["mae"] <= e["baseline_mae"] * 1.1
