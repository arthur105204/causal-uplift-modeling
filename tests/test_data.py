from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.data import (
    CSV_FILENAME,
    EXPECTED_COLUMNS,
    FEATURE_COLUMNS,
    PRIMARY_OUTCOME,
    SECONDARY_OUTCOME,
    SUPPORTED_OUTCOMES,
    TREATMENT_COLUMN,
    load_csv,
    load_parquet,
    resolve_csv_path,
    resolve_outcome,
    save_parquet,
)


def test_resolve_outcome_defaults_to_conversion_unchanged() -> None:
    """No argument (and explicitly passing None) must preserve the existing
    conversion-only behavior this pipeline had before outcome became
    configurable."""

    assert resolve_outcome() == PRIMARY_OUTCOME
    assert resolve_outcome(None) == PRIMARY_OUTCOME


def test_resolve_outcome_accepts_conversion_explicitly() -> None:
    assert resolve_outcome("conversion") == PRIMARY_OUTCOME


def test_resolve_outcome_selects_visit() -> None:
    assert resolve_outcome("visit") == SECONDARY_OUTCOME


def test_resolve_outcome_rejects_unsupported_values() -> None:
    for bogus in ("exposure", "click", "conversion ", "Conversion", ""):
        with pytest.raises(ValueError):
            resolve_outcome(bogus)


def test_supported_outcomes_is_exactly_conversion_and_visit() -> None:
    assert SUPPORTED_OUTCOMES == (PRIMARY_OUTCOME, SECONDARY_OUTCOME)


def test_outcome_selection_leaves_features_and_treatment_untouched() -> None:
    """Selecting a different outcome must be orthogonal to which columns are
    features (f0..f11) or the treatment column -- resolve_outcome only names
    the Y column, never touches X or T."""

    before_features, before_treatment = FEATURE_COLUMNS, TREATMENT_COLUMN
    resolve_outcome("visit")
    assert FEATURE_COLUMNS == before_features
    assert TREATMENT_COLUMN == before_treatment
    assert TREATMENT_COLUMN not in FEATURE_COLUMNS
    assert SECONDARY_OUTCOME not in FEATURE_COLUMNS
    assert PRIMARY_OUTCOME not in FEATURE_COLUMNS


def _synthetic_frame(rows: int = 20) -> pd.DataFrame:
    """A frame shaped like the notebook's post-split partitions: features,
    treatment, row_id, and BOTH outcome columns present at once -- exactly
    what train/validation/test.parquet actually contain (see
    docs/secondary_visit_outcome_experiment_plan.md Phase 1 audit finding:
    both outcomes are already persisted together)."""

    data = {f: list(range(rows)) for f in FEATURE_COLUMNS}
    data[TREATMENT_COLUMN] = [i % 2 for i in range(rows)]
    data[PRIMARY_OUTCOME] = [(i // 3) % 2 for i in range(rows)]  # deliberately different pattern
    data[SECONDARY_OUTCOME] = [(i // 5) % 2 for i in range(rows)]  # from PRIMARY_OUTCOME's
    data["row_id"] = list(range(rows))
    return pd.DataFrame(data)


def test_selecting_visit_changes_only_which_column_is_y() -> None:
    """This is what every model-stage cell in kaggle_execution.ipynb now
    does: Y = frame[OUTCOME_COLUMN]. Switching OUTCOME_COLUMN must select a
    different column's values -- not silently return the same data."""

    frame = _synthetic_frame()
    y_conversion = frame[resolve_outcome("conversion")]
    y_visit = frame[resolve_outcome("visit")]
    assert not y_conversion.equals(y_visit), "fixture's conversion/visit columns must actually differ"
    assert y_conversion.equals(frame[PRIMARY_OUTCOME])
    assert y_visit.equals(frame[SECONDARY_OUTCOME])


def test_selecting_visit_leaves_features_treatment_and_row_ids_byte_identical() -> None:
    """Reading a different Y off the same frame must never perturb X, T, or
    row_id -- this is the guarantee that lets the visit sensitivity
    experiment reuse conversion's exact physical row partition."""

    frame = _synthetic_frame()
    features_before = frame[list(FEATURE_COLUMNS)].copy()
    treatment_before = frame[TREATMENT_COLUMN].copy()
    row_id_before = frame["row_id"].copy()

    for outcome in ("conversion", "visit"):
        _ = frame[resolve_outcome(outcome)]  # the only thing a model stage reads differently
        pd.testing.assert_frame_equal(frame[list(FEATURE_COLUMNS)], features_before)
        pd.testing.assert_series_equal(frame[TREATMENT_COLUMN], treatment_before)
        pd.testing.assert_series_equal(frame["row_id"], row_id_before)


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
