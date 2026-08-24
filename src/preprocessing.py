"""Feature preprocessing and train/validation splitting.

Two model families need two different representations of the same
categorical features (D32/D34), and both are fit on TRAIN ONLY then reused
unchanged on validation:

- LightGBM (response model, T-Learner, X-Learner): pandas categorical dtype,
  using LightGBM's native categorical split handling.
- Causal Forest (econml.grf.CausalForest): no native categorical support, so
  categorical features are frequency-capped top-K one-hot encoded, with a
  trailing OTHER bucket for everything outside the top K (including unseen
  categories at transform time). A single ordinal/rank column is deliberately
  avoided -- that would reintroduce the ordinal-structure bug D32 exists to
  fix. K is chosen for resource feasibility, never by model performance.
"""

from __future__ import annotations

import pandas as pd
from pandas.api.types import CategoricalDtype
from sklearn.model_selection import train_test_split

from src.data import (
    CATEGORICAL_FEATURES,
    CONTINUOUS_FEATURES,
    FEATURE_COLUMNS,
    PRIMARY_OUTCOME,
    TREATMENT_COLUMN,
)


def _require_features(frame: pd.DataFrame) -> None:
    missing = sorted(set(FEATURE_COLUMNS).difference(frame.columns))
    if missing:
        raise ValueError(f"Frame is missing required feature columns: {missing}")


class LightGBMFeatureTransform:
    """Continuous features stay float64; categorical features become a
    train-fitted pandas categorical dtype so LightGBM uses native categorical
    splits instead of treating the token as an ordered number."""

    def __init__(self) -> None:
        self._fitted = False
        self._category_dtypes: dict[str, CategoricalDtype] = {}

    def fit(self, train_frame: pd.DataFrame) -> "LightGBMFeatureTransform":
        _require_features(train_frame)
        self._category_dtypes = {
            feature: CategoricalDtype(
                categories=pd.Index(train_frame[feature].dropna().astype("float64").unique()).sort_values(),
                ordered=False,
            )
            for feature in CATEGORICAL_FEATURES
        }
        self._fitted = True
        return self

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        if not self._fitted:
            raise RuntimeError("transform() called before fit()")
        _require_features(frame)
        output = frame.loc[:, list(FEATURE_COLUMNS)].copy()
        for feature in CONTINUOUS_FEATURES:
            output[feature] = output[feature].astype("float64")
        for feature in CATEGORICAL_FEATURES:
            output[feature] = pd.Categorical(
                output[feature].astype("float64"), dtype=self._category_dtypes[feature]
            )
        return output

    def fit_transform(self, train_frame: pd.DataFrame) -> pd.DataFrame:
        return self.fit(train_frame).transform(train_frame)


CATEGORICAL_ENCODER_K_LADDER = (32, 16, 8)


def _category_column(feature: str, value: float) -> str:
    return f"{feature}__cat_{value!r}"


def _other_column(feature: str) -> str:
    return f"{feature}__OTHER"


class CausalForestCategoricalEncoder:
    """Frequency-capped top-K + OTHER one-hot encoding for Causal Forest's
    categorical features. Fit on TRAIN only, reused unchanged afterwards.
    Continuous features pass through unchanged."""

    def __init__(self, k: int = 32) -> None:
        if k not in CATEGORICAL_ENCODER_K_LADDER:
            raise ValueError(f"k={k!r} must be one of {CATEGORICAL_ENCODER_K_LADDER}")
        self.k = k
        self._fitted = False
        self._vocabularies: dict[str, list[float]] = {}

    def fit(self, train_frame: pd.DataFrame) -> "CausalForestCategoricalEncoder":
        _require_features(train_frame)
        vocabularies = {}
        for feature in CATEGORICAL_FEATURES:
            values = train_frame[feature].astype("float64")
            counts = values.value_counts()
            # Deterministic tie-break: (count desc, value asc).
            ranked = sorted(counts.index.tolist(), key=lambda v: (-counts[v], v))
            vocabularies[feature] = sorted(float(v) for v in ranked[: self.k])
        self._vocabularies = vocabularies
        self._fitted = True
        return self

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        if not self._fitted:
            raise RuntimeError("transform() called before fit()")
        _require_features(frame)
        blocks = [frame[[feature]].astype("float64") for feature in CONTINUOUS_FEATURES]
        for feature in CATEGORICAL_FEATURES:
            vocab = self._vocabularies[feature]
            values = frame[feature].astype("float64")
            in_vocab = values.isin(vocab)
            block = {_category_column(feature, v): (values == v).astype("float64") for v in vocab}
            block[_other_column(feature)] = (~in_vocab).astype("float64")
            blocks.append(pd.DataFrame(block, index=frame.index))
        return pd.concat(blocks, axis=1)

    def fit_transform(self, train_frame: pd.DataFrame) -> pd.DataFrame:
        return self.fit(train_frame).transform(train_frame)


SPLIT_SEED = 42
VALIDATION_FRACTION = 0.15


def train_validation_split(
    frame: pd.DataFrame,
    *,
    validation_fraction: float = VALIDATION_FRACTION,
    seed: int = SPLIT_SEED,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """One seeded, joint-(treatment, conversion)-stratified train/validation
    split, so both treatment arms and both outcome classes are represented
    in both halves."""

    strata = frame[TREATMENT_COLUMN].astype(str) + "_" + frame[PRIMARY_OUTCOME].astype(str)
    train_frame, val_frame = train_test_split(
        frame, test_size=validation_fraction, random_state=seed, stratify=strata
    )
    return train_frame.reset_index(drop=True), val_frame.reset_index(drop=True)
