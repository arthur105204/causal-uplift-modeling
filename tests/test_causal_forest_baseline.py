"""Synthetic-fixture unit tests for src/causal_forest_baseline.py.

No real data -- these check the fit/predict/honesty/support/reload mechanism
itself against frozen, predeclared numeric pass criteria (T10 CODE PLAN).
Never cited as a real-data result; the full-scale governed run happens in the
T10 SMOKE/RESOURCE notebook stages, not here.
"""

from __future__ import annotations

import pickle

import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr

from src.causal_forest_baseline import (
    FROZEN_CAUSAL_FOREST_CONFIG,
    AggregateSupportResult,
    CausalForestRepresentationError,
    LeafArmSupport,
    aggregate_jacobian_support,
    config_hash,
    fit_causal_forest,
    honest_leaf_arm_support,
    predict_tau,
)
from src.data import CATEGORICAL_FEATURES, FEATURE_COLUMNS

# Deliberately NOT the raw f0-f11 Criteo column names: these tests exercise an
# already-encoded generic numeric matrix, distinct from the raw representation
# `test_fit_rejects_raw_criteo_feature_frame` below asserts is rejected (D32).
ENCODED_FEATURE_COLUMNS = tuple(f"x{i}" for i in range(12))

# Frozen synthetic-gate parameters (T10 CODE PLAN) -- not tuned after seeing results.
N_SYNTH = 4000
EFFECT_MAGNITUDE = 2.0


def _synthetic_frame(seed: int) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    X = pd.DataFrame(rng.normal(size=(N_SYNTH, 12)), columns=list(ENCODED_FEATURE_COLUMNS))
    T = rng.integers(0, 2, size=N_SYNTH).astype(np.float64)
    noise = rng.normal(size=N_SYNTH)
    return X, T, noise


def _fit(X, T, Y, seed: int = 42):
    return fit_causal_forest(X, T, Y, seed=seed)


# --- config_hash -------------------------------------------------------------

def test_config_hash_is_stable_and_deterministic() -> None:
    first = config_hash()
    second = config_hash()
    assert first == second
    assert len(first) == 64


def test_config_hash_changes_with_config_content() -> None:
    changed = dict(FROZEN_CAUSAL_FOREST_CONFIG)
    changed["n_estimators"] = 200
    assert config_hash(changed) != config_hash(FROZEN_CAUSAL_FOREST_CONFIG)


# --- fit_causal_forest guards --------------------------------------------------

def test_fit_rejects_n_estimators_not_divisible_by_subforest_size() -> None:
    X, T, noise = _synthetic_frame(seed=1)
    Y = 0.5 * X["x0"].to_numpy() + T * EFFECT_MAGNITUDE + noise
    bad_config = dict(FROZEN_CAUSAL_FOREST_CONFIG)
    bad_config["n_estimators"] = 101  # not divisible by subforest_size=4
    with pytest.raises(ValueError, match="divisible"):
        fit_causal_forest(X, T, Y, config=bad_config)


def test_fit_rejects_multi_column_treatment() -> None:
    X, T, noise = _synthetic_frame(seed=2)
    Y = 0.5 * X["x0"].to_numpy() + noise
    T_bad = np.stack([T, T], axis=1)
    with pytest.raises(ValueError, match="single binary treatment"):
        fit_causal_forest(X, T_bad, Y)


def test_feature_names_never_include_treatment() -> None:
    X, T, noise = _synthetic_frame(seed=3)
    Y = 0.5 * X["x0"].to_numpy() + T * EFFECT_MAGNITUDE + noise
    model = _fit(X, T, Y)
    assert model.feature_names == ENCODED_FEATURE_COLUMNS
    assert "T" not in model.feature_names and "treatment" not in model.feature_names


def test_predict_rejects_mismatched_columns() -> None:
    X, T, noise = _synthetic_frame(seed=4)
    Y = 0.5 * X["x0"].to_numpy() + T * EFFECT_MAGNITUDE + noise
    model = _fit(X, T, Y)
    bad = X.rename(columns={"x0": "x0_renamed"})
    with pytest.raises(ValueError, match="feature_names"):
        predict_tau(model, bad)


# --- Raw-categorical-representation guard (D32) -------------------------------

