from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.audit import FEATURE_COLUMNS
from src.preprocessing import (
    CONTRACT_VERSION,
    IdentityFeatureTransform,
    PreprocessingContractError,
    preprocessing_contract,
)


def _frame(rows: int = 20, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame({feature: rng.normal(size=rows) for feature in FEATURE_COLUMNS})


def test_transform_selects_exact_ordered_columns_at_float64() -> None:
    frame = _frame().astype("float32")
    frame["extra_column_not_in_x"] = 1
    transform = IdentityFeatureTransform()
    output = transform.fit_transform(frame)
    assert tuple(output.columns) == FEATURE_COLUMNS
    assert all(str(dtype) == "float64" for dtype in output.dtypes)
    assert "extra_column_not_in_x" not in output.columns


def test_transform_before_fit_raises() -> None:
    transform = IdentityFeatureTransform()
    with pytest.raises(PreprocessingContractError, match="before fit"):
        transform.transform(_frame())


def test_fit_rejects_missing_required_columns() -> None:
    frame = _frame().drop(columns="f0")
    transform = IdentityFeatureTransform()
    with pytest.raises(PreprocessingContractError, match="missing columns"):
        transform.fit(frame)


def test_transform_rejects_missing_required_columns() -> None:
    transform = IdentityFeatureTransform().fit(_frame())
    incomplete = _frame().drop(columns="f5")
    with pytest.raises(PreprocessingContractError, match="missing columns"):
        transform.transform(incomplete)


def test_fit_uses_train_rows_only_then_applies_unchanged_to_validation() -> None:
    train = _frame(rows=50, seed=1)
    validation = _frame(rows=10, seed=2)
    transform = IdentityFeatureTransform()
    transform.fit(train)
    # No aspect of `validation` influenced `fit`; transform is a pure per-row mapping.
    output = transform.transform(validation)
    pd.testing.assert_frame_equal(output, validation.loc[:, list(FEATURE_COLUMNS)].astype("float64"))


def test_deterministic_output_across_repeated_calls() -> None:
    frame = _frame()
    transform = IdentityFeatureTransform().fit(frame)
    first = transform.transform(frame)
    second = transform.transform(frame)
    pd.testing.assert_frame_equal(first, second)


def test_row_count_and_order_preserved() -> None:
    frame = _frame(rows=30)
    transform = IdentityFeatureTransform().fit(frame)
    output = transform.transform(frame)
    assert len(output) == len(frame)
    assert list(output.index) == list(frame.index)


def test_input_column_order_does_not_change_output_order() -> None:
    frame = _frame()
    reordered = frame.loc[:, list(reversed(FEATURE_COLUMNS))]
    transform = IdentityFeatureTransform().fit(frame)
    output = transform.transform(reordered)
    assert tuple(output.columns) == FEATURE_COLUMNS


def test_missing_values_pass_through_unimputed() -> None:
    frame = _frame(rows=10)
    frame.loc[0, "f0"] = np.nan
    frame.loc[3, "f7"] = np.nan
    transform = IdentityFeatureTransform().fit(frame)
    output = transform.transform(frame)
    assert pd.isna(output.loc[0, "f0"])
    assert pd.isna(output.loc[3, "f7"])
    assert output.isna().sum().sum() == 2


def test_unseen_edge_values_pass_through() -> None:
    train = _frame(rows=20, seed=5)
    transform = IdentityFeatureTransform().fit(train)
    edge_cases = pd.DataFrame({feature: [1e300, -1e300, 0.0] for feature in FEATURE_COLUMNS})
    output = transform.transform(edge_cases)
    np.testing.assert_array_equal(output.to_numpy(), edge_cases.to_numpy())


def test_contract_is_serializable_and_content_stable() -> None:
    contract = preprocessing_contract()
    assert contract["contract_version"] == CONTRACT_VERSION
    assert contract["feature_columns"] == list(FEATURE_COLUMNS)
    assert contract["imputation"] == "none"
    assert contract["missingness_indicator_features"] == "none"
    assert contract["fit_boundary"] == "train_only"
    import json

    # Must round-trip through JSON with no non-serializable content.
    json.dumps(contract)
