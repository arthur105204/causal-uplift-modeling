"""Reusable, causal-agnostic LightGBM binary-classifier fitting primitive (T07).

Knows nothing about arms, treatment, or causal roles -- it fits one LightGBM
binary classifier with a frozen, hashed configuration and validation-only
early stopping. T07's Response baseline calls this once on (train, train)/
(validation, validation); a future T-Learner task can call it twice (once per
arm-subset) without a new abstraction. The causal interpretation of inputs and
outputs stays visible in the caller (notebook), not here.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

import lightgbm as lgb
import numpy as np

FROZEN_LIGHTGBM_VERSION = "4.7.0"

# Every value left at LightGBM's own library default except where a project
# contract forces it (objective, seed, determinism). No hyperparameter search,
# no tuning: this is the one predeclared configuration T07 uses.
FROZEN_BINARY_CONFIG: dict[str, object] = {
    "objective": "binary",
    "metric": "binary_logloss",
    "boosting_type": "gbdt",
    "learning_rate": 0.1,
    "num_leaves": 31,
    "max_depth": -1,
    "min_data_in_leaf": 20,
    "feature_fraction": 1.0,
    "bagging_fraction": 1.0,
    "bagging_freq": 0,
    "lambda_l1": 0.0,
    "lambda_l2": 0.0,
    "seed": 42,
    "deterministic": True,
    "force_row_wise": True,
    "num_threads": 0,
    "verbosity": -1,
}
NUM_BOOST_ROUND_CAP = 2000
EARLY_STOPPING_ROUNDS = 50


def config_hash(config: dict[str, object] | None = None) -> str:
    """Deterministic sha256 of the frozen config plus its two external caps.

    Computed the same way as T06's ``definitions_sha256`` (sorted-JSON, then
    sha256) so the two share one hashing convention across this project.
    """

    payload = dict(config if config is not None else FROZEN_BINARY_CONFIG)
    payload["num_boost_round_cap"] = NUM_BOOST_ROUND_CAP
    payload["early_stopping_rounds"] = EARLY_STOPPING_ROUNDS
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


@dataclass(frozen=True)
class FittedBinaryClassifier:
    booster: lgb.Booster
    best_iteration: int
    config_hash: str
    feature_names: tuple[str, ...]


def fit_binary_classifier(
    X_train,
    y_train,
    X_val,
    y_val,
    *,
    config: dict[str, object] | None = None,
    seed: int = 42,
) -> FittedBinaryClassifier:
    """Fit one LightGBM binary classifier: parameters from X_train/y_train only,
    best_iteration chosen by early stopping against X_val/y_val only."""

    effective_config = dict(config if config is not None else FROZEN_BINARY_CONFIG)
    effective_config["seed"] = seed
    frozen_hash = config_hash(effective_config)

    feature_names = tuple(X_train.columns)
    if tuple(X_val.columns) != feature_names:
        raise ValueError("X_train and X_val must share identical, identically-ordered columns")

    train_set = lgb.Dataset(X_train, label=y_train, feature_name=list(feature_names), free_raw_data=False)
    val_set = lgb.Dataset(X_val, label=y_val, feature_name=list(feature_names), reference=train_set, free_raw_data=False)

    booster = lgb.train(
        effective_config,
        train_set,
        num_boost_round=NUM_BOOST_ROUND_CAP,
        valid_sets=[val_set],
        valid_names=["validation"],
        callbacks=[lgb.early_stopping(stopping_rounds=EARLY_STOPPING_ROUNDS), lgb.log_evaluation(period=0)],
    )

    return FittedBinaryClassifier(
        booster=booster,
        best_iteration=int(booster.best_iteration),
        config_hash=frozen_hash,
        feature_names=feature_names,
    )


def predict_probabilities(model: FittedBinaryClassifier, X) -> np.ndarray:
    """Predict at the fitted model's own best_iteration."""

    if tuple(X.columns) != model.feature_names:
        raise ValueError("Prediction frame columns do not match the fitted model's feature_names")
    return np.asarray(model.booster.predict(X, num_iteration=model.best_iteration), dtype=np.float64)
