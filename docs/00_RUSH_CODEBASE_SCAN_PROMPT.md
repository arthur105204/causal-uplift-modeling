# RUSH FULL CODEBASE SCAN

You are a senior Data Scientist / ML Engineer helping me rapidly relearn this repository.

I am using FAST mode and have very limited time.

Your goal is to inspect the repository broadly enough that the resulting study material is reliable.

DO NOT stop between phases.
DO NOT ask me for confirmation.
DO NOT modify production source code.
DO NOT run expensive training jobs.
DO NOT inspect held-out results.

Execute everything below in ONE continuous pass:

INVENTORY
→ SYSTEMATIC SCAN
→ COVERAGE AUDIT
→ STUDY DOCUMENT GENERATION

Optimize for useful understanding per token/time.

---

# OUTPUT

Create only:

    docs/00_CRASH_CODEBASE_MAP.md

Do NOT create dozens of intermediate files.

The scan manifest / coverage audit should be included as compact appendices
inside this document.

The repository source code is the source of truth.

Generated documentation is only a study aid.

---

# 0. SNAPSHOT REPOSITORY STATE

First inspect:

    git branch --show-current
    git rev-parse HEAD
    git status --short
    git ls-files

Record at the top of the document:

Branch:
HEAD:
Generated at:

Add:

> This study guide describes the repository state at the commit above.
> If HEAD changes, implementation claims must be reverified.

---

# 1. INVENTORY THE ENTIRE LOGICAL CODEBASE

Enumerate all git-tracked logical project files.

Classify them as:

SOURCE
TEST
CONFIG
SCRIPT
NOTEBOOK
DOCUMENTATION / DECISION RECORD
DATA METADATA / MANIFEST
ENVIRONMENT / BUILD
OTHER

Ignore detailed inspection only for things such as:

.git/
.venv/
__pycache__/
cache/
large raw datasets
binary model artifacts
outputs/runs/
generated temporary files

Do NOT skip a source/config/test file merely because its filename looks unimportant.

For each logical project file determine:

PATH
TYPE
ROLE
IMPORTANCE

Importance:

CRITICAL
HIGH
MEDIUM
LOW

Do not output the full inventory yet.
Keep it internally and summarize it later in the appendix.

---

# 2. SCAN STRATEGY — FAST BUT SYSTEMATIC

Do NOT attempt to explain every line.

The goal is:

100% logical-file awareness
+
100% critical execution-path coverage
+
deep inspection of correctness-critical code.

Use this rule:

CRITICAL:
read implementation deeply.

HIGH:
read all behavior affecting correctness.

MEDIUM:
read relevant symbols / call sites.

LOW:
identify role and dependencies; skim unless needed.

Prioritize roughly:

data/contracts
→ dataset identity
→ split
→ preprocessing
→ metrics
→ Random / Response baseline
→ T-Learner
→ X-Learner
→ Causal Forest
→ experiment runners
→ scripts
→ notebooks
→ tests
→ configs
→ relevant decision docs

Adapt to actual repository evidence.

---

# 3. FILES / AREAS THAT MUST NOT BE SKIPPED

If they exist, inspect especially carefully:

src/data.py
src/split.py or split-related implementation
src/metrics.py

Response model implementation
src/tlearner.py
src/xlearner.py

src/causal_forest_baseline.py
src/causal_forest_runner.py

scripts/t11_run_stage.py

matching tests

relevant configs

kaggle/01_data_understanding.ipynb
kaggle/02_uplift_modeling.ipynb

README and methodological / decision documents that constrain implementation.

Do not assume these exact paths exist.
Verify them.

---

# 4. HOW TO INSPECT EACH CRITICAL MODULE

For every CRITICAL/HIGH implementation identify:

WHY IT EXISTS

IMPORTANT SYMBOLS

WHO CALLS IT

WHAT IT CALLS

INPUT

OUTPUT

SIDE EFFECTS

DATA SHAPE / ROW IDENTITY

FAILURE PATHS

TESTS

CONFIG DEPENDENCIES

LEAKAGE / ALIGNMENT RISKS

STATISTICAL ROLE

CAUSAL ROLE

RESOURCE / PERFORMANCE RISKS

Do not spend time explaining basic Python syntax.

---

# 5. TRACE THE REAL END-TO-END FLOW

Verify actual implementation for:

