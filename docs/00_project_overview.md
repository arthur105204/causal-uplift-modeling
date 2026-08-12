# Sprint 1 project overview

## Purpose and phase

This derived overview summarizes the Sprint 1 design and specification freeze
for causal uplift modeling on CRITEO-UPLIFTv2.1. Sprint 1 records requirements;
it does not assert that models, audits, promotion gates, or held-out evaluation
have been executed. Implementation and development evidence belong to Sprint 2,
and authorized held-out evaluation belongs to Sprint 3.

## Authority and precedence

The authority hierarchy is defined in the [documentation map](index.md):

1. the owner-approved [decision register](decision_register.csv);
2. the numbered causal, data, audit, duplicate, methodology, experiment, and
   metric specifications;
3. the [Sprint 1 plan](tasks/sprint1_spec_completion.md);
4. ADR implementation details; and
5. derived summaries and review reports.

This file creates no project decision. When it conflicts with a higher-authority
source, that source controls and this overview must be corrected.

## Frozen causal scope

| Item | Sprint 1 contract |
|---|---|
| Unit | One released CRITEO-UPLIFTv2.1 observation/row, not an assumed unique user. |
| Eligible population | All released rows passing the predeclared hard data-integrity gates in document 01. |
| `X` | Exactly ordered `f0` through `f11`. |
| `T` | Binary `treatment` assignment. |
| Primary `Y` | Binary `conversion`. |
| Secondary outcome | `visit`, only when present and schema-valid, in a separate pipeline. |
| Audit-only field | `exposure`; never primary treatment, feature, eligibility condition, or population filter. |
| Primary estimand | Assignment/intention-to-treat CATE for ranking over the eligible released population. |
| Aggregate summary | Assigned-arm ATE; not a ranking estimator. |

Rows are excluded from the primary population only for predeclared hard
data-integrity failures. Repeated values, repeated feature profiles, feature
tails, extreme estimated scores, rare outcomes, or improved model performance do
not authorize primary exclusion. Deduplication or grouped-profile analyses are
separate sensitivities.

Claims are limited to the eligible released population and supported covariate
regions. Durable person identity, publisher provenance details, field timing,
and transport beyond this population remain documented limitations or
`PROVISIONAL` evidence requirements; they do not reopen the frozen primary
eligibility definition.

## Evidence and audit scope

Every requirement uses exactly one class from document 03:

- `HARD_GATE` for deterministic workflow requirements;
- `EMPIRICAL_DIAGNOSTIC` for measured signals that cannot prove causal
  identification; or
- `ASSUMPTION_SUPPORT_OR_LIMITATION` for source/design support and irreducible
  limitations.

Sprint 1 freezes the design-calibrated diagnostic algorithms and action
taxonomy. Numerical calibration, checksums, and executed evidence are
`OPEN_FOR_SPRINT2` and must be completed before the pre-test executable freeze.
They are not current empirical results.

## Estimator portfolio

| Method | Role/status |
|---|---|
| Random ranking | Required theoretical/seeded reference; not a causal estimator. |
| Response model | Required non-causal targeting comparator. |
| T-Learner | Required primary causal baseline. |
| X-Learner | Accepted main comparator with Sprint 2 correctness and execution gates. |
| Causal Forest | Accepted main comparator planned for Sprint 2; exact implementation is provisional. |
| DR-Learner | Conditional stretch comparator; test-ineligible unless every promotion gate passes before freeze. |
| S-Learner | Deferred. |

LightGBM is a provisional default base-learner framework for methodology-approved
components. Exact objectives, hyperparameters, stability, and scale behavior
require Sprint 2 evidence. A Python–R or other cross-language Causal Forest bridge
remains deferred unless its ADR activation condition is met.

## Experiment and test boundary

The frozen outer split is 70% training, 15% validation, and 15% held-out test
with the exact stratification and seed rules in document 06. Validation is the
only feedback source for development selection. All robustness retraining,
cross-fitting, promotion, calibration, and final refitting finish before the
pre-test freeze. The held-out test cannot be used for heuristic input choice,
threshold selection, duplicate policy, method selection, tuning, seed choice, or
post-result replacement.

Input selection is fail-closed through an explicit manifest. Silent filename
heuristics and silent scale fallback are not protocol options. A scale failure
is recorded and handled through the D23 promotion process before test access.

## Metric hierarchy

- Primary ranking statistic: Qini above the theoretical expected-random line.
- Secondary curve summaries: exact raw Qini/AUUC-family conventions in document
  07.
- Decision summaries: fixed-coverage `uplift@K` and incremental conversions.
- Response ROC-AUC, average precision, and log loss: response/nuisance
  diagnostics only.
- Empirical PEHE against true ITE on real CRITEO-UPLIFTv2.1: prohibited.

Metric formulas, units, tie handling, support failures, bootstrap convention, and
test-use restrictions are controlled by
[document 07](07_metric_specification.md).

## Sprint boundaries and next evidence

Sprint 1 closes documentation only after its checklist contains no `BLOCKER`.
Sprint 2 owns implementation, processed-data lineage/manifests,
design-calibration values, objective tests, scale gates, development validation,
method promotion, and the pre-test executable freeze. Canonical compressed-source
and decompressed-CSV checksums plus ordered CSV-to-Parquet semantic identity have
now been recorded. T01 implementation choices, including the operational
resource rule and ZSTD layout, are accepted; production pipeline verification
and all model evidence remain open. Sprint 3 owns the authorized one-time
held-out evaluation.

## Forward execution convention

This paragraph is a Sprint 2+ implementation convention, not a retroactive
Sprint 1 freeze claim. The task notebook is the primary human-readable research,
execution, verification, evidence, and interpretation record. Immutable
machine-readable outputs remain under `outputs/runs/<run_id>/`, configuration
under `configs/`, and implementation decisions under `docs/adr/`. Modules,
scripts, and automated tests are optional supporting infrastructure introduced
only when concretely justified; notebook-first does not mean notebook-only and
does not relax any artifact, leakage, or held-out-isolation rule.
