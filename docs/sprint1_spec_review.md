# Sprint 1 Specification Review

**Review date:** 2026-08-06  
**Models, audits, benchmarks, checksums, or held-out evaluation executed:** no

## Review scope

The review covered:

- governance: `docs/decision_register.csv`, `docs/decision_register.md`, and
  `docs/tasks/sprint1_spec_completion.md`;
- numbered specifications: `docs/00_project_overview.md` through
  `docs/07_metric_specification.md`;
- ADRs: `ADR-base-learner.md`, `ADR-data-stack.md`, `ADR-CF-bridge.md`,
  `ADR-CF-implementation.md`, and `ADR-experiment-artifacts.md`;
- repository guidance: `README.md`, `LICENSE`, `data/README.md`,
  `docs/index.md`, `REPRODUCIBILITY.md`, `.gitignore`, and both example JSON
  configurations; and
- derived evidence: this review, `docs/sprint1_freeze_checklist.md`, and
  `docs/literature_review_matrix.md`.

No file under `data/raw/`, `data/processed/`, `outputs/`, or `archive/` was used
as evidence.

## Authority applied

The hierarchy in [the documentation map](index.md) was applied in this order:

1. owner-approved [decision register](decision_register.csv);
2. numbered specifications, with documents 01, 02, and 06 controlling their
   named contracts;
3. the [Sprint 1 plan](tasks/sprint1_spec_completion.md);
4. ADR implementation decisions and gates;
5. README, overview, literature routing, and reproducibility guidance; and
6. review reports and checklists.

Timestamp recency was not used to resolve conflicts.

## Decision-register validation

The UTF-8 CSV parsed successfully with 29 decision rows and 9 columns:
`ID`, `Sprint`, `Quyết định`, `Phương án chọn`, `Vì sao chọn`,
`Vì sao không chọn phương án khác`, `Cách kiểm chứng / Success criterion`,
`Task / Artifact liên quan`, and `Trạng Thái`.

- IDs are unique and valid from `D01` through `D29`.
- No decision or selected-option text is blank.
- No status is blank or uninterpretable.
- Status counts are 23 `Đã khóa`, 4 `Tạm thời`, 1 `Mở rộng`, and 1
  `Trì hoãn`.
- No material encoding damage was found.
- Owner metadata is not provided; project-owner approval is implied by the
  authoritative register. This is a minor metadata limitation, not a blocker.

Every active row remains interpretable. Decision fidelity was checked as
follows:

| Decision | Register status | Local specification treatment | Result |
|---|---|---|---|
| D01 | Đã khóa | Assignment/ITT CATE | PASS |
| D02 | Đã khóa | Conversion primary; visit separate secondary pipeline | PASS |
| D03 | Đã khóa | CATE/uplift ranking, not response probability | PASS |
| D04 | Đã khóa | Explicit RCT/design audits | PASS |
| D05 | Đã khóa | Ordered `f0`–`f11`; forbidden post-assignment/label fields | PASS |
| D06 | Đã khóa | Frozen source-row 70/15/15 split | PASS |
| D07 | Đã khóa | Keep all eligible rows; deduplication is sensitivity-only | PASS |
| D08 | Đã khóa | Profile-overlap audit and sensitivity | PASS |
| D09 | Tạm thời | `float64` primary; `float32` sensitivity-only | PASS_WITH_LIMITATION |
| D10 | Đã khóa | Comparative T/X/CF/conditional-DR framing | PASS |
| D11 | Đã khóa | Theoretical random plus seeded permutation illustration | PASS |
| D12 | Đã khóa | Response LightGBM comparator; response metrics diagnostic | PASS |
| D13 | Đã khóa | Two-arm LightGBM T-Learner | PASS |
| D14 | Đã khóa | Cross-fitted LightGBM X-Learner main comparator | PASS |
| D15 | Tạm thời | CF role retained; exact implementation selected by provisional ADR | PASS_WITH_LIMITATION |
| D16 | Mở rộng | DR-Learner conditional stretch with promotion gate | PASS_WITH_LIMITATION |
| D17 | Đã khóa | LightGBM family selected; executable ADR remains provisional | PASS_WITH_LIMITATION |
| D18 | Đã khóa | Binary objectives for factual outcomes; regression for pseudo-effects | PASS |
| D19 | Đã khóa | Parquet analytical storage with lineage | PASS |
| D20 | Tạm thời | Pandas/PyArrow default; bounded Polars/DuckDB fallback gate | PASS_WITH_LIMITATION |
| D21 | Đã khóa | Explicit configs and immutable run manifests | PASS |
| D22 | Trì hoãn | Cross-language CF bridge deferred only | PASS |
| D23 | Đã khóa | 50K→500K→2M→full scale gates; no silent downgrade | PASS |
| D24 | Đã khóa | Qini above theoretical random is primary | PASS |
| D25 | Đã khóa | Raw Qini area/declared AUUC-family secondary convention | PASS |
| D26 | Đã khóa | Fixed-coverage uplift and incremental conversions | PASS |
| D27 | Đã khóa | AUC/AP/log loss are outcome/nuisance diagnostics only | PASS |
| D28 | Đã khóa | No empirical PEHE against true ITE on real data | PASS |
| D29 | Tạm thời | Paired bootstrap plus complete seed reporting | PASS_WITH_LIMITATION |

