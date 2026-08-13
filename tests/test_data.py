from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pytest

from src.data import (
    FEATURE_COLUMNS,
    PROCESSED_COLUMNS,
    RAW_SCHEMA,
    ROW_GROUP_SIZE,
    DataContractError,
    SemanticHasher,
    convert_csv_to_parquet,
    finalize_artifact_manifest,
    load_selector,
    open_processed_dataset,
    promote_processed_with_rollback,
    sha256_file,
    validate_processed_parquet,
    validate_source_identity,
    verify_expected_file_checksum,
    write_bytes_new,
    write_json_new,
    write_text_new,
)


def _frame(rows: int = 8) -> pd.DataFrame:
    payload = {
        name: [float(index) + column / 100 for index in range(rows)]
        for column, name in enumerate(FEATURE_COLUMNS)
    }
    payload.update(
        {
            "treatment": [index % 2 for index in range(rows)],
            "conversion": [(index // 2) % 2 for index in range(rows)],
            "visit": [(index + 1) % 2 for index in range(rows)],
            "exposure": [index % 2 for index in range(rows)],
        }
    )
    return pd.DataFrame(payload)


def _selector_payload(raw: Path, compressed: Path, processed: Path) -> dict:
    return {
        "manifest_role": "LOCAL_SELECTOR",
        "dataset_name": "CRITEO-UPLIFTv2.1",
        "raw_path": str(raw),
        "raw_compressed_path": str(compressed),
        "processed_path": str(processed),
        "raw_sha256": sha256_file(raw),
        "raw_compressed_sha256": sha256_file(compressed),
        "processed_sha256": None,
        "expected_rows": len(pd.read_csv(raw)),
        "feature_columns": list(FEATURE_COLUMNS),
        "treatment_column": "treatment",
        "primary_outcome": "conversion",
        "secondary_outcomes": ["visit"],
        "post_assignment_columns": ["exposure"],
        "source_row_identity": {
            "field": "_source_row_id",
            "definition": "zero-based canonical CSV data-row ordinal",
            "model_feature": False,
        },
        "conversion": {
            "format": "parquet",
            "compression": "zstd",
            "row_group_size": ROW_GROUP_SIZE,
            "analytical_precision": "float64",
        },
    }


def _write_selector(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "selector.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_missing_manifest_selected_input_fails_closed(tmp_path: Path) -> None:
    raw = tmp_path / "missing.csv"
    compressed = tmp_path / "source.csv.gz"
    compressed.write_bytes(b"placeholder")
    selector_payload = {
        "manifest_role": "LOCAL_SELECTOR",
        "dataset_name": "CRITEO-UPLIFTv2.1",
        "raw_path": str(raw),
        "raw_compressed_path": str(compressed),
        "processed_path": str(tmp_path / "processed.parquet"),
        "raw_sha256": "0" * 64,
        "raw_compressed_sha256": sha256_file(compressed),
        "processed_sha256": None,
        "expected_rows": 1,
        "feature_columns": list(FEATURE_COLUMNS),
        "treatment_column": "treatment",
        "primary_outcome": "conversion",
        "secondary_outcomes": ["visit"],
        "post_assignment_columns": ["exposure"],
        "source_row_identity": {"field": "_source_row_id", "model_feature": False},
        "conversion": {
            "format": "parquet",
            "compression": "zstd",
            "row_group_size": ROW_GROUP_SIZE,
            "analytical_precision": "float64",
        },
    }
    selector = load_selector(_write_selector(tmp_path, selector_payload), tmp_path)
    with pytest.raises(FileNotFoundError, match="missing"):
        validate_source_identity(selector)


def test_malformed_schema_fails_before_conversion(tmp_path: Path) -> None:
    frame = _frame().drop(columns=["f11"])
    raw = tmp_path / "malformed.csv"
    raw.write_text(frame.to_csv(index=False), encoding="utf-8")
    destination = tmp_path / "malformed.parquet"
    with pytest.raises(DataContractError, match="schema|columns"):
        convert_csv_to_parquet(raw, destination, row_limit=None)
    assert not destination.exists()


def test_checksum_incompatible_artifact_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "artifact.bin"
    path.write_bytes(b"current")
    with pytest.raises(DataContractError, match="checksum mismatch"):
        verify_expected_file_checksum(path, "0" * 64)


def test_processed_consumer_accepts_pinned_identity_and_rejects_same_schema_stale_file(
    tmp_path: Path,
) -> None:
    first_frame = _frame()
    first_raw = tmp_path / "first.csv"
    first_raw.write_text(first_frame.to_csv(index=False), encoding="utf-8")
    compressed = tmp_path / "source.csv.gz"
    compressed.write_bytes(b"synthetic compressed-source identity fixture")
    processed = tmp_path / "processed.parquet"
    first_result = convert_csv_to_parquet(first_raw, processed, row_limit=None)

    payload = _selector_payload(first_raw, compressed, processed)
    generation_selector = load_selector(_write_selector(tmp_path, payload), tmp_path)
    with pytest.raises(DataContractError, match="CONSUMPTION requires"):
        open_processed_dataset(generation_selector)

    payload["processed_sha256"] = first_result["file_sha256"]
    selector = load_selector(_write_selector(tmp_path, payload), tmp_path)
    assert open_processed_dataset(selector).schema.names == list(PROCESSED_COLUMNS)

    stale_frame = _frame()
    stale_frame.loc[0, "f0"] = 999.0
    stale_raw = tmp_path / "stale.csv"
    stale_raw.write_text(stale_frame.to_csv(index=False), encoding="utf-8")
    replacement = tmp_path / "same-schema-replacement.parquet"
    stale_result = convert_csv_to_parquet(stale_raw, replacement, row_limit=None)
    assert stale_result["file_sha256"] != first_result["file_sha256"]
    replacement.replace(processed)

    with pytest.raises(DataContractError, match="checksum mismatch"):
        open_processed_dataset(selector)


def test_small_conversion_is_semantic_and_physically_deterministic(tmp_path: Path) -> None:
    frame = _frame()
    raw = tmp_path / "canonical.csv"
    raw.write_text(frame.to_csv(index=False), encoding="utf-8")
    compressed = tmp_path / "canonical.csv.gz"
    compressed.write_bytes(b"synthetic compressed-source identity fixture")
    first = tmp_path / "first.parquet"
    second = tmp_path / "second.parquet"

    selector = load_selector(
        _write_selector(tmp_path, _selector_payload(raw, compressed, first)),
        tmp_path,
    )
    assert validate_source_identity(selector)["status"] == "PASS"

    first_result = convert_csv_to_parquet(raw, first, row_limit=None)
    second_result = convert_csv_to_parquet(raw, second, row_limit=None)
    first_validation = validate_processed_parquet(
        first,
        expected_rows=len(frame),
        expected_raw_semantics=first_result["raw_semantics"],
    )
    second_validation = validate_processed_parquet(
        second,
        expected_rows=len(frame),
        expected_raw_semantics=second_result["raw_semantics"],
    )

    assert first_result["file_sha256"] == second_result["file_sha256"]
    assert first_result["raw_semantics"] == second_result["raw_semantics"]
    assert first_validation["semantic_identity"] is True
    assert second_validation["semantic_identity"] is True
    assert first_validation["float64_preserved"] is True
    assert first_validation["columns"] == list(PROCESSED_COLUMNS)
    assert first_validation["source_row_id"]["complete_unique_ordered"] is True
    assert first_validation["source_row_id"]["model_feature"] is False
    assert first_validation["compression"] == ["zstd"]


@pytest.fixture
def completed_run(tmp_path: Path) -> Path:
    run_root = tmp_path / "run"
    audit = run_root / "audit"
    audit.mkdir(parents=True)
    (audit / "artifact_manifest.json").write_text(
        json.dumps({"status": "COMPLETED_PASS"}), encoding="utf-8"
    )
    return run_root


def test_completed_run_rejects_late_json(completed_run: Path) -> None:
    with pytest.raises(DataContractError, match="immutable"):
        write_json_new(completed_run, "audit/late.json", {"unexpected": True})


def test_completed_run_rejects_late_csv(completed_run: Path) -> None:
    with pytest.raises(DataContractError, match="immutable"):
        write_text_new(completed_run, "tables/late.csv", "value\n1\n")


def test_completed_run_rejects_late_png(completed_run: Path) -> None:
    with pytest.raises(DataContractError, match="immutable"):
        write_bytes_new(completed_run, "figures/late.png", b"synthetic-png")


def test_governed_artifact_writer_rejects_overwrite(tmp_path: Path) -> None:
    run_root = tmp_path / "run"
    destination = write_text_new(run_root, "tables/existing.csv", "value\n1\n")

    with pytest.raises(FileExistsError):
        write_text_new(run_root, "tables/existing.csv", "value\n2\n")

    assert destination.read_text(encoding="utf-8") == "value\n1\n"


def test_artifact_manifest_records_declared_stage_and_population(tmp_path: Path) -> None:
    run_root = tmp_path / "outputs" / "runs" / "t02_fixture"
    write_json_new(run_root, "audit/run_config.json", {"task": "T02"})

    manifest_path = finalize_artifact_manifest(
        run_root,
        run_id="t02_fixture",
        external_artifacts=[],
        final_status="COMPLETED_PASS",
        created_at_utc="2026-08-13T00:00:00+00:00",
        stage="pre_split_descriptive_eda",
        population="validated_unsplit_released_rows",
    )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["artifacts"]
    assert {
        (artifact["stage"], artifact["population"])
        for artifact in manifest["artifacts"]
    } == {("pre_split_descriptive_eda", "validated_unsplit_released_rows")}


def test_failed_promotion_restores_existing_canonical(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = tmp_path / "candidate.parquet"
    canonical = tmp_path / "canonical.parquet"
    candidate.write_bytes(b"validated candidate")
    canonical.write_bytes(b"existing canonical")
    expected_candidate_hash = sha256_file(candidate)
    existing_canonical_hash = sha256_file(canonical)

    original_replace = __import__("os").replace

    def fail_candidate_to_target(source, destination):
        if Path(source) == candidate and Path(destination) == canonical:
            raise OSError("synthetic promotion failure")
        return original_replace(source, destination)

    monkeypatch.setattr("src.data.os.replace", fail_candidate_to_target)
    with pytest.raises(OSError, match="synthetic promotion failure"):
        promote_processed_with_rollback(
            candidate,
            canonical,
            expected_sha256=expected_candidate_hash,
        )

    assert sha256_file(canonical) == existing_canonical_hash
    assert candidate.is_file()
    assert not canonical.with_name(canonical.name + ".previous.tmp").exists()


def test_interrupted_promotion_state_fails_closed_without_discarding_backup(
    tmp_path: Path,
) -> None:
    candidate = tmp_path / "candidate.parquet"
    canonical = tmp_path / "canonical.parquet"
    backup = canonical.with_name(canonical.name + ".previous.tmp")
    candidate.write_bytes(b"validated candidate")
    backup.write_bytes(b"previous canonical requiring explicit validation")

    with pytest.raises(DataContractError, match="canonical target is missing"):
        promote_processed_with_rollback(
            candidate,
            canonical,
            expected_sha256=sha256_file(candidate),
        )

    assert not canonical.exists()
    assert candidate.read_bytes() == b"validated candidate"
    assert backup.read_bytes() == b"previous canonical requiring explicit validation"


def test_semantic_digest_is_independent_of_batch_boundaries() -> None:
    frame = _frame(rows=9)
    table = pa.Table.from_pandas(frame, schema=RAW_SCHEMA, preserve_index=False)
    one_batch = SemanticHasher(RAW_SCHEMA)
    one_batch.update(table.to_batches(max_chunksize=9)[0])

    uneven_batches = SemanticHasher(RAW_SCHEMA)
    for batch in table.to_batches(max_chunksize=4):
        uneven_batches.update(batch)

    assert one_batch.result() == uneven_batches.result()
