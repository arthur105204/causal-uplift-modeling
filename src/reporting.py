"""Report-building helpers for the Kaggle execution notebook: packaging one
model stage's test-set evaluation into a standard set of artifact files,
building the cross-model comparison table, and running the paired-bootstrap
significance check used throughout the report stage.

This module is notebook orchestration plumbing, same as src.artifacts: it
saves/loads/assembles what src.evaluation.evaluate_ranking already computed,
and never reimplements a metric itself. See src.evaluation's module
docstring for the Qini/AUUC/uplift@K definitions this module packages and
compares.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.artifacts import load_csv_artifact, load_json, save_csv, save_json
from src.data import load_parquet, save_parquet
from src.evaluation import evaluate_ranking


def package_ranking_artifacts(
    model_dir, label, val_metrics, test_metrics,
    val_scores, test_scores, T_val, Y_val, T_test, Y_test,
    row_id_val, row_id_test, runtime_seconds, extra_metrics=None,
):
    """Persist one model's validation+test predictions, curves, and metrics
    in the shape every report-stage cell expects: one prediction artifact,
    one metrics artifact, one set of curve artifacts."""

    predictions = pd.concat([
        pd.DataFrame({
            "row_id": np.asarray(row_id_val), "partition": "validation",
            "score": np.asarray(val_scores, dtype=np.float64),
            "treatment": np.asarray(T_val, dtype=np.float64), "outcome": np.asarray(Y_val, dtype=np.float64),
        }),
        pd.DataFrame({
            "row_id": np.asarray(row_id_test), "partition": "test",
            "score": np.asarray(test_scores, dtype=np.float64),
            "treatment": np.asarray(T_test, dtype=np.float64), "outcome": np.asarray(Y_test, dtype=np.float64),
        }),
    ], ignore_index=True)
    save_parquet(predictions, model_dir / "predictions.parquet")
    save_csv(test_metrics.qini_curve, model_dir / "qini_curve.csv")
    save_csv(test_metrics.uplift_curve, model_dir / "uplift_curve.csv")
    save_csv(test_metrics.decile_table, model_dir / "decile_table.csv")
    metrics = {
        "label": label,
        "runtime_seconds": runtime_seconds,
        "n_test": test_metrics.n,
        "val_qini_above_random": val_metrics.qini_above_random,
        "val_auuc_above_random": val_metrics.auuc_above_random,
        "test_qini_above_random": test_metrics.qini_above_random,
        "test_auuc_above_random": test_metrics.auuc_above_random,
        "test_qini_area": test_metrics.qini_area,
        "test_auuc_area": test_metrics.auuc_area,
        "test_uplift_at_k": test_metrics.uplift_at_k,
    }
    if extra_metrics:
        metrics.update(extra_metrics)
    save_json(metrics, model_dir / "metrics.json")
    return metrics


def load_ranking_artifact(model_dir):
    return {
        "metrics": load_json(model_dir / "metrics.json"),
        "qini_curve": load_csv_artifact(model_dir / "qini_curve.csv"),
        "uplift_curve": load_csv_artifact(model_dir / "uplift_curve.csv"),
        "decile_table": load_csv_artifact(model_dir / "decile_table.csv"),
        "predictions": load_parquet(model_dir / "predictions.parquet"),
    }


OBJECTIVE_LABELS = {
    "Response LightGBM": "P(Y|X) — naive targeting baseline",
    "T-Learner": "tau(X) — CATE estimation",
    "X-Learner": "tau(X) — CATE estimation",
    "Causal Forest": "tau(X) — CATE estimation",
    "Random (reference)": "Uninformative random ranking",
}


def build_model_comparison_table(available: dict, random_metrics) -> pd.DataFrame:
    """One row per available model plus the random reference, sorted by
    qini_above_random -- the primary ranking statistic (see the notebook's
    glossary and src.evaluation's module docstring)."""

    rows = []
    for label, d in available.items():
        m = load_json(d / "metrics.json")
        row = {
            "model": label, "objective": OBJECTIVE_LABELS[label],
            "auuc_above_random": m["test_auuc_above_random"],
            "qini_above_random": m["test_qini_above_random"],
            "auuc_area": m["test_auuc_area"], "qini_area": m["test_qini_area"],
        }
        row.update({f"uplift@{k}": v for k, v in m["test_uplift_at_k"].items()})
        rows.append(row)
    rows.append({
        "model": "Random (reference)", "objective": OBJECTIVE_LABELS["Random (reference)"],
        "auuc_above_random": random_metrics.auuc_above_random,
        "qini_above_random": random_metrics.qini_above_random, "auuc_area": random_metrics.auuc_area,
        "qini_area": random_metrics.qini_area,
        **{f"uplift@{k}": v for k, v in random_metrics.uplift_at_k.items()},
    })
    comparison = pd.DataFrame(rows).set_index("model").sort_values("qini_above_random", ascending=False)
    return comparison[["objective"] + [c for c in comparison.columns if c != "objective"]]


def paired_bootstrap_gaps(score_a, score_b, treatment, outcome, *, seed: int, n_boot: int = 500, metrics) -> dict:
    """95% CI (2.5th/97.5th percentile) of the gap (a - b) for each named
    metric, evaluated jointly on the same n_boot paired bootstrap resamples
    of the test rows -- "is this gap real, or could it be resampling noise
    at this sample size" (see the notebook's glossary).

    `metrics`: dict[str, Callable[[RankingMetrics], float]], e.g.
    {"qini_above_random": lambda m: m.qini_above_random,
     "uplift@10%": lambda m: m.uplift_at_k["10pct"]}.

    Returns {name: {"ci_low", "ci_high", "excludes_zero", "gap_samples"}}.
    """

    score_a = np.asarray(score_a, dtype=np.float64)
    score_b = np.asarray(score_b, dtype=np.float64)
    treatment = np.asarray(treatment, dtype=np.float64)
    outcome = np.asarray(outcome, dtype=np.float64)
    n = len(treatment)
    rng = np.random.default_rng(seed)
    gaps = {name: np.empty(n_boot) for name in metrics}
    for b in range(n_boot):
        idx = rng.integers(0, n, size=n)
        m_a = evaluate_ranking(score_a[idx], treatment[idx], outcome[idx])
        m_b = evaluate_ranking(score_b[idx], treatment[idx], outcome[idx])
        for name, extract in metrics.items():
            gaps[name][b] = extract(m_a) - extract(m_b)

    result = {}
    for name, arr in gaps.items():
        lo, hi = np.percentile(arr, [2.5, 97.5])
        result[name] = {
            "gap_samples": arr, "ci_low": float(lo), "ci_high": float(hi),
            "excludes_zero": bool(lo > 0 or hi < 0),
        }
    return result
