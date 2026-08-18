# Experiment protocol

## Authority and non-result status

This document is the source of truth for sampling, splitting, development,
selection, cross-fitting, robustness, pre-test freeze, final refit, held-out
evaluation, and reproducibility. It defines no actual run, audit, or metric
result and does not itself authorize test release.

The owner-approved [`decision_register.csv`](decision_register.csv) has higher
precedence. This protocol implements its accepted roles and cannot silently
remove or redefine them.

The protocol inherits the [causal contract](01_causal_contract.md),
[data contract](02_data_contract.md), [audit gates](03_assumption_and_audit_spec.md),
[duplicate protocol](04_duplicate_profile_protocol.md),
[methodology roles](05_methodology_scope.md), and
[metric conventions](07_metric_specification.md).

## Fixed defaults

| Item | Sprint 1 convention |
|---|---|
| Scale progression | D30 requires `SMOKE → [RESOURCE GATE(S) if required] → FULL`; SMOKE is mandatory for every task, zero/one/multiple RESOURCE gates are predeclared per estimator's resource risk, and exact SMOKE/RESOURCE workload sizes are task-local config values frozen before execution, not global constants. Superseded from the prior fixed `50,000 → 500,000 → 2,000,000 → full` D23 progression (`D23`, superseded 2026-08-18); T01-T06 evidence produced under D23 is retained unchanged. |
| Data tools | Pandas + PyArrow are the D20 default. Polars or DuckDB may replace a failing operation only after the ADR-data-stack benchmark verifies row alignment, schema, identity, runtime, and peak memory at the applicable scale. |
| Numeric precision | `float64` is the D09 primary analytical precision; `float32` is sensitivity-only unless a new owner-approved decision changes it. |
| Sampling seed | `42`. |
| Outer split | `70%` train, `15%` validation, `15%` held-out test. |
| Outer stratification | Joint `(T,Y)` stratum. |
| Outer split seed | `42`, used for both split stages. |
| Primary model seed | `42`. |
| Robustness model seeds | `42`, `123`, `2026`. |
| Random-ranking seed | `42`. |
| Random-permutation seed | `42`. |
| Diagnostic null calibration | Document 03's design-consistent assignment reference; initial `2,000` replications from master seed `42`, with deterministic stored sub-seeds and Monte Carlo intervals. Generated values are development artifacts, not universal constants. |
| DR cross-fitting | Five folds, joint `(T,Y)` stratification, fold seed `42`; required only if DR is implemented. |
| X-Learner cross-fitting | Primary: deterministic two-fold training-only cross-fitting, joint `(T,Y)` stratification, fold seed `42`. Five-fold is a predeclared validation sensitivity/promotion candidate, never an automatic replacement. |
| Causal Forest | Accepted `MAIN_COMPARATOR` planned for Sprint 2; exact implementation is provisional and test-ineligible until all CF ADR gates pass. |
| Cross-language CF bridge | `DEFERRED` unless the CF implementation ADR proves it is required. |
| Bootstrap | `500` paired, treatment-arm-stratified resamples; models are not retrained inside draws. |
| Bootstrap seed | `42`. |
| Random permutations | `200`. |
| Early stopping | Up to `50` rounds on validation during development only. |
| Missing features | Preserve missing `f0`–`f11` values for LightGBM native handling; no imputation or added missingness feature. Missingness is still reported. |
| Secondary outcome | If present and binary, `visit` is evaluated only as a predeclared secondary robustness outcome. It never replaces primary `Y=conversion`, enters `X`, filters rows, or selects a model. |

The D30 SMOKE/RESOURCE stages are resource/correctness promotion gates, not
candidate sample sizes from which a favorable metric may be selected. Every
attempted stage and its disposition is recorded before moving forward. The
final evaluated population must be fixed before model selection and cannot be
chosen by comparing validation or test metrics.

## Partition roles

### Training partition

Used to fit candidate core models, inner cross-fitted nuisance models, and any
development-only candidate. It may be resampled or folded only under predeclared
training procedures.

### Validation partition

Used for early stopping, fixed hyperparameter/method selection, DR promotion,
robustness comparison, threshold selection, and determining final fixed iteration
counts. Reuse is accepted as development selection and must not be described as
held-out final evaluation.

