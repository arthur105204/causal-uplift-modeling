You are working as the primary code-review and refactoring agent for this repository:

arthur105204/causal-uplift-modeling

Your task is to perform a repository-wide correctness audit and then implement a coordinated fix for a CRITICAL feature-semantics bug affecting preprocessing, diagnostics, LightGBM models, Causal Forest integration, configs, tests, documentation, and public notebooks.

Do not make isolated local patches. First understand the whole dependency chain, then fix it coherently.

==================================================
1. CRITICAL FACT THAT MUST DRIVE THE REFACTOR
==================================================

The active dataset is CRITEO-UPLIFTv2.1.

The publisher/paper explicitly defines the 12 anonymous features as:

CONTINUOUS:
- f0
- f2
- f7
- f10

CATEGORICAL:
- f1
- f3
- f4
- f5
- f6
- f8
- f9
- f11

The official Criteo benchmark implementation also uses exactly:

cat_features = [
    "f1", "f3", "f4", "f5",
    "f6", "f8", "f9", "f11"
]

This mapping is AUTHORITATIVE for this refactor.

Important distinction:

physical storage dtype != semantic feature type

The released categorical tokens may physically be stored as float64.
That does NOT make them continuous or ordinal variables.

The current repository incorrectly treats all f0-f11 as generic numeric/continuous-like float64 model inputs.

That is the critical bug.

==================================================
2. FIRST: SCAN THE ENTIRE CODEBASE
==================================================

Before modifying files, recursively inspect the repository for every assumption that:

- f0-f11 are all numeric/continuous features
- all 12 model features should remain float64
- preprocessing is "no-op" or "identity"
- all features can be used in SMD / means / variances
- LightGBM receives all features as ordinary numeric columns
- CausalForest receives raw f0-f11 directly
- categorical semantics are inferred from cardinality
- old T03/T04/T07/T08/T09/T10 artifacts/results are reused
- public notebooks claim no preprocessing is necessary

Search for at least these patterns:

IdentityFeatureTransform
no-op preprocessing
identity transform
12 numeric
numeric features
all float64
FEATURE_COLUMNS
astype("float64")
astype('float64')
categorical_feature
max_absolute_smd
eligible_for_max_abs_smd
smd_feature_record
balance_diagnostics
cross_fitted_treatment_predictability
fit_binary_classifier
fit_regressor
fit_causal_forest
to_numpy
T04_ACCEPTED
T07_FULL
T08
T09
T10
f0-f11
f0–f11

Also inspect:

src/
tests/
configs/
docs/
docs/adr/
kaggle/
notebooks/internal/
outputs/runs references
decision_register.csv

Do NOT edit anything yet.

First create an impact map:

FILE
CURRENT ASSUMPTION
WHY IT IS WRONG OR UNAFFECTED
REQUIRED CHANGE
PRIORITY P0/P1/P2

Then continue implementing the fix.

==================================================
3. IMPORTANT PROJECT CONSTRAINTS
==================================================

Do NOT:

