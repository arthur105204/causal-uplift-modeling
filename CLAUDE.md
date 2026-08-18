# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

A governed research project — causal uplift / CATE modeling on CRITEO-UPLIFTv2.1 — not a
software product. Most of the repository is frozen specification; the executable part is a
small, deliberately conservative data layer plus a Kaggle-first notebook series.

`AGENTS.md` is the authoritative operating contract for agents in this repo. Read it before
any non-trivial work. The rules below are the parts most likely to be violated by accident.

**Kaggle is the primary execution environment.** The active notebook series lives under
`kaggle/00_project_overview.ipynb` through `kaggle/07_final_story.ipynb`; GitHub Issue #20
(`[MASTER]`) is the authoritative execution plan and task-to-notebook mapping. `notebooks/legacy/`
holds the pre-reset notebooks, retained as historical evidence — their accepted results are
inherited, not re-derived, and they are not edited going forward.

## Commands

The virtual environment at `.venv/` has the dependencies; the system Python does not.
Run everything from the repository root — `src.data` / `src.audit` resolve via the root on
`sys.path`, so `python -m pytest` (not bare `pytest`) is required.

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pytest tests/ -q                       # full suite
.venv\Scripts\python.exe -m pytest tests/test_data.py -q           # one file
.venv\Scripts\python.exe -m pytest tests/test_audit.py::test_feature_infinity_is_rejected -q   # one test
.venv\Scripts\jupyter.exe lab                                      # notebooks
```

There is no linter, formatter, or pytest config file. Tests are a regression aid, not the
verification gate: verification is the applicable HARD_GATE set (`docs/03`) plus a fresh-kernel
Run All reconciled to expected artifacts. `tests pass != clean Run All succeeds` (`AGENTS.md` §10).

## Authority order (do not silently override)

CLAUDE.md is operational guidance only and never overrides the decision register, frozen
contracts/protocols, accepted ADRs/evidence, or Issue wording.

1. `docs/decision_register.csv` — owner-approved decisions (`D01`–`D29`), in Vietnamese.
2. Numbered contracts in `docs/` (`01_causal_contract`, `02_data_contract`, `06_experiment_protocol`,
   `07_metric_specification`, …) and ACCEPTED ADRs in `docs/adr/`.
3. Accepted empirical evidence, then Issue wording, then existing code.

`docs/index.md` maps the documents and their statuses. Changing implementation to match code is
backwards: change the highest affected source first, with owner approval.

## Frozen essentials

Enforced in code by `src/data.py` and re-asserted in every notebook:

- `X` is exactly `f0`-`f11`, in order — nothing else, ever.
- `T` = `treatment` (assignment/ITT, not exposure). Primary `Y` = `conversion`; `visit` is a
  secondary outcome in a separate pipeline.
- `exposure` is audit-only: excluded from `X`, eligibility, filtering, and the treatment
  definition.
- `_source_row_id` is a zero-based CSV row ordinal used for provenance/alignment. It is not a
  person identifier and must never enter `X`.
- D09 primary analytical precision is `float64`; `float32` is a sensitivity projection only.
- Keep every released row by default (D07, `docs/04`). Duplicate/dedup/weighting analyses are
  sensitivity analyses only; rows may be excluded only on a predeclared hard-integrity gate failure.
- Outer split 70/15/15, joint `(T,Y)` stratification, seed `42`; D23 scale rungs
  50K → 500K → 2M → full.
- Held-out test data is untouchable until T17. No unofficial held-out diagnostics, no tuning on
  test-derived information. If an operation would read held-out performance, stop.

Task dependency (per Issue #4 and MASTER #20): **T03-A** (pre-split evidence only) → **T05**
(create and seal the frozen outer split) → **T03-B** (split-identity integrity: source-row
disjointness, train/validation overlap) → **T04** (model-facing missing-value handling). **T03-C**
(the 2,000-draw randomization calibration) is mandatory but off the blocking path — it may run in
parallel any time after T05, and must complete before T16. T03-A must not construct the split, run
final calibration, access held-out evidence, or start successor work.

Predicted uplift is not a true ITE; balance diagnostics do not prove randomization; `f0`-`f11`
are anonymized and have no known business meaning.

## Data path architecture

Every data-consuming task inherits the same chain — never bypass a link, never discover input by
glob, filename order, or directory heuristic:

```
configs/data_manifest.json (git-ignored local selector)
  → load_selector()                 validates roles, columns, conversion settings, hashes
  → validate_source_identity()      raw CSV + .csv.gz SHA-256, exact header, sizes
  → convert_csv_to_parquet()        GENERATION: streamed Arrow, appends _source_row_id
  → validate_processed_parquet()    schema, row-group layout, ZSTD, ordinal continuity, semantics
  → promote_processed_with_rollback()  → data/processed/criteo-uplift-v2.1.parquet
  → open_processed_dataset()        CONSUMPTION: fails closed unless the expected SHA-256 matches
