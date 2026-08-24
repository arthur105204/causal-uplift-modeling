# Documentation Simplification — Owner Decisions

Continue from branch `docs-reconciliation-t11`.

This is a SECOND PASS over the documentation/planning reconciliation.

The previous pass correctly reconciled:
- D32 feature semantics;
- Kaggle multi-session execution;
- the four public notebooks;
- internal-vs-public notebook roles;
- fold-local learned preprocessing;
- Causal Forest representation as an unresolved blocker.

DO NOT undo those changes.

However, the previous pass preserved too much historical audit/governance complexity.
The owner has now reviewed the scientific purpose of the project and approved the
simplifications below.

The goal of this pass is:

> Reduce the repository to the minimum methodological and engineering rigor needed
> for a defensible causal-ML benchmark, without weakening causal correctness,
> leakage control, model comparison, uncertainty estimation, or held-out isolation.

Do not redesign the project.
Do not introduce new statistical machinery.

---

# 1. Scientific objective — owner-approved

The project is NOT trying to identify a universally best CATE/uplift algorithm.

The project is a controlled empirical benchmark of selected implementations on
CRITEO-UPLIFTv2.1.

The main question is approximately:

> Under one common randomized advertising benchmark and one fixed experimental
> protocol, how do selected uplift/CATE implementations differ in their ability
> to rank observations for incremental conversion / treatment allocation?

The evaluated portfolio remains:

- theoretical random reference;
- Response LightGBM as a non-causal targeting comparator;
- LightGBM T-Learner;
- LightGBM X-Learner;
- Causal Forest.

Conclusions must be explicitly:

- dataset-specific;
- implementation-specific;
- protocol-specific;
- metric-specific.

Do NOT claim:
- one estimator is universally best;
- a meta-learner's observed performance is intrinsic to that meta-learner;
- observed superiority explains WHY an estimator is theoretically better.

A valid final claim is of the form:

> Among the evaluated implementations, estimator A achieved stronger held-out
> uplift-ranking / treatment-allocation performance under the frozen
> CRITEO-UPLIFTv2.1 protocol.

---

# 2. Create an owner-approved D33 — Assignment evidence and audit simplification

Add a new owner decision rather than silently rewriting historical decisions.

Suggested title:

D33 — Assignment evidence and diagnostic-scope simplification

D33 must establish:

## 2.1 Randomization evidence

Randomization support comes primarily from the documented experimental
assignment mechanism / publisher design.

Observed baseline balance does NOT prove randomization.

Baseline hypothesis testing or null calibration is NOT required to establish
random assignment.

Balance diagnostics are descriptive/sanity diagnostics only.

## 2.2 Required balance diagnostics

Continuous features:

- descriptive arm summaries where useful;
- SMD;
- optionally compact distribution summaries when they materially help interpretation.

Categorical features:

- category proportions;
- TVD or equivalent simple distribution-distance summary.

Do not:
- compute SMD/mean/variance on categorical token magnitude;
- combine SMD and TVD into one raw statistic;
- create a new omnibus mixed-type test.

## 2.3 Remove the 2,000-draw calibration from P0

The following are no longer mandatory:

- 2,000 treatment-assignment permutations;
- p95/p99 null thresholds for baseline balance;
- Monte Carlo confidence intervals for those thresholds;
- null-calibrated PASS/WARNING/MATERIAL_CONCERN balance bands;
- mandatory repeated refitting of X→T models under null assignments.

Historical specifications/evidence remain in Git history or are explicitly marked
SUPERSEDED_BY_D33 where necessary.

Do not delete historical evidence.

## 2.4 X → T treatment predictability

X→T prediction may remain as an OPTIONAL internal sanity diagnostic.

It is:
- not proof of randomization;
- not a P0 gate;
- not required before T16;
- not required for model training or final evaluation.

If retained, it should be simple and descriptive.

Do not create a permutation-calibration subsystem around it.

## 2.5 Propensity/overlap diagnostics

Basic treatment-arm support required by an estimator remains mandatory.

