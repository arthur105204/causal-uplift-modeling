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


def test_auuc_matches_hand_calculation_on_a_tiny_fixture() -> None:
    """4 rows, ranked by score desc: T=1/Y=1, T=0/Y=0, T=1/Y=0, T=0/Y=1.

    uplift_gain(r) = (cum_y1/cum_n1 - cum_y0/cum_n0) * r, defined only where
    both arms are present:
      r=1: only treated present            -> undefined, dropped
      r=2: (1/1 - 0/1) * 2 = 2.0           at coverage 0.50
      r=3: (1/2 - 0/1) * 3 = 1.5           at coverage 0.75
      r=4: (1/2 - 1/2) * 4 = 0.0           at coverage 1.00
    Trapezoids from (0,0): 0.5*(0+2.0)*0.50 + 0.5*(2.0+1.5)*0.25
                         + 0.5*(1.5+0.0)*0.25 = 0.5 + 0.4375 + 0.1875 = 1.125
    """

    scores = [4.0, 3.0, 2.0, 1.0]
    treatment = [1, 0, 1, 0]
    outcome = [1, 0, 0, 1]
    result = evaluate_ranking(scores, treatment, outcome)
    assert result.auuc_area == pytest.approx(1.125)
    assert result.theoretical_random_auuc_area == pytest.approx(0.0)  # u_full = 0.0
    assert result.auuc_above_random == pytest.approx(1.125)


def test_auuc_curve_starts_at_origin_and_is_monotone_in_coverage() -> None:
    rng = np.random.default_rng(3)
    n = 400
    treatment = rng.integers(0, 2, size=n).astype(float)
    outcome = rng.integers(0, 2, size=n).astype(float)
    result = evaluate_ranking(rng.uniform(size=n), treatment, outcome)
    curve = result.uplift_curve
    assert curve["coverage"].iloc[0] == 0.0
    assert curve["uplift_gain"].iloc[0] == 0.0
    assert curve["coverage"].iloc[-1] == pytest.approx(1.0)
    assert curve["coverage"].is_monotonic_increasing


def test_good_ranking_beats_random_on_auuc_too() -> None:
    rng = np.random.default_rng(0)
    n = 500
    treatment = rng.integers(0, 2, size=n).astype(float)
    true_uplift = rng.normal(size=n)
    outcome = (rng.uniform(size=n) < np.clip(0.2 + 0.3 * treatment * (true_uplift > 0), 0, 1)).astype(float)
    assert evaluate_ranking(true_uplift, treatment, outcome).auuc_above_random > 0


def test_reversed_ranking_loses_to_random_on_auuc_too() -> None:
    rng = np.random.default_rng(0)
    n = 500
    treatment = rng.integers(0, 2, size=n).astype(float)
    true_uplift = rng.normal(size=n)
    outcome = (rng.uniform(size=n) < np.clip(0.2 + 0.3 * treatment * (true_uplift > 0), 0, 1)).astype(float)
    assert evaluate_ranking(-true_uplift, treatment, outcome).auuc_above_random < 0


def test_auuc_and_qini_are_distinct_statistics() -> None:
    """Guards against AUUC accidentally being implemented as an alias of
    Qini -- they weight arm imbalance differently, so on imbalanced arms
    they must not coincide."""

    rng = np.random.default_rng(5)
    n = 600
    treatment = (rng.uniform(size=n) < 0.8).astype(float)  # deliberately imbalanced arms
    outcome = (rng.uniform(size=n) < 0.2 + 0.2 * treatment).astype(float)
    result = evaluate_ranking(rng.uniform(size=n), treatment, outcome)
    assert result.auuc_area != pytest.approx(result.qini_area)


def test_response_diagnostics_perfect_separation_gives_auc_one() -> None:
    outcome = [0, 0, 0, 1, 1, 1]
    probabilities = [0.1, 0.1, 0.2, 0.8, 0.9, 0.9]
    diagnostics = response_diagnostics(probabilities, outcome)
    assert diagnostics.roc_auc == pytest.approx(1.0)
