"""Synthetic-fixture unit tests for src/tlearner.py.

No real data needed -- mirrors tests/test_lightgbm_baseline.py's convention.
The full-scale governed SMOKE/FULL runs happen in kaggle/02_uplift_modeling.ipynb.
"""

from __future__ import annotations

import numpy as np
import pytest

from src.tlearner import (
    TLearnerContractError,
    assert_aligned_predictions,
    compute_tau,
    partition_by_arm,
    reconcile_reloaded_tau,
)


def test_partition_by_arm_splits_correctly() -> None:
    treatment = np.array([1, 0, 1, 0, 1])
    values = np.array([10, 20, 30, 40, 50])
    (treated,), (control,) = partition_by_arm(treatment, values)
    np.testing.assert_array_equal(treated, [10, 30, 50])
    np.testing.assert_array_equal(control, [20, 40])


def test_partition_by_arm_rejects_missing_treated_arm() -> None:
    treatment = np.zeros(5)
    with pytest.raises(TLearnerContractError, match="Treated arm is empty"):
        partition_by_arm(treatment, np.arange(5))


def test_partition_by_arm_rejects_missing_control_arm() -> None:
    treatment = np.ones(5)
    with pytest.raises(TLearnerContractError, match="Control arm is empty"):
        partition_by_arm(treatment, np.arange(5))


def test_partition_by_arm_rejects_non_binary_treatment() -> None:
    treatment = np.array([1, 0, 2])
    with pytest.raises(TLearnerContractError, match="outside"):
        partition_by_arm(treatment, np.arange(3))


def test_partition_by_arm_rejects_mismatched_array_length() -> None:
    treatment = np.array([1, 0, 1])
    with pytest.raises(TLearnerContractError, match="length"):
        partition_by_arm(treatment, np.arange(2))


def test_assert_aligned_predictions_passes_when_aligned() -> None:
    ids = np.array([1, 2, 3])
    assert_aligned_predictions(ids, ids.copy(), ids)


def test_assert_aligned_predictions_rejects_mu1_mismatch() -> None:
    expected = np.array([1, 2, 3])
    with pytest.raises(TLearnerContractError, match="mu1"):
        assert_aligned_predictions(np.array([1, 2, 4]), expected, expected)


def test_assert_aligned_predictions_rejects_mu0_mismatch() -> None:
    expected = np.array([1, 2, 3])
    with pytest.raises(TLearnerContractError, match="mu0"):
        assert_aligned_predictions(expected, np.array([1, 2, 4]), expected)


def test_compute_tau_exact_construction() -> None:
    mu1 = np.array([0.5, 0.3])
    mu0 = np.array([0.2, 0.3])
    tau = compute_tau(mu1, mu0)
    np.testing.assert_array_equal(tau, mu1 - mu0)


def test_compute_tau_hand_computed_sign_orientation() -> None:
    """Hand-computed fixture: mu1=[0.8,0.2], mu0=[0.3,0.6] -> tau=[0.5,-0.4].
    Sign orientation is a direct consequence of the subtraction, verified here
    rather than by a separate production-code assertion."""

    mu1 = np.array([0.8, 0.2])
    mu0 = np.array([0.3, 0.6])
    tau = compute_tau(mu1, mu0)
    np.testing.assert_allclose(tau, [0.5, -0.4])
    assert tau[0] > 0
    assert tau[1] < 0


def test_compute_tau_rejects_shape_mismatch() -> None:
    with pytest.raises(TLearnerContractError, match="shape"):
        compute_tau(np.array([0.1, 0.2]), np.array([0.1, 0.2, 0.3]))


def test_compute_tau_rejects_non_finite() -> None:
    with pytest.raises(TLearnerContractError, match="non-finite"):
        compute_tau(np.array([0.1, np.inf]), np.array([0.1, 0.2]))


def test_compute_tau_rejects_out_of_bounds() -> None:
    with pytest.raises(TLearnerContractError, match=r"\[0,1\]"):
        compute_tau(np.array([0.1, 1.5]), np.array([0.1, 0.2]))


def test_reconcile_reloaded_tau_matches_within_derived_tolerance() -> None:
    mu1_stored = np.array([0.500001, 0.3])
    mu0_stored = np.array([0.2, 0.300001])
    tau_stored = mu1_stored - mu0_stored
    # Tiny per-surface perturbations, each within docs/06 tolerance on its own.
    mu1_reloaded = mu1_stored + 5e-9
    mu0_reloaded = mu0_stored - 5e-9
    matches, tau_reloaded, info = reconcile_reloaded_tau(
        mu1_reloaded, mu0_reloaded, tau_stored, mu1_stored, mu0_stored,
    )
    assert matches
    assert info["max_deviation"] <= info["max_bound"]


def test_reconcile_reloaded_tau_rejects_large_deviation() -> None:
    mu1_stored = np.array([0.5])
    mu0_stored = np.array([0.2])
    tau_stored = mu1_stored - mu0_stored
    mu1_reloaded = mu1_stored + 0.01  # far outside any reasonable reload tolerance
    mu0_reloaded = mu0_stored
    matches, _, _ = reconcile_reloaded_tau(mu1_reloaded, mu0_reloaded, tau_stored, mu1_stored, mu0_stored)
    assert not matches


def test_reconcile_reloaded_tau_near_zero_cancellation_case() -> None:
    """tau near zero from two comparably-sized mu1/mu0 -- the bound must be
    derived from mu1/mu0 magnitudes, not from tau's own tiny magnitude, or a
    naive rtol-on-tau check would wrongly reject a genuinely tiny, valid
    reload deviation."""

    mu1_stored = np.array([0.500002])
    mu0_stored = np.array([0.500000])
    tau_stored = mu1_stored - mu0_stored  # 0.000002, near zero
    mu1_reloaded = mu1_stored + 3e-9
    mu0_reloaded = mu0_stored - 3e-9
    matches, _, info = reconcile_reloaded_tau(mu1_reloaded, mu0_reloaded, tau_stored, mu1_stored, mu0_stored)
    assert matches
    # the bound is dominated by 2*atol + rtol*(~1.0), not by rtol*|tau_stored| (~2e-6*1e-6, negligible)
    assert info["max_bound"] > 1e-7
