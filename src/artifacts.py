"""Stage-artifact I/O for the Kaggle execution notebook.

`notebooks/kaggle_execution.ipynb` runs as independent, restart-safe stages
(data -> preprocessing -> baseline -> uplift -> causal_forest -> report).
Each stage's expensive output (a fitted model, a prediction, a metric) is
persisted here so a later stage -- possibly in a fresh kernel, after an
explicit restart taken to reclaim memory -- can load it instead of
recomputing it.

This module is notebook orchestration plumbing: generic save/load helpers
and a config fingerprint. It does not compute a metric, fit a model, or
transform a feature -- that logic stays in src.data / src.preprocessing /
src.models / src.evaluation, which this module never reimplements.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import joblib
import pandas as pd

from src.data import PRIMARY_OUTCOME, on_kaggle, repo_root, resolve_outcome

# data/preprocessing are shared across every outcome -- the row partition and
# the feature transforms never depend on which outcome (Y) is being modeled
# (see docs/secondary_visit_outcome_experiment_plan.md Phase 1/5 audit), so
# they live at one location and are computed once, reused by every outcome.
SHARED_STAGES = ("data", "preprocessing")
# baseline/uplift/causal_forest/report DO depend on which outcome was
# selected (the fitted model, its predictions, its metrics) -- each lives
# under its own outcome subdirectory so a conversion run and a visit run can
# never collide or be mistaken for one another on disk.
OUTCOME_SCOPED_STAGES = ("baseline", "uplift", "causal_forest", "report")
STAGES = SHARED_STAGES + OUTCOME_SCOPED_STAGES


def artifact_root() -> Path:
    """Root directory for every stage's artifacts.

    Kaggle only permits writes under /kaggle/working (see src.data.output_dir),
    so artifacts land at /kaggle/working/outputs/ there; locally at the
    repo-relative outputs/, which is gitignored. Kaggle is the execution
    target this exists for -- the local path only exists for development
    validation of the notebook itself.
    """

    root = (Path("/kaggle/working") if on_kaggle() else repo_root()) / "outputs"
    root.mkdir(parents=True, exist_ok=True)
    return root


def stage_dir(stage: str, *, outcome: str | None = None) -> Path:
    """Directory for one stage's artifacts.

    `outcome` is only consulted for OUTCOME_SCOPED_STAGES, where it selects
    which outcome's subdirectory to use (default: resolve_outcome's default,
    conversion) -- e.g. outputs/conversion/baseline/ vs
    outputs/visit/baseline/. SHARED_STAGES ignore it entirely: they resolve
    to the same outputs/data/ or outputs/preprocessing/ regardless of
    outcome, by design (see SHARED_STAGES above).
    """

    if stage not in STAGES:
        raise ValueError(f"unknown stage {stage!r}, expected one of {STAGES}")
    root = artifact_root()
    if stage in OUTCOME_SCOPED_STAGES:
        path = root / resolve_outcome(outcome) / stage
    else:
        path = root / stage
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_fingerprint(*parts: object) -> str:
    """Short deterministic fingerprint of whatever run-defining values are
    passed in (sample size, seed, split fractions, ...).

    Used to detect a stale artifact -- one saved under a different
    SAMPLE_ROWS/SEED than the current run -- so a later stage never silently
    trusts data it wasn't actually produced from.
    """

    payload = json.dumps(parts, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def experiment_metadata(outcome: str | None, *, seed: int, data_signature: str) -> dict:
    """Standard experiment-identifying fields every stage's metadata JSON
    should carry, so a conversion artifact and a visit artifact are never
    ambiguous about which experiment produced them.

    `outcome=None` resolves to the default (conversion), matching
    src.data.resolve_outcome. `experiment_name` encodes both the outcome and
    its role ("<outcome>_primary" for conversion, "<outcome>_sensitivity"
    for every other supported outcome) so it reads unambiguously on its own,
    without needing the plan document open to interpret it.
    """

    resolved = resolve_outcome(outcome)
    role = "primary" if resolved == PRIMARY_OUTCOME else "sensitivity"
    return {
        "outcome_column": resolved,
        "experiment_name": f"{resolved}_{role}",
        "seed": seed,
        "data_signature": data_signature,
    }


def save_json(obj: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def artifact_is_fresh(meta_path: Path, expected_signature: str, *, outcome: str | None = None) -> bool:
    """True if a stage's cached metadata is safe to reuse: the file exists,
    parses, and its data_signature matches. When `outcome` is given, the
    cached metadata's own outcome_column must also match the resolved
    outcome -- this is what stops a visit run from ever treating a
    conversion-trained artifact (or vice versa) as fresh, even though both
    can share the same data_signature (see SHARED_STAGES: the underlying row
    partition really is identical, only the outcome differs).

    `outcome=None` (used for SHARED_STAGES, whose metadata never carries an
    outcome_column at all) skips the outcome check entirely -- unchanged
    behavior from before outcome became configurable.
    """

    if not meta_path.is_file():
        return False
    try:
        meta = load_json(meta_path)
    except Exception:
        return False
    if meta.get("data_signature") != expected_signature:
        return False
    if outcome is not None and meta.get("outcome_column") != resolve_outcome(outcome):
        return False
    return True


def save_pickle(obj: object, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(obj, path)


def load_pickle(path: Path) -> object:
    return joblib.load(path)


def save_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def load_csv_artifact(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)
