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
import sys
from pathlib import Path

import pytest

NOTEBOOKS = sorted(Path(__file__).resolve().parent.parent.glob("notebooks/*.ipynb"))


def _bootstrap_source(notebook_path: Path) -> str:
    """The first code cell of a notebook is its bootstrap."""

    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    for cell in notebook["cells"]:
        if cell["cell_type"] == "code":
            return "".join(cell["source"])
    raise AssertionError(f"{notebook_path.name} has no code cell")


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


def _fake_repo(root: Path) -> Path:
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
    with pytest.raises(RuntimeError, match="repository root"):
        _run_bootstrap(_bootstrap_source(notebook_path), empty)


def test_every_notebook_ships_the_same_bootstrap() -> None:
    """All four must share one bootstrap; a drifting copy is how one notebook
    ends up broken on Kaggle while the others work."""

    sources = {p.name: _bootstrap_source(p) for p in NOTEBOOKS}
    assert len(set(sources.values())) == 1, f"bootstrap differs across notebooks: {sorted(sources)}"
