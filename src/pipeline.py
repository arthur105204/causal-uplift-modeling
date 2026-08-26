"""Stage-runner functions for the Kaggle execution notebook.

Each function here is a straight extraction of one notebook stage's
orchestration (cache-check, fit, evaluate, persist) out of
notebooks/kaggle_execution.ipynb, so the notebook reads as a data-science
narrative instead of an engineering log. No modeling, evaluation, or
artifact-format logic changes as part of this move -- every call below still
goes through src.data / src.preprocessing / src.models / src.evaluation /
src.artifacts exactly as the notebook cells used to.

The T-Learner/X-Learner fitting stage is deliberately NOT here -- it stays
inline in the notebook. That call site is where a real bug lived once (see
README's Methodology notes and tests/test_artifacts.py's raw-frame guard):
fit_x_learner must receive the RAW train frame, never an already-transformed
one, and keeping that exact call visible in the notebook -- not tucked
inside a helper -- is a deliberate guardrail against silently reintroducing
it, not an inconsistency in how aggressively this module hides plumbing.
"""

from __future__ import annotations

import gc
import time

import pandas as pd

from src.artifacts import (
    artifact_is_fresh, config_fingerprint, experiment_metadata,
    load_json, load_pickle, save_csv, save_json, save_pickle, stage_dir,
)
from src.data import (
    CATEGORICAL_FEATURES, CONTINUOUS_FEATURES, FEATURE_COLUMNS,
    PRIMARY_OUTCOME, SECONDARY_OUTCOME, TREATMENT_COLUMN,
    basic_summary, load_csv, load_parquet, resolve_csv_path, save_parquet,
)
from src.evaluation import compute_ate, evaluate_ranking, response_diagnostics
from src.models import fit_causal_forest, fit_response_model, predict, predict_causal_forest_tau
from src.preprocessing import (
    CausalForestCategoricalEncoder, LightGBMFeatureTransform, train_validation_test_split,
)
from src.reporting import package_ranking_artifacts


def stage_cache_hit(meta_path, data_signature: str, *, outcome: str | None = None, extra_files=()) -> bool:
    """True if a stage's cached artifacts are safe to reuse: its metadata is
    fresh (src.artifacts.artifact_is_fresh) and every extra required file
    (typically model.pkl) is present."""

    if not artifact_is_fresh(meta_path, data_signature, outcome=outcome):
        return False
    return all(p.is_file() for p in extra_files)


