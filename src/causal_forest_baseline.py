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
from econml.grf import CausalForest

FROZEN_ECONML_VERSION = "0.17.0"

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