The CF distinction is preserved: Causal Forest remains a planned Sprint 2 main
comparator; its exact implementation is provisional and promotion-gated; the
cross-language bridge remains deferred. X-Learner remains a main comparator,
DR-Learner remains conditional stretch, S-Learner remains deferred, and ATE is
an aggregate estimand/RCT summary rather than a ranking estimator.

## Resolved contradictions

| ID | Before correction | Source-of-truth | Correction | Status |
|---|---|---|---|---|
| R-01 | Overview treated frozen population/eligibility as a freeze blocker. | D01, D05, D07 and document 01 | Overview now uses all released rows passing hard integrity gates, with dedup/grouped analyses as sensitivities. | PASS |
| R-02 | README implied completed Phase 1 execution, test outputs, and unavailable notebooks. | Documents 01, 05, 06, and 07 | README now describes Sprint 1 specification freeze, Sprint 2/3 execution boundaries, and only existing directories. | PASS |
| R-03 | Base-learner ADR mixed `ACCEPTED` and `PROVISIONAL`. | D12–D14, D17–D18 plus the task's implementation-status rule | D17's LightGBM family selection is preserved while the executable ADR has one status: `PROVISIONAL`. | PASS |
| R-04 | Data-stack ADR retained stale release/checksum/tolerance blockers. | D09, D19–D21, D23 and documents 02/06 | ADR now separates frozen procedures from Sprint 2 evidence, requires manifest selection, and prohibits silent precision/scale fallback. | PASS |
| R-05 | Lower-precedence workflow text allowed heuristic input selection and silent scale downgrade. | D19–D23 and documents 02/06 | Derived guidance now requires explicit manifests and fail-closed D23 scale handling. Legacy implementation remains Sprint 2 reconciliation work. | PASS_WITH_LIMITATION |
| R-06 | Sprint plan and literature matrix were empty. | Current Sprint task | Both now contain substantive scope, acceptance, deferral, literature-role, and non-claim content. | PASS |

## Specification status

