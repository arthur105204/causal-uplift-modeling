"""Synthetic-fixture unit tests for src/xlearner.py.

Small hand-computable fixtures only -- no real data. Mirrors
tests/test_tlearner.py's convention: prove the correctness-surface primitives
(fold assignment, OOF coverage/opposite-fold assertions, pseudo-outcome
construction, combination) independently of any LightGBM fit or real dataset.
"""

from __future__ import annotations

import numpy as np
import pytest

from src.xlearner import (
    XLearnerContractError,
    assert_full_oof_coverage,
    assert_opposite_fold,
    assign_folds,
    combine_tau,
    compute_pseudo_outcomes,
    empirical_treatment_rate,
)


# --- assign_folds -------------------------------------------------------------

def test_assign_folds_disjoint_and_covers_population() -> None:
    n = 400
    rng = np.random.default_rng(0)
    source_row_id = np.arange(n)
    treatment = rng.integers(0, 2, size=n)
    outcome = rng.integers(0, 2, size=n)

    fold_a, fold_b = assign_folds(source_row_id, treatment, outcome, seed=42)

    assert len(set(fold_a.tolist()) & set(fold_b.tolist())) == 0
    assert set(fold_a.tolist()) | set(fold_b.tolist()) == set(source_row_id.tolist())
    assert abs(len(fold_a) - len(fold_b)) <= 1


def test_assign_folds_deterministic_given_seed() -> None:
    n = 300
    rng = np.random.default_rng(1)
    source_row_id = np.arange(n)
    treatment = rng.integers(0, 2, size=n)
    outcome = rng.integers(0, 2, size=n)

    fold_a1, fold_b1 = assign_folds(source_row_id, treatment, outcome, seed=42)
    fold_a2, fold_b2 = assign_folds(source_row_id, treatment, outcome, seed=42)
    np.testing.assert_array_equal(fold_a1, fold_a2)
    np.testing.assert_array_equal(fold_b1, fold_b2)


