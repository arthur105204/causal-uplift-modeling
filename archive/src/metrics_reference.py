"""Reference (loop-based, obviously-correct) T06 uplift-metric implementation.

Clarity beats speed here on purpose: every formula is a direct, literal
translation of docs/07, written as an explicit loop over ranked rows rather
than a vectorized expression, so it can be checked by eye against the spec
and used to cross-check src/metrics.py (the production, vectorized
implementation) on identical fixtures. The two implementations intentionally
share no causal arithmetic -- only frozen constants, result dataclasses, and
the purely mechanical curve-point selection rule (src/metrics_common.py).
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from src.metrics_common import (
    MIN_ROWS_FOR_DECILE,
    RANKING_K_GRID,
    RANKING_K_LABELS,
    TOP_K_STATUS_OK,
    TOP_K_STATUS_UNSUPPORTED,
    AteResult,
    MetricContractError,
    RankingMetrics,
    select_curve_points,
)


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
    if len(set(source_row_id.tolist())) != n:
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

    y1 = float(outcome[treatment == 1].sum())
    y0 = float(outcome[treatment == 0].sum())
    p1 = y1 / n1
    p0 = y0 / n0
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
    """Reference implementation: an explicit loop over the ranked prefix."""

    scores, treatment, outcome, source_row_id, n = _validate_ranking_inputs(
        scores, treatment, outcome, source_row_id
    )
    if n < MIN_ROWS_FOR_DECILE:
        raise MetricContractError(f"Decile uplift requires N >= {MIN_ROWS_FOR_DECILE}, got N={n}")

    # Frozen ranking convention: sort score descending, tie-break by _source_row_id ascending.
    order = sorted(range(n), key=lambda i: (-scores[i], source_row_id[i]))

    cum_n1 = cum_n0 = cum_y1 = cum_y0 = 0
    coverage_points: list[float] = []
    qini_gain_points: list[float] = []
    decile_rows: dict[int, dict[str, float]] = {
        b: {"n": 0, "n1": 0, "n0": 0, "y1": 0, "y0": 0} for b in range(1, 11)
    }

    for zero_based_position, row_index in enumerate(order):
        r = zero_based_position + 1  # one-based rank
        # Cast to plain Python types at extraction: this reference implementation
        # must not leak numpy scalar types (e.g. numpy.float64 poisoning every
        # downstream accumulator via +=), which are numerically fine but break
        # plain JSON serialization of the final result.
        t = int(treatment[row_index])
        y = float(outcome[row_index])
        if t == 1:
            cum_n1 += 1
            cum_y1 += y
        else:
            cum_n0 += 1
            cum_y0 += y
        if cum_n0 > 0:
            gain = cum_y1 - cum_y0 * (cum_n1 / cum_n0)
            coverage_points.append(r / n)
            qini_gain_points.append(gain)

        decile_id = 1 + (10 * (r - 1)) // n
        bucket = decile_rows[decile_id]
        bucket["n"] += 1
        if t == 1:
            bucket["n1"] += 1
            bucket["y1"] += y
        else:
            bucket["n0"] += 1
            bucket["y0"] += y

    if not qini_gain_points:
        raise MetricContractError("No valid Qini prefix exists (cum_n0 never positive)")

    q_full = qini_gain_points[-1]
    coverage_array = np.array(coverage_points, dtype=np.float64)
    gain_array = np.array(qini_gain_points, dtype=np.float64)
    curve = select_curve_points(coverage_array, gain_array)

    qini_area = 0.0
    for j in range(1, len(curve)):
        c0, q0 = curve["coverage"].iloc[j - 1], curve["qini_gain"].iloc[j - 1]
        c1, q1 = curve["coverage"].iloc[j], curve["qini_gain"].iloc[j]
        qini_area += 0.5 * (q0 + q1) * (c1 - c0)

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
        n1_k = n0_k = y1_k = y0_k = 0
        for row_index in order[:m_k]:
            if treatment[row_index] == 1:
                n1_k += 1
                y1_k += outcome[row_index]
            else:
                n0_k += 1
                y0_k += outcome[row_index]
        if n1_k == 0 or n0_k == 0:
            uplift_at_k[label] = None
            incremental_at_k[label] = None
            top_k_status[label] = TOP_K_STATUS_UNSUPPORTED
        else:
            value = (y1_k / n1_k) - (y0_k / n0_k)
            uplift_at_k[label] = value
            incremental_at_k[label] = m_k * value
            top_k_status[label] = TOP_K_STATUS_OK

    decile_table_rows = []
    for decile_id in range(1, 11):
        bucket = decile_rows[decile_id]
        n1_b, n0_b, y1_b, y0_b = bucket["n1"], bucket["n0"], bucket["y1"], bucket["y0"]
        if n1_b == 0 or n0_b == 0:
            treated_rate = control_rate = observed_uplift = incremental = None
        else:
            treated_rate = y1_b / n1_b
            control_rate = y0_b / n0_b
            observed_uplift = treated_rate - control_rate
            incremental = bucket["n"] * observed_uplift
        decile_table_rows.append(
            {
                "decile": decile_id,
                "n": bucket["n"],
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

    # Final cast to plain Python floats: reading back through a pandas float64
    # column (curve["qini_gain"].iloc[...]) yields numpy.float64 regardless of
    # what fed the DataFrame, so this boundary is cast explicitly rather than
    # relying on every upstream accumulation to stay numpy-free.
    return RankingMetrics(
        n=n,
        qini_area=float(qini_area),
        theoretical_random_qini_area=float(theoretical_random_qini_area),
        qini_above_random=float(qini_above_random),
        uplift_at_k={key: (None if value is None else float(value)) for key, value in uplift_at_k.items()},
        incremental_conversions_at_k={
            key: (None if value is None else float(value)) for key, value in incremental_at_k.items()
        },
        top_k_status=top_k_status,
        decile_table=pd.DataFrame(decile_table_rows),
        qini_curve=curve,
    )
