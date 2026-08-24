"""Loading and basic validation for CRITEO-UPLIFTv2.1.

Feature semantics (D32): physical float64 storage does not imply continuous/
ordinal meaning. f0, f2, f7, f10 are genuinely continuous; f1, f3, f4, f5,
f6, f8, f9, f11 are categorical numeric tokens with no ordinal structure.
Treat the categorical group as categorical everywhere (dtype, model input,
diagnostics) -- reading them as plain floats silently reintroduces the bug
D32 exists to fix.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

FEATURE_COLUMNS = tuple(f"f{i}" for i in range(12))

CONTINUOUS_FEATURES = ("f0", "f2", "f7", "f10")
CATEGORICAL_FEATURES = ("f1", "f3", "f4", "f5", "f6", "f8", "f9", "f11")

assert set(CONTINUOUS_FEATURES) | set(CATEGORICAL_FEATURES) == set(FEATURE_COLUMNS)
assert not (set(CONTINUOUS_FEATURES) & set(CATEGORICAL_FEATURES))

TREATMENT_COLUMN = "treatment"
PRIMARY_OUTCOME = "conversion"
SECONDARY_OUTCOME = "visit"
AUDIT_ONLY_COLUMN = "exposure"  # post-assignment; never enters X

EXPECTED_COLUMNS = FEATURE_COLUMNS + (
    TREATMENT_COLUMN,
    PRIMARY_OUTCOME,
    SECONDARY_OUTCOME,
    AUDIT_ONLY_COLUMN,
)


def load_csv(path: Path | str) -> pd.DataFrame:
    """Load the raw CRITEO CSV and check it has the expected shape/columns."""

    frame = pd.read_csv(path)
    missing = sorted(set(EXPECTED_COLUMNS).difference(frame.columns))
    if missing:
        raise ValueError(f"Input CSV is missing expected columns: {missing}")
    if frame.empty:
        raise ValueError("Input CSV has no rows")
    return frame


def basic_summary(frame: pd.DataFrame) -> dict:
    """Cheap sanity summary: shape, null counts, treatment/outcome support."""

    return {
        "n_rows": len(frame),
        "n_cols": frame.shape[1],
        "null_counts": frame[list(EXPECTED_COLUMNS)].isna().sum().to_dict(),
        "treatment_counts": frame[TREATMENT_COLUMN].value_counts().to_dict(),
        "conversion_rate": float(frame[PRIMARY_OUTCOME].mean()),
    }


def save_parquet(frame: pd.DataFrame, path: Path | str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)


def load_parquet(path: Path | str) -> pd.DataFrame:
    return pd.read_parquet(path)
