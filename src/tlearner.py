"""T-Learner correctness primitives (T08): arm partitioning and tau
construction/reconciliation only. Fitting stays in src/lightgbm_baseline.py;
causal-ranking evaluation stays in src/metrics.py. This module adds only the
T-Learner-specific combination/validation logic that doesn't belong in either.
"""

from __future__ import annotations

import numpy as np

from src.data import DataContractError


class TLearnerContractError(DataContractError):
    """Raised when a T08 T-Learner construction/validation invariant is violated."""


def _as_array(values, dtype=np.float64) -> np.ndarray:
    return np.asarray(values, dtype=dtype)


def partition_by_arm(treatment, *arrays: np.ndarray):
    """Boolean-mask partition of aligned arrays into (treated, control) tuples.

    `treatment` must be complete binary {0,1}. Every array in `arrays` must be
    the same length as `treatment`. Raises if either arm is empty.
    """

    treatment_arr = _as_array(treatment)
    if np.isnan(treatment_arr).any():
        raise TLearnerContractError("treatment contains missing values")
    unique = set(treatment_arr.tolist())
    if not unique.issubset({0.0, 1.0}):
        raise TLearnerContractError(f"treatment contains values outside {{0,1}}: {unique}")

    length = len(treatment_arr)
    prepared = []
    for array in arrays:
        array = np.asarray(array)
        if len(array) != length:
            raise TLearnerContractError(
                f"Array length {len(array)} does not match treatment length {length}"
            )
        prepared.append(array)

    treated_mask = treatment_arr == 1
    control_mask = treatment_arr == 0
    if not treated_mask.any():
        raise TLearnerContractError("Treated arm is empty; cannot partition for T-Learner fitting")
    if not control_mask.any():
        raise TLearnerContractError("Control arm is empty; cannot partition for T-Learner fitting")

    treated = tuple(array[treated_mask] for array in prepared)
    control = tuple(array[control_mask] for array in prepared)
    return treated, control


def assert_aligned_predictions(
    source_row_id_mu1: np.ndarray,
    source_row_id_mu0: np.ndarray,
    source_row_id_expected: np.ndarray,
) -> None:
    """Both surfaces must have scored exactly the expected cohort, same row order."""

    mu1_ids = np.asarray(source_row_id_mu1)
    mu0_ids = np.asarray(source_row_id_mu0)
    expected_ids = np.asarray(source_row_id_expected)
    if not np.array_equal(mu1_ids, expected_ids):
        raise TLearnerContractError("mu1 predictions are not row-identity-aligned to the expected validation cohort")
    if not np.array_equal(mu0_ids, expected_ids):
        raise TLearnerContractError("mu0 predictions are not row-identity-aligned to the expected validation cohort")


def compute_tau(mu1_hat, mu0_hat) -> np.ndarray:
    """Authoritative same-run construction: tau_hat = mu1_hat - mu0_hat, exact.

    Validates shape and [0,1]/finite bounds on both inputs first; sign
    orientation is a direct, testable consequence of this definition (see
    tests/test_tlearner.py), not a separately-asserted runtime check.
    """

    mu1_arr = _as_array(mu1_hat)
    mu0_arr = _as_array(mu0_hat)
    if mu1_arr.shape != mu0_arr.shape:
        raise TLearnerContractError(
            f"mu1_hat shape {mu1_arr.shape} does not match mu0_hat shape {mu0_arr.shape}"
        )
    for name, array in (("mu1_hat", mu1_arr), ("mu0_hat", mu0_arr)):
        if not np.isfinite(array).all():
            raise TLearnerContractError(f"{name} contains non-finite values")
        if (array < 0).any() or (array > 1).any():
            raise TLearnerContractError(f"{name} contains values outside [0,1]")
    return mu1_arr - mu0_arr


def reconcile_reloaded_tau(
    mu1_reloaded,
    mu0_reloaded,
    tau_stored,
    mu1_stored,
    mu0_stored,
    *,
    rtol: float = 1e-6,
    atol: float = 1e-8,
):
    """Reconcile a reloaded tau against the stored tau via a tolerance derived
    from the two independent nuisance-prediction reload tolerances (docs/06:
    rtol=1e-6, atol=1e-8 per surface), not a fresh unjustified exact-equality
    or a naive flat np.allclose on tau itself.

    tau can be near zero by cancellation of two comparably-sized mu1/mu0
    values, so the bound must be evaluated per-element from the *stored*
    mu1/mu0 magnitudes, not from tau's own (possibly tiny) magnitude:

        |tau_reload - tau_stored| <= 2*atol + rtol*(|mu1_stored| + |mu0_stored|)

    which follows directly from the triangle inequality applied to each
    surface's own independently-bounded reload error.
    """

    mu1_reloaded_arr = _as_array(mu1_reloaded)
    mu0_reloaded_arr = _as_array(mu0_reloaded)
    tau_stored_arr = _as_array(tau_stored)
    mu1_stored_arr = _as_array(mu1_stored)
    mu0_stored_arr = _as_array(mu0_stored)

    tau_reloaded = mu1_reloaded_arr - mu0_reloaded_arr
    bound = 2.0 * atol + rtol * (np.abs(mu1_stored_arr) + np.abs(mu0_stored_arr))
    deviation = np.abs(tau_reloaded - tau_stored_arr)
    matches = bool(np.all(deviation <= bound))
    return matches, tau_reloaded, {
        "max_deviation": float(deviation.max()) if deviation.size else 0.0,
        "max_bound": float(bound.max()) if bound.size else 0.0,
        "rtol": rtol,
        "atol": atol,
    }