def run_data_stage(config: dict, sample_rows: int | None, seed: int, env_info: dict) -> str:
    """Load-or-compute Stage 1's artifacts (split, dataset/feature summaries).
    Returns the data signature every downstream stage's own artifacts are
    checked against."""

    data_dir = stage_dir("data")
    split_cfg = config["split"]
    signature = config_fingerprint(sample_rows, seed, split_cfg, config["data"])
    run_config_path = data_dir / "run_config.json"
    parquet_paths = [data_dir / f"{name}.parquet" for name in ("train", "validation", "test")]

    if stage_cache_hit(run_config_path, signature, extra_files=parquet_paths):
        return signature

    stage_start = time.perf_counter()
    csv_path = resolve_csv_path()
    frame = load_csv(csv_path)

    missing_features = [f for f in FEATURE_COLUMNS if f not in frame.columns]
    assert not missing_features, f"missing features: {missing_features}"
    assert TREATMENT_COLUMN in frame.columns, f"missing treatment column {TREATMENT_COLUMN!r}"
    assert PRIMARY_OUTCOME in frame.columns, f"missing outcome column {PRIMARY_OUTCOME!r}"
    assert set(frame[TREATMENT_COLUMN].unique()) <= {0, 1}, "treatment must be binary"
    assert set(frame[PRIMARY_OUTCOME].unique()) <= {0, 1}, "conversion must be binary"

    summary = basic_summary(frame)
    ate = compute_ate(frame[TREATMENT_COLUMN], frame[PRIMARY_OUTCOME])
    by_treatment = frame.groupby(TREATMENT_COLUMN)[[PRIMARY_OUTCOME, SECONDARY_OUTCOME]].mean()

    if sample_rows is not None and sample_rows < len(frame):
        from sklearn.model_selection import train_test_split as _tts
        strata = frame[TREATMENT_COLUMN].astype(str) + "_" + frame[PRIMARY_OUTCOME].astype(str)
        frame, _ = _tts(frame, train_size=sample_rows, random_state=seed, stratify=strata)
        frame = frame.reset_index(drop=True)

    train_frame, val_frame, test_frame = train_validation_test_split(
        frame,
        train_fraction=split_cfg["train_fraction"],
        validation_fraction=split_cfg["validation_fraction"],
        test_fraction=split_cfg["test_fraction"],
        seed=seed,
    )
    keep_cols = list(FEATURE_COLUMNS) + [TREATMENT_COLUMN, PRIMARY_OUTCOME, SECONDARY_OUTCOME]
    partitions = {"train": train_frame, "validation": val_frame, "test": test_frame}
    split_summary = {}
    for name, part in partitions.items():
        out = part.loc[:, keep_cols].reset_index(drop=True)
        out.insert(0, "row_id", out.index.to_numpy())
        save_parquet(out, data_dir / f"{name}.parquet")
        split_summary[name] = {
            "n_rows": int(len(part)),
            "treatment_rate": float(part[TREATMENT_COLUMN].mean()),
            "conversion_rate": float(part[PRIMARY_OUTCOME].mean()),
            "visit_rate": float(part[SECONDARY_OUTCOME].mean()),
        }

    feature_rows = []
    for f in CONTINUOUS_FEATURES:
        s = train_frame[f].astype("float64")
        desc = s.describe(percentiles=[0.25, 0.5, 0.75])
        feature_rows.append({
            "feature": f, "kind": "continuous", "n_unique": int(s.nunique()),
            "mean": float(desc["mean"]), "std": float(desc["std"]), "min": float(desc["min"]),
            "p25": float(desc["25%"]), "p50": float(desc["50%"]), "p75": float(desc["75%"]), "max": float(desc["max"]),
            "top_category": None, "top_category_share": None,
        })
    for f in CATEGORICAL_FEATURES:
        vc = train_frame[f].astype("float64").value_counts()
        feature_rows.append({
            "feature": f, "kind": "categorical", "n_unique": int(vc.shape[0]),
            "mean": None, "std": None, "min": None, "p25": None, "p50": None, "p75": None, "max": None,
            "top_category": float(vc.index[0]), "top_category_share": float(vc.iloc[0] / len(train_frame)),
        })
    save_csv(pd.DataFrame(feature_rows), data_dir / "feature_summary.csv")

    dataset_summary = {
        "n_rows": summary["n_rows"], "n_cols": summary["n_cols"],
        "n_features": len(FEATURE_COLUMNS),
        "continuous_features": list(CONTINUOUS_FEATURES), "categorical_features": list(CATEGORICAL_FEATURES),
        "treatment_counts": {str(k): int(v) for k, v in summary["treatment_counts"].items()},
        "conversion_rate": summary["conversion_rate"],
        "visit_rate": float(frame[SECONDARY_OUTCOME].mean()),
        "conversion_rate_by_treatment": {str(k): float(v) for k, v in by_treatment[PRIMARY_OUTCOME].items()},
        "visit_rate_by_treatment": {str(k): float(v) for k, v in by_treatment[SECONDARY_OUTCOME].items()},
        "ate": {"ate": ate.ate, "se": ate.se, "ci_95_low": ate.ci_95_low, "ci_95_high": ate.ci_95_high,
                "relative_lift": ate.relative_lift},
        "csv_path": str(csv_path), "csv_size_mb": csv_path.stat().st_size / 1024**2,
        "sample_rows_used": None if sample_rows is None else int(len(frame)),
    }
    save_json(dataset_summary, data_dir / "dataset_summary.json")
    save_json(split_summary, data_dir / "split_summary.json")
    save_json({
        "data_signature": signature, "seed": seed, "sample_rows": sample_rows,
        "split": split_cfg, "env": env_info,
        "runtime_seconds": time.perf_counter() - stage_start,
    }, run_config_path)

    del frame, train_frame, val_frame, test_frame, by_treatment
    gc.collect()
    return signature


