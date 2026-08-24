# ADR: experiment artifacts

**Status:** PROVISIONAL  
**Decision authority:** Owner-approved authoritative decision_register.csv

## Context

The repository already writes tables, figures, prediction samples, LightGBM text
models, logs, and audit files below `outputs/`. Existing files are not endorsed as
current evidence. This ADR freezes names and stage semantics before any future
held-out evaluation.

From Sprint 2 empirical execution onward, the relevant notebook is the primary
human-readable protocol, execution, verification, and interpretation record.
The run artifacts governed here remain the authoritative machine-readable
evidence. Notebook-first therefore does not permit embedding untracked result
state in a notebook or weakening immutable-run, manifest, prediction, model, or
test-isolation requirements.

## Provisional decision

Every listed artifact path is relative to the immutable run root
`outputs/runs/<run_id>/`. Keep the existing subdirectory layout and two required
manifests beneath that root:

```text
audit/
figures/
logs/
models/
predictions/
tables/
```

Every executed run has a unique `run_id` matching its run-root directory. Each
machine-readable table records it in content; binary model/figure files and logs
are linked to it through both manifests. A completed run directory is immutable.
A rerun or correction creates a new `run_id`; no artifact is archived, replaced,
or overwritten inside a completed run.

### Required control artifacts

| Path | Stage and meaning |
|---|---|
| `audit/environment.json` | Pinned runtime/package/platform information. |
| `audit/run_config.json` | Input, sample, split, seed, method, and metric configuration. |
| `audit/pretest_freeze.json` | Immutable pre-release decisions and checksums required by document 06. |
| `audit/artifact_manifest.json` | Final list of produced artifacts, SHA-256 checksums, stage/population, and status. |
| `audit/audit_summary.csv` | One row per predeclared audit ID using document 03 status vocabulary. |
| `audit/audit_report.md` | Narrative rendered only from linked artifacts; no hard-coded result claims. |

### Required tables

```text
tables/data_summary.csv
tables/split_summary.csv
tables/ate_summary.csv
tables/response_diagnostics.csv
tables/validation_selection.csv
tables/uplift_at_k.csv
tables/model_summary.csv
```

### Optional / P1 tables (T14 decile/segment analysis)

Per D33, decile/segment tables are optional (T14/P1) reporting for every
estimator — useful, never a precondition for that estimator's acceptance or
promotion:

```text
tables/random_deciles.csv
tables/response_deciles.csv
tables/tlearner_deciles.csv
tables/xlearner_deciles.csv
```

If produced, a conditional promoted method uses exactly
`tables/drlearner_deciles.csv`; a Sprint 2 Causal Forest that passes all ADR
gates uses `tables/causal_forest_deciles.csv`; a later promoted S-Learner
would use `tables/slearner_deciles.csv`. None of these are required tables.

`split_summary.csv` may contain train/validation counts before freeze, but test
label counts/rates remain sealed or redacted until release. Every metric table
contains `run_id`, `stage` (`validation` or `test`), `population`, method, metric,
value, and unit directly or through an unambiguous normalized schema.

### Required figures

```text
figures/cumulative_uplift_rate.png
figures/cumulative_uplift_gain.png
figures/qini_curve.png
```

Optional / P1 (T14, D33): `figures/response_uplift_deciles.png`,
`figures/tlearner_uplift_deciles.png`, `figures/xlearner_uplift_deciles.png`,
and, if produced, `figures/drlearner_uplift_deciles.png` /
`figures/causal_forest_uplift_deciles.png`. Figures are presentations of
machine-readable tables, not primary evidence, and none of the decile figures
are required for any estimator's acceptance or promotion.

### Required models and predictions

```text
models/response_model.txt
models/tlearner_mu1.txt
models/tlearner_mu0.txt
predictions/test_predictions_sample.csv
```

X-Learner serialized components use
`models/xlearner_<component>.txt`; the freeze manifest must enumerate
the exact nuisance, pseudo-effect, final-stage, and propensity/weighting
components before release. This component manifest is mandatory because the
accepted estimator cannot be silently omitted.