processed/raw data
→ selector / metadata / checksum
→ dataset abstraction
→ _source_row_id
→ frozen split membership
→ TRAIN / VALIDATION / HELD-OUT boundaries
→ X / T / Y construction
→ learner fit
→ prediction
→ tau / score
→ persisted predictions
→ uplift metrics
→ experiment artifacts / manifests

For every important transition identify:

FILE
SYMBOL
INPUT
OPERATION
OUTPUT
NEXT CALL

Do NOT invent missing transitions.

If not confirmed:

UNKNOWN

---

# 6. DATA / CAUSAL CONTRACT AUDIT

Locate code/test evidence for:

feature set X
treatment
primary outcome
secondary outcome
exposure handling
_source_row_id
dtype / precision
row retention
TRAIN / VALIDATION / HELD-OUT
split seed / stratification
estimand
prediction interpretation
primary metric
secondary metrics
diagnostic metrics
bootstrap / calibration design

For each distinguish:

FROZEN METHODOLOGY

IMPLEMENTATION DETAIL

RESOURCE / EXECUTION DECISION

This distinction is important.

---

# 7. MODEL COVERAGE

Verify the actual implementation of:

Random ranking
Response model
T-Learner
X-Learner
Causal Forest

For each identify:

TRAINING POPULATION

INPUT

FIT ENTRY POINT

TRAINING PROCEDURE

PREDICTION ENTRY POINT

OUTPUT SCORE

WHAT SCORE MEANS

WHAT SCORE DOES NOT MEAN

SEED / RANDOMNESS

LEAKAGE BOUNDARY

VALIDATION PATH

TEST COVERAGE

KNOWN LIMITATIONS

Do NOT call the Response model a causal estimator.

Do NOT describe predicted uplift as observed individual treatment effect.

---

# 8. T-LEARNER / X-LEARNER — DEEP SCAN

For T-Learner verify:

treated outcome model
control outcome model
mu1
mu0
tau = mu1 - mu0
validation scoring
row alignment
sign convention

For X-Learner verify:

cross-fitting
fold generation
OOF nuisance predictions
mu1
mu0
D1
D0
effect models
weighting g(x)
final tau
OOF coverage checks
sign convention
row alignment

Identify precisely where leakage would occur if OOF logic were removed.

---

# 9. CAUSAL FOREST — DEEP SCAN

Verify the actual selected estimator.

If current code uses:

econml.grf.CausalForest

describe that implementation rather than a generic DML Causal Forest.

Inspect:

X/T/Y handling
n_estimators
criterion
honest
inference
min_samples_leaf
max_samples
min_balancedness_tol
subforest_size
max_depth
n_jobs
random_state

For each important parameter explain briefly:

WHAT IT CONTROLS
WHY CURRENT VALUE EXISTS
STATISTICAL EFFECT
COMPUTATIONAL EFFECT

Inspect:

alpha
Jacobian
tau
pseudo-inverse behavior
rank diagnostics
condition number diagnostics

Separate:

HARD CORRECTNESS

from:

DIAGNOSTIC ONLY

based on actual current code/tests.

---

# 10. T11 RUNNER — DEEP SCAN

Trace the full runner:

request/config
→ cohort selection
→ exact cohort identity
→ TRAIN materialization
→ fit
→ model serialization
→ checkpoint
→ reload verification
→ VALIDATION materialization
→ prediction
→ persistence
→ diagnostics
→ resource evidence
→ artifact manifest

Inspect checkpoint/resume behavior.

Verify:

run_id
dataset identity
full TRAIN identity
fit cohort identity
VALIDATION identity
config hash
sampling seed
model seed

Explain what mismatches cause fail-closed behavior.

Also identify:

serialization memory duplication
TRAIN memory lifetime
validation memory behavior
resource sampler
RSS
available RAM
swap

---

# 11. METRIC SCAN

Inspect actual metric code for:

Qini
Qini above theoretical random
uplift@K
incremental conversions
random reference
ranking direction
tie breaking
_source_row_id use

Explain briefly:

why AUC/AP/logloss are diagnostic rather than causal-selection metrics

why good response prediction does not guarantee good uplift ranking

how row alignment is protected

---

# 12. TEST COVERAGE

For each CRITICAL implementation inspect relevant tests.

Map:

SOURCE BEHAVIOR
→ TEST
→ CONTRACT PROTECTED

Especially verify tests for:

