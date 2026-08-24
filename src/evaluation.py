"""Uplift-ranking evaluation: ATE, Qini curve/area, uplift@K, response
diagnostics.

Qini definition: rank rows by predicted uplift score, descending. At each
prefix of size r,

    qini_gain(r) = cum_y1(r) - cum_y0(r) * cum_n1(r) / cum_n0(r)

where cum_n1/cum_n0/cum_y1/cum_y0 are cumulative treated/control counts and
outcome sums within the prefix. This is the observed cumulative incremental
outcome versus what the control arm's response rate would predict for the
same number of treated units. The theoretical random-ranking reference line
is Q_random(c) = c * Q_full, i.e. theoretical_random_qini_area = Q_full / 2.
qini_above_random is the primary summary statistic used to compare models.

AUUC (area under the uplift curve) is reported alongside it as a second,
differently-weighted view of the same ranking. The uplift curve differs from
Qini in how it handles arm imbalance:

    uplift_gain(r) = (cum_y1(r)/cum_n1(r) - cum_y0(r)/cum_n0(r)) * r

i.e. the difference of the two arms' response *rates*, scaled by prefix
size, rather than Qini's count-ratio reweighting of the control outcome sum.
Both are reported above their own theoretical random reference (area / 2).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, log_loss, roc_auc_score

RANKING_K_GRID = (0.10, 0.20, 0.30, 0.50, 1.00)
RANKING_K_LABELS = ("10pct", "20pct", "30pct", "50pct", "100pct")


def _as_array(values, dtype=np.float64) -> np.ndarray:
    return np.asarray(values, dtype=dtype)


@dataclass(frozen=True)
class AteResult:
    ate: float
    se: float
    ci_95_low: float
    ci_95_high: float
    relative_lift: float | None


def compute_ate(treatment, outcome) -> AteResult:
    """ate = p1 - p0, with the unpooled normal difference-in-proportions interval."""

    treatment, outcome = _as_array(treatment), _as_array(outcome)
    n1, n0 = int((treatment == 1).sum()), int((treatment == 0).sum())
    if n1 == 0 or n0 == 0:
        raise ValueError("ATE is undefined: an arm is empty")
    p1, p0 = float(outcome[treatment == 1].mean()), float(outcome[treatment == 0].mean())
    ate = p1 - p0
    se = math.sqrt(p1 * (1 - p1) / n1 + p0 * (1 - p0) / n0)
    return AteResult(
        ate=ate, se=se, ci_95_low=ate - 1.96 * se, ci_95_high=ate + 1.96 * se,
        relative_lift=(ate / p0) if p0 > 0 else None,
    )


@dataclass(frozen=True)
class RankingMetrics:
    n: int
    qini_area: float
    theoretical_random_qini_area: float
    qini_above_random: float
    auuc_area: float
    theoretical_random_auuc_area: float
    auuc_above_random: float
    uplift_at_k: dict[str, float | None]
    decile_table: pd.DataFrame
    qini_curve: pd.DataFrame
    uplift_curve: pd.DataFrame


def evaluate_ranking(scores, treatment, outcome) -> RankingMetrics:
    scores, treatment, outcome = _as_array(scores), _as_array(treatment), _as_array(outcome)
    n = len(scores)
    if n == 0:
        raise ValueError("Empty evaluation population")
    if not ((treatment == 1).any() and (treatment == 0).any()):
        raise ValueError("Both treatment arms must be present")

    order = np.lexsort((np.arange(n), -scores))  # score desc, stable tie-break
    treatment, outcome = treatment[order], outcome[order]

    is_treated = treatment == 1
    cum_n1 = np.cumsum(is_treated)
    cum_n0 = np.cumsum(~is_treated)
    cum_y1 = np.cumsum(is_treated * outcome)
    cum_y0 = np.cumsum((~is_treated) * outcome)

    valid = cum_n0 > 0
    if not valid.any():
        raise ValueError("No valid Qini prefix exists (cum_n0 never positive)")
    ranks = np.arange(1, n + 1)
    with np.errstate(divide="ignore", invalid="ignore"):
        gain_all = cum_y1 - cum_y0 * (cum_n1 / np.where(cum_n0 == 0, np.nan, cum_n0))
    coverage, gain = (ranks[valid] / n).astype(np.float64), gain_all[valid].astype(np.float64)

    q_full = float(gain[-1])
    curve = pd.DataFrame({"coverage": np.concatenate([[0.0], coverage]), "qini_gain": np.concatenate([[0.0], gain])})
    c, q = curve["coverage"].to_numpy(), curve["qini_gain"].to_numpy()
    qini_area = float(np.sum(0.5 * (q[1:] + q[:-1]) * (c[1:] - c[:-1])))
    theoretical_random_qini_area = q_full / 2.0

    # Uplift curve / AUUC. Distinct from Qini: Qini reweights the control
    # arm's outcome sum by the treated/control count ratio, whereas the
    # uplift curve takes the difference of the two arms' response *rates*
    # and scales it by the prefix size:
    #     uplift_gain(r) = (cum_y1(r)/cum_n1(r) - cum_y0(r)/cum_n0(r)) * r
    # Only prefixes where BOTH arms are present are defined.
    both_arms = (cum_n0 > 0) & (cum_n1 > 0)
    if not both_arms.any():
        raise ValueError("No valid uplift prefix exists (never both arms present)")
    with np.errstate(divide="ignore", invalid="ignore"):
        rate1 = np.where(cum_n1 == 0, np.nan, cum_y1 / np.where(cum_n1 == 0, np.nan, cum_n1))
        rate0 = np.where(cum_n0 == 0, np.nan, cum_y0 / np.where(cum_n0 == 0, np.nan, cum_n0))
        uplift_gain_all = (rate1 - rate0) * ranks
    uplift_coverage = (ranks[both_arms] / n).astype(np.float64)
    uplift_gain = uplift_gain_all[both_arms].astype(np.float64)

    u_full = float(uplift_gain[-1])
    uplift_curve_frame = pd.DataFrame({
        "coverage": np.concatenate([[0.0], uplift_coverage]),
        "uplift_gain": np.concatenate([[0.0], uplift_gain]),
    })
    uc, ug = uplift_curve_frame["coverage"].to_numpy(), uplift_curve_frame["uplift_gain"].to_numpy()
    auuc_area = float(np.sum(0.5 * (ug[1:] + ug[:-1]) * (uc[1:] - uc[:-1])))
    theoretical_random_auuc_area = u_full / 2.0

    uplift_at_k: dict[str, float | None] = {}
    for k, label in zip(RANKING_K_GRID, RANKING_K_LABELS):
        m = min(n, max(1, math.ceil(k * n)))
        n1_k, n0_k = int(cum_n1[m - 1]), int(cum_n0[m - 1])
        uplift_at_k[label] = None if (n1_k == 0 or n0_k == 0) else float(cum_y1[m - 1] / n1_k - cum_y0[m - 1] / n0_k)

    decile_id = 1 + ((ranks - 1) * 10) // n
    decile_rows = []
    for b in range(1, 11):
        mask = decile_id == b
        t_b, o_b = treatment[mask], outcome[mask]
        n1_b, n0_b = int((t_b == 1).sum()), int((t_b == 0).sum())
        rate1 = float(o_b[t_b == 1].mean()) if n1_b else None
        rate0 = float(o_b[t_b == 0].mean()) if n0_b else None
        decile_rows.append({
            "decile": b, "n": int(mask.sum()), "n1": n1_b, "n0": n0_b,
            "observed_uplift": (rate1 - rate0) if (rate1 is not None and rate0 is not None) else None,
        })

    return RankingMetrics(
        n=n, qini_area=qini_area, theoretical_random_qini_area=theoretical_random_qini_area,
        qini_above_random=qini_area - theoretical_random_qini_area,
        auuc_area=auuc_area, theoretical_random_auuc_area=theoretical_random_auuc_area,
        auuc_above_random=auuc_area - theoretical_random_auuc_area,
        uplift_at_k=uplift_at_k,
        decile_table=pd.DataFrame(decile_rows), qini_curve=curve,
        uplift_curve=uplift_curve_frame,
    )


@dataclass(frozen=True)
class ResponseDiagnostics:
    roc_auc: float
    average_precision: float
    log_loss: float


def response_diagnostics(probability_scores, outcome) -> ResponseDiagnostics:
    """Response-model diagnostics only -- never a causal ranking metric."""

    probabilities, outcome = _as_array(probability_scores), _as_array(outcome)
    bounded = np.clip(probabilities, 1e-15, 1 - 1e-15)
    return ResponseDiagnostics(
        roc_auc=float(roc_auc_score(outcome, probabilities)),
        average_precision=float(average_precision_score(outcome, probabilities)),
        log_loss=float(log_loss(outcome, bounded, labels=[0, 1])),
    )