Required X-Learner development artifacts are:

```text
audit/xlearner_fold_manifest.parquet
audit/xlearner_correctness.json
predictions/development/xlearner/seed_<seed>/oof_nuisance.parquet
predictions/development/xlearner/seed_<seed>/pseudo_outcomes.parquet
predictions/development/xlearner/seed_<seed>/validation_predictions.parquet
```

They use the formulas, primary two-fold/five-fold-sensitivity roles, seeds, and
validation-only acceptance rule frozen in document 05.

If DR-Learner is promoted, its exact serialized components must be listed in the
freeze manifest as `models/drlearner_<component>.<ext>` before release;
`OPEN_DECISION / PROMOTION_BLOCKER`: component names and serialization format.

If Sprint 2 Causal Forest passes every implementation gate, its serialized model
and score fields must use exact paths/schemas declared by the CF ADR and freeze
manifest. A cross-language model artifact is forbidden while the bridge decision
remains DEFERRED.

For every frozen model and required seed, the authoritative full row-level test
prediction artifact is locked at:

```text
outputs/runs/<run_id>/predictions/test/<model>/seed_<seed>/predictions.parquet
```

It must contain exactly the required identity/governance fields
`observation_id`, `model`, `model_version`, `seed`, `uplift_score`, `run_id`,
`split_hash`, `data_hash`, `config_hash`, and `code_hash`, plus only explicitly
versioned metric inputs approved by the data and metric contracts. The artifact
is retained as a permanent project record and its SHA-256 is recorded in
`audit/artifact_manifest.json`.

`observation_id` is the stable frozen observation identity from the split
manifest. It must remain identical across every model, seed, metric, and
reproduction artifact governed by that split. It identifies a released row for
artifact alignment and is never interpreted as a person or unique user.

`predictions/test_predictions_sample.csv` remains bounded inspection-only. It
must be deterministically derived from the corresponding authoritative Parquet
artifact, record that artifact's SHA-256 and sampling rule, contain no `visit` or
`exposure`, and remain unopened before test release. It is never authoritative
for metric recomputation.

Every final metric table and every bootstrap summary/draw artifact must reference
the exact SHA-256 hash or hashes of the authoritative prediction Parquet artifacts
from which it was computed. Manifest reconciliation fails if a metric or
bootstrap artifact cannot be traced to the exact frozen predictions.

### Required audit and robustness names

The following existing names are retained when their corresponding predeclared
procedure is run:

```text
audit/split_integrity.csv
audit/duplicate_audit.csv
audit/duplicate_rates.csv
audit/covariate_balance.csv
audit/treatment_predictability.csv
audit/ate_verification.csv
audit/model_probability_diagnostics.csv
audit/random_baseline_summary.csv
audit/random_baseline_draws.csv
audit/bootstrap_model_comparison.csv
audit/bootstrap_draws.csv
audit/repeated_seed_results.csv
audit/duplicate_sensitivity.csv
audit/metric_definitions.csv
```

Each file records `stage` and `population`. The current names do not authorize
test-based model selection: repeated-seed and duplicate-sensitivity artifacts are
development/validation-only and must be completed before freeze.

Duplicate-origin artifacts remain:

```text
audit/duplicate_origin/duplicate_origin_summary.csv
audit/duplicate_origin/duplicate_origin_report.json
```

The run log remains `logs/phase1_<YYYYMMDD_HHMMSS>.log`; its exact run-relative
path is captured in `audit/artifact_manifest.json`.

## Verification gate

Before pre-test release, a synthetic or development-only dry run must verify:

1. every required artifact for the frozen portfolio has exactly one declared
   run-relative path, stage, population, schema/version, and producer;
2. required X-Learner artifacts are present; conditional S/DR/Causal-Forest
   names appear only when their decision and promotion status permits them;
3. every run uses `outputs/runs/<run_id>/`, completed run directories are
   immutable, and a rerun cannot overwrite any prior artifact;
