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

from src.data import DataContractError, FEATURE_COLUMNS

CONTRACT_VERSION = "t04-preprocessing-v1"


class PreprocessingContractError(DataContractError):
    """Raised when the T04 preprocessing contract is violated."""


class IdentityFeatureTransform:
    """The frozen T04 transform: select `f0`-`f11`, in order, at `float64`.

    ``fit`` is a no-op today (no learned state exists) but is kept explicit so
    a future learner-specific transform can share the same fit-on-train-only
    calling convention without a breaking change.
    """

    def __init__(self) -> None:
        self._fitted = False

    def fit(self, train_frame: pd.DataFrame) -> "IdentityFeatureTransform":
        missing = sorted(set(FEATURE_COLUMNS).difference(train_frame.columns))
        if missing:
            raise PreprocessingContractError(f"Training frame is missing columns: {missing}")
        self._fitted = True
        return self

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        if not self._fitted:
            raise PreprocessingContractError("transform() called before fit()")
        missing = sorted(set(FEATURE_COLUMNS).difference(frame.columns))
        if missing:
            raise PreprocessingContractError(f"Frame is missing columns: {missing}")
        selected = frame.loc[:, list(FEATURE_COLUMNS)].astype("float64")
        if tuple(selected.columns) != FEATURE_COLUMNS:
            raise PreprocessingContractError("Transformed output column order drifted from the frozen contract")
        return selected

    def fit_transform(self, train_frame: pd.DataFrame) -> pd.DataFrame:
        return self.fit(train_frame).transform(train_frame)


def preprocessing_contract() -> dict[str, Any]:
    """Serializable, content-hashable description of the frozen T04 contract."""

    return {
        "contract_version": CONTRACT_VERSION,
        "feature_columns": list(FEATURE_COLUMNS),
        "precision": "float64",
        "missing_value_policy": "preserve_for_native_lightgbm_handling",
        "imputation": "none",
        "missingness_indicator_features": "none",
        "fit_boundary": "train_only",
        "learned_state": "none",
        "estimator_specific_branches": {},
        "held_out_application_rule": (
            "apply the identical fitted transform to held-out features at T17; "
            "no refitting, no held-out-informed adjustment"
        ),
    }
