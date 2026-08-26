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
from src.preprocessing import LightGBMFeatureTransform

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
CROSS_FITTING_FOLDS = 2
INNER_VALIDATION_FRACTION = 0.2  # held-out slice for the nuisance models' early stopping


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
# X-Learner. Two things must be fold-local, not just one:
#   1. the nuisance models (mu0/mu1) -- every row's out-of-fold nuisance
#      prediction must come from a model fit on the OPPOSITE fold, or a row's
#      own outcome leaks into its own pseudo-outcome target;
#   2. the categorical feature transform (LightGBMFeatureTransform) each
#      nuisance model is trained under -- fitting ONE transform on the whole
#      train partition and reusing it for both folds lets each fold's
#      categorical vocabulary be informed by the opposite fold's own category
#      values. This was a real bug in this project (see README's Methodology
#      notes), fixed by giving each fold its own fold-local transform, fit
#      only on that fold's own raw training rows.
# The effect stage (tau1/tau0) has no cross-fitting boundary to violate: its
# transform is fit once on the whole raw train partition, same as T-Learner.
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


def _require_raw_features(frame) -> None:
    already_categorical = [
        feature
        for feature in CATEGORICAL_FEATURES
        if feature in getattr(frame, "columns", ()) and isinstance(frame[feature].dtype, pd.CategoricalDtype)
    ]
    if already_categorical:
        raise ValueError(
            f"fit_x_learner received an already-transformed frame (categorical dtype on "
            f"{already_categorical}); pass the RAW f0..f11 frame instead -- fit_x_learner fits "
            "its own fold-local LightGBMFeatureTransform internally, and reusing a globally-fit "
            "transform here would silently reintroduce the fold-local preprocessing bug"
        )