Zero required treatment/control support remains a real correctness failure.

Large propensity-diagnostic suites, sparse-mass calibration, fixed propensity
bands, and similar analyses are OPTIONAL unless a concrete modeling problem
requires them.

---

# 3. Remove T03-C as a mandatory pre-T16 blocker

Reconcile all documents that currently say:

- T03-C is mandatory;
- T03-C requires 2,000 draws;
- T03-C must complete before T16;
- T16 requires randomization-calibration thresholds.

The new structure should be approximately:

T03 required core:
- correct input identity;
- schema / labels;
- correct X/T/Y roles;
- forbidden-column checks;
- D32 semantic feature handling;
- missing/infinite-value checks;
- row identity;
- split disjointness/accounting;
- basic treatment/outcome support;
- descriptive baseline balance.

Optional/internal diagnostics:
- X→T predictability;
- deeper distribution diagnostics;
- duplicate-profile sensitivities;
- precision sensitivities;
- additional overlap diagnostics.

Do not create a replacement P0 calibration task.

T16 should NOT require T03-C null thresholds.

---

# 4. Simplify duplicate / precision governance

Preserve the important distinction:

- `_source_row_id` identifies released rows for alignment;
- equal feature profiles do not imply duplicate people;
- primary analysis keeps all released rows.

Required:
- source-row uniqueness;
- split identity/disjointness;
- row accounting.

Optional / sensitivity only:
- detailed duplicate-profile taxonomy;
- cross-split profile overlap beyond what is needed for leakage interpretation;
- float32 collision analysis;
- source-vs-float32 duplicate reconciliation;
- extensive DP-01...DP-07 machinery that does not change the primary analysis.

Do not delete historical documents merely because they are no longer P0.
Reclassify their role.

---

# 5. Keep the 500-draw paired bootstrap

DO NOT simplify this away.

The 500-draw paired, treatment-arm-stratified bootstrap remains part of the
main evaluation because it quantifies uncertainty in the actual model-comparison
result.

It uses:
- fixed predictions;
- shared resamples across models;
- no model retraining inside bootstrap draws.

This is fundamentally different from the removed baseline-randomization
calibration.

---

# 6. Random reference simplification

The theoretical expected-random reference remains the PRIMARY random reference.

Any seeded/random-permutation distribution is secondary/illustrative and must
not block the core experiment unless the metric implementation genuinely
requires it.

If current contracts make exactly 200 random permutations a blocking prerequisite,
reclassify them as secondary diagnostic/illustrative evidence unless removing
them would change the frozen definition of a reported primary metric.

Do NOT change the actual Qini formula or ranking orientation.

Preserve tests that verify good / reversed / random-equivalent rankings.

---

# 7. Robustness-seed scope

Primary FULL model seed remains 42 unless another existing owner decision
explicitly controls it.

Additional seeds 123 and 2026 may be used to characterize algorithmic stability,
but full multi-seed retraining must NOT become a universal P0 blocker merely for
completeness.

Reclassify robustness seeds as:

- important supporting evidence where computationally reasonable;
- non-selection evidence;
- never choose the favorable seed;
- nonblocking unless a specific estimator implementation requires stochastic
  stability verification for correctness.

Respect D31's existing Causal Forest one-shot compute constraint.

Do not silently invalidate useful existing seed evidence.

---

# 8. T14 / decile / segment analysis

Keep T14 P1 / optional.

It must never block:
- T15;
- T16;
- T17;
- T18.

Remove any other document that accidentally makes decile outputs mandatory
artifacts for T-Learner/X-Learner/Causal Forest acceptance.

For example, if an estimator's required-artifact list includes a decile table
only because of prior governance, move that artifact to T14/P1.

---

# 9. Secondary `visit` outcome

`conversion` remains the primary outcome.

`visit` remains a permitted secondary robustness outcome.

Do NOT require a full duplicate modeling pipeline over `visit` unless the owner
later explicitly requests it.

A compact secondary analysis may be reported when inexpensive.

