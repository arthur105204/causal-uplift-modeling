"""T11 unified Causal Forest stage runner (robustness / gcp_parity / full).

One reusable orchestration path for every NEW T11 stage -- never a separate
ad-hoc script per stage. TRAIN and VALIDATION partitions are loaded
independently via ``src.data.materialize_pandas_by_source_row_id`` and never
coexist as one whole-population frame: TRAIN is loaded, used to fit, and
freed before VALIDATION is loaded to predict. Held-out rows are never
requested by this module.

Progress is recorded as append-only, hash-chained checkpoints
(``audit/checkpoints/NNN_name.json``) rather than one mutated file, so a
crash can resume from the highest valid checkpoint instead of repeating
already-completed, potentially expensive work. ``audit/run_config.json`` is
written exactly once, before fitting, and is never touched again; output
hashes live only in checkpoints and the final ``artifact_manifest.json``.

This module never reads held-out data and never selects a "best" seed --
that judgement, and all statistical narrative, stays in the notebook
(CLAUDE.md "Notebook-first, not notebook-only"). It produces governed
evidence artifacts only: a serialized model, persisted validation
predictions, and a bounded diagnostic-support summary.
"""

from __future__ import annotations

import json
import os
import pickle
import platform
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.dataset as pads
import pyarrow.parquet as pq
from sklearn.model_selection import train_test_split

from src.causal_forest_baseline import (
    FROZEN_CAUSAL_FOREST_CONFIG,
    FROZEN_ECONML_VERSION,
    FittedCausalForest,
    aggregate_jacobian_support,
    config_hash as causal_forest_config_hash,
    fit_causal_forest,
    predict_tau,
)
from src.data import (
    DataContractError,
    FEATURE_COLUMNS,
    PRIMARY_OUTCOME,
    SOURCE_ROW_ID,
    TREATMENT_COLUMN,
    finalize_artifact_manifest,
    materialize_pandas_by_source_row_id,
    sha256_file,
    write_bytes_new_atomic,
    write_json_new,
)

STAGES = ("smoke", "robustness", "gcp_parity", "full")

CHECKPOINT_STARTED = "001_started"
CHECKPOINT_MODEL_SERIALIZED = "002_model_serialized"
CHECKPOINT_PREDICTIONS_PERSISTED = "003_predictions_persisted"
CHECKPOINT_FINALIZED = "004_finalized"
CHECKPOINT_SEQUENCE = (
    CHECKPOINT_STARTED,
    CHECKPOINT_MODEL_SERIALIZED,
    CHECKPOINT_PREDICTIONS_PERSISTED,
    CHECKPOINT_FINALIZED,
)

MODEL_ARTIFACT_RELATIVE_PATH = "models/causal_forest.pkl"
PREDICTIONS_ARTIFACT_RELATIVE_PATH = "predictions/validation_tau.parquet"
DIAGNOSTIC_SUMMARY_RELATIVE_PATH = "audit/diagnostic_support_summary.json"
RESOURCE_EVIDENCE_RELATIVE_PATH = "audit/resource_evidence.json"
RUN_CONFIG_RELATIVE_PATH = "audit/run_config.json"
RELOAD_CHECK_SAMPLE_SIZE = 512


class CausalForestRunnerError(DataContractError):
    """Raised for T11 runner orchestration/identity violations."""


