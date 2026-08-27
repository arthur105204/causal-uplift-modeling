from __future__ import annotations

import subprocess
from types import SimpleNamespace

import pytest

from src.notebook_setup import check_dependencies


def test_check_dependencies_returns_real_versions_for_already_present_packages() -> None:
    # "os" has no __version__ -- exercises the "n/a" fallback, not the
    # install path (nothing is missing, so subprocess is never invoked).
    assert check_dependencies(required=("os",)) == {"os": "n/a"}


def test_check_dependencies_raises_when_install_subprocess_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """Must never silently continue -- a failed install (e.g. no internet on
    a fresh Kaggle kernel) has to raise, not report a fake success."""

    monkeypatch.setattr(
        subprocess, "run",
        lambda *a, **k: SimpleNamespace(returncode=1, stdout="", stderr="no internet"),
    )
    with pytest.raises(RuntimeError, match="Dependency installation failed"):
        check_dependencies(required=("this_package_does_not_exist_xyz",))


def test_check_dependencies_raises_when_still_missing_after_a_reported_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A returncode of 0 from pip is not sufficient proof of success -- the
    import is re-verified, and a package still unimportable afterward must
    also raise rather than be reported as present."""

    monkeypatch.setattr(
        subprocess, "run",
        lambda *a, **k: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )
    with pytest.raises(RuntimeError, match="Still missing after install"):
        check_dependencies(required=("this_package_does_not_exist_xyz",))
