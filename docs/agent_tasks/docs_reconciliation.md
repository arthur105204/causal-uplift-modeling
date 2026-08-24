You are the documentation, governance, and project-planning reconciliation agent
for this repository.

Work ONLY on the documentation/planning layer in this session.

Do not modify:
- src/
- tests/
- model implementation
- Kaggle notebook computational code
- immutable outputs/runs/*
- held-out data or results

Another agent may be editing implementation in parallel, so keep this work isolated
to your own branch/worktree.

==================================================
CURRENT OWNER-APPROVED WORKFLOW
==================================================

Treat the following as the CURRENT owner-approved execution direction that the
repository must be reconciled to.

1. Kaggle is the primary heavy-compute environment.

2. Full execution may use MULTIPLE Kaggle sessions.
   A full pipeline does NOT have to fit inside one notebook session.

3. Expensive stages communicate through explicit, versioned, immutable artifacts.
   Downstream stages must be reproducible from declared upstream outputs.

4. Local execution is mainly for:
   - editing
   - unit tests
   - synthetic/small verification
   - review

5. Public reader-facing notebooks are exactly:

   kaggle/01_data_understanding.ipynb
   kaggle/02_uplift_modeling.ipynb
   kaggle/03_validation_uncertainty.ipynb
   kaggle/04_final_evaluation.ipynb

6. GitHub Issues are execution tasks.
   They are NOT required to map 1:1 to public notebooks.

7. Heavy/internal computation may live in:
   notebooks/internal/

8. Public notebooks must:
   - show scientific reasoning
   - show important analytical/model logic
   - show results, interpretation, limitations

   They should NOT expose large amounts of engineering plumbing such as:
   - path resolution
   - manifest traversal
   - hashing internals
   - artifact registries
   - serialization machinery
   - environment-capture implementation

   Principle:

   ABSTRACT ENGINEERING PLUMBING;
   KEEP SCIENTIFIC COMPUTATION VISIBLE.

9. Authoritative CRITEO-UPLIFTv2.1 feature semantics are:

   continuous:
   f0, f2, f7, f10

   categorical:
   f1, f3, f4, f5, f6, f8, f9, f11

   Physical float64 storage does NOT imply continuous or ordinal semantics.

10. Causal Forest remains a mandatory main comparator.

11. T03-C randomization calibration remains mandatory before T16/pre-test freeze.

12. Do NOT change these frozen foundations merely for deadline convenience:

   - X = f0...f11
   - T = treatment assignment
   - primary Y = conversion
   - visit = secondary outcome
   - exposure = audit-only
   - assignment/ITT CATE estimand
   - retain-all primary row policy
   - frozen 70/15/15 split
   - joint (T,Y) stratification
   - held-out isolation
   - T-Learner formula
   - X-Learner pseudo-outcome/cross-fitting logic
   - frozen uplift metric conventions
   - 500-draw paired arm-stratified bootstrap
   - one-shot held-out evaluation

13. Deadline mode is active.

   Preferred workflow:

   UNDERSTAND CORE LOGIC
   -> CODE PLAN
   -> IMPLEMENT
   -> VERIFY
   -> CODE MAP
   -> REVIEW
   -> TEACH-BACK
   -> ACCEPT

14. Teach-back should focus on:

   INPUT
   -> OPERATION
   -> OUTPUT
   -> WHY
   -> FAILURE MODE

   For statistical/modeling stages also cover:
   - main formula
   - leakage risk
   - verification

   The owner is not required to memorize generic engineering syntax.

==================================================
YOUR TASK
==================================================

Audit and reconcile the entire documentation/planning layer.

Read at minimum:

AGENTS.md
CLAUDE.md
README.md

docs/decision_register.csv
docs/index.md
docs/00_project_overview.md
docs/01_causal_contract.md
docs/02_data_contract.md
docs/03_assumption_and_audit_spec.md
docs/04_duplicate_profile_protocol.md
docs/05_methodology_scope.md
docs/06_experiment_protocol.md
docs/07_metric_specification.md

all docs/adr/*.md

GitHub MASTER Issue #20

GitHub Issues #4 through #19 where relevant.

Also search the repository documentation for stale wording such as:

- 12 numeric features
- canonical numeric order
- no-op preprocessing
- IdentityFeatureTransform
- 00_project_overview.ipynb
- 01_data_feasibility.ipynb
- 02_eda_split_preprocessing.ipynb
- 03_metrics_and_meta_learners.ipynb
- 04_causal_forest.ipynb
- 05_validation_uncertainty.ipynb
- 06_heldout_evaluation.ipynb
- 07_final_story.ipynb
- LOCAL authoritative
- fixed 50K -> 500K -> 2M -> full when D30 supersedes it
- language implying all f0-f11 are continuous

==================================================
AUTHORITY / CHANGE RULE
==================================================

Do not rewrite history deceptively.

If an old owner-approved decision must be corrected because of newly established
feature semantics:

- preserve the old decision
- add an explicit amendment/superseding decision
- reference the new decision from affected older decisions

For the feature-semantics correction, add an explicit new decision such as D32
if no equivalent authoritative decision already exists.

D32 should establish:

- 4 continuous features
- 8 categorical features
- physical dtype vs semantic type distinction
- categorical numeric tokens have no ordinal interpretation
- LightGBM requires categorical-aware representation
- Causal Forest requires estimator-specific categorical representation
- treating all twelve token columns as continuous is rejected

Do not silently rewrite D17 history.
Annotate/amend it through D32.

==================================================
REWRITE AGENTS.md
==================================================

Rewrite AGENTS.md into a concise operational contract.

It should contain only durable agent rules:

1. authority order
2. frozen methodological foundations
3. current Kaggle multi-session execution model
4. public-vs-internal notebook distinction
5. feature-semantics rule
6. deadline-mode lifecycle
7. CODE PLAN requirements
8. notebook good-practice rule
9. held-out isolation
10. implementation boundaries
11. verification / clean-run rules
12. review/falsification
13. CODE MAP / teach-back
14. multi-agent coordination
15. repository hygiene

Avoid duplicating detailed metric formulas, estimator configuration, or ADR content.

AGENTS.md should point to existing authoritative docs instead.

==================================================
REWRITE CLAUDE.md
==================================================

Make CLAUDE.md much shorter.

It should mainly say:

- read AGENTS.md first
- follow authority hierarchy
- use docs/index.md to locate contracts
- use decision_register.csv for owner-approved decisions
- GitHub Issues define execution tasks
- Kaggle is primary heavy compute
- commands for tests/environment
- one writer per working tree
- do not auto-advance lifecycle phases
- do not access held-out before authorization

Do NOT duplicate the full contents of AGENTS.md.

==================================================
RECONCILE NUMBERED DOCS
==================================================

Correct stale or misleading CURRENT-contract language.

Especially:

docs/02_data_contract.md
- distinguish physical dtype from semantic type
- replace "canonical numeric order" with "canonical column order"
- document the 4 continuous / 8 categorical mapping

docs/03_assumption_and_audit_spec.md
- ensure continuous diagnostics and categorical diagnostics are conceptually separated
- do not preserve all-feature SMD as if categorical token magnitude were meaningful
- do not invent a new calibration threshold

docs/05_methodology_scope.md
- align estimator representation requirements with D32

docs/06_experiment_protocol.md
- fit estimator-specific preprocessing on training only
- cross-fitting preprocessing must respect OOF boundaries
- multiple Kaggle sessions are allowed
- explicit stage artifacts connect sessions
- public notebooks do not have to execute every heavy stage themselves

Preserve held-out and methodological rules.

==================================================
RECONCILE ADRs
==================================================

Audit every ADR for assumptions invalidated by D32 or the new Kaggle workflow.

In particular:

ADR-base-learner
ADR-CF-implementation
ADR-CF-bridge
ADR-data-stack
ADR-experiment-artifacts

Do not invent a Causal Forest categorical encoding.

If representation is unresolved, document it as an explicit decision/blocker.

==================================================
RECONCILE MASTER ISSUE #20
==================================================

MASTER #20 is currently stale.

Rewrite it around the CURRENT architecture.

Public artifact mapping should become approximately:

01 Data Understanding
  <- data / audit / split / preprocessing evidence

02 Uplift Modeling
  <- metrics + Response + T-Learner + X-Learner + Causal Forest

03 Validation & Uncertainty
  <- common validation comparison + diagnostics where triggered +
     optional segment analysis + bootstrap

04 Final Evaluation
  <- pre-test freeze + one-shot held-out evaluation +
     final interpretation / defense

Explicitly state:

Issue != notebook.

Heavy stages may run across multiple Kaggle sessions/internal notebooks.

Do not use GitHub issue checkboxes as empirical truth unless verified against
current configs/evidence.

==================================================
RECONCILE INDIVIDUAL ISSUES
==================================================

Audit relevant Issues #4-#19.

Remove stale execution-location requirements such as:

"run in 04_causal_forest.ipynb"

where the task is now better expressed as:

Execution:
- Kaggle-primary governed stage
- may use one or more Kaggle sessions/internal notebooks

Public presentation:
- consumed by the appropriate public notebook

Keep each Issue focused on:

GOAL
INPUT
PROCESS
OUTPUT
VERIFICATION
DEPENDENCIES
DEFINITION OF DONE

Do not expose low-value engineering details unless correctness depends on them.

Do not change methodological requirements just to simplify Issues.

==================================================
README / INDEX
==================================================

Update README.md and docs/index.md LAST.

README should describe:

- research objective
- 4-notebook public story
- Kaggle multi-session reproducibility
- high-level estimator portfolio
- artifact-based stage chaining
- no implementation-history narrative

docs/index.md should accurately describe authority and current document status.

==================================================
DO NOT TOUCH IMPLEMENTATION STATE
==================================================

Do not fabricate or modify:

- accepted model runs
- run IDs
- metrics
- hashes
- empirical results
- lifecycle evidence

If an implementation/config is stale because of feature semantics, REPORT that
it must be reopened by the implementation agent.

Do not pretend the corrected run has already happened.

==================================================
FINAL DELIVERABLE
==================================================

After edits, report:

1. Files changed
2. GitHub Issues changed
3. Conflicts resolved
4. Historical decisions preserved/superseded
5. Remaining stale implementation/config references
6. Remaining owner decisions/blockers
7. Final current task graph
8. Final public notebook mapping
9. A short INPUT -> PROCESS -> OUTPUT summary of the whole project
10. Any item you deliberately did NOT change and why

Run a final repository documentation search for stale architecture/semantics terms.

Do not stop after producing an audit report.
Proceed to reconcile all safe documentation/project-management changes in scope.