def get_lgbm_transform(data_signature: str) -> LightGBMFeatureTransform:
    """Load-or-fit the LightGBM categorical-feature transform. Used by the
    response model and the T-Learner; the X-Learner fits its own fold-local
    transforms internally and does not use this one."""

    prep_dir = stage_dir("preprocessing")
    meta_path = prep_dir / "lgbm_transform_metadata.json"
    transform_path = prep_dir / "lgbm_transform.joblib"
    if stage_cache_hit(meta_path, data_signature, extra_files=[transform_path]):
        return load_pickle(transform_path)

    train_frame = load_parquet(stage_dir("data") / "train.parquet")
    transform = LightGBMFeatureTransform().fit(train_frame)
    save_pickle(transform, transform_path)
    save_json({
        "data_signature": data_signature,
        "continuous_features": list(CONTINUOUS_FEATURES),
        "categorical_features": list(CATEGORICAL_FEATURES),
    }, meta_path)
    del train_frame
    gc.collect()
    return transform


def run_baseline_stage(config: dict, outcome_column: str, seed: int, data_signature: str) -> dict:
    """Load-or-fit Stage 2 (response model). Returns its metrics dict."""

    baseline_dir = stage_dir("baseline", outcome=outcome_column)
    meta_path = baseline_dir / "metrics.json"
    if stage_cache_hit(meta_path, data_signature, outcome=outcome_column, extra_files=[baseline_dir / "model.pkl"]):
        return load_json(meta_path)

    data_dir = stage_dir("data")
    transform = get_lgbm_transform(data_signature)
    train_frame = load_parquet(data_dir / "train.parquet")
    val_frame = load_parquet(data_dir / "validation.parquet")
    test_frame = load_parquet(data_dir / "test.parquet")

    X_train, X_val, X_test = (transform.transform(f) for f in (train_frame, val_frame, test_frame))
    Y_train, Y_val, Y_test = (f[outcome_column] for f in (train_frame, val_frame, test_frame))
    T_train, T_val, T_test = (f[TREATMENT_COLUMN] for f in (train_frame, val_frame, test_frame))
    row_id_val, row_id_test = val_frame["row_id"], test_frame["row_id"]
    del train_frame
    gc.collect()

    start = time.perf_counter()
    model = fit_response_model(X_train, Y_train, X_val, Y_val, seed=seed)
    runtime = time.perf_counter() - start

    val_scores = predict(model, X_val)
    test_scores = predict(model, X_test)
    diagnostics = response_diagnostics(val_scores, Y_val)
    val_metrics = evaluate_ranking(val_scores, T_val, Y_val)
    test_metrics = evaluate_ranking(test_scores, T_test, Y_test)

    from sklearn.calibration import calibration_curve
    from sklearn.metrics import precision_recall_curve, roc_curve
    fpr, tpr, _ = roc_curve(Y_val, val_scores)
    precision, recall, _ = precision_recall_curve(Y_val, val_scores)
    frac_pos, mean_pred = calibration_curve(Y_val, val_scores, n_bins=10, strategy="quantile")
    save_csv(pd.DataFrame({"fpr": fpr, "tpr": tpr}), baseline_dir / "roc_curve.csv")
    save_csv(pd.DataFrame({"precision": precision, "recall": recall}), baseline_dir / "pr_curve.csv")
    save_csv(pd.DataFrame({"mean_predicted": mean_pred, "fraction_positive": frac_pos}),
              baseline_dir / "calibration_curve.csv")

    save_pickle(model, baseline_dir / "model.pkl")
    metrics = package_ranking_artifacts(
        baseline_dir, "Response LightGBM", val_metrics, test_metrics,
        val_scores, test_scores, T_val, Y_val, T_test, Y_test,
        row_id_val, row_id_test, runtime,
        extra_metrics={
            **experiment_metadata(outcome_column, seed=seed, data_signature=data_signature),
            "best_iteration": int(model.best_iteration),
            "val_roc_auc": diagnostics.roc_auc, "val_average_precision": diagnostics.average_precision,
            "val_log_loss": diagnostics.log_loss,
        },
    )

    del X_train, X_val, X_test, val_frame, test_frame
    gc.collect()
    return metrics


