"""T01 manifest-driven CRITEO-UPLIFTv2.1 loading and conversion helpers.

The notebook remains the primary research record.  This module contains only
the reusable, regression-sensitive mechanics needed by later data tasks:
manifest resolution, fail-closed schema checks, deterministic Parquet writing,
semantic hashing, and immutable run-artifact handling.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.csv as pacsv
import pyarrow.dataset as pads
import pyarrow.parquet as pq


FEATURE_COLUMNS = tuple(f"f{i}" for i in range(12))
CONTINUOUS_FEATURES = (
    "f0",
    "f2",
    "f7",
    "f10",
)

CATEGORICAL_FEATURES = (
    "f1",
    "f3",
    "f4",
    "f5",
    "f6",
    "f8",
    "f9",
    "f11",
)

FEATURE_SEMANTICS = {
    **{feature: "continuous" for feature in CONTINUOUS_FEATURES},
    **{feature: "categorical" for feature in CATEGORICAL_FEATURES},
}

if set(CONTINUOUS_FEATURES) & set(CATEGORICAL_FEATURES):
    raise RuntimeError("Feature semantic groups overlap")

if set(CONTINUOUS_FEATURES) | set(CATEGORICAL_FEATURES) != set(FEATURE_COLUMNS):
    raise RuntimeError("Feature semantic groups do not cover FEATURE_COLUMNS")
TREATMENT_COLUMN = "treatment"
PRIMARY_OUTCOME = "conversion"
SECONDARY_OUTCOME = "visit"
AUDIT_ONLY_COLUMN = "exposure"
SOURCE_ROW_ID = "_source_row_id"
RAW_COLUMNS = FEATURE_COLUMNS + (
    TREATMENT_COLUMN,
    PRIMARY_OUTCOME,
    SECONDARY_OUTCOME,
    AUDIT_ONLY_COLUMN,
)
PROCESSED_COLUMNS = RAW_COLUMNS + (SOURCE_ROW_ID,)
MODEL_FEATURES = FEATURE_COLUMNS
FORBIDDEN_MODEL_COLUMNS = (
    TREATMENT_COLUMN,
    PRIMARY_OUTCOME,
    SECONDARY_OUTCOME,
    AUDIT_ONLY_COLUMN,
    SOURCE_ROW_ID,
)

ROW_GROUP_SIZE = 1_048_576
CSV_BLOCK_SIZE = 16 * 1024 * 1024
SCAN_BATCH_SIZE = 131_072
EXPECTED_ARROW_TYPES = {
    **{name: pa.float64() for name in FEATURE_COLUMNS},
    TREATMENT_COLUMN: pa.int64(),
    PRIMARY_OUTCOME: pa.int64(),
    SECONDARY_OUTCOME: pa.int64(),
    AUDIT_ONLY_COLUMN: pa.int64(),
    SOURCE_ROW_ID: pa.int64(),
}
RAW_SCHEMA = pa.schema([pa.field(name, EXPECTED_ARROW_TYPES[name]) for name in RAW_COLUMNS])
PROCESSED_SCHEMA = pa.schema(
    [pa.field(name, EXPECTED_ARROW_TYPES[name]) for name in PROCESSED_COLUMNS]
)
WRITER_SETTINGS = {
    "compression": "zstd",
    "row_group_size": ROW_GROUP_SIZE,
    "use_dictionary": True,
    "write_statistics": True,
    "data_page_version": "1.0",
    "version": "2.6",
}


class DataContractError(RuntimeError):
    """Raised when a T01 input, conversion, or artifact contract fails."""


@dataclass(frozen=True)
class ResolvedSelector:
    selector_path: Path
    repo_root: Path
    raw_csv_path: Path
    raw_compressed_path: Path
    processed_path: Path
    payload: dict[str, Any]


def sha256_file(path: Path, block_size: int = 8 * 1024 * 1024) -> str:
    """Return the SHA-256 digest of one existing file."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(block_size), b""):
            digest.update(block)
    return digest.hexdigest()


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        character in "0123456789abcdef" for character in value.lower()
    )


def _resolve_declared_path(repo_root: Path, declared: object, field: str) -> Path:
    if not isinstance(declared, str) or not declared.strip():
        raise DataContractError(f"Selector field {field!r} must be a non-empty path")
    candidate = Path(declared)
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    return candidate.resolve()


