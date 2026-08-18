"""Shared, non-causal scaffolding for the T06 uplift-metric implementations.

This module holds exactly what the T06 code plan approved as safe to share
between `src/metrics.py` (production, vectorized) and `src/metrics_reference.py`
(reference, loop-based, hand-verifiable): frozen constants, the result
dataclasses, the shared exception type, and the purely mechanical 151-point
curve-selection rule. None of this is causal ranking/Qini arithmetic -- that
logic is intentionally implemented twice, independently, and cross-checked in
tests/test_metrics.py so a bug in one cannot hide behind the other.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from src.data import DataContractError

RANKING_K_GRID: tuple[float, ...] = (0.10, 0.20, 0.30, 0.50, 1.00)
RANKING_K_LABELS: tuple[str, ...] = ("10pct", "20pct", "30pct", "50pct", "100pct")
CURVE_MAX_POINTS = 151
MIN_ROWS_FOR_DECILE = 10

# The frozen docs/07 random-RANKING reference distribution: exactly 200 independent
# seeded random-score rankings. This is unrelated to T03-C's treatment-label
# CONDITIONAL_PERMUTATION_APPROXIMATION (src/audit.py) -- that permutes treatment
# assignment for randomization-assumption calibration; this generates independent
# random SCORES to rank by, for the uplift-metric no-skill baseline.
RANDOM_RANKING_REFERENCE_DRAWS = 200
RANDOM_RANKING_SEED = 42

# Top-K status vocabulary. docs/07 (the higher-precedence numbered contract) says
# a top-K value with a missing arm is simply NA: "If either arm is absent, both
# values are NA... comparison at that coverage is blocked." Issue #7's "Frozen
# rules" separately say this case "is UNSUPPORTED_METRIC" -- read literally, that
# would mean overloading the numeric field with a string, which conflicts with
# docs/07's NA convention used everywhere else (deciles, ATE's relative_lift).
# Per source precedence (decision register > numbered contracts > Issue wording),
# docs/07 wins: the numeric field stays None/NA. TOP_K_STATUS_UNSUPPORTED is the
# minimal reason field docs/07 does not forbid, so a caller can still distinguish
# "undefined because an arm is absent" from any other reason without touching the
# numeric type. The Issue #7 wording is stale relative to docs/07 on this point;
# reconciling the Issue text is deferred until GitHub write access is available.
TOP_K_STATUS_OK = "OK"
TOP_K_STATUS_UNSUPPORTED = "UNSUPPORTED_METRIC"


class MetricContractError(DataContractError):
    """Raised when a T06 metric-computation contract is violated."""


@dataclass(frozen=True)
class AteResult:
    ate: float
    se: float
    ci_95_low: float
    ci_95_high: float
    ate_percentage_points: float
    relative_lift: float | None  # None = NA (p0 == 0)


@dataclass(frozen=True)
class RankingMetrics:
    n: int
    qini_area: float
    theoretical_random_qini_area: float
    qini_above_random: float
    uplift_at_k: dict[str, float | None]  # None = NA (docs/07); see top_k_status for why
    incremental_conversions_at_k: dict[str, float | None]
    top_k_status: dict[str, str]  # TOP_K_STATUS_OK or TOP_K_STATUS_UNSUPPORTED, keyed like uplift_at_k
    decile_table: pd.DataFrame
    qini_curve: pd.DataFrame


@dataclass(frozen=True)
class ResponseDiagnostics:
    roc_auc: float
    average_precision: float
    log_loss: float


def select_curve_points(
    coverage: np.ndarray,
    qini_gain: np.ndarray,
    *,
    max_points: int = CURVE_MAX_POINTS,
) -> pd.DataFrame:
    """Frozen, purely mechanical row-selection rule for the stored/plotted curve.

    Keeps every valid point if there are at most `max_points`; otherwise selects
    `max_points` unique integer positions from `round(linspace(0, L-1, max_points))`,
    which always retains the first and last valid point. Prepends the coverage-0
    origin. This selection (not the qini_gain values themselves) is shared between
    the reference and production implementations because it is index bookkeeping,
    not causal arithmetic -- sharing it cannot hide a Qini-formula bug, and NOT
    sharing it would make the two curves disagree on large populations for a
    reason unrelated to correctness.
    """

    valid_length = len(coverage)
    if valid_length != len(qini_gain):
        raise MetricContractError("coverage and qini_gain must have equal length")
    if valid_length <= max_points:
        indices = np.arange(valid_length)
    else:
        indices = np.unique(np.round(np.linspace(0, valid_length - 1, max_points)).astype(np.int64))
    curve = pd.DataFrame({"coverage": coverage[indices], "qini_gain": qini_gain[indices]})
    origin = pd.DataFrame({"coverage": [0.0], "qini_gain": [0.0]})
    return pd.concat([origin, curve], ignore_index=True)


def metric_definitions_payload() -> dict[str, Any]:
    """Serializable description of the frozen T06 metric contract, for hashing."""

    return {
        "contract_version": "t06-metrics-v1",
        "ranking_convention": "sort score descending; tie-break by _source_row_id ascending",
        "k_grid": list(RANKING_K_GRID),
        "curve_max_points": CURVE_MAX_POINTS,
        "min_rows_for_decile": MIN_ROWS_FOR_DECILE,
        "primary_statistic": "qini_above_random",
        "raw_qini_formula": "qini_gain(r) = cum_y1(r) - cum_y0(r) * cum_n1(r) / cum_n0(r), skipped where cum_n0(r) == 0",
        "expected_random_line": "Q_random(c) = c * Q_full; theoretical_random_qini_area = Q_full / 2",
        "random_ranking_reference": {
            "draws": RANDOM_RANKING_REFERENCE_DRAWS,
            "seed": RANDOM_RANKING_SEED,
            "role": "secondary empirical context; theoretical random line remains primary",
        },
        "uncertainty": "500 paired treatment-arm-stratified bootstrap draws; implemented in T15, not T06",
        "prohibited_labels": ["AUUC", "normalized Qini", "Qini coefficient", "uplift AUC", "PEHE"],
        "response_diagnostics": "roc_auc, average_precision, log_loss; diagnostic only, never selects a causal winner",
        "top_k_status": {
            "role": "reason field alongside uplift_at_k/incremental_conversions_at_k; never overloads the numeric value",
            "values": [TOP_K_STATUS_OK, TOP_K_STATUS_UNSUPPORTED],
            "unsupported_condition": (
                "either treatment arm has zero rows in the top-K prefix (n1_k == 0 or n0_k == 0); "
                "docs/07 (higher precedence than Issue #7's wording) governs: the numeric value stays NA (None), "
                f"and status is {TOP_K_STATUS_UNSUPPORTED!r}"
            ),
        },
    }