def get_cf_encoder(config: dict, data_signature: str) -> CausalForestCategoricalEncoder:
    """Load-or-fit the Causal Forest categorical encoder at the configured
    K. A cached encoder fit at a different K is never reused, even if its
    data_signature matches."""

    prep_dir = stage_dir("preprocessing")
    meta_path = prep_dir / "cf_encoder_metadata.json"
    encoder_path = prep_dir / "cf_encoder.joblib"
    k = config["causal_forest"]["categorical_top_k"]
    if stage_cache_hit(meta_path, data_signature, extra_files=[encoder_path]) and load_json(meta_path).get("k") == k:
        return load_pickle(encoder_path)

    train_frame = load_parquet(stage_dir("data") / "train.parquet")
    encoder = CausalForestCategoricalEncoder(k=k).fit(train_frame)
    save_pickle(encoder, encoder_path)
    save_json({"data_signature": data_signature, "k": k}, meta_path)
    del train_frame
    gc.collect()
    return encoder


def run_causal_forest_stage(config: dict, outcome_column: str, seed: int, data_signature: str) -> dict:
    """Load-or-fit Stage 4 (Causal Forest). Returns its metrics dict, and
    always (re)writes resource_evidence.json alongside it -- see Stage 4's
    markdown for why that evidence matters."""

    cf_dir = stage_dir("causal_forest", outcome=outcome_column)
    meta_path = cf_dir / "metrics.json"
    if stage_cache_hit(meta_path, data_signature, outcome=outcome_column, extra_files=[cf_dir / "model.pkl"]):
        return load_json(meta_path)

    data_dir = stage_dir("data")
    encoder = get_cf_encoder(config, data_signature)

    train_frame = load_parquet(data_dir / "train.parquet")
    T_train, Y_train = train_frame[TREATMENT_COLUMN], train_frame[outcome_column]
    X_train_cf = encoder.transform(train_frame)
    encoded_feature_count = int(X_train_cf.shape[1])
    n_train_rows = int(len(X_train_cf))
    del train_frame
    gc.collect()

    start = time.perf_counter()
    model = fit_causal_forest(X_train_cf, T_train, Y_train, seed=seed)
    runtime = time.perf_counter() - start
    del X_train_cf
    gc.collect()

    val_frame = load_parquet(data_dir / "validation.parquet")
    T_val, Y_val, row_id_val = val_frame[TREATMENT_COLUMN], val_frame[outcome_column], val_frame["row_id"]
    X_val_cf = encoder.transform(val_frame)
    val_scores = predict_causal_forest_tau(model, X_val_cf)
    val_metrics = evaluate_ranking(val_scores, T_val, Y_val)
    del val_frame, X_val_cf
    gc.collect()

    test_frame = load_parquet(data_dir / "test.parquet")
    T_test, Y_test, row_id_test = test_frame[TREATMENT_COLUMN], test_frame[outcome_column], test_frame["row_id"]
    X_test_cf = encoder.transform(test_frame)
    test_scores = predict_causal_forest_tau(model, X_test_cf)
    test_metrics = evaluate_ranking(test_scores, T_test, Y_test)
    del test_frame, X_test_cf
    gc.collect()

    save_pickle(model, cf_dir / "model.pkl")
    cf_config = config["causal_forest"]
    save_json({
        "categorical_top_k": cf_config["categorical_top_k"],
        "encoded_feature_count": encoded_feature_count,
        "n_train_rows": n_train_rows,
        "estimated_encoded_matrix_bytes": n_train_rows * encoded_feature_count * 8,
        "n_estimators": cf_config["n_estimators"], "honest": cf_config["honest"],
        "min_samples_leaf": cf_config["min_samples_leaf"], "max_samples": cf_config["max_samples"],
        "subforest_size": cf_config["subforest_size"], "n_jobs": cf_config["n_jobs"],
        "runtime_seconds": runtime,
    }, cf_dir / "resource_evidence.json")

    metrics = package_ranking_artifacts(
        cf_dir, "Causal Forest", val_metrics, test_metrics,
        val_scores, test_scores, T_val, Y_val, T_test, Y_test,
        row_id_val, row_id_test, runtime,
        extra_metrics=experiment_metadata(outcome_column, seed=seed, data_signature=data_signature),
    )
    return metrics
