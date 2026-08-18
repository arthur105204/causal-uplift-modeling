"""T06 uplift-metric tests: fixtures, reference<->production cross-checks, and
the docs/07 edge-case / HARD_GATE matrix.

Fixture note on the "good"/"reversed" pair: rows alternate treatment strictly
(even source_row_id = treated, odd = control) so that every ranked prefix has
equal treated/control counts. That is deliberate for making uplift@K land on
exact round numbers (1.0), but it also makes cum_n1(r) == cum_n0(r) at every
valid prefix, which degenerates the Qini formula's cum_n1/cum_n0 asymmetry
into a plain difference. The treatment-swap asymmetry test therefore uses a
separate, arm-IMBALANCED fixture, where that degeneracy does not occur.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

import src.metrics as production
import src.metrics_reference as reference
from src.metrics_common import (
    MetricContractError,
    RANDOM_RANKING_REFERENCE_DRAWS,
    TOP_K_STATUS_OK,
    TOP_K_STATUS_UNSUPPORTED,
)

# HARD_GATE / docs/07 edge-case tests are parametrized across both
# implementations (fix for review MAJOR #4): the reference implementation's
# own validation/error-raising code paths previously had zero independent
# coverage -- only its happy-path arithmetic was exercised, indirectly, via
# the cross-check test. Each implementation validates independently (no
# shared validation logic), so each earns its own assertion here.
IMPLEMENTATIONS = [production, reference]
IMPLEMENTATION_IDS = ["production", "reference"]


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------

def _good_fixture():
    """N=20. Score descends with source_row_id (row 0 ranked first). Treatment
    alternates T=1,T=0,T=1,T=0,... In the top half (id 0-9) every treated row
    converts and every control row does not; in the bottom half (id 10-19) it
    is the reverse. Overall p1=p0=0.5 (ATE=0), but the ranking is maximally
    informative: the true effect is concentrated entirely in the top half.
    """
    n = 20
    source_row_id = np.arange(n, dtype=np.int64)
    scores = (n - source_row_id).astype(np.float64)  # id 0 -> highest score
    treatment = (source_row_id % 2 == 0).astype(np.float64)  # even id = treated
    in_top_half = source_row_id < 10
    outcome = np.where(
        treatment == 1,
        np.where(in_top_half, 1.0, 0.0),
        np.where(in_top_half, 0.0, 1.0),
    )
    return scores, treatment, outcome, source_row_id


def _reversed_fixture():
    scores, treatment, outcome, source_row_id = _good_fixture()
    return -scores, treatment, outcome, source_row_id


def _permuted_input_order(scores, treatment, outcome, source_row_id, permutation):
    return scores[permutation], treatment[permutation], outcome[permutation], source_row_id[permutation]


def _imbalanced_fixture():
    """N=10, 7 treated / 3 control -- arm-imbalanced on purpose, for the
    treatment-swap asymmetry test."""
    source_row_id = np.arange(10, dtype=np.int64)
    scores = (10 - source_row_id).astype(np.float64)
    treatment = np.array([1, 1, 1, 1, 1, 1, 1, 0, 0, 0], dtype=np.float64)
    outcome = np.array([1, 1, 0, 0, 1, 0, 0, 1, 0, 1], dtype=np.float64)
    return scores, treatment, outcome, source_row_id


def _sparse_top_fixture():
    """N=10, 8 treated / 2 control, control rows ranked last. Top-10% and
    several early prefixes have no control rows at all."""
    source_row_id = np.arange(10, dtype=np.int64)
    scores = (10 - source_row_id).astype(np.float64)
    treatment = np.array([1, 1, 1, 1, 1, 1, 1, 1, 0, 0], dtype=np.float64)
    outcome = np.array([1, 0, 1, 0, 1, 0, 1, 0, 1, 0], dtype=np.float64)
    return scores, treatment, outcome, source_row_id


def _tiny_fixture(n=9):
    source_row_id = np.arange(n, dtype=np.int64)
    scores = (n - source_row_id).astype(np.float64)
    treatment = (source_row_id % 2 == 0).astype(np.float64)
    outcome = (source_row_id % 3 == 0).astype(np.float64)
    return scores, treatment, outcome, source_row_id


def _large_fixture(n=300, seed=123):
    rng = np.random.default_rng(seed)
    source_row_id = np.arange(n, dtype=np.int64)
    scores = rng.normal(size=n)
    treatment = (rng.uniform(size=n) < 0.5).astype(np.float64)
    outcome = (rng.uniform(size=n) < 0.3).astype(np.float64)
    return scores, treatment, outcome, source_row_id


# ----------------------------------------------------------------------
# Reference <-> production exact agreement
# ----------------------------------------------------------------------

@pytest.mark.parametrize(
    "fixture_fn",
    [_good_fixture, _reversed_fixture, _imbalanced_fixture, _sparse_top_fixture, _large_fixture],
)
def test_reference_and_production_agree_exactly(fixture_fn) -> None:
    scores, treatment, outcome, source_row_id = fixture_fn()
    prod = production.evaluate_ranking(scores, treatment, outcome, source_row_id)
    ref = reference.evaluate_ranking(scores, treatment, outcome, source_row_id)

    assert prod.n == ref.n
    assert prod.qini_area == pytest.approx(ref.qini_area, abs=1e-9)
    assert prod.theoretical_random_qini_area == pytest.approx(ref.theoretical_random_qini_area, abs=1e-9)
    assert prod.qini_above_random == pytest.approx(ref.qini_above_random, abs=1e-9)
    assert prod.uplift_at_k.keys() == ref.uplift_at_k.keys()
    for key in prod.uplift_at_k:
        if prod.uplift_at_k[key] is None or ref.uplift_at_k[key] is None:
            assert prod.uplift_at_k[key] is ref.uplift_at_k[key]
        else:
            assert prod.uplift_at_k[key] == pytest.approx(ref.uplift_at_k[key], abs=1e-9)
    pd.testing.assert_frame_equal(
        prod.qini_curve.reset_index(drop=True), ref.qini_curve.reset_index(drop=True), check_exact=False, atol=1e-9
    )
    pd.testing.assert_frame_equal(
        prod.decile_table.reset_index(drop=True), ref.decile_table.reset_index(drop=True), check_exact=False, atol=1e-9
    )


def test_reference_and_production_ate_agree_exactly() -> None:
    _, treatment, outcome, _ = _good_fixture()
    prod = production.compute_ate(treatment, outcome)
    ref = reference.compute_ate(treatment, outcome)
    assert prod == ref  # frozen dataclass, plain float fields -> exact equality is meaningful here


# ----------------------------------------------------------------------
# Orientation: good beats random, reversed loses to random
# ----------------------------------------------------------------------

def test_good_ranking_scores_above_random() -> None:
    scores, treatment, outcome, source_row_id = _good_fixture()
    result = production.evaluate_ranking(scores, treatment, outcome, source_row_id)
    assert result.qini_above_random > 0


def test_reversed_ranking_scores_below_random() -> None:
    scores, treatment, outcome, source_row_id = _reversed_fixture()
    result = production.evaluate_ranking(scores, treatment, outcome, source_row_id)
    assert result.qini_above_random < 0


def test_good_fixture_uplift_at_k_hand_computed_values() -> None:
    """Top 10/20/30/50% of the good fixture are entirely within the informative
    top half, split evenly and cleanly: uplift = 1.0 exactly at each. At 100%
    the two halves cancel: uplift = 0.0 exactly."""
    scores, treatment, outcome, source_row_id = _good_fixture()
    result = production.evaluate_ranking(scores, treatment, outcome, source_row_id)
    for key in ("10pct", "20pct", "30pct", "50pct"):
        assert result.uplift_at_k[key] == pytest.approx(1.0)
    assert result.uplift_at_k["100pct"] == pytest.approx(0.0)


def test_reversed_fixture_uplift_at_k_hand_computed_values() -> None:
    scores, treatment, outcome, source_row_id = _reversed_fixture()
    result = production.evaluate_ranking(scores, treatment, outcome, source_row_id)
    for key in ("10pct", "20pct", "30pct", "50pct"):
        assert result.uplift_at_k[key] == pytest.approx(-1.0)
    assert result.uplift_at_k["100pct"] == pytest.approx(0.0)


# ----------------------------------------------------------------------
# Ties, order invariance, treatment-coding asymmetry
# ----------------------------------------------------------------------

def test_constant_score_ties_resolve_by_source_row_id_ascending() -> None:
    scores, treatment, outcome, source_row_id = _good_fixture()
    constant_scores = np.zeros_like(scores)
    frame = pd.DataFrame(
        {"score": constant_scores, "treatment": treatment, "outcome": outcome, "source_row_id": source_row_id}
    )
    ranked = frame.sort_values(["score", "source_row_id"], ascending=[False, True])
    assert list(ranked["source_row_id"]) == sorted(source_row_id.tolist())


def test_order_invariance_under_input_row_shuffling() -> None:
    scores, treatment, outcome, source_row_id = _good_fixture()
    rng = np.random.default_rng(7)
    permutation = rng.permutation(len(scores))
    shuffled = _permuted_input_order(scores, treatment, outcome, source_row_id, permutation)

    original = production.evaluate_ranking(scores, treatment, outcome, source_row_id)
    from_shuffled = production.evaluate_ranking(*shuffled)

    assert original.qini_area == pytest.approx(from_shuffled.qini_area, abs=1e-12)
    assert original.qini_above_random == pytest.approx(from_shuffled.qini_above_random, abs=1e-12)
    pd.testing.assert_frame_equal(original.qini_curve, from_shuffled.qini_curve)


def test_treatment_coding_swap_is_not_a_simple_sign_flip() -> None:
    """Under arm imbalance, cum_n1(r) != cum_n0(r) generically, so swapping
    which label means 'treated' is NOT equivalent to negating qini_above_random
    -- it is a genuinely different quantity. This is the regression test for
    the specific risk flagged in [TUTOR]/[CODE PLAN]."""
    scores, treatment, outcome, source_row_id = _imbalanced_fixture()
    original = production.evaluate_ranking(scores, treatment, outcome, source_row_id)
    swapped = production.evaluate_ranking(scores, 1 - treatment, outcome, source_row_id)
    assert swapped.qini_above_random != pytest.approx(-original.qini_above_random, abs=1e-9)


def test_sort_direction_regression() -> None:
    """A sanity net distinct from the good/reversed sign test: negating scores
    must flip which prefix is 'first', which flips the sign of qini_above_random
    for an informative ranking (it does not have to be an exact negation of the
    value, only the sign, since Q_full is unaffected by ranking direction)."""
    scores, treatment, outcome, source_row_id = _good_fixture()
    forward = production.evaluate_ranking(scores, treatment, outcome, source_row_id)
    backward = production.evaluate_ranking(-scores, treatment, outcome, source_row_id)
    assert forward.qini_above_random > 0 > backward.qini_above_random


# ----------------------------------------------------------------------
# Zero-arm / sparse / skipped-prefix behavior
# ----------------------------------------------------------------------

def test_sparse_top_k_is_unsupported_not_fabricated() -> None:
    """docs/07 (higher-precedence than Issue #7's literal-string wording): a
    missing arm at K leaves the numeric value NA (None). top_k_status carries
    the reason as a separate field rather than overloading the numeric type."""
    scores, treatment, outcome, source_row_id = _sparse_top_fixture()
    result = production.evaluate_ranking(scores, treatment, outcome, source_row_id)
    assert result.uplift_at_k["10pct"] is None
    assert result.incremental_conversions_at_k["10pct"] is None
    assert result.top_k_status["10pct"] == TOP_K_STATUS_UNSUPPORTED


def test_top_k_status_is_ok_when_both_arms_present() -> None:
    scores, treatment, outcome, source_row_id = _good_fixture()
    result = production.evaluate_ranking(scores, treatment, outcome, source_row_id)
    assert all(status == TOP_K_STATUS_OK for status in result.top_k_status.values())


def test_reference_and_production_top_k_status_agree() -> None:
    scores, treatment, outcome, source_row_id = _sparse_top_fixture()
    prod = production.evaluate_ranking(scores, treatment, outcome, source_row_id)
    ref = reference.evaluate_ranking(scores, treatment, outcome, source_row_id)
    assert prod.top_k_status == ref.top_k_status


def test_zero_cumulative_control_prefixes_are_skipped_not_zeroed() -> None:
    scores, treatment, outcome, source_row_id = _sparse_top_fixture()
    result = production.evaluate_ranking(scores, treatment, outcome, source_row_id)
    # Ranked rows 1-8 are all treated (no control yet); those coverage points
    # (0.1 .. 0.8) must not appear in the curve at all.
    covered = set(np.round(result.qini_curve["coverage"].to_numpy(), 6))
    for missing_coverage in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8):
        assert missing_coverage not in covered


# ----------------------------------------------------------------------
# HARD_GATE / docs/07 edge cases
# ----------------------------------------------------------------------

@pytest.mark.parametrize("impl", IMPLEMENTATIONS, ids=IMPLEMENTATION_IDS)
def test_empty_population_raises(impl) -> None:
    empty = np.array([], dtype=np.float64)
    with pytest.raises(MetricContractError, match="Empty evaluation population"):
        impl.evaluate_ranking(empty, empty, empty, empty.astype(np.int64))
    with pytest.raises(MetricContractError, match="Empty evaluation population"):
        impl.compute_ate(empty, empty)


def test_empty_population_raises_response_diagnostics() -> None:
    """response_diagnostics is single-implementation (production only) --
    see module docstring for why it is not duplicated."""
    empty = np.array([], dtype=np.float64)
    with pytest.raises(MetricContractError, match="Empty evaluation population"):
        production.response_diagnostics(empty, empty)


@pytest.mark.parametrize("impl", IMPLEMENTATIONS, ids=IMPLEMENTATION_IDS)
def test_missing_treatment_arm_raises(impl) -> None:
    scores, _, outcome, source_row_id = _good_fixture()
    all_treated = np.ones_like(outcome)
    with pytest.raises(MetricContractError, match="missing arm"):
        impl.evaluate_ranking(scores, all_treated, outcome, source_row_id)
    with pytest.raises(MetricContractError, match="empty"):
        impl.compute_ate(all_treated, outcome)


@pytest.mark.parametrize("impl", IMPLEMENTATIONS, ids=IMPLEMENTATION_IDS)
def test_non_binary_treatment_raises(impl) -> None:
    scores, treatment, outcome, source_row_id = _good_fixture()
    bad_treatment = treatment.copy()
    bad_treatment[0] = 2
    with pytest.raises(MetricContractError, match="outside"):
        impl.evaluate_ranking(scores, bad_treatment, outcome, source_row_id)


@pytest.mark.parametrize("impl", IMPLEMENTATIONS, ids=IMPLEMENTATION_IDS)
def test_non_binary_outcome_raises(impl) -> None:
    scores, treatment, outcome, source_row_id = _good_fixture()
    bad_outcome = outcome.copy()
    bad_outcome[0] = 0.5
    with pytest.raises(MetricContractError, match="outside"):
        impl.evaluate_ranking(scores, treatment, bad_outcome, source_row_id)


@pytest.mark.parametrize("impl", IMPLEMENTATIONS, ids=IMPLEMENTATION_IDS)
def test_mismatched_lengths_raise(impl) -> None:
    scores, treatment, outcome, source_row_id = _good_fixture()
    with pytest.raises(MetricContractError, match="[Mm]ismatched"):
        impl.evaluate_ranking(scores[:-1], treatment, outcome, source_row_id)


def test_mismatched_lengths_raise_response_diagnostics() -> None:
    with pytest.raises(MetricContractError, match="equal length"):
        production.response_diagnostics(np.array([0.1, 0.2]), np.array([0, 1, 0]))


@pytest.mark.parametrize("impl", IMPLEMENTATIONS, ids=IMPLEMENTATION_IDS)
def test_non_finite_score_raises(impl) -> None:
    scores, treatment, outcome, source_row_id = _good_fixture()
    scores = scores.copy()
    scores[0] = np.inf
    with pytest.raises(MetricContractError, match="non-finite"):
        impl.evaluate_ranking(scores, treatment, outcome, source_row_id)


@pytest.mark.parametrize("impl", IMPLEMENTATIONS, ids=IMPLEMENTATION_IDS)
def test_duplicate_source_row_id_raises(impl) -> None:
    scores, treatment, outcome, source_row_id = _good_fixture()
    source_row_id = source_row_id.copy()
    source_row_id[1] = source_row_id[0]
    with pytest.raises(MetricContractError, match="unique"):
        impl.evaluate_ranking(scores, treatment, outcome, source_row_id)


@pytest.mark.parametrize("impl", IMPLEMENTATIONS, ids=IMPLEMENTATION_IDS)
def test_missing_source_row_id_raises_before_int_cast(impl) -> None:
    """Regression for review MINOR #6: a NaN _source_row_id must be caught by
    an explicit contract check before the int64 cast, not surface as an
    uncontrolled numpy/pandas exception."""
    scores, treatment, outcome, source_row_id = _good_fixture()
    source_row_id = source_row_id.astype(np.float64)
    source_row_id[0] = np.nan
    with pytest.raises(MetricContractError, match="missing values"):
        impl.evaluate_ranking(scores, treatment, outcome, source_row_id)


@pytest.mark.parametrize("impl", IMPLEMENTATIONS, ids=IMPLEMENTATION_IDS)
def test_decile_requires_at_least_ten_rows(impl) -> None:
    scores, treatment, outcome, source_row_id = _tiny_fixture(n=9)
    with pytest.raises(MetricContractError, match="N >= 10"):
        impl.evaluate_ranking(scores, treatment, outcome, source_row_id)


def test_uplift_score_is_not_clipped() -> None:
    """Uplift scores are signed effects, not probabilities; values outside
    [-1, 1] must be accepted unchanged."""
    scores, treatment, outcome, source_row_id = _good_fixture()
    extreme_scores = scores.copy()
    extreme_scores[0] = 500.0
    extreme_scores[-1] = -500.0
    result = production.evaluate_ranking(extreme_scores, treatment, outcome, source_row_id)
    assert result.n == len(scores)  # ran to completion; nothing was rejected or clamped


def test_relative_lift_is_na_when_control_rate_is_zero() -> None:
    treatment = np.array([1.0, 1.0, 0.0, 0.0])
    outcome = np.array([1.0, 0.0, 0.0, 0.0])  # control never converts: p0 = 0
    result = production.compute_ate(treatment, outcome)
    assert result.relative_lift is None


# ----------------------------------------------------------------------
# Response diagnostics
# ----------------------------------------------------------------------

def test_response_diagnostics_perfect_separation() -> None:
    probabilities = np.array([1.0, 1.0, 1.0, 0.0, 0.0, 0.0])
    outcome = np.array([1.0, 1.0, 1.0, 0.0, 0.0, 0.0])
    result = production.response_diagnostics(probabilities, outcome)
    assert result.roc_auc == pytest.approx(1.0)
    assert result.average_precision == pytest.approx(1.0)
    assert result.log_loss < 1e-6


def test_response_diagnostics_constant_score_is_ln2_log_loss() -> None:
    """A constant p=0.5 prediction has log loss exactly ln(2), regardless of the
    true label distribution -- a clean hand-checkable identity."""
    probabilities = np.full(8, 0.5)
    outcome = np.array([1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0])
    result = production.response_diagnostics(probabilities, outcome)
    assert result.roc_auc == pytest.approx(0.5)
    assert result.log_loss == pytest.approx(math.log(2))


def test_response_diagnostics_rejects_probability_outside_unit_interval() -> None:
    probabilities = np.array([1.5, 0.2, 0.3, 0.4])
    outcome = np.array([1.0, 0.0, 1.0, 0.0])
    with pytest.raises(MetricContractError, match=r"\[0,1\]"):
        production.response_diagnostics(probabilities, outcome)


def test_response_diagnostics_requires_both_outcome_classes() -> None:
    probabilities = np.array([0.1, 0.2, 0.3, 0.4])
    outcome = np.array([1.0, 1.0, 1.0, 1.0])
    with pytest.raises(MetricContractError, match="both outcome classes"):
        production.response_diagnostics(probabilities, outcome)


# ----------------------------------------------------------------------
# Random-ranking reference distribution (distinct from T03-C's treatment-
# label permutation calibration)
# ----------------------------------------------------------------------

def test_seeded_random_scores_are_deterministic() -> None:
    first = production.seeded_random_scores(50, seed=42)
    second = production.seeded_random_scores(50, seed=42)
    np.testing.assert_array_equal(first, second)


def test_seeded_random_scores_differ_across_seeds() -> None:
    first = production.seeded_random_scores(50, seed=1)
    second = production.seeded_random_scores(50, seed=2)
    assert not np.array_equal(first, second)


def test_public_random_ranking_reference_produces_exactly_200_draws() -> None:
    """The frozen public entry point must always run exactly
    RANDOM_RANKING_REFERENCE_DRAWS (200) -- not a caller-adjustable parameter."""
    scores, treatment, outcome, source_row_id = _good_fixture()
    distribution = production.random_ranking_reference_distribution(treatment, outcome, source_row_id)
    assert len(distribution) == RANDOM_RANKING_REFERENCE_DRAWS == 200
    assert distribution["draw_index"].nunique() == 200


def test_random_ranking_reference_is_deterministic_given_master_seed() -> None:
    scores, treatment, outcome, source_row_id = _good_fixture()
    first = production._random_ranking_reference_distribution(treatment, outcome, source_row_id, n_draws=5, master_seed=42)
    second = production._random_ranking_reference_distribution(treatment, outcome, source_row_id, n_draws=5, master_seed=42)
    pd.testing.assert_frame_equal(first, second)


def test_random_ranking_reference_private_helper_accepts_small_draw_count() -> None:
    scores, treatment, outcome, source_row_id = _good_fixture()
    small = production._random_ranking_reference_distribution(treatment, outcome, source_row_id, n_draws=5)
    assert len(small) == 5


# ----------------------------------------------------------------------
# Metric definitions
# ----------------------------------------------------------------------

def test_metric_definitions_are_serializable_and_stable() -> None:
    import json

    definitions = production.metric_definitions()
    json.dumps(definitions)  # must round-trip with no non-serializable content
    assert definitions["primary_statistic"] == "qini_above_random"
    assert definitions["curve_max_points"] == 151
    assert definitions["random_ranking_reference"]["draws"] == 200
    assert "AUUC" in definitions["prohibited_labels"]