@dataclass(frozen=True)
class StageRequest:
    """Fully-specified inputs for one T11 stage execution.

    ``train_ids``/``validation_ids`` are the frozen T05 split's
    ``_source_row_id`` arrays for their respective partitions (see
    ``src.split.SplitDataset``) -- this module never derives them itself and
    never touches held-out identities. ``population_size`` is the number of
    TRAIN rows actually fit on: pass ``len(train_ids)`` for the FULL stage
    (no subsampling), or a smaller bounded count for robustness/gcp_parity,
    which triggers a joint-(T,Y)-stratified draw seeded by ``sampling_seed``
    (D31).
    """

    stage: str
    run_id: str
    run_root: Path
    dataset: pads.Dataset
    dataset_sha256: str
    train_ids: np.ndarray
    validation_ids: np.ndarray
    population_size: int
    sampling_seed: int
    model_seed: int
    diagnostic_sample_size: int
    config: dict[str, object] | None = None

    def __post_init__(self) -> None:
        if self.stage not in STAGES:
            raise CausalForestRunnerError(f"Unknown stage {self.stage!r}; must be one of {STAGES}")
        if self.population_size <= 0:
            raise CausalForestRunnerError("population_size must be positive")
        if self.population_size > len(self.train_ids):
            raise CausalForestRunnerError(
                f"population_size ({self.population_size}) exceeds available TRAIN ids "
                f"({len(self.train_ids)})"
            )
        if len(self.validation_ids) == 0:
            raise CausalForestRunnerError("validation_ids must be non-empty")
        if self.diagnostic_sample_size <= 0 or self.diagnostic_sample_size > len(self.validation_ids):
            raise CausalForestRunnerError(
                "diagnostic_sample_size must be positive and at most len(validation_ids)"
            )
        overlap = np.intersect1d(
            np.asarray(self.train_ids, dtype=np.int64),
            np.asarray(self.validation_ids, dtype=np.int64),
            assume_unique=False,
        )
        if overlap.size:
            raise CausalForestRunnerError(
                f"train_ids and validation_ids are not disjoint: {overlap.size} shared id(s)"
            )


def _ids_identity(ids: np.ndarray) -> dict[str, Any]:
    """A compact, order-independent identity for a (possibly huge) id array.

    Never stores the raw ids in checkpoint/config JSON -- only a count and a
    sha256 digest of the sorted, newline-joined decimal ids.
    """

    sorted_ids = np.sort(np.asarray(ids, dtype=np.int64))
    digest_source = "\n".join(str(int(value)) for value in sorted_ids).encode("utf-8")
    import hashlib

    return {"count": int(sorted_ids.size), "sha256": hashlib.sha256(digest_source).hexdigest()}


def modeling_environment() -> dict[str, Any]:
    """Environment fields for the GCP parity contract.

    ``hard_match`` fields must be identical between the local reference run
    and any GCP execution of the same stage/config. ``recorded_not_gated``
    fields are captured for the record but never block parity -- platform,
    CPU, and BLAS/OpenMP backend differences are expected and permitted.
    """

    import econml
    import sklearn

    hard_match = {
        "python": sys.version,
        "econml": econml.__version__,
        "scikit_learn": sklearn.__version__,
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "pyarrow": pa.__version__,
    }
    if econml.__version__ != FROZEN_ECONML_VERSION:
        raise CausalForestRunnerError(
            f"Installed econml {econml.__version__} does not match the frozen T10 version "
            f"{FROZEN_ECONML_VERSION}"
        )

    try:
        blas_summary = _numpy_blas_summary()
    except Exception as exc:  # best-effort diagnostic only, never gates
        blas_summary = f"unavailable: {exc}"

    recorded_not_gated = {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "os_name": os.name,
        "numpy_blas": blas_summary,
    }
    return {"hard_match": hard_match, "recorded_not_gated": recorded_not_gated}


def _numpy_blas_summary() -> str:
    try:
        config = np.__config__.show(mode="dicts")
        return json.dumps(config, default=str)
    except TypeError:
        import contextlib
        import io

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            np.__config__.show()
        return buffer.getvalue().strip()


def stratified_subset_ids(
    dataset: pads.Dataset, ids: np.ndarray, *, population_size: int, sampling_seed: int
) -> np.ndarray:
    """Draw exactly ``population_size`` ids, joint-(T,Y)-stratified.

    Works identically for a TRAIN or a VALIDATION id array -- used internally
    by ``_ensure_model_serialized`` to bound the fitted population
    (robustness/gcp_parity/smoke), and by callers (e.g.
    ``scripts/t11_run_stage.py``) to bound SMOKE's validation-scoring
    population the same deterministic way, rather than scoring the complete
    frozen VALIDATION cohort.

    Loads only a bounded 3-column projection (id/treatment/outcome) for the
    candidate ids -- never the full feature set -- to build the
    stratification key, matching the convention in ``src.split._joint_strata``.
    """

    if population_size == len(ids):
        return np.sort(np.asarray(ids, dtype=np.int64))

    strata_frame = materialize_pandas_by_source_row_id(
        dataset,
        columns=[SOURCE_ROW_ID, TREATMENT_COLUMN, PRIMARY_OUTCOME],
        source_row_ids=ids,
    )
    strata_key = (
        strata_frame[TREATMENT_COLUMN].astype(str) + "_" + strata_frame[PRIMARY_OUTCOME].astype(str)
    )
    subset_ids, _ = train_test_split(
        strata_frame[SOURCE_ROW_ID].to_numpy(dtype=np.int64),
        train_size=population_size,
        random_state=sampling_seed,
        stratify=strata_key,
    )
    return np.sort(np.asarray(subset_ids, dtype=np.int64))


