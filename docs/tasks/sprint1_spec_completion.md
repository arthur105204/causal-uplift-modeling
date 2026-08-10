# Sprint 1 — Specification Completion

## Sprint goal

Freeze the causal design, data/audit contracts, methodology roles, experiment
governance, metric conventions, ADR boundaries, and reproducibility scaffolding
for CRITEO-UPLIFTv2.1. Sprint 1 does not train a final model, execute a full-data
audit, or evaluate the held-out test set.

## In scope

- causal question, assignment/ITT estimand, unit, eligibility, and claim limits;
- canonical `X/T/Y` and primary/secondary outcome roles;
- data schema, lineage, numeric precision, and fail-closed validation;
- assumption evidence and audit-action specification;
- duplicate/profile definitions and primary keep-all policy;
- estimator portfolio, causal roles, and promotion boundaries;
- train/validation/test, cross-fitting, robustness, and pre-test-freeze protocol;
- metric formulas, units, top-K rules, edge cases, and uncertainty specification;
- ADR reconciliation with owner-approved decisions;
- documentation, manifest examples, data policy, and reproducibility scaffolding;
  and
- bounded literature grounding and explicit non-claims.

## Out of scope

- model training or final refitting;
- hyperparameter or package-version selection;
- full-data audit execution or numerical calibration;
- held-out test access or test-derived selection;
- final predictions, model binaries, bootstrap draws, or metric results;
- scale-gate execution and resource benchmarks; and
- deployment or production refit.

## Deliverables

### Governance and core specifications

- `docs/decision_register.csv`
- `docs/decision_register.md`
- `docs/00_project_overview.md`
- `docs/01_causal_contract.md`
- `docs/02_data_contract.md`
- `docs/03_assumption_and_audit_spec.md`
- `docs/04_duplicate_profile_protocol.md`
- `docs/05_methodology_scope.md`
- `docs/06_experiment_protocol.md`
- `docs/07_metric_specification.md`
- `docs/tasks/sprint1_spec_completion.md`

### ADRs

- `docs/adr/ADR-base-learner.md`
- `docs/adr/ADR-data-stack.md`
- `docs/adr/ADR-CF-bridge.md`
- `docs/adr/ADR-CF-implementation.md`
- `docs/adr/ADR-experiment-artifacts.md`

### Documentation and reproducibility scaffolding

- `README.md`
- `LICENSE`
- `data/README.md`
- `docs/index.md`
- `docs/literature_review_matrix.md`
- `REPRODUCIBILITY.md`
- `configs/data_manifest.example.json`
- `configs/run_config.example.json`
- `.gitignore`

### Final review

- `docs/sprint1_spec_review.md`
- `docs/sprint1_freeze_checklist.md`

## Acceptance criteria

- [x] The assignment/ITT CATE estimand is frozen.
- [x] `X=f0`–`f11`, `T=treatment`, and primary `Y=conversion` are frozen.
- [x] `exposure` is prohibited from primary `X`, eligibility, population
  filtering, and the primary treatment definition.
- [x] Primary population and eligibility agree across source and derived docs.
- [x] Random, Response, T-Learner, X-Learner, Causal Forest, DR-Learner, and
  S-Learner roles are declared without a predeclared winner.
- [x] LightGBM is explicitly `PROVISIONAL`; exact implementation evidence is
  assigned to Sprint 2.
- [x] Causal Forest's accepted estimator role and provisional implementation are
  distinct, and its ADR gates are explicit.
- [x] DR-Learner has an explicit development-only promotion gate and fallback.
- [x] Train/validation/test, cross-fitting, robustness, pre-test freeze, and
  one-time test release are documented.
- [x] Metric formulas, units, support failures, top-K rules, and uncertainty are
  specified; empirical PEHE against true ITE on real data is prohibited.
- [x] No test access or test-derived selection is permitted before freeze.
- [x] Every required Sprint 1 document exists and is non-empty.
- [x] No unresolved contradiction remains among source documents.
- [x] Raw/processed data and generated outputs are excluded from version control.
- [x] Reproducibility instructions and non-secret configuration examples exist.
- [x] The final freeze checklist contains zero `BLOCKER` rows.

## Deferred to Sprint 2

- executed audit, correctness, validation, and artifact evidence;
- actual release metadata, paths, row counts, and SHA-256 manifest values;
- D23 scale-gate execution and resource evidence;
- target/objective unit tests and exact model serialization;
- X-Learner, Causal Forest, and conditional DR-Learner implementation evidence;
- design-calibrated numerical audit thresholds and Monte Carlo artifacts;
- the predeclared two-fold versus five-fold X-Learner comparison; and
- exact learner packages, hyperparameters, iteration counts, and environment
  lock.

Held-out evaluation is deferred to Sprint 3 after the Sprint 2 pre-test
executable freeze.

## Completion evidence

Completion is evidenced only by the deliverable documents, internal-link and
configuration validation, source-to-derived consistency review, and the final
checklist. Legacy files under `outputs/` or `archive/` are not completion
evidence.

## Final status

**Current status:** READY_WITH_LIMITATIONS

The final review must replace this with exactly one of:

- `READY_FOR_FREEZE`
- `READY_WITH_LIMITATIONS`
- `BLOCKED`

It must not select a ready status while any checklist row is `BLOCKER`.
