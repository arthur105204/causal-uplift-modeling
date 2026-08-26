from __future__ import annotations

from pathlib import Path

import pytest

import src.artifacts as artifacts
from src.artifacts import artifact_is_fresh, experiment_metadata, save_json, stage_dir


def test_experiment_metadata_defaults_to_conversion_primary() -> None:
    meta = experiment_metadata(None, seed=42, data_signature="abc123")
    assert meta == {
        "outcome_column": "conversion",
        "experiment_name": "conversion_primary",
        "seed": 42,
        "data_signature": "abc123",
    }


def test_experiment_metadata_conversion_explicit_matches_default() -> None:
    assert experiment_metadata("conversion", seed=42, data_signature="abc123") == experiment_metadata(
        None, seed=42, data_signature="abc123"
    )


def test_experiment_metadata_visit_is_labeled_sensitivity() -> None:
    meta = experiment_metadata("visit", seed=42, data_signature="def456")
    assert meta == {
        "outcome_column": "visit",
        "experiment_name": "visit_sensitivity",
        "seed": 42,
        "data_signature": "def456",
    }


def test_experiment_metadata_rejects_unsupported_outcome() -> None:
    with pytest.raises(ValueError):
        experiment_metadata("exposure", seed=42, data_signature="abc123")


def test_experiment_metadata_required_keys_present_for_every_supported_outcome() -> None:
    required = {"outcome_column", "experiment_name", "seed", "data_signature"}
    for outcome in ("conversion", "visit"):
        meta = experiment_metadata(outcome, seed=7, data_signature="sig")
        assert required <= set(meta.keys())


@pytest.fixture()
def isolated_artifact_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """stage_dir()/artifact_root() resolve against the real repo by default --
    redirect them to a scratch directory so these tests never touch the
    actual outputs/ tree."""

    monkeypatch.setattr(artifacts, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(artifacts, "on_kaggle", lambda: False)
    return tmp_path


def test_stage_dir_shared_stage_ignores_outcome(isolated_artifact_root: Path) -> None:
    """data/preprocessing artifacts must be the SAME physical directory for
    both outcomes -- this is what lets the visit experiment reuse conversion's
    exact train/validation/test row partition instead of regenerating it."""

    assert stage_dir("data", outcome="conversion") == stage_dir("data", outcome="visit")
    assert stage_dir("preprocessing", outcome="conversion") == stage_dir("preprocessing", outcome="visit")


def test_stage_dir_outcome_scoped_stage_differs_by_outcome(isolated_artifact_root: Path) -> None:
    for stage in ("baseline", "uplift", "causal_forest", "report"):
        conversion_dir = stage_dir(stage, outcome="conversion")
        visit_dir = stage_dir(stage, outcome="visit")
        assert conversion_dir != visit_dir, f"{stage} must not collide between outcomes"
        assert "conversion" in conversion_dir.parts
        assert "visit" in visit_dir.parts


def test_stage_dir_default_outcome_is_conversion(isolated_artifact_root: Path) -> None:
    assert stage_dir("baseline") == stage_dir("baseline", outcome="conversion")


def test_stage_dir_rejects_unsupported_outcome(isolated_artifact_root: Path) -> None:
    with pytest.raises(ValueError):
        stage_dir("baseline", outcome="exposure")


def test_artifact_is_fresh_missing_file_is_false(tmp_path: Path) -> None:
    assert artifact_is_fresh(tmp_path / "does_not_exist.json", "sig") is False


def test_artifact_is_fresh_signature_mismatch_is_false(tmp_path: Path) -> None:
    meta_path = tmp_path / "metrics.json"
    save_json({"data_signature": "sig-a"}, meta_path)
    assert artifact_is_fresh(meta_path, "sig-b") is False


def test_artifact_is_fresh_no_outcome_check_when_outcome_not_passed(tmp_path: Path) -> None:
    """SHARED_STAGES metadata never carries outcome_column -- outcome=None
    (the default) must not require one."""

    meta_path = tmp_path / "run_config.json"
    save_json({"data_signature": "sig"}, meta_path)
    assert artifact_is_fresh(meta_path, "sig") is True


def test_artifact_is_fresh_rejects_conversion_artifact_for_a_visit_request(tmp_path: Path) -> None:
    """The core cache-safety guarantee: a conversion-trained model's metadata
    must never be reported fresh when a visit run asks for it, even though
    both share the same data_signature (same underlying row partition)."""

    meta_path = tmp_path / "metrics.json"
    save_json({"data_signature": "sig", "outcome_column": "conversion"}, meta_path)
    assert artifact_is_fresh(meta_path, "sig", outcome="visit") is False
    assert artifact_is_fresh(meta_path, "sig", outcome="conversion") is True


def test_artifact_is_fresh_rejects_visit_artifact_for_a_conversion_request(tmp_path: Path) -> None:
    meta_path = tmp_path / "metrics.json"
    save_json({"data_signature": "sig", "outcome_column": "visit"}, meta_path)
    assert artifact_is_fresh(meta_path, "sig", outcome="conversion") is False
    assert artifact_is_fresh(meta_path, "sig", outcome="visit") is True


def test_artifact_is_fresh_handles_unparseable_json(tmp_path: Path) -> None:
    meta_path = tmp_path / "metrics.json"
    meta_path.write_text("not json", encoding="utf-8")
    assert artifact_is_fresh(meta_path, "sig") is False