def _sample_rss_bytes() -> int | None:
    """Best-effort single RSS snapshot. Never blocks a run if psutil is absent."""

    try:
        import psutil

        return int(psutil.Process().memory_info().rss)
    except Exception:
        return None


class _ResourceSampler:
    """Continuous background process-RSS / host-memory sampler.

    Runs in a daemon thread so it keeps sampling while ``model.fit()`` blocks
    the main thread on native numeric code. Started before the TRAIN
    partition load and stopped in a ``finally`` block (via context-manager
    ``__exit__``) that always runs, even on an exception -- it never leaves
    an orphaned sampler thread. ``peak_rss_bytes`` is the true maximum of
    these continuous samples, distinct from the sparse per-checkpoint
    snapshots recorded elsewhere in this module (which stay as
    ``rss_stage_snapshots`` for reference, but are never labeled ``peak_``).

    Process RSS and host/system memory are always reported as separate
    fields -- this class never conflates the two.
    """

    def __init__(self, interval_seconds: float = 0.5):
        self._interval_seconds = interval_seconds
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self.samples: list[dict[str, Any]] = []

    def _loop(self) -> None:
        try:
            import psutil

            process = psutil.Process()
        except Exception:
            return
        while not self._stop_event.is_set():
            try:
                virtual_memory = psutil.virtual_memory()
                sample = {
                    "t": time.perf_counter(),
                    "rss_bytes": int(process.memory_info().rss),
                    "system_available_bytes": int(virtual_memory.available),
                    "system_percent": float(virtual_memory.percent),
                }
                try:
                    sample["swap_used_bytes"] = int(psutil.swap_memory().used)
                except Exception:
                    sample["swap_used_bytes"] = None
                self.samples.append(sample)
            except Exception:
                pass
            self._stop_event.wait(self._interval_seconds)

    def __enter__(self) -> "_ResourceSampler":
        self._thread = threading.Thread(
            target=self._loop, name="t11-resource-sampler", daemon=True
        )
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=self._interval_seconds * 10)

    def peak_rss_bytes(self) -> int | None:
        values = [s["rss_bytes"] for s in self.samples]
        return max(values) if values else None

    def peak_rss_bytes_between(self, start_t: float, end_t: float) -> int | None:
        values = [s["rss_bytes"] for s in self.samples if start_t <= s["t"] <= end_t]
        return max(values) if values else None

    def min_system_available_bytes(self) -> int | None:
        values = [s["system_available_bytes"] for s in self.samples]
        return min(values) if values else None

    def max_system_percent(self) -> float | None:
        values = [s["system_percent"] for s in self.samples]
        return max(values) if values else None

    def max_swap_used_bytes(self) -> int | None:
        values = [s["swap_used_bytes"] for s in self.samples if s.get("swap_used_bytes") is not None]
        return max(values) if values else None


def _checkpoint_path(run_root: Path, name: str) -> Path:
    return run_root / "audit" / "checkpoints" / f"{name}.json"


