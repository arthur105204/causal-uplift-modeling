"""Synthetic-fixture tests for src/causal_forest_runner.py (T11).

No real data. These check orchestration mechanics only -- checkpoint
hash-chaining, resume/recovery without refitting, resume-identity
enforcement, atomic-artifact persistence, and deterministic reproduction --
against tiny synthetic fixtures. The governed real-data T11 stages run
elsewhere (scripts/t11_run_stage.py against the frozen T05 split), never here.
"""

from __future__ import annotations

import json
import pickle
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.dataset as pads
import pytest

import src.causal_forest_runner as causal_forest_runner
from src.causal_forest_baseline import (
    CausalForestRepresentationError,
    FROZEN_CAUSAL_FOREST_CONFIG,
    FROZEN_ECONML_VERSION,
)
from src.causal_forest_runner import (
    CHECKPOINT_SEQUENCE,
    CausalForestRunnerError,
    StageRequest,
    _ids_identity,
    _read_checkpoint_chain,
    stratified_subset_ids,
    modeling_environment,
    run_stage,
    write_active_sentinel,
)
from src.data import (
    FEATURE_COLUMNS,
    PRIMARY_OUTCOME,
    SOURCE_ROW_ID,
    TREATMENT_COLUMN,
    convert_csv_to_parquet,
    sha256_file,
)

SMALL_CONFIG = {**FROZEN_CAUSAL_FOREST_CONFIG, "n_estimators": 8}  # divisible by subforest_size=4

# D32: fit_causal_forest() now fails closed on raw, unencoded CRITEO categorical
# token columns (f1/f3/f4/f5/f6/f8/f9/f11). src.causal_forest_runner passes
# `src.data.FEATURE_COLUMNS` -- the real, contract-required raw column set --
# straight into fit_causal_forest(), so any test that exercises a full
# run_stage() fit is now genuinely blocked until an explicit CausalForest
# representation ADR is accepted and the runner is updated to encode its
# feature frame accordingly (docs/adr/ADR-CF-implementation.md). These tests
# are skipped, not weakened or deleted, pending that ADR; see
# test_run_stage_fails_closed_on_raw_categorical_representation below for the
# corresponding "it blocks correctly" coverage.
CF_REPRESENTATION_BLOCKED_REASON = (
    "T11 CausalForest fit path blocked pending the CausalForest categorical "
    "representation ADR (D32; docs/adr/ADR-CF-implementation.md) -- "
    "src.causal_forest_runner passes raw FEATURE_COLUMNS directly, which "
    "fit_causal_forest() now rejects by design"
)


def _build_dataset(tmp_path: Path, rows: int) -> tuple[pads.Dataset, str]:
    rng = np.random.default_rng(7)
    payload = {name: rng.normal(size=rows) for name in FEATURE_COLUMNS}
    payload["treatment"] = rng.integers(0, 2, size=rows)
    payload["conversion"] = rng.integers(0, 2, size=rows)
    payload["visit"] = rng.integers(0, 2, size=rows)
    payload["exposure"] = rng.integers(0, 2, size=rows)
    frame = pd.DataFrame(payload)
    raw = tmp_path / "runner_source.csv"
    raw.write_text(frame.to_csv(index=False), encoding="utf-8")
    processed = tmp_path / "runner_processed.parquet"
    result = convert_csv_to_parquet(raw, processed, row_limit=None)
    return pads.dataset(processed, format="parquet"), result["file_sha256"]


def _make_request(
    tmp_path: Path,
    dataset: pads.Dataset,
    dataset_sha256: str,
    *,
    run_id: str,
    train_ids: np.ndarray,
    validation_ids: np.ndarray,
    population_size: int,
    diagnostic_sample_size: int = 20,
    sampling_seed: int = 42,
    model_seed: int = 42,
) -> StageRequest:
    return StageRequest(
        stage="robustness",
        run_id=run_id,
        run_root=tmp_path / "runs" / run_id,
        dataset=dataset,
        dataset_sha256=dataset_sha256,
        train_ids=train_ids,
        validation_ids=validation_ids,
        population_size=population_size,
        sampling_seed=sampling_seed,
        model_seed=model_seed,
        diagnostic_sample_size=diagnostic_sample_size,
        config=SMALL_CONFIG,
    )


