"""Frozen 70/15/15 train/validation/held-out split (T05).

Implements the one-time seeded, jointly-(T,Y)-stratified split, its
disjointness/row-accounting verification, deterministic regeneration, and a
fail-closed held-out access guard. Reused by every downstream task that needs
partition membership, which is why it lives in ``src/`` rather than a notebook.

This module never trains a model, imputes a feature, or reads held-out labels.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from src.audit import assert_binary_complete, assert_source_row_identity
from src.data import (
    DataContractError,
    PRIMARY_OUTCOME,
    SOURCE_ROW_ID,
    TREATMENT_COLUMN,
)

SPLIT_SEED = 42
TRAIN_FRACTION = 0.70
VALIDATION_FRACTION = 0.15
HELDOUT_FRACTION = 0.15
SPLIT_LABELS = ("train", "validation", "held_out")
HELDOUT_RELEASE_STATUS = "HELDOUT_RELEASED"


class SplitContractError(DataContractError):
    """Raised when a T05 split-construction or verification invariant is violated."""


class HeldOutAccessError(SplitContractError):
    """Raised when held-out row identities are requested without a valid T17 release marker."""


def _joint_strata(frame: pd.DataFrame) -> pd.Series:
    """Build the joint (T,Y) stratification key. Reads T and Y mechanically only."""

    assert_binary_complete(frame[TREATMENT_COLUMN], TREATMENT_COLUMN)
    assert_binary_complete(frame[PRIMARY_OUTCOME], PRIMARY_OUTCOME)
    return frame[TREATMENT_COLUMN].astype(str) + "_" + frame[PRIMARY_OUTCOME].astype(str)


def assign_split(
    frame: pd.DataFrame,
    *,
    seed: int = SPLIT_SEED,
    train_fraction: float = TRAIN_FRACTION,
    validation_fraction: float = VALIDATION_FRACTION,
) -> pd.DataFrame:
    """Assign every row to train/validation/held_out in one seeded, stratified split.

    Returns a two-column mapping (_source_row_id, split) with no other data
    attached — no feature, treatment, or outcome value is carried into the
    returned membership table itself.
    """

    assert_source_row_identity(frame, require_zero_based_complete=True)
    strata = _joint_strata(frame)
    ids = frame[SOURCE_ROW_ID].to_numpy()

    train_ids, remainder_ids, _, remainder_strata = train_test_split(
        ids, strata, train_size=train_fraction, random_state=seed, stratify=strata,
    )
    remainder_validation_share = validation_fraction / (1.0 - train_fraction)
    validation_ids, heldout_ids = train_test_split(
        remainder_ids, train_size=remainder_validation_share, random_state=seed, stratify=remainder_strata,
    )

    membership = pd.concat(
        [
            pd.DataFrame({SOURCE_ROW_ID: train_ids, "split": "train"}),
            pd.DataFrame({SOURCE_ROW_ID: validation_ids, "split": "validation"}),
            pd.DataFrame({SOURCE_ROW_ID: heldout_ids, "split": "held_out"}),
        ],
        ignore_index=True,
    )
    membership[SOURCE_ROW_ID] = membership[SOURCE_ROW_ID].astype(np.int64)
    membership = membership.sort_values(SOURCE_ROW_ID, kind="mergesort").reset_index(drop=True)
    if len(membership) != len(frame):
        raise SplitContractError(
            f"Split membership row count ({len(membership)}) does not reconcile with input ({len(frame)})"
        )
    return membership


def verify_disjoint_and_complete(
    membership: pd.DataFrame,
    expected_source_row_ids: pd.Series,
) -> dict[str, Any]:
    """Verify pairwise-disjoint identities and full-union row accounting. Fails closed."""

    groups = {
        label: set(membership.loc[membership["split"] == label, SOURCE_ROW_ID].tolist())
        for label in SPLIT_LABELS
    }
    labels = list(SPLIT_LABELS)
    pairwise_overlaps = {
        f"{labels[i]}_x_{labels[j]}": len(groups[labels[i]] & groups[labels[j]])
        for i in range(len(labels))
        for j in range(i + 1, len(labels))
    }
    total_overlap = sum(pairwise_overlaps.values())
    union = set().union(*groups.values())
    expected = {int(value) for value in expected_source_row_ids}
    complete = union == expected
    if total_overlap or not complete:
        raise SplitContractError(
            f"Split disjointness/accounting failed: pairwise_overlaps={pairwise_overlaps}, "
            f"union_size={len(union)}, expected_size={len(expected)}, complete={complete}"
        )
    return {
        "pairwise_overlaps": pairwise_overlaps,
        "union_row_count": len(union),
        "expected_row_count": len(expected),
        "complete": complete,
        "counts": {label: len(groups[label]) for label in labels},
    }


def membership_hash(membership: pd.DataFrame) -> str:
    """Deterministic content hash of (_source_row_id -> split) membership, order-independent."""

    ordered = membership.sort_values(SOURCE_ROW_ID, kind="mergesort")
    label_codes = ordered["split"].map({label: index for index, label in enumerate(SPLIT_LABELS)})
    if label_codes.isna().any():
        raise SplitContractError("Membership contains a split label outside the frozen set")
    digest = hashlib.sha256()
    digest.update(b"t05-split-membership-v1|")
    digest.update(ordered[SOURCE_ROW_ID].to_numpy(dtype="<i8").tobytes())
    digest.update(label_codes.to_numpy(dtype="<i1").tobytes())
    return digest.hexdigest()


def verify_deterministic_regeneration(
    frame: pd.DataFrame,
    expected_hash: str,
    **assign_split_kwargs: Any,
) -> None:
    """Regenerate the split from scratch and fail closed if the membership hash differs."""

    regenerated = assign_split(frame, **assign_split_kwargs)
    observed_hash = membership_hash(regenerated)
    if observed_hash != expected_hash:
        raise SplitContractError(
            f"Split regeneration hash mismatch: expected {expected_hash}, observed {observed_hash}"
        )


def support_summary(frame: pd.DataFrame, membership: pd.DataFrame, split_label: str) -> dict[str, Any]:
    """Non-sealed (T,Y) support summary for 'train' or 'validation' only. Refuses 'held_out'."""

    if split_label == "held_out":
        raise HeldOutAccessError("support_summary() may not be called with split_label='held_out'")
    if split_label not in SPLIT_LABELS:
        raise SplitContractError(f"Unknown split label: {split_label}")
    ids = membership.loc[membership["split"] == split_label, SOURCE_ROW_ID]
    subset = frame.loc[frame[SOURCE_ROW_ID].isin(ids)]
    counts = (
        subset.groupby([TREATMENT_COLUMN, PRIMARY_OUTCOME], observed=True)
        .size()
        .reindex(pd.MultiIndex.from_product([[0, 1], [0, 1]], names=[TREATMENT_COLUMN, PRIMARY_OUTCOME]), fill_value=0)
    )
    if int(counts.sum()) != len(ids):
        raise SplitContractError(f"{split_label} support summary does not reconcile with membership count")
    return {
        "split": split_label,
        "n": int(len(ids)),
        "counts": {f"T={t},Y={y}": int(n) for (t, y), n in counts.items()},
    }


def held_out_support_gate(frame: pd.DataFrame, membership: pd.DataFrame) -> str:
    """Verify held-out (T,Y) support internally; return only an opaque PASS/FAIL status.

    No held-out count, rate, or distribution is returned or logged by this function.
    """

    ids = membership.loc[membership["split"] == "held_out", SOURCE_ROW_ID]
    subset = frame.loc[frame[SOURCE_ROW_ID].isin(ids)]
    counts = subset.groupby([TREATMENT_COLUMN, PRIMARY_OUTCOME], observed=True).size()
    has_all_four_cells = len(counts) == 4 and bool((counts > 0).all())
    return "PASS" if has_all_four_cells else "FAIL"


@dataclass(frozen=True)
class SplitDataset:
    """Row-aligned split membership with a fail-closed held-out guard.

    ``train_ids``/``validation_ids`` are freely available. ``held_out_ids``
    requires a release manifest written by the authorized T17 process; before
    T17 that file does not exist, so the guard fails closed structurally
    rather than via a flag that could be flipped by accident.
    """

    membership: pd.DataFrame

    def _ids(self, label: str) -> np.ndarray:
        return self.membership.loc[self.membership["split"] == label, SOURCE_ROW_ID].to_numpy(dtype=np.int64)

    def train_ids(self) -> np.ndarray:
        return self._ids("train")

    def validation_ids(self) -> np.ndarray:
        return self._ids("validation")

    def held_out_ids(self, *, release_manifest_path: Path) -> np.ndarray:
        if not release_manifest_path.is_file():
            raise HeldOutAccessError(
                f"Held-out release marker not found at {release_manifest_path}; "
                "held-out row identities remain sealed until the authorized T17 release."
            )
        marker = json.loads(release_manifest_path.read_text(encoding="utf-8"))
        if marker.get("status") != HELDOUT_RELEASE_STATUS:
            raise HeldOutAccessError(
                f"Held-out release marker exists but its status is not {HELDOUT_RELEASE_STATUS!r}"
            )
        return self._ids("held_out")