def _read_checkpoint_chain(run_root: Path) -> list[dict[str, Any]]:
    """Read existing checkpoints in order, verifying the hash chain.

    Returns an empty list for a fresh run. Raises if a checkpoint is missing
    from the middle of the sequence, or if a recorded prior-checkpoint hash
    does not match the actual preceding file -- both indicate tampering or a
    partially-written state this runner refuses to trust.
    """

    chain: list[dict[str, Any]] = []
    previous_path: Path | None = None
    for name in CHECKPOINT_SEQUENCE:
        path = _checkpoint_path(run_root, name)
        if not path.is_file():
            break
        payload = json.loads(path.read_text(encoding="utf-8"))
        expected_prior_hash = sha256_file(previous_path) if previous_path is not None else None
        if payload.get("prior_checkpoint_sha256") != expected_prior_hash:
            raise CausalForestRunnerError(
                f"Checkpoint {name} hash-chain mismatch -- refusing to resume from an "
                "inconsistent checkpoint history"
            )
        chain.append(payload)
        previous_path = path
    return chain


def _write_checkpoint(run_root: Path, name: str, payload: dict[str, Any]) -> Path:
    checkpoints_dir = run_root / "audit" / "checkpoints"
    index = CHECKPOINT_SEQUENCE.index(name)
    prior_path = (
        _checkpoint_path(run_root, CHECKPOINT_SEQUENCE[index - 1]) if index > 0 else None
    )
    full_payload = {
        "checkpoint_name": name,
        "written_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "prior_checkpoint_sha256": sha256_file(prior_path) if prior_path is not None else None,
        **payload,
    }
    return write_json_new(run_root, f"audit/checkpoints/{name}.json", full_payload)


def write_active_sentinel(sentinel_path: Path, run_id: str) -> Path:
    """Record which run_id is active, outside the governed run root.

    Written atomically (tmp + fsync + rename) so a reader never observes a
    half-written sentinel. A resume script reads this file to discover which
    run_id to continue; it is not part of the immutable run evidence.
    """

    sentinel_path = sentinel_path.resolve()
    sentinel_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = sentinel_path.with_name(sentinel_path.name + ".tmp")
    with temporary_path.open("w", encoding="utf-8") as handle:
        handle.write(run_id)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary_path, sentinel_path)
    return sentinel_path


def run_stage(request: StageRequest) -> dict[str, Any]:
    """Execute (or resume) one T11 stage end-to-end.

    DAG: verify identity -> load TRAIN (partitioned) -> fit -> atomic
    serialize+hash -> checkpoint 002 -> bounded reload check -> free TRAIN
    intermediates -> load VALIDATION (partitioned) -> predict complete
    validation -> atomic persist+hash -> checkpoint 003 -> bounded diagnostic
    sample -> checkpoint 004 -> finalize.
    """

    run_started_perf_counter = time.perf_counter()
    run_root = request.run_root.resolve()
    config = dict(request.config if request.config is not None else FROZEN_CAUSAL_FOREST_CONFIG)
    frozen_config_hash = causal_forest_config_hash({**config, "random_state": request.model_seed})
    train_identity = _ids_identity(request.train_ids)
    validation_identity = _ids_identity(request.validation_ids)

    with _ResourceSampler() as resource_sampler:
        fit_train_ids = stratified_subset_ids(
            request.dataset,
            request.train_ids,
            population_size=request.population_size,
            sampling_seed=request.sampling_seed,
        )
        fit_train_identity = _ids_identity(fit_train_ids)

        chain = _read_checkpoint_chain(run_root)

        run_config_path = run_root / RUN_CONFIG_RELATIVE_PATH
        if chain:
            started = chain[0]
            _verify_resume_identity(
                started,
                request=request,
                config_hash=frozen_config_hash,
                train_identity=train_identity,
                fit_train_identity=fit_train_identity,
                validation_identity=validation_identity,
            )
        else:
            started_payload = {
                "stage": request.stage,
                "run_id": request.run_id,
                "population_size": request.population_size,
                "sampling_seed": request.sampling_seed,
                "model_seed": request.model_seed,
                "diagnostic_sample_size": request.diagnostic_sample_size,
                "dataset_sha256": request.dataset_sha256,
                "train_ids_identity": train_identity,
                "fit_train_ids_identity": fit_train_identity,
                "validation_ids_identity": validation_identity,
                "frozen_config": config,
                "config_hash": frozen_config_hash,
                "econml_version": FROZEN_ECONML_VERSION,
            }

            if not run_config_path.exists():
                write_json_new(
                    run_root,
                    RUN_CONFIG_RELATIVE_PATH,
                    started_payload,
                )

            _write_checkpoint(
                run_root,
                CHECKPOINT_STARTED,
                {
                    **started_payload,
                    "rss_bytes_at_checkpoint": _sample_rss_bytes(),
                },
            )
            chain = _read_checkpoint_chain(run_root)

        fitted = _ensure_model_serialized(
            request,
            run_root,
            config,
            frozen_config_hash,
            chain,
            fit_train_ids=fit_train_ids,
            resource_sampler=resource_sampler,
        )
        chain = _read_checkpoint_chain(run_root)

        predictions_path = _ensure_predictions_persisted(
            request,
            run_root,
            fitted,
            chain,
        )
        chain = _read_checkpoint_chain(run_root)

        summary = _ensure_finalized(
            request,
            run_root,
            fitted,
            predictions_path,
            chain,
            run_started_perf_counter=run_started_perf_counter,
            resource_sampler=resource_sampler,
        )

    return {
        "run_id": request.run_id,
        "stage": request.stage,
        "run_root": str(run_root),
        "checkpoints": [
            c["checkpoint_name"]
            for c in _read_checkpoint_chain(run_root)
        ],
        "diagnostic_summary": summary,
    }


