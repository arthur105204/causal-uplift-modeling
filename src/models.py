"""Response LightGBM baseline, T-Learner, X-Learner, and Causal Forest.

All models share one feature contract: X is exactly f0..f11 in order,
T is binary treatment assignment, Y is the binary outcome (primary:
conversion). See src/preprocessing.py for the categorical representation
each model needs.
"""

from __future__ import annotations

from dataclasses import dataclass

import lightgbm as lgb
import numpy as np
import pandas as pd
from econml.grf import CausalForest
from sklearn.model_selection import train_test_split

from src.data import CATEGORICAL_FEATURES

# ---------------------------------------------------------------------------
# LightGBM fitting primitives (shared by the response model, T-Learner, and
# X-Learner's nuisance/effect stages).
# ---------------------------------------------------------------------------

BINARY_CONFIG: dict[str, object] = {
    "objective": "binary",
    "metric": "binary_logloss",
    "boosting_type": "gbdt",
    "learning_rate": 0.1,
    "num_leaves": 31,
    "min_data_in_leaf": 20,
    "seed": 42,
    "deterministic": True,
    "force_row_wise": True,
    "verbosity": -1,
}
REGRESSION_CONFIG: dict[str, object] = {**BINARY_CONFIG, "objective": "regression", "metric": "l2"}
NUM_BOOST_ROUND_CAP = 2000
EARLY_STOPPING_ROUNDS = 50
EFFECT_NUM_BOOST_ROUND = 100  # X-Learner effect stage: no valid held-out target to early-stop against


def fit_classifier(X_train, y_train, X_val, y_val, *, seed: int = 42) -> lgb.Booster:
    """Fit one LightGBM binary classifier, best iteration chosen by early
    stopping against (X_val, y_val)."""

    config = {**BINARY_CONFIG, "seed": seed}
    feature_names = list(X_train.columns)
    train_set = lgb.Dataset(X_train, label=y_train, feature_name=feature_names, categorical_feature=list(CATEGORICAL_FEATURES))
    val_set = lgb.Dataset(X_val, label=y_val, feature_name=feature_names, categorical_feature=list(CATEGORICAL_FEATURES), reference=train_set)
    return lgb.train(
        config,
        train_set,
        num_boost_round=NUM_BOOST_ROUND_CAP,
        valid_sets=[val_set],
        callbacks=[lgb.early_stopping(EARLY_STOPPING_ROUNDS), lgb.log_evaluation(period=0)],
    )


def fit_regressor(X_train, y_train, *, seed: int = 42) -> lgb.Booster:
    """Fit one LightGBM regressor for a fixed round count (no early stopping:
    X-Learner pseudo-outcome targets have no valid held-out counterpart)."""

    config = {**REGRESSION_CONFIG, "seed": seed}
    train_set = lgb.Dataset(X_train, label=y_train, feature_name=list(X_train.columns), categorical_feature=list(CATEGORICAL_FEATURES))
    return lgb.train(config, train_set, num_boost_round=EFFECT_NUM_BOOST_ROUND, callbacks=[lgb.log_evaluation(period=0)])


def predict(booster: lgb.Booster, X) -> np.ndarray:
    return np.asarray(booster.predict(X, num_iteration=booster.best_iteration or None), dtype=np.float64)


# ---------------------------------------------------------------------------
# Response model: plain binary classifier on conversion, ignoring treatment.
# Non-causal targeting comparator.
# ---------------------------------------------------------------------------


def fit_response_model(X_train, y_train, X_val, y_val, *, seed: int = 42) -> lgb.Booster:
    return fit_classifier(X_train, y_train, X_val, y_val, seed=seed)


# ---------------------------------------------------------------------------
# T-Learner: two independent outcome models, one per arm.
# tau_hat(x) = mu1_hat(x) - mu0_hat(x)
# ---------------------------------------------------------------------------


@dataclass
class TLearner:
    mu1: lgb.Booster
    mu0: lgb.Booster

    def predict_tau(self, X) -> np.ndarray:
        return predict(self.mu1, X) - predict(self.mu0, X)


def fit_t_learner(X_train, T_train, Y_train, X_val, T_val, Y_val, *, seed: int = 42) -> TLearner:
    treated_train, control_train = T_train == 1, T_train == 0
    treated_val, control_val = T_val == 1, T_val == 0
    mu1 = fit_classifier(X_train[treated_train], Y_train[treated_train], X_val[treated_val], Y_val[treated_val], seed=seed)
    mu0 = fit_classifier(X_train[control_train], Y_train[control_train], X_val[control_val], Y_val[control_val], seed=seed)
    return TLearner(mu1=mu1, mu0=mu0)


# ---------------------------------------------------------------------------
# X-Learner. The nuisance models (mu0/mu1) MUST be fit fold-locally: the
# training population is split into two folds, and every row's out-of-fold
# nuisance prediction comes from the model fit on the OPPOSITE fold. Fitting
# mu0/mu1 on the whole training set and scoring the same rows (no fold split)
# leaks each row's own outcome into its own pseudo-outcome target -- this was
# a real bug in this project, fixed by making the split fold-local.
# ---------------------------------------------------------------------------


