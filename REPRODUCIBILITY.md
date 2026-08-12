# Reproducibility

## Current phase

The current phase is **Sprint 2 — T01 ready for implementation**. Sprint 1
specifications remain frozen, and T01-D01 through T01-D06 are accepted in
`docs/adr/ADR-T01-data-engineering.md`. This guide does not authorize model
training or construction or inspection of held-out evaluation. T01 production
implementation and verification have not yet been performed.

## Environment

The repository declares Python dependencies in `requirements.txt`:

```powershell
python -m pip install -r requirements.txt
```

No exact Python version or fully pinned environment lockfile has been frozen.
Dependency ranges are therefore a setup aid, not proof of byte-identical
reproduction. Exact interpreter, package, platform, threading, and hardware
metadata remain `OPEN_FOR_SPRINT2` and must be captured in immutable run
manifests.

## Local data setup

Follow [`data/README.md`](data/README.md). Raw and processed data remain local and
must not be committed. Future executable runs use an explicit populated manifest
derived from `configs/data_manifest.example.json`; they must not discover input
through filename or directory heuristics.

The populated local manifest records authoritative release metadata, paths,
SHA-256 checksums, schema, conversion lineage, and tool versions. Placeholder
values in the example are not execution evidence.

## Notebook-first execution record

From Sprint 2 onward, the task notebook is the primary human-readable research
and execution record. It must state the question and protocol before code, expose
important operations and checks, link immutable machine-readable outputs, and
separate observations from decisions and unsupported conclusions.

For T01, the primary artifact is
`notebooks/02_data_engineering_pipeline.ipynb`. Its environment cell records the
interpreter, relevant packages, platform, CPU and memory with each run. A helper
under `src/`, `scripts/`, or `tests/` is optional and is introduced only when
reuse, regression verification, an authoritative contract, or avoidance of
unreasonable notebook duplication justifies it. Notebooks must not become thin
wrappers around opaque helper packages.

## Phase boundaries

- **Sprint 1:** freeze specifications, ADR boundaries, documentation, and
  non-secret configuration templates.
- **Sprint 2:** reconcile implementation, execute synthetic/development audits,
  validate objectives, run scale gates, compare candidates on validation, and
  create the pre-test executable freeze.
- **Sprint 3:** release and evaluate the held-out test once under the frozen
  portfolio and metric protocol.

No test feature, label, prediction, summary, or metric may select an upstream
choice before the pre-test freeze.

## Randomness and configuration

Seeds, fold counts, split procedures, learner parameters, package versions, and
artifact schemas must be explicit and versioned. The authoritative defaults are
in `docs/06_experiment_protocol.md`; an example run configuration cannot override
them.

Every future completed run writes to a unique immutable
`outputs/runs/<run_id>/` root and records data, split, fold, config, code, and
artifact hashes. A rerun creates a new run ID. Validation selects permitted
choices; the test never selects a model or seed.

## Data and artifact policy

The following remain outside version control:

- raw and processed datasets;
- populated local manifests containing machine-specific or restricted paths;
- generated outputs, models, predictions, pseudo-outcomes, bootstrap draws, and
  logs; and
- caches, virtual environments, notebook checkpoints, and local IDE state.

Only notebooks, source code, specifications, approved ADRs, justified
tests/fixtures without real rows, and non-secret configuration examples are
candidates for version control.

## Known limitations

- No exact environment lockfile is currently available.
- Canonical compressed-source, decompressed-CSV, and CSV-to-Parquet semantic
  identity evidence is recorded. T01-D04 now uses an operation-specific resource
  failure rule with no universal fixed RAM percentage; T01-D06 selects ZSTD with
  the retained benchmarked row-group layout. Production pipeline verification,
  model correctness, calibration values, and artifact dry-run evidence remain
  open.
- LightGBM is a provisional default framework; exact packages, objectives,
  hyperparameters, and serialization must pass Sprint 2 gates.
- Causal Forest implementation and DR-Learner promotion remain gated.
- No official held-out evaluation is asserted by Sprint 1.