def _verify_resume_identity(
    started: dict[str, Any],
    *,
    request: StageRequest,
    config_hash: str,
    train_identity: dict[str, Any],
    fit_train_identity= dict[str, Any],
    validation_identity: dict[str, Any],
) -> None:
    mismatches = []
    if started.get("stage") != request.stage:
        mismatches.append("stage")
    if started.get("run_id") != request.run_id:
        mismatches.append("run_id")
    if started.get("population_size") != request.population_size:
        mismatches.append("population_size")
    if started.get("sampling_seed") != request.sampling_seed:
        mismatches.append("sampling_seed")
    if started.get("model_seed") != request.model_seed:
        mismatches.append("model_seed")
    if started.get("dataset_sha256") != request.dataset_sha256:
        mismatches.append("dataset_sha256")
    if started.get("config_hash") != config_hash:
        mismatches.append("config_hash")
    if started.get("train_ids_identity") != train_identity:
        mismatches.append("train_ids_identity")

    if started.get("fit_train_ids_identity") != fit_train_identity:
        mismatches.append("fit_train_ids_identity")

    if started.get("validation_ids_identity") != validation_identity:
        mismatches.append("validation_ids_identity")
    if mismatches:
        raise CausalForestRunnerError(
            f"Resume identity mismatch against checkpoint 001 for fields: {mismatches} -- "
            "refusing to resume a run under different parameters"
        )