- access held-out/test labels or held-out performance
- rerun held-out evaluation
- use held-out information to decide preprocessing/model choices
- delete historical governed outputs
- rewrite old historical run artifacts as if they never happened
- silently modify immutable outputs/runs/*
- invent a new threshold just to make diagnostics pass
- infer category/continuous status from cardinality
- treat numeric category tokens as ordered values
- choose a Causal Forest encoding arbitrarily
- change the causal estimand
- change the frozen split
- change Qini/AUUC/uplift metric formulas without evidence
- reopen unrelated methodology decisions
- introduce unnecessary framework/architecture complexity

Preserve:

- dataset identity/checksums
- _source_row_id semantics
- 70/15/15 split membership
- T = treatment assignment
- Y = conversion
- visit = secondary
- exposure = audit-only/post-assignment
- T-Learner tau = mu1 - mu0
- X-Learner pseudo-outcome formulas
- X-Learner OOF/cross-fitting logic
- existing metric formulas
- no PEHE on real data
- held-out isolation
- immutable historical evidence

==================================================
4. TARGET FEATURE CONTRACT
==================================================

Create one authoritative semantic definition, ideally in src/data.py:

FEATURE_COLUMNS = (
    "f0", "f1", "f2", "f3", "f4", "f5",
    "f6", "f7", "f8", "f9", "f10", "f11"
)

CONTINUOUS_FEATURES = (
    "f0",
    "f2",
    "f7",
    "f10",
)

CATEGORICAL_FEATURES = (
    "f1",
    "f3",
    "f4",
    "f5",
    "f6",
    "f8",
    "f9",
    "f11",
)

Add fail-fast invariants:

- continuous and categorical sets do not overlap
- union equals FEATURE_COLUMNS
- canonical feature order remains f0...f11

Do NOT change the raw physical storage contract simply because a variable is categorical.

Raw/processed f0-f11 may remain float64 in Parquet.

==================================================
5. PREPROCESSING CONTRACT V2
==================================================

The current src/preprocessing.py likely contains an IdentityFeatureTransform and a contract that says:

- all f0-f11 remain float64
- no learned state
- no estimator-specific branches

This contract is superseded.

Refactor toward a semantic preprocessing contract.

For LightGBM:

- continuous features remain float64
- categorical tokens become unordered categorical features
- category vocabulary/state must be learned from TRAIN ONLY
- validation/test must reuse the train-fitted vocabulary
- no refitting on validation/test
- unseen categories must have an explicit deterministic handling rule
- no imputation unless separately justified
- row count/order must be preserved
- column order must remain canonical

Prefer a clear class such as:

LightGBMFeatureTransform

Do NOT preserve IdentityFeatureTransform as a compatibility alias if that would allow old incorrect code to keep running silently.

Bump preprocessing contract version.

Update preprocessing_contract() so it reports:

- continuous feature list
- categorical feature list
- physical storage precision
- LightGBM representation
- learned categorical vocabularies/state
- train-only fit boundary
- unseen-category policy
- no-imputation policy
- held-out application rule
- CausalForest representation status

==================================================
6. LIGHTGBM
==================================================

Audit src/lightgbm_baseline.py.

The current LightGBM Dataset construction probably does not explicitly preserve categorical semantics.

Fix both:

- binary classifier
- regression/effect model

Requirements:

- validate the input feature representation
- continuous features must remain numeric
- categorical features must be categorical, not raw float continuous
- explicitly pass categorical_feature or otherwise use LightGBM's supported native categorical representation
- train/validation categorical vocabularies must align
- prediction-time representation must match training representation
- reject raw categorical token frames where appropriate

This affects:

- Response baseline
- T-Learner outcome models
- X-Learner nuisance outcome models
- X-Learner effect regressors
- any future DR LightGBM stages

Do NOT alter T-Learner or X-Learner causal formulas merely because the base learner representation changes.

==================================================
7. T-LEARNER
==================================================

Inspect src/tlearner.py.

Expected outcome:

The math / partitioning logic should mostly remain unchanged.

Preserve:

tau_hat = mu1_hat - mu0_hat

Do not refactor this module merely for stylistic consistency unless required by the representation fix.

However, all OLD fitted T-Learner model results based on the incorrect feature representation must be considered stale development evidence.

==================================================
8. X-LEARNER
==================================================

Inspect src/xlearner.py and all calling code.

Preserve:

D1 = Y - mu0_oof
D0 = mu1_oof - Y

and final combination rule.

But verify category preprocessing under cross-fitting.

IMPORTANT:

For OOF nuisance models, preprocessing state must obey the same OOF leakage boundary.

If category vocabularies are learned, do not learn them using rows that belong to the OOF validation fold unless the project explicitly defines a leakage-safe shared semantic mapping.

Default safe rule:

For each OOF fold:
- fit categorical transform on that fold's training side
- apply that fitted transform to its OOF side

Do not use test data.

==================================================
9. T03 AUDIT / BALANCE DIAGNOSTICS
==================================================

This is also affected.

Current src/audit.py likely applies:

smd_feature_record()

to all FEATURE_COLUMNS and then computes:

max_absolute_smd

This is invalid for categorical numeric tokens.

Required behavior:

CONTINUOUS_FEATURES:
- SMD
- variance ratio
- continuous-distribution diagnostics such as KS where already justified

CATEGORICAL_FEATURES:
- category-distribution diagnostics
- do not compute numeric mean/SMD using category token magnitudes

Add a categorical diagnostic such as total variation distance:

TVD = 0.5 * sum_c |P(X=c | T=1) - P(X=c | T=0)|

Optionally report:
- max category proportion gap
- category count
- missing counts by arm

Do NOT invent an arbitrary TVD failure threshold.

smd_feature_record() should fail closed if called on a categorical feature.

balance_diagnostics() should separate continuous and categorical diagnostics.

Do NOT combine max SMD and max TVD by simply taking max() across them.

They are different quantities on different scales.

==================================================
10. T03 RANDOMIZATION CALIBRATION
==================================================

This must be REOPENED, not silently reused.

Preserve generic mechanisms that remain valid:

- conditional_permute_treatment()
- deterministic seed derivation
- fold assignment mechanics
- empirical_order_statistic()
- Monte Carlo interval mechanics
- empirical_tail_fraction()
- generic diagnostic_action() primitive if it is not tied to SMD semantics

But the old calibration contract:

max_absolute_eligible_feature_smd over all f0-f11

is SUPERSEDED.

Required state:

- continuous family: max absolute SMD
- categorical family: max TVD
- joint disposition / final p95/p99 action rule: UNSPECIFIED / BLOCKED until explicitly justified

Do not invent a new joint action threshold in this refactor.

The code/config should fail closed.

Suggested status naming:

T03_REOPENED_FEATURE_SEMANTICS
REOPENED_PENDING_MIXED_TYPE_SPEC
BLOCKED_PENDING_MIXED_TYPE_SPEC
SUPERSEDED_FEATURE_SEMANTICS

Preserve old lifecycle history; append a reopening event rather than pretending old runs never existed.

==================================================
11. T03 X->T PREDICTABILITY DIAGNOSTIC
==================================================

cross_fitted_treatment_predictability() uses LightGBM.

It must also respect categorical semantics.

For each diagnostic fold:

- fit category representation on training side only
- transform validation side using training representation
- fit LightGBM with categorical features recognized correctly

Preserve OOF isolation and deterministic fold behavior.

==================================================
12. CAUSAL FOREST — FAIL CLOSED FIRST
==================================================

This is extremely important.

econml.grf.CausalForest does NOT provide the same native categorical semantics as LightGBM.

Current code likely does something similar to:

X_arr = X.to_numpy()

and passes the raw 12 numeric token columns into CausalForest.

That is no longer acceptable.

Immediate fix:

Raw CRITEO f0-f11 must NOT be accepted directly by fit_causal_forest().

Fail closed with a clear error explaining that:

f1/f3/f4/f5/f6/f8/f9/f11 are categorical tokens and require an explicit estimator-specific CausalForest representation.

Do NOT arbitrarily choose:

- ordinal encoding
- one-hot encoding
- hashing
- target encoding
- paper's original transform

without an explicit design decision.

The official Criteo benchmark used categorical hashing/projection + one-hot in parts of its benchmark, but that is evidence about their benchmark preprocessing, NOT automatic authorization for econml CausalForest in this project.

CausalForest representation must be handled as a separate ADR / implementation decision, because feature expansion may radically affect memory/runtime at ~9.8M training rows.

Old CausalForest fitted results based on raw category-token-as-continuous representation are stale.

Do not access held-out.

==================================================
13. DATA CONTRACT / DOCUMENTATION
==================================================

Update docs/02_data_contract.md.

The schema should clearly distinguish:

PHYSICAL TYPE
vs
SEMANTIC TYPE

For example:

f0,f2,f7,f10
- physical: float64
- semantic: continuous

f1,f3,f4,f5,f6,f8,f9,f11
- physical: numeric anonymized tokens / float64
- semantic: categorical

Replace misleading language such as:

"canonical numeric order"

with:

"canonical column order"

where appropriate.

Do not rewrite historical claims unless they are current-contract claims.

==================================================
14. DECISION REGISTER
==================================================

Do not silently rewrite prior decision history.

Add a new explicit decision, e.g. D32:

Decision:
Publisher-defined feature semantics

Selected:
4 continuous + 8 categorical

LightGBM:
native categorical representation

CausalForest:
explicit estimator-specific representation required

Rejected:
treating categorical float tokens as ordered continuous quantities

Evidence:
publisher Table 2 + official benchmark implementation

Verification:
semantic contract tests + model input tests

Status:
Locked

If older D17 says something like "12 numeric features", annotate that its feature characterization is amended/superseded by D32 rather than rewriting history deceptively.

==================================================
15. CONFIGS / LIFECYCLE STATES
==================================================

Audit:

configs/t03_audit.json
configs/t04_preprocessing.json
configs/t07_baselines.json
configs/t08_tlearner.json
configs/t09_xlearner.json
configs/t10_causal_forest.json

Expected:

T04:
- reopen/supersede no-op preprocessing v1
- create/declare preprocessing v2
- old accepted run cannot authorize v2

T03:
- reopen feature-semantics-dependent diagnostics/calibration
- preserve unaffected identity/duplicate/permutation mechanics

T07/T08/T09:
- old fitted results become STALE_FEATURE_REPRESENTATION
- do not delete them
- require corrected development reruns

T10:
- raw feature representation blocked
- old fitted result stale
- corrected CF path blocked until representation ADR is accepted

Do not fabricate new successful run IDs, hashes, metrics, or lifecycle evidence.

==================================================
16. TESTS
==================================================

Rewrite/add regression tests so this bug cannot return.

At minimum test:

FEATURE CONTRACT
- exactly 4 continuous
- exactly 8 categorical
- no overlap
- union equals FEATURE_COLUMNS

PREPROCESSING
- continuous output remains float64
- categorical output uses categorical semantics
- train-only category fitting
- validation reuses train categories
- unseen-category policy is deterministic
- row order preserved
- feature order preserved
- no imputation
- transform-before-fit fails
- missing feature fails
- contract serializes

LIGHTGBM
- raw float category tokens are rejected
- correct categorical representation is accepted
- binary classifier works
- regression model works
- deterministic same seed
- train/validation feature schema alignment enforced

AUDIT
- SMD accepts continuous feature
- SMD rejects categorical feature
- TVD/category-distribution diagnostic works
- balance diagnostics separate feature families
- no joint threshold is fabricated
- T03 calibration status remains reopened/blocked

X->T DIAGNOSTIC
- fold-local preprocessing
- OOF isolation
- category representation correct

CAUSAL FOREST
- raw CRITEO feature frame is rejected
- already encoded generic numeric synthetic matrix may still be accepted where tests intentionally represent encoded CF input

T/X learners
- causal formulas unchanged
- no regression in row alignment, sign convention, OOF coverage

==================================================
17. PUBLIC NOTEBOOK 1
==================================================

Audit:

kaggle/01_data_understanding.ipynb

Public notebook constraints:

It must read as a first-publication artifact.

Do not narrate:
- previous failed versions
- prior bugs
- old run history
- "we used to..."
- internal governance noise

Reader-facing narrative should say:

- publisher identifies 4 continuous and 8 categorical features
- categorical values are anonymized numeric tokens
- numeric magnitude is not interpreted as ordinal
- continuous EDA uses quantiles/distributions
- categorical EDA uses cardinality/frequency concentration
- do not infer semantic type from cardinality
- preprocessing is estimator-aware, not generic no-op

Also preserve prior public-notebook cleanup goals:

- avoid machine-specific paths
- avoid "reused from earlier run"
- avoid governance-heavy narration
- keep charts/result/interpretation reader-first
- do not imply _source_row_id is a raw Criteo field
- decision problem should refer to treatment assignment / ITT, not actual exposure

==================================================
18. PUBLIC NOTEBOOK 2
==================================================

Audit:

kaggle/02_uplift_modeling.ipynb

Remove/replace:

- IdentityFeatureTransform
- "frozen no-op preprocessing"
- "12 numeric features"
- reuse of stale T07/T08/T09/T10 model results
- historical run narration in the public scientific story

Use corrected representation.

Keep public notebook reader-facing:

1. modeling question
2. response baseline
3. T-Learner
4. X-Learner
5. Causal Forest only when representation is valid
6. comparison
7. interpretation

Do not show internal governance machinery unless necessary for reproducibility.

==================================================
19. INTERNAL NOTEBOOKS
==================================================

Audit:

notebooks/internal/t03_data_integrity_audit.ipynb

Update source code to use mixed-type diagnostics.

Do not rewrite or delete historical outputs pretending the old run did not happen.

If the notebook is historical governed evidence, preserve historical artifact history and update the current source/next-run logic.

==================================================
20. STALE EVIDENCE POLICY
==================================================

Classify old evidence carefully.

Likely still valid:

- T01 data loading / checksum
- raw/processed row identity
- _source_row_id
- duplicate equality definitions
- T05 split membership
- T06 metric formulas
- T-Learner algebra
- X-Learner pseudo-outcome algebra

Likely stale / must be rerun:

- balance/SMD claims involving categorical token arithmetic
- X->T LightGBM predictability if categorical semantics were ignored
- T04 identity/no-op preprocessing
- T07 fitted response model
- T08 fitted T-Learner models
- T09 fitted X-Learner models
- T10 fitted CausalForest model

Do not delete stale artifacts.

Mark current contracts/configs accordingly.

==================================================
21. IMPLEMENTATION ORDER
==================================================

Use this order unless repository dependencies prove a small adjustment is necessary:

P0:
1. src/data.py
2. decision register feature-semantics decision
3. src/preprocessing.py
4. tests/test_preprocessing.py
5. src/lightgbm_baseline.py
6. tests/test_lightgbm_baseline.py
7. src/audit.py
8. tests/test_audit.py
9. src/causal_forest_baseline.py
10. tests/test_causal_forest_baseline.py

P1:
11. configs/t03_audit.json
12. configs/t04_preprocessing.json
13. configs/t07_baselines.json
14. configs/t08_tlearner.json
15. configs/t09_xlearner.json
16. configs/t10_causal_forest.json
17. docs/02_data_contract.md
18. docs/06_experiment_protocol.md
19. docs/adr/ADR-base-learner.md
20. CF ADR / representation status
21. internal T03 notebook
22. public notebook 01
23. public notebook 02

P2:
24. run focused tests
25. run full unit test suite
26. inspect diffs for stale assumptions
27. report required development reruns

Do NOT run held-out evaluation.

==================================================
22. TEST COMMANDS
==================================================

After core feature/preprocessing/LightGBM changes:

pytest -q \
  tests/test_data.py \
  tests/test_preprocessing.py \
  tests/test_lightgbm_baseline.py

After audit changes:

pytest -q tests/test_audit.py

After CausalForest guard:

pytest -q tests/test_causal_forest_baseline.py

Then:

pytest -q \
  tests/test_tlearner.py \
  tests/test_xlearner.py

Finally:

pytest -q
git diff --check

Also run repository search again for stale assumptions:

git grep -n -E \
"IdentityFeatureTransform|no-op preprocessing|12 numeric|numeric features|all.*float64|max_absolute_eligible_feature_smd|categorical_feature"

Review every hit manually.

==================================================
23. IMPORTANT: DO NOT FAKE SUCCESS
==================================================

If tests expose secondary issues:

- fix them if they are directly caused by this feature-semantics refactor
- report unrelated pre-existing failures separately

Do not weaken tests merely to get green.

Do not remove assertions that expose real semantic problems.

Do not fabricate:
- model metrics
- accepted lifecycle states
- successful full-run IDs
- hashes
- validation results
- CausalForest resource feasibility

==================================================
24. REQUIRED FINAL REPORT
==================================================

When finished, give me a structured report with:

A. ROOT CAUSE
Explain exactly how numeric storage was confused with semantic feature type.

B. FILES CHANGED
For every file:
- what changed
- why
- whether change is correctness / test / config / documentation / presentation

C. UNAFFECTED COMPONENTS
Explicitly list what did NOT need methodological changes.

D. STALE EVIDENCE
List old runs/results that can no longer authorize current models.

E. CAUSAL FOREST STATUS
State clearly whether it is:
- blocked
- encoded
- tested
- resource-validated
Do not imply more than actually completed.

F. TEST RESULTS
Include exact test commands and pass/fail counts.

G. REMAINING BLOCKERS
Especially:
- T03 mixed-type calibration joint action rule
- CausalForest categorical representation
- required T07/T08/T09/T10 development reruns

H. DIFF AUDIT
List any remaining grep hits for:
- no-op preprocessing
- 12 numeric
- IdentityFeatureTransform
- all-feature SMD
and explain whether each remaining occurrence is historical, intentional, or still needs fixing.

==================================================
25. WORKING STYLE
==================================================

Do not stop after the initial scan.

Proceed from audit to implementation unless there is a true methodological ambiguity that cannot safely be resolved.

For ambiguous choices:

- fail closed
- document the blocker
- do not invent a methodological decision

Make the smallest coherent repository-wide correction.

Avoid overengineering.

The primary goal is methodological correctness, leakage safety, reproducibility, and a clean public scientific narrative.