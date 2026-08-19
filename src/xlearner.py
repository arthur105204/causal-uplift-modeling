"""X-Learner correctness primitives (T09): fold assignment, OOF-coverage/
opposite-fold assertions, pseudo-outcome construction, and the final weighted
combination. Fitting stays in src/lightgbm_baseline.py; causal-ranking
evaluation stays in src/metrics.py. This module adds only the X-Learner-
specific logic that doesn't belong in either.
"""

from __future__ import annotations

import numpy as np
from sklearn.model_selection import train_test_split

from src.data import DataContractError


class XLearnerContractError(DataContractError):
    """Raised when a T09 X-Learner construction/validation invariant is violated."""


def assign_folds(source_row_id, treatment, outcome, *, seed: int = 42):
    """Deterministic joint-(T,Y)-stratified 50/50 split of the given training
    population into Fold A / Fold B. Reuses the same train_test_split
    stratification mechanism already used by src/split.py's assign_split() and
    T07/T08's SMOKE sampling -- no new sampling algorithm.
    """

    source_row_id = np.asarray(source_row_id)
    treatment = np.asarray(treatment)
    outcome = np.asarray(outcome)
    if not (len(source_row_id) == len(treatment) == len(outcome)):
        raise XLearnerContractError("source_row_id, treatment, outcome must have equal length")
    if len(source_row_id) == 0:
        raise XLearnerContractError("Empty population; cannot assign folds")

    strata = np.array([f"{int(t)}_{int(y)}" for t, y in zip(treatment, outcome)])
    fold_a_ids, fold_b_ids = train_test_split(
        source_row_id, train_size=0.5, random_state=seed, stratify=strata,
    )
    fold_a_ids = np.sort(fold_a_ids)
    fold_b_ids = np.sort(fold_b_ids)
    if set(fold_a_ids.tolist()) & set(fold_b_ids.tolist()):
        raise XLearnerContractError("Fold A and Fold B are not disjoint")
    if len(fold_a_ids) + len(fold_b_ids) != len(source_row_id):
        raise XLearnerContractError("Fold A/B union does not reconcile with the input population")
    return fold_a_ids, fold_b_ids


def assert_opposite_fold(row_fold_labels, prediction_fold_labels, *, name: str) -> None:
    """Every row's nuisance prediction must come from the model fit on the
    OPPOSITE fold -- never the row's own fold."""

    row_fold_labels = np.asarray(row_fold_labels)
    prediction_fold_labels = np.asarray(prediction_fold_labels)
    if len(row_fold_labels) != len(prediction_fold_labels):
        raise XLearnerContractError(f"{name}: row/prediction fold-label length mismatch")
    same_fold = row_fold_labels == prediction_fold_labels
    if same_fold.any():
        raise XLearnerContractError(
            f"{name}: {int(same_fold.sum())} row(s) received a nuisance prediction from their own fold"
        )


def assert_full_oof_coverage(expected_source_row_id, oof_source_row_id, *, name: str) -> None:
    """Every expected training row must appear in the OOF prediction set
    exactly once -- no duplicates, no gaps."""

    expected = np.asarray(expected_source_row_id)
    actual = np.asarray(oof_source_row_id)
    if len(actual) != len(np.unique(actual)):
        raise XLearnerContractError(f"{name}: duplicate row IDs in OOF predictions")
    if set(expected.tolist()) != set(actual.tolist()):
        raise XLearnerContractError(f"{name}: OOF prediction set does not exactly match the expected row set")


def compute_pseudo_outcomes(treatment, outcome, mu0_oof, mu1_oof):
    """D1 = Y - mu0_oof on treated rows; D0 = mu1_oof - Y on control rows.

    Every row must already carry both mu0_oof and mu1_oof (assembled from the
    opposite fold, regardless of the row's own arm) before calling this --
    D1/D0 then simply select which existing OOF column applies to that row's
    arm. Validates finiteness/[0,1]-bounds on both nuisance columns first.
    """

    treatment = np.asarray(treatment, dtype=np.float64)
    outcome = np.asarray(outcome, dtype=np.float64)
    mu0_oof = np.asarray(mu0_oof, dtype=np.float64)
    mu1_oof = np.asarray(mu1_oof, dtype=np.float64)

    lengths = {len(treatment), len(outcome), len(mu0_oof), len(mu1_oof)}
    if len(lengths) != 1:
        raise XLearnerContractError(f"Mismatched input lengths: {lengths}")

    for name, arr in (("outcome", outcome), ("mu0_oof", mu0_oof), ("mu1_oof", mu1_oof)):
        if not np.isfinite(arr).all():
            raise XLearnerContractError(f"{name} contains non-finite values")
    for name, arr in (("mu0_oof", mu0_oof), ("mu1_oof", mu1_oof)):
        if (arr < 0).any() or (arr > 1).any():
            raise XLearnerContractError(f"{name} contains values outside [0,1]")

    treated_mask = treatment == 1
    control_mask = treatment == 0
    if not treated_mask.any():
        raise XLearnerContractError("No treated rows; cannot construct D1")
    if not control_mask.any():
        raise XLearnerContractError("No control rows; cannot construct D0")

    d1 = outcome[treated_mask] - mu0_oof[treated_mask]
    d0 = mu1_oof[control_mask] - outcome[control_mask]
    return d1, d0, treated_mask, control_mask


def empirical_treatment_rate(treatment) -> float:
    """g(x) primary rule (this project): training-only empirical treatment
    rate -- a fixed constant, not a covariate-varying estimated propensity,
    absent a documented design assignment probability (none found in
    docs/01_causal_contract.md or docs/02_data_contract.md as of T09)."""

    treatment = np.asarray(treatment, dtype=np.float64)
    if len(treatment) == 0:
        raise XLearnerContractError("Empty treatment array; cannot compute empirical treatment rate")
    unique = set(treatment.tolist())
    if not unique.issubset({0.0, 1.0}):
        raise XLearnerContractError(f"treatment contains values outside {{0,1}}: {unique}")
    return float(np.mean(treatment == 1))


def combine_tau(tau1_hat, tau0_hat, g):
    """tau_hat(x) = g(x)*tau0_hat(x) + (1-g(x))*tau1_hat(x).

    `g` may be a single float (this project's frozen constant rule) or an
    array matching tau1_hat/tau0_hat's shape (for a future covariate-varying
    g, not used by the primary rule).
    """

    tau1_hat = np.asarray(tau1_hat, dtype=np.float64)
    tau0_hat = np.asarray(tau0_hat, dtype=np.float64)
    if tau1_hat.shape != tau0_hat.shape:
        raise XLearnerContractError(
            f"tau1_hat shape {tau1_hat.shape} does not match tau0_hat shape {tau0_hat.shape}"
        )
    for name, arr in (("tau1_hat", tau1_hat), ("tau0_hat", tau0_hat)):
        if not np.isfinite(arr).all():
            raise XLearnerContractError(f"{name} contains non-finite values")

    if isinstance(g, (int, float)):
        if not (0.0 <= float(g) <= 1.0):
            raise XLearnerContractError(f"g must lie in [0,1], got {g}")
        g_arr = np.full_like(tau1_hat, float(g))
    else:
        g_arr = np.asarray(g, dtype=np.float64)
        if g_arr.shape != tau1_hat.shape:
            raise XLearnerContractError("g array must match tau1_hat/tau0_hat shape")
        if not ((g_arr >= 0.0) & (g_arr <= 1.0)).all():
            raise XLearnerContractError("g must lie in [0,1] elementwise")

    return g_arr * tau0_hat + (1.0 - g_arr) * tau1_hat
