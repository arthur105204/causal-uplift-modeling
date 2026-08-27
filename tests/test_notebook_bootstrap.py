"""The notebook bootstrap must locate the repo from a fresh Kaggle kernel.

A Kaggle kernel starts in /kaggle/working, which is NOT the repository, so
the previous `Path.cwd()`-based bootstrap silently resolved to the wrong
directory and failed to import src at all. These tests execute the *actual*
bootstrap source shipped in each notebook against a simulated Kaggle-style
layout, rather than re-implementing the logic here.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import pytest

NOTEBOOK_DIR = Path(__file__).resolve().parent.parent / "notebooks"
NOTEBOOKS = sorted(NOTEBOOK_DIR.glob("*.ipynb"))
# 01-04 are the methodology notebooks and must share one identical bootstrap.
# kaggle_execution.ipynb is the one-click runner: its bootstrap is a deliberate
# superset (it additionally offers to git-clone the repo on Kaggle), so it is
# held to the same *behaviour* but not to byte-identical source.
METHODOLOGY_NOTEBOOKS = [p for p in NOTEBOOKS if p.name[:2].isdigit()]


def _bootstrap_source(notebook_path: Path) -> str:
    """The code cell that resolves REPO_ROOT.

    Deliberately not "the first code cell" -- the execution notebook opens
    with a run-parameters cell, and a positional assumption here would test
    the wrong thing while still passing.
    """

    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    for cell in notebook["cells"]:
        if cell["cell_type"] == "code":
            source = "".join(cell["source"])
            if "REPO_ROOT" in source:
                return source
    raise AssertionError(f"{notebook_path.name} has no cell defining REPO_ROOT")


def _run_bootstrap(source: str, cwd: Path) -> Path:
    previous_cwd = Path.cwd()
    previous_path = list(sys.path)
    os.chdir(cwd)
    try:
        namespace: dict = {}
        exec(compile(source, "<bootstrap>", "exec"), namespace)
        return Path(namespace["REPO_ROOT"])
    finally:
        os.chdir(previous_cwd)
        sys.path[:] = previous_path


# kaggle_execution.ipynb's bootstrap requires every one of these to accept a
# repo copy (see its REQUIRED_MARKERS) -- the methodology notebooks (01-04)
# only require src/data.py, but a fixture repo with all six still satisfies
# that weaker check too, so one fixture covers both.
REQUIRED_MARKERS = (
    "src/data.py",
    "src/models.py",
    "src/preprocessing.py",
    "src/notebook_setup.py",
    "src/pipeline.py",
    "src/reporting.py",
)


def _fake_repo(root: Path) -> Path:
    (root / "src").mkdir(parents=True)
    for marker in REQUIRED_MARKERS:
        (root / marker).write_text("# marker\n", encoding="utf-8")
    return root


def _fake_repo_missing_pipeline_files(root: Path) -> Path:
    """A stale/incomplete repo copy: only the oldest marker file exists."""

    (root / "src").mkdir(parents=True)
    (root / "src" / "data.py").write_text("# marker\n", encoding="utf-8")
    return root


@pytest.mark.parametrize("notebook_path", NOTEBOOKS, ids=lambda p: p.name)
def test_bootstrap_finds_repo_when_cwd_is_the_repo(notebook_path: Path, tmp_path: Path) -> None:
    """Local development: the notebook is run from inside the repository."""

    repo = _fake_repo(tmp_path / "repo")
    assert _run_bootstrap(_bootstrap_source(notebook_path), repo).resolve() == repo.resolve()


@pytest.mark.parametrize("notebook_path", NOTEBOOKS, ids=lambda p: p.name)
def test_bootstrap_finds_repo_from_a_kaggle_style_working_dir(notebook_path: Path, tmp_path: Path) -> None:
    """Kaggle: the kernel's cwd is a working directory that merely *contains*
    the cloned repository -- cwd itself has no src/."""

    working = tmp_path / "working"
    working.mkdir()
    repo = _fake_repo(working / "causal-uplift-modeling")
    assert _run_bootstrap(_bootstrap_source(notebook_path), working).resolve() == repo.resolve()


@pytest.mark.parametrize("notebook_path", NOTEBOOKS, ids=lambda p: p.name)
def test_bootstrap_finds_repo_from_a_nested_subdirectory(notebook_path: Path, tmp_path: Path) -> None:
    """The notebook is opened from notebooks/, so cwd is a child of the repo."""

    repo = _fake_repo(tmp_path / "repo")
    nested = repo / "notebooks"
    nested.mkdir()
    assert _run_bootstrap(_bootstrap_source(notebook_path), nested).resolve() == repo.resolve()


@pytest.mark.parametrize("notebook_path", NOTEBOOKS, ids=lambda p: p.name)
def test_bootstrap_fails_loudly_when_repo_is_absent(notebook_path: Path, tmp_path: Path) -> None:
    """Better a clear error than a silently wrong REPO_ROOT."""

    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(RuntimeError, match="(?i)repositor"):
        _run_bootstrap(_bootstrap_source(notebook_path), empty)


def test_kaggle_execution_bootstrap_accepts_repo_with_all_markers(tmp_path: Path) -> None:
    """A repo with every required marker file is accepted."""

    path = NOTEBOOK_DIR / "kaggle_execution.ipynb"
    repo = _fake_repo(tmp_path / "repo")
    assert _run_bootstrap(_bootstrap_source(path), repo).resolve() == repo.resolve()


def test_kaggle_execution_bootstrap_rejects_incomplete_repo(tmp_path: Path) -> None:
    """A stale repo copy that only has src/data.py (missing
    src/notebook_setup.py, src/pipeline.py, src/reporting.py, ...) must be
    rejected, not silently accepted as if it were a complete checkout --
    this is what used to produce a confusing ModuleNotFoundError two cells
    later instead of a clear error here."""

    path = NOTEBOOK_DIR / "kaggle_execution.ipynb"
    incomplete = _fake_repo_missing_pipeline_files(tmp_path / "incomplete")
    with pytest.raises(RuntimeError, match="(?i)repositor"):
        _run_bootstrap(_bootstrap_source(path), incomplete)


def test_methodology_notebooks_ship_the_same_bootstrap() -> None:
    """01-04 must share one bootstrap; a drifting copy is how one notebook
    ends up broken on Kaggle while the others work."""

    sources = {p.name: _bootstrap_source(p) for p in METHODOLOGY_NOTEBOOKS}
    assert len(set(sources.values())) == 1, f"bootstrap differs across notebooks: {sorted(sources)}"


def test_execution_notebook_exists_and_orchestrates_rather_than_reimplements() -> None:
    """The one-click runner must call into src/, not carry its own copy of the
    modelling code -- that duplication is exactly what it exists to avoid."""

    path = NOTEBOOK_DIR / "kaggle_execution.ipynb"
    assert path.is_file(), "notebooks/kaggle_execution.ipynb is missing"
    notebook = json.loads(path.read_text(encoding="utf-8"))
    source = "\n".join("".join(c["source"]) for c in notebook["cells"] if c["cell_type"] == "code")

    for imported in ("fit_response_model", "fit_t_learner", "fit_x_learner", "fit_causal_forest", "evaluate_ranking"):
        assert imported in source, f"execution notebook does not use src.{imported}"
    # No redefinition of the modelling primitives.
    for reimplemented in ("def fit_t_learner", "def fit_x_learner", "def fit_causal_forest", "def evaluate_ranking"):
        assert reimplemented not in source, f"execution notebook reimplements {reimplemented!r}"


def test_execution_notebook_passes_the_raw_frame_to_the_x_learner() -> None:
    """Guards the fold-local preprocessing fix at the call site: handing
    fit_x_learner a globally-transformed frame is the leak this project
    already fixed once."""

    path = NOTEBOOK_DIR / "kaggle_execution.ipynb"
    notebook = json.loads(path.read_text(encoding="utf-8"))
    source = "\n".join("".join(c["source"]) for c in notebook["cells"] if c["cell_type"] == "code")
    assert "fit_x_learner(train_frame" in source, "X-Learner must receive the raw train frame"


def test_execution_notebook_scopes_every_stage_dir_call_by_outcome() -> None:
    """Regression guard: conversion and visit must create and read
    independent artifact directories. src.artifacts.stage_dir() defaults an
    omitted `outcome` to "conversion" -- a notebook cell that calls
    stage_dir("baseline"|"uplift"|"causal_forest"|"report") without also
    passing `outcome=` silently reads/writes the conversion tree even on a
    visit run (this is exactly the bug that produced
    FileNotFoundError: outputs/conversion/baseline/roc_curve.csv on an
    OUTCOME="visit" run -- src.data/src.artifacts/src.pipeline were never
    the problem, two notebook call sites were)."""

    path = NOTEBOOK_DIR / "kaggle_execution.ipynb"
    notebook = json.loads(path.read_text(encoding="utf-8"))
    source = "\n".join("".join(c["source"]) for c in notebook["cells"] if c["cell_type"] == "code")

    unscoped = re.findall(
        r'stage_dir\(\s*["\'](?:baseline|uplift|causal_forest|report)["\']\s*\)', source,
    )
    assert not unscoped, (
        f"found stage_dir(...) call(s) for an outcome-scoped stage with no `outcome=` "
        f"argument -- these silently default to the conversion tree: {unscoped}"
    )


def test_pip_package_map_translates_sklearn_to_scikit_learn() -> None:
    """The bare "sklearn" PyPI package is a deprecated stub that fails to
    install; a missing sklearn must be installed as "scikit-learn" instead."""

    from src.notebook_setup import PIP_PACKAGE_MAP

    assert PIP_PACKAGE_MAP["sklearn"] == "scikit-learn"