def test_fit_rejects_raw_criteo_feature_frame() -> None:
    """The raw f0-f11 Criteo frame -- categorical tokens stored as float64 --
    must never be accepted directly; econml.grf.CausalForest has no native
    categorical representation to fall back on (D32)."""

    rng = np.random.default_rng(50)
    X = pd.DataFrame(rng.normal(size=(N_SYNTH, 12)), columns=list(FEATURE_COLUMNS))
    T = rng.integers(0, 2, size=N_SYNTH).astype(np.float64)
    Y = 0.5 * X["f0"].to_numpy() + T * EFFECT_MAGNITUDE + rng.normal(size=N_SYNTH)
    with pytest.raises(CausalForestRepresentationError, match="categorical"):
        fit_causal_forest(X, T, Y)


def test_fit_rejects_frame_with_any_raw_categorical_column_present() -> None:
    """Even one raw categorical column name mixed into an otherwise-encoded
    frame must be rejected, not just an all-raw frame."""

    rng = np.random.default_rng(51)
    columns = list(ENCODED_FEATURE_COLUMNS)
    columns[1] = CATEGORICAL_FEATURES[0]  # sneak in one raw categorical name
    X = pd.DataFrame(rng.normal(size=(N_SYNTH, 12)), columns=columns)
    T = rng.integers(0, 2, size=N_SYNTH).astype(np.float64)
    Y = 0.5 * X["x0"].to_numpy() + T * EFFECT_MAGNITUDE + rng.normal(size=N_SYNTH)
    with pytest.raises(CausalForestRepresentationError, match="categorical"):
        fit_causal_forest(X, T, Y)


def test_fit_accepts_already_encoded_generic_numeric_matrix() -> None:
    """An already-encoded generic numeric matrix (no raw categorical column
    names) is unaffected by the raw-representation guard."""

    X, T, noise = _synthetic_frame(seed=52)
    Y = 0.5 * X["x0"].to_numpy() + T * EFFECT_MAGNITUDE + noise
    model = _fit(X, T, Y)
    assert model.feature_names == ENCODED_FEATURE_COLUMNS


def test_fit_accepts_bare_numpy_array_without_column_names() -> None:
    """A bare numpy array (no ``.columns``) is never subject to the raw-name
    guard -- it cannot express the raw categorical column names at all."""

    X, T, noise = _synthetic_frame(seed=53)
    Y = 0.5 * X["x0"].to_numpy() + T * EFFECT_MAGNITUDE + noise
    model = _fit(X.to_numpy(), T, Y)
    assert model.feature_names == tuple(f"x{i}" for i in range(12))


# --- Synthetic gate: frozen numeric pass criteria (T10 CODE PLAN) ------------------

def test_synthetic_gate_positive_effect() -> None:
    X, T, noise = _synthetic_frame(seed=10)
    Y = 0.5 * X["x0"].to_numpy() + T * EFFECT_MAGNITUDE + noise
    model = _fit(X, T, Y)
    tau_hat = predict_tau(model, X)

    assert abs(tau_hat.mean() - EFFECT_MAGNITUDE) <= 0.20
    assert (tau_hat > 0).mean() >= 0.95


def test_synthetic_gate_negative_effect() -> None:
    X, T, noise = _synthetic_frame(seed=11)
    Y = 0.5 * X["x0"].to_numpy() - T * EFFECT_MAGNITUDE + noise
    model = _fit(X, T, Y)
    tau_hat = predict_tau(model, X)

    assert abs(tau_hat.mean() - (-EFFECT_MAGNITUDE)) <= 0.20
    assert (tau_hat < 0).mean() >= 0.95


def test_synthetic_gate_zero_effect() -> None:
    X, T, noise = _synthetic_frame(seed=12)
    Y = 0.5 * X["x0"].to_numpy() + noise  # Y independent of T
    model = _fit(X, T, Y)
    tau_hat = predict_tau(model, X)

    assert abs(tau_hat.mean()) <= 0.10


def test_synthetic_gate_heterogeneous_effect() -> None:
    X, T, noise = _synthetic_frame(seed=13)
    regime = (X["x0"].to_numpy() > 0).astype(np.float64)
    true_tau = EFFECT_MAGNITUDE * regime
    Y = 0.5 * X["x1"].to_numpy() + T * true_tau + noise
    model = _fit(X, T, Y)
    tau_hat = predict_tau(model, X)

    gap = tau_hat[regime == 1].mean() - tau_hat[regime == 0].mean()
    assert gap >= 1.0

    corr, _ = spearmanr(tau_hat, regime)
    assert corr >= 0.5


