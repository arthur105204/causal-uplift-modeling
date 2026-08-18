"""Reusable, regression-sensitive mechanics for the governed T03 audit.

The T03 notebook remains the primary research narrative.  This module contains
the exact operations whose reuse or edge cases materially affect correctness:
pre-split integrity checks, duplicate definitions, deterministic conditional
permutation and folds, balance/predictability statistics, Monte Carlo order
statistics, compact mapping hashes, and governed artifact schemas.

Nothing in this module authorizes a production audit, an outer split, held-out
access, or final T03-B calibration.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
import platform
import sys
from collections.abc import Callable, Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.model_selection import StratifiedKFold

from src.data import (
    AUDIT_ONLY_COLUMN,
    FEATURE_COLUMNS,
    FORBIDDEN_MODEL_COLUMNS,
    PRIMARY_OUTCOME,
    SECONDARY_OUTCOME,
    SOURCE_ROW_ID,
    TREATMENT_COLUMN,
    DataContractError,
    assert_model_feature_contract,
    write_bytes_new,
    write_json_new,
    write_text_new,
)


ORDERING_CONTRACT_VERSION = "t03-canonical-source-row-v1"
SEED_DERIVATION_VERSION = "numpy-seedsequence-pcg64-spawn-key-v1"
EVIDENCE_SCHEMA_VERSION = "t03-evidence-v1"
MASTER_PERMUTATION_SEED = 42
FOLD_SEED = 42
N_FOLDS = 5
INITIAL_NULL_REPLICATIONS = 2_000
CONTINUATION_INCREMENT = 2_000
QUANTILES = (0.01, 0.05, 0.25, 0.50, 0.75, 0.95, 0.99)

LIGHTGBM_TREATMENT_CONFIG: dict[str, Any] = {
    "boosting_type": "gbdt",
    "objective": "binary",
    "n_estimators": 100,
    "learning_rate": 0.1,
    "num_leaves": 31,
    "max_depth": -1,
    "min_child_samples": 20,
    "min_child_weight": 1e-3,
    "min_split_gain": 0.0,
    "subsample_for_bin": 200_000,
    "subsample": 1.0,
    "subsample_freq": 0,
    "colsample_bytree": 1.0,
    "reg_alpha": 0.0,
    "reg_lambda": 0.0,
    "class_weight": None,
    "is_unbalance": False,
    "scale_pos_weight": 1.0,
    "max_bin": 255,
    "use_missing": True,
    "zero_as_missing": False,
    "random_state": 42,
    "data_random_seed": 42,
    "deterministic": True,
    "force_col_wise": True,
    "device_type": "cpu",
    "n_jobs": 1,
    "verbosity": -1,
}

DUPLICATE_DEFINITIONS: dict[str, tuple[str, ...]] = {
    "DP-03": FEATURE_COLUMNS,
    "DP-04": FEATURE_COLUMNS + (TREATMENT_COLUMN,),
    "DP-05": FEATURE_COLUMNS + (TREATMENT_COLUMN, PRIMARY_OUTCOME),
}

T03A_ARTIFACT_KINDS: dict[str, str] = {
    "audit/environment.json": "json",
    "audit/run_config.json": "json",
    "audit/data_manifest.json": "json",
    "audit/predecessor_reconciliation.json": "json",
    "audit/pre_split_integrity.csv": "csv",
    "audit/audit_summary.csv": "csv",
    "audit/causal_audit.json": "json",
    "audit/duplicate_audit.csv": "csv",
    "audit/duplicate_rates.csv": "csv",
    "audit/duplicate_origin/duplicate_origin_summary.csv": "csv",
    "audit/duplicate_origin/duplicate_origin_report.json": "json",
    "audit/assumption_evidence.csv": "csv",
    "audit/balance_diagnostics.csv": "csv",
    "audit/randomization_calibration/algorithm_contract.json": "json",
    "audit/randomization_calibration/artifact_schema.json": "json",
    "audit/randomization_calibration/algorithm_verification.json": "json",
    "audit/randomization_calibration/resource_smoke.json": "json",
    "tables/t03a_interpretation.csv": "csv",
    "audit/t03a_summary.json": "json",
}

EXECUTION_MODES = {
    "UNIT_FIXTURE",
    "SMOKE_ONLY",
    "NON_FINAL_RESOURCE_EVIDENCE",
    "FINAL_CALIBRATION",
}
EVIDENCE_CLASSES = {
    "HARD_GATE",
    "EMPIRICAL_DIAGNOSTIC",
    "ASSUMPTION_SUPPORT_OR_LIMITATION",
}
EVIDENCE_STATUSES = {
    "HARD_GATE": {"PASS", "FAIL"},
    "EMPIRICAL_DIAGNOSTIC": {"INFO", "WARNING", "MATERIAL_CONCERN"},
    "ASSUMPTION_SUPPORT_OR_LIMITATION": {"SUPPORTED", "UNSUPPORTED", "LIMITED"},
}
REQUIRED_ACTIONS = {
    "PASS",
    "WARNING",
    "ROBUSTNESS_REQUIRED",
    "STOP",
    "LIMITATION",
    "UNSUPPORTED_METRIC",
}


class AuditContractError(DataContractError):
    """Raised when an accepted T03 audit convention is violated."""


def canonical_json_sha256(payload: Any) -> str:
    """Hash a JSON-compatible payload with deterministic encoding."""

    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _record(
    audit_id: str,
    evidence_class: str,
    condition: str,
    passed: bool,
    observed: Any,
    *,
    failure_action: str = "STOP",
) -> dict[str, Any]:
    return {
        "audit_id": audit_id,
        "evidence_class": evidence_class,
        "condition": condition,
        "observed": observed,
        "evidence_status": "PASS" if passed else "FAIL",
        "required_action": "PASS" if passed else failure_action,
        "execution_state": "EXECUTED",
        "passed": bool(passed),
    }


def assert_binary_complete(series: pd.Series, name: str) -> None:
    """Require a complete, unremapped binary field."""

    if series.isna().any():
        raise AuditContractError(f"{name} contains missing values")
    values = set(series.unique().tolist())
    if not values.issubset({0, 1}):
        raise AuditContractError(f"{name} contains values outside {{0,1}}: {values}")


def assert_source_row_identity(
    frame: pd.DataFrame,
    *,
    require_zero_based_complete: bool = False,
) -> None:
    """Validate released-row identity without treating it as person identity."""

    if SOURCE_ROW_ID not in frame.columns:
        raise AuditContractError(f"Missing required identity column {SOURCE_ROW_ID}")
    ids = frame[SOURCE_ROW_ID]
    if ids.isna().any():
        raise AuditContractError(f"{SOURCE_ROW_ID} contains null values")
    if not pd.api.types.is_integer_dtype(ids.dtype):
        raise AuditContractError(f"{SOURCE_ROW_ID} must use an integer dtype")
    if ids.duplicated().any():
        raise AuditContractError(f"{SOURCE_ROW_ID} contains duplicate released-row ordinals")
    ordered = ids.to_numpy(dtype=np.int64, copy=False)
    if require_zero_based_complete and not np.array_equal(
        ordered, np.arange(len(frame), dtype=np.int64)
    ):
        raise AuditContractError(
            f"{SOURCE_ROW_ID} does not reconcile to the complete zero-based canonical order"
        )


def validate_pre_split_frame(
    frame: pd.DataFrame,
    *,
    require_zero_based_complete: bool = False,
) -> pd.DataFrame:
    """Return machine-readable T03-A hard-gate and diagnostic records.

    The function never removes or modifies a row. Missing features are reported;
    infinite feature values and invalid labels fail closed.
    """

    required = set(FEATURE_COLUMNS) | {
        TREATMENT_COLUMN,
        PRIMARY_OUTCOME,
        SOURCE_ROW_ID,
    }
    allowed = required | {SECONDARY_OUTCOME, AUDIT_ONLY_COLUMN}
    missing = sorted(required.difference(frame.columns))
    undeclared = sorted(set(frame.columns).difference(allowed))
    if missing:
        raise AuditContractError(f"Missing required columns: {missing}")
    if undeclared:
        raise AuditContractError(f"Undeclared columns are not allowed: {undeclared}")
    if frame.empty:
        raise AuditContractError("The pre-split population is empty")

    assert_model_feature_contract(FEATURE_COLUMNS)
    assert_binary_complete(frame[TREATMENT_COLUMN], TREATMENT_COLUMN)
    assert_binary_complete(frame[PRIMARY_OUTCOME], PRIMARY_OUTCOME)
    if SECONDARY_OUTCOME in frame:
        assert_binary_complete(frame[SECONDARY_OUTCOME], SECONDARY_OUTCOME)
    assert_source_row_identity(
        frame,
        require_zero_based_complete=require_zero_based_complete,
    )

    records = [
        _record("HG-02", "HARD_GATE", "required schema and non-empty population", True, len(frame)),
        _record("HG-03", "HARD_GATE", "X/T/Y roles and forbidden-X guard", True, list(FEATURE_COLUMNS)),
        _record("HG-04", "HARD_GATE", "complete binary treatment and conversion", True, "{0,1}"),
        _record("HG-07", "HARD_GATE", "non-null unique released-row identity", True, len(frame)),
    ]
    for feature in FEATURE_COLUMNS:
        if not pd.api.types.is_numeric_dtype(frame[feature].dtype):
            raise AuditContractError(f"Feature {feature} is not numeric")

    # T03-A.5: one vectorized multi-column pass over all twelve features, not one pass per feature.
    feature_values = frame.loc[:, list(FEATURE_COLUMNS)].to_numpy(dtype=np.float64, na_value=np.nan)
    missing_counts = np.isnan(feature_values).sum(axis=0)
    infinite_counts = np.isinf(feature_values).sum(axis=0)
    total_infinities = int(infinite_counts.sum())
    if total_infinities:
        offending = {
            feature: int(count)
            for feature, count in zip(FEATURE_COLUMNS, infinite_counts)
            if count
        }
        raise AuditContractError(f"Features contain {total_infinities} infinities: {offending}")

    for feature, missing_count in zip(FEATURE_COLUMNS, missing_counts):
        records.append(
            {
                "audit_id": f"ED-01-{feature}",
                "evidence_class": "EMPIRICAL_DIAGNOSTIC",
                "condition": "missingness characterization only",
                "observed": int(missing_count),
                "evidence_status": "INFO",
                "required_action": "PASS",
                "execution_state": "EXECUTED",
                "passed": True,
            }
        )

    records.append(
        _record(
            "HG-05",
            "HARD_GATE",
            "numeric features contain no positive or negative infinity",
            True,
            {"features": list(FEATURE_COLUMNS), "infinity_count": 0},
        )
    )

    arm_counts = frame[TREATMENT_COLUMN].value_counts().reindex([0, 1], fill_value=0)
    if bool((arm_counts == 0).any()):
        raise AuditContractError(f"Global treatment-arm support failed: {arm_counts.to_dict()}")
    records.append(
        _record(
            "HG-06",
            "HARD_GATE",
            "both assignment arms have global support",
            True,
            {str(k): int(v) for k, v in arm_counts.items()},
        )
    )
    return pd.DataFrame(records)


def duplicate_profile_summary(
    frame: pd.DataFrame,
    *,
    definition_id: str,
    columns: Sequence[str],
    row_universe: str,
    precision: str,
) -> dict[str, Any]:
    """Summarize exact value repetition under one explicit definition."""

    selected = tuple(columns)
    missing = sorted(set(selected).difference(frame.columns))
    if missing:
        raise AuditContractError(f"{definition_id} is missing columns: {missing}")
    grouped = frame.groupby(list(selected), dropna=False, sort=False).size()
    repeated = grouped[grouped > 1]
    return {
        "definition_id": definition_id,
        "columns": list(selected),
        "row_universe": row_universe,
        "precision": precision,
        "rows_total": int(len(frame)),
        "rows_in_duplicate_groups": int(repeated.sum()),
        "rows_beyond_first": int((repeated - 1).sum()),
        "duplicate_group_count": int(repeated.size),
        "largest_group": int(repeated.max()) if not repeated.empty else 1,
        "interpretation": "equal released-row values are not evidence of duplicate people",
        "row_removal_authorized": False,
    }


def duplicate_audit(
    frame: pd.DataFrame,
    *,
    row_universe: str = "unsplit_validated_released_rows",
    precision: str = "float64_primary",
) -> pd.DataFrame:
    """Apply pre-split DP-01 through DP-05 without deduplication."""

    assert_source_row_identity(frame)
    optional = tuple(
        name for name in (SECONDARY_OUTCOME, AUDIT_ONLY_COLUMN) if name in frame.columns
    )
    definitions = {
        "DP-01": (SOURCE_ROW_ID,),
        "DP-02": FEATURE_COLUMNS
        + (TREATMENT_COLUMN, PRIMARY_OUTCOME)
        + optional,
        **DUPLICATE_DEFINITIONS,
    }
    rows = [
        duplicate_profile_summary(
            frame,
            definition_id=definition,
            columns=columns,
            row_universe=row_universe,
            precision=precision,
        )
        for definition, columns in definitions.items()
    ]
    return pd.DataFrame(rows)


def cross_split_profile_overlap(
    frame: pd.DataFrame,
    split_membership: pd.DataFrame,
    *,
    definition_id: str,
    columns: Sequence[str],
    splits: Sequence[str] = ("train", "validation"),
) -> dict[str, Any]:
    """DP-06: report value profiles that appear in more than one of `splits`.

    Not row leakage by itself — distinct rows may share an anonymous feature
    profile. `split_membership` must be a (_source_row_id, split) mapping;
    only the requested splits are read, so held-out membership is never
    inspected by this function even if present in the mapping.
    """

    selected = tuple(columns)
    missing = sorted(set(selected).difference(frame.columns))
    if missing:
        raise AuditContractError(f"{definition_id} is missing columns: {missing}")
    labels = split_membership.loc[split_membership["split"].isin(splits), [SOURCE_ROW_ID, "split"]]
    working = frame.loc[:, [SOURCE_ROW_ID] + list(selected)].merge(labels, on=SOURCE_ROW_ID, how="inner")

    per_split_groups = working.groupby(list(selected) + ["split"], dropna=False, sort=False).size()
    per_split_groups = per_split_groups.reset_index(name="n")
    distinct_splits_per_profile = per_split_groups.groupby(list(selected), dropna=False)["split"].nunique()
    overlapping_profiles = distinct_splits_per_profile[distinct_splits_per_profile > 1]

    if overlapping_profiles.empty:
        rows_in_overlapping_profiles = 0
    else:
        profile_index = per_split_groups.set_index(list(selected)).index
        is_overlapping = profile_index.isin(overlapping_profiles.index)
        rows_in_overlapping_profiles = int(per_split_groups.loc[is_overlapping, "n"].sum())

    return {
        "definition_id": f"DP-06-{definition_id}",
        "columns": list(selected),
        "splits_compared": list(splits),
        "rows_compared": int(len(working)),
        "overlapping_profile_count": int(len(overlapping_profiles)),
        "rows_in_overlapping_profiles": rows_in_overlapping_profiles,
        "interpretation": "cross-split value-profile repetition; not row leakage unless _source_row_id overlaps (DP-01)",
        "row_removal_authorized": False,
    }


def precision_reconciliation(
    source_frame: pd.DataFrame,
    processed_frame: pd.DataFrame,
) -> dict[str, Any]:
    """Compare source float64, explicit float32 projection, and Parquet values."""

    source = source_frame.copy()
    processed = processed_frame.copy()
    if SOURCE_ROW_ID not in source:
        source[SOURCE_ROW_ID] = np.arange(len(source), dtype=np.int64)
    assert_source_row_identity(source)
    assert_source_row_identity(processed)
    source = source.sort_values(SOURCE_ROW_ID, kind="mergesort").reset_index(drop=True)
    processed = processed.sort_values(SOURCE_ROW_ID, kind="mergesort").reset_index(drop=True)
    if not np.array_equal(source[SOURCE_ROW_ID], processed[SOURCE_ROW_ID]):
        raise AuditContractError("DP-07 source/processed row identities do not align")
    source64 = source.loc[:, list(FEATURE_COLUMNS)].astype("float64")
    processed64 = processed.loc[:, list(FEATURE_COLUMNS)].astype("float64")
    semantic_equal = bool(
        np.array_equal(
            source64.to_numpy(),
            processed64.to_numpy(),
            equal_nan=True,
        )
    )
    if not semantic_equal:
        raise AuditContractError("DP-07 processed float64 values differ from source precision")
    projected32 = source64.astype("float32")
    source_summary = duplicate_profile_summary(
        source64,
        definition_id="DP-07-source-float64",
        columns=FEATURE_COLUMNS,
        row_universe="aligned_source_rows",
        precision="source_float64",
    )
    projected_summary = duplicate_profile_summary(
        projected32,
        definition_id="DP-07-source-float32-sensitivity",
        columns=FEATURE_COLUMNS,
        row_universe="aligned_source_rows",
        precision="float32_sensitivity",
    )
    processed_summary = duplicate_profile_summary(
        processed64,
        definition_id="DP-07-processed-float64",
        columns=FEATURE_COLUMNS,
        row_universe="aligned_processed_rows",
        precision="processed_float64_primary",
    )
    return {
        "definition_id": "DP-07",
        "rows": int(len(source)),
        "source_processed_semantic_equal": semantic_equal,
        "source_float64": source_summary,
        "float32_sensitivity": projected_summary,
        "processed_float64": processed_summary,
        "float32_additional_rows_beyond_first": int(
            projected_summary["rows_beyond_first"] - source_summary["rows_beyond_first"]
        ),
        "primary_precision": "float64",
        "row_removal_authorized": False,
    }


def _block_column_kind(series: pd.Series, name: str) -> str:
    values = series.dropna()
    if values.empty:
        return "all_null"
    if pd.api.types.is_numeric_dtype(values.dtype) or all(
        isinstance(value, (bool, int, float, np.integer, np.floating))
        and not isinstance(value, complex)
        for value in values
    ):
        return "numeric"
    if all(isinstance(value, str) for value in values):
        return "string"
    raise AuditContractError(
        f"Block column {name} has incompatible or mixed key types"
    )


def canonicalize_population(
    frame: pd.DataFrame,
    *,
    block_columns: Sequence[str] = (),
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Return canonical block order and ascending released-row order per block."""

    assert_source_row_identity(frame)
    blocks = tuple(block_columns)
    missing = sorted(set(blocks).difference(frame.columns))
    if missing:
        raise AuditContractError(f"Missing configured block columns: {missing}")
    work = frame.copy()
    kinds: dict[str, str] = {}
    for column in blocks:
        kinds[column] = _block_column_kind(work[column], column)
        if isinstance(work[column].dtype, pd.CategoricalDtype):
            work[column] = work[column].astype(object)
    sort_columns = list(blocks) + [SOURCE_ROW_ID]
    work = work.sort_values(
        sort_columns,
        ascending=True,
        na_position="last",
        kind="mergesort",
    ).reset_index(drop=True)
    contract = {
        "ordering_contract_version": ORDERING_CONTRACT_VERSION,
        "row_order": f"ascending {SOURCE_ROW_ID} within canonical blocks",
        "block_columns": list(blocks),
        "block_column_kinds": kinds,
        "block_order": "declared-column lexicographic ascending; numeric numeric-order; string Unicode-order; nulls last",
        "categorical_order": "labels, never storage codes",
        "no_block_rule": "full population is one block",
    }
    contract["block_contract_config_sha256"] = canonical_json_sha256(contract)
    return work, contract


