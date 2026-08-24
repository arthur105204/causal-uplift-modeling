from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from src.data import CATEGORICAL_FEATURES, CONTINUOUS_FEATURES, FEATURE_COLUMNS
from src.preprocessing import (
    CONTRACT_VERSION,
    LightGBMFeatureTransform,
    PreprocessingContractError,
    preprocessing_contract,
)


def _frame(rows: int = 20, seed: int = 0, category_span: int = 5) -> pd.DataFrame:
    """Synthetic frame: continuous features are Gaussian floats; categorical
    features are drawn from a small integer-valued float64 token set, matching
    how the released CRITEO categorical tokens are physically stored."""

    rng = np.random.default_rng(seed)
    columns = {}
    for feature in FEATURE_COLUMNS:
        if feature in CONTINUOUS_FEATURES:
            columns[feature] = rng.normal(size=rows)
        else:
            columns[feature] = rng.integers(0, category_span, size=rows).astype("float64")
    return pd.DataFrame(columns)


def test_transform_uses_semantic_dtypes_per_feature() -> None:
    frame = _frame()
    frame["extra_column_not_in_x"] = 1
    transform = LightGBMFeatureTransform()
    output = transform.fit_transform(frame)
    assert tuple(output.columns) == FEATURE_COLUMNS
    assert "extra_column_not_in_x" not in output.columns
    for feature in CONTINUOUS_FEATURES:
        assert str(output[feature].dtype) == "float64"
    for feature in CATEGORICAL_FEATURES:
        assert isinstance(output[feature].dtype, pd.CategoricalDtype)
        assert output[feature].dtype.ordered is False


def test_transform_before_fit_raises() -> None:
    transform = LightGBMFeatureTransform()
    with pytest.raises(PreprocessingContractError, match="before fit"):
        transform.transform(_frame())


def test_fit_rejects_missing_required_columns() -> None:
    frame = _frame().drop(columns="f0")
    transform = LightGBMFeatureTransform()
    with pytest.raises(PreprocessingContractError, match="missing"):
        transform.fit(frame)


def test_transform_rejects_missing_required_columns() -> None:
    transform = LightGBMFeatureTransform().fit(_frame())
    incomplete = _frame().drop(columns="f5")
    with pytest.raises(PreprocessingContractError, match="missing"):
        transform.transform(incomplete)


def test_categorical_vocabulary_is_fit_on_train_only_and_reused_on_validation() -> None:
    train = pd.DataFrame({feature: [0.0, 1.0, 2.0] * 5 for feature in FEATURE_COLUMNS})
    validation = pd.DataFrame({feature: [0.0, 1.0] * 3 for feature in FEATURE_COLUMNS})

    transform = LightGBMFeatureTransform().fit(train)
    train_output = transform.transform(train)
    validation_output = transform.transform(validation)

    for feature in CATEGORICAL_FEATURES:
        train_categories = train_output[feature].dtype.categories
        validation_categories = validation_output[feature].dtype.categories
        # Validation reuses the exact train-fitted vocabulary, never its own.
        assert list(train_categories) == [0.0, 1.0, 2.0]
        assert list(validation_categories) == [0.0, 1.0, 2.0]


def test_unseen_category_becomes_missing_deterministically() -> None:
    train = pd.DataFrame({feature: [0.0, 1.0] * 5 for feature in FEATURE_COLUMNS})
    validation = pd.DataFrame({feature: [0.0, 99.0] for feature in FEATURE_COLUMNS})

    transform = LightGBMFeatureTransform().fit(train)
    output = transform.transform(validation)
    unseen_counts = transform.unseen_category_counts(validation)

    for feature in CATEGORICAL_FEATURES:
        assert pd.isna(output.loc[1, feature])
        assert not pd.isna(output.loc[0, feature])
        assert unseen_counts[feature] == 1


def test_unseen_category_counts_before_fit_raises() -> None:
    transform = LightGBMFeatureTransform()
    with pytest.raises(PreprocessingContractError, match="before fit"):
        transform.unseen_category_counts(_frame())


def test_no_imputation_missing_values_pass_through() -> None:
    frame = _frame(rows=10)
    frame.loc[0, "f0"] = np.nan  # continuous
    frame.loc[3, "f1"] = np.nan  # categorical
    transform = LightGBMFeatureTransform().fit(frame)
    output = transform.transform(frame)
    assert pd.isna(output.loc[0, "f0"])
    assert pd.isna(output.loc[3, "f1"])


def test_row_count_and_order_preserved() -> None:
    frame = _frame(rows=30)
    transform = LightGBMFeatureTransform().fit(frame)
    output = transform.transform(frame)
    assert len(output) == len(frame)
    assert list(output.index) == list(frame.index)


def test_input_column_order_does_not_change_output_order() -> None:
    frame = _frame()
    reordered = frame.loc[:, list(reversed(FEATURE_COLUMNS))]
    transform = LightGBMFeatureTransform().fit(frame)
    output = transform.transform(reordered)
    assert tuple(output.columns) == FEATURE_COLUMNS


def test_deterministic_output_across_repeated_calls() -> None:
    frame = _frame()
    transform = LightGBMFeatureTransform().fit(frame)
    first = transform.transform(frame)
    second = transform.transform(frame)
    pd.testing.assert_frame_equal(first, second)


def test_category_state_is_serializable_and_train_fitted() -> None:
    train = pd.DataFrame({feature: [2.0, 0.0, 1.0] * 5 for feature in FEATURE_COLUMNS})
    transform = LightGBMFeatureTransform().fit(train)
    state = transform.category_state()
    assert set(state.keys()) == set(CATEGORICAL_FEATURES)
    for feature in CATEGORICAL_FEATURES:
        assert state[feature] == [0.0, 1.0, 2.0]
    json.dumps(state)


def test_category_state_before_fit_raises() -> None:
    transform = LightGBMFeatureTransform()
    with pytest.raises(PreprocessingContractError, match="before fit"):
        transform.category_state()


def test_contract_is_serializable_and_content_stable() -> None:
    contract = preprocessing_contract()
    assert contract["contract_version"] == CONTRACT_VERSION
    assert contract["feature_columns"] == list(FEATURE_COLUMNS)
    assert contract["feature_semantics"]["continuous"] == list(CONTINUOUS_FEATURES)
    assert contract["feature_semantics"]["categorical"] == list(CATEGORICAL_FEATURES)
    assert contract["physical_storage_precision"] == "float64"
    assert contract["lightgbm_representation"]["continuous"] == "float64"
    assert contract["lightgbm_representation"]["categorical"]
    assert contract["lightgbm_representation"]["unknown_category"]
    assert contract["fit_boundary"] == "train_only"
    assert contract["imputation"] == "none"
    assert contract["held_out_rule"]
    assert contract["causal_forest_representation"]

    json.dumps(contract)