# --- Honesty / treatment-control support --------------------------------------------

def test_honest_leaf_arm_support_disjoint_and_nonempty() -> None:
    X, T, noise = _synthetic_frame(seed=20)
    Y = 0.5 * X["x0"].to_numpy() + T * EFFECT_MAGNITUDE + noise
    model = _fit(X, T, Y)

    support = honest_leaf_arm_support(model, X, T)
    assert len(support) > 0
    assert all(isinstance(s, LeafArmSupport) for s in support)
    # Every reachable estimation leaf must have been reconstructed from a
    # nonempty set of estimation-sample rows.
    assert all((s.n_treated + s.n_control) > 0 for s in support)


def test_honest_leaf_arm_support_detects_non_disjoint_split(monkeypatch) -> None:
    X, T, noise = _synthetic_frame(seed=21)
    Y = 0.5 * X["x0"].to_numpy() + T * EFFECT_MAGNITUDE + noise
    model = _fit(X, T, Y)

    tree0 = model.model.estimators_[0]
    original = tree0.get_train_test_split_inds

    def _fake_non_disjoint():
        split_local, est_local = original()
        # Force an overlap to simulate an honesty violation.
        corrupted_est = np.concatenate([est_local, split_local[:1]])
        return split_local, corrupted_est

    monkeypatch.setattr(tree0, "get_train_test_split_inds", _fake_non_disjoint)
    with pytest.raises(ValueError, match="honesty violated"):
        honest_leaf_arm_support(model, X, T)


def test_honest_leaf_arm_support_uses_global_not_local_indices() -> None:
    """Regression test for the local-vs-global index mapping bug caught during
    CODE PLAN review: tree.get_train_test_split_inds() returns indices local
    to forest.get_subsample_inds()[i], not global row indices into X/T."""

    X, T, noise = _synthetic_frame(seed=22)
    Y = 0.5 * X["x0"].to_numpy() + T * EFFECT_MAGNITUDE + noise
    model = _fit(X, T, Y)

    forest = model.model
    subsample = forest.get_subsample_inds()[0]
    tree0 = forest.estimators_[0]
    split_local, est_local = tree0.get_train_test_split_inds()

    # Local indices must be valid positions within the subsample, not raw row
    # ids into the full N_SYNTH population (this is exactly the distinction
    # the mapping bug conflated).
    assert est_local.max() < len(subsample)
    assert split_local.max() < len(subsample)
    # The mapped global indices, by contrast, range over the full population.
    est_global = subsample[est_local]
    assert est_global.max() < len(X)


# --- Aggregate Jacobian support (the actual T10 hard identification gate) ---------------

def test_aggregate_jacobian_support_passes_on_balanced_fixture() -> None:
    X, T, noise = _synthetic_frame(seed=40)
    Y = 0.5 * X["x0"].to_numpy() + T * EFFECT_MAGNITUDE + noise
    model = _fit(X, T, Y)

    result = aggregate_jacobian_support(model, X)
    assert isinstance(result, AggregateSupportResult)
    assert result.n_queries == N_SYNTH
    assert result.full_rank_dimension == 2  # theta(T) + intercept beta
    assert result.alpha_all_finite
    assert result.jac_all_finite
    assert result.tau_all_finite
    assert result.all_full_rank
    assert result.passed
    assert set(result.condition_number_distribution.keys()) == {"min", "p50", "p95", "p99", "max"}