def _ensure_model_serialized(
    request: StageRequest,
    run_root: Path,
    config: dict[str, object],
    frozen_config_hash: str,
    chain: list[dict[str, Any]],
    fit_train_ids: np.ndarray,
    resource_sampler: "_ResourceSampler | None" = None,
) -> FittedCausalForest:
    model_path = run_root / MODEL_ARTIFACT_RELATIVE_PATH
    if len(chain) >= 2:
        return pickle.loads(model_path.read_bytes())

    rss_timeline: dict[str, int | None] = {"before_train_load": _sample_rss_bytes()}

    train_frame = materialize_pandas_by_source_row_id(
        request.dataset,
        columns=[SOURCE_ROW_ID, *FEATURE_COLUMNS, TREATMENT_COLUMN, PRIMARY_OUTCOME],
        source_row_ids=fit_train_ids,
    )
    rss_timeline["after_train_load"] = _sample_rss_bytes()
    rss_timeline["immediately_before_fit"] = _sample_rss_bytes()

    fit_started = time.perf_counter()
    fitted = fit_causal_forest(
        X=train_frame[list(FEATURE_COLUMNS)],
        T=train_frame[TREATMENT_COLUMN],
        Y=train_frame[PRIMARY_OUTCOME],
        config=config,
        seed=request.model_seed,
    )
    fit_wall_seconds = time.perf_counter() - fit_started
    rss_timeline["immediately_after_fit"] = _sample_rss_bytes()
    peak_rss_during_fit_bytes = (
        resource_sampler.peak_rss_bytes_between(fit_started, fit_started + fit_wall_seconds)
        if resource_sampler is not None
        else None
    )

    serialization_started = time.perf_counter()
    model_bytes = pickle.dumps(fitted)
    _, model_sha256 = write_bytes_new_atomic(run_root, MODEL_ARTIFACT_RELATIVE_PATH, model_bytes)
    rss_timeline["after_serialization"] = _sample_rss_bytes()

    reload_sample = train_frame[list(FEATURE_COLUMNS)].head(RELOAD_CHECK_SAMPLE_SIZE)
    reloaded = pickle.loads(model_path.read_bytes())
    original_tau = predict_tau(fitted, reload_sample)
    reloaded_tau = predict_tau(reloaded, reload_sample)
    reload_matches = bool(np.array_equal(original_tau, reloaded_tau))
    serialization_reload_wall_seconds = time.perf_counter() - serialization_started
    if not reload_matches:
        raise CausalForestRunnerError(
            "Serialized-model reload check failed: reloaded predictions differ from the "
            "in-memory fitted model on a bounded sample"
        )

    actual_train_rows = int(len(train_frame))
    del train_frame
    rss_timeline["after_train_cleanup"] = _sample_rss_bytes()

    _write_checkpoint(
        run_root,
        CHECKPOINT_MODEL_SERIALIZED,
        {
            "model_artifact_path": MODEL_ARTIFACT_RELATIVE_PATH,
            "model_sha256": model_sha256,
            "config_hash": frozen_config_hash,
            "actual_train_rows": actual_train_rows,
            "fit_wall_seconds": fit_wall_seconds,
            "serialization_reload_wall_seconds": serialization_reload_wall_seconds,
            "rss_bytes_at_checkpoint": rss_timeline["after_train_cleanup"],
            "rss_timeline": rss_timeline,
            "peak_rss_during_fit_bytes": peak_rss_during_fit_bytes,
            "reload_verification": {
                "sample_size": int(len(reload_sample)),
                "predictions_match": reload_matches,
            },
        },
    )

    return fitted


def _ensure_predictions_persisted(
    request: StageRequest,
    run_root: Path,
    fitted: FittedCausalForest,
    chain: list[dict[str, Any]],
) -> Path:
    predictions_path = run_root / PREDICTIONS_ARTIFACT_RELATIVE_PATH
    if len(chain) >= 3:
        return predictions_path

    validation_frame = materialize_pandas_by_source_row_id(
        request.dataset,
        columns=[SOURCE_ROW_ID, *FEATURE_COLUMNS],
        source_row_ids=request.validation_ids,
    )
    predict_started = time.perf_counter()
    tau = predict_tau(fitted, validation_frame[list(FEATURE_COLUMNS)])
    predict_wall_seconds = time.perf_counter() - predict_started

    persist_started = time.perf_counter()
    predictions_table = pa.table(
        {
            SOURCE_ROW_ID: pa.array(validation_frame[SOURCE_ROW_ID].to_numpy(dtype=np.int64)),
            "tau": pa.array(np.asarray(tau, dtype=np.float64)),
        }
    )
    import io

    buffer = io.BytesIO()
    pq.write_table(predictions_table, buffer, compression="zstd")
    _, predictions_sha256 = write_bytes_new_atomic(
        run_root, PREDICTIONS_ARTIFACT_RELATIVE_PATH, buffer.getvalue()
    )
    persist_wall_seconds = time.perf_counter() - persist_started

    _write_checkpoint(
        run_root,
        CHECKPOINT_PREDICTIONS_PERSISTED,
        {
            "predictions_artifact_path": PREDICTIONS_ARTIFACT_RELATIVE_PATH,
            "predictions_sha256": predictions_sha256,
            "predicted_rows": int(len(validation_frame)),
            "predict_wall_seconds": predict_wall_seconds,
            "persist_wall_seconds": persist_wall_seconds,
            "rss_bytes_at_checkpoint": _sample_rss_bytes(),
        },
    )
    del validation_frame
    return predictions_path