| Area | Status | Evidence file | Limitation/deferred item |
|---|---|---|---|
| Authority and register | PASS | `docs/decision_register.csv`; `docs/index.md` | Owner column is absent; owner approval is implied by the authoritative register. |
| Causal contract | PASS_WITH_LIMITATION | `docs/01_causal_contract.md` | Publisher evidence for timing/design details remains provisional. |
| Data contract | PASS_WITH_LIMITATION | `docs/02_data_contract.md` | Actual release metadata, paths, checksums, and durable identity evidence are Sprint 2. |
| Audit/action contract | PASS_WITH_LIMITATION | `docs/03_assumption_and_audit_spec.md` | Design-calibrated numerical thresholds are generated in Sprint 2. |
| Duplicate/profile protocol | PASS_WITH_LIMITATION | `docs/04_duplicate_profile_protocol.md` | No unique-person claim; durable source identity requires execution evidence. |
| Estimator roles | PASS | `docs/05_methodology_scope.md` | No model is declared winner. |
| LightGBM implementation | PASS_WITH_LIMITATION | `docs/adr/ADR-base-learner.md` | Exact package, objectives, hyperparameters, and scale evidence are Sprint 2. |
| Causal Forest implementation | PASS_WITH_LIMITATION | `docs/adr/ADR-CF-implementation.md` | Eight promotion gates remain to be executed. |
| DR-Learner branch | PASS_WITH_LIMITATION | `docs/05_methodology_scope.md` | Conditional stretch method remains test-ineligible unless promoted. |
| Experiment/test governance | PASS | `docs/06_experiment_protocol.md` | Execution and pre-test freeze evidence are later-phase work. |
| Metrics and edge cases | PASS | `docs/07_metric_specification.md` | Numerical results are not part of Sprint 1. |
| Artifact governance | PASS_WITH_LIMITATION | `docs/adr/ADR-experiment-artifacts.md` | 50K development-only transition gate is Sprint 2. |
| Repository/reproducibility scaffolding | PASS_WITH_LIMITATION | `README.md`; `REPRODUCIBILITY.md`; `configs/` | Exact environment lock and legacy-code reconciliation are Sprint 2. |
| Literature grounding | PASS | `docs/literature_review_matrix.md` | Bounded matrix; not a systematic review. |
| Model/audit execution evidence | OPEN_FOR_SPRINT2 | `docs/06_experiment_protocol.md` | No execution claimed or required for Sprint 1. |
| Held-out evaluation | OPEN_FOR_SPRINT2 | `docs/06_experiment_protocol.md` | Owned by Sprint 3 after pre-test executable freeze. |

The repository text scan also found legacy implementation paths that cast
features to `float32`, permit an automatic sample-size fallback, discover
Parquet input, or operate on a test partition (notably `src/data.py`,
`scripts/inspect_parquet.py`, and `scripts/run_phase1_audit.py`). Those files are
not specification sources and were not modified in this documentation-only
task. The README and reproducibility guide classify implementation
reconciliation as Sprint 2 work; none of those paths is authorized as the
current protocol.

## Remaining Sprint 2 items

- populate and verify the actual dataset/checksum/run manifests;
- reconcile implementation with manifest selection, `float64`, D23 scale gates,
  and test isolation;
- execute objective, leakage, alignment, reload, and synthetic correctness
  tests;
- generate design-calibrated diagnostic reference distributions and hashes;
- execute the 50K→500K→2M→full scale/resource gates;
- validate X-Learner and Causal Forest implementations and conditionally assess
  DR-Learner promotion;
- compare two-fold versus five-fold X-Learner cross-fitting on development data;
- freeze exact packages, hyperparameters, iteration counts, and environment;
  and
- complete artifact-ADR and provisional-ADR verification gates before test
  release.

Held-out evaluation remains Sprint 3 work and cannot feed back into selection.

## Validation performed

- Parsed all 29 decision-register rows and reconciled every ID.
- Compared X/T/Y, estimand, exposure, population, estimator roles, split,
  cross-fitting, seeds, metrics, top-K, duplicate policy, artifact names, and
  test-freeze terminology across source documents.
- Scanned the repository text while excluding data, generated outputs, archive,
  virtual environments, Git metadata, and caches.
- Verified all local Markdown links and both example JSON files.
- Checked required-file presence, non-zero size, local absolute paths, and
  secret-like content.
- Did not train a model, execute an audit, read row-level outputs, access the
  held-out test, stage files, commit, or push.

## Final review decision

**READY_WITH_LIMITATIONS**

There are no Sprint 1 specification blockers. All remaining limitations are
explicitly provisional or assigned to Sprint 2/3 execution.
