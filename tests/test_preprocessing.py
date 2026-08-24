from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.data import CATEGORICAL_FEATURES, CONTINUOUS_FEATURES, FEATURE_COLUMNS, PRIMARY_OUTCOME, TREATMENT_COLUMN
from src.preprocessing import (
    CausalForestCategoricalEncoder,
    LightGBMFeatureTransform,
    train_validation_split,
)


def _frame(rows: int = 40, seed: int = 0, category_span: int = 5) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    columns = {}
    for feature in FEATURE_COLUMNS:
        if feature in CONTINUOUS_FEATURES:
            columns[feature] = rng.normal(size=rows)
        else:
            columns[feature] = rng.integers(0, category_span, size=rows).astype("float64")
    columns[TREATMENT_COLUMN] = rng.integers(0, 2, size=rows)
    columns[PRIMARY_OUTCOME] = rng.integers(0, 2, size=rows)
    return pd.DataFrame(columns)


# --- LightGBM categorical dtype transform (D32) ---------------------------


def test_transform_uses_semantic_dtypes_per_feature() -> None:
    frame = _frame()
    transform = LightGBMFeatureTransform().fit(frame)
    output = transform.transform(frame)
    assert tuple(output.columns) == FEATURE_COLUMNS
    for feature in CONTINUOUS_FEATURES:
        assert str(output[feature].dtype) == "float64"
    for feature in CATEGORICAL_FEATURES:
        assert isinstance(output[feature].dtype, pd.CategoricalDtype)
        assert output[feature].dtype.ordered is False


def test_transform_before_fit_raises() -> None:
    with pytest.raises(RuntimeError, match="before fit"):
        LightGBMFeatureTransform().transform(_frame())


def test_categorical_vocabulary_is_fit_on_train_only_and_reused_on_validation() -> None:
    train = pd.DataFrame({feature: [0.0, 1.0, 2.0] * 5 for feature in FEATURE_COLUMNS})
    validation = pd.DataFrame({feature: [0.0, 1.0] * 3 for feature in FEATURE_COLUMNS})
    transform = LightGBMFeatureTransform().fit(train)
    val_output = transform.transform(validation)
    for feature in CATEGORICAL_FEATURES:
        assert list(val_output[feature].dtype.categories) == [0.0, 1.0, 2.0]


def test_unseen_category_becomes_nan() -> None:
    train = pd.DataFrame({feature: [0.0, 1.0] * 5 for feature in FEATURE_COLUMNS})
    validation = pd.DataFrame({feature: [0.0, 99.0] for feature in FEATURE_COLUMNS})
    output = LightGBMFeatureTransform().fit(train).transform(validation)
    for feature in CATEGORICAL_FEATURES:
        assert pd.isna(output.loc[1, feature])


# --- Causal Forest top-K + OTHER encoder (D34) -----------------------------


def test_cf_encoder_output_is_one_hot_with_other_bucket() -> None:
    train = pd.DataFrame({feature: [0.0, 1.0, 2.0, 3.0] * 10 for feature in FEATURE_COLUMNS})
    encoder = CausalForestCategoricalEncoder(k=32).fit(train)
    output = encoder.transform(train)
    for feature in CATEGORICAL_FEATURES:
        assert f"{feature}__OTHER" in output.columns
    for feature in CONTINUOUS_FEATURES:
        assert feature in output.columns


def test_cf_encoder_routes_unseen_category_to_other() -> None:
    train = pd.DataFrame({feature: [0.0] * 20 for feature in FEATURE_COLUMNS})
    encoder = CausalForestCategoricalEncoder(k=8).fit(train)
    unseen = pd.DataFrame({feature: [99.0] for feature in FEATURE_COLUMNS})
    output = encoder.transform(unseen)
    for feature in CATEGORICAL_FEATURES:
        assert output.loc[0, f"{feature}__OTHER"] == 1.0


def test_cf_encoder_rejects_invalid_k() -> None:
    with pytest.raises(ValueError, match="32, 16, 8"):
        CausalForestCategoricalEncoder(k=4)


def test_cf_encoder_never_produces_a_single_ordinal_column() -> None:
    train = pd.DataFrame({feature: [0.0, 1.0, 2.0] * 10 for feature in FEATURE_COLUMNS})
    output = CausalForestCategoricalEncoder(k=32).fit_transform(train)
    # every categorical feature must expand into >1 column (never collapse to one rank/ordinal column)
    for feature in CATEGORICAL_FEATURES:
        expanded = [c for c in output.columns if c.startswith(feature + "__")]
        assert len(expanded) > 1


# --- train/validation split -------------------------------------------------


def test_split_is_disjoint_and_complete() -> None:
    frame = _frame(rows=200, seed=1)
    train, val = train_validation_split(frame)
    assert len(train) + len(val) == len(frame)


def test_split_preserves_both_arms_and_outcomes_in_both_halves() -> None:
    frame = _frame(rows=200, seed=2)
    train, val = train_validation_split(frame)
    for part in (train, val):
        assert set(part[TREATMENT_COLUMN].unique()) == {0, 1}
        assert set(part[PRIMARY_OUTCOME].unique()) == {0, 1}


def test_split_is_deterministic_for_a_fixed_seed() -> None:
    frame = _frame(rows=100, seed=3)
    train1, val1 = train_validation_split(frame, seed=7)
    train2, val2 = train_validation_split(frame, seed=7)
    pd.testing.assert_frame_equal(train1, train2)
    pd.testing.assert_frame_equal(val1, val2)