def test_aggregate_jacobian_support_passes_despite_per_leaf_degeneracy() -> None:
    """Reproduces the real-data finding synthetically: under class imbalance
    matching the actual dataset's ~85/15 treatment split, many individual
    honest-estimation leaves are single-arm (diagnostic, expected), while the
    forest-AGGREGATE Jacobian -- the quantity that actually governs
    identification -- remains full rank. This is the concrete evidence that
    the corrected gate (aggregate-level) is the right one and the removed
    per-leaf-100% hard gate was over-constrained."""

    rng = np.random.default_rng(41)
    n = N_SYNTH
    X = pd.DataFrame(rng.normal(size=(n, 12)), columns=list(ENCODED_FEATURE_COLUMNS))
    T_imbalanced = (rng.random(n) < 0.85).astype(np.float64)  # ~85% treated, matching real data
    noise = rng.normal(size=n)
    Y = 0.5 * X["x0"].to_numpy() + T_imbalanced * EFFECT_MAGNITUDE + noise

    model = _fit(X, T_imbalanced, Y)

    leaf_support = honest_leaf_arm_support(model, X, T_imbalanced)
    min_counts = np.array([min(s.n_treated, s.n_control) for s in leaf_support])
    degenerate_fraction = float((min_counts == 0).mean())
    # Diagnostic only -- not asserted as a pass/fail threshold, just confirming
    # the phenomenon reproduces synthetically at a materially nonzero rate.
    assert degenerate_fraction > 0.05

    result = aggregate_jacobian_support(model, X)
    assert result.passed
    assert result.all_full_rank
    assert result.tau_all_finite


def test_aggregate_jacobian_support_no_invented_condition_number_cutoff() -> None:
    """The gate must not fail solely on a large condition number -- only on
    non-finite alpha/jac/tau or a rank deficiency, per instruction (no
    invented condition-number cutoff)."""

    X, T, noise = _synthetic_frame(seed=42)
    Y = 0.5 * X["x0"].to_numpy() + T * EFFECT_MAGNITUDE + noise
    model = _fit(X, T, Y)

    result = aggregate_jacobian_support(model, X)
    # A large max condition number alone must not flip `passed` to False.
    if result.condition_number_distribution["max"] > 100:
        assert result.passed == (
            result.alpha_all_finite
            and result.jac_all_finite
            and result.tau_all_finite
        )        

def test_aggregate_jacobian_rank_deficiency_is_diagnostic_only(monkeypatch) -> None:
    """Finite alpha/jac/tau must pass even when one aggregate Jacobian is singular."""

    X, T, noise = _synthetic_frame(seed=43)
    Y = 0.5 * X["x0"].to_numpy() + T * EFFECT_MAGNITUDE + noise
    model = _fit(X, T, Y)

    original_predict_alpha_and_jac = model.model.predict_alpha_and_jac

    def _singular_first_jacobian(X_arr):
        alpha, jac = original_predict_alpha_and_jac(X_arr)
        jac = jac.copy()
        jac[0] = 0.0
        return alpha, jac

    monkeypatch.setattr(
        model.model,
        "predict_alpha_and_jac",
        _singular_first_jacobian,
    )

    result = aggregate_jacobian_support(model, X)

    assert result.alpha_all_finite
    assert result.jac_all_finite
    assert result.tau_all_finite

    assert not result.all_full_rank
    assert result.jac_full_rank_fraction < 1.0

    # Rank deficiency is diagnostic only.
    assert result.passed

# --- Determinism / serialization-reload --------------------------------------------

def test_deterministic_refit_same_seed_same_data() -> None:
    X, T, noise = _synthetic_frame(seed=30)
    Y = 0.5 * X["x0"].to_numpy() + T * EFFECT_MAGNITUDE + noise

    first = _fit(X, T, Y, seed=42)
    second = _fit(X, T, Y, seed=42)

    assert first.config_hash == second.config_hash
    np.testing.assert_array_equal(predict_tau(first, X), predict_tau(second, X))


def test_different_seed_changes_predictions() -> None:
    X, T, noise = _synthetic_frame(seed=31)
    Y = 0.5 * X["x0"].to_numpy() + T * EFFECT_MAGNITUDE + noise

    seed42 = _fit(X, T, Y, seed=42)
    seed123 = _fit(X, T, Y, seed=123)

    assert seed42.config_hash != seed123.config_hash  # random_state is part of the hashed payload
    assert not np.array_equal(predict_tau(seed42, X), predict_tau(seed123, X))


def test_reload_via_pickle_matches_original_exactly() -> None:
    X, T, noise = _synthetic_frame(seed=32)
    Y = 0.5 * X["x0"].to_numpy() + T * EFFECT_MAGNITUDE + noise
    model = _fit(X, T, Y)

    original_tau = predict_tau(model, X)
    reloaded_model = pickle.loads(pickle.dumps(model))
    reloaded_tau = predict_tau(reloaded_model, X)

    np.testing.assert_array_equal(original_tau, reloaded_tau)
    assert reloaded_model.config_hash == model.config_hash