def test_assign_folds_stratifies_joint_t_y() -> None:
    """Each of the four (T,Y) strata should split ~50/50 across folds."""

    n_per_stratum = 100
    source_row_id = np.arange(4 * n_per_stratum)
    treatment = np.repeat([0, 0, 1, 1], n_per_stratum)
    outcome = np.tile(np.repeat([0, 1], n_per_stratum // 2), 4)

    fold_a, fold_b = assign_folds(source_row_id, treatment, outcome, seed=42)
    fold_a_set = set(fold_a.tolist())

    for t in (0, 1):
        for y in (0, 1):
            stratum_ids = source_row_id[(treatment == t) & (outcome == y)]
            in_a = sum(1 for i in stratum_ids if i in fold_a_set)
            assert abs(in_a - len(stratum_ids) / 2) <= max(2, len(stratum_ids) * 0.1)


def test_assign_folds_rejects_mismatched_lengths() -> None:
    with pytest.raises(XLearnerContractError):
        assign_folds(np.arange(10), np.zeros(9), np.zeros(10))


def test_assign_folds_rejects_empty() -> None:
    with pytest.raises(XLearnerContractError):
        assign_folds(np.array([]), np.array([]), np.array([]))


# --- assert_opposite_fold ------------------------------------------------------

def test_assert_opposite_fold_passes_when_all_opposite() -> None:
    row_fold = np.array(["A", "A", "B", "B"])
    pred_fold = np.array(["B", "B", "A", "A"])
    assert_opposite_fold(row_fold, pred_fold, name="mu0_oof")


def test_assert_opposite_fold_raises_on_same_fold_leakage() -> None:
    row_fold = np.array(["A", "A", "B", "B"])
    pred_fold = np.array(["B", "A", "A", "A"])  # index 1 and 3 leak same-fold
    with pytest.raises(XLearnerContractError, match="own fold"):
        assert_opposite_fold(row_fold, pred_fold, name="mu0_oof")


def test_assert_opposite_fold_rejects_length_mismatch() -> None:
    with pytest.raises(XLearnerContractError, match="length mismatch"):
        assert_opposite_fold(np.array(["A", "B"]), np.array(["B"]), name="mu1_oof")


# --- assert_full_oof_coverage --------------------------------------------------

def test_assert_full_oof_coverage_passes_on_exact_match() -> None:
    expected = np.array([1, 2, 3, 4])
    actual = np.array([4, 3, 2, 1])
    assert_full_oof_coverage(expected, actual, name="mu0_oof")


def test_assert_full_oof_coverage_raises_on_missing_row() -> None:
    expected = np.array([1, 2, 3, 4])
    actual = np.array([1, 2, 3])
    with pytest.raises(XLearnerContractError, match="does not exactly match"):
        assert_full_oof_coverage(expected, actual, name="mu0_oof")


def test_assert_full_oof_coverage_raises_on_duplicate_row() -> None:
    expected = np.array([1, 2, 3, 4])
    actual = np.array([1, 1, 2, 3, 4])
    with pytest.raises(XLearnerContractError, match="duplicate"):
        assert_full_oof_coverage(expected, actual, name="mu1_oof")


# --- compute_pseudo_outcomes ----------------------------------------------------

def test_compute_pseudo_outcomes_hand_computed_signs() -> None:
    treatment = np.array([1, 1, 0, 0])
    outcome = np.array([1, 0, 1, 0])
    mu0_oof = np.array([0.3, 0.3, 0.2, 0.2])
    mu1_oof = np.array([0.6, 0.6, 0.5, 0.5])

    d1, d0, treated_mask, control_mask = compute_pseudo_outcomes(treatment, outcome, mu0_oof, mu1_oof)

    np.testing.assert_allclose(d1, [0.7, -0.3])
    np.testing.assert_allclose(d0, [-0.5, 0.5])
    np.testing.assert_array_equal(treated_mask, [True, True, False, False])
    np.testing.assert_array_equal(control_mask, [False, False, True, True])


def test_compute_pseudo_outcomes_swapped_formula_gives_wrong_sign() -> None:
    """D1 must use mu0_oof (not mu1_oof) on treated rows -- using the wrong
    nuisance surface silently flips the sign of the pseudo-effect."""

    treatment = np.array([1, 1, 0, 0])
    outcome = np.array([1, 0, 1, 0])
    mu0_oof = np.array([0.3, 0.3, 0.2, 0.2])
    mu1_oof = np.array([0.6, 0.6, 0.5, 0.5])

    d1, _, treated_mask, _ = compute_pseudo_outcomes(treatment, outcome, mu0_oof, mu1_oof)
    wrong_d1 = outcome[treated_mask] - mu1_oof[treated_mask]
    assert not np.allclose(d1, wrong_d1)


def test_compute_pseudo_outcomes_rejects_non_finite() -> None:
    treatment = np.array([1, 0])
    outcome = np.array([np.nan, 0.0])
    mu0_oof = np.array([0.3, 0.2])
    mu1_oof = np.array([0.6, 0.5])
    with pytest.raises(XLearnerContractError, match="non-finite"):
        compute_pseudo_outcomes(treatment, outcome, mu0_oof, mu1_oof)


def test_compute_pseudo_outcomes_rejects_out_of_bounds_mu() -> None:
    treatment = np.array([1, 0])
    outcome = np.array([1.0, 0.0])
    mu0_oof = np.array([0.3, 0.2])
    mu1_oof = np.array([1.5, 0.5])
    with pytest.raises(XLearnerContractError, match=r"\[0,1\]"):
        compute_pseudo_outcomes(treatment, outcome, mu0_oof, mu1_oof)


def test_compute_pseudo_outcomes_rejects_mismatched_lengths() -> None:
    with pytest.raises(XLearnerContractError, match="Mismatched"):
        compute_pseudo_outcomes(np.array([1, 0]), np.array([1.0]), np.array([0.3, 0.2]), np.array([0.6, 0.5]))


def test_compute_pseudo_outcomes_rejects_missing_arm() -> None:
    treatment = np.array([1, 1])
    outcome = np.array([1.0, 0.0])
    mu0_oof = np.array([0.3, 0.3])
    mu1_oof = np.array([0.6, 0.6])
    with pytest.raises(XLearnerContractError, match="control"):
        compute_pseudo_outcomes(treatment, outcome, mu0_oof, mu1_oof)


# --- empirical_treatment_rate ----------------------------------------------------

def test_empirical_treatment_rate_hand_computed() -> None:
    treatment = np.array([1, 1, 0, 0, 0])
    assert empirical_treatment_rate(treatment) == pytest.approx(0.4)


def test_empirical_treatment_rate_rejects_empty() -> None:
    with pytest.raises(XLearnerContractError):
        empirical_treatment_rate(np.array([]))


def test_empirical_treatment_rate_rejects_non_binary_values() -> None:
    with pytest.raises(XLearnerContractError):
        empirical_treatment_rate(np.array([0, 1, 2]))


# --- combine_tau -------------------------------------------------------------------

def test_combine_tau_hand_computed_constant_g() -> None:
    tau1_hat = np.array([1.0, 2.0])
    tau0_hat = np.array([3.0, 4.0])
    result = combine_tau(tau1_hat, tau0_hat, g=0.25)
    # tau_hat = g*tau0 + (1-g)*tau1
    expected = np.array([0.25 * 3.0 + 0.75 * 1.0, 0.25 * 4.0 + 0.75 * 2.0])
    np.testing.assert_allclose(result, expected)


def test_combine_tau_g_zero_endpoint_equals_tau1() -> None:
    tau1_hat = np.array([1.0, 2.0, 3.0])
    tau0_hat = np.array([9.0, 9.0, 9.0])
    result = combine_tau(tau1_hat, tau0_hat, g=0.0)
    np.testing.assert_allclose(result, tau1_hat)


def test_combine_tau_g_one_endpoint_equals_tau0() -> None:
    tau1_hat = np.array([1.0, 2.0, 3.0])
    tau0_hat = np.array([9.0, 9.0, 9.0])
    result = combine_tau(tau1_hat, tau0_hat, g=1.0)
    np.testing.assert_allclose(result, tau0_hat)


def test_combine_tau_accepts_array_g() -> None:
    tau1_hat = np.array([1.0, 2.0])
    tau0_hat = np.array([3.0, 4.0])
    g = np.array([0.0, 1.0])
    result = combine_tau(tau1_hat, tau0_hat, g=g)
    np.testing.assert_allclose(result, [1.0, 4.0])


def test_combine_tau_rejects_shape_mismatch() -> None:
    with pytest.raises(XLearnerContractError, match="shape"):
        combine_tau(np.array([1.0, 2.0]), np.array([1.0, 2.0, 3.0]), g=0.5)


def test_combine_tau_rejects_g_out_of_bounds() -> None:
    with pytest.raises(XLearnerContractError, match=r"\[0,1\]"):
        combine_tau(np.array([1.0]), np.array([2.0]), g=1.5)


def test_combine_tau_rejects_non_finite_inputs() -> None:
    with pytest.raises(XLearnerContractError, match="non-finite"):
        combine_tau(np.array([np.nan]), np.array([2.0]), g=0.5)
