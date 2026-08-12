# Documentation map

## Authority hierarchy

When documents conflict, apply this precedence:

1. owner-approved [`decision_register.csv`](decision_register.csv);
2. numbered causal, data, audit, duplicate, methodology, experiment, and metric
   specifications, with documents 01, 02, and 06 controlling their named
   contracts;
3. [Sprint 1 specification-completion plan](tasks/sprint1_spec_completion.md);
4. ADR implementation decisions and gates;
5. derived README, overview, literature routing, and reproducibility guidance;
6. review reports and freeze checklists.

A lower-authority document cannot silently defer, remove, or redefine an
owner-approved decision.

## Core specifications

| Document | Purpose | Authority | Sprint 1 status |
|---|---|---|---|
| [`00_project_overview.md`](00_project_overview.md) | Derived phase and scope summary | Derived | PASS |
| [`01_causal_contract.md`](01_causal_contract.md) | Causal question, variables, estimands, population, claims | Source of truth | PASS_WITH_LIMITATION: publisher/design evidence remains provisional |
| [`02_data_contract.md`](02_data_contract.md) | Dataset identity, schema, roles, lineage, precision | Source of truth | PASS_WITH_LIMITATION: raw checksum evidence is recorded; processed lineage remains T01 work |
| [`03_assumption_and_audit_spec.md`](03_assumption_and_audit_spec.md) | Evidence classes, gates, diagnostics, action rules | Source of truth | PASS_WITH_LIMITATION: numerical calibration is Sprint 2 |
| [`04_duplicate_profile_protocol.md`](04_duplicate_profile_protocol.md) | Row identity and repeated-profile governance | Source of truth | PASS_WITH_LIMITATION: durable/person identity is unavailable |
| [`05_methodology_scope.md`](05_methodology_scope.md) | Estimator roles, formulas, and promotion rules | Numbered methodology source | PASS_WITH_LIMITATION: implementations require Sprint 2 evidence |
| [`06_experiment_protocol.md`](06_experiment_protocol.md) | Split, selection, cross-fitting, freeze, and test isolation | Source of truth | PASS_WITH_LIMITATION: executable gates are Sprint 2 |
| [`07_metric_specification.md`](07_metric_specification.md) | Metric formulas, units, edge cases, uncertainty | Source of truth | PASS |

The owner-approved CSV is the only authoritative decision register.
[`decision_register.md`](decision_register.md) is a redirect and contains no
independent decision.

## Sprint plan

[`tasks/sprint1_spec_completion.md`](tasks/sprint1_spec_completion.md) defines
Sprint 1 scope, deliverables, acceptance criteria, and later-phase deferrals. It
cannot override the register or numbered specifications.

## ADRs

| ADR | Status | Scope |
|---|---|---|
| [`ADR-base-learner.md`](adr/ADR-base-learner.md) | PROVISIONAL | LightGBM default base-learner framework; exact implementation is Sprint 2 |
| [`ADR-data-stack.md`](adr/ADR-data-stack.md) | PROVISIONAL | Pandas/PyArrow default technology path and bounded fallback gate |
| [`ADR-T01-data-engineering.md`](adr/ADR-T01-data-engineering.md) | ACCEPTED | T01 loader, determinism, source-row identity, operational resource rule, manifest governance, and ZSTD layout |
| [`ADR-CF-bridge.md`](adr/ADR-CF-bridge.md) | DEFERRED | Cross-language integration only; does not defer Causal Forest |
| [`ADR-CF-implementation.md`](adr/ADR-CF-implementation.md) | PROVISIONAL | Exact Causal Forest implementation and promotion gates |
| [`ADR-experiment-artifacts.md`](adr/ADR-experiment-artifacts.md) | PROVISIONAL | Immutable run layout, manifests, prediction lineage, and retention |

An ADR may implement an accepted decision but cannot change its estimator role,
estimand, population, or test boundary.

## Derived documents

- [`README.md`](../README.md): public project orientation and phase status.
- [`00_project_overview.md`](00_project_overview.md): derived specification map.
- [`literature_review_matrix.md`](literatures/literature_review_matrix.md): bounded research
  grounding and non-claims.
- [`REPRODUCIBILITY.md`](../REPRODUCIBILITY.md): non-executing environment and
  phase guidance.
- [`sprint1_spec_review.md`](sprint1_spec_review.md): final consistency review.
- [`sprint1_freeze_checklist.md`](sprint1_freeze_checklist.md): row-level freeze
  decision evidence.

## Change-control rule

1. Change the highest-authority affected source first.
2. Obtain owner approval when an accepted decision changes.
3. Reconcile affected numbered specifications.
4. Amend ADR implementation details without redefining higher decisions.
5. Update README, overview, literature routing, review, and checklist last.
6. Run link, status, placeholder, local-path, secret, and cross-document scans
   before declaring a freeze.

Timestamp recency alone never resolves a conflict. Execution evidence and held-out
results cannot retroactively rewrite a pre-test specification.

## Sprint 2+ execution workflow

From Sprint 2 empirical work onward, notebooks are the primary human-readable
research, execution, verification, evidence, and interpretation artifacts.
Machine-readable evidence belongs under immutable
`outputs/runs/<run_id>/`; reproducible inputs belong under `configs/`; and
implementation decisions belong under `docs/adr/`.

`src/`, `tests/`, and `scripts/` are optional supporting infrastructure. They are
created only when reuse, automated regression verification, an authoritative
contract, or avoidance of unreasonable notebook duplication justifies them.
Notebook-first does not weaken manifests, hashes, model/prediction retention,
test isolation, or any numbered contract.