@dataclass
class XLearner:
    tau1: lgb.Booster  # fit on treated rows' pseudo-outcome D1
    tau0: lgb.Booster  # fit on control rows' pseudo-outcome D0
    g: float  # empirical treatment rate; constant weight, not a covariate-varying propensity

    def predict_tau(self, X) -> np.ndarray:
        tau1_hat = predict(self.tau1, X)
        tau0_hat = predict(self.tau0, X)
        return self.g * tau0_hat + (1.0 - self.g) * tau1_hat


def fit_x_learner(X_train, T_train, Y_train, *, seed: int = 42) -> XLearner:
    strata = pd.Series(T_train).astype(str) + "_" + pd.Series(Y_train).astype(str)
    idx = np.arange(len(X_train))
    fold_a, fold_b = train_test_split(idx, train_size=0.5, random_state=seed, stratify=strata)

    def _fit_arms(fold_idx):
        X_f, T_f, Y_f = X_train.iloc[fold_idx], np.asarray(T_train)[fold_idx], np.asarray(Y_train)[fold_idx]
        treated, control = T_f == 1, T_f == 0
        mu1 = fit_classifier(X_f[treated], Y_f[treated], X_f[treated], Y_f[treated], seed=seed)
        mu0 = fit_classifier(X_f[control], Y_f[control], X_f[control], Y_f[control], seed=seed)
        return mu1, mu0

    mu1_a, mu0_a = _fit_arms(fold_a)
    mu1_b, mu0_b = _fit_arms(fold_b)

    # Opposite-fold scoring: fold A rows are scored by the fold-B models, and
    # vice versa -- this is what makes the OOF nuisance predictions leak-free.
    mu0_oof = np.empty(len(X_train), dtype=np.float64)
    mu1_oof = np.empty(len(X_train), dtype=np.float64)
    mu0_oof[fold_a] = predict(mu0_b, X_train.iloc[fold_a])
    mu1_oof[fold_a] = predict(mu1_b, X_train.iloc[fold_a])
    mu0_oof[fold_b] = predict(mu0_a, X_train.iloc[fold_b])
    mu1_oof[fold_b] = predict(mu1_a, X_train.iloc[fold_b])

    T_arr = np.asarray(T_train, dtype=np.float64)
    Y_arr = np.asarray(Y_train, dtype=np.float64)
    treated_mask, control_mask = T_arr == 1, T_arr == 0

    d1 = Y_arr[treated_mask] - mu0_oof[treated_mask]
    d0 = mu1_oof[control_mask] - Y_arr[control_mask]

    tau1 = fit_regressor(X_train[treated_mask], d1, seed=seed)
    tau0 = fit_regressor(X_train[control_mask], d0, seed=seed)
    g = float(np.mean(T_arr == 1))  # this project's design has no documented covariate-varying propensity
    return XLearner(tau1=tau1, tau0=tau0, g=g)


# ---------------------------------------------------------------------------
# Causal Forest (econml.grf.CausalForest). Fit on Causal-Forest-encoded X
# (see src.preprocessing.CausalForestCategoricalEncoder) -- raw categorical
# tokens are rejected, since CausalForest has no native categorical support
# and passing them through as floats would reintroduce the D32 ordinal bug.
# honest=True and n_jobs=1 are load-bearing: honesty is required for valid
# inference, and n_jobs=1 is required for determinism (empirically verified --
# n_jobs=2/-1 produced different predictions than n_jobs=1 with an identical
# random_state).
# ---------------------------------------------------------------------------

CAUSAL_FOREST_CONFIG: dict[str, object] = {
    "n_estimators": 100,
    "honest": True,
    "inference": False,
    "min_samples_leaf": 5,
    "max_samples": 0.45,
    "subforest_size": 4,
    "n_jobs": 1,
}


def _reject_raw_categorical_columns(X) -> None:
    if hasattr(X, "columns"):
        overlap = sorted(set(X.columns) & set(CATEGORICAL_FEATURES))
        if overlap:
            raise ValueError(
                f"fit_causal_forest received raw categorical column(s) {overlap}; "
                "encode with CausalForestCategoricalEncoder first"
            )


def fit_causal_forest(X, T, Y, *, seed: int = 42) -> CausalForest:
    _reject_raw_categorical_columns(X)
    config = {**CAUSAL_FOREST_CONFIG, "random_state": seed}
    X_arr = X.to_numpy() if hasattr(X, "to_numpy") else np.asarray(X, dtype=np.float64)
    T_arr = np.asarray(T, dtype=np.float64).reshape(-1, 1)
    Y_arr = np.asarray(Y, dtype=np.float64)
    model = CausalForest(**config)
    model.fit(X_arr, T_arr, Y_arr)
    return model


def predict_causal_forest_tau(model: CausalForest, X) -> np.ndarray:
    X_arr = X.to_numpy() if hasattr(X, "to_numpy") else np.asarray(X, dtype=np.float64)
    return np.asarray(model.predict(X_arr), dtype=np.float64).reshape(-1)
