# Sprint 1 Freeze Checklist

**Review date:** 2026-08-06  
**Execution evidence produced:** none

| ID | Requirement | Status | Evidence | Limitation / next action |
|---|---|---|---|---|
| A1 | Primary population and unit | PASS | `docs/01_causal_contract.md` | One released row; hard-gate exclusions only. |
| A2 | Canonical X/T/Y | PASS | `docs/01_causal_contract.md` | `X=f0`–`f11`, `T=treatment`, primary `Y=conversion`. |
| A3 | Assignment/ITT CATE estimand | PASS | D01; `docs/01_causal_contract.md` | Claims remain population- and support-bounded. |
| A4 | Treatment versus exposure | PASS_WITH_LIMITATION | `docs/01_causal_contract.md` | Exposure is prohibited from primary use; publisher timing evidence remains provisional. |
| A5 | Primary and secondary outcomes | PASS_WITH_LIMITATION | D02; `docs/01_causal_contract.md` | Visit is optional and uses a separate pipeline. |
| B1 | Schema and label contract | PASS | `docs/02_data_contract.md` | Fail closed on missing/invalid fields. |
| B2 | Authoritative input specification | PASS | `docs/02_data_contract.md`; `ADR-data-stack.md` | Explicit manifest only; no heuristic selection. |
| B3 | Processed-to-raw lineage | PASS_WITH_LIMITATION | `docs/02_data_contract.md` | Actual lineage evidence is Sprint 2. |
| B4 | Numeric representation | PASS | D09; `docs/02_data_contract.md` | `float64` primary; `float32` sensitivity-only. |
| B5 | Actual manifest/checksum evidence | OPEN_FOR_SPRINT2 | `docs/02_data_contract.md` | SHA-256 fields/algorithm are frozen; values are not yet generated. |
| B6 | No silent scale fallback | PASS | D23; `docs/06_experiment_protocol.md` | Fail or explicitly amend before test release. |
| C1 | Randomization/treatment-predictability protocol | PASS_WITH_LIMITATION | `docs/03_assumption_and_audit_spec.md` | Exact assignment source evidence remains provisional. |
| C2 | Balance and observable support | PASS | `docs/03_assumption_and_audit_spec.md` | Design-calibrated actions and deterministic support failures are defined. |
| C3 | Duplicate/profile protocol | PASS_WITH_LIMITATION | `docs/04_duplicate_profile_protocol.md` | Equal profiles are not unique-person identities. |
| C4 | Evidence and action taxonomies | PASS | `docs/03_assumption_and_audit_spec.md` | Includes `UNSUPPORTED_METRIC`. |
| C5 | Numerical audit calibration | OPEN_FOR_SPRINT2 | `docs/03_assumption_and_audit_spec.md` | Generate null percentiles and Monte Carlo evidence before pre-test freeze. |
| D1 | Random/Response/T/X/CF roles | PASS | D10–D15; `docs/05_methodology_scope.md` | X and CF remain main comparators. |
| D2 | DR-Learner promotion rule | PASS_WITH_LIMITATION | D16; `docs/05_methodology_scope.md` | Conditional stretch; test-ineligible until all gates pass. |
| D3 | LightGBM ADR status | PASS_WITH_LIMITATION | D17–D18; `ADR-base-learner.md` | Family selected; executable ADR is `PROVISIONAL`. |
| D4 | No predeclared winner | PASS | `docs/05_methodology_scope.md` | Selection is validation-only. |
| D5 | Exact LightGBM implementation | OPEN_FOR_SPRINT2 | `ADR-base-learner.md` | Freeze package, objectives, hyperparameters, iterations, and serialization. |
| D6 | Exact CF implementation evidence | OPEN_FOR_SPRINT2 | `ADR-CF-implementation.md` | Pass all eight gates; bridge remains deferred. |
| E1 | Frozen outer split | PASS | D06; `docs/06_experiment_protocol.md` | 70/15/15 with seed 42 and joint T/Y stratification. |
| E2 | Validation-only selection | PASS | `docs/06_experiment_protocol.md` | No test-derived choices. |
| E3 | Pre-test executable freeze | PASS | `docs/06_experiment_protocol.md` | Required before any authorized test release. |
| E4 | Held-out test isolation | PASS | `docs/06_experiment_protocol.md` | One-time use after freeze only. |
| E5 | Cross-fitting status | PASS_WITH_LIMITATION | `docs/05_methodology_scope.md`; `docs/06_experiment_protocol.md` | X primary two-fold; five-fold sensitivity; empirical comparison is Sprint 2. |
| E6 | Seed governance | PASS | `docs/06_experiment_protocol.md` | Primary 42; robustness 42/123/2026; no seed cherry-picking. |
| E7 | Model/audit execution | OPEN_FOR_SPRINT2 | `docs/06_experiment_protocol.md` | No Sprint 1 execution result is claimed. |
| E8 | Held-out evaluation execution | OPEN_FOR_SPRINT2 | `docs/06_experiment_protocol.md` | Sprint 3 only after freeze. |
| F1 | Primary ranking metric | PASS | D24; `docs/07_metric_specification.md` | Qini above theoretical random. |
| F2 | Secondary metrics | PASS | D25–D27; `docs/07_metric_specification.md` | Raw Qini area and fixed-coverage decision metrics; response metrics diagnostic only. |
| F3 | Metric edge cases/top-K support | PASS | `docs/07_metric_specification.md` | Tie, zero denominator, support, and unsupported-metric rules are explicit. |
| F4 | No PEHE on real data | PASS | D28; `docs/07_metric_specification.md` | True ITE is unobserved. |
| F5 | Uncertainty convention | PASS | D29; `docs/07_metric_specification.md` | Paired arm-stratified bootstrap and separate seed variability. |
| G1 | README phase/scope | PASS | `README.md` | No completed model/test claim. |
| G2 | Repository LICENSE | PASS | `LICENSE`; `data/README.md` | MIT does not relicense the dataset. |
| G3 | Data README | PASS | `data/README.md` | Data stays local; schema/manifest/security rules documented. |
| G4 | Documentation map | PASS | `docs/index.md` | Authority and ADR statuses are explicit. |
| G5 | Reproducibility guide | PASS_WITH_LIMITATION | `REPRODUCIBILITY.md` | Exact environment lock and implementation evidence are Sprint 2. |
| G6 | Non-secret JSON examples | PASS | `configs/data_manifest.example.json`; `configs/run_config.example.json` | Templates only; not frozen run evidence. |
| G7 | Ignore policy | PASS | `.gitignore` | Data, outputs, archive, secrets, caches, and model artifacts excluded. |
| G8 | Required files non-empty | PASS | Sprint 1 deliverable inventory | All required files exist and have non-zero size. |
| G9 | Authoritative register integrity | PASS | `docs/decision_register.csv` | 29 rows, 9 columns, unique D01–D29; owner metadata absent but approval implied. |
| H1 | Literature matrix complete | PASS | `docs/literature_review_matrix.md` | Four core sources plus routing synthesis. |
| H2 | Sources linked to project decisions | PASS | `docs/literature_review_matrix.md` | Dataset, meta-learner, forest, and DR roles are mapped. |
| H3 | Literature non-claims | PASS | `docs/literature_review_matrix.md` | No exhaustive-review, universal-winner, or true-ITE claim. |

## Freeze decision

Sprint 1 closure conditions are met:

- `BLOCKER` count is zero;
- all required documents exist and are non-empty;
- source documents are internally consistent and faithful to the register; and
- provisional/deferred execution work is assigned to Sprint 2/3.

| Status | Count |
|---|---:|
| PASS | 32 |
| PASS_WITH_LIMITATION | 9 |
| OPEN_FOR_SPRINT2 | 6 |
| BLOCKER | 0 |

**Final status: FROZEN_WITH_DOCUMENTED_LIMITATIONS**