def replication_seed_metadata(
    replication_index: int,
    *,
    master_seed: int = MASTER_PERMUTATION_SEED,
) -> tuple[np.random.Generator, dict[str, Any]]:
    """Create the frozen deterministic PCG64 stream for one zero-based draw."""

    if not isinstance(replication_index, (int, np.integer)) or replication_index < 0:
        raise ValueError("replication_index must be a non-negative integer")
    sequence = np.random.SeedSequence(
        entropy=int(master_seed),
        spawn_key=(int(replication_index),),
        pool_size=4,
    )
    state = sequence.generate_state(4, dtype=np.uint32)
    metadata = {
        "master_seed": int(master_seed),
        "replication_index": int(replication_index),
        "spawn_key": [int(replication_index)],
        "pool_size": 4,
        "bit_generator": "PCG64",
        "numpy_version": np.__version__,
        "generate_state_uint32": [int(value) for value in state],
        "state_hex": "".join(f"{int(value):08x}" for value in state),
        "seed_derivation_algorithm_version": SEED_DERIVATION_VERSION,
    }
    metadata["stream_identity_sha256"] = canonical_json_sha256(metadata)
    return np.random.Generator(np.random.PCG64(sequence)), metadata


def _little_endian_array(values: Iterable[Any], dtype: str) -> np.ndarray:
    array = np.asarray(values, dtype=dtype)
    return np.ascontiguousarray(array)


