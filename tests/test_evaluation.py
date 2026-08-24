from __future__ import annotations

import numpy as np
import pytest

from src.evaluation import compute_ate, evaluate_ranking, response_diagnostics


def test_compute_ate_matches_hand_calculation() -> None:
    treatment = [1, 1, 1, 1, 0, 0, 0, 0]
    outcome = [1, 1, 0, 0, 0, 0, 0, 1]
    result = compute_ate(treatment, outcome)
    assert result.ate == pytest.approx(0.5 - 0.25)


def test_compute_ate_rejects_empty_arm() -> None:
    with pytest.raises(ValueError, match="empty"):
        compute_ate([1, 1, 1], [1, 0, 1])


def test_good_ranking_scores_above_theoretical_random() -> None:
    rng = np.random.default_rng(0)
    n = 500
    treatment = rng.integers(0, 2, size=n).astype(float)
    true_uplift = rng.normal(size=n)
    # outcome correlated with true_uplift for treated rows only -> a perfect ranker should beat random
    outcome = (rng.uniform(size=n) < np.clip(0.2 + 0.3 * treatment * (true_uplift > 0), 0, 1)).astype(float)
    result = evaluate_ranking(true_uplift, treatment, outcome)
    assert result.qini_above_random > 0


def test_reversed_ranking_scores_below_theoretical_random() -> None:
    rng = np.random.default_rng(0)
    n = 500
    treatment = rng.integers(0, 2, size=n).astype(float)
    true_uplift = rng.normal(size=n)
    outcome = (rng.uniform(size=n) < np.clip(0.2 + 0.3 * treatment * (true_uplift > 0), 0, 1)).astype(float)
    reversed_scores = -true_uplift
    result = evaluate_ranking(reversed_scores, treatment, outcome)
    assert result.qini_above_random < 0


def test_random_scores_are_close_to_theoretical_random() -> None:
    rng = np.random.default_rng(1)
    n = 2000
    treatment = rng.integers(0, 2, size=n).astype(float)
    outcome = rng.integers(0, 2, size=n).astype(float)
    random_scores = rng.uniform(size=n)
    result = evaluate_ranking(random_scores, treatment, outcome)
    assert abs(result.qini_above_random) < 0.1 * abs(result.theoretical_random_qini_area) + 1.0


def test_evaluate_ranking_rejects_single_arm() -> None:
    with pytest.raises(ValueError, match="arm"):
        evaluate_ranking([0.1, 0.2, 0.3], [1, 1, 1], [1, 0, 1])


def test_uplift_at_k_is_none_when_an_arm_is_missing_in_prefix() -> None:
    # all treated rows ranked last -> top-10% prefix has zero treated rows
    scores = [1.0] * 90 + [0.0] * 10
    treatment = [0] * 90 + [1] * 10
    outcome = [0] * 100
    result = evaluate_ranking(scores, treatment, outcome)
    assert result.uplift_at_k["10pct"] is None


def test_response_diagnostics_perfect_separation_gives_auc_one() -> None:
    outcome = [0, 0, 0, 1, 1, 1]
    probabilities = [0.1, 0.1, 0.2, 0.8, 0.9, 0.9]
    diagnostics = response_diagnostics(probabilities, outcome)
    assert diagnostics.roc_auc == pytest.approx(1.0)
