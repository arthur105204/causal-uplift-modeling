"""Behavioral/invariant tests for src.reporting's statistical core:
paired_bootstrap_gaps (the significance check every notebook's "is this gap
real" conclusion rests on) and build_model_comparison_table (the leaderboard
every notebook's Section 4 displays). No hardcoded benchmark numbers -- these
tests construct small synthetic fixtures and check properties that must hold
regardless of the exact data, mirroring the style of tests/test_evaluation.py.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from src.artifacts import save_json
from src.evaluation import evaluate_ranking
from src.reporting import OBJECTIVE_LABELS, build_model_comparison_table, paired_bootstrap_gaps


def _synthetic_test_rows(rng: np.random.Generator, n: int) -> tuple[np.ndarray, np.ndarray]:
    """Treatment/outcome pair with both arms and both outcome classes present,
    so evaluate_ranking never hits an edge case unrelated to what these tests
    check."""

    treatment = rng.integers(0, 2, size=n).astype(np.float64)
    outcome = rng.integers(0, 2, size=n).astype(np.float64)
    return treatment, outcome


# --- paired_bootstrap_gaps -------------------------------------------------


def test_paired_bootstrap_identical_scores_gap_is_always_exactly_zero() -> None:
    """The defining property of a *paired* bootstrap: the same resample
    indices are applied to both models on every draw. If score_a and score_b
    are identical arrays, m_a and m_b are computed on identical resampled
    data every single draw, so the gap must be exactly zero on every draw --
    not just close to zero. If the two models were resampled independently
    instead of jointly, this would fail (their metrics would differ draw to
    draw even with identical underlying scores)."""

    rng = np.random.default_rng(0)
    n = 300
    treatment, outcome = _synthetic_test_rows(rng, n)
    scores = rng.normal(size=n)

    result = paired_bootstrap_gaps(
        scores, scores, treatment, outcome, seed=1, n_boot=25,
        metrics={"qini_above_random": lambda m: m.qini_above_random},
    )["qini_above_random"]

    assert np.all(result["gap_samples"] == 0.0)
    assert result["ci_low"] == 0.0
    assert result["ci_high"] == 0.0
    assert result["excludes_zero"] is False


def test_paired_bootstrap_ci_bounds_are_ordered() -> None:
    rng = np.random.default_rng(2)
    n = 400
    treatment, outcome = _synthetic_test_rows(rng, n)
    result = paired_bootstrap_gaps(
        rng.normal(size=n), rng.normal(size=n), treatment, outcome, seed=3, n_boot=30,
        metrics={"qini_above_random": lambda m: m.qini_above_random,
                 "auuc_above_random": lambda m: m.auuc_above_random},
    )
    for metric_result in result.values():
        assert metric_result["ci_low"] <= metric_result["ci_high"]


def test_paired_bootstrap_excludes_zero_matches_ci_bounds() -> None:
    """`excludes_zero` must be a pure function of ci_low/ci_high, not an
    independently-computed flag that could drift from the printed interval."""

    rng = np.random.default_rng(4)
    n = 400
    treatment, outcome = _synthetic_test_rows(rng, n)
    result = paired_bootstrap_gaps(
        rng.normal(size=n), rng.normal(size=n) * 0.01, treatment, outcome, seed=5, n_boot=30,
        metrics={"qini_above_random": lambda m: m.qini_above_random},
    )["qini_above_random"]
    assert result["excludes_zero"] == (result["ci_low"] > 0 or result["ci_high"] < 0)


def test_paired_bootstrap_detects_a_large_engineered_gap() -> None:
    """score_a is strongly predictive of who benefits from treatment; score_b
    is pure noise. The resulting qini_above_random gap should be large and
    positive on (almost) every resample, so the 95% CI should sit entirely
    above zero -- this is the behavior every notebook's "statistically
    distinguishable" conclusion depends on."""

    rng = np.random.default_rng(6)
    n = 3000
    treatment = rng.integers(0, 2, size=n).astype(np.float64)
    true_uplift = rng.normal(size=n)
    outcome = (rng.uniform(size=n) < np.clip(0.2 + 0.5 * treatment * (true_uplift > 0), 0, 1)).astype(np.float64)

    informative_scores = true_uplift
    noise_scores = rng.normal(size=n)

    result = paired_bootstrap_gaps(
        informative_scores, noise_scores, treatment, outcome, seed=7, n_boot=50,
        metrics={"qini_above_random": lambda m: m.qini_above_random},
    )["qini_above_random"]

    assert result["excludes_zero"] is True
    assert result["ci_low"] > 0


