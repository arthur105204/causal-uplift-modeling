"""Synthetic-fixture unit tests for src/lightgbm_baseline.py.

No real data, no full dataset needed -- these check the fit/predict/config-hash
mechanism itself (train-only fitting, early-stopping sanity, bounds, column
contracts, determinism, categorical-feature semantics per D32), mirroring
tests/test_split.py's and tests/test_preprocessing.py's small-fixture
convention. The full-scale governed run happens in kaggle/02_uplift_modeling.ipynb,
not here.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.data import CATEGORICAL_FEATURES, CONTINUOUS_FEATURES, FEATURE_COLUMNS
from src.lightgbm_baseline import (
    EFFECT_NUM_BOOST_ROUND,
    FROZEN_BINARY_CONFIG,
    FROZEN_REGRESSION_CONFIG,
    NUM_BOOST_ROUND_CAP,
    config_hash,
    fit_binary_classifier,
    fit_regressor,
    predict_probabilities,
    predict_values,
    regression_config_hash,
)
from src.preprocessing import LightGBMFeatureTransform


def _raw_frame(n: int, rule, seed: int) -> tuple[pd.DataFrame, np.ndarray]:
    """Publisher-shaped raw frame: continuous features are Gaussian floats,
    categorical features are a small float64-token set -- never cast to
    LightGBM representation here, so callers explicitly choose whether to."""

    rng = np.random.default_rng(seed)
    columns = {}
    for feature in FEATURE_COLUMNS:
        if feature in CONTINUOUS_FEATURES:
            columns[feature] = rng.normal(size=n)
        else:
            columns[feature] = rng.integers(0, 6, size=n).astype("float64")
    X = pd.DataFrame(columns)
    y = rule(X).astype(np.float64)
    return X, y


def _frame(n: int, rule, seed: int) -> tuple[pd.DataFrame, np.ndarray]:
    """A single train-only LightGBM-ready frame (category vocab fit on itself)."""

    raw, y = _raw_frame(n, rule, seed)
    X = LightGBMFeatureTransform().fit_transform(raw)
    return X, y


def _train_val_pair(
    n_train: int, rule_train, seed_train: int, n_val: int, rule_val, seed_val: int
) -> tuple[pd.DataFrame, np.ndarray, pd.DataFrame, np.ndarray]:
    """Train/validation LightGBM-ready pair sharing one train-fitted category
    vocabulary -- the same OOF/held-out application rule D32 requires."""

    raw_train, y_train = _raw_frame(n_train, rule_train, seed_train)
    raw_val, y_val = _raw_frame(n_val, rule_val, seed_val)
    transform = LightGBMFeatureTransform().fit(raw_train)
    X_train = transform.transform(raw_train)
    X_val = transform.transform(raw_val)
    return X_train, y_train, X_val, y_val


def test_config_hash_is_stable_and_deterministic() -> None:
    first = config_hash()
    second = config_hash()
    assert first == second
    assert len(first) == 64


def test_config_hash_changes_with_config_content() -> None:
    changed = dict(FROZEN_BINARY_CONFIG)
    changed["learning_rate"] = 0.05
    assert config_hash(changed) != config_hash(FROZEN_BINARY_CONFIG)


# --- Categorical-semantics guard (D32) ---------------------------------------

def test_fit_rejects_raw_float_categorical_tokens() -> None:
    """Categorical features must be pandas categorical, not raw float64 --
    the exact bug D32 fixes."""

    X_train, y_train = _raw_frame(200, lambda X: (X["f0"] > 0), seed=100)
    X_val, y_val = _raw_frame(100, lambda X: (X["f0"] > 0), seed=101)
    with pytest.raises(ValueError, match="categorical"):
        fit_binary_classifier(X_train, y_train, X_val, y_val)


def test_fit_regressor_rejects_raw_float_categorical_tokens() -> None:
    X_train, y_train = _raw_frame(200, lambda X: X["f0"], seed=102)
    with pytest.raises(ValueError, match="categorical"):
        fit_regressor(X_train, y_train)


def test_fit_rejects_continuous_feature_cast_to_categorical() -> None:
    X_train, y_train = _frame(200, lambda X: (X["f0"] > 0), seed=103)
    X_val, y_val = _frame(100, lambda X: (X["f0"] > 0), seed=104)
    X_train_bad = X_train.copy()
    X_train_bad["f0"] = X_train_bad["f0"].astype("category")
    with pytest.raises(ValueError, match="continuous"):
        fit_binary_classifier(X_train_bad, y_train, X_val, y_val)


def test_predict_rejects_raw_float_categorical_tokens() -> None:
    """Prediction-time representation must match training representation."""

    X_train, y_train, X_val, y_val = _train_val_pair(
        200, lambda X: (X["f0"] > 0), 105, 100, lambda X: (X["f0"] > 0), 106
    )
    model = fit_binary_classifier(X_train, y_train, X_val, y_val)
    raw_val, _ = _raw_frame(50, lambda X: (X["f0"] > 0), seed=107)
    with pytest.raises(ValueError, match="categorical"):
        predict_probabilities(model, raw_val)


def test_correct_categorical_representation_is_accepted() -> None:
    X_train, y_train, X_val, y_val = _train_val_pair(
        300, lambda X: (X["f1"] > 2), 108, 150, lambda X: (X["f1"] > 2), 109
    )
    model = fit_binary_classifier(X_train, y_train, X_val, y_val)
    probabilities = predict_probabilities(model, X_val)
    assert np.isfinite(probabilities).all()


# --- Binary classifier fit/predict mechanics ---------------------------------

def test_fit_uses_train_only_for_parameters_not_validation() -> None:
    """Train rule: y=1 iff f0>0. Validation is given the OPPOSITE rule. If
    fitting used validation rows for parameters (not just early stopping), the
    model would be pulled toward the inverted rule; it must not be."""

    X_train, y_train, X_val, y_val = _train_val_pair(
        400, lambda X: (X["f0"] > 0), 1, 200, lambda X: (X["f0"] <= 0), 2
    )

    model = fit_binary_classifier(X_train, y_train, X_val, y_val)
    probabilities = predict_probabilities(model, X_train)

    high_f0 = X_train["f0"] > 0
    assert probabilities[high_f0.to_numpy()].mean() > probabilities[~high_f0.to_numpy()].mean()


def test_early_stopping_selects_reasonable_best_iteration() -> None:
    X_train, y_train, X_val, y_val = _train_val_pair(
        400, lambda X: (X["f0"] > 0), 3, 200, lambda X: (X["f0"] > 0), 4
    )

    model = fit_binary_classifier(X_train, y_train, X_val, y_val)
    assert 1 <= model.best_iteration <= NUM_BOOST_ROUND_CAP


def test_predictions_bounded_and_finite() -> None:
    X_train, y_train, X_val, y_val = _train_val_pair(
        300, lambda X: (X["f2"] > 0), 5, 150, lambda X: (X["f2"] > 0), 6
    )

    model = fit_binary_classifier(X_train, y_train, X_val, y_val)
    probabilities = predict_probabilities(model, X_val)
    assert np.isfinite(probabilities).all()
    assert (probabilities >= 0).all() and (probabilities <= 1).all()


def test_predict_rejects_mismatched_columns() -> None:
    X_train, y_train, X_val, y_val = _train_val_pair(
        200, lambda X: (X["f0"] > 0), 7, 100, lambda X: (X["f0"] > 0), 8
    )
    model = fit_binary_classifier(X_train, y_train, X_val, y_val)

    bad = X_val.rename(columns={"f0": "f0_renamed"})
    with pytest.raises(ValueError, match="feature_names"):
        predict_probabilities(model, bad)


def test_fit_rejects_mismatched_train_val_columns() -> None:
    X_train, y_train, X_val, y_val = _train_val_pair(
        200, lambda X: (X["f0"] > 0), 9, 100, lambda X: (X["f0"] > 0), 10
    )
    X_val_bad = X_val.rename(columns={"f0": "f0_renamed"})

    with pytest.raises(ValueError, match="identical"):
        fit_binary_classifier(X_train, y_train, X_val_bad, y_val)


def test_deterministic_refit_same_seed_same_data() -> None:
    X_train, y_train, X_val, y_val = _train_val_pair(
        300, lambda X: (X["f3"] > 2), 11, 150, lambda X: (X["f3"] > 2), 12
    )

    first = fit_binary_classifier(X_train, y_train, X_val, y_val)
    second = fit_binary_classifier(X_train, y_train, X_val, y_val)

    assert first.best_iteration == second.best_iteration
    assert first.config_hash == second.config_hash
    np.testing.assert_array_equal(
        predict_probabilities(first, X_val), predict_probabilities(second, X_val)
    )


# --- Regression primitive (T09) ---------------------------------------------

def test_binary_config_and_hash_unchanged_by_regression_addition() -> None:
    """Adding the regression primitive must not alter the existing binary
    config content or its hash convention."""

    assert FROZEN_BINARY_CONFIG["objective"] == "binary"
    assert config_hash() == config_hash(FROZEN_BINARY_CONFIG)


def test_fit_regressor_uses_fixed_round_count_no_early_stopping() -> None:
    X_train, y_train = _frame(300, lambda X: X["f0"] + X["f1"], seed=20)
    model = fit_regressor(X_train, y_train)
    assert model.num_boost_round == EFFECT_NUM_BOOST_ROUND
    assert model.booster.num_trees() == EFFECT_NUM_BOOST_ROUND


def test_fit_regressor_rejects_binary_objective() -> None:
    X_train, y_train = _frame(200, lambda X: X["f0"], seed=21)
    bad_config = dict(FROZEN_REGRESSION_CONFIG)
    bad_config["objective"] = "binary"
    with pytest.raises(ValueError, match="regression objective"):
        fit_regressor(X_train, y_train, config=bad_config)


def test_fit_regressor_predicts_signed_continuous_values() -> None:
    """Pseudo-outcome-like target: signed, continuous, not in [0,1]."""

    X_train, y_train = _frame(400, lambda X: 5 * X["f2"] - 3 * X["f3"], seed=22)
    model = fit_regressor(X_train, y_train)
    predictions = predict_values(model, X_train)
    assert np.isfinite(predictions).all()
    assert (predictions < 0).any() and (predictions > 0).any()


def test_predict_values_rejects_mismatched_columns() -> None:
    X_train, y_train = _frame(200, lambda X: X["f0"], seed=23)
    model = fit_regressor(X_train, y_train)
    bad = X_train.rename(columns={"f0": "f0_renamed"})
    with pytest.raises(ValueError, match="feature_names"):
        predict_values(model, bad)


def test_regression_config_hash_deterministic_and_distinct_from_binary() -> None:
    assert regression_config_hash() == regression_config_hash(FROZEN_REGRESSION_CONFIG)
    assert regression_config_hash() != config_hash()


def test_deterministic_refit_regressor_same_seed_same_data() -> None:
    X_train, y_train = _frame(300, lambda X: X["f4"] - X["f5"], seed=24)
    first = fit_regressor(X_train, y_train)
    second = fit_regressor(X_train, y_train)
    assert first.config_hash == second.config_hash
    np.testing.assert_array_equal(predict_values(first, X_train), predict_values(second, X_train))
