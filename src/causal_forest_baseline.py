"""Causal Forest fitting/diagnostic primitive (T10): a thin wrapper around
econml.grf.CausalForest with a frozen, hashed configuration, plus the
honesty/treatment-control-support diagnostic ADR-CF-implementation requires.

econml.grf.CausalForest fits a forest that solves the local moment equation
E[(Y - <theta(x), T> - beta(x)) (T;1) | X=x] = 0 directly at every point x --
theta(x) (the treatment effect) and beta(x) (a local intercept) are estimated
jointly and locally via forest-weighted neighborhoods. This is NOT DML-style
nuisance residualization and involves no upfront cross-fitting stage: no
separate nuisance model is fit before the forest.

Causal-role interpretation of X/T/Y stays in the caller (notebook/tests) --
this module only knows about the frozen fitting/diagnostic mechanics.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

import numpy as np
import pandas as pd
from econml.grf import CausalForest

from src.data import CATEGORICAL_FEATURES, CONTINUOUS_FEATURES, FEATURE_COLUMNS, DataContractError

FROZEN_ECONML_VERSION = "0.17.0"


class CausalForestRepresentationError(DataContractError):
    """Raised when fit_causal_forest() receives raw, unencoded categorical tokens."""

# Every value left at econml's own library default except where this project's
# reproducibility contract forces it (random_state is set per call; n_jobs=1
# is forced -- see below). No hyperparameter search, no tuning.
FROZEN_CAUSAL_FOREST_CONFIG: dict[str, object] = {
    "n_estimators": 100,          # econml's own default; divisible by subforest_size (required
                                   # by the library -- n_estimators % subforest_size must be 0)
    "criterion": "mse",           # package default: the standard local-moment-estimation split
                                   # rule from the reference GRF algorithm (verified from source
                                   # docstring, not assumed); "het" is a distinct, not-default
                                   # heterogeneity-score variant, not used here
    "honest": True,               # mandatory per ADR-CF-implementation -- never False
    "inference": False,           # this project's uncertainty mechanism is the frozen 500-draw
                                   # paired arm-stratified validation bootstrap (AGENTS.md,
                                   # docs/06), applied post hoc to already-computed scores -- not
                                   # any estimator's internal per-row analytic/BLB interval.
                                   # inference=True's Bootstrap-of-Little-Bags machinery is
                                   # unused overhead with no downstream consumer; disabled rather
                                   # than left on by default-inertia.
    "min_samples_leaf": 5,        # package default, untouched
    "max_samples": 0.45,          # package default, untouched
    "min_balancedness_tol": 0.45, # package default, untouched -- NOTE: this bounds split-size
                                   # imbalance between the two children of a split; it is NOT a
                                   # treatment/control arm-balance mechanism. Arm support is
                                   # verified separately by honest_leaf_arm_support() below.
    "subforest_size": 4,          # package default
    "max_depth": None,            # package default
    "n_jobs": 1,                  # NOT the package default (-1). Verified empirically (T10
                                   # IMPLEMENT): with an identical random_state, n_jobs=2 and
                                   # n_jobs=-1 each produced different predictions than n_jobs=1.
                                   # Determinism requires n_jobs=1; this is a correctness
                                   # requirement, not a performance preference.
}


def _reject_raw_categorical_columns(X) -> None:
    """Fail closed on raw, unencoded CRITEO categorical token columns.

    econml.grf.CausalForest has no native categorical-feature representation
    equivalent to LightGBM's train-fitted category dtype (D32). f1/f3/f4/f5/
    f6/f8/f9/f11 are anonymized categorical tokens, not ordered continuous
    quantities -- passing them through as raw float64 columns silently
    reintroduces the same bug D32 fixes for LightGBM. This project does not
    pick an encoding (ordinal/one-hot/hashing/target-encoding/etc.) here:
    that choice is deferred to a dedicated CausalForest representation ADR
    (docs/adr/ADR-CF-implementation.md). Callers passing an already-encoded
    generic numeric matrix (no column named after a raw categorical feature)
    are unaffected.
    """

    if not hasattr(X, "columns"):
        return
    raw_categorical_present = sorted(set(X.columns) & set(CATEGORICAL_FEATURES))
    if raw_categorical_present:
        raise CausalForestRepresentationError(
            "fit_causal_forest() received raw, unencoded CRITEO categorical token "
            f"column(s) {raw_categorical_present}. These are categorical tokens, not "
            "ordered continuous quantities, and econml.grf.CausalForest has no native "
            "categorical representation to fall back on. An explicit, separately-decided "
            "CausalForest encoding is required (see docs/adr/ADR-CF-implementation.md) -- "
            "this function refuses to guess one."
        )


CATEGORICAL_ENCODER_K_LADDER = (32, 16, 8)


class CausalForestEncodingError(DataContractError):
    """Raised when CausalForestCategoricalEncoder is misused or fed invalid input."""


def _other_column(feature: str) -> str:
    return f"{feature}__OTHER"


def _category_column(feature: str, value: float) -> str:
    return f"{feature}__cat_{value!r}"


def _require_feature_columns(frame: pd.DataFrame) -> None:
    missing = sorted(set(FEATURE_COLUMNS).difference(frame.columns))
    if missing:
        raise CausalForestEncodingError(f"Frame is missing required feature columns: {missing}")


def _reject_missing_categorical_values(frame: pd.DataFrame) -> None:
    """FAIL CLOSED on NaN in a D34 categorical feature (owner decision,
    2026-08-24). T03 evidence shows zero missing values across the released
    population, so a NaN here signals an unexpected data-contract change --
    it is not silently routed to OTHER or a new MISSING bucket."""

    for feature in CATEGORICAL_FEATURES:
        na_count = int(frame[feature].isna().sum())
        if na_count:
            raise CausalForestEncodingError(
                f"Categorical feature {feature!r} contains {na_count} missing value(s); "
                "CausalForestCategoricalEncoder fails closed on NaN per the D34 owner decision "
                "(no MISSING bucket, no routing to OTHER)."
            )


class CausalForestCategoricalEncoder:
    """Frequency-capped ('top-K + OTHER') one-hot representation for
    CausalForest's categorical features (D34; resolves the D32 encoding
    blocker in docs/adr/ADR-CF-implementation.md).

    TRAIN-only fit, frozen and reused unchanged on validation/held-out --
    this object is never refit downstream of its first ``fit()`` call.
    Continuous features (``CONTINUOUS_FEATURES``) pass through unchanged.
    Categorical features (``CATEGORICAL_FEATURES``) become one binary
    indicator column per retained category plus one trailing ``OTHER``
    indicator -- never a single integer/rank column, which would
    reintroduce the ordinal-structure bug D32 exists to fix.

    ``k`` must come from the predeclared RESOURCE ladder
    ``CATEGORICAL_ENCODER_K_LADDER`` and is chosen only by resource
    feasibility (see ``src/causal_forest_runner.py``'s RESOURCE gate) --
    never by predictive/uplift performance.
    """

    def __init__(self, k: int) -> None:
        if k not in CATEGORICAL_ENCODER_K_LADDER:
            raise CausalForestEncodingError(
                f"k={k!r} is not in the predeclared RESOURCE ladder {CATEGORICAL_ENCODER_K_LADDER}"
            )
        self._k = k
        self._fitted = False
        self._vocabularies: dict[str, list[float]] = {}

    @property
    def k(self) -> int:
        return self._k

    def fit(self, train_frame: pd.DataFrame) -> "CausalForestCategoricalEncoder":
        _require_feature_columns(train_frame)
        _reject_missing_categorical_values(train_frame)

        vocabularies: dict[str, list[float]] = {}
        for feature in CATEGORICAL_FEATURES:
            values = train_frame[feature].astype("float64")
            counts = values.value_counts()
            # Deterministic tie-break: (count DESC, category value ASC) --
            # never rely on value_counts()'s own tie ordering, which is not
            # a stable cross-version contract.
            ranked = sorted(counts.index.tolist(), key=lambda v: (-counts[v], v))
            top_k = sorted(ranked[: self._k])
            vocabularies[feature] = [float(v) for v in top_k]

        self._vocabularies = vocabularies
        self._fitted = True
        return self

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        if not self._fitted:
            raise CausalForestEncodingError("transform() called before fit()")
        _require_feature_columns(frame)
        _reject_missing_categorical_values(frame)

        blocks: list[pd.DataFrame] = [frame[[feature]].astype("float64") for feature in CONTINUOUS_FEATURES]

        for feature in CATEGORICAL_FEATURES:
            vocab = self._vocabularies[feature]
            values = frame[feature].astype("float64")
            in_vocab = values.isin(vocab)
            block_columns = {
                _category_column(feature, value): (values == value).astype("float64") for value in vocab
            }
            block_columns[_other_column(feature)] = (~in_vocab).astype("float64")
            blocks.append(pd.DataFrame(block_columns, index=frame.index))

        output = pd.concat(blocks, axis=1)
        if list(output.columns) != self.output_columns:
            raise CausalForestEncodingError("Transformed column order drifted from the frozen contract")
        return output

    def fit_transform(self, train_frame: pd.DataFrame) -> pd.DataFrame:
        return self.fit(train_frame).transform(train_frame)

    @property
    def output_columns(self) -> list[str]:
        if not self._fitted:
            raise CausalForestEncodingError("output_columns accessed before fit()")
        columns: list[str] = list(CONTINUOUS_FEATURES)
        for feature in CATEGORICAL_FEATURES:
            for value in self._vocabularies[feature]:
                columns.append(_category_column(feature, value))
            columns.append(_other_column(feature))
        return columns

    def other_bucket_counts(self, frame: pd.DataFrame) -> dict[str, int]:
        """Diagnostic only -- reported for interpretation, never used to
        select K (K is a resource-feasibility decision, D34)."""

        if not self._fitted:
            raise CausalForestEncodingError("other_bucket_counts() called before fit()")
        _require_feature_columns(frame)
        _reject_missing_categorical_values(frame)

        result: dict[str, int] = {}
        for feature in CATEGORICAL_FEATURES:
            values = frame[feature].astype("float64")
            vocab = self._vocabularies[feature]
            result[feature] = int((~values.isin(vocab)).sum())
        return result

    def vocabulary_state(self) -> dict[str, object]:
        if not self._fitted:
            raise CausalForestEncodingError("vocabulary_state() called before fit()")
        return {
            "k": self._k,
            "vocabularies": {feature: list(values) for feature, values in self._vocabularies.items()},
            "output_dimensionality": len(self.output_columns),
        }


def config_hash(config: dict[str, object] | None = None) -> str:
    """Deterministic sha256 of the frozen config, same convention as
    src/lightgbm_baseline.py's config_hash()."""

    payload = dict(config if config is not None else FROZEN_CAUSAL_FOREST_CONFIG)
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


@dataclass(frozen=True)
class FittedCausalForest:
    model: CausalForest
    config_hash: str
    feature_names: tuple[str, ...]
    # D34: the frozen TRAIN-only categorical encoder that produced this
    # model's X, if any. Default None keeps this backward compatible with
    # every call site/test that predates D34 (an already-encoded synthetic
    # matrix with no encoder attached). None here is also the fail-closed
    # signal src.causal_forest_runner uses to refuse validation scoring of a
    # historical/pre-D34 model under the new runner path.
    categorical_encoder: "CausalForestCategoricalEncoder | None" = None


def fit_causal_forest(
    X,
    T,
    Y,
    *,
    config: dict[str, object] | None = None,
    seed: int = 42,
) -> FittedCausalForest:
    """Fit one econml.grf.CausalForest. T is passed as its own argument --
    never concatenated into X. T must be a single binary column."""

    _reject_raw_categorical_columns(X)

    effective_config = dict(config if config is not None else FROZEN_CAUSAL_FOREST_CONFIG)
    effective_config["random_state"] = seed
    frozen_hash = config_hash(effective_config)

    if effective_config["n_estimators"] % effective_config["subforest_size"] != 0:
        raise ValueError(
            f"n_estimators={effective_config['n_estimators']} must be divisible by "
            f"subforest_size={effective_config['subforest_size']} (econml.grf.CausalForest requirement)"
        )

    feature_names = tuple(X.columns) if hasattr(X, "columns") else tuple(f"x{i}" for i in range(np.asarray(X).shape[1]))
    X_arr = X.to_numpy() if hasattr(X, "to_numpy") else np.asarray(X, dtype=np.float64)
    T_raw = np.asarray(T, dtype=np.float64)
    Y_arr = np.asarray(Y, dtype=np.float64)

    # Validate T's shape BEFORE reshaping -- reshape(-1, 1) always succeeds and
    # always produces a (N, 1) array regardless of input shape, so the check
    # must happen on the raw shape or a multi-column T would be silently
    # flattened into a longer single column instead of rejected.
    if T_raw.ndim == 2 and T_raw.shape[1] != 1:
        raise ValueError("fit_causal_forest requires a single binary treatment column")
    T_arr = T_raw.reshape(-1, 1)

    model = CausalForest(**effective_config)
    model.fit(X_arr, T_arr, Y_arr)

    return FittedCausalForest(model=model, config_hash=frozen_hash, feature_names=feature_names)


def predict_tau(model: FittedCausalForest, X) -> np.ndarray:
    """Predict tau(x) for every row of X."""

    if hasattr(X, "columns") and tuple(X.columns) != model.feature_names:
        raise ValueError("Prediction frame columns do not match the fitted model's feature_names")
    X_arr = X.to_numpy() if hasattr(X, "to_numpy") else np.asarray(X, dtype=np.float64)
    pred = model.model.predict(X_arr)
    return np.asarray(pred, dtype=np.float64).reshape(-1)


@dataclass(frozen=True)
class LeafArmSupport:
    tree_index: int
    leaf_id: int
    n_treated: int
    n_control: int


def honest_leaf_arm_support(model: FittedCausalForest, X, T) -> list[LeafArmSupport]:
    """Reconstruct each honest tree's ESTIMATION-sample leaves (never the
    split-determining sample) and count treated/control rows per leaf.

    DIAGNOSTIC ONLY -- not a pass/fail gate. econml.grf.CausalForest's own
    identification is a forest-AGGREGATE property (predict_alpha_and_jac()
    averages each tree's local moment contribution across all trees, then
    solves one pseudo-inverse at the aggregate level -- see
    econml/grf/_base_grf.py). It does not require every individual
    (tree, leaf) pair to contain both arms, and neither does this project's
    T10 support gate: see aggregate_jacobian_support() below for the actual
    hard identification check. A single tree's leaf lacking one arm is
    expected, ordinary behavior under class imbalance with an unconstrained
    max_depth and an absolute min_samples_leaf floor -- not evidence of
    estimator failure by itself.

    econml.grf.CausalForest.get_train_test_split_inds() (per-tree) returns
    indices LOCAL to that tree's own subsample (as drawn by
    forest.get_subsample_inds()[i]), not global row indices into X. They must
    be mapped back through the subsample before being used to index X/T:

        subsample = forest.get_subsample_inds()[i]
        split_local, est_local = tree.get_train_test_split_inds()
        split_global = subsample[split_local]
        est_global = subsample[est_local]

    Leaf support is computed from est_global only -- the split_global sample
    determines tree structure and never contributes to a leaf's estimated
    value, so it is irrelevant to support.
    """

    X_arr = X.to_numpy() if hasattr(X, "to_numpy") else np.asarray(X, dtype=np.float64)
    T_arr = np.asarray(T, dtype=np.float64).reshape(-1)

    forest = model.model
    subsample_inds = forest.get_subsample_inds()
    results: list[LeafArmSupport] = []

    for tree_index, tree in enumerate(forest.estimators_):
        subsample = subsample_inds[tree_index]
        split_local, est_local = tree.get_train_test_split_inds()
        if not set(split_local.tolist()).isdisjoint(set(est_local.tolist())):
            raise ValueError(f"tree {tree_index}: split/estimation samples are not disjoint -- honesty violated")
        est_global = subsample[est_local]

        leaf_ids = tree.apply(X_arr[est_global])
        T_est = T_arr[est_global]
        for leaf in np.unique(leaf_ids):
            mask = leaf_ids == leaf
            n_treated = int((T_est[mask] == 1).sum())
            n_control = int((T_est[mask] == 0).sum())
            results.append(LeafArmSupport(tree_index=tree_index, leaf_id=int(leaf), n_treated=n_treated, n_control=n_control))

    return results


@dataclass(frozen=True)
class AggregateSupportResult:
    n_queries: int
    full_rank_dimension: int
    alpha_all_finite: bool
    jac_all_finite: bool
    tau_all_finite: bool
    jac_full_rank_fraction: float
    all_full_rank: bool
    passed: bool
    condition_number_distribution: dict[str, float]


def aggregate_jacobian_support(model: FittedCausalForest, X) -> AggregateSupportResult:
    """Evaluate aggregate local-moment correctness and numerical diagnostics.

    Hard correctness requires:
    - alpha(x) finite
    - jac(x) finite
    - tau(x) finite

    Aggregate Jacobian numerical rank and condition numbers are diagnostic
    only. Rank deficiency by itself does not fail the model because EconML's
    prediction path uses the Moore-Penrose pseudo-inverse.

    jac_full_rank_fraction, all_full_rank, and condition-number summaries are
    retained for reporting and investigation.
    """

    X_arr = X.to_numpy() if hasattr(X, "to_numpy") else np.asarray(X, dtype=np.float64)
    forest = model.model

    alpha, jac = forest.predict_alpha_and_jac(X_arr)
    tau = predict_tau(model, X)

    alpha_all_finite = bool(np.isfinite(alpha).all())
    jac_all_finite = bool(np.isfinite(jac).all())
    tau_all_finite = bool(np.isfinite(tau).all())

    full_rank_dimension = jac.shape[1]
    ranks = np.array([np.linalg.matrix_rank(jac[i]) for i in range(jac.shape[0])])
    jac_full_rank_fraction = float((ranks == full_rank_dimension).mean())
    all_full_rank = bool((ranks == full_rank_dimension).all())

    cond_numbers = np.array([np.linalg.cond(jac[i]) for i in range(jac.shape[0])])
    condition_number_distribution = {
        "min": float(np.min(cond_numbers)),
        "p50": float(np.quantile(cond_numbers, 0.50)),
        "p95": float(np.quantile(cond_numbers, 0.95)),
        "p99": float(np.quantile(cond_numbers, 0.99)),
        "max": float(np.max(cond_numbers)),
    }

    passed = alpha_all_finite and jac_all_finite and tau_all_finite
    return AggregateSupportResult(
        n_queries=int(jac.shape[0]),
        full_rank_dimension=int(full_rank_dimension),
        alpha_all_finite=alpha_all_finite,
        jac_all_finite=jac_all_finite,
        tau_all_finite=tau_all_finite,
        jac_full_rank_fraction=jac_full_rank_fraction,
        all_full_rank=all_full_rank,
        passed=passed,
        condition_number_distribution=condition_number_distribution,
    )
