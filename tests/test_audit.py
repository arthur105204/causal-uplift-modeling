from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import log_loss

from src.audit import (
    FEATURE_COLUMNS,
    LIGHTGBM_TREATMENT_CONFIG,
    ORDERING_CONTRACT_VERSION,
    AuditContractError,
    algorithm_contract,
    balance_diagnostics,
    binomial_order_statistic_interval_ranks,
    build_treatment_stratified_folds,
    calibration_artifact_schema,
    canonical_block_membership_hash,
    conditional_permute_treatment,
    continuation_indices,
    cross_fitted_treatment_predictability,
    cross_split_profile_overlap,
    deferred_evidence_record,
    diagnostic_action,
    duplicate_audit,
    empirical_order_statistic,
    empirical_tail_fraction,
    hash_row_mapping,
    monte_carlo_order_statistic_interval,
    monte_carlo_action_stability,
    precision_reconciliation,
    replication_seed_metadata,
    smd_feature_record,
    validate_evidence_record,
    validate_no_permutation_p_value_language,
    validate_pre_split_frame,
    verify_regenerated_mapping_hash,
    write_fixture_mapping_new,
    write_t03_csv_new,
    write_t03_json_new,
)
from src.data import DataContractError, assert_model_feature_contract


def _frame(rows: int = 20) -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            feature: np.arange(rows, dtype=np.float64) + index / 100.0
            for index, feature in enumerate(FEATURE_COLUMNS)
        }
    )
    frame["treatment"] = np.arange(rows) % 2
    frame["conversion"] = (np.arange(rows) // 2) % 2
    frame["visit"] = (np.arange(rows) + 1) % 2
    frame["exposure"] = np.arange(rows) % 2
    frame["_source_row_id"] = np.arange(rows, dtype=np.int64)
    return frame


def test_malformed_schema_fails_closed() -> None:
    with pytest.raises(AuditContractError, match="Missing required columns"):
        validate_pre_split_frame(_frame().drop(columns="f11"))


@pytest.mark.parametrize("column", ["treatment", "conversion"])
def test_invalid_binary_t_or_y_fails_closed(column: str) -> None:
    frame = _frame()
    frame.loc[0, column] = 2
    with pytest.raises(AuditContractError, match="outside"):
        validate_pre_split_frame(frame)


def test_feature_nan_is_reported_not_imputed() -> None:
    frame = _frame()
    frame.loc[0, "f0"] = np.nan
    report = validate_pre_split_frame(frame)
    row = report.loc[report["audit_id"] == "ED-01-f0"].iloc[0]
    assert row["observed"] == 1
    assert row["evidence_status"] == "INFO"
    assert pd.isna(frame.loc[0, "f0"])


def test_feature_infinity_is_rejected() -> None:
    frame = _frame()
    frame.loc[0, "f0"] = np.inf
    with pytest.raises(AuditContractError, match="infinities"):
        validate_pre_split_frame(frame)


@pytest.mark.parametrize("mutation", ["duplicate", "null"])
def test_invalid_source_row_identity_fails_closed(mutation: str) -> None:
    frame = _frame()
    if mutation == "duplicate":
        frame.loc[1, "_source_row_id"] = frame.loc[0, "_source_row_id"]
    else:
        frame["_source_row_id"] = frame["_source_row_id"].astype("Int64")
        frame.loc[0, "_source_row_id"] = pd.NA
    with pytest.raises(AuditContractError, match="_source_row_id"):
        validate_pre_split_frame(frame)


def test_complete_pre_split_population_requires_canonical_source_order() -> None:
    frame = _frame().sample(frac=1.0, random_state=42).reset_index(drop=True)
    with pytest.raises(AuditContractError, match="canonical order"):
        validate_pre_split_frame(frame, require_zero_based_complete=True)


def test_forbidden_or_undeclared_feature_input_is_rejected() -> None:
    frame = _frame()
    frame["invented_feature"] = 1.0
    with pytest.raises(AuditContractError, match="Undeclared"):
        validate_pre_split_frame(frame)


def test_forbidden_treatment_cannot_enter_model_features() -> None:
    with pytest.raises(Exception, match="exactly"):
        assert_model_feature_contract((*FEATURE_COLUMNS, "treatment"))


def test_duplicate_definitions_are_exact_and_do_not_remove_rows() -> None:
    frame = _frame(rows=4)
    duplicate = frame.iloc[[0]].copy()
    duplicate["_source_row_id"] = 4
    duplicate["conversion"] = 1 - duplicate["conversion"]
    combined = pd.concat([frame, duplicate], ignore_index=True)
    report = duplicate_audit(combined).set_index("definition_id")

    assert report.loc["DP-01", "rows_beyond_first"] == 0
    assert report.loc["DP-03", "rows_beyond_first"] == 1
    assert report.loc["DP-04", "rows_beyond_first"] == 1
    assert report.loc["DP-05", "rows_beyond_first"] == 0
    assert report.loc["DP-02", "rows_beyond_first"] == 0
    assert not report["row_removal_authorized"].any()


def test_cross_split_profile_overlap_detects_shared_profile_across_splits() -> None:
    frame = _frame(rows=4)
    duplicate = frame.iloc[[0]].copy()
    duplicate["_source_row_id"] = 4
    combined = pd.concat([frame, duplicate], ignore_index=True)
    membership = pd.DataFrame({
        "_source_row_id": [0, 1, 2, 3, 4],
        "split": ["train", "train", "validation", "validation", "validation"],
    })

    from src.audit import FEATURE_COLUMNS as FC

    result = cross_split_profile_overlap(
        combined, membership, definition_id="DP-03", columns=FC,
    )
    assert result["definition_id"] == "DP-06-DP-03"
    assert result["overlapping_profile_count"] == 1
    assert result["rows_in_overlapping_profiles"] == 2
    assert result["row_removal_authorized"] is False


def test_cross_split_profile_overlap_ignores_held_out_membership() -> None:
    frame = _frame(rows=4)
    duplicate = frame.iloc[[0]].copy()
    duplicate["_source_row_id"] = 4
    combined = pd.concat([frame, duplicate], ignore_index=True)
    # Row 4 (a copy of row 0's profile) sits in held_out; comparing train vs validation only
    # must not see it, since held-out membership is never inspected by this function.
    membership = pd.DataFrame({
        "_source_row_id": [0, 1, 2, 3, 4],
        "split": ["train", "train", "validation", "validation", "held_out"],
    })

    from src.audit import FEATURE_COLUMNS as FC

    result = cross_split_profile_overlap(
        combined, membership, definition_id="DP-03", columns=FC,
    )
    assert result["overlapping_profile_count"] == 0
    assert result["rows_compared"] == 4


def test_cross_split_profile_overlap_zero_when_profiles_do_not_repeat() -> None:
    frame = _frame(rows=4)
    membership = pd.DataFrame({
        "_source_row_id": [0, 1, 2, 3],
        "split": ["train", "train", "validation", "validation"],
    })

    from src.audit import FEATURE_COLUMNS as FC

    result = cross_split_profile_overlap(
        frame, membership, definition_id="DP-03", columns=FC,
    )
    assert result["overlapping_profile_count"] == 0
    assert result["rows_in_overlapping_profiles"] == 0


def test_dp07_detects_float32_only_collision() -> None:
    source = _frame(rows=2)
    source.loc[:, FEATURE_COLUMNS] = 1.0
    source.loc[0, "f0"] = 1.00000001
    source.loc[1, "f0"] = 1.00000002
    processed = source.copy()

    evidence = precision_reconciliation(source, processed)

    assert evidence["source_processed_semantic_equal"] is True
    assert evidence["source_float64"]["rows_beyond_first"] == 0
    assert evidence["float32_sensitivity"]["rows_beyond_first"] == 1
    assert evidence["float32_additional_rows_beyond_first"] == 1
    assert evidence["primary_precision"] == "float64"


def test_conditional_permutation_preserves_global_and_block_counts() -> None:
    frame = _frame(rows=24)
    frame["block"] = np.repeat(["a", "b", "c"], 8)
    mapping, evidence = conditional_permute_treatment(
        frame,
        replication_index=3,
        block_columns=["block"],
    )

    merged = frame[["_source_row_id", "block", "treatment"]].merge(mapping)
    expected_blocks = pd.Index(["a", "b", "c"], name="block")
    pd.testing.assert_index_equal(
        pd.Index(sorted(merged["block"].unique()), name="block"),
        expected_blocks,
        exact=True,
    )
    assert len(merged) == len(frame) == len(mapping)
    assert merged["_source_row_id"].nunique() == len(frame)
    assert set(merged["treatment"].unique()) == {0, 1}
    assert set(merged["T_perm"].unique()) == {0, 1}

    expected_index = pd.MultiIndex.from_product(
        [expected_blocks, [0, 1]], names=["block", "treatment"]
    )
    original = (
        merged.groupby(["block", "treatment"], observed=True)
        .size()
        .reindex(expected_index, fill_value=0)
    )
    permuted = merged.groupby(["block", "T_perm"], observed=True).size()
    permuted.index = permuted.index.set_names(["block", "treatment"])
    permuted = permuted.reindex(expected_index, fill_value=0)

    def semantic_index_tuples(index: pd.MultiIndex) -> list[tuple[object, ...]]:
        return [
            tuple(value.item() if hasattr(value, "item") else value for value in item)
            for item in index.tolist()
        ]

    expected_index_tuples = semantic_index_tuples(expected_index)
    assert semantic_index_tuples(original.index) == expected_index_tuples
    assert semantic_index_tuples(permuted.index) == expected_index_tuples
    np.testing.assert_array_equal(
        original.to_numpy(dtype=np.int64),
        permuted.to_numpy(dtype=np.int64),
    )
    assert mapping["T_perm"].sum() == frame["treatment"].sum()
    assert evidence["method"] == "CONDITIONAL_PERMUTATION_APPROXIMATION"


def test_same_seed_config_and_input_reproduce_assignment_hash() -> None:
    frame = _frame(rows=30)
    first, first_evidence = conditional_permute_treatment(frame, replication_index=8)
    second, second_evidence = conditional_permute_treatment(frame, replication_index=8)
    pd.testing.assert_frame_equal(first, second)
    assert first_evidence["assignment_sha256"] == second_evidence["assignment_sha256"]


def test_distinct_replication_indices_have_distinct_stream_identities() -> None:
    _, first = replication_seed_metadata(0)
    _, second = replication_seed_metadata(1)
    assert first["stream_identity_sha256"] != second["stream_identity_sha256"]
    assert first["state_hex"] != second["state_hex"]


def test_valid_chance_permutation_collision_is_not_an_error() -> None:
    frame = _frame(rows=4)
    frame["block"] = ["a", "a", "b", "b"]
    frame["treatment"] = [0, 0, 1, 1]
    first, first_evidence = conditional_permute_treatment(
        frame, replication_index=0, block_columns=["block"]
    )
    second, second_evidence = conditional_permute_treatment(
        frame, replication_index=1, block_columns=["block"]
    )
    assert first_evidence["stream_identity_sha256"] != second_evidence["stream_identity_sha256"]
    assert first_evidence["assignment_sha256"] == second_evidence["assignment_sha256"]
    pd.testing.assert_frame_equal(first, second)


def test_predeclared_indices_produce_at_least_two_assignments_on_nondegenerate_fixture() -> None:
    frame = _frame(rows=20)
    hashes = {
        conditional_permute_treatment(frame, replication_index=index)[1]["assignment_sha256"]
        for index in range(8)
    }
    assert len(hashes) >= 2


def test_input_row_order_does_not_change_permutation_mapping() -> None:
    frame = _frame(rows=30)
    shuffled = frame.sample(frac=1.0, random_state=123).reset_index(drop=True)
    first, first_evidence = conditional_permute_treatment(frame, replication_index=5)
    second, second_evidence = conditional_permute_treatment(shuffled, replication_index=5)
    pd.testing.assert_frame_equal(first, second)
    assert first_evidence["assignment_sha256"] == second_evidence["assignment_sha256"]


def test_block_input_order_does_not_change_permutation_mapping() -> None:
    frame = _frame(rows=24)
    frame["block"] = np.repeat([2, 10, 3], 8)
    reordered = pd.concat(
        [frame.loc[frame["block"] == key] for key in [10, 3, 2]], ignore_index=True
    )
    first, first_evidence = conditional_permute_treatment(
        frame, replication_index=6, block_columns=["block"]
    )
    second, second_evidence = conditional_permute_treatment(
        reordered, replication_index=6, block_columns=["block"]
    )
    pd.testing.assert_frame_equal(first, second)
    assert first_evidence["assignment_sha256"] == second_evidence["assignment_sha256"]


def test_canonical_block_membership_hash_ignores_input_order() -> None:
    frame = _frame(rows=20)
    frame["block"] = np.repeat(["b", "a"], 10)
    shuffled = frame.sample(frac=1.0, random_state=9)
    assert canonical_block_membership_hash(frame, block_columns=["block"])[0] == canonical_block_membership_hash(shuffled, block_columns=["block"])[0]


def test_fold_mapping_is_stable_after_input_reordering() -> None:
    frame = _frame(rows=40)
    shuffled = frame.sample(frac=1.0, random_state=12)
    first, first_evidence = build_treatment_stratified_folds(frame)
    second, second_evidence = build_treatment_stratified_folds(shuffled)
    pd.testing.assert_frame_equal(first, second)
    assert first_evidence["fold_assignment_sha256"] == second_evidence["fold_assignment_sha256"]


class _FixtureClassifier:
    created = 0

    def __init__(self) -> None:
        type(self).created += 1
        self.classes_ = np.array([0, 1])
        self.prevalence = 0.5

    def fit(self, x: pd.DataFrame, y: np.ndarray) -> "_FixtureClassifier":
        self.prevalence = float(np.mean(y))
        return self

    def predict_proba(self, x: pd.DataFrame) -> np.ndarray:
        p = np.full(len(x), self.prevalence)
        return np.column_stack([1.0 - p, p])


def test_oof_isolation_and_fresh_classifier_per_fold_and_replication() -> None:
    frame = _frame(rows=40)
    _FixtureClassifier.created = 0
    first = cross_fitted_treatment_predictability(frame, model_factory=_FixtureClassifier)
    second = cross_fitted_treatment_predictability(frame, model_factory=_FixtureClassifier)
    assert _FixtureClassifier.created == 10
    assert all(row["identity_overlap_n"] == 0 for row in first["fold_records"])
    assert all(row["fresh_classifier"] for row in second["fold_records"])
    assert len(first["oof_probability"]) == len(frame)


def test_folds_are_rebuilt_from_current_assignment_not_stale_labels() -> None:
    frame = _frame(rows=40)
    first = cross_fitted_treatment_predictability(frame, model_factory=_FixtureClassifier)
    changed = frame.copy()
    changed["treatment"] = np.repeat([0, 1], 20)
    second = cross_fitted_treatment_predictability(changed, model_factory=_FixtureClassifier)
    assert first["fold_evidence"]["fold_assignment_sha256"] != second["fold_evidence"]["fold_assignment_sha256"]


def test_treatment_metric_formulas_reconcile() -> None:
    frame = _frame(rows=40)
    result = cross_fitted_treatment_predictability(frame, model_factory=_FixtureClassifier)
    expected_model = log_loss(frame.sort_values("_source_row_id")["treatment"], result["oof_probability"], labels=[0, 1])
    expected_constant = log_loss(frame.sort_values("_source_row_id")["treatment"], result["constant_probability"], labels=[0, 1])
    assert result["roc_auc"] == pytest.approx(0.5)
    assert result["log_loss"] == pytest.approx(expected_model)
    assert result["constant_prevalence_log_loss"] == pytest.approx(expected_constant)
    assert result["log_loss_gain"] == pytest.approx(expected_constant - expected_model)


def _smd_frame() -> pd.DataFrame:
    frame = _frame(rows=8)
    frame["treatment"] = [0, 0, 0, 0, 1, 1, 1, 1]
    for feature in FEATURE_COLUMNS:
        frame[feature] = 1.0
    frame["f0"] = [0.0, 1.0, 2.0, 3.0, 2.0, 3.0, 4.0, 5.0]
    return frame


def test_smd_uses_treated_minus_control_and_ddof_one() -> None:
    record = smd_feature_record(_smd_frame(), "f0")
    expected_variance = np.var([0.0, 1.0, 2.0, 3.0], ddof=1)
    expected = (3.5 - 1.5) / np.sqrt((expected_variance + expected_variance) / 2)
    assert record["ddof"] == 1
    assert record["smd_signed"] == pytest.approx(expected)
    assert record["smd_absolute"] == pytest.approx(abs(expected))


def test_max_absolute_smd_excludes_only_global_constants() -> None:
    records, summary = balance_diagnostics(_smd_frame())
    assert summary["max_feature"] == "f0"
    assert set(summary["excluded_global_constants"]) == set(FEATURE_COLUMNS) - {"f0"}
    assert records.loc[records["feature"] == "f0", "eligible_for_max_abs_smd"].item()


def test_zero_variance_with_different_arm_means_is_invalid() -> None:
    frame = _smd_frame()
    frame.loc[frame["treatment"] == 0, "f1"] = 0.0
    frame.loc[frame["treatment"] == 1, "f1"] = 1.0
    record = smd_feature_record(frame, "f1")
    assert record["statistic_status"] == "UNDEFINED_ZERO_POOLED_SD"
    assert record["calibration_valid"] is False


def test_insufficient_nonmissing_support_is_invalid() -> None:
    frame = _smd_frame()
    frame.loc[frame["treatment"] == 1, "f1"] = np.nan
    frame.loc[frame.index[-1], "f1"] = 1.0
    record = smd_feature_record(frame, "f1")
    assert record["statistic_status"] == "UNDEFINED_INSUFFICIENT_NONMISSING_SUPPORT"
    assert record["smd_signed"] is None


def test_inverse_ecdf_percentile_ranks_and_no_interpolation() -> None:
    values = np.arange(1, 2001, dtype=float)
    assert empirical_order_statistic(values, 0.95)["order_statistic_rank_one_based"] == 1900
    assert empirical_order_statistic(values, 0.99)["order_statistic_rank_one_based"] == 1980
    assert empirical_order_statistic(values, 0.95)["threshold"] == 1900


def test_threshold_equality_remains_in_lower_action_band() -> None:
    assert diagnostic_action(0.95, 0.95, 0.99) == {
        "evidence_status": "INFO",
        "required_action": "PASS",
    }
    assert diagnostic_action(0.99, 0.95, 0.99) == {
        "evidence_status": "WARNING",
        "required_action": "WARNING",
    }


def test_exact_binomial_monte_carlo_interval_is_ordered() -> None:
    ranks = binomial_order_statistic_interval_ranks(2000, 0.99)
    interval = monte_carlo_order_statistic_interval(np.arange(2000, dtype=float), 0.99)
    assert 1 <= ranks["lower_rank_one_based"] <= ranks["upper_rank_one_based"] <= 2000
    assert interval["lower_value"] <= interval["upper_value"]
    assert interval["method"] == "exact_binomial_order_statistic_numeric"


def test_monte_carlo_action_instability_requests_exact_continuation_increment() -> None:
    stability = monte_carlo_action_stability(
        0.96,
        p95_point=0.95,
        p99_point=0.99,
        p95_interval={"lower_value": 0.94, "upper_value": 0.97},
        p99_interval={"lower_value": 0.98, "upper_value": 1.00},
        current_replications=2000,
    )
    assert stability["stable"] is False
    assert stability["action_changed_across_interval_endpoints"] is True
    assert stability["next_replication_target"] == 4000


def test_continuation_is_append_only_and_deterministic() -> None:
    assert list(continuation_indices(2000, 4000)) == list(range(2000, 4000))
    first = replication_seed_metadata(2000)[1]["stream_identity_sha256"]
    repeated = replication_seed_metadata(2000)[1]["stream_identity_sha256"]
    assert first == repeated


def test_empirical_tail_fraction_is_not_labeled_a_p_value() -> None:
    summary = empirical_tail_fraction([0.1, 0.2, 0.3], 0.2)
    assert summary["empirical_tail_fraction"] == pytest.approx(2 / 3)
    assert summary["terminology"] == "CALIBRATION_SUMMARY_NOT_PERMUTATION_P_VALUE"
    assert "p_value" not in summary


def test_deferred_evidence_has_null_status_and_action() -> None:
    record = deferred_evidence_record("ED-03")
    assert record["execution_state"] == "DEFERRED_T03_C"
    assert record["evidence_status"] is None
    assert record["required_action"] is None
    validate_evidence_record({"evidence_class": "EMPIRICAL_DIAGNOSTIC", **record})


def test_held_out_dp06_is_sealed_and_null() -> None:
    record = deferred_evidence_record("DP-06", held_out_sealed=True)
    assert record["execution_state"] == "SEALED_DEFERRED_BY_TEST_ISOLATION"
    assert record["evidence_status"] is None and record["required_action"] is None


def test_regenerated_mapping_hash_mismatch_fails_closed() -> None:
    ids = np.arange(4, dtype=np.int64)
    values = np.array([0, 1, 0, 1], dtype=np.int8)
    expected = hash_row_mapping(ids, values, value_name="T_perm", value_dtype="i1")
    verify_regenerated_mapping_hash(expected, ids, values, value_name="T_perm", value_dtype="i1")
    with pytest.raises(AuditContractError, match="hash mismatch"):
        verify_regenerated_mapping_hash("0" * 64, ids, values, value_name="T_perm", value_dtype="i1")


def test_production_schema_forbids_full_mapping_persistence() -> None:
    schema = calibration_artifact_schema()
    assert schema["production_full_mapping_persistence"] is False
    assert schema["regeneration_required"] is True
    assert "source_row_to_T_perm_sha256" in schema["per_replication"]
    assert "source_row_to_fold_id_sha256" in schema["per_replication"]


def test_full_mapping_writer_rejects_production_mode(tmp_path: Path) -> None:
    with pytest.raises(AuditContractError, match="forbidden"):
        write_fixture_mapping_new(
            tmp_path / "run",
            "audit/debug/full_mapping.parquet",
            b"fixture",
            execution_mode="FINAL_CALIBRATION",
        )


def test_t03_governed_writers_reject_late_json_csv_and_overwrite(tmp_path: Path) -> None:
    run_root = tmp_path / "run"
    first = write_t03_json_new(run_root, "audit/run_config.json", {"task": "T03-A"})
    with pytest.raises(FileExistsError):
        write_t03_json_new(run_root, "audit/run_config.json", {"task": "changed"})
    assert json.loads(first.read_text())["task"] == "T03-A"

    (run_root / "audit" / "artifact_manifest.json").write_text(
        json.dumps({"status": "COMPLETED_PASS"}), encoding="utf-8"
    )
    # Completed-run immutability is a shared data-layer invariant (src/data.py, used by both
    # T01 and T03), so it raises the base DataContractError, not the AuditContractError subclass.
    with pytest.raises(DataContractError, match="immutable"):
        write_t03_json_new(run_root, "audit/t03a_summary.json", {"late": True})
    with pytest.raises(DataContractError, match="immutable"):
        write_t03_csv_new(
            run_root,
            "audit/pre_split_integrity.csv",
            pd.DataFrame({"late": [True]}),
        )


def test_undeclared_t03_artifact_path_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(AuditContractError, match="Undeclared"):
        write_t03_json_new(tmp_path / "run", "audit/unlisted.json", {})


def test_permutation_p_value_terminology_is_rejected() -> None:
    with pytest.raises(AuditContractError, match="must not be called"):
        validate_no_permutation_p_value_language({"label": "permutation p-value"})


def test_frozen_algorithm_contract_contains_no_results() -> None:
    contract = algorithm_contract()
    assert contract["execution_state"] == "DEFERRED_T03_C"
    assert contract["initial_replications"] == 2000
    assert contract["classifier"] == LIGHTGBM_TREATMENT_CONFIG
    assert contract["ordering_contract_version"] == ORDERING_CONTRACT_VERSION
    assert "threshold_values" not in contract
