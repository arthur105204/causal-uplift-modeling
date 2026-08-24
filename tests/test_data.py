from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.data import (
    CSV_FILENAME,
    EXPECTED_COLUMNS,
    FEATURE_COLUMNS,
    load_csv,
    load_parquet,
    resolve_csv_path,
    save_parquet,
)


def _touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")
    return path


def test_resolve_csv_prefers_any_attached_kaggle_dataset_slug(tmp_path: Path) -> None:
    """The dataset slug must not be hardcoded -- whatever the user names it,
    the CSV should be found."""

    kaggle_input = tmp_path / "input"
    expected = _touch(kaggle_input / "someone-elses-slug-name" / CSV_FILENAME)
    found = resolve_csv_path(kaggle_input=kaggle_input, local_dir=tmp_path / "nonexistent")
    assert found == expected


def test_resolve_csv_searches_nested_directories_inside_a_dataset(tmp_path: Path) -> None:
    kaggle_input = tmp_path / "input"
    expected = _touch(kaggle_input / "slug" / "nested" / "deeper" / CSV_FILENAME)
    assert resolve_csv_path(kaggle_input=kaggle_input, local_dir=tmp_path / "none") == expected


def test_resolve_csv_falls_back_to_local_data_raw(tmp_path: Path) -> None:
    local = tmp_path / "raw"
    expected = _touch(local / CSV_FILENAME)
    assert resolve_csv_path(kaggle_input=tmp_path / "no-kaggle-here", local_dir=local) == expected


def test_resolve_csv_raises_an_actionable_error_when_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="attach a dataset"):
        resolve_csv_path(kaggle_input=tmp_path / "nope", local_dir=tmp_path / "also-nope")


def _frame(rows: int = 8) -> pd.DataFrame:
    payload = {name: [float(i) + col / 100 for i in range(rows)] for col, name in enumerate(FEATURE_COLUMNS)}
    payload.update({
        "treatment": [i % 2 for i in range(rows)],
        "conversion": [(i // 2) % 2 for i in range(rows)],
        "visit": [(i + 1) % 2 for i in range(rows)],
        "exposure": [i % 2 for i in range(rows)],
    })
    return pd.DataFrame(payload)


def test_load_csv_reads_expected_columns(tmp_path: Path) -> None:
    frame = _frame()
    path = tmp_path / "data.csv"
    frame.to_csv(path, index=False)
    loaded = load_csv(path)
    assert set(EXPECTED_COLUMNS).issubset(loaded.columns)
    assert len(loaded) == len(frame)


def test_load_csv_rejects_missing_columns(tmp_path: Path) -> None:
    frame = _frame().drop(columns=["f11"])
    path = tmp_path / "data.csv"
    frame.to_csv(path, index=False)
    with pytest.raises(ValueError, match="missing"):
        load_csv(path)


def test_load_csv_rejects_empty_file(tmp_path: Path) -> None:
    path = tmp_path / "empty.csv"
    _frame(rows=0).to_csv(path, index=False)
    with pytest.raises(ValueError, match="no rows"):
        load_csv(path)


def test_parquet_roundtrip_preserves_values(tmp_path: Path) -> None:
    frame = _frame(rows=25)
    path = tmp_path / "processed.parquet"
    save_parquet(frame, path)
    reloaded = load_parquet(path)
    pd.testing.assert_frame_equal(reloaded, frame)
