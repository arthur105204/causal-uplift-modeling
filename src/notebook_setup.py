"""Environment bootstrap helpers for the Kaggle execution notebook.

Repository discovery (finding REPO_ROOT and putting it on sys.path) must
stay inside the notebook itself -- it runs before src/ is even importable,
so it cannot live here (see notebooks/kaggle_execution.ipynb's Stage 0 and
tests/test_notebook_bootstrap.py, which exercises that cell's source
directly). Everything else about environment setup has no such
chicken-and-egg problem and lives here instead, so the notebook's remaining
Stage 0 cells read as short calls rather than blocks of infrastructure code.
"""

from __future__ import annotations

import importlib
import platform
import subprocess
import sys
from pathlib import Path

REQUIRED_PACKAGES = (
    "numpy", "pandas", "sklearn", "lightgbm", "econml", "pyarrow", "matplotlib", "yaml", "joblib",
)


def check_dependencies(required: tuple[str, ...] = REQUIRED_PACKAGES) -> dict[str, str]:
    """Import each required package. Returns {name: version} for whatever
    already imports, and {name: "MISSING"} for whatever doesn't -- missing
    packages are also installed (best-effort; requires Kaggle internet
    access), so re-running the notebook cell that calls this after a first
    "MISSING" report typically resolves it."""

    results: dict[str, str] = {}
    missing = []
    for name in required:
        try:
            module = importlib.import_module(name)
            results[name] = str(getattr(module, "__version__", "n/a"))
        except ImportError:
            results[name] = "MISSING"
            missing.append(name)
    if missing:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", *missing], check=False)
    return results


def git_commit(repo_root: Path) -> str:
    """Short commit hash the current checkout is at, for the reproducibility
    fingerprint -- "unknown" if this isn't a git checkout or git isn't
    available (e.g. a cloned-without-history Kaggle attach)."""

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=repo_root,
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip() or "unknown"
    except Exception:
        return "unknown (not a git checkout, or git unavailable)"


def collect_env_info(
    repo_root: Path, *, seed: int, sample_rows: int | None, run_stage: str, outcome_column: str,
) -> dict:
    """Standard fields identifying what produced a given run -- written into
    every stage's run_config.json / metrics.json so a result can always be
    traced back to the exact code + config that made it."""

    return {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "git_commit": git_commit(repo_root),
        "seed": seed,
        "sample_rows": sample_rows,
        "run_stage": run_stage,
        "outcome_column": outcome_column,
    }