```

`configs/data_manifest.example.json` is the committed template; the populated
`configs/data_manifest.json` is git-ignored and must exist for any real local run. During
generation `processed_sha256` may be `null`; before consumption it must be pinned from completed
run evidence — `open_processed_dataset()` refuses to open Parquet without it.

The manifest is environment-local: its **paths** differ between a Kaggle session (which mounts a
versioned input dataset, not this selector file) and a local checkout, but its **checksums are
environment-invariant** — identity is verified the same way in both places. Kaggle notebooks in
`kaggle/` detect their environment and fall back to `/kaggle/input` when no local manifest exists;
they do not require `configs/data_manifest.json` to run their feasibility/EDA-level diagnostics.

`SemanticHasher` produces a batch-boundary-independent digest per column so CSV and Parquet can be
compared for value/order/null identity independently of physical layout. Semantic identity is
mandatory; byte-identical physical output is only claimed within one environment.

## Run-artifact governance

D21 (configs + immutable run manifests) applies to **consequential experiments**: model training,
persisted predictions, model comparison, bootstrap uncertainty, frozen evaluation, and the T17
held-out run. For those, machine-readable evidence lives in immutable
`outputs/runs/<run_id>/{audit,tables,figures,predictions,metrics,models}/` (git-ignored), written
with the governed writers — `write_json_new`, `write_text_new`, `write_bytes_new` — which refuse to
overwrite and refuse to write to a run whose `audit/artifact_manifest.json` already carries a
`COMPLETED*`/`FAILED*` status. `finalize_artifact_manifest()` hashes everything and closes the run.
A rerun never mutates a run: it mints a new `<task>_<UTC timestamp>_<micros>` run id. Failed-run
evidence is kept, not deleted.

This machinery is **not** required around routine EDA tables, temporary figures, or one-off
exploratory calculations — applying the full immutable-manifest ceremony there is disproportionate
and not what D21 intends. Use judgment: if a number will be compared, reused downstream, or cited
in a final claim, it earns run-scoped evidence; if it is illustrative or exploratory, it does not.

## Notebook-first, not notebook-only

`kaggle/00_project_overview.ipynb` through `kaggle/07_final_story.ipynb` are the primary research
artifacts (see Issue #20 for the exact task-to-notebook mapping). Each must expose the question,
protocol, core computation, verification, observations, interpretation, and limitations — never
become a thin wrapper around opaque helpers. Each notebook reads as a first-time presentation of
the current study: it does not narrate earlier versions, prior runs, or redesign history.

Code moves into `src/` only when reuse, correctness, or an authoritative contract justifies it —
which is why `src/data.py` holds hashing/manifest/Parquet mechanics and `src/audit.py` holds
permutation, folds, balance/predictability statistics, and Monte Carlo order statistics, while the
statistical narrative stays in the notebook. Notebooks bootstrap `REPO_ROOT` onto `sys.path`
themselves and hash their own source into run evidence.

## Working rules

The user drives an explicit phase lifecycle — `[TUTOR]` → `[CODE PLAN]` → `[IMPLEMENT]` →
`[VERIFY]` → `[CLEAN RUN]` → `[REVIEW]` → `[ACCEPT]`. Execute only the requested phase; do not
auto-advance. During `[REVIEW]`, falsify and report findings — do not edit unless asked. Full
lifecycle in `AGENTS.md` §3–§14.

One writer per working tree; a reviewing agent reports findings and does not edit (`AGENTS.md` §15).

Successful execution is not verification. Check the task-relevant invariants listed in
`AGENTS.md` §10.

Never `git add .`. Commit, push, Issue closure, and starting the next task are separate actions
that require explicit authorization. Never commit raw/processed data, the populated selector, or
`outputs/` artifacts.
