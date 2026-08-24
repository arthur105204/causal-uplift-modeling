from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.data import EXPECTED_COLUMNS, FEATURE_COLUMNS, load_csv, load_parquet, save_parquet


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
