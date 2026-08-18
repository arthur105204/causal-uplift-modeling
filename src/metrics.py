"""Production (vectorized) T06 uplift-metric implementation.

This is the stable interface T07-T18 import. Its causal/ranking arithmetic is
implemented independently of src/metrics_reference.py -- the two are
cross-checked for exact agreement in tests/test_metrics.py rather than
sharing computation, so a formula bug in one cannot hide behind the other.
Only frozen constants, result dataclasses, the shared exception type, and the
purely mechanical curve-point selection rule are shared (src/metrics_common.py).

Response-model diagnostics (ROC-AUC / average precision / log loss) are
implemented once here via scikit-learn -- they are standard, well-tested
library formulas, not this project's novel causal-ranking logic, so the
dual-implementation discipline is reserved for the Qini/uplift formulas where
the actual risk of a silently-reversed ranking lives.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, log_loss, roc_auc_score

from src.metrics_common import (
    MIN_ROWS_FOR_DECILE,
    RANDOM_RANKING_REFERENCE_DRAWS,
    RANDOM_RANKING_SEED,
    RANKING_K_GRID,
    RANKING_K_LABELS,
    TOP_K_STATUS_OK,
    TOP_K_STATUS_UNSUPPORTED,
    AteResult,
    MetricContractError,
    RankingMetrics,
    ResponseDiagnostics,
    metric_definitions_payload,
    select_curve_points,
)

__all__ = [
    "AteResult",
    "RankingMetrics",
    "ResponseDiagnostics",
    "MetricContractError",
    "compute_ate",
    "evaluate_ranking",
    "response_diagnostics",
    "seeded_random_scores",
    "random_ranking_reference_distribution",
    "metric_definitions",
]


def _as_array(values, dtype=np.float64) -> np.ndarray:
    return np.asarray(values, dtype=dtype)


def _validate_binary_complete(values: np.ndarray, name: str) -> None:
    if np.isnan(values).any():
        raise MetricContractError(f"{name} contains missing values")
    unique = set(values.tolist())
    if not unique.issubset({0.0, 1.0}):
        raise MetricContractError(f"{name} contains values outside {{0,1}}: {unique}")


def _validate_ranking_inputs(scores, treatment, outcome, source_row_id):
    scores = _as_array(scores)
    treatment = _as_array(treatment)
    outcome = _as_array(outcome)
    source_row_id_raw = _as_array(source_row_id, dtype=np.float64)
    if np.isnan(source_row_id_raw).any():
        raise MetricContractError("_source_row_id contains missing values")
    source_row_id = source_row_id_raw.astype(np.int64)

    lengths = {len(scores), len(treatment), len(outcome), len(source_row_id)}
    if len(lengths) != 1:
        raise MetricContractError(f"Mismatched input lengths: {lengths}")
    n = len(scores)
    if n == 0:
        raise MetricContractError("Empty evaluation population")
    if not np.isfinite(scores).all():
        raise MetricContractError("Scores contain non-finite values")
    if pd.Series(source_row_id).duplicated().any():
        raise MetricContractError("_source_row_id is not unique within the evaluation population")

    _validate_binary_complete(treatment, "treatment")
    _validate_binary_complete(outcome, "outcome")
    if not (treatment == 1).any() or not (treatment == 0).any():
        raise MetricContractError("Both treatment arms must be present (missing arm)")

    return scores, treatment, outcome, source_row_id, n


def compute_ate(treatment, outcome) -> AteResult:
    """ate = p1 - p0, with the unpooled normal difference-in-proportions interval."""

    treatment = _as_array(treatment)
    outcome = _as_array(outcome)
    if len(treatment) != len(outcome):
        raise MetricContractError("treatment and outcome must have equal length")
    if len(treatment) == 0:
        raise MetricContractError("Empty evaluation population")
    _validate_binary_complete(treatment, "treatment")
    _validate_binary_complete(outcome, "outcome")

    n1 = int((treatment == 1).sum())
    n0 = int((treatment == 0).sum())
    if n1 == 0 or n0 == 0:
        raise MetricContractError("ATE is undefined: an arm is empty")

    p1 = float(outcome[treatment == 1].mean())
    p0 = float(outcome[treatment == 0].mean())
    ate = p1 - p0
    se = math.sqrt(p1 * (1 - p1) / n1 + p0 * (1 - p0) / n0)
    relative_lift = (ate / p0) if p0 > 0 else None
    return AteResult(
        ate=ate,
        se=se,
        ci_95_low=ate - 1.96 * se,
        ci_95_high=ate + 1.96 * se,
        ate_percentage_points=100 * ate,
        relative_lift=relative_lift,
    )


def evaluate_ranking(scores, treatment, outcome, source_row_id) -> RankingMetrics:
    """Production implementation: vectorized cumulative-sum arithmetic."""

    scores, treatment, outcome, source_row_id, n = _validate_ranking_inputs(
        scores, treatment, outcome, source_row_id
    )
    if n < MIN_ROWS_FOR_DECILE:
        raise MetricContractError(f"Decile uplift requires N >= {MIN_ROWS_FOR_DECILE}, got N={n}")

    frame = pd.DataFrame({"score": scores, "treatment": treatment, "outcome": outcome, "source_row_id": source_row_id})
    ranked = frame.sort_values(["score", "source_row_id"], ascending=[False, True]).reset_index(drop=True)

    is_treated = (ranked["treatment"] == 1).to_numpy()
    is_control = ~is_treated
    outcome_arr = ranked["outcome"].to_numpy()

    cum_n1 = np.cumsum(is_treated)
    cum_n0 = np.cumsum(is_control)
    cum_y1 = np.cumsum(is_treated * outcome_arr)
    cum_y0 = np.cumsum(is_control * outcome_arr)

    valid = cum_n0 > 0
    if not valid.any():
        raise MetricContractError("No valid Qini prefix exists (cum_n0 never positive)")

    ranks = np.arange(1, n + 1)
    with np.errstate(divide="ignore", invalid="ignore"):
        qini_gain_all = cum_y1 - cum_y0 * (cum_n1 / np.where(cum_n0 == 0, np.nan, cum_n0))
    coverage_array = (ranks[valid] / n).astype(np.float64)
    gain_array = qini_gain_all[valid].astype(np.float64)

    q_full = float(gain_array[-1])
    curve = select_curve_points(coverage_array, gain_array)

    c = curve["coverage"].to_numpy()
    q = curve["qini_gain"].to_numpy()
    qini_area = float(np.sum(0.5 * (q[1:] + q[:-1]) * (c[1:] - c[:-1])))

    theoretical_random_qini_area = q_full / 2.0
    qini_above_random = qini_area - theoretical_random_qini_area

    # Uplift@K: first m_k ranked rows for each frozen coverage grid value.
    # docs/07 (higher-precedence than Issue #7's wording) says a missing arm at
    # a given K makes the numeric value NA -- so uplift_at_k/incremental_at_k
    # stay float | None. top_k_status is the separate, minimal reason field
    # (see TOP_K_STATUS_* in metrics_common.py) that records *why* it is None.
    uplift_at_k: dict[str, float | None] = {}
    incremental_at_k: dict[str, float | None] = {}
    top_k_status: dict[str, str] = {}
    for k, label in zip(RANKING_K_GRID, RANKING_K_LABELS):
        m_k = min(n, max(1, math.ceil(k * n)))
        n1_k = int(cum_n1[m_k - 1])
        n0_k = int(cum_n0[m_k - 1])
        if n1_k == 0 or n0_k == 0:
            uplift_at_k[label] = None
            incremental_at_k[label] = None
            top_k_status[label] = TOP_K_STATUS_UNSUPPORTED
        else:
            y1_k = float(cum_y1[m_k - 1])
            y0_k = float(cum_y0[m_k - 1])
            value = (y1_k / n1_k) - (y0_k / n0_k)
            uplift_at_k[label] = value
            incremental_at_k[label] = m_k * value
            top_k_status[label] = TOP_K_STATUS_OK

    # Decile: decile(r) = 1 + floor(10*(r-1)/N), vectorized via integer floor division.
    decile_id = 1 + ((ranks - 1) * 10) // n
    decile_frame = pd.DataFrame(
        {
            "decile": decile_id,
            "treatment": ranked["treatment"].to_numpy(),
            "outcome": outcome_arr,
        }
    )
    decile_rows = []
    for b in range(1, 11):
        subset = decile_frame.loc[decile_frame["decile"] == b]
        n1_b = int((subset["treatment"] == 1).sum())
        n0_b = int((subset["treatment"] == 0).sum())
        y1_b = float(subset.loc[subset["treatment"] == 1, "outcome"].sum())
        y0_b = float(subset.loc[subset["treatment"] == 0, "outcome"].sum())
        if n1_b == 0 or n0_b == 0:
            treated_rate = control_rate = observed_uplift = incremental = None
        else:
            treated_rate = y1_b / n1_b
            control_rate = y0_b / n0_b
            observed_uplift = treated_rate - control_rate
            incremental = len(subset) * observed_uplift
        decile_rows.append(
            {
                "decile": b,
                "n": int(len(subset)),
                "n1": n1_b,
                "n0": n0_b,
                "y1": y1_b,
                "y0": y0_b,
                "treated_rate": treated_rate,
                "control_rate": control_rate,
                "observed_uplift": observed_uplift,
                "incremental_conversions": incremental,
                "low_control_conversion_warning": y0_b < 5,
            }
        )

    return RankingMetrics(
        n=n,
        qini_area=qini_area,
        theoretical_random_qini_area=theoretical_random_qini_area,
        qini_above_random=qini_above_random,
        uplift_at_k=uplift_at_k,
        incremental_conversions_at_k=incremental_at_k,
        top_k_status=top_k_status,
        decile_table=pd.DataFrame(decile_rows),
        qini_curve=curve,
    )


def response_diagnostics(probability_scores, outcome) -> ResponseDiagnostics:
    """Response-model diagnostics only -- never a causal ranking metric.

    Single sklearn-backed implementation (see module docstring for why this is
    not duplicated the way the Qini/uplift formulas are).
    """

    probabilities = _as_array(probability_scores)
    outcome = _as_array(outcome)
    if len(probabilities) != len(outcome):
        raise MetricContractError("probability_scores and outcome must have equal length")
    if len(probabilities) == 0:
        raise MetricContractError("Empty evaluation population")
    if not np.isfinite(probabilities).all() or (probabilities < 0).any() or (probabilities > 1).any():
        raise MetricContractError("Response probabilities must lie in [0,1] and be finite")
    _validate_binary_complete(outcome, "outcome")
    if len(set(outcome.tolist())) < 2:
        raise MetricContractError("response_diagnostics requires both outcome classes to be present")

    bounded = np.clip(probabilities, 1e-15, 1 - 1e-15)  # numerical bound for log only; stored scores unmodified
    return ResponseDiagnostics(
        roc_auc=float(roc_auc_score(outcome, probabilities)),
        average_precision=float(average_precision_score(outcome, probabilities)),
        log_loss=float(log_loss(outcome, bounded, labels=[0, 1])),
    )


def seeded_random_scores(n: int, seed: int) -> np.ndarray:
    """Deterministic uniform random scores for one random-RANKING draw.

    Unrelated to T03-C's treatment-label permutation calibration (src/audit.py's
    CONDITIONAL_PERMUTATION_APPROXIMATION) -- this draws independent scores to
    rank by, not treatment reassignments.
    """

    if n <= 0:
        raise MetricContractError("n must be positive")
    rng = np.random.default_rng(seed)
    return rng.uniform(size=n)


def _random_ranking_draw_seed(master_seed: int, draw_index: int) -> int:
    """Deterministic per-draw sub-seed, using the same general SeedSequence +
    spawn_key technique as T03-C's replication seeds (src/audit.py) for
    project-wide seeding consistency -- not the identical derivation (T03-C
    seeds treatment-label permutations; this seeds independent random-ranking
    scores, a different quantity with its own spawn-key convention)."""

    sequence = np.random.SeedSequence(entropy=int(master_seed), spawn_key=(int(draw_index),))
    return int(sequence.generate_state(1, dtype=np.uint32)[0])


def _random_ranking_reference_distribution(
    treatment, outcome, source_row_id, *, n_draws: int, master_seed: int = RANDOM_RANKING_SEED
) -> pd.DataFrame:
    """Internal helper: `n_draws` independent random-ranking draws, each scored via
    evaluate_ranking(). Not the frozen public entry point -- see
    random_ranking_reference_distribution(). Exists so tests can exercise this
    machinery cheaply with a small draw count instead of the frozen 200.
    """

    n = len(treatment)
    rows = []
    for draw_index in range(n_draws):
        seed = _random_ranking_draw_seed(master_seed, draw_index)
        scores = seeded_random_scores(n, seed)
        result = evaluate_ranking(scores, treatment, outcome, source_row_id)
        rows.append(
            {
                "draw_index": draw_index,
                "seed": seed,
                "qini_area": result.qini_area,
                "qini_above_random": result.qini_above_random,
            }
        )
    return pd.DataFrame(rows)


def random_ranking_reference_distribution(
    treatment, outcome, source_row_id, *, master_seed: int = RANDOM_RANKING_SEED
) -> pd.DataFrame:
    """The frozen docs/07 random-RANKING reference distribution: exactly 200
    independent seeded random-score rankings (RANDOM_RANKING_REFERENCE_DRAWS).

    This is random-ranking reference logic for the uplift-metric no-skill
    baseline -- distinct from T03-C's treatment-assignment permutation
    calibration. The theoretical expected-random line remains the primary
    random reference; this distribution is secondary empirical context.
    The draw count is frozen and not a caller-supplied parameter.
    """

    return _random_ranking_reference_distribution(
        treatment, outcome, source_row_id, n_draws=RANDOM_RANKING_REFERENCE_DRAWS, master_seed=master_seed
    )


def metric_definitions() -> dict[str, Any]:
    """Serializable description of the frozen T06 metric contract, for hashing."""

    return metric_definitions_payload()