It cannot alter:
- model selection;
- primary conclusions;
- the frozen conversion analysis.

---

# 10. Keep these P0 scientific/correctness requirements

DO NOT simplify the following away:

- correct CRITEO dataset identity;
- D32 feature semantics;
- X/T/Y/exposure roles;
- train-only learned preprocessing;
- fold-local learned preprocessing for OOF/cross-fitting;
- no post-treatment leakage;
- frozen train/validation/held-out split;
- deterministic `_source_row_id` alignment;
- held-out isolation;
- correct T-Learner formula;
- correct X-Learner pseudo-outcomes / OOF logic;
- valid Causal Forest representation;
- common validation cohort;
- correct Qini/uplift metrics;
- treatment-allocation/top-K metrics;
- 500-draw paired bootstrap;
- pre-test freeze;
- exactly one held-out evaluation;
- evidence-bounded interpretation.

These constitute the scientific core.

---

# 11. Causal Forest remains mandatory, but do not over-engineer it

Causal Forest remains a selected main comparator.

Its current categorical representation blocker is real.

Do not:
- remove CF for convenience;
- feed raw categorical numeric tokens as ordinal values;
- invent an encoding in this documentation pass.

Keep the representation as an explicit unresolved implementation/ADR decision.

The implementation agent will resolve that separately.

---

# 12. Owner-decision boundary — add to AGENTS.md

Add a concise durable rule.

Use approximately:

## Owner decision boundary

Agents may autonomously make engineering decisions that do not alter the
scientific experiment, estimand, statistical procedure, estimator semantics,
selection rule, or held-out protocol.

For consequential methodological/statistical decisions, an agent must:

1. identify the decision;
2. provide only genuinely viable options;
3. recommend one with concise trade-offs;
4. explain INPUT -> OPERATION -> OUTPUT -> FAILURE MODE;
5. obtain owner approval before implementation.

Correctness fixes that merely restore an already-approved invariant
(e.g. preventing leakage or making learned preprocessing fold-local)
do not require a new methodology decision, but must be reported and verified.

Routine reruns under an already-approved corrected contract do not require
separate owner approval unless a gate fails or a methodology/config change
becomes necessary.

Also add this scope-control rule:

> Before adding a new mandatory diagnostic, gate, artifact, calibration,
> sensitivity, or infrastructure component, state which scientific conclusion
> would become invalid or materially less defensible without it.
> If no concrete answer exists, it must not become P0.

---

# 13. Simplify lifecycle language where possible

Do not remove:
- CODE PLAN for nontrivial implementation;
- VERIFY;
- REVIEW/FALSIFY;
- TEACH-BACK;
- ACCEPT.

But avoid turning every routine operation into its own governed lifecycle.

Deadline mode should favor:

UNDERSTAND CORE LOGIC
-> CODE PLAN
-> IMPLEMENT
-> VERIFY
-> REVIEW
-> TEACH-BACK
-> ACCEPT

Use immutable run evidence proportionally for consequential experiments, not
for routine descriptive calculations.

---

# 14. Rewrite the research framing in README

README should make the actual study clear.

It should say that the project is a:

> controlled empirical comparison of selected causal-uplift implementations
> under one common large-scale randomized advertising benchmark.

Explain that:

- Response asks who is likely to convert;
- uplift models ask where treatment changes conversion;
- models are compared on their ability to support incremental-response /
  treatment-allocation ranking;
- the goal is NOT universal algorithm superiority.

The result is conditional on:

- this dataset/population;
- D32 representation;
- selected model implementations;
- fixed protocol;
- selected metrics and targeting coverages.

Keep this concise.

---

# 15. Main project task graph

Reconcile MASTER/docs toward this core path:

DATA IDENTITY + SEMANTICS
    ->
FROZEN SPLIT
    ->
PREPROCESSING
    ->
UPLIFT METRICS
    ->
RESPONSE
    ->
T-LEARNER
    ->
X-LEARNER
    ->
CAUSAL FOREST
    ->
COMMON VALIDATION COMPARISON
    ->