4. all machine-readable artifacts can be loaded and reconcile to the manifest;
5. checksums are computed after closing files;
6. model reload reproduces frozen development predictions within the exact
   reload rule and same-environment rerun tolerances in document 06;
7. no pre-release artifact reveals test labels, summaries, predictions, or
   metrics; and
8. narrative reports contain no unsupported hard-coded PASS/result text;
9. authoritative prediction Parquet artifacts use the locked model/seed path,
   contain every required field, and reconcile row identity and hashes; and
10. final metric and bootstrap artifacts reference the exact authoritative
    prediction artifact hashes.

## Status transition

Sprint 1 freezes this contract but does not require execution evidence. This ADR
becomes **ACCEPTED** only after a successful SMOKE development-only dry run (D30)
verifies paths, schemas, immutable run directories, manifest reconciliation,
model reload within the frozen tolerance, test isolation, and authoritative
prediction artifacts including downstream hash references. If any check fails or
remains undefined, the ADR remains **PROVISIONAL** and must be corrected before
any RESOURCE gate or FULL execution.

## Fallback

If any required name, schema, lineage, immutable-run rule, authoritative
prediction rule, hash reference, or verification check remains unresolved, do
not release test data. The fallback is to retain development outputs as
non-final, correct the artifact contract, run another development-only dry run
under a new `run_id`, and create a new freeze manifest.

## Consequences

- Existing repository names are preserved where their semantics are valid.
- New manifests make the freeze and artifact lineage explicit.
- Ambiguous legacy files remain non-authoritative until linked by a verified
  manifest.
- This ADR follows the SMOKE status-transition rule above (D30); no Sprint 1
  execution evidence or present PASS is required or asserted.

## Artifact retention policy

### Retain as permanent project records

Retain for the lifetime of the project repository:

- Sprint specifications and ADRs;
- decision-register snapshot;
- data manifest and source checksums;
- split and fold manifests;
- configuration files;
- run manifests;
- code/git hashes;
- package/environment lock;
- selected validation records;
- pre-test freeze record;
- final frozen full row-level test prediction files for every shortlisted model
  and required training seed, retained with the reproducibility package;
- final metrics, bootstrap outputs and stability tables;
- final model artifacts;
- incident and invalidation records;
- reproduction commands.

### Retain until final report approval and reproducibility verification

- OOF nuisance predictions;
- validation predictions;
- pseudo-outcomes;
- robustness predictions;
- non-selected model artifacts;
- scale-gate reports;
- development logs;
- pre-registered robustness model artifacts.

These may be archived or deleted only after:

1. the final report is accepted;
2. the frozen experiment can be reproduced;
3. their deletion is recorded in a cleanup manifest.

### Reconstructible temporary artifacts

The following may be deleted after successful run validation:

- temporary batches;
- interrupted partial files;
- duplicated format-conversion caches;
- model-library temporary files;
- failed-run outputs not used in any reported result.

Deletion requires:

- confirmation that the artifact is not referenced by a run manifest;
- preservation of the failure/incident log;
- no overwrite of a successful immutable run folder.

### Immutability

- Run folders are immutable after completion.
- A rerun creates a new run ID.
- No successful artifact may be silently overwritten.
- A completed run's folder is never edited in place, and its files are never
  re-derived to "fix" them. Every correction takes exactly one of two forms,
  chosen by what the defect actually affects. If it is unclear which form
  applies, it is Class A.

#### Class A: scientific correction

The defect affects, or could plausibly affect, the model, its configuration,
the analyzed population, predictions, metrics, or the lineage connecting them.
The affected run remains immutable and untouched; its invalidation is recorded
externally (in a new record referencing it, never inside it), and a complete
replacement governed run is produced under a new `run_id`. No partial
correction is authorized for this class.

#### Class B: audit-only erratum

The defect affects only metadata or reporting fields -- run-level bookkeeping,
labeling, or measurement of something ancillary to the result -- and does not
change, and is proven not to change, any model, configuration, population,
prediction, or metric value. An audit-only erratum is authorized only when all
of the following hold:

