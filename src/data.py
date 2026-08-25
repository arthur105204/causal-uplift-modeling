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
import yaml

CSV_FILENAME = "criteo-uplift-v2.1.csv"

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


def repo_root() -> Path:
    """The repository root, derived from this file's own location -- never
    from the caller's working directory (which on Kaggle is /kaggle/working,
    not the repo)."""

    return Path(__file__).resolve().parent.parent


def load_config(path: Path | str | None = None) -> dict:
    """Load configs/config.yaml. Every value in it is consumed by src/ or the
    notebooks; tests/test_config.py asserts it stays in sync with the code
    defaults so it cannot silently drift into decoration."""

    config_path = Path(path) if path is not None else repo_root() / "configs" / "config.yaml"
    with open(config_path, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def on_kaggle() -> bool:
    return Path("/kaggle/working").is_dir()


def output_dir() -> Path:
    """A writable directory for generated artifacts.

    Kaggle only permits writes under /kaggle/working, so notebooks must never
    write next to the (read-only) attached repository/dataset.
    """

    target = Path("/kaggle/working/processed") if on_kaggle() else repo_root() / "data" / "processed"
    target.mkdir(parents=True, exist_ok=True)
    return target


def resolve_csv_path(
    filename: str = CSV_FILENAME,
    *,
    kaggle_input: Path | str = "/kaggle/input",
    local_dir: Path | str | None = None,
) -> Path:
    """Locate the raw CRITEO CSV without hardcoding a Kaggle dataset slug.

    Searches every attached Kaggle input dataset (whatever the slug), then
    the local data/raw/ copy used for development.
    """

    kaggle_input = Path(kaggle_input)
    if kaggle_input.is_dir():
        matches = sorted(kaggle_input.glob(f"**/{filename}"))
        if matches:
            return matches[0]

    local = Path(local_dir) if local_dir is not None else repo_root() / "data" / "raw"
    candidate = local / filename
    if candidate.is_file():
        return candidate

    raise FileNotFoundError(
        f"Could not find {filename}. Searched {kaggle_input}/**/ and {local}. "
        f"On Kaggle, attach a dataset containing {filename}; locally, place it "
        f"at data/raw/{filename}."
    )


def load_csv(path: Path | str | None = None) -> pd.DataFrame:
    """Load the raw CRITEO CSV and check it has the expected shape/columns.

    With no path, auto-discovers the CSV (Kaggle input, then data/raw/).
    """

    frame = pd.read_csv(resolve_csv_path() if path is None else path)
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