def test_paired_bootstrap_is_deterministic_given_a_fixed_seed() -> None:
    rng = np.random.default_rng(8)
    n = 300
    treatment, outcome = _synthetic_test_rows(rng, n)
    score_a, score_b = rng.normal(size=n), rng.normal(size=n)

    metrics = {"qini_above_random": lambda m: m.qini_above_random}
    first = paired_bootstrap_gaps(score_a, score_b, treatment, outcome, seed=42, n_boot=20, metrics=metrics)
    second = paired_bootstrap_gaps(score_a, score_b, treatment, outcome, seed=42, n_boot=20, metrics=metrics)

    np.testing.assert_array_equal(
        first["qini_above_random"]["gap_samples"], second["qini_above_random"]["gap_samples"]
    )


def test_paired_bootstrap_returns_exactly_the_requested_metrics() -> None:
    rng = np.random.default_rng(9)
    n = 300
    treatment, outcome = _synthetic_test_rows(rng, n)
    result = paired_bootstrap_gaps(
        rng.normal(size=n), rng.normal(size=n), treatment, outcome, seed=1, n_boot=10,
        metrics={
            "qini_above_random": lambda m: m.qini_above_random,
            "uplift@10%": lambda m: m.uplift_at_k["10pct"],
        },
    )
    assert set(result.keys()) == {"qini_above_random", "uplift@10%"}


# --- build_model_comparison_table ------------------------------------------


def _write_metrics(model_dir: Path, *, qini_above_random: float) -> None:
    save_json(
        {
            "test_qini_above_random": qini_above_random,
            "test_auuc_above_random": qini_above_random * 1.1,
            "test_qini_area": qini_above_random + 100.0,
            "test_auuc_area": qini_above_random + 120.0,
            "test_uplift_at_k": {"10pct": 0.01, "20pct": 0.02, "100pct": 0.005},
        },
        model_dir / "metrics.json",
    )


@pytest.fixture()
def random_metrics():
    rng = np.random.default_rng(0)
    n = 300
    treatment, outcome = _synthetic_test_rows(rng, n)
    return evaluate_ranking(rng.uniform(size=n), treatment, outcome)


def test_build_model_comparison_table_sorted_descending_by_qini(tmp_path: Path, random_metrics) -> None:
    available = {}
    for label, value in [("Response LightGBM", 5.0), ("Causal Forest", 20.0), ("T-Learner", 10.0)]:
        d = tmp_path / label
        d.mkdir()
        _write_metrics(d, qini_above_random=value)
        available[label] = d

    table = build_model_comparison_table(available, random_metrics)
    assert list(table["qini_above_random"]) == sorted(table["qini_above_random"], reverse=True)
    assert table.index[0] == "Causal Forest"


def test_build_model_comparison_table_includes_random_reference_row(tmp_path: Path, random_metrics) -> None:
    d = tmp_path / "Response LightGBM"
    d.mkdir()
    _write_metrics(d, qini_above_random=5.0)

    table = build_model_comparison_table({"Response LightGBM": d}, random_metrics)
    assert "Random (reference)" in table.index
    assert table.loc["Random (reference)", "objective"] == OBJECTIVE_LABELS["Random (reference)"]
    assert table.loc["Random (reference)", "qini_above_random"] == pytest.approx(random_metrics.qini_above_random)


def test_build_model_comparison_table_objective_column_matches_labels(tmp_path: Path, random_metrics) -> None:
    available = {}
    for label in ("Response LightGBM", "X-Learner"):
        d = tmp_path / label
        d.mkdir()
        _write_metrics(d, qini_above_random=1.0)
        available[label] = d

    table = build_model_comparison_table(available, random_metrics)
    for label in available:
        assert table.loc[label, "objective"] == OBJECTIVE_LABELS[label]


def test_build_model_comparison_table_excludes_models_not_in_available(tmp_path: Path, random_metrics) -> None:
    d = tmp_path / "Causal Forest"
    d.mkdir()
    _write_metrics(d, qini_above_random=1.0)

    table = build_model_comparison_table({"Causal Forest": d}, random_metrics)
    assert "T-Learner" not in table.index
    assert "X-Learner" not in table.index
    assert "Response LightGBM" not in table.index


def test_build_model_comparison_table_carries_uplift_at_k_columns(tmp_path: Path, random_metrics) -> None:
    d = tmp_path / "Response LightGBM"
    d.mkdir()
    _write_metrics(d, qini_above_random=1.0)

    table = build_model_comparison_table({"Response LightGBM": d}, random_metrics)
    assert "uplift@10pct" in table.columns
    assert table.loc["Response LightGBM", "uplift@10pct"] == pytest.approx(0.01)