### Held-out test partition

Used once after pre-test freeze to evaluate the frozen portfolio and predeclared
metrics. It is not used for early stopping, calibration choice, clipping,
duplicate policy, audit thresholds, feature/method/hyperparameter selection,
cross-fitting, robustness retraining, or promotion.

The split builder may use `T` and `Y` mechanically to create the declared joint
strata and to return opaque HARD_GATE support status. Before release, test labels,
test outcome/arm summaries, and test-derived diagnostics remain sealed from the
development process. Pre-release `split_summary.csv` must omit or seal test label
counts/rates; they may be populated only after authorized release.

## Required sequence

### Stage 0 — Input and audit gates

1. Select the manifest-identified Parquet and record lineage.
2. Apply HG-01 through HG-07 from document 03.
3. Apply the fixed missing-value rule above, preserve primary `float64`
   precision, keep all rows under the primary duplicate policy, and freeze the
   diagnostic-calibration algorithm without test information. Generated
   development-data thresholds are locked later, before the pre-test executable
   freeze.
4. Preserve `_source_row_id` as the original zero-based canonical source-row
   ordinal through conversion and any sampling; do not renumber retained rows
   before splitting.
5. Execute only the current D30 SMOKE/RESOURCE stage. Promote to the next
   predeclared stage, and finally to FULL, only after its predeclared
   correctness/resource evidence passes; do not introduce an unregistered
   sample-size fallback.
6. If `visit` is present, validate its binary label schema and predeclare its
   secondary-outcome tables before development. Do not use it for primary model
   fitting, promotion, threshold selection, or population filtering.

Any HARD_GATE failure stops the run.

### Stage 1 — Split and seal

1. Create the seeded 70/15/15 joint `(T,Y)` split once.
2. Verify identity disjointness and row accounting.
3. Materialize or hash the exact ordered membership of each partition.
4. Seal held-out test features and labels. Only permitted schema and opaque
   support-gate results may be exposed before release.

No resplit is allowed because validation results are unfavorable.

### Stage 2 — Core development and validation selection

1. Fit the LightGBM response comparator and T-Learner on training rows with seed
   `42`.
2. Use validation labels for early stopping and development metrics only.
3. Generate the seeded random validation ranking and theoretical-random
   reference under document 07.
4. Fit the accepted X-Learner main comparator with deterministic two-fold training-only
   cross-fitting. Every pseudo-effect uses out-of-fold nuisance predictions;
   signed/continuous pseudo-effects use a regression objective, never binary
   classification. Five-fold may be run only as the predeclared sensitivity or
   promotion candidate in document 05. Apply the sign, OOF coverage, leakage,
   support, synthetic, and serialization gates there.
5. Record fixed learner parameters and selected iteration counts for response,
   T-Learner, and every X-Learner component.
6. The S-Learner remains deferred and is not silently substituted for response
   or T-Learner.

### Stage 3 — Stretch comparator and robustness

All work in this stage is completed before freeze and uses no test information.

- If DR-Learner is attempted, fit nuisances with five-fold training-only
  cross-fitting and apply every promotion gate in document 05 on validation.
- Causal Forest is an accepted Sprint 2 main comparator, not a Sprint 1 stretch
  method. In Sprint 2 it follows the implementation-selection and correctness,
  synthetic-effect, leakage, honesty/support, resource, validation, seed, and
  pre-test-freeze gates in its ADR. It cannot enter held-out evaluation before
  all gates pass and cannot be silently omitted before they are evaluated.
- Refit candidates for robustness seeds `42`, `123`, and `2026`, scoring only
  validation. The primary method/model seed remains `42`; robustness does not
  select a favorable seed.
- Run any duplicate keep/drop/weighting sensitivity only within training and
  validation. Test-based deduplication sensitivity is prohibited.
- Run the predeclared 500-draw paired arm-stratified validation bootstrap on
  already-computed validation scores when required for DR promotion; do not
  retrain inside bootstrap draws.
- Run document 03's predeclared design-consistent randomization calibration,
  probability diagnostics, and permitted overlap/stability checks on development
  data only. Finalize the generated 95th/99th-percentile values, Monte Carlo
  intervals, code revision, and artifact hashes before Stage 5.