dataset identity
split integrity
feature roles
metric sign/orientation
T-Learner
X-Learner OOF/sign
Causal Forest config
Causal Forest diagnostics
runner checkpoints
resume identity
exact cohort identity
serialization/reload
leakage / alignment

Also identify important behavior that appears weakly tested or untested.

---

# 13. NOTEBOOK SCAN

Inspect notebook structure without wasting time on every JSON field.

Identify:

reader-facing narrative
RUN_* flags
production source calls
historical recomputation branches
artifact loading paths
expensive cells
unsafe cells if any
lazy/full-data materialization behavior

Do not treat notebook code as canonical when implementation lives in src/.

---

# 14. STALE DOCUMENTATION / AI-GENERATED CODE AUDIT

Compare implementation against:

comments
README
configs
decision docs
notebook narrative

Identify only meaningful discrepancies.

Look for:

stale documentation
misleading names
unnecessary abstraction
duplicate logic
overengineering
weak validation
resource duplication
hidden coupling
AI-generated complexity
comments inconsistent with implementation

Do NOT manufacture criticism.

Separate findings into:

REAL ISSUE
ACCEPTABLE TRADE-OFF
STALE DOCUMENTATION
UNKNOWN

---

# 15. COVERAGE AUDIT — DO THIS BEFORE WRITING FINAL GUIDE

Now audit your own scan.

Verify that every logical project file is accounted for as:

READ_FULL
READ_RELEVANT
SKIPPED_WITH_REASON

Check especially:

unread source modules
unread tests for critical code
configs referenced by source
scripts invoking source
notebooks invoking source
missing call-chain links
contracts supported only by documentation but not code
source behavior without tests

Do not claim full coverage if important paths remain unread.

Choose one disposition:

SCAN_COMPLETE

SCAN_COMPLETE_WITH_KNOWN_GAPS

SCAN_INCOMPLETE

Continue to write the study guide even if there are known gaps,
but label those gaps clearly.

---

# 16. GENERATE docs/00_CRASH_CODEBASE_MAP.md

The document must be optimized for rapid learning.

Use this structure:

# Repository Snapshot

# 1. Project in 60 Seconds

# 2. Architecture / Data Flow Diagram

# 3. Frozen Data / Causal / Evaluation Contracts

# 4. End-to-End Execution Flow

# 5. Critical Modules

# 6. Model Portfolio

# 7. T-Learner

# 8. X-Learner

# 9. Causal Forest

# 10. Causal Forest Jacobian / Support Logic

# 11. T11 Runner / Resume / Artifacts

# 12. Metrics

# 13. Resource / Memory Behavior

# 14. Testing Map

# 15. Important Design Decisions

# 16. Known Weaknesses / AI-Code Risks

# 17. Debugging Map

# 18. If Requirements Change

# 19. What I Must Know Before Mentor Review

# 20. Crash Review

# Appendix A — Codebase Scan Coverage

Include compact table:

PATH
TYPE
IMPORTANCE
SCAN STATUS

# Appendix B — Known Gaps / Unknowns

# Appendix C — Stale Documentation / Implementation Discrepancies

---

# 17. OUTPUT STYLE — FAST MODE

This is a RUSH review.

Prefer:

tables
ASCII flows
short paragraphs
call chains
exact symbols
compact explanations

Avoid:

generic definitions
long prose
repeated explanations
framework tutorials
marketing language
buzzwords
fake design justifications

Do not quote large source-code blocks.

Use:

file → symbol

instead.

For CRITICAL code, depth matters more than breadth.

For LOW-importance files, coverage matters more than detailed explanation.

---

# 18. PRIORITY IF CONTEXT OR TIME GETS TIGHT

If you cannot deeply analyze everything, NEVER sacrifice these:

1. data.py / dataset identity
2. split logic
3. metrics.py
4. T-Learner
5. X-Learner
6. Causal Forest baseline
7. Causal Forest runner
8. matching tests
9. model/data configs
10. modeling notebook execution flow

Compress LOW-priority documentation instead.

Do NOT silently skip critical code.

---

# 19. FINAL TERMINAL RESPONSE

After creating:

    docs/00_CRASH_CODEBASE_MAP.md

print only:

Repository:
Branch:
HEAD:
Scan disposition:
Logical files accounted for:
Critical modules deeply inspected:
Known gaps:
Output:
docs/00_CRASH_CODEBASE_MAP.md

Then STOP.

Do not start interactive Q&A.
Do not modify source code.
Do not run model training.