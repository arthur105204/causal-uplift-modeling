# Documentation map

## Authority hierarchy

When documents conflict, apply this precedence:

1. owner-approved [`decision_register.csv`](decision_register.csv);
2. numbered causal, data, audit, duplicate, methodology, experiment, and metric
   specifications, with documents 01, 02, and 06 controlling their named
   contracts, and ACCEPTED ADR decisions in `adr/`;
3. GitHub Issues as the current execution plan — [MASTER #20][master-issue] is
   the authoritative task-to-notebook overview, individual Issues #4-#19 are
   task-scoped execution specs, and neither may silently redefine tier 1/2;
4. accepted task-specific empirical evidence under `outputs/runs/<run_id>/`;
5. derived README, `AGENTS.md`/`CLAUDE.md`, overview, literature routing, and
   reproducibility guidance;
6. historical Sprint 1 closure records — [`sprint1_spec_review.md`](sprint1_spec_review.md),
   [`sprint1_freeze_checklist.md`](sprint1_freeze_checklist.md), and
   [`tasks/sprint1_spec_completion.md`](tasks/sprint1_spec_completion.md) — frozen
   at Sprint 1 close and retained as historical evidence, not live plans; they
   do not describe or govern current Sprint 2+ execution.

[master-issue]: https://github.com/arthur105204/causal-uplift-modeling/issues/20

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

Current execution planning lives in GitHub Issues: [MASTER #20][master-issue]
carries the task graph, the current Kaggle multi-session execution model, the
public-notebook mapping, and per-Issue links; individual Issues #4-#19 carry
task-scoped GOAL/INPUT/PROCESS/OUTPUT/VERIFICATION/DEPENDENCIES/DEFINITION OF
DONE specs. Neither overrides the register or numbered specifications.

[`tasks/sprint1_spec_completion.md`](tasks/sprint1_spec_completion.md) defined
Sprint 1 scope, deliverables, acceptance criteria, and later-phase deferrals.
It is closed and superseded by the above for current execution planning; it
remains as the historical record of what Sprint 1 delivered.

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
- [`AGENTS.md`](../AGENTS.md): operating contract for agents working in this repository.
- [`CLAUDE.md`](../CLAUDE.md): short pointer/command reference for Claude Code, deferring to
  `AGENTS.md`.
- [`00_project_overview.md`](00_project_overview.md): derived specification map.
- [`literature_review_matrix.md`](literatures/literature_review_matrix.md): bounded research
  grounding and non-claims.

## Historical Sprint 1 closure records

Frozen at Sprint 1 close; retained as evidence of what was reviewed and
accepted, not as live specifications of current Sprint 2+ status.

- [`sprint1_spec_review.md`](sprint1_spec_review.md): Sprint 1 final consistency review.
- [`sprint1_freeze_checklist.md`](sprint1_freeze_checklist.md): Sprint 1 row-level freeze
  decision evidence.
- [`tasks/sprint1_spec_completion.md`](tasks/sprint1_spec_completion.md): Sprint 1 scope,
  deliverables, and acceptance criteria.

## Change-control rule

1. Change the highest-authority affected source first.
2. Obtain owner approval when an accepted decision changes.
3. Reconcile affected numbered specifications and ADRs.
4. Reconcile MASTER #20 and affected individual GitHub Issues to match.
5. Update README, `AGENTS.md`/`CLAUDE.md`, overview, and literature routing last.
6. Run link, status, placeholder, local-path, secret, and cross-document scans
   before declaring the change complete.

Timestamp recency alone never resolves a conflict. Execution evidence and held-out
results cannot retroactively rewrite a pre-test specification.

## Sprint 2+ execution workflow

Kaggle is the primary heavy-compute environment; a full pipeline may span
multiple Kaggle sessions connected by explicit, versioned, immutable
artifacts under `outputs/runs/<run_id>/` rather than shared runtime state.
Notebooks are the primary human-readable research, execution, verification,
evidence, and interpretation artifacts — `kaggle/01_data_understanding.ipynb`
through `kaggle/04_final_evaluation.ipynb` for the public reader-facing story
(see MASTER #20 for the task-to-notebook mapping), and `notebooks/internal/`
for heavy or held-out-sensitive computation that is not reader-facing.
Reproducible inputs belong under `configs/`, and implementation decisions
belong under `docs/adr/`.

`src/`, `tests/`, and `scripts/` are optional supporting infrastructure. They are
created only when reuse, automated regression verification, an authoritative
contract, or avoidance of unreasonable notebook duplication justifies them.
Notebook-first does not weaken manifests, hashes, model/prediction retention,
test isolation, or any numbered contract.

D32 (`decision_register.csv`) is the authoritative feature-semantics decision:
`f0`,`f2`,`f7`,`f10` are continuous and `f1`,`f3`,`f4`,`f5`,`f6`,`f8`,`f9`,`f11`
are categorical numeric tokens. It governs model-input representation across
`docs/02`, `docs/03`, `docs/05`, `docs/06`, and the base-learner/Causal-Forest
ADRs without changing the canonical `X = f0...f11` definition itself.
