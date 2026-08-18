#!/usr/bin/env python
"""T06 verification: run the synthetic metric cross-checks and persist the
immutable metric-definition evidence at outputs/runs/<run_id>/audit/metric_definitions.csv.

No real or held-out Criteo data is touched -- every check here uses the same
synthetic fixture family as tests/test_metrics.py. This script's one job is to
run that verification standalone (not depending on pytest at run time) and
write the governed, run-scoped evidence per ADR-experiment-artifacts (all
artifact paths are relative to outputs/runs/<run_id>/ -- no global
outputs/audit/ copy is written).
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


def _find_repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "src" / "data.py").is_file():
            return candidate
    raise RuntimeError(f"Could not locate repository root above {start}")


REPO_ROOT = _find_repo_root(Path(__file__).resolve())
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.data import finalize_artifact_manifest, sha256_file, write_json_new, write_text_new  # noqa: E402
import src.metrics as metrics  # noqa: E402
import src.metrics_reference as metrics_reference  # noqa: E402


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _good_fixture():
    """Same construction as tests/test_metrics.py's _good_fixture(): N=20,
    strictly alternating treatment, effect concentrated in the top half."""
    n = 20
    source_row_id = np.arange(n, dtype=np.int64)
    scores = (n - source_row_id).astype(np.float64)
    treatment = (source_row_id % 2 == 0).astype(np.float64)
    in_top_half = source_row_id < 10
    outcome = np.where(
        treatment == 1,
        np.where(in_top_half, 1.0, 0.0),
        np.where(in_top_half, 0.0, 1.0),
    )
    return scores, treatment, outcome, source_row_id


def run_verification() -> dict[str, bool]:
    """Cross-check reference vs. production and the frozen random-ranking
    reference draw count, on synthetic fixtures only."""

    scores, treatment, outcome, source_row_id = _good_fixture()
    prod = metrics.evaluate_ranking(scores, treatment, outcome, source_row_id)
    ref = metrics_reference.evaluate_ranking(scores, treatment, outcome, source_row_id)

    checks = {
        "qini_area_matches_reference": abs(prod.qini_area - ref.qini_area) < 1e-9,
        "qini_above_random_matches_reference": abs(prod.qini_above_random - ref.qini_above_random) < 1e-9,
        "good_ranking_scores_above_random": prod.qini_above_random > 0,
        "uplift_at_10pct_hand_computed_value": abs(prod.uplift_at_k["10pct"] - 1.0) < 1e-9,
    }

    distribution = metrics.random_ranking_reference_distribution(treatment, outcome, source_row_id)
    checks["random_ranking_reference_has_exactly_200_draws"] = len(distribution) == 200

    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError(f"T06 verification failed: {failed}")
    return checks


def main() -> None:
    checks = run_verification()

    run_id = datetime.now(timezone.utc).strftime("t06_metrics_%Y%m%dT%H%M%SZ_%f")
    run_root = REPO_ROOT / "outputs" / "runs" / run_id
    run_root.mkdir(parents=True, exist_ok=False)

    try:
        git_head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, check=True, capture_output=True, text=True
        ).stdout.strip()
        git_dirty = bool(
            subprocess.run(
                ["git", "status", "--porcelain"], cwd=REPO_ROOT, check=True, capture_output=True, text=True
            ).stdout.strip()
        )
    except (OSError, subprocess.CalledProcessError):
        git_head, git_dirty = None, None

    write_json_new(
        run_root,
        "audit/run_config.json",
        {
            "run_id": run_id,
            "created_at_utc": _utc_now(),
            "stage": "t06_metrics_verification",
            "src_metrics_sha256": sha256_file(REPO_ROOT / "src" / "metrics.py"),
            "src_metrics_reference_sha256": sha256_file(REPO_ROOT / "src" / "metrics_reference.py"),
            "src_metrics_common_sha256": sha256_file(REPO_ROOT / "src" / "metrics_common.py"),
            "git_head": git_head,
            "git_dirty": git_dirty,
            "real_or_held_out_data_accessed": False,
        },
    )

    definitions = metrics.metric_definitions()
    definitions_sha256 = hashlib.sha256(json.dumps(definitions, sort_keys=True).encode()).hexdigest()

    def _flatten(value: object) -> object:
        return value if isinstance(value, (str, int, float, bool)) or value is None else json.dumps(value)

    # ADR-experiment-artifacts requires every machine-readable table to record
    # run_id, stage, and population -- not just the run-level run_config.json.
    definitions_stage = "t06_metrics_verification"
    definitions_population = "synthetic_fixtures_only"
    definitions_rows = pd.DataFrame(
        [
            {
                "field": key,
                "value": _flatten(value),
                "run_id": run_id,
                "stage": definitions_stage,
                "population": definitions_population,
            }
            for key, value in definitions.items()
        ]
        + [
            {
                "field": "definitions_sha256",
                "value": definitions_sha256,
                "run_id": run_id,
                "stage": definitions_stage,
                "population": definitions_population,
            }
        ]
    )
    write_text_new(run_root, "audit/metric_definitions.csv", definitions_rows.to_csv(index=False, lineterminator="\n"))

    summary = {
        "run_id": run_id,
        "status": "COMPLETED_T06_METRICS_VERIFIED",
        "definitions_sha256": definitions_sha256,
        "verification_checks": checks,
        "real_or_held_out_data_accessed": False,
    }
    write_json_new(run_root, "audit/t06_summary.json", summary)

    finalize_artifact_manifest(
        run_root,
        run_id=run_id,
        final_status=summary["status"],
        created_at_utc=_utc_now(),
        stage="t06_metrics_verification",
        population="synthetic_fixtures_only",
        external_artifacts=[
            {
                "path": "src/metrics.py",
                "role": "reusable_t06_contract",
                "sha256": sha256_file(REPO_ROOT / "src" / "metrics.py"),
                "status": "PASS",
            },
            {
                "path": "src/metrics_reference.py",
                "role": "reusable_t06_reference",
                "sha256": sha256_file(REPO_ROOT / "src" / "metrics_reference.py"),
                "status": "PASS",
            },
            {
                "path": "src/metrics_common.py",
                "role": "reusable_t06_shared_scaffolding",
                "sha256": sha256_file(REPO_ROOT / "src" / "metrics_common.py"),
                "status": "PASS",
            },
        ],
    )

    print(f"Run: {run_id}")
    print(f"Metric definitions hash: {definitions_sha256}")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
