#!/usr/bin/env python
"""T11 CLI: run one stage (robustness | gcp_parity | full) of the unified
Causal Forest runner against the frozen T05 split.

Thin wrapper only -- every orchestration, checkpointing, and partition-loading
decision lives in ``src/causal_forest_runner.py``. This script's job is
argument parsing, loading the manifest-selected processed dataset and the
frozen T05 split membership identically to the notebook's own loading cell
(never the whole-population ``materialize_pandas`` pattern the T11 CODE PLAN
correction replaced), and invoking ``run_stage()``.

Example (NOT executed by this IMPLEMENT phase -- infrastructure only):
    .venv/Scripts/python.exe scripts/t11_run_stage.py \\
        --stage robustness --model-seed 123 --population-size 500000 \\
        --sampling-seed 42 --diagnostic-sample-size 100000 \\
        --run-id t11_robustness_seed123_20260901T000000Z_000000 \\
        --i-understand-this-executes-real-data-model-training
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "src" / "data.py").is_file():
            return candidate
    raise RuntimeError(f"Could not locate repository root above {start}")


REPO_ROOT = _find_repo_root(Path(__file__).resolve())
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

STAGE_CHOICES = ("smoke", "robustness", "gcp_parity", "full")


def _load_train_validation_ids(repo_root: Path):
    """Load and verify the frozen T05 split membership, exactly as the T11
    notebook section does -- never derived, never regenerated here."""

    import pandas as pd

    from src.split import SplitContractError, SplitDataset, membership_hash

    t05_config_path = repo_root / "configs" / "t05_split.json"
    t05_config = json.loads(t05_config_path.read_text(encoding="utf-8"))
    if t05_config["lifecycle_state"] != "T05_SPLIT_ACCEPTED":
        raise SplitContractError(f"T05 split is not accepted: {t05_config['lifecycle_state']}")

    t05_run_manifest_path = repo_root / t05_config["lifecycle_state_evidence"]["authorizing_run_manifest"]
    t05_run_root = t05_run_manifest_path.parent.parent
    membership = pd.read_csv(t05_run_root / "audit" / "split_membership.csv")
    observed_hash = membership_hash(membership)
    expected_hash = t05_config["lifecycle_state_evidence"]["membership_sha256"]
    if observed_hash != expected_hash:
        raise SplitContractError(
            f"Split membership hash mismatch: expected {expected_hash}, observed {observed_hash}"
        )

    split_dataset = SplitDataset(membership=membership)
    return split_dataset.train_ids(), split_dataset.validation_ids()


def _load_dataset(repo_root: Path):
    from src.data import load_selector, open_processed_dataset

    selector_path = repo_root / "configs" / "data_manifest.json"
    selector = load_selector(selector_path, repo_root)
    dataset = open_processed_dataset(selector)
    return dataset, selector.payload["processed_sha256"]


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--stage", required=True, choices=STAGE_CHOICES)
    parser.add_argument("--run-id", required=True, help="Unique <task>_<UTC timestamp>_<micros> run id")
    parser.add_argument("--population-size", type=int, required=True)
    parser.add_argument("--sampling-seed", type=int, default=42)
    parser.add_argument("--model-seed", type=int, required=True)
    parser.add_argument("--diagnostic-sample-size", type=int, required=True)
    parser.add_argument(
        "--validation-scoring-size",
        type=int,
        default=None,
        help=(
            "Bound VALIDATION scoring to a deterministic stratified subset of this size "
            "(drawn with --sampling-seed) instead of the complete frozen VALIDATION cohort. "
            "Intended for --stage smoke, which exercises the production DAG cheaply rather than "
            "scoring the full population; omit for robustness/gcp_parity/full."
        ),
    )
    parser.add_argument(
        "--run-root-base",
        type=Path,
        default=None,
        help="Defaults to <repo_root>/outputs/runs",
    )
    parser.add_argument(
        "--config-json",
        type=Path,
        default=None,
        help="Optional override of FROZEN_CAUSAL_FOREST_CONFIG (path to a JSON object)",
    )
    parser.add_argument(
        "--active-sentinel-path",
        type=Path,
        default=None,
        help="Defaults to <run_root_base>/.t11_<stage>_active_run_id.txt",
    )
    parser.add_argument(
        "--i-understand-this-executes-real-data-model-training",
        dest="confirmed",
        action="store_true",
        help=(
            "Required confirmation flag -- this script fits a real Causal Forest on real "
            "development data and is not a dry run."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if not args.confirmed:
        print(
            "Refusing to run: pass --i-understand-this-executes-real-data-model-training to "
            "confirm this invocation is an authorized, owner-approved real-data T11 execution.",
            file=sys.stderr,
        )
        return 2

    from src.causal_forest_baseline import FROZEN_CAUSAL_FOREST_CONFIG
    from src.causal_forest_runner import StageRequest, run_stage, stratified_subset_ids, write_active_sentinel

    run_root_base = args.run_root_base or (REPO_ROOT / "outputs" / "runs")
    run_root = run_root_base / args.run_id

    dataset, dataset_sha256 = _load_dataset(REPO_ROOT)
    train_ids, validation_ids = _load_train_validation_ids(REPO_ROOT)

    if args.validation_scoring_size is not None:
        validation_ids = stratified_subset_ids(
            dataset,
            validation_ids,
            population_size=args.validation_scoring_size,
            sampling_seed=args.sampling_seed,
        )

    config = FROZEN_CAUSAL_FOREST_CONFIG
    if args.config_json is not None:
        config = json.loads(args.config_json.read_text(encoding="utf-8"))

    sentinel_path = args.active_sentinel_path or (run_root_base / f".t11_{args.stage}_active_run_id.txt")
    write_active_sentinel(sentinel_path, args.run_id)

    request = StageRequest(
        stage=args.stage,
        run_id=args.run_id,
        run_root=run_root,
        dataset=dataset,
        dataset_sha256=dataset_sha256,
        train_ids=train_ids,
        validation_ids=validation_ids,
        population_size=args.population_size,
        sampling_seed=args.sampling_seed,
        model_seed=args.model_seed,
        diagnostic_sample_size=args.diagnostic_sample_size,
        config=config,
    )

    result = run_stage(request)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
