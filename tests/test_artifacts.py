from __future__ import annotations

import pytest

from src.artifacts import experiment_metadata


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