PAIRED BOOTSTRAP
    ->
PRE-TEST FREEZE
    ->
ONE-SHOT HELD-OUT EVALUATION
    ->
FINAL INTERPRETATION

Supporting/off-path work may include:

- descriptive balance;
- X→T sanity diagnostic;
- duplicate sensitivity;
- precision sensitivity;
- deeper overlap diagnostics;
- decile/segment analysis;
- additional seed robustness;
- secondary visit analysis.

Nothing in that supporting list should block the core path unless an actual
correctness problem is discovered.

---

# 16. Public notebook story remains four notebooks

Do NOT change the four-notebook architecture.

01_data_understanding
- causal/decision problem
- dataset
- feature semantics
- concise EDA
- descriptive balance
- split/preprocessing principles

02_uplift_modeling
- Response
- T-Learner
- X-Learner
- Causal Forest
- core equations/logic
- development results

03_validation_uncertainty
- common validation comparison
- Qini/AUUC/uplift@K/incremental conversions
- paired bootstrap
- relevant robustness only

04_final_evaluation
- frozen experiment
- one-shot held-out evaluation
- final comparison
- limitations
- benchmark-specific conclusion

Public notebooks must not narrate historical governance complexity.

---

# 17. Documents to reconcile

At minimum review/update:

AGENTS.md
CLAUDE.md only if its pointer becomes inconsistent
README.md
docs/index.md
docs/00_project_overview.md
docs/03_assumption_and_audit_spec.md
docs/05_methodology_scope.md
docs/06_experiment_protocol.md
docs/decision_register.csv

Relevant ADRs only where affected.

Do not edit `src/`, tests, computational notebook code, or run evidence in this pass.

---

# 18. GitHub Issues

The current `github_issue_reconciliation_drafts.md` is now stale because it still
preserves the old mandatory T03-C calibration.

DO NOT apply that draft.

After documentation is corrected:

1. regenerate MASTER #20 replacement;
2. regenerate affected Issue patches;
3. especially update #4, #16, #17 and any issue that still treats:
   - 2,000 calibration;
   - randomization thresholds;
   - unnecessary seed robustness;
   - decile artifacts;
   as blocking requirements.

Keep Issue structure concise:

GOAL
INPUT
PROCESS
OUTPUT
VERIFICATION
DEPENDENCIES
DEFINITION OF DONE

Do not put long governance rationale into Issues.

---

# 19. Historical preservation

Do not hide prior decisions.

Where an old frozen requirement changes:

- preserve the historical row/text where practical;
- add D33 or an explicit superseded/amended status;
- reference the new decision;
- do not pretend the earlier decision never existed.

Do not modify immutable empirical evidence.

---

# 20. Final consistency questions

Before finishing, test every remaining P0 requirement with:

> If we remove this requirement, would the core model comparison become
> scientifically wrong, materially biased, irreproducible, or unable to support
> the stated conclusion?

If NO:
- make it supporting/P1/optional, or remove it from the current execution plan.

If YES:
- keep it P0 and briefly state why.

Do not use "more rigorous", "more auditable", or "more comprehensive" alone as a
reason to keep something P0.

---

# Final deliverable

Report:

1. New owner decisions added/amended.
2. Mandatory requirements removed from P0.
3. Requirements retained in P0 and WHY.
4. Optional/P1 work retained.
5. Files changed.
6. Remaining real methodology decisions.
7. Remaining implementation blockers.
8. Revised critical path.
9. Revised GitHub Issue draft status.
10. Any suspected over-engineering that still remains.

Run a stale-term search for at least:

- 2,000
- randomization calibration
- T03-C mandatory
- p95
- p99
- Monte Carlo
- X→T
- propensity
- float32
- duplicate sensitivity
- three seeds
- decile
- `ROBUSTNESS_REQUIRED`

Classify every remaining hit as:

- legitimately required;
- historical/superseded;
- optional/supporting;
- stale and needing correction.

Do not stop at an audit.
Apply all safe documentation/planning simplifications above.
Do not merge into main.