def hash_row_mapping(
    source_row_ids: Iterable[Any],
    values: Iterable[Any],
    *,
    value_name: str,
    value_dtype: str,
) -> str:
    """Hash one canonical row mapping without persisting the row-level mapping."""

    ids = _little_endian_array(source_row_ids, "<i8")
    mapped = _little_endian_array(values, value_dtype)
    if len(ids) != len(mapped):
        raise AuditContractError("Mapping identity and value lengths differ")
    if len(ids) and not np.all(np.diff(ids) > 0):
        raise AuditContractError("Mapping hashes require ascending unique source-row IDs")
    digest = hashlib.sha256()
    digest.update(f"{ORDERING_CONTRACT_VERSION}|{SOURCE_ROW_ID}|{value_name}|{value_dtype}\n".encode())
    digest.update(ids.tobytes(order="C"))
    digest.update(mapped.tobytes(order="C"))
    return digest.hexdigest()


def canonical_population_identity_hash(frame: pd.DataFrame) -> str:
    ordered = frame.sort_values(SOURCE_ROW_ID, kind="mergesort")
    ids = ordered[SOURCE_ROW_ID].to_numpy(dtype=np.int64, copy=False)
    return hash_row_mapping(ids, np.zeros(len(ids), dtype=np.uint8), value_name="population_membership", value_dtype="u1")