@pytest.fixture
def small_dataset(tmp_path: Path) -> tuple[pads.Dataset, str, np.ndarray, np.ndarray]:
    dataset, dataset_sha256 = _build_dataset(tmp_path, rows=120)
    train_ids = np.arange(0, 90)
    validation_ids = np.arange(90, 120)
    return dataset, dataset_sha256, train_ids, validation_ids


# --- StageRequest validation --------------------------------------------------


def test_stage_request_rejects_overlapping_train_and_validation_ids(
    tmp_path: Path, small_dataset
) -> None:
    dataset, dataset_sha256, train_ids, validation_ids = small_dataset
    overlapping_validation = np.concatenate([validation_ids, train_ids[:1]])
    with pytest.raises(CausalForestRunnerError, match="not disjoint"):
        _make_request(
            tmp_path,
            dataset,
            dataset_sha256,
            run_id="overlap",
            train_ids=train_ids,
            validation_ids=overlapping_validation,
            population_size=60,
        )


def test_stage_request_rejects_population_size_exceeding_train_ids(
    tmp_path: Path, small_dataset
) -> None:
    dataset, dataset_sha256, train_ids, validation_ids = small_dataset
    with pytest.raises(CausalForestRunnerError, match="population_size"):
        _make_request(
            tmp_path,
            dataset,
            dataset_sha256,
            run_id="oversized",
            train_ids=train_ids,
            validation_ids=validation_ids,
            population_size=len(train_ids) + 1,
        )


def test_stage_request_rejects_out_of_range_diagnostic_sample_size(
    tmp_path: Path, small_dataset
) -> None:
    dataset, dataset_sha256, train_ids, validation_ids = small_dataset
    with pytest.raises(CausalForestRunnerError, match="diagnostic_sample_size"):
        _make_request(
            tmp_path,
            dataset,
            dataset_sha256,
            run_id="bad_diag",
            train_ids=train_ids,
            validation_ids=validation_ids,
            population_size=60,
            diagnostic_sample_size=len(validation_ids) + 1,
        )


def test_stage_request_rejects_unknown_stage(tmp_path: Path, small_dataset) -> None:
    dataset, dataset_sha256, train_ids, validation_ids = small_dataset
    with pytest.raises(CausalForestRunnerError, match="Unknown stage"):
        StageRequest(
            stage="not_a_real_stage",
            run_id="bad_stage",
            run_root=tmp_path / "runs" / "bad_stage",
            dataset=dataset,
            dataset_sha256=dataset_sha256,
            train_ids=train_ids,
            validation_ids=validation_ids,
            population_size=60,
            sampling_seed=42,
            model_seed=42,
            diagnostic_sample_size=10,
            config=SMALL_CONFIG,
        )


# --- _ids_identity -------------------------------------------------------------


def test_ids_identity_is_order_independent() -> None:
    ids = np.arange(50)
    shuffled = np.random.default_rng(1).permutation(ids)
    assert _ids_identity(ids) == _ids_identity(shuffled)


def test_ids_identity_changes_with_membership() -> None:
    first = _ids_identity(np.arange(50))
    second = _ids_identity(np.arange(51))
    assert first != second


# --- stratified_subset_ids ----------------------------------------------


def test_stratified_subset_returns_exact_population_size_and_subset(
    tmp_path: Path, small_dataset
) -> None:
    dataset, _dataset_sha256, train_ids, _validation_ids = small_dataset
    subset = stratified_subset_ids(
        dataset, train_ids, population_size=40, sampling_seed=42
    )
    assert subset.size == 40
    assert set(subset.tolist()).issubset(set(train_ids.tolist()))
    assert list(subset) == sorted(subset.tolist())


def test_stratified_subset_deterministic_for_fixed_seed(tmp_path: Path, small_dataset) -> None:
    dataset, _dataset_sha256, train_ids, _validation_ids = small_dataset
    first = stratified_subset_ids(dataset, train_ids, population_size=40, sampling_seed=42)
    second = stratified_subset_ids(dataset, train_ids, population_size=40, sampling_seed=42)
    assert np.array_equal(first, second)


def test_stratified_subset_skips_materialization_when_full_population(
    tmp_path: Path, small_dataset, monkeypatch: pytest.MonkeyPatch
) -> None:
    dataset, _dataset_sha256, train_ids, _validation_ids = small_dataset

    def _fail_if_called(*args, **kwargs):
        raise AssertionError("materialize_pandas_by_source_row_id should not be called")

    monkeypatch.setattr(
        causal_forest_runner, "materialize_pandas_by_source_row_id", _fail_if_called
    )
    subset = stratified_subset_ids(
        dataset, train_ids, population_size=len(train_ids), sampling_seed=42
    )
    assert np.array_equal(subset, np.sort(train_ids))


