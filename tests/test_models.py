from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.data import CATEGORICAL_FEATURES, CONTINUOUS_FEATURES, FEATURE_COLUMNS
from src.models import fit_causal_forest, fit_t_learner, fit_x_learner, predict_causal_forest_tau
from src.preprocessing import CausalForestCategoricalEncoder, LightGBMFeatureTransform


def _synthetic(rows: int, seed: int, true_effect: float) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    """X uninformative noise; T random; Y = base_rate + true_effect * T + noise,
    so any correctly-signed uplift estimator should recover tau ~= true_effect."""

    rng = np.random.default_rng(seed)
    raw = pd.DataFrame({
        feature: rng.normal(size=rows) if feature in CONTINUOUS_FEATURES else rng.integers(0, 4, size=rows).astype("float64")
        for feature in FEATURE_COLUMNS
    })
    T = rng.integers(0, 2, size=rows).astype(np.float64)
    base_rate = 0.3
    prob = np.clip(base_rate + true_effect * T, 0.01, 0.99)
    Y = (rng.uniform(size=rows) < prob).astype(np.float64)
    return raw, T, Y


def _lightgbm_features(train_raw: pd.DataFrame, *other_raw: pd.DataFrame):
    transform = LightGBMFeatureTransform().fit(train_raw)
    return (transform.transform(train_raw), *(transform.transform(f) for f in other_raw))


def test_t_learner_recovers_positive_uplift_sign() -> None:
    raw, T, Y = _synthetic(rows=400, seed=1, true_effect=0.4)
    X = _lightgbm_features(raw)[0]
    split = 300
    learner = fit_t_learner(X.iloc[:split], T[:split], Y[:split], X.iloc[split:], T[split:], Y[split:])
    tau_hat = learner.predict_tau(X.iloc[split:])
    assert len(tau_hat) == len(X) - split
    assert np.mean(tau_hat) > 0


def test_t_learner_recovers_negative_uplift_sign() -> None:
    raw, T, Y = _synthetic(rows=400, seed=2, true_effect=-0.4)
    X = _lightgbm_features(raw)[0]
    split = 300
    learner = fit_t_learner(X.iloc[:split], T[:split], Y[:split], X.iloc[split:], T[split:], Y[split:])
    tau_hat = learner.predict_tau(X.iloc[split:])
    assert np.mean(tau_hat) < 0


def test_x_learner_predict_tau_has_correct_shape_and_is_finite() -> None:
    raw, T, Y = _synthetic(rows=300, seed=3, true_effect=0.3)
    learner = fit_x_learner(raw, T, Y)  # fit_x_learner takes the RAW frame; it fits its own fold-local transforms
    X = _lightgbm_features(raw)[0]
    tau_hat = learner.predict_tau(X)
    assert len(tau_hat) == len(X)
    assert np.isfinite(tau_hat).all()


def test_x_learner_g_is_empirical_treatment_rate() -> None:
    raw, T, Y = _synthetic(rows=200, seed=4, true_effect=0.2)
    learner = fit_x_learner(raw, T, Y)
    assert learner.g == pytest.approx(float(np.mean(T == 1)), abs=1e-9)


def test_x_learner_rejects_pre_transformed_frame() -> None:
    """fit_x_learner must receive the RAW frame -- passing an already
    globally-transformed frame would silently reintroduce the fold-local
    preprocessing bug (global vocabulary leaking across the fold boundary)."""

    raw, T, Y = _synthetic(rows=200, seed=7, true_effect=0.2)
    X = _lightgbm_features(raw)[0]  # pre-transformed: categorical dtype columns, no f-column float64 raw form
    with pytest.raises((KeyError, ValueError, AttributeError, TypeError)):
        fit_x_learner(X, T, Y)


def test_x_learner_fold_local_transforms_are_fit_on_disjoint_fold_rows(monkeypatch) -> None:
    """Regression test for the bug fixed in commit 675f09d ("X-Learner
    fold-local preprocessing was not actually fold-local"): fit_x_learner
    must fit a SEPARATE LightGBMFeatureTransform per cross-fitting fold,
    each on only that fold's own raw rows -- not one transform fit globally
    and reused across both folds, which lets each fold's categorical
    vocabulary be informed by the opposite fold's category values.

    Row-level fold-disjointness is the root property that makes categorical
    vocabulary divergence between folds possible in the first place: if a
    fold's transform is fit only on that fold's own rows, it can only ever
    learn categories present in that fold, which is exactly the invariant
    the fix commit restores. This intercepts every LightGBMFeatureTransform
    .fit() call fit_x_learner makes and asserts the fold-local calls
    partition the raw training frame, rather than trusting predict_tau's
    shape/finiteness alone -- which the previous, broken (globally-fit)
    implementation would also have passed.
    """

    raw, T, Y = _synthetic(rows=200, seed=8, true_effect=0.2)

    fit_calls: list[pd.Index] = []
    original_fit = LightGBMFeatureTransform.fit

    def _recording_fit(self, train_frame):
        fit_calls.append(pd.Index(train_frame.index))
        return original_fit(self, train_frame)

    monkeypatch.setattr(LightGBMFeatureTransform, "fit", _recording_fit)

    fit_x_learner(raw, T, Y, seed=8)

    assert len(fit_calls) == 3, (
        "expected exactly 3 LightGBMFeatureTransform.fit calls: one per "
        "cross-fitting fold (fold-local nuisance vocab) plus one global "
        "effect-stage fit -- a different count means the fold-local fix has "
        f"regressed to a single shared transform (got {len(fit_calls)} calls)"
    )
    fold_a_idx, fold_b_idx, effect_idx = fit_calls

    assert len(fold_a_idx.intersection(fold_b_idx)) == 0, (
        "the two fold-local transforms must be fit on disjoint rows -- any "
        "overlap means a fold's categorical vocabulary is informed by the "
        "opposite fold, reintroducing the fold-local preprocessing leak"
    )
    assert set(fold_a_idx) | set(fold_b_idx) == set(raw.index), (
        "the two folds' fit-rows must partition the full raw training frame"
    )
    assert set(effect_idx) == set(raw.index), (
        "the effect-stage transform has no cross-fitting boundary and should "
        "be fit on the whole raw train partition"
    )


def test_causal_forest_rejects_raw_categorical_columns() -> None:
    raw, T, Y = _synthetic(rows=50, seed=5, true_effect=0.2)
    with pytest.raises(ValueError, match="raw categorical"):
        fit_causal_forest(raw, T, Y)


def test_causal_forest_fits_on_encoded_features_and_predicts() -> None:
    raw, T, Y = _synthetic(rows=150, seed=6, true_effect=0.3)
    encoder = CausalForestCategoricalEncoder(k=8).fit(raw)
    X_encoded = encoder.transform(raw)
    model = fit_causal_forest(X_encoded, T, Y)
    tau_hat = predict_causal_forest_tau(model, X_encoded)
    assert len(tau_hat) == len(raw)
    assert np.isfinite(tau_hat).all()