def _hash_block_column(series: pd.Series, kind: str) -> str:
    digest = hashlib.sha256()
    missing = series.isna().to_numpy(dtype=np.uint8)
    digest.update(missing.tobytes(order="C"))
    if kind == "numeric":
        values = pd.to_numeric(series, errors="raise").fillna(0).to_numpy(dtype="<f8")
        digest.update(np.ascontiguousarray(values).tobytes(order="C"))
    else:
        for value in series:
            encoded = b"" if pd.isna(value) else str(value).encode("utf-8")
            digest.update(len(encoded).to_bytes(8, "little"))
            digest.update(encoded)
    return digest.hexdigest()


def canonical_block_membership_hash(
    frame: pd.DataFrame,
    *,
    block_columns: Sequence[str] = (),
) -> tuple[str, dict[str, Any]]:
    """Hash population/block membership in ascending released-row order."""

    canonical, contract = canonicalize_population(frame, block_columns=block_columns)
    ordered = canonical.sort_values(SOURCE_ROW_ID, kind="mergesort")
    payload = {
        "population_identity_sha256": canonical_population_identity_hash(ordered),
        "block_contract_config_sha256": contract["block_contract_config_sha256"],
        "block_columns": [],
    }
    for column in block_columns:
        payload["block_columns"].append(
            {
                "name": column,
                "kind": contract["block_column_kinds"][column],
                "sha256": _hash_block_column(
                    ordered[column], contract["block_column_kinds"][column]
                ),
            }
        )
    payload["block_membership_sha256"] = canonical_json_sha256(payload)
    return payload["block_membership_sha256"], payload