def fit_x_learner(raw_train_frame, T_train, Y_train, *, seed: int = 42) -> XLearner:
    """raw_train_frame: the RAW (untransformed) f0..f11 frame -- NOT the
    output of a globally-fit LightGBMFeatureTransform. This function fits its
    own fold-local transforms internally; passing an already-transformed
    frame would silently reintroduce the fold-local preprocessing bug."""

    _require_raw_features(raw_train_frame)
    T_arr = np.asarray(T_train, dtype=np.float64)
    Y_arr = np.asarray(Y_train, dtype=np.float64)
    strata = pd.Series(T_arr).astype(str) + "_" + pd.Series(Y_arr).astype(str)
    idx = np.arange(len(raw_train_frame))
    fold_a, fold_b = train_test_split(idx, train_size=0.5, random_state=seed, stratify=strata)

    def _fit_arm_with_early_stopping(X_arm, Y_arm):
        # Early-stopping validation must be a genuine held-out slice, not the
        # arm's own training rows -- fitting and early-stopping against the
        # same rows lets LightGBM chase training loss to the round cap
        # (near-zero training logloss, no real stopping signal), which both
        # wastes compute and can degrade the OOF pseudo-outcome quality this
        # nuisance stage feeds into.
        inner_idx = np.arange(len(X_arm))
        inner_train, inner_val = train_test_split(
            inner_idx, test_size=INNER_VALIDATION_FRACTION, random_state=seed, stratify=Y_arm
        )
        return fit_classifier(
            X_arm.iloc[inner_train], Y_arm[inner_train], X_arm.iloc[inner_val], Y_arm[inner_val], seed=seed
        )

    def _fit_fold(fold_idx):
        raw_fold = raw_train_frame.iloc[fold_idx]
        transform = LightGBMFeatureTransform().fit(raw_fold)
        X_fold = transform.transform(raw_fold)
        T_f, Y_f = T_arr[fold_idx], Y_arr[fold_idx]
        treated, control = T_f == 1, T_f == 0
        mu1 = _fit_arm_with_early_stopping(X_fold[treated], Y_f[treated])
        mu0 = _fit_arm_with_early_stopping(X_fold[control], Y_f[control])
        return mu1, mu0, transform

    mu1_a, mu0_a, transform_a = _fit_fold(fold_a)
    mu1_b, mu0_b, transform_b = _fit_fold(fold_b)

    # Opposite-fold scoring: fold A rows are transformed by fold B's own
    # fold-local vocabulary and scored by fold B's models, and vice versa --
    # this keeps both the model AND its feature representation leak-free
    # across the cross-fitting boundary.
    mu0_oof = np.empty(len(raw_train_frame), dtype=np.float64)
    mu1_oof = np.empty(len(raw_train_frame), dtype=np.float64)
    X_a_by_b = transform_b.transform(raw_train_frame.iloc[fold_a])
    X_b_by_a = transform_a.transform(raw_train_frame.iloc[fold_b])
    mu0_oof[fold_a] = predict(mu0_b, X_a_by_b)
    mu1_oof[fold_a] = predict(mu1_b, X_a_by_b)
    mu0_oof[fold_b] = predict(mu0_a, X_b_by_a)
    mu1_oof[fold_b] = predict(mu1_a, X_b_by_a)

    treated_mask, control_mask = T_arr == 1, T_arr == 0
    d1 = Y_arr[treated_mask] - mu0_oof[treated_mask]
    d0 = mu1_oof[control_mask] - Y_arr[control_mask]

    # Effect-stage transform: fit once on the whole raw train partition --
    # this stage has no cross-fitting boundary, so a global fit is correct.
    effect_transform = LightGBMFeatureTransform().fit(raw_train_frame)
    X_effect = effect_transform.transform(raw_train_frame)
    tau1 = fit_regressor(X_effect[treated_mask], d1, seed=seed)
    tau0 = fit_regressor(X_effect[control_mask], d0, seed=seed)
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
# max_depth=20 is a memory safety cap, not a capacity constraint: on full
# CRITEO scale the unbounded default (max_depth=None) risked OOM on a
# standard 30GB Kaggle kernel (empirically observed). min_samples_leaf=5
# already limits how deep a well-behaved split needs to go; a benchmark under
# this exact config measured tree depth reaching 32 well before that leaf
# floor forced a stop, so 20 caps the pathological tail without binding on
# typical splits. The pathological tail is not hypothetical: this dataset has
# a documented population of exact repeated-feature-value rows (see
# archive/docs/04_duplicate_profile_protocol.md) -- large groups of rows a
# split cannot separate on X alone recurse far deeper than a clean, unique-
# valued sample would, which is the actual mechanism max_depth guards
# against, not a generic "more data needs a shallower tree" heuristic.
# max_features="sqrt" replaces econml's own default ("auto" == all features
# considered at every split): standard random-forest feature subsampling,
# not a departure from the causal-forest method. It shrinks per-node
# split-search memory/time roughly 8x here (sqrt(76)~9 vs 76) and, if
# anything, decorrelates trees more than evaluating every feature at every
# split.
# ---------------------------------------------------------------------------

CAUSAL_FOREST_CONFIG: dict[str, object] = {
    "n_estimators": 100,
    "max_depth": 20,
    "honest": True,
    "inference": False,
    "min_samples_leaf": 5,
    "max_samples": 0.45,
    "subforest_size": 4,
    "n_jobs": 1,
    "max_features": "sqrt",
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
    # Preserve the caller's dtype (float32 from CausalForestCategoricalEncoder) instead of
    # forcing float64 -- econml's CausalForest.fit() converts X to float32 internally anyway
    # (sklearn.tree._tree.DTYPE), so forcing float64 here just makes it allocate a redundant
    # float64 copy that stays resident for the entire multi-hour, n_jobs=1 fit.
    if hasattr(X, "to_numpy"):
        X_arr = X.to_numpy()
    else:
        X_arr = np.asarray(X, dtype=X.dtype if hasattr(X, "dtype") else np.float32)
    T_arr = np.asarray(T, dtype=np.float64).reshape(-1, 1)
    Y_arr = np.asarray(Y, dtype=np.float64)
    model = CausalForest(**config)
    model.fit(X_arr, T_arr, Y_arr)
    return model


def predict_causal_forest_tau(model: CausalForest, X) -> np.ndarray:
    X_arr = X.to_numpy() if hasattr(X, "to_numpy") else np.asarray(X, dtype=np.float64)
    return np.asarray(model.predict(X_arr), dtype=np.float64).reshape(-1)