def test_stratified_subset_ids_also_works_on_a_validation_id_array(
    tmp_path: Path, small_dataset
) -> None:
    dataset, _dataset_sha256, _train_ids, validation_ids = small_dataset
    subset = stratified_subset_ids(
        dataset, validation_ids, population_size=15, sampling_seed=42
    )
    assert subset.size == 15
    assert set(subset.tolist()).issubset(set(validation_ids.tolist()))


# --- run_stage: raw-categorical-representation guard (D32) --------------------


def test_run_stage_fails_closed_on_raw_categorical_representation(
    tmp_path: Path, small_dataset
) -> None:
    """run_stage() must propagate fit_causal_forest()'s raw-representation
    guard rather than silently succeeding on raw f0-f11 columns -- the
    production consequence of D32 the skipped tests above are blocked on."""

    dataset, dataset_sha256, train_ids, validation_ids = small_dataset
    request = _make_request(
        tmp_path,
        dataset,
        dataset_sha256,
        run_id="blocked_run",
        train_ids=train_ids,
        validation_ids=validation_ids,
        population_size=60,
    )
    with pytest.raises(CausalForestRepresentationError, match="categorical"):
        run_stage(request)


# --- run_stage: full pipeline ---------------------------------------------------


@pytest.mark.skip(reason=CF_REPRESENTATION_BLOCKED_REASON)
def test_full_stage_run_produces_ordered_checkpoints_and_artifacts(
    tmp_path: Path, small_dataset
) -> None:
    dataset, dataset_sha256, train_ids, validation_ids = small_dataset
    request = _make_request(
        tmp_path,
        dataset,
        dataset_sha256,
        run_id="full_run",
        train_ids=train_ids,
        validation_ids=validation_ids,
        population_size=60,
    )

    result = run_stage(request)

    assert result["checkpoints"] == list(CHECKPOINT_SEQUENCE)

    run_root = request.run_root
    assert (run_root / "audit" / "run_config.json").is_file()
    assert (run_root / "models" / "causal_forest.pkl").is_file()
    assert (run_root / "predictions" / "validation_tau.parquet").is_file()
    assert (run_root / "audit" / "diagnostic_support_summary.json").is_file()
    resource_evidence = json.loads(
        (run_root / "audit" / "resource_evidence.json").read_text(encoding="utf-8")
    )
    assert resource_evidence["model_artifact_size_bytes"] > 0
    assert resource_evidence["predictions_artifact_size_bytes"] > 0
    assert resource_evidence["total_wall_seconds"] > 0
    assert resource_evidence["fit_wall_seconds"] > 0
    assert resource_evidence["predict_wall_seconds"] > 0
    assert "peak_rss_bytes_at_finalize" not in resource_evidence  # old mislabeled single-snapshot name
    if resource_evidence["peak_rss_bytes"] is not None:
        assert resource_evidence["peak_rss_bytes"] >= resource_evidence["rss_bytes_at_finalize"]
        assert len(resource_evidence["rss_stage_snapshots"]) >= 1

    manifest = json.loads((run_root / "audit" / "artifact_manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"].startswith("COMPLETED")

    predictions = pd.read_parquet(run_root / "predictions" / "validation_tau.parquet")
    assert predictions[SOURCE_ROW_ID].tolist() == sorted(validation_ids.tolist())
    assert "tau" in predictions.columns
    assert len(predictions) == len(validation_ids)


@pytest.mark.skip(reason=CF_REPRESENTATION_BLOCKED_REASON)
def test_full_stage_run_config_written_once_and_never_mutated(
    tmp_path: Path, small_dataset
) -> None:
    dataset, dataset_sha256, train_ids, validation_ids = small_dataset
    request = _make_request(
        tmp_path,
        dataset,
        dataset_sha256,
        run_id="config_immutable",
        train_ids=train_ids,
        validation_ids=validation_ids,
        population_size=60,
    )
    run_stage(request)
    run_config_path = request.run_root / "audit" / "run_config.json"
    before = run_config_path.read_text(encoding="utf-8")
    before_hash = sha256_file(run_config_path)

    # Resuming an already-completed run must not touch run_config.json.
    run_stage(request)
    assert run_config_path.read_text(encoding="utf-8") == before
    assert sha256_file(run_config_path) == before_hash


@pytest.mark.skip(reason=CF_REPRESENTATION_BLOCKED_REASON)
def test_two_fresh_runs_with_identical_inputs_produce_identical_predictions(
    tmp_path: Path, small_dataset
) -> None:
    dataset, dataset_sha256, train_ids, validation_ids = small_dataset
    request_a = _make_request(
        tmp_path,
        dataset,
        dataset_sha256,
        run_id="determinism_a",
        train_ids=train_ids,
        validation_ids=validation_ids,
        population_size=60,
    )
    request_b = _make_request(
        tmp_path,
        dataset,
        dataset_sha256,
        run_id="determinism_b",
        train_ids=train_ids,
        validation_ids=validation_ids,
        population_size=60,
    )
    run_stage(request_a)
    run_stage(request_b)

    predictions_a = pd.read_parquet(request_a.run_root / "predictions" / "validation_tau.parquet")
    predictions_b = pd.read_parquet(request_b.run_root / "predictions" / "validation_tau.parquet")
    pd.testing.assert_frame_equal(predictions_a, predictions_b)


@pytest.mark.skip(reason=CF_REPRESENTATION_BLOCKED_REASON)
def test_smoke_stage_runs_through_same_dag_with_bounded_validation_scoring(
    tmp_path: Path, small_dataset
) -> None:
    """Mirrors scripts/t11_run_stage.py's smoke path: TRAIN is the usual
    stratified subset (via population_size), but VALIDATION is ALSO bounded
    (via stratified_subset_ids on validation_ids) rather than the complete
    frozen validation cohort -- smoke exercises the production DAG cheaply,
    it does not score the full population."""

    dataset, dataset_sha256, train_ids, validation_ids_full = small_dataset
    bounded_validation_ids = causal_forest_runner.stratified_subset_ids(
        dataset, validation_ids_full, population_size=20, sampling_seed=42
    )
    request = _make_request(
        tmp_path,
        dataset,
        dataset_sha256,
        run_id="smoke_run",
        train_ids=train_ids,
        validation_ids=bounded_validation_ids,
        population_size=40,
        diagnostic_sample_size=10,
    )
    request = StageRequest(
        stage="smoke",
        run_id=request.run_id,
        run_root=request.run_root,
        dataset=request.dataset,
        dataset_sha256=request.dataset_sha256,
        train_ids=request.train_ids,
        validation_ids=request.validation_ids,
        population_size=request.population_size,
        sampling_seed=request.sampling_seed,
        model_seed=request.model_seed,
        diagnostic_sample_size=request.diagnostic_sample_size,
        config=request.config,
    )

    result = run_stage(request)

    assert result["stage"] == "smoke"
    assert result["checkpoints"] == list(CHECKPOINT_SEQUENCE)
    predictions = pd.read_parquet(request.run_root / "predictions" / "validation_tau.parquet")
    assert len(predictions) == 20
    manifest = json.loads(
        (request.run_root / "audit" / "artifact_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["status"].startswith("COMPLETED")


# --- run_stage: resume / recovery -----------------------------------------------


@pytest.mark.skip(reason=CF_REPRESENTATION_BLOCKED_REASON)
def test_resume_after_crash_before_predictions_does_not_refit(
    tmp_path: Path, small_dataset, monkeypatch: pytest.MonkeyPatch
) -> None:
    dataset, dataset_sha256, train_ids, validation_ids = small_dataset
    request = _make_request(
        tmp_path,
        dataset,
        dataset_sha256,
        run_id="crash_recovery",
        train_ids=train_ids,
        validation_ids=validation_ids,
        population_size=60,
    )

    fit_calls = {"count": 0}
    original_fit = causal_forest_runner.fit_causal_forest

    def counting_fit(*args, **kwargs):
        fit_calls["count"] += 1
        return original_fit(*args, **kwargs)

    monkeypatch.setattr(causal_forest_runner, "fit_causal_forest", counting_fit)

    original_ensure_predictions = causal_forest_runner._ensure_predictions_persisted
    call_state = {"raised": False}

    def flaky_ensure_predictions(*args, **kwargs):
        if not call_state["raised"]:
            call_state["raised"] = True
            raise RuntimeError("synthetic crash before predictions persisted")
        return original_ensure_predictions(*args, **kwargs)

    monkeypatch.setattr(
        causal_forest_runner, "_ensure_predictions_persisted", flaky_ensure_predictions
    )

    with pytest.raises(RuntimeError, match="synthetic crash"):
        run_stage(request)

    chain_after_crash = _read_checkpoint_chain(request.run_root)
    assert [c["checkpoint_name"] for c in chain_after_crash] == [
        CHECKPOINT_SEQUENCE[0],
        CHECKPOINT_SEQUENCE[1],
    ]
    assert fit_calls["count"] == 1
    assert not (request.run_root / "audit" / "artifact_manifest.json").exists()

    result = run_stage(request)

    assert fit_calls["count"] == 1  # resume must not refit
    assert result["checkpoints"] == list(CHECKPOINT_SEQUENCE)
    assert (request.run_root / "audit" / "artifact_manifest.json").is_file()


def test_resume_rejects_parameter_mismatch_against_checkpoint_one(
    tmp_path: Path, small_dataset, monkeypatch: pytest.MonkeyPatch
) -> None:
    dataset, dataset_sha256, train_ids, validation_ids = small_dataset
    request = _make_request(
        tmp_path,
        dataset,
        dataset_sha256,
        run_id="mismatch_test",
        train_ids=train_ids,
        validation_ids=validation_ids,
        population_size=60,
        model_seed=42,
    )

    def always_raise(*args, **kwargs):
        raise RuntimeError("stop after checkpoint 001")

    monkeypatch.setattr(causal_forest_runner, "_ensure_model_serialized", always_raise)
    with pytest.raises(RuntimeError, match="stop after checkpoint 001"):
        run_stage(request)
    monkeypatch.undo()

    mismatched_request = _make_request(
        tmp_path,
        dataset,
        dataset_sha256,
        run_id="mismatch_test",
        train_ids=train_ids,
        validation_ids=validation_ids,
        population_size=60,
        model_seed=2026,  # different from the run that wrote checkpoint 001
    )
    with pytest.raises(CausalForestRunnerError, match="Resume identity mismatch"):
        run_stage(mismatched_request)


# --- _ResourceSampler (continuous RSS/host-memory sampler) ---------------------
def test_fit_cohort_identity_is_persisted_and_common_across_model_seeds(
    tmp_path: Path,
    small_dataset,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Robustness model seeds must use the exact same sampled TRAIN cohort."""

    dataset, dataset_sha256, train_ids, validation_ids = small_dataset

    def _stop_after_checkpoint_001(*args, **kwargs):
        raise RuntimeError("stop after checkpoint 001")

    monkeypatch.setattr(
        causal_forest_runner,
        "_ensure_model_serialized",
        _stop_after_checkpoint_001,
    )

    fit_identities = []

    for model_seed in (42, 123, 2026):
        request = _make_request(
            tmp_path,
            dataset,
            dataset_sha256,
            run_id=f"common_cohort_seed_{model_seed}",
            train_ids=train_ids,
            validation_ids=validation_ids,
            population_size=40,
            sampling_seed=42,
            model_seed=model_seed,
        )

        with pytest.raises(RuntimeError, match="stop after checkpoint 001"):
            run_stage(request)

        started = json.loads(
            (
                request.run_root
                / "audit"
                / "checkpoints"
                / "001_started.json"
            ).read_text(encoding="utf-8")
        )

        run_config = json.loads(
            (
                request.run_root
                / "audit"
                / "run_config.json"
            ).read_text(encoding="utf-8")
        )

        assert started["fit_train_ids_identity"]["count"] == 40
        assert (
            started["fit_train_ids_identity"]
            == run_config["fit_train_ids_identity"]
        )

        fit_identities.append(started["fit_train_ids_identity"])

    assert fit_identities[0] == fit_identities[1] == fit_identities[2]

def test_resource_sampler_starts_and_stops_safely() -> None:
    with causal_forest_runner._ResourceSampler(interval_seconds=0.05) as sampler:
        time.sleep(0.3)
    assert sampler._thread is not None
    sampler._thread.join(timeout=2)
    assert not sampler._thread.is_alive()
    assert len(sampler.samples) >= 1
    for sample in sampler.samples:
        assert sample["rss_bytes"] > 0
        assert sample["system_available_bytes"] > 0
        assert 0.0 <= sample["system_percent"] <= 100.0


def test_resource_sampler_peak_is_true_max_of_continuous_samples() -> None:
    with causal_forest_runner._ResourceSampler(interval_seconds=0.05) as sampler:
        time.sleep(0.3)
    assert sampler.samples  # otherwise the test proves nothing
    assert sampler.peak_rss_bytes() == max(s["rss_bytes"] for s in sampler.samples)
    # A single lifecycle-style snapshot never exceeds the true continuous peak,
    # since it is itself one of (or bounded by) the sampled values.
    single_snapshot = causal_forest_runner._sample_rss_bytes()
    assert single_snapshot is None or sampler.peak_rss_bytes() is not None


def test_resource_sampler_peak_between_bounds_a_window() -> None:
    with causal_forest_runner._ResourceSampler(interval_seconds=0.05) as sampler:
        window_start = time.perf_counter()
        time.sleep(0.3)
        window_end = time.perf_counter()
    windowed_peak = sampler.peak_rss_bytes_between(window_start, window_end)
    assert windowed_peak is None or windowed_peak <= sampler.peak_rss_bytes()
    # A window entirely before sampling started must find nothing.
    assert sampler.peak_rss_bytes_between(window_start - 100.0, window_start - 50.0) is None


def test_resource_sampler_thread_does_not_survive_an_exception_in_the_with_block() -> None:
    captured: dict[str, object] = {}
    with pytest.raises(RuntimeError, match="synthetic failure inside sampled block"):
        with causal_forest_runner._ResourceSampler(interval_seconds=0.05) as sampler:
            captured["sampler"] = sampler
            time.sleep(0.1)
            raise RuntimeError("synthetic failure inside sampled block")

    thread = captured["sampler"]._thread
    assert thread is not None
    thread.join(timeout=2)
    assert not thread.is_alive()


@pytest.mark.skip(reason=CF_REPRESENTATION_BLOCKED_REASON)
def test_resource_evidence_schema_is_stable_across_independent_runs(
    tmp_path: Path, small_dataset
) -> None:
    dataset, dataset_sha256, train_ids, validation_ids = small_dataset
    request_a = _make_request(
        tmp_path,
        dataset,
        dataset_sha256,
        run_id="schema_a",
        train_ids=train_ids,
        validation_ids=validation_ids,
        population_size=60,
    )
    request_b = _make_request(
        tmp_path,
        dataset,
        dataset_sha256,
        run_id="schema_b",
        train_ids=train_ids,
        validation_ids=validation_ids,
        population_size=60,
    )
    run_stage(request_a)
    run_stage(request_b)

    evidence_a = json.loads(
        (request_a.run_root / "audit" / "resource_evidence.json").read_text(encoding="utf-8")
    )
    evidence_b = json.loads(
        (request_b.run_root / "audit" / "resource_evidence.json").read_text(encoding="utf-8")
    )
    # Numeric timing/RSS values legitimately differ run to run -- the SCHEMA
    # (key set) must not.
    assert set(evidence_a.keys()) == set(evidence_b.keys())
    expected_keys = {
        "stage",
        "population_size",
        "model_artifact_size_bytes",
        "predictions_artifact_size_bytes",
        "run_root_disk_usage_bytes_at_finalize",
        "total_wall_seconds",
        "fit_wall_seconds",
        "predict_wall_seconds",
        "serialization_reload_wall_seconds",
        "persist_wall_seconds",
        "prediction_throughput_rows_per_second",
        "rss_bytes_at_finalize",
        "peak_rss_bytes",
        "peak_rss_bytes_method",
        "peak_rss_during_fit_bytes",
        "continuous_sampler_sample_count",
        "rss_timeline",
        "rss_stage_snapshots",
        "system_memory_available_bytes_min",
        "system_memory_percent_max",
        "swap_used_bytes_max",
    }
    assert set(evidence_a.keys()) == expected_keys


# --- environment / sentinel helpers ---------------------------------------------


def test_modeling_environment_reports_hard_match_fields() -> None:
    environment = modeling_environment()
    hard_match = environment["hard_match"]
    assert hard_match["econml"] == FROZEN_ECONML_VERSION
    for field in ("python", "econml", "scikit_learn", "numpy", "pandas", "pyarrow"):
        assert field in hard_match
    assert "recorded_not_gated" in environment


def test_write_active_sentinel_is_atomic_and_readable(tmp_path: Path) -> None:
    sentinel_path = tmp_path / "sentinels" / ".t11_active_run_id.txt"
    write_active_sentinel(sentinel_path, "t11_full_20260819T000000Z_000000")
    assert sentinel_path.read_text(encoding="utf-8") == "t11_full_20260819T000000Z_000000"
    assert not sentinel_path.with_name(sentinel_path.name + ".tmp").exists()