def _write_resource_evidence(
    run_root: Path,
    request: StageRequest,
    *,
    run_started_perf_counter: float,
    resource_sampler: "_ResourceSampler | None",
) -> None:
    """Record model/prediction artifact sizes, disk footprint, timings, RSS,
    and host-memory pressure.

    D31 requires capturing this evidence during the 500K robustness runs so
    the FULL-stage disk preflight can be frozen from real measurements rather
    than an assumed number. Best-effort: a missing ``psutil`` (or a missing
    ``resource_sampler``, e.g. in a unit test that calls this directly) never
    blocks a run, it only omits the affected fields.

    RSS naming discipline: ``peak_rss_bytes`` is the true maximum observed by
    the continuous background ``_ResourceSampler`` (0.5s interval, spanning
    TRAIN load through finalize) -- never a single snapshot. The sparse
    per-checkpoint snapshots this module also records (started/
    model_serialized/predictions_persisted/finalize) are reported separately
    as ``rss_stage_snapshots`` and never relabeled as a peak. Host-level
    memory pressure (available RAM, percent used, swap) is reported under its
    own ``system_*``/``swap_*`` fields -- process RSS is never conflated with
    system memory.
    """

    model_path = run_root / MODEL_ARTIFACT_RELATIVE_PATH
    predictions_path = run_root / PREDICTIONS_ARTIFACT_RELATIVE_PATH
    run_root_disk_usage_bytes = sum(
        path.stat().st_size for path in run_root.rglob("*") if path.is_file()
    )

    chain = _read_checkpoint_chain(run_root)
    rss_stage_snapshots = [
        {"checkpoint": entry["checkpoint_name"], "rss_bytes": entry.get("rss_bytes_at_checkpoint")}
        for entry in chain
        if entry.get("rss_bytes_at_checkpoint") is not None
    ]
    rss_bytes_at_finalize = _sample_rss_bytes()
    if rss_bytes_at_finalize is not None:
        rss_stage_snapshots.append({"checkpoint": "finalize", "rss_bytes": rss_bytes_at_finalize})

    model_serialized_checkpoint = next(
        (c for c in chain if c["checkpoint_name"] == CHECKPOINT_MODEL_SERIALIZED), {}
    )
    predictions_checkpoint = next(
        (c for c in chain if c["checkpoint_name"] == CHECKPOINT_PREDICTIONS_PERSISTED), {}
    )
    fit_wall_seconds = model_serialized_checkpoint.get("fit_wall_seconds")
    serialization_reload_wall_seconds = model_serialized_checkpoint.get(
        "serialization_reload_wall_seconds"
    )
    rss_timeline = model_serialized_checkpoint.get("rss_timeline")
    peak_rss_during_fit_bytes = model_serialized_checkpoint.get("peak_rss_during_fit_bytes")
    predict_wall_seconds = predictions_checkpoint.get("predict_wall_seconds")
    persist_wall_seconds = predictions_checkpoint.get("persist_wall_seconds")
    predicted_rows = predictions_checkpoint.get("predicted_rows")
    prediction_throughput_rows_per_second = (
        predicted_rows / predict_wall_seconds
        if predicted_rows and predict_wall_seconds
        else None
    )

    if resource_sampler is not None:
        peak_rss_bytes = resource_sampler.peak_rss_bytes()
        continuous_sample_count = len(resource_sampler.samples)
        system_memory_available_bytes_min = resource_sampler.min_system_available_bytes()
        system_memory_percent_max = resource_sampler.max_system_percent()
        swap_used_bytes_max = resource_sampler.max_swap_used_bytes()
    else:
        peak_rss_bytes = None
        continuous_sample_count = 0
        system_memory_available_bytes_min = None
        system_memory_percent_max = None
        swap_used_bytes_max = None
    # A live sample is always a valid lower bound on the true peak, even if
    # the continuous sampler produced no samples (e.g. a near-instant stage).
    if rss_bytes_at_finalize is not None:
        peak_rss_bytes = max(peak_rss_bytes, rss_bytes_at_finalize) if peak_rss_bytes is not None else rss_bytes_at_finalize

    payload = {
        "stage": request.stage,
        "population_size": request.population_size,
        "model_artifact_size_bytes": model_path.stat().st_size if model_path.is_file() else None,
        "predictions_artifact_size_bytes": (
            predictions_path.stat().st_size if predictions_path.is_file() else None
        ),
        "run_root_disk_usage_bytes_at_finalize": run_root_disk_usage_bytes,
        "total_wall_seconds": time.perf_counter() - run_started_perf_counter,
        "fit_wall_seconds": fit_wall_seconds,
        "predict_wall_seconds": predict_wall_seconds,
        "serialization_reload_wall_seconds": serialization_reload_wall_seconds,
        "persist_wall_seconds": persist_wall_seconds,
        "prediction_throughput_rows_per_second": prediction_throughput_rows_per_second,
        "rss_bytes_at_finalize": rss_bytes_at_finalize,
        "peak_rss_bytes": peak_rss_bytes,
        "peak_rss_bytes_method": (
            "true maximum observed by a continuous background sampler (0.5s interval) spanning "
            "TRAIN load through finalize -- not a sparse snapshot max"
        ),
        "peak_rss_during_fit_bytes": peak_rss_during_fit_bytes,
        "continuous_sampler_sample_count": continuous_sample_count,
        "rss_timeline": rss_timeline,
        "rss_stage_snapshots": rss_stage_snapshots,
        "system_memory_available_bytes_min": system_memory_available_bytes_min,
        "system_memory_percent_max": system_memory_percent_max,
        "swap_used_bytes_max": swap_used_bytes_max,
    }
    write_json_new(run_root, RESOURCE_EVIDENCE_RELATIVE_PATH, payload)


