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

# Import name -> pip package name, for the (rare) packages where they differ.
# "sklearn" specifically: the bare "sklearn" PyPI package is a deprecated
# stub that now fails to install outright ("pip install sklearn" errors);
# the real package is "scikit-learn". Only consulted for the install step --
# import-checking always uses the import name.
PIP_PACKAGE_MAP = {
    "sklearn": "scikit-learn",
}


def check_dependencies(required: tuple[str, ...] = REQUIRED_PACKAGES) -> dict[str, str]:
    """Import each required package, installing and re-verifying whatever is
    missing. Returns {name: version} -- every value is a real version string,
    never "MISSING", because this function raises instead of returning a
    result that claims success while a dependency is still unavailable.

    Raises RuntimeError if the install subprocess fails (e.g. no internet on
    a fresh Kaggle kernel) or if a package still fails to import afterward.
    """

    results: dict[str, str] = {}
    missing = []
    for name in required:
        try:
            module = importlib.import_module(name)
            results[name] = str(getattr(module, "__version__", "n/a"))
        except ImportError:
            missing.append(name)

    if missing:
        pip_names = [PIP_PACKAGE_MAP.get(name, name) for name in missing]
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", *pip_names],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                "Dependency installation failed. Check Kaggle internet settings or "
                f"package availability.\nAttempted: {pip_names}\n{result.stderr.strip()}"
            )

        still_missing = []
        for name in missing:
            try:
                module = importlib.import_module(name)
                results[name] = str(getattr(module, "__version__", "n/a"))
            except ImportError:
                still_missing.append(name)
        if still_missing:
            raise RuntimeError(
                "Dependency installation failed. Check Kaggle internet settings or "
                f"package availability. Still missing after install: {still_missing}"
            )

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
