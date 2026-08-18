from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.audit import FEATURE_COLUMNS
from src.split import (
    HELDOUT_RELEASE_STATUS,
    SPLIT_LABELS,
    HeldOutAccessError,
    SplitContractError,
    SplitDataset,
    assign_split,
    held_out_support_gate,
    membership_hash,
    support_summary,
    verify_deterministic_regeneration,
    verify_disjoint_and_complete,
)


def _frame(rows: int = 4000, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    frame = pd.DataFrame(
        {feature: rng.normal(size=rows) for feature in FEATURE_COLUMNS}
    )
    frame["treatment"] = rng.binomial(1, 0.7, size=rows)
    # Deliberately near-balanced (T,Y) cells for unit-fixture purposes: this exercises split
    # mechanics, not realistic Criteo class rarity. The rare-cell case at real scale (thousands
    # of rows even at <1% share) is exercised separately against the full processed dataset.
    p_convert = np.where(frame["treatment"] == 1, 0.45, 0.35)
    frame["conversion"] = rng.binomial(1, p_convert)
    frame["_source_row_id"] = np.arange(rows, dtype=np.int64)
    return frame


def test_split_preserves_row_count_and_approximate_proportions() -> None:
    frame = _frame(rows=10_000)
    membership = assign_split(frame)
    assert len(membership) == len(frame)
    counts = membership["split"].value_counts()
    assert counts["train"] / len(frame) == pytest.approx(0.70, abs=0.01)
    assert counts["validation"] / len(frame) == pytest.approx(0.15, abs=0.01)
    assert counts["held_out"] / len(frame) == pytest.approx(0.15, abs=0.01)


def test_split_stratification_preserves_joint_ty_within_tolerance() -> None:
    frame = _frame(rows=20_000)
    membership = assign_split(frame)
    merged = frame.merge(membership, on="_source_row_id")
    overall_rate = merged["conversion"].mean()
    for label in ("train", "validation", "held_out"):
        subset_rate = merged.loc[merged["split"] == label, "conversion"].mean()
        assert subset_rate == pytest.approx(overall_rate, abs=0.02)
        overall_treated = merged["treatment"].mean()
        subset_treated = merged.loc[merged["split"] == label, "treatment"].mean()
        assert subset_treated == pytest.approx(overall_treated, abs=0.02)


def test_split_is_disjoint_and_complete() -> None:
    frame = _frame(rows=3000)
    membership = assign_split(frame)
    result = verify_disjoint_and_complete(membership, frame["_source_row_id"])
    assert result["complete"] is True
    assert all(overlap == 0 for overlap in result["pairwise_overlaps"].values())
    assert sum(result["counts"].values()) == len(frame)


def test_disjointness_check_fails_closed_on_overlap() -> None:
    frame = _frame(rows=400)
    membership = assign_split(frame)
    corrupted = membership.copy()
    corrupted.loc[corrupted.index[0], "split"] = "train"
    corrupted.loc[corrupted.index[1], "split"] = "train"
    # Force a genuine overlap: duplicate one row's id into another split.
    duplicate_row = corrupted.iloc[[0]].copy()
    duplicate_row["split"] = "validation"
    corrupted = pd.concat([corrupted, duplicate_row], ignore_index=True)
    with pytest.raises(SplitContractError, match="disjointness"):
        verify_disjoint_and_complete(corrupted, frame["_source_row_id"])


def test_disjointness_check_fails_closed_on_incomplete_union() -> None:
    frame = _frame(rows=400)
    membership = assign_split(frame).iloc[:-1]  # drop one row
    with pytest.raises(SplitContractError, match="disjointness"):
        verify_disjoint_and_complete(membership, frame["_source_row_id"])


def test_membership_hash_is_order_independent() -> None:
    frame = _frame(rows=500)
    membership = assign_split(frame)
    shuffled = membership.sample(frac=1.0, random_state=7).reset_index(drop=True)
    assert membership_hash(membership) == membership_hash(shuffled)


def test_deterministic_regeneration_reproduces_identical_hash() -> None:
    frame = _frame(rows=500)
    membership = assign_split(frame)
    expected = membership_hash(membership)
    verify_deterministic_regeneration(frame, expected)  # must not raise


def test_deterministic_regeneration_fails_closed_on_changed_input() -> None:
    frame = _frame(rows=500)
    membership = assign_split(frame)
    expected = membership_hash(membership)
    changed = frame.copy()
    changed.loc[0, "treatment"] = 1 - changed.loc[0, "treatment"]
    with pytest.raises(SplitContractError, match="hash mismatch"):
        verify_deterministic_regeneration(changed, expected)


def test_source_row_id_is_never_renumbered() -> None:
    frame = _frame(rows=500)
    membership = assign_split(frame)
    assert set(membership["_source_row_id"]) == set(frame["_source_row_id"])


def test_support_summary_reconciles_for_train_and_validation() -> None:
    frame = _frame(rows=5000)
    membership = assign_split(frame)
    for label in ("train", "validation"):
        summary = support_summary(frame, membership, label)
        assert sum(summary["counts"].values()) == summary["n"]


def test_support_summary_rejects_held_out() -> None:
    frame = _frame(rows=500)
    membership = assign_split(frame)
    with pytest.raises(HeldOutAccessError):
        support_summary(frame, membership, "held_out")


def test_held_out_support_gate_returns_opaque_status_only() -> None:
    frame = _frame(rows=5000)
    membership = assign_split(frame)
    status = held_out_support_gate(frame, membership)
    assert status in {"PASS", "FAIL"}
    assert isinstance(status, str)


def test_held_out_ids_fail_closed_without_release_marker(tmp_path: Path) -> None:
    frame = _frame(rows=400)
    membership = assign_split(frame)
    dataset = SplitDataset(membership=membership)
    missing_marker = tmp_path / "does_not_exist.json"
    with pytest.raises(HeldOutAccessError, match="not found"):
        dataset.held_out_ids(release_manifest_path=missing_marker)


def test_held_out_ids_fail_closed_with_wrong_status(tmp_path: Path) -> None:
    frame = _frame(rows=400)
    membership = assign_split(frame)
    dataset = SplitDataset(membership=membership)
    marker = tmp_path / "release.json"
    marker.write_text(json.dumps({"status": "NOT_YET_RELEASED"}), encoding="utf-8")
    with pytest.raises(HeldOutAccessError, match="status"):
        dataset.held_out_ids(release_manifest_path=marker)


def test_held_out_ids_succeed_with_valid_release_marker(tmp_path: Path) -> None:
    frame = _frame(rows=400)
    membership = assign_split(frame)
    dataset = SplitDataset(membership=membership)
    marker = tmp_path / "release.json"
    marker.write_text(json.dumps({"status": HELDOUT_RELEASE_STATUS}), encoding="utf-8")
    ids = dataset.held_out_ids(release_manifest_path=marker)
    expected = set(membership.loc[membership["split"] == "held_out", "_source_row_id"])
    assert set(ids.tolist()) == expected


def test_train_and_validation_ids_available_without_any_guard() -> None:
    frame = _frame(rows=400)
    membership = assign_split(frame)
    dataset = SplitDataset(membership=membership)
    assert len(dataset.train_ids()) > 0
    assert len(dataset.validation_ids()) > 0


def test_split_labels_are_exactly_the_frozen_three() -> None:
    frame = _frame(rows=400)
    membership = assign_split(frame)
    assert set(membership["split"].unique()) == set(SPLIT_LABELS)
