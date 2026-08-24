"""T04 preprocessing / feature-engineering contract.

Default posture is no-op, per Issue #5: `X` stays exactly the ordered
`f0`-`f11` columns at primary `float64` precision, and missing values pass
through unimputed for LightGBM's native handling (docs/06). No transform is
fit on anything but train rows.

T03-A/T03-B evidence already shows zero missing values across the released
population, so there is currently nothing to impute even in principle; the
identity transform below exists so the fit-on-train-only boundary and the
column/dtype contract are enforced and tested regardless. An estimator-
specific branch is added only if a future learner's API genuinely cannot
accept this shared representation (T04.5) -- none does yet, because no
learner has been implemented.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
from pandas.api.types import CategoricalDtype

from src.data import (
    CATEGORICAL_FEATURES,
    CONTINUOUS_FEATURES,
    DataContractError,
    FEATURE_COLUMNS,
)
CONTRACT_VERSION = "t04-preprocessing-v2"


class PreprocessingContractError(DataContractError):
    """Raised when the preprocessing contract is violated."""

def _require_features(frame: pd.DataFrame) -> None:
    missing = sorted(set(FEATURE_COLUMNS).difference(frame.columns))

    if missing:
        raise PreprocessingContractError(
            f"Frame is missing required feature columns: {missing}"
        )

class LightGBMFeatureTransform:
    """Prepare publisher-defined continuous/categorical features for LightGBM."""

    def __init__(self) -> None:
        self._fitted = False
        self._category_dtypes: dict[str, CategoricalDtype] = {}

    def fit(
        self,
        train_frame: pd.DataFrame,
    ) -> "LightGBMFeatureTransform":
        _require_features(train_frame)

        category_dtypes = {}

        for feature in CATEGORICAL_FEATURES:
            values = (
                train_frame[feature]
                .dropna()
                .astype("float64")
                .unique()
            )

            categories = pd.Index(values).sort_values()

            category_dtypes[feature] = CategoricalDtype(
                categories=categories,
                ordered=False,
            )

        self._category_dtypes = category_dtypes
        self._fitted = True

        return self

    def transform(
        self,
        frame: pd.DataFrame,
    ) -> pd.DataFrame:
        if not self._fitted:
            raise PreprocessingContractError(
                "transform() called before fit()"
            )

        _require_features(frame)

        output = frame.loc[:, list(FEATURE_COLUMNS)].copy()

        for feature in CONTINUOUS_FEATURES:
            output[feature] = output[feature].astype("float64")

        for feature in CATEGORICAL_FEATURES:
            output[feature] = pd.Categorical(
                output[feature].astype("float64"),
                dtype=self._category_dtypes[feature],
            )

        if tuple(output.columns) != FEATURE_COLUMNS:
            raise PreprocessingContractError(
                "Feature column order drifted from the contract"
            )

        return output

    def fit_transform(
        self,
        train_frame: pd.DataFrame,
    ) -> pd.DataFrame:
        return self.fit(train_frame).transform(train_frame)

    def unseen_category_counts(
        self,
        frame: pd.DataFrame,
    ) -> dict[str, int]:
        if not self._fitted:
            raise PreprocessingContractError(
                "unseen_category_counts() called before fit()"
            )

        result = {}

        for feature in CATEGORICAL_FEATURES:
            categories = self._category_dtypes[feature].categories
            values = frame[feature]

            unseen = values.notna() & ~values.isin(categories)
            result[feature] = int(unseen.sum())

        return result

    def category_state(self) -> dict[str, list[float]]:
        if not self._fitted:
            raise PreprocessingContractError(
                "category_state() called before fit()"
            )

        return {
            feature: [
                float(value)
                for value in dtype.categories.tolist()
            ]
            for feature, dtype in self._category_dtypes.items()
        }


def preprocessing_contract() -> dict[str, Any]:
    """Serializable, content-hashable description of the frozen T04 contract."""

    return {
        "contract_version": CONTRACT_VERSION,
        "feature_columns": list(FEATURE_COLUMNS),
        "feature_semantics": {
            "continuous": list(CONTINUOUS_FEATURES),
            "categorical": list(CATEGORICAL_FEATURES),
        },
        "physical_storage_precision": "float64",
        "lightgbm_representation": {
            "continuous": "float64",
            "categorical": "train-fitted pandas unordered category",
            "unknown_category": "missing",
        },
        "fit_boundary": "train_only",
        "learned_state": "categorical vocabularies",
        "imputation": "none",
        "held_out_rule": (
            "reuse the frozen training-fitted category vocabularies; "
            "never refit on held-out data"
        ),
        "causal_forest_representation": (
            "blocked until an explicit categorical encoding contract "
            "is accepted"
        ),
    }