Current code paths that compute repeated-seed or duplicate-policy comparisons on
the test partition are non-conforming for selection and must be moved to this
stage or disabled before test release.

### Stage 4 — Final refit before freeze

After all selection and robustness decisions are final:

1. Fix the portfolio, parameters, primary seed, tie rules, and iteration counts.
2. Refit the response model and both T-Learner arm models once on combined
   training plus validation rows with primary seed `42`, using the fixed
   iteration counts and no early stopping.
3. Rebuild the X-Learner's two-fold cross-fitted nuisance predictions on
   combined training plus validation with all formulas, weights, folds, and
   iteration counts fixed, then fit its final effect stages. Use five folds only
   if that predeclared candidate was selected on validation before freeze. No
   test row enters a nuisance or effect-stage fit.
4. If DR was promoted, rebuild its five-fold cross-fitted nuisance predictions on
   combined training plus validation with all choices fixed, then fit its final
   CATE stage. No test row enters a nuisance or final-stage fit.
5. In Sprint 2, refit Causal Forest only if every implementation and validation
   promotion gate has passed; use the selected honesty/sample-splitting protocol
   and no test row.
6. Serialize the final models and verify reload/prediction equivalence on a
   development-only fixture.

All retraining required by robustness, promotion, or finalization ends here.

### Stage 5 — Pre-test freeze

Write `outputs/runs/<run_id>/audit/pretest_freeze.json` and lock:

- input manifest/checksums, actual sample size, precision, and duplicate policy;
- exact partition membership hashes and split/stratification procedure;
- `X/T/Y` and forbidden columns;
- accepted/required/promoted/deferred estimator list and estimator roles,
  explicitly including X-Learner as a main comparator, Causal Forest as a
  Sprint 2 main comparator with provisional implementation status, DR-Learner as
  a conditional stretch comparator, and S-Learner as deferred;
- preprocessing/missing-value behavior;
- learner parameters, selected iteration counts, primary and robustness seeds;
- cross-fitting folds/seeds and resolved X-Learner and DR nuisance,
  pseudo-effect, propensity/weighting, and final-stage conventions;
- document 03's randomization-reference method or labeled conditional-permutation
  approximation, replication seeds/count, generated diagnostic percentiles,
  Monte Carlo intervals, and calibration-artifact hashes;
- exact metric formulas, coverages, tie rules, curve grid, uncertainty procedure,
  and promotion/claim rules;
- whether optional `visit` is available and schema-valid, plus its secondary
  aggregate/ranking summaries and the rule that they cannot alter primary
  selection or claims;
- exact artifact names, code revision if available, environment, and test-release
  authority; and
- verification-gate evidence for every PROVISIONAL ADR.

Any unresolved unconditional `FREEZE_BLOCKER` prevents test release. A
`PROMOTION_BLOCKER` prevents only the affected optional method from entering the
frozen portfolio; explicitly applying its documented fallback exclusion closes
that optional branch for the core freeze. Any other `OPEN_DECISION / ...BLOCKER`
follows its stated scope and must be resolved or have its documented fallback
recorded in the freeze manifest.

### Stage 6 — One-time held-out evaluation

1. Verify the freeze manifest and final-model checksums.
2. Release test features for scoring and then labels for the single evaluation.
3. Score every frozen method without refitting or calibration.
4. Compute only document 07 metrics and the predeclared 200 random permutations.
5. Compute the predeclared paired arm-stratified 500-draw bootstrap on fixed test
   predictions for reporting uncertainty; no model is retrained.
6. If frozen as available, compute the secondary assigned-arm `visit` contrast
   and secondary ranking summaries using the already-frozen primary method
   rankings. Label them secondary; they cannot change the selected portfolio or
   primary `conversion` conclusion.
7. Write the exact artifacts in the artifact ADR and close the manifest with
   checksums.

Held-out findings are reported even when unfavorable. They cannot cause a method,
seed, metric, cutoff, or model to be replaced on the same test partition.

## Cross-fitting consistency

- The outer test split is never a cross-fitting fold.
- X-Learner nuisance predictions used to construct signed pseudo-effects are
  out-of-fold for every development row. Fold assignment uses run-local row
  identity, joint `(T,Y)` stratification, primary two folds, and seed `42`.
  Five-fold assignments are retained separately when the predeclared
  sensitivity/promotion candidate is run.