def _ensure_finalized(
    request: StageRequest,
    run_root: Path,
    fitted: FittedCausalForest,
    predictions_path: Path,
    chain: list[dict[str, Any]],
    *,
    run_started_perf_counter: float,
    resource_sampler: "_ResourceSampler | None" = None,
) -> dict[str, Any]:
    summary_path = run_root / DIAGNOSTIC_SUMMARY_RELATIVE_PATH
    if len(chain) >= 4:
        return json.loads(summary_path.read_text(encoding="utf-8"))

    rng = np.random.default_rng(request.sampling_seed)
    audit_ids = rng.choice(
        request.validation_ids, size=request.diagnostic_sample_size, replace=False
    )
    audit_frame = materialize_pandas_by_source_row_id(
        request.dataset,
        columns=[SOURCE_ROW_ID, *FEATURE_COLUMNS],
        source_row_ids=audit_ids,
    )
    support = aggregate_jacobian_support(fitted, audit_frame[list(FEATURE_COLUMNS)])
    summary_payload = {
        "n_queries": support.n_queries,
        "full_rank_dimension": support.full_rank_dimension,
        "alpha_all_finite": support.alpha_all_finite,
        "jac_all_finite": support.jac_all_finite,
        "tau_all_finite": support.tau_all_finite,
        "jac_full_rank_fraction": support.jac_full_rank_fraction,
        "all_full_rank": support.all_full_rank,
        "passed": support.passed,
        "condition_number_distribution": support.condition_number_distribution,
    }
    write_json_new(run_root, DIAGNOSTIC_SUMMARY_RELATIVE_PATH, summary_payload)
    _write_resource_evidence(
        run_root,
        request,
        run_started_perf_counter=run_started_perf_counter,
        resource_sampler=resource_sampler,
    )

    _write_checkpoint(
        run_root,
        CHECKPOINT_FINALIZED,
        {
            "diagnostic_summary_path": DIAGNOSTIC_SUMMARY_RELATIVE_PATH,
            "diagnostic_passed": support.passed,
        },
    )

    final_status = "COMPLETED_PASS" if support.passed else "COMPLETED_FAIL"
    finalize_artifact_manifest(
        run_root,
        run_id=request.run_id,
        external_artifacts=[],
        final_status=final_status,
        created_at_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        stage=f"t11_causal_forest_{request.stage}",
        population="frozen_t05_train_subset_fit_and_complete_validation_scored",
    )
    return summary_payload