def conditional_permute_treatment(
    frame: pd.DataFrame,
    *,
    replication_index: int,
    block_columns: Sequence[str] = (),
    master_seed: int = MASTER_PERMUTATION_SEED,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Permute only T under the accepted conditional-permutation approximation."""

    assert_binary_complete(frame[TREATMENT_COLUMN], TREATMENT_COLUMN)
    canonical, contract = canonicalize_population(frame, block_columns=block_columns)
    rng, seed_metadata = replication_seed_metadata(
        replication_index,
        master_seed=master_seed,
    )
    permuted = np.empty(len(canonical), dtype=np.int8)
    block_counts: list[dict[str, Any]] = []
    if block_columns:
        grouped = canonical.groupby(list(block_columns), sort=False, dropna=False, observed=True)
        positions = grouped.indices.items()
    else:
        positions = [("__FULL_DEVELOPMENT_POPULATION__", np.arange(len(canonical)))]
    for block_key, raw_positions in positions:
        indices = np.asarray(raw_positions, dtype=np.int64)
        original = canonical.iloc[indices][TREATMENT_COLUMN].to_numpy(dtype=np.int8)
        assigned = rng.permutation(original)
        permuted[indices] = assigned
        original_counts = np.bincount(original, minlength=2)[:2]
        assigned_counts = np.bincount(assigned, minlength=2)[:2]
        if not np.array_equal(original_counts, assigned_counts):
            raise AuditContractError("Conditional permutation changed a block arm count")
        block_counts.append(
            {
                "block_key": repr(block_key),
                "n": int(len(indices)),
                "control_n": int(original_counts[0]),
                "treated_n": int(original_counts[1]),
            }
        )
    mapping = pd.DataFrame(
        {
            SOURCE_ROW_ID: canonical[SOURCE_ROW_ID].to_numpy(dtype=np.int64),
            "T_perm": permuted,
        }
    ).sort_values(SOURCE_ROW_ID, kind="mergesort").reset_index(drop=True)
    ids = mapping[SOURCE_ROW_ID].to_numpy(dtype=np.int64)
    mapping_hash = hash_row_mapping(
        ids,
        mapping["T_perm"].to_numpy(dtype=np.int8),
        value_name="T_perm",
        value_dtype="i1",
    )
    block_membership_hash, block_evidence = canonical_block_membership_hash(
        frame,
        block_columns=block_columns,
    )
    evidence = {
        "method": "CONDITIONAL_PERMUTATION_APPROXIMATION",
        "ordering_contract_version": ORDERING_CONTRACT_VERSION,
        "block_contract": contract,
        "block_membership_sha256": block_membership_hash,
        "block_membership_evidence": block_evidence,
        "seed": seed_metadata,
        "stream_identity_sha256": seed_metadata["stream_identity_sha256"],
        "assignment_sha256": mapping_hash,
        "global_control_n": int((mapping["T_perm"] == 0).sum()),
        "global_treated_n": int((mapping["T_perm"] == 1).sum()),
        "block_invariants": block_counts,
        "collision_policy": "valid chance collisions are retained without retry",
    }
    return mapping, evidence


def build_treatment_stratified_folds(
    frame: pd.DataFrame,
    *,
    treatment_column: str = TREATMENT_COLUMN,
    n_splits: int = N_FOLDS,
    seed: int = FOLD_SEED,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Build reproducible row-to-fold membership from canonical row order."""

    assert_binary_complete(frame[treatment_column], treatment_column)
    canonical = frame.sort_values(SOURCE_ROW_ID, kind="mergesort").reset_index(drop=True)
    assert_source_row_identity(canonical)
    counts = canonical[treatment_column].value_counts().reindex([0, 1], fill_value=0)
    if int(counts.min()) < n_splits:
        raise AuditContractError(
            f"Treatment-stratified {n_splits}-fold construction lacks arm support: {counts.to_dict()}"
        )
    splitter = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    fold_ids = np.full(len(canonical), -1, dtype=np.int16)
    placeholder = np.zeros((len(canonical), 1), dtype=np.uint8)
    for fold_id, (_, validation_index) in enumerate(
        splitter.split(placeholder, canonical[treatment_column].to_numpy())
    ):
        if np.any(fold_ids[validation_index] != -1):
            raise AuditContractError("A row was assigned to more than one fold")
        fold_ids[validation_index] = fold_id
    if np.any(fold_ids < 0):
        raise AuditContractError("At least one row has no out-of-fold assignment")
    mapping = pd.DataFrame(
        {
            SOURCE_ROW_ID: canonical[SOURCE_ROW_ID].to_numpy(dtype=np.int64),
            "fold_id": fold_ids,
        }
    )
    mapping_hash = hash_row_mapping(
        mapping[SOURCE_ROW_ID],
        mapping["fold_id"],
        value_name="fold_id",
        value_dtype="<i2",
    )
    evidence = {
        "n_splits": int(n_splits),
        "stratification": treatment_column,
        "fold_seed": int(seed),
        "ordering_contract_version": ORDERING_CONTRACT_VERSION,
        "fold_assignment_sha256": mapping_hash,
        "fold_counts": {
            str(fold): int(count)
            for fold, count in mapping["fold_id"].value_counts().sort_index().items()
        },
    }
    return mapping, evidence


def fixed_lightgbm_classifier() -> Any:
    """Construct one fresh classifier using the frozen diagnostic parameters."""

    try:
        from lightgbm import LGBMClassifier
    except ImportError as exc:  # pragma: no cover - environment failure path
        raise AuditContractError("LightGBM is required for the fixed X-to-T diagnostic") from exc
    return LGBMClassifier(**LIGHTGBM_TREATMENT_CONFIG)


def cross_fitted_treatment_predictability(
    frame: pd.DataFrame,
    *,
    treatment_column: str = TREATMENT_COLUMN,
    model_factory: Callable[[], Any] = fixed_lightgbm_classifier,
    n_splits: int = N_FOLDS,
    fold_seed: int = FOLD_SEED,
) -> dict[str, Any]:
    """Run the fixed OOF X-to-T diagnostic for one observed or null assignment."""

    assert_model_feature_contract(FEATURE_COLUMNS)
    canonical = frame.sort_values(SOURCE_ROW_ID, kind="mergesort").reset_index(drop=True)
    folds, fold_evidence = build_treatment_stratified_folds(
        canonical,
        treatment_column=treatment_column,
        n_splits=n_splits,
        seed=fold_seed,
    )
    if not np.array_equal(canonical[SOURCE_ROW_ID], folds[SOURCE_ROW_ID]):
        raise AuditContractError("Fold mapping does not align with canonical rows")
    x = canonical.loc[:, list(FEATURE_COLUMNS)]
    treatment = canonical[treatment_column].to_numpy(dtype=np.int8)
    oof_probability = np.full(len(canonical), np.nan, dtype=np.float64)
    constant_probability = np.full(len(canonical), np.nan, dtype=np.float64)
    fold_records: list[dict[str, Any]] = []
    for fold_id in range(n_splits):
        validation_mask = folds["fold_id"].to_numpy() == fold_id
        training_mask = ~validation_mask
        if not training_mask.any() or not validation_mask.any():
            raise AuditContractError(f"Fold {fold_id} has an empty train or validation side")
        training_ids = set(canonical.loc[training_mask, SOURCE_ROW_ID].tolist())
        validation_ids = set(canonical.loc[validation_mask, SOURCE_ROW_ID].tolist())
        if training_ids.intersection(validation_ids):
            raise AuditContractError(f"Fold {fold_id} violates OOF isolation")
        train_t = treatment[training_mask]
        validation_t = treatment[validation_mask]
        if set(np.unique(train_t).tolist()) != {0, 1}:
            raise AuditContractError(f"Fold {fold_id} training side lacks an assignment arm")
        model = model_factory()
        model.fit(x.loc[training_mask], train_t)
        probabilities = np.asarray(model.predict_proba(x.loc[validation_mask]))
        classes = np.asarray(model.classes_)
        class_one = np.flatnonzero(classes == 1)
        if len(class_one) != 1:
            raise AuditContractError("Classifier output does not contain exactly one T=1 class")
        prediction = probabilities[:, int(class_one[0])].astype(np.float64)
        if not np.isfinite(prediction).all() or np.any((prediction < 0) | (prediction > 1)):
            raise AuditContractError("X-to-T probability output is invalid")
        oof_probability[validation_mask] = prediction
        constant_probability[validation_mask] = float(train_t.mean())
        fold_records.append(
            {
                "fold_id": fold_id,
                "train_n": int(training_mask.sum()),
                "validation_n": int(validation_mask.sum()),
                "train_control_n": int((train_t == 0).sum()),
                "train_treated_n": int((train_t == 1).sum()),
                "validation_control_n": int((validation_t == 0).sum()),
                "validation_treated_n": int((validation_t == 1).sum()),
                "identity_overlap_n": 0,
                "fresh_classifier": True,
            }
        )
    if not np.isfinite(oof_probability).all() or not np.isfinite(constant_probability).all():
        raise AuditContractError("OOF predictions do not cover every canonical row")
    model_log_loss = float(log_loss(treatment, oof_probability, labels=[0, 1]))
    constant_log_loss = float(log_loss(treatment, constant_probability, labels=[0, 1]))
    return {
        "roc_auc": float(roc_auc_score(treatment, oof_probability)),
        "log_loss": model_log_loss,
        "constant_prevalence_log_loss": constant_log_loss,
        "log_loss_gain": constant_log_loss - model_log_loss,
        "fold_evidence": fold_evidence,
        "fold_records": fold_records,
        "oof_probability": oof_probability,
        "constant_probability": constant_probability,
        "feature_columns": list(FEATURE_COLUMNS),
        "classifier_config": dict(LIGHTGBM_TREATMENT_CONFIG),
    }


def _ks_distance(first: np.ndarray, second: np.ndarray) -> float | None:
    first = np.sort(first[np.isfinite(first)])
    second = np.sort(second[np.isfinite(second)])
    if not len(first) or not len(second):
        return None
    support = np.sort(np.concatenate([first, second]))
    first_cdf = np.searchsorted(first, support, side="right") / len(first)
    second_cdf = np.searchsorted(second, support, side="right") / len(second)
    return float(np.max(np.abs(first_cdf - second_cdf)))


def smd_feature_record(
    frame: pd.DataFrame,
    feature: str,
    *,
    treatment_column: str = TREATMENT_COLUMN,
) -> dict[str, Any]:
    """Compute the frozen treated-minus-control SMD and companion diagnostics."""

    assert_binary_complete(frame[treatment_column], treatment_column)
    control = frame.loc[frame[treatment_column] == 0, feature].dropna().to_numpy(dtype=np.float64)
    treated = frame.loc[frame[treatment_column] == 1, feature].dropna().to_numpy(dtype=np.float64)
    base = {
        "feature": feature,
        "control_nonmissing_n": int(len(control)),
        "treated_nonmissing_n": int(len(treated)),
        "control_missing_n": int((frame.loc[frame[treatment_column] == 0, feature].isna()).sum()),
        "treated_missing_n": int((frame.loc[frame[treatment_column] == 1, feature].isna()).sum()),
        "ddof": 1,
        "variance_weighting": "equal_arm",
        "sign": "treated_minus_control",
        "imputation": "none",
        "literature_reference_abs_smd": 0.10,
        "literature_reference_role": "LITERATURE_REFERENCE_NOT_GATE",
    }
    if len(control) < 2 or len(treated) < 2:
        return {
            **base,
            "statistic_status": "UNDEFINED_INSUFFICIENT_NONMISSING_SUPPORT",
            "calibration_valid": False,
            "smd_signed": None,
            "smd_absolute": None,
            "variance_ratio": None,
        }
    mean_control, mean_treated = float(control.mean()), float(treated.mean())
    variance_control = float(control.var(ddof=1))
    variance_treated = float(treated.var(ddof=1))
    pooled_sd = math.sqrt((variance_treated + variance_control) / 2.0)
    combined = np.concatenate([control, treated])
    globally_constant = bool(np.all(combined == combined[0]))
    if pooled_sd == 0:
        status = (
            "UNDEFINED_GLOBAL_CONSTANT"
            if globally_constant and mean_treated == mean_control
            else "UNDEFINED_ZERO_POOLED_SD"
        )
        return {
            **base,
            "control_mean": mean_control,
            "treated_mean": mean_treated,
            "control_variance": variance_control,
            "treated_variance": variance_treated,
            "pooled_within_arm_sd": pooled_sd,
            "statistic_status": status,
            "calibration_valid": status == "UNDEFINED_GLOBAL_CONSTANT",
            "eligible_for_max_abs_smd": False,
            "smd_signed": None,
            "smd_absolute": None,
            "variance_ratio": None,
        }
    signed = (mean_treated - mean_control) / pooled_sd
    ratio = None if variance_control == 0 else variance_treated / variance_control
    quantile_control = np.quantile(control, QUANTILES)
    quantile_treated = np.quantile(treated, QUANTILES)
    finite_values = [signed, pooled_sd, mean_control, mean_treated, variance_control, variance_treated]
    if ratio is not None:
        finite_values.append(ratio)
    if not np.isfinite(finite_values).all():
        status = "UNDEFINED_NONFINITE"
        calibration_valid = False
        eligible = False
        signed_value = absolute_value = None
    else:
        status = "DEFINED"
        calibration_valid = True
        eligible = True
        signed_value = float(signed)
        absolute_value = float(abs(signed))
    record = {
        **base,
        "control_mean": mean_control,
        "treated_mean": mean_treated,
        "control_variance": variance_control,
        "treated_variance": variance_treated,
        "pooled_within_arm_sd": pooled_sd,
        "statistic_status": status,
        "calibration_valid": calibration_valid,
        "eligible_for_max_abs_smd": eligible,
        "smd_signed": signed_value,
        "smd_absolute": absolute_value,
        "variance_ratio": None if ratio is None else float(ratio),
        "ks_ecdf_distance": _ks_distance(control, treated),
    }
    for probability, q0, q1 in zip(QUANTILES, quantile_control, quantile_treated):
        label = f"q{int(probability * 100):02d}"
        record[f"control_{label}"] = float(q0)
        record[f"treated_{label}"] = float(q1)
        record[f"treated_minus_control_{label}"] = float(q1 - q0)
    return record


def balance_diagnostics(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Compute all feature SMD records and the max-absolute eligible statistic."""

    records = pd.DataFrame([smd_feature_record(frame, feature) for feature in FEATURE_COLUMNS])
    invalid = records.loc[~records["calibration_valid"], "feature"].tolist()
    if invalid:
        raise AuditContractError(f"Balance calibration contains invalid features: {invalid}")
    eligible = records.loc[records["eligible_for_max_abs_smd"]]
    if eligible.empty:
        raise AuditContractError("UNDEFINED_NO_ELIGIBLE_FEATURES")
    maximum_row = eligible.loc[eligible["smd_absolute"].idxmax()]
    summary = {
        "max_absolute_smd": float(maximum_row["smd_absolute"]),
        "max_feature": str(maximum_row["feature"]),
        "eligible_features": eligible["feature"].tolist(),
        "excluded_global_constants": records.loc[
            records["statistic_status"] == "UNDEFINED_GLOBAL_CONSTANT", "feature"
        ].tolist(),
        # The observed statistic is computed in T03-A; its disposition (INFO/WARNING/
        # MATERIAL_CONCERN) requires the T03-C design-null calibrated percentiles.
        "threshold_source": "DEFERRED_T03_C_DESIGN_CALIBRATION",
    }
    return records, summary


def empirical_order_statistic(
    values: Sequence[float],
    probability: float,
) -> dict[str, Any]:
    """Return the non-interpolated inverse-ECDF order statistic."""

    array = np.asarray(values, dtype=np.float64)
    if not len(array) or not np.isfinite(array).all():
        raise AuditContractError("Null statistics must be a non-empty finite sequence")
    if not 0 < probability < 1:
        raise ValueError("probability must lie strictly between zero and one")
    ordered = np.sort(array)
    rank = int(math.ceil(len(ordered) * probability))
    threshold = float(ordered[rank - 1])
    return {
        "probability": float(probability),
        "replications": int(len(ordered)),
        "order_statistic_rank_one_based": rank,
        "threshold": threshold,
        "below_count": int(np.sum(ordered < threshold)),
        "equal_count": int(np.sum(ordered == threshold)),
        "above_count": int(np.sum(ordered > threshold)),
        "interpolation": "none_inverse_ecdf",
    }


def binomial_order_statistic_interval_ranks(
    replications: int,
    probability: float,
    *,
    confidence: float = 0.95,
) -> dict[str, Any]:
    """Compute exact-binomial order-statistic interval ranks numerically."""

    if replications <= 0 or not 0 < probability < 1 or not 0 < confidence < 1:
        raise ValueError("Invalid binomial order-statistic interval arguments")
    k = np.arange(replications + 1, dtype=np.float64)
    log_pmf = np.array(
        [
            math.lgamma(replications + 1)
            - math.lgamma(int(value) + 1)
            - math.lgamma(replications - int(value) + 1)
            + value * math.log(probability)
            + (replications - value) * math.log1p(-probability)
            for value in k
        ]
    )
    pmf = np.exp(log_pmf - float(log_pmf.max()))
    pmf /= pmf.sum()
    cdf = np.cumsum(pmf)
    survival_inclusive = np.cumsum(pmf[::-1])[::-1]
    alpha_half = (1.0 - confidence) / 2.0
    lower_candidates = [
        rank
        for rank in range(1, replications + 1)
        if cdf[rank - 1] <= alpha_half
    ]
    upper_candidates = [
        rank
        for rank in range(1, replications + 1)
        if survival_inclusive[rank] <= alpha_half
    ]
    lower_clipped = not lower_candidates
    upper_clipped = not upper_candidates
    lower_rank = max(lower_candidates) if lower_candidates else 1
    upper_rank = min(upper_candidates) if upper_candidates else replications
    return {
        "replications": int(replications),
        "probability": float(probability),
        "confidence": float(confidence),
        "lower_rank_one_based": int(lower_rank),
        "upper_rank_one_based": int(upper_rank),
        "lower_endpoint_clipped": lower_clipped,
        "upper_endpoint_clipped": upper_clipped,
        "method": "exact_binomial_order_statistic_numeric",
    }


def monte_carlo_order_statistic_interval(
    values: Sequence[float],
    probability: float,
    *,
    confidence: float = 0.95,
) -> dict[str, Any]:
    """Attach null-statistic values to the exact-binomial interval ranks."""

    ordered = np.sort(np.asarray(values, dtype=np.float64))
    if not len(ordered) or not np.isfinite(ordered).all():
        raise AuditContractError("Null statistics must be a non-empty finite sequence")
    ranks = binomial_order_statistic_interval_ranks(
        len(ordered), probability, confidence=confidence
    )
    return {
        **ranks,
        "lower_value": float(ordered[ranks["lower_rank_one_based"] - 1]),
        "upper_value": float(ordered[ranks["upper_rank_one_based"] - 1]),
    }


def diagnostic_action(observed: float, p95: float, p99: float) -> dict[str, str]:
    """Apply the frozen strict-above action boundaries."""

    if not np.isfinite([observed, p95, p99]).all() or p95 > p99:
        raise AuditContractError("Diagnostic thresholds are non-finite or incorrectly ordered")
    if observed <= p95:
        return {"evidence_status": "INFO", "required_action": "PASS"}
    if observed <= p99:
        return {"evidence_status": "WARNING", "required_action": "WARNING"}
    return {
        "evidence_status": "MATERIAL_CONCERN",
        "required_action": "ROBUSTNESS_REQUIRED",
    }


def monte_carlo_action_stability(
    observed: float,
    *,
    p95_point: float,
    p99_point: float,
    p95_interval: Mapping[str, Any],
    p99_interval: Mapping[str, Any],
    current_replications: int,
) -> dict[str, Any]:
    """Determine whether MC threshold uncertainty can change the required action."""

    point_action = diagnostic_action(observed, p95_point, p99_point)
    clipped = any(
        bool(interval.get(field, False))
        for interval in (p95_interval, p99_interval)
        for field in ("lower_endpoint_clipped", "upper_endpoint_clipped")
    )
    alternatives: list[dict[str, str]] = []
    invalid_order = False
    for q95 in (p95_interval["lower_value"], p95_interval["upper_value"]):
        for q99 in (p99_interval["lower_value"], p99_interval["upper_value"]):
            if q95 > q99:
                invalid_order = True
                continue
            alternatives.append(diagnostic_action(observed, float(q95), float(q99)))
    action_changed = any(action != point_action for action in alternatives)
    stable = not clipped and not invalid_order and not action_changed
    return {
        "stable": stable,
        "point_action": point_action,
        "alternative_actions": alternatives,
        "endpoint_clipped": clipped,
        "invalid_interval_order": invalid_order,
        "action_changed_across_interval_endpoints": action_changed,
        "next_replication_target": (
            None if stable else current_replications + CONTINUATION_INCREMENT
        ),
        "continuation_rule": "append exactly 2000 deterministic replications",
    }


def empirical_tail_fraction(values: Sequence[float], observed: float) -> dict[str, Any]:
    """Return a calibration summary that is explicitly not a p-value."""

    array = np.asarray(values, dtype=np.float64)
    if not len(array) or not np.isfinite(array).all() or not np.isfinite(observed):
        raise AuditContractError("Tail-fraction inputs must be finite and non-empty")
    count = int(np.sum(array >= observed))
    return {
        "empirical_tail_fraction": count / len(array),
        "at_least_observed_count": count,
        "replications": int(len(array)),
        "terminology": "CALIBRATION_SUMMARY_NOT_PERMUTATION_P_VALUE",
    }


def continuation_indices(existing_replications: int, target_replications: int) -> range:
    """Return the deterministic append-only replication-index interval."""

    if existing_replications < 0 or target_replications <= existing_replications:
        raise ValueError("Continuation target must exceed the existing replication count")
    if target_replications % CONTINUATION_INCREMENT:
        raise AuditContractError("Continuation totals must be multiples of 2,000")
    if existing_replications and existing_replications % CONTINUATION_INCREMENT:
        raise AuditContractError("Existing production totals must be multiples of 2,000")
    return range(existing_replications, target_replications)


def deferred_evidence_record(
    audit_id: str,
    *,
    held_out_sealed: bool = False,
) -> dict[str, Any]:
    """Serialize not-executed evidence without fabricating a status or action."""

    if held_out_sealed:
        execution_state = "SEALED_DEFERRED_BY_TEST_ISOLATION"
        deferred_to = "T17"
    else:
        # Randomization calibration (ED-03/ED-04 disposition) is T03-C, not T03-B.
        # T03-B is split-identity and development-integrity diagnostics (DP-01/HG-07, ED-02).
        execution_state = "DEFERRED_T03_C"
        deferred_to = "T03-C"
    return {
        "audit_id": audit_id,
        "method_status": "ACCEPTED",
        "execution_state": execution_state,
        "evidence_status": None,
        "required_action": None,
        "deferred_to": deferred_to,
    }


def pending_disposition_evidence_record(
    audit_id: str,
    *,
    observed: Any,
) -> dict[str, Any]:
    """Serialize an executed T03-A observed statistic awaiting T03-C disposition.

    Distinct from ``deferred_evidence_record``: the observed value has genuinely
    been computed against the real population (e.g. ED-03's max absolute SMD).
    Only the evidence_status/required_action mapping is pending, because it
    requires the T03-C design-null calibrated percentiles.
    """

    return {
        "audit_id": audit_id,
        "execution_state": "EXECUTED_PENDING_T03C_DISPOSITION",
        "evidence_status": None,
        "required_action": None,
        "observed": observed,
        "deferred_to": "T03-C",
    }


def validate_evidence_record(record: Mapping[str, Any]) -> None:
    """Enforce evidence/action/execution separation."""

    required = {"evidence_class", "evidence_status", "required_action", "execution_state"}
    missing = sorted(required.difference(record))
    if missing:
        raise AuditContractError(f"Evidence record is missing fields: {missing}")
    execution = record["execution_state"]
    if execution in {
        "DEFERRED_T03_C",
        "SEALED_DEFERRED_BY_TEST_ISOLATION",
        "EXECUTED_PENDING_T03C_DISPOSITION",
    }:
        if record["evidence_status"] is not None or record["required_action"] is not None:
            raise AuditContractError("Deferred/undispositioned evidence must have null status and action")
        return
    evidence_class = record["evidence_class"]
    if evidence_class not in EVIDENCE_CLASSES:
        raise AuditContractError(f"Unknown evidence class: {evidence_class}")
    if record["evidence_status"] not in EVIDENCE_STATUSES[evidence_class]:
        raise AuditContractError("Evidence status is invalid for its evidence class")
    if record["required_action"] not in REQUIRED_ACTIONS:
        raise AuditContractError("Unknown required action")


def verify_regenerated_mapping_hash(
    expected_sha256: str,
    source_row_ids: Iterable[Any],
    values: Iterable[Any],
    *,
    value_name: str,
    value_dtype: str,
) -> None:
    """Fail closed when regenerated production mapping identity differs."""

    observed = hash_row_mapping(
        source_row_ids,
        values,
        value_name=value_name,
        value_dtype=value_dtype,
    )
    if observed != expected_sha256:
        raise AuditContractError(
            f"Regenerated {value_name} mapping hash mismatch: expected {expected_sha256}, observed {observed}"
        )


def calibration_artifact_schema() -> dict[str, Any]:
    """Return the future T03-B compact persistence contract."""

    return {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "population_level": [
            "canonical_source_row_identity_sha256",
            "block_contract_config_sha256",
            "block_membership_sha256",
        ],
        "per_replication": [
            "replication_index",
            "master_seed",
            "sub_seed_metadata",
            "ordering_contract_version",
            "block_contract_config_sha256",
            "source_row_to_T_perm_sha256",
            "source_row_to_fold_id_sha256",
            "invariant_checks",
            "null_statistics",
            "execution_resource_metadata",
        ],
        "production_full_mapping_persistence": False,
        "full_mapping_allowed_modes": ["UNIT_FIXTURE", "SMOKE_ONLY"],
        "regeneration_required": True,
        "regenerated_hash_mismatch_action": "STOP",
    }


def algorithm_contract() -> dict[str, Any]:
    """Return the frozen, result-free T03-B algorithm declaration."""

    return {
        "method": "CONDITIONAL_PERMUTATION_APPROXIMATION",
        "execution_state": "DEFERRED_T03_C",
        "initial_replications": INITIAL_NULL_REPLICATIONS,
        "continuation_increment": CONTINUATION_INCREMENT,
        "master_seed": MASTER_PERMUTATION_SEED,
        "seed_derivation_version": SEED_DERIVATION_VERSION,
        "ordering_contract_version": ORDERING_CONTRACT_VERSION,
        "features": list(FEATURE_COLUMNS),
        "classifier": dict(LIGHTGBM_TREATMENT_CONFIG),
        "folds": {"count": N_FOLDS, "stratification": TREATMENT_COLUMN, "seed": FOLD_SEED},
        "smd": {
            "formula": "(mean_treated-mean_control)/sqrt((var_treated_ddof1+var_control_ddof1)/2)",
            "maximum": "max absolute eligible-feature SMD",
            "abs_smd_0_10": "LITERATURE_REFERENCE_NOT_GATE",
        },
        "percentiles": {
            "definition": "z_(ceil(B*p))",
            "interpolation": "none",
            "probabilities": [0.95, 0.99],
            "equality_boundary": "lower_action_band",
        },
        "monte_carlo_interval": "exact_binomial_order_statistic_95_percent",
        "monte_carlo_instability": "endpoint clipping or action change across p95/p99 interval endpoints",
        "continuation": "append exactly 2000 deterministic replications without replacing earlier draws",
        "empirical_tail_fraction_role": "CALIBRATION_SUMMARY_NOT_PERMUTATION_P_VALUE",
        "held_out_access": False,
    }


def validate_no_permutation_p_value_language(payload: Any) -> None:
    """Reject terminology that upgrades a calibration summary to a p-value."""

    def inspect(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, item in value.items():
                inspect(str(key))
                inspect(item)
            return
        if isinstance(value, (list, tuple, set)):
            for item in value:
                inspect(item)
            return
        if not isinstance(value, str):
            return
        normalized = " ".join(
            value.lower().replace("_", " ").replace("-", " ").split()
        )
        guarded = (
            "not permutation p value" in normalized
            or "must not be called a permutation p value" in normalized
        )
        if "permutation p value" in normalized and not guarded:
            raise AuditContractError(
                "empirical_tail_fraction must not be called a permutation p-value"
            )

    inspect(payload)


def t03_implementation_environment() -> dict[str, Any]:
    """Return result-free implementation metadata for a future governed run."""

    packages = {}
    for distribution in ("lightgbm", "scikit-learn", "numpy", "pandas"):
        try:
            packages[distribution] = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            packages[distribution] = None
    return {
        "python": sys.version,
        "platform": platform.platform(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "packages": packages,
        "lightgbm_classifier_config": dict(LIGHTGBM_TREATMENT_CONFIG),
        "ordering_contract_version": ORDERING_CONTRACT_VERSION,
        "seed_derivation_version": SEED_DERIVATION_VERSION,
    }


def write_t03_json_new(run_root: Path, relative_path: str, payload: Any) -> Path:
    """Write one declared T03-A JSON artifact without overwrite or late mutation."""

    if T03A_ARTIFACT_KINDS.get(relative_path) != "json":
        raise AuditContractError(f"Undeclared T03-A JSON artifact path: {relative_path}")
    validate_no_permutation_p_value_language(payload)
    return write_json_new(run_root, relative_path, payload)


def write_t03_csv_new(run_root: Path, relative_path: str, frame: pd.DataFrame) -> Path:
    """Write one declared T03-A CSV artifact without overwrite or late mutation."""

    if T03A_ARTIFACT_KINDS.get(relative_path) != "csv":
        raise AuditContractError(f"Undeclared T03-A CSV artifact path: {relative_path}")
    validate_no_permutation_p_value_language(list(frame.columns))
    return write_text_new(run_root, relative_path, frame.to_csv(index=False, lineterminator="\n"))


def write_fixture_mapping_new(
    run_root: Path,
    relative_path: str,
    payload: bytes,
    *,
    execution_mode: str,
) -> Path:
    """Permit full mappings only for intentionally bounded fixture/smoke evidence."""

    if execution_mode not in {"UNIT_FIXTURE", "SMOKE_ONLY"}:
        raise AuditContractError("Full row mappings are forbidden for production calibration")
    return write_bytes_new(run_root, relative_path, payload)