- DR nuisance predictions used to construct a pseudo-outcome are out-of-fold for
  every development row.
- Fold assignment uses run-local row identities, joint `(T,Y)` stratification,
  five folds, and seed `42`; assignments are stored or hashed.
- Fold count, seed, nuisance definitions, propensity clipping/support behavior,
  and final-stage learner are frozen before DR validation comparison.
- T-Learner and response use the outer train/validation process, not DR folds.
- Causal Forest uses only the honesty/sample-splitting behavior selected by its
  provisional ADR; a cross-language bridge remains deferred unless that ADR
  proves it is required.

## Seed policy

Seeds govern stochastic sampling, splitting, model fitting, cross-fitting,
random ranking, permutations, and bootstrap. Each component records its seed
separately even when the value is `42`. No seed is changed or selected after
observing validation or test performance. Seed robustness reports all configured
seeds; it does not promote the best seed.

## Failure and rerun policy

- A pre-release HARD_GATE or ADR-gate failure is corrected and rerun without
  test access; failed evidence is retained.
- A resource failure stops the current D30 SMOKE/RESOURCE stage and records the
  failure. Work may remain at the last passed stage for development, but
  held-out scope cannot be silently changed to an unregistered sample size;
  progression or deferral requires the applicable predeclared gate and
  owner-approved decision.
- A software failure after test release may be rerun only if the frozen models,
  predictions, metric code, and inputs are unchanged and the rerun is purely
  mechanical. Otherwise the current test is consumed and a genuinely new test
  population is required for another final evaluation.
- No post-test robustness retraining is permitted. New ideas return to a new
  development cycle and cannot claim confirmation on the consumed test.

## Artifact contract

Exact paths and conditional method names are controlled by
[ADR-experiment-artifacts](adr/ADR-experiment-artifacts.md). An artifact filename
does not authorize test use; its stage, population, run ID, and manifest linkage
must also conform to this protocol.

## Reproducibility and equivalence policy

### Exact equality required

The following must match exactly:

- dataset identifier and checksum;
- data, config, code, split, fold, manifest, and artifact hashes;
- schema and column roles;
- observation IDs;
- train/validation/test membership;
- fold membership;
- configuration files;
- seeds;
- package lock or environment identifier;
- row counts;
- artifact paths;
- manifest fields;
- model shortlist.

Any mismatch is a STOP condition.

### Artifact reload equivalence

Reloading the same saved prediction or model artifact must reproduce:

- the same artifact checksum when the file is unchanged;
- the same row IDs;
- the same row count;
- the same score orientation;
- no missing or non-finite predictions; and
- exact stored prediction values and metadata when the unchanged frozen
  prediction artifact is reloaded.

Unchanged frozen files, manifests, and serialized artifacts are byte-for-byte
identical. Re-executing training is a separate same-environment rerun comparison
and uses the floating-point defaults below.

### Floating-point rerun tolerance

Provisional default for the same pinned environment, data, config and
seed:

- prediction arrays:
  `rtol = 1e-6`, `atol = 1e-8`;
- scalar metrics computed from the same frozen predictions:
  absolute difference no greater than
  `1e-8 × max(1, abs(reference_metric))`.

These are technical equivalence tolerances, not statistical
significance thresholds.

### Verification gate

The tolerances must be tested on the SMOKE run.

If they fail:

1. investigate threading, batching, library and hardware causes;
2. record the observed deterministic envelope;
3. update the ADR before promotion to any RESOURCE gate or to FULL;
4. do not silently relax tolerances after test access.

### Stochastic variation

Differences caused by intentionally different training seeds are not
reproducibility failures. They are reported as training instability.

This higher-precedence experiment policy supplies the frozen defaults and
acceptance rule for the base-learner, data-stack, Causal Forest, and artifact ADR
verification gates. It supersedes any lower-precedence `OPEN_DECISION` or
`FREEZE_BLOCKER` wording about numeric reproducibility tolerance; Sprint 2 gate
evidence may trigger only the documented pre-RESOURCE-gate/pre-FULL amendment
path above.