def load_selector(selector_path: Path, repo_root: Path) -> ResolvedSelector:
    """Load one explicit local selector; never search directories for inputs."""

    selector_path = selector_path.resolve()
    repo_root = repo_root.resolve()
    if not selector_path.is_file():
        raise FileNotFoundError(f"Explicit T01 selector does not exist: {selector_path}")
    try:
        payload = json.loads(selector_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DataContractError(f"Cannot parse selector {selector_path}: {exc}") from exc

    required = {
        "manifest_role",
        "dataset_name",
        "raw_path",
        "raw_compressed_path",
        "processed_path",
        "raw_sha256",
        "raw_compressed_sha256",
        "processed_sha256",
        "expected_rows",
        "feature_columns",
        "treatment_column",
        "primary_outcome",
        "secondary_outcomes",
        "post_assignment_columns",
        "source_row_identity",
        "conversion",
    }
    missing = sorted(required.difference(payload))
    if missing:
        raise DataContractError(f"Selector is missing required fields: {missing}")
    if payload["manifest_role"] != "LOCAL_SELECTOR":
        raise DataContractError("manifest_role must be LOCAL_SELECTOR")
    if payload["dataset_name"] != "CRITEO-UPLIFTv2.1":
        raise DataContractError("dataset_name must be CRITEO-UPLIFTv2.1")
    if tuple(payload["feature_columns"]) != FEATURE_COLUMNS:
        raise DataContractError("feature_columns must be exactly f0 through f11 in order")
    if payload["treatment_column"] != TREATMENT_COLUMN:
        raise DataContractError("treatment_column must be treatment")
    if payload["primary_outcome"] != PRIMARY_OUTCOME:
        raise DataContractError("primary_outcome must be conversion")
    if tuple(payload["secondary_outcomes"]) != (SECONDARY_OUTCOME,):
        raise DataContractError("secondary_outcomes must contain only visit for T01")
    if tuple(payload["post_assignment_columns"]) != (AUDIT_ONLY_COLUMN,):
        raise DataContractError("post_assignment_columns must contain only exposure")
    identity = payload["source_row_identity"]
    if identity.get("field") != SOURCE_ROW_ID or identity.get("model_feature") is not False:
        raise DataContractError("_source_row_id must be declared as non-feature identity metadata")
    if not isinstance(payload["expected_rows"], int) or payload["expected_rows"] <= 0:
        raise DataContractError("expected_rows must be a positive integer")
    for hash_field in ("raw_sha256", "raw_compressed_sha256"):
        if not _is_sha256(payload[hash_field]):
            raise DataContractError(f"{hash_field} must be a 64-character SHA-256")
    if payload["processed_sha256"] is not None and not _is_sha256(
        payload["processed_sha256"]
    ):
        raise DataContractError(
            "processed_sha256 must be null during GENERATION or a 64-character "
            "SHA-256 before CONSUMPTION"
        )
    conversion = payload["conversion"]
    expected_conversion = {
        "format": "parquet",
        "compression": "zstd",
        "row_group_size": ROW_GROUP_SIZE,
        "analytical_precision": "float64",
    }
    for key, expected in expected_conversion.items():
        if conversion.get(key) != expected:
            raise DataContractError(
                f"conversion.{key} must be {expected!r}, got {conversion.get(key)!r}"
            )

    return ResolvedSelector(
        selector_path=selector_path,
        repo_root=repo_root,
        raw_csv_path=_resolve_declared_path(repo_root, payload["raw_path"], "raw_path"),
        raw_compressed_path=_resolve_declared_path(
            repo_root, payload["raw_compressed_path"], "raw_compressed_path"
        ),
        processed_path=_resolve_declared_path(
            repo_root, payload["processed_path"], "processed_path"
        ),
        payload=payload,
    )


def portable_repo_path(path: Path, repo_root: Path) -> str:
    """Return a slash-normalized repository-relative path or fail closed."""

    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError as exc:
        raise DataContractError(f"Path is outside the repository root: {path}") from exc


def validate_source_identity(selector: ResolvedSelector) -> dict[str, Any]:
    """Validate approved source paths, exact header, sizes, and SHA-256 values."""

    for path in (selector.raw_csv_path, selector.raw_compressed_path):
        if not path.is_file():
            raise FileNotFoundError(f"Manifest-selected source is missing: {path}")

    raw_sha256 = sha256_file(selector.raw_csv_path)
    compressed_sha256 = sha256_file(selector.raw_compressed_path)
    if raw_sha256 != selector.payload["raw_sha256"]:
        raise DataContractError(
            f"Raw CSV checksum mismatch: expected {selector.payload['raw_sha256']}, "
            f"observed {raw_sha256}"
        )
    if compressed_sha256 != selector.payload["raw_compressed_sha256"]:
        raise DataContractError(
            "Compressed source checksum mismatch: expected "
            f"{selector.payload['raw_compressed_sha256']}, observed {compressed_sha256}"
        )

    with selector.raw_csv_path.open("r", encoding="utf-8", newline="") as handle:
        header = tuple(next(csv.reader(handle)))
    if header != RAW_COLUMNS:
        raise DataContractError(
            f"Raw schema/header mismatch: expected {RAW_COLUMNS}, observed {header}"
        )

    expected_sizes = selector.payload.get("source_size_bytes", {})
    observed_sizes = {
        "raw_csv": selector.raw_csv_path.stat().st_size,
        "raw_compressed": selector.raw_compressed_path.stat().st_size,
    }
    for key, expected in expected_sizes.items():
        if key in observed_sizes and expected is not None and observed_sizes[key] != expected:
            raise DataContractError(
                f"{key} size mismatch: expected {expected}, observed {observed_sizes[key]}"
            )

    return {
        "dataset_name": selector.payload["dataset_name"],
        "raw_csv": {
            "path": portable_repo_path(selector.raw_csv_path, selector.repo_root),
            "size_bytes": observed_sizes["raw_csv"],
            "sha256": raw_sha256,
        },
        "raw_compressed": {
            "path": portable_repo_path(selector.raw_compressed_path, selector.repo_root),
            "size_bytes": observed_sizes["raw_compressed"],
            "sha256": compressed_sha256,
        },
        "header": list(header),
        "status": "PASS",
    }


def verify_expected_file_checksum(path: Path, expected_sha256: str) -> dict[str, Any]:
    """Fail when an existing artifact does not match its declared checksum."""

    if not path.is_file():
        raise FileNotFoundError(path)
    if not _is_sha256(expected_sha256):
        raise DataContractError("Expected artifact checksum is not a valid SHA-256")
    observed = sha256_file(path)
    if observed != expected_sha256:
        raise DataContractError(
            f"Artifact checksum mismatch for {path}: expected {expected_sha256}, observed {observed}"
        )
    return {"path": str(path), "sha256": observed, "status": "PASS"}


def open_csv_reader(path: Path) -> pacsv.CSVStreamingReader:
    """Open the canonical CSV with explicit physical types."""

    if not path.is_file():
        raise FileNotFoundError(path)
    return pacsv.open_csv(
        path,
        read_options=pacsv.ReadOptions(
            block_size=CSV_BLOCK_SIZE,
            use_threads=True,
        ),
        parse_options=pacsv.ParseOptions(delimiter=",", quote_char='"'),
        convert_options=pacsv.ConvertOptions(
            column_types={name: EXPECTED_ARROW_TYPES[name] for name in RAW_COLUMNS},
            strings_can_be_null=False,
        ),
    )


def _validate_raw_batch(batch: pa.RecordBatch, stats: dict[str, Any]) -> None:
    if tuple(batch.schema.names) != RAW_COLUMNS:
        raise DataContractError(
            f"Parsed batch columns differ from the contract: {batch.schema.names}"
        )
    if not batch.schema.equals(RAW_SCHEMA, check_metadata=False):
        raise DataContractError(f"Parsed batch schema differs from contract: {batch.schema}")

    for name in FEATURE_COLUMNS:
        array = batch.column(batch.schema.get_field_index(name))
        stats["null_counts"][name] += array.null_count
        values = array.drop_null().to_numpy(zero_copy_only=False)
        if values.size and not np.isfinite(values).all():
            raise DataContractError(f"Feature {name} contains positive or negative infinity")

    for name in (TREATMENT_COLUMN, PRIMARY_OUTCOME, SECONDARY_OUTCOME):
        array = batch.column(batch.schema.get_field_index(name))
        stats["null_counts"][name] += array.null_count
        if array.null_count:
            raise DataContractError(f"Required binary field {name} contains nulls")
        values = array.to_numpy(zero_copy_only=False)
        observed = set(np.unique(values).tolist())
        stats["binary_support"][name].update(observed)
        if not observed.issubset({0, 1}):
            raise DataContractError(f"Field {name} contains values outside {{0,1}}: {observed}")

    exposure = batch.column(batch.schema.get_field_index(AUDIT_ONLY_COLUMN))
    stats["null_counts"][AUDIT_ONLY_COLUMN] += exposure.null_count


class SemanticHasher:
    """Streaming, batch-boundary-independent semantic digest for fixed-width columns."""

    def __init__(self, schema: pa.Schema):
        self.schema = schema.remove_metadata()
        self.rows = 0
        self._validity_digests = {name: hashlib.sha256() for name in schema.names}
        self._value_digests = {name: hashlib.sha256() for name in schema.names}
        self._headers: dict[str, bytes] = {}
        for field in self.schema:
            self._headers[field.name] = (
                f"{field.name}|{field.type}|nullable={field.nullable}\n".encode("utf-8")
            )

    def update(self, batch: pa.RecordBatch | pa.Table) -> None:
        if not batch.schema.remove_metadata().equals(self.schema, check_metadata=False):
            raise DataContractError("Semantic hash input schema changed during streaming")
        for name in self.schema.names:
            column = batch[name]
            chunks: Iterable[pa.Array]
            if isinstance(column, pa.ChunkedArray):
                chunks = column.chunks
            else:
                chunks = (column,)
            for array in chunks:
                valid = np.asarray(array.is_valid().to_numpy(zero_copy_only=False), dtype=np.uint8)
                filled = pc.fill_null(array, 0)
                values = np.asarray(filled.to_numpy(zero_copy_only=False))
                if pa.types.is_floating(array.type):
                    values = np.asarray(values, dtype="<f8")
                elif pa.types.is_integer(array.type):
                    values = np.asarray(values, dtype="<i8")
                else:
                    raise DataContractError(f"Unsupported semantic-hash type: {array.type}")
                # Validity and values use separate streams so the final digest is
                # independent of CSV/Parquet batch boundaries.
                self._validity_digests[name].update(valid.tobytes(order="C"))
                self._value_digests[name].update(values.tobytes(order="C"))
        self.rows += batch.num_rows

    def result(self) -> dict[str, Any]:
        column_hashes = {}
        for name in self.schema.names:
            digest = hashlib.sha256()
            digest.update(self._headers[name])
            digest.update(self._validity_digests[name].digest())
            digest.update(self._value_digests[name].digest())
            column_hashes[name] = digest.hexdigest()
        summary = {
            "schema": str(self.schema),
            "rows": self.rows,
            "column_sha256": column_hashes,
        }
        summary["semantic_sha256"] = hashlib.sha256(
            json.dumps(summary, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return summary


def _augment_with_source_ids(batch: pa.RecordBatch, offset: int) -> pa.RecordBatch:
    ids = pa.array(np.arange(offset, offset + batch.num_rows, dtype=np.int64))
    return pa.RecordBatch.from_arrays(
        [batch.column(index) for index in range(batch.num_columns)] + [ids],
        names=list(RAW_COLUMNS) + [SOURCE_ROW_ID],
    )


def _flush_row_group(
    writer: pq.ParquetWriter,
    pieces: list[pa.RecordBatch],
) -> None:
    table = pa.Table.from_batches(pieces, schema=PROCESSED_SCHEMA)
    writer.write_table(table, row_group_size=ROW_GROUP_SIZE)


def convert_csv_to_parquet(
    raw_csv_path: Path,
    destination: Path,
    *,
    row_limit: int | None,
) -> dict[str, Any]:
    """Convert a canonical source prefix to deterministic ZSTD Parquet."""

    if row_limit is not None and row_limit <= 0:
        raise ValueError("row_limit must be positive or None")
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite conversion target: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)

    reader = open_csv_reader(raw_csv_path)
    if not reader.schema.equals(RAW_SCHEMA, check_metadata=False):
        raise DataContractError(f"CSV schema differs from contract: {reader.schema}")

    raw_hasher = SemanticHasher(RAW_SCHEMA)
    stats: dict[str, Any] = {
        "null_counts": {name: 0 for name in RAW_COLUMNS},
        "binary_support": {
            TREATMENT_COLUMN: set(),
            PRIMARY_OUTCOME: set(),
            SECONDARY_OUTCOME: set(),
        },
    }
    writer: pq.ParquetWriter | None = None
    pieces: list[pa.RecordBatch] = []
    buffered_rows = 0
    written_rows = 0
    started = time.perf_counter()

    try:
        writer = pq.ParquetWriter(
            destination,
            PROCESSED_SCHEMA,
            compression=WRITER_SETTINGS["compression"],
            use_dictionary=WRITER_SETTINGS["use_dictionary"],
            write_statistics=WRITER_SETTINGS["write_statistics"],
            data_page_version=WRITER_SETTINGS["data_page_version"],
            version=WRITER_SETTINGS["version"],
        )
        for source_batch in reader:
            remaining_total = None if row_limit is None else row_limit - written_rows - buffered_rows
            if remaining_total is not None and remaining_total <= 0:
                break
            if remaining_total is not None and source_batch.num_rows > remaining_total:
                source_batch = source_batch.slice(0, remaining_total)
            _validate_raw_batch(source_batch, stats)
            raw_hasher.update(source_batch)

            augmented = _augment_with_source_ids(
                source_batch,
                offset=written_rows + buffered_rows,
            )
            start = 0
            while start < augmented.num_rows:
                needed = ROW_GROUP_SIZE - buffered_rows
                piece = augmented.slice(start, min(needed, augmented.num_rows - start))
                pieces.append(piece)
                buffered_rows += piece.num_rows
                start += piece.num_rows
                if buffered_rows == ROW_GROUP_SIZE:
                    _flush_row_group(writer, pieces)
                    written_rows += buffered_rows
                    pieces = []
                    buffered_rows = 0
        if pieces:
            _flush_row_group(writer, pieces)
            written_rows += buffered_rows
            pieces = []
            buffered_rows = 0
    except Exception:
        if writer is not None:
            writer.close()
        destination.unlink(missing_ok=True)
        raise
    else:
        writer.close()

    if row_limit is not None and written_rows != row_limit:
        destination.unlink(missing_ok=True)
        raise DataContractError(
            f"Source ended before requested prefix: requested {row_limit}, observed {written_rows}"
        )
    if written_rows == 0:
        destination.unlink(missing_ok=True)
        raise DataContractError("Conversion produced an empty artifact")

    return {
        "rows": written_rows,
        "raw_semantics": raw_hasher.result(),
        "null_counts": stats["null_counts"],
        "binary_support": {
            key: sorted(value) for key, value in stats["binary_support"].items()
        },
        "writer_settings": WRITER_SETTINGS,
        "elapsed_seconds": time.perf_counter() - started,
        "file_size_bytes": destination.stat().st_size,
        "file_sha256": sha256_file(destination),
    }


def validate_processed_parquet(
    path: Path,
    *,
    expected_rows: int,
    expected_raw_semantics: dict[str, Any],
) -> dict[str, Any]:
    """Validate layout, row identity, precision, order, and semantic equality."""

    if not path.is_file():
        raise FileNotFoundError(path)
    parquet_file = pq.ParquetFile(path)
    schema = parquet_file.schema_arrow.remove_metadata()
    if not schema.equals(PROCESSED_SCHEMA, check_metadata=False):
        raise DataContractError(f"Processed schema differs from contract: {schema}")
    if parquet_file.metadata.num_rows != expected_rows:
        raise DataContractError(
            f"Processed row count mismatch: expected {expected_rows}, "
            f"observed {parquet_file.metadata.num_rows}"
        )

    row_group_rows = [
        parquet_file.metadata.row_group(index).num_rows
        for index in range(parquet_file.metadata.num_row_groups)
    ]
    expected_groups = [ROW_GROUP_SIZE] * (expected_rows // ROW_GROUP_SIZE)
    if expected_rows % ROW_GROUP_SIZE:
        expected_groups.append(expected_rows % ROW_GROUP_SIZE)
    if row_group_rows != expected_groups:
        raise DataContractError(
            f"Row-group layout mismatch: expected {expected_groups}, observed {row_group_rows}"
        )

    compressions = sorted(
        {
            parquet_file.metadata.row_group(group).column(column).compression.lower()
            for group in range(parquet_file.metadata.num_row_groups)
            for column in range(parquet_file.metadata.num_columns)
        }
    )
    if compressions != ["zstd"]:
        raise DataContractError(f"Expected only ZSTD compression, observed {compressions}")

    processed_hasher = SemanticHasher(RAW_SCHEMA)
    next_source_id = 0
    scanner = pads.dataset(path, format="parquet").scanner(
        columns=list(PROCESSED_COLUMNS),
        batch_size=SCAN_BATCH_SIZE,
        use_threads=True,
    )
    for batch in scanner.to_batches():
        ids = batch.column(batch.schema.get_field_index(SOURCE_ROW_ID)).to_numpy(
            zero_copy_only=False
        )
        expected_ids = np.arange(next_source_id, next_source_id + batch.num_rows, dtype=np.int64)
        if not np.array_equal(ids, expected_ids):
            raise DataContractError(
                f"Source-row ordinal mismatch beginning at processed offset {next_source_id}"
            )
        next_source_id += batch.num_rows
        processed_hasher.update(batch.select(list(RAW_COLUMNS)))

    processed_semantics = processed_hasher.result()
    semantic_identity = processed_semantics == expected_raw_semantics
    if not semantic_identity:
        raise DataContractError("Processed values/order/null masks differ from parsed raw source")

    return {
        "status": "PASS",
        "rows": expected_rows,
        "columns": list(PROCESSED_COLUMNS),
        "schema": str(schema),
        "feature_dtypes": {name: str(schema.field(name).type) for name in FEATURE_COLUMNS},
        "float64_preserved": all(
            pa.types.is_float64(schema.field(name).type) for name in FEATURE_COLUMNS
        ),
        "source_row_id": {
            "field": SOURCE_ROW_ID,
            "first": 0,
            "last": expected_rows - 1,
            "complete_unique_ordered": next_source_id == expected_rows,
            "model_feature": SOURCE_ROW_ID in MODEL_FEATURES,
        },
        "row_groups": row_group_rows,
        "compression": compressions,
        "semantic_identity": semantic_identity,
        "semantic_digest": processed_semantics,
        "file_size_bytes": path.stat().st_size,
        "file_sha256": sha256_file(path),
    }


def open_processed_dataset(
    selector: ResolvedSelector,
    *,
    expected_sha256: str | None = None,
) -> pads.Dataset:
    """Open a checksum-pinned processed dataset without materializing it.

    Conversion is the GENERATION path and may begin before a processed checksum
    exists.  This function is the CONSUMPTION boundary: it requires either the
    selector-pinned checksum or the freshly calculated checksum supplied by the
    same successful generation flow, and verifies identity before Arrow opens
    the artifact.
    """

    if not selector.processed_path.is_file():
        raise FileNotFoundError(selector.processed_path)
    selector_sha256 = selector.payload["processed_sha256"]
    if expected_sha256 is not None and not _is_sha256(expected_sha256):
        raise DataContractError("expected_sha256 must be a 64-character SHA-256")
    if (
        selector_sha256 is not None
        and expected_sha256 is not None
        and selector_sha256.lower() != expected_sha256.lower()
    ):
        raise DataContractError(
            "Processed checksum linkage is inconsistent: selector.processed_sha256 "
            f"is {selector_sha256}, but the generation/run evidence supplied "
            f"{expected_sha256}"
        )
    authoritative_sha256 = expected_sha256 or selector_sha256
    if authoritative_sha256 is None:
        raise DataContractError(
            "Processed-data CONSUMPTION requires an authoritative expected SHA-256. "
            "Pin processed_sha256 in the mutable selector from completed run evidence, "
            "or supply the freshly calculated checksum from the same GENERATION flow."
        )
    verify_expected_file_checksum(selector.processed_path, authoritative_sha256)
    dataset = pads.dataset(selector.processed_path, format="parquet")
    if not dataset.schema.remove_metadata().equals(PROCESSED_SCHEMA, check_metadata=False):
        raise DataContractError("Manifest-selected processed dataset violates the schema contract")
    return dataset


def scan_batches(
    dataset: pads.Dataset,
    *,
    columns: Iterable[str],
    batch_size: int = SCAN_BATCH_SIZE,
) -> Iterable[pa.RecordBatch]:
    """Return deterministic projected batches without implicit Pandas conversion."""

    selected = tuple(columns)
    undeclared = sorted(set(selected).difference(PROCESSED_COLUMNS))
    if undeclared:
        raise DataContractError(f"Requested undeclared columns: {undeclared}")
    return dataset.scanner(
        columns=list(selected),
        batch_size=batch_size,
        use_threads=True,
    ).to_batches()


def materialize_pandas(
    dataset: pads.Dataset,
    *,
    columns: Iterable[str],
    row_limit: int | None,
):
    """Explicitly materialize one declared projection/population to Pandas."""

    selected = tuple(columns)
    undeclared = sorted(set(selected).difference(PROCESSED_COLUMNS))
    if undeclared:
        raise DataContractError(f"Requested undeclared columns: {undeclared}")
    scanner = dataset.scanner(
        columns=list(selected),
        batch_size=SCAN_BATCH_SIZE,
        use_threads=True,
    )
    table = scanner.to_table() if row_limit is None else scanner.head(row_limit)
    return table.to_pandas(split_blocks=True, self_destruct=False)


def materialize_pandas_by_source_row_id(
    dataset: pads.Dataset,
    *,
    columns: Iterable[str],
    source_row_ids,
):
    """Materialize ONLY the rows at the given _source_row_id positions.

    _source_row_id is provably identical to the row's positional ordinal in
    the processed parquet file: conversion appends
    ``np.arange(offset, offset + batch.num_rows)`` per batch
    (``_augment_with_source_ids``), and ``validate_processed_parquet``'s
    ordinal-continuity check enforces this as a frozen contract property (see
    ``source_row_id.complete_unique_ordered`` in its result). This function
    therefore uses ``source_row_id`` values directly as
    ``pyarrow.dataset.Dataset.take()`` row positions -- a compact int64
    positional read -- rather than a value-based ``isin`` filter scan and
    rather than any Python ``set``/``list`` of the requested ids. Held-out (or
    any other unrequested) rows are never assembled into a resident,
    Python-visible structure by this call; unrequested row groups a
    fragment-level take can skip are skipped, and within a touched fragment
    only the requested rows are decoded into the returned table.

    Fails closed on duplicate or missing/out-of-range ids -- never silently
    deduplicates or drops rows. Returns rows in ascending source_row_id order
    (this project's established frozen row order).
    """

    selected = tuple(columns)
    undeclared = sorted(set(selected).difference(PROCESSED_COLUMNS))
    if undeclared:
        raise DataContractError(f"Requested undeclared columns: {undeclared}")
    if SOURCE_ROW_ID not in selected:
        raise DataContractError(
            f"materialize_pandas_by_source_row_id requires {SOURCE_ROW_ID!r} in columns"
        )

    indices = np.asarray(source_row_ids, dtype=np.int64)
    if indices.ndim != 1:
        raise DataContractError("source_row_ids must be one-dimensional")
    if indices.size == 0:
        raise DataContractError("source_row_ids must be non-empty")

    sorted_indices = np.sort(indices)
    unique_indices = np.unique(sorted_indices)
    if unique_indices.size != sorted_indices.size:
        duplicate_count = int(sorted_indices.size - unique_indices.size)
        raise DataContractError(
            f"Duplicate source_row_id values in requested set: {duplicate_count} duplicate(s) -- "
            "refusing to silently deduplicate"
        )

    indices_array = pa.array(sorted_indices, type=pa.int64())
    try:
        table = dataset.take(indices_array, columns=list(selected))
    except (pa.lib.ArrowIndexError, IndexError) as exc:
        raise DataContractError(
            f"take() failed on requested source_row_ids -- likely a missing/out-of-range id: {exc}"
        ) from exc

    frame = table.to_pandas(split_blocks=True, self_destruct=False)

    if len(frame) != sorted_indices.size:
        raise DataContractError(
            f"take() row-count mismatch: requested {sorted_indices.size} source_row_ids, got "
            f"{len(frame)} rows -- refusing to silently drop or duplicate rows"
        )
    observed_ids = frame[SOURCE_ROW_ID].to_numpy()
    if not np.array_equal(observed_ids, sorted_indices):
        raise DataContractError(
            "Returned row identity/order does not match the requested sorted source_row_ids -- "
            "frozen row order violated"
        )

    return frame


def assert_model_feature_contract(columns: Iterable[str]) -> None:
    """Fail unless model features are exactly f0 through f11 in order."""

    observed = tuple(columns)
    if observed != MODEL_FEATURES:
        raise DataContractError(
            f"Model features must be exactly {MODEL_FEATURES}, observed {observed}"
        )
    overlap = sorted(set(observed).intersection(FORBIDDEN_MODEL_COLUMNS))
    if overlap:
        raise DataContractError(f"Forbidden variables entered X: {overlap}")


def promote_processed_with_rollback(
    candidate: Path,
    target: Path,
    *,
    expected_sha256: str,
) -> dict[str, Any]:
    """Promote a verified candidate with exception rollback and crash detection.

    The two-step backup/replacement sequence is not a true crash-atomic
    filesystem replacement.  A backup left by an abrupt prior interruption is
    never discarded or guessed at: promotion fails closed with recovery
    instructions before changing either path.
    """

    if sha256_file(candidate) != expected_sha256:
        raise DataContractError("Candidate hash changed before promotion")
    target.parent.mkdir(parents=True, exist_ok=True)
    backup = target.with_name(target.name + ".previous.tmp")
    if backup.exists():
        if target.exists():
            state = "both the canonical target and rollback backup exist"
        else:
            state = "the canonical target is missing while its rollback backup exists"
        raise DataContractError(
            f"Interrupted or ambiguous prior promotion: {state}. "
            f"No files were changed. Validate {backup} against its recorded identity "
            "and restore it explicitly, or resolve the ambiguity before retrying."
        )
    prior = None
    if target.exists():
        prior = {
            "size_bytes": target.stat().st_size,
            "sha256": sha256_file(target),
        }
        os.replace(target, backup)
    try:
        os.replace(candidate, target)
        observed = sha256_file(target)
        if observed != expected_sha256:
            raise DataContractError("Promoted processed artifact hash differs from candidate")
    except Exception:
        target.unlink(missing_ok=True)
        if backup.exists():
            os.replace(backup, target)
        raise
    else:
        backup.unlink(missing_ok=True)
    return {
        "status": "PASS",
        "promotion_safety": "ROLLBACK_PROTECTED_NOT_CRASH_ATOMIC",
        "prior_derivative": prior,
        "processed_sha256": expected_sha256,
        "processed_size_bytes": target.stat().st_size,
    }


def _run_is_complete(run_root: Path) -> bool:
    manifest = run_root / "audit" / "artifact_manifest.json"
    if not manifest.is_file():
        return False
    try:
        status = json.loads(manifest.read_text(encoding="utf-8")).get("status")
    except (OSError, json.JSONDecodeError):
        return True
    return isinstance(status, str) and status.startswith(("COMPLETED", "FAILED"))


def _new_run_artifact_path(run_root: Path, relative_path: str) -> Path:
    """Resolve a new governed artifact path and fail closed for completed runs."""

    run_root = run_root.resolve()
    if _run_is_complete(run_root):
        raise DataContractError(f"Completed run is immutable: {run_root}")
    destination = (run_root / relative_path).resolve()
    try:
        destination.relative_to(run_root)
    except ValueError as exc:
        raise DataContractError("Run artifact path escapes the run root") from exc
    destination.parent.mkdir(parents=True, exist_ok=True)
    return destination


def write_bytes_new(run_root: Path, relative_path: str, payload: bytes) -> Path:
    """Write bytes once while refusing completed-run or overwrite mutation."""

    destination = _new_run_artifact_path(run_root, relative_path)
    with destination.open("xb") as handle:
        handle.write(payload)
    return destination


def write_text_new(run_root: Path, relative_path: str, payload: str) -> Path:
    """Write UTF-8 text once under the governed run-artifact contract."""

    return write_bytes_new(run_root, relative_path, payload.encode("utf-8"))


def write_json_new(run_root: Path, relative_path: str, payload: Any) -> Path:
    """Write JSON once under the governed run-artifact contract."""

    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    return write_text_new(run_root, relative_path, text)


def write_bytes_new_atomic(run_root: Path, relative_path: str, payload: bytes) -> tuple[Path, str]:
    """Write bytes crash-safely for large artifacts and return (path, sha256).

    ``write_bytes_new`` opens the destination path directly under exclusive
    create, so a crash mid-write leaves a truncated file sitting at the real
    artifact path. This variant instead writes to a ``.tmp`` sibling in the
    same directory, ``flush()``+``fsync()``s it, and only then performs a
    single atomic ``os.replace`` onto the destination -- the destination path
    never observably exists in a partially-written state. Intended for large,
    expensive-to-regenerate artifacts (serialized models, persisted
    predictions) where a checkpoint must be able to trust that a hash taken
    after this call reflects a complete file.
    """

    destination = _new_run_artifact_path(run_root, relative_path)
    if destination.exists():
        raise FileExistsError(destination)
    temporary_path = destination.with_name(destination.name + ".tmp")
    if temporary_path.exists():
        raise DataContractError(f"Stale temporary artifact present: {temporary_path}")
    with temporary_path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary_path, destination)
    return destination, sha256_file(destination)


def finalize_artifact_manifest(
    run_root: Path,
    *,
    run_id: str,
    external_artifacts: list[dict[str, Any]],
    final_status: str,
    created_at_utc: str,
    stage: str = "development_data_engineering",
    population: str = "canonical_released_rows_or_declared_prefix",
) -> Path:
    """Hash all closed run artifacts and atomically close the run."""

    if not final_status.startswith(("COMPLETED", "FAILED")):
        raise ValueError("final_status must begin with COMPLETED or FAILED")
    if not stage.strip() or not population.strip():
        raise ValueError("stage and population must be non-empty")
    run_root = run_root.resolve()
    audit_dir = run_root / "audit"
    manifest_path = audit_dir / "artifact_manifest.json"
    if manifest_path.exists():
        raise FileExistsError(manifest_path)
    artifacts = []
    for path in sorted(run_root.rglob("*")):
        if not path.is_file() or "temporary" in path.relative_to(run_root).parts:
            continue
        artifacts.append(
            {
                "path": path.relative_to(run_root).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "stage": stage,
                "population": population,
                "status": "PASS",
            }
        )
    payload = {
        "run_id": run_id,
        "status": final_status,
        "created_at_utc": created_at_utc,
        "artifacts": artifacts,
        "external_artifacts": external_artifacts,
    }
    temporary_path = audit_dir / "artifact_manifest.json.tmp"
    with temporary_path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(temporary_path, manifest_path)
    return manifest_path


def copy_file_new(source: Path, destination: Path) -> None:
    """Copy one file while refusing to overwrite the destination."""

    if destination.exists():
        raise FileExistsError(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as source_handle, destination.open("xb") as destination_handle:
        shutil.copyfileobj(source_handle, destination_handle, length=8 * 1024 * 1024)


def implementation_environment() -> dict[str, Any]:
    """Return implementation-level version fields used in run evidence."""

    return {
        "python": sys.version,
        "numpy": np.__version__,
        "pyarrow": pa.__version__,
        "writer_settings": WRITER_SETTINGS,
    }