1. **Scientific hash reconciliation.** Every applicable scientific artifact of
   the affected run is proven unchanged by recomputing its SHA-256 from the
   still-untouched original file and comparing it to the hash already recorded
   by that run's own artifact manifest -- not merely asserted. This covers, at
   minimum and by category: every serialized model artifact; every
   authoritative development/prediction artifact; every metric or table
   artifact carrying a scientific result; the frozen `config_hash` (recomputed
   from the run's own recorded configuration and checked for self-consistency,
   not merely copied); the data/split/population identity fields (checked
   against their own authoritative sources); and the code/metric-definition
   identity fields already frozen and recorded (checked against the current
   source files). The run's own `run_config.json` may itself contain the
   defective field being corrected, so its overall file hash is never treated
   as proof that its *content* is trustworthy; each of its unaffected
   scientific fields is reconciled individually against its own independent
   source.
2. **Untouched original.** The original run's folder, and every file inside
   it, remains byte-for-byte unchanged -- confirmed by recomputing every
   listed artifact's hash and confirming the file set on disk exactly matches
   the file set the original manifest recorded, with nothing added or
   removed.
3. **Erratum record.** A new, separately governed erratum record is created,
   under its own new `run_id` and the same immutable-run-root convention as
   any other governed run, naming: the affected run's `run_id`; the exact
   field path(s) being superseded; the old (incorrect) value(s); the corrected
   value(s); the reason; and the scientific-hash-reconciliation result that
   authorized the erratum.
4. **Fail closed.** If any scientific hash or identity check in (1) does not
   match, the erratum is refused and the defect is handled as Class A instead.
5. **Superseding scope.** The erratum record supersedes only the explicitly
   named field(s), for reporting purposes only. The original run's files
   remain the sole physical record of what was actually produced at execution
   time; a reader reconciles a corrected value by consulting the original run
   and its erratum record together. Scientific results remain authoritative
   only for as long as, and precisely because, (1) proved them unchanged.
6. **Never scientific.** An erratum may never alter, in effect or in
   appearance, model performance, ranking metrics, the analyzed population,
   configuration, predictions, or any methodological decision. Any correction
   that would touch those is Class A, regardless of how it is framed.

#### Erratum-run control artifacts

An erratum run is itself a governed run under `outputs/runs/<run_id>/` and is
bound by the same immutable-run-root rule as any other. It uses exactly the
required control artifacts applicable to a run that performs no data-engineering,
audit-gate, or held-out work: `audit/environment.json`, `audit/run_config.json`,
and `audit/artifact_manifest.json`, plus `audit/erratum.json` carrying the
correction and reconciliation content above. `audit/pretest_freeze.json` and
`audit/audit_summary.csv`/`audit/audit_report.md` are not produced -- consistent
with every other non-freeze, non-audit-gate governed run in this project, since
those three are scoped to Stage 5 pre-test freeze and to docs/03's HG-01..HG-07
audit-ID vocabulary respectively, neither of which an erratum run executes. An
erratum run produces no model, prediction, or metric artifact of its own.

#### Resource-measurement validity (forward rule)

A resource-evidence field may be labeled a peak-memory measurement only when it
comes from a valid stage-scoped peak measurement: either (a) the measured stage
ran within its own clean process boundary and the value comes from that
process's OS/runtime historical-peak counter, or (b) a correctly scoped
continuous sampler actually tracked the running maximum throughout the stage.
Two arbitrary before/after instantaneous RSS (or equivalent) samples must never
be labeled a peak or a peak-delta. If a stage-specific peak cannot be
established by either valid mechanism, the field is recorded as
`NOT_COMPARABLE` or `UNAVAILABLE` with a stated reason, not fabricated or
approximated. Wall time, completion status, and OOM/termination status remain
reportable independently of whether a peak-memory value is available. This
rule is platform-neutral and does not mandate a specific OS or runtime
mechanism (Kaggle sessions and local environments may use different valid
mechanisms).
