from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import lightgbm
import matplotlib
import numpy as np
import pandas as pd
import pyarrow
import pyarrow.parquet as pq
import sklearn
from lightgbm import LGBMClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split

# Không mở cửa sổ biểu đồ khi chạy bằng terminal.
matplotlib.use("Agg")
import matplotlib.pyplot as plt


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SMOKE_TEST_TEMP_DIR = PROJECT_ROOT / "outputs" / "logs" / "environment_check"


def print_versions() -> None:
    """Print Python and package versions."""
    print("=" * 70)
    print("PACKAGE VERSIONS")
    print("=" * 70)
    print("Python:", sys.version)
    print("NumPy:", np.__version__)
    print("pandas:", pd.__version__)
    print("scikit-learn:", sklearn.__version__)
    print("LightGBM:", lightgbm.__version__)
    print("DuckDB:", duckdb.__version__)
    print("PyArrow:", pyarrow.__version__)
    print("Matplotlib:", matplotlib.__version__)


def create_test_data(n_rows: int = 2_000) -> pd.DataFrame:
    """Create a small synthetic binary-classification dataset."""
    rng = np.random.default_rng(42)

    f0 = rng.normal(size=n_rows)
    f1 = rng.normal(size=n_rows)
    treatment = rng.binomial(1, 0.7, size=n_rows)

    probability = 1 / (
        1 + np.exp(-(-1.5 + 0.8 * f0 - 0.4 * f1 + 0.3 * treatment))
    )
    conversion = rng.binomial(1, probability)

    return pd.DataFrame(
        {
            "f0": f0.astype("float32"),
            "f1": f1.astype("float32"),
            "treatment": treatment.astype("int8"),
            "conversion": conversion.astype("int8"),
        }
    )


def escape_sql_path(path: Path) -> str:
    """Escape a filesystem path for a DuckDB SQL string."""
    return str(path.resolve()).replace("\\", "/").replace("'", "''")


def test_csv_gz_to_parquet(temp_dir: Path, df: pd.DataFrame) -> Path:
    """Test pandas CSV.GZ output and DuckDB Parquet conversion."""
    csv_path = temp_dir / "test_data.csv.gz"
    parquet_path = temp_dir / "test_data.parquet"

    df.to_csv(
        csv_path,
        index=False,
        compression="gzip",
    )

    csv_sql_path = escape_sql_path(csv_path)
    parquet_sql_path = escape_sql_path(parquet_path)

    connection = duckdb.connect(database=":memory:")
    try:
        connection.execute(
            f"""
            COPY (
                SELECT *
                FROM read_csv_auto(
                    '{csv_sql_path}',
                    header = true
                )
            )
            TO '{parquet_sql_path}'
            (
                FORMAT PARQUET,
                COMPRESSION ZSTD
            )
            """
        )
    finally:
        connection.close()

    if not parquet_path.exists():
        raise RuntimeError("DuckDB không tạo được file Parquet.")

    print("✓ DuckDB đọc CSV.GZ và ghi Parquet thành công.")
    return parquet_path


def test_pyarrow_and_pandas(
    parquet_path: Path,
    expected_rows: int,
) -> pd.DataFrame:
    """Test reading Parquet with PyArrow and pandas."""
    parquet_file = pq.ParquetFile(parquet_path)

    if parquet_file.metadata.num_rows != expected_rows:
        raise RuntimeError(
            "Số dòng trong Parquet không khớp dữ liệu ban đầu."
        )

    print("✓ PyArrow đọc metadata Parquet thành công.")
    print("  Schema:")
    print(parquet_file.schema_arrow)

    loaded_df = pd.read_parquet(
        parquet_path,
        engine="pyarrow",
    )

    if len(loaded_df) != expected_rows:
        raise RuntimeError("pandas đọc sai số dòng từ Parquet.")

    required_columns = {"f0", "f1", "treatment", "conversion"}
    if not required_columns.issubset(loaded_df.columns):
        raise RuntimeError("Parquet thiếu cột cần thiết.")

    print("✓ pandas đọc Parquet bằng PyArrow thành công.")
    return loaded_df


def test_sklearn_and_lightgbm(df: pd.DataFrame) -> None:
    """Test train/test splitting and LightGBM training."""
    features = ["f0", "f1"]
    target = "conversion"

    x_train, x_test, y_train, y_test = train_test_split(
        df[features],
        df[target],
        test_size=0.25,
        random_state=42,
        stratify=df[target],
    )

    print("✓ scikit-learn train_test_split hoạt động.")

    model = LGBMClassifier(
        objective="binary",
        n_estimators=30,
        learning_rate=0.05,
        num_leaves=15,
        random_state=42,
        n_jobs=-1,
        verbosity=-1,
    )

    model.fit(x_train, y_train)

    probabilities = model.predict_proba(x_test)[:, 1]

    if not np.isfinite(probabilities).all():
        raise RuntimeError("LightGBM tạo prediction NaN hoặc infinite.")

    auc = roc_auc_score(y_test, probabilities)

    print("✓ LightGBM train và predict thành công.")
    print(f"  Test ROC-AUC: {auc:.4f}")


def test_matplotlib(temp_dir: Path) -> None:
    """Test saving a Matplotlib figure."""
    output_path = temp_dir / "test_plot.png"

    figure, axis = plt.subplots()
    axis.plot([0, 1, 2], [0, 1, 0])
    axis.set_title("Environment smoke test")
    figure.tight_layout()
    figure.savefig(output_path)
    plt.close(figure)

    if not output_path.exists():
        raise RuntimeError("Matplotlib không lưu được biểu đồ.")

    print("✓ Matplotlib tạo và lưu biểu đồ thành công.")


def main() -> None:
    """Run all environment smoke tests."""
    print_versions()

    SMOKE_TEST_TEMP_DIR.mkdir(parents=True, exist_ok=True)
    temp_dir = SMOKE_TEST_TEMP_DIR
    generated_paths = [
        temp_dir / "test_data.csv.gz",
        temp_dir / "test_data.parquet",
        temp_dir / "test_plot.png",
    ]
    for path in generated_paths:
        path.unlink(missing_ok=True)
    try:
        print("\n" + "=" * 70)
        print("FUNCTIONAL TESTS")
        print("=" * 70)

        test_df = create_test_data()

        parquet_path = test_csv_gz_to_parquet(
            temp_dir=temp_dir,
            df=test_df,
        )

        loaded_df = test_pyarrow_and_pandas(
            parquet_path=parquet_path,
            expected_rows=len(test_df),
        )

        test_sklearn_and_lightgbm(loaded_df)
        test_matplotlib(temp_dir)
    finally:
        for path in generated_paths:
            path.unlink(missing_ok=True)

    print("\n" + "=" * 70)
    print("✅ TẤT CẢ KIỂM TRA ĐỀU THÀNH CÔNG")
    print("=" * 70)
    print(
        "Môi trường đã sẵn sàng cho luồng "
        "CSV.GZ → DuckDB → Parquet → pandas/PyArrow → LightGBM."
    )


if __name__ == "__main__":
    main()
