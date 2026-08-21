# Execution Protocol

This file is the MASTER STUDY INSTRUCTION.

Do NOT load or execute the entire file at once.

Work phase-by-phase.

For each phase:

1. Read only the current phase and any explicitly referenced previous study artifacts.
2. Inspect the actual repository source/tests needed for that phase.
3. Produce the requested output files.
4. Verify important claims against source code.
5. Write/update `docs/study/STUDY_STATE.md`.
6. STOP after completing the phase.
7. Do not continue to the next phase until I explicitly say:
   CONTINUE STUDY

The repository source code is the source of truth.
Generated study files are navigation/learning aids only.

If a generated study file conflicts with source code:
SOURCE CODE WINS.

Do not recursively trust previous AI-generated study notes without re-verifying
important technical claims against source.
IMPORTANT SOURCE-OF-TRUTH RULE

The generated learning/*.md files are navigation/study aids only.

The repository implementation is the source of truth.

Whenever answering a technical question, reviewing a design,
or testing my understanding:

1. use the study files to locate the relevant area;
2. reopen the actual source code;
3. verify the claim against the current implementation;
4. if the study file disagrees with source code, source code wins;
5. update the study file only after confirming the code.

Do not recursively treat AI-generated study notes as evidence.
I need to relearn this codebase quickly enough to explain and modify it
in front of senior data-science / ML mentors.

This is a RUSH REVIEW.

Do not optimize for producing documentation.
Optimize for whether I can independently understand, trace, debug,
and modify the core system.

TIME/ATTENTION CONSTRAINT:
Assume I have only one focused study session.

Do not modify production source code.

============================================================
PHASE 1 — BUILD THE MINIMUM MENTAL MODEL
============================================================

Inspect the actual repository.

Do not infer architecture from filenames alone.

Focus specifically on this project's real architecture:

processed data / identity
→ frozen split
→ preprocessing
→ uplift metrics
→ Response baseline
→ T-Learner
→ X-Learner
→ Causal Forest
→ run/checkpoint/artifact machinery
→ validation
→ future held-out evaluation

Ignore web-app concepts such as frontend, authentication, controllers,
database, REST APIs, etc. unless they actually exist in this repository.

Create only:

learning/00_CRASH_CODEBASE_MAP.md

It must contain:

1. Project purpose in <= 10 lines.
2. One ASCII system/data-flow diagram.
3. The 6–8 most important source files/modules.
4. Dependency direction between them.
5. The primary end-to-end execution path:
   input → transformation → model → predictions → metrics → artifacts.
6. What is frozen methodology vs implementation detail.
7. The five highest-risk correctness areas.
8. The exact order I should study the code.

Every important claim must reference:
file + symbol/function/class.

Mark unsupported claims UNKNOWN.

Do not create generic framework explanations.

============================================================
PHASE 2 — TRACE THE CORE FLOWS
============================================================

Identify only the 4 most important flows in THIS repository.

At minimum consider:

A. data artifact → frozen TRAIN/VALIDATION rows
B. TRAIN rows → T-Learner/X-Learner predictions
C. TRAIN rows → Causal Forest model → validation tau
D. persisted predictions → uplift metrics

For each flow show:

TRIGGER
→ INPUT
→ exact file/function
→ transformation
→ output
→ side effect/artifact
→ failure/leakage risk

Show important data shapes where possible.

Do not skip intermediate functions that affect correctness.

============================================================
PHASE 3 — DEEP DIVE THE CRITICAL CODE
============================================================

Prioritize these if they exist:

src/data.py
src/split.py
src/metrics.py
src/tlearner.py
src/xlearner.py
src/causal_forest_baseline.py
src/causal_forest_runner.py
kaggle/02_uplift_modeling.ipynb

For each selected module explain only:

WHY IT EXISTS

INPUT

OUTPUT

CORE ALGORITHM

IMPORTANT CALL CHAIN

IMPORTANT VARIABLES

SIDE EFFECTS

FAILURE MODES

CAUSAL / STATISTICAL ASSUMPTIONS

LEAKAGE / ALIGNMENT RISKS

WHY CURRENT IMPLEMENTATION MAY HAVE BEEN CHOSEN

REALISTIC ALTERNATIVE

TRADE-OFF

WHAT WOULD CHANGE IF REQUIREMENT CHANGED

HOW TESTS PROVE IT

AI-GENERATED CODE RISKS

Do not explain routine Python syntax unless it affects runtime behavior.

Clearly label claims:

CONFIRMED BY CODE
LIKELY
UNKNOWN

============================================================
PHASE 4 — FIND WHAT I MUST BE ABLE TO EXPLAIN
============================================================

Create:

learning/01_MUST_KNOW.md

Limit this aggressively.

Include:

- 10 concepts I must understand;
- 10 functions/classes I must recognize instantly;
- 5 data/causal contracts I must not get wrong;
- 5 implementation decisions a senior mentor may challenge;
- 5 known weaknesses or trade-offs;
- 5 things I must NEVER bluff about.

Do not produce a general repository summary again.

============================================================
PHASE 5 — TEST ME, DO NOT TEACH ME FIRST
============================================================

After generating the two files above, STOP generating documents.

Start an interactive technical defense.

Ask ONE question at a time.

Do not give the answer before I answer.

Questions must be based on actual repository code.

Frequently ask:

- Where exactly is that implemented?
- What is the input shape?
- What is returned?
- What happens to _source_row_id?
- What prevents leakage?
- Why is this fitted on TRAIN only?
- Why is this metric valid for uplift ranking?
- Why not use another estimator?
- What happens if this function fails?
- What artifact exists after this step?
- How does resume know it is the same experiment?
- What would change if this requirement changed?
- Which test would detect the regression?

After each answer:

1. classify:
   CORRECT
   PARTIALLY CORRECT
   INCORRECT
   TOO VAGUE

2. tell me exactly what was missing;

3. cite the relevant code;

4. ask one deeper follow-up.

Do not reward buzzwords.

If I cannot explain INPUT → OPERATION → OUTPUT,
treat that as lack of understanding.

============================================================
PHASE 6 — CHANGE/DEBUG TESTS
============================================================

Periodically give me a realistic requirement or bug.

Before helping, require me to state:

1. current flow;
2. files I think need modification;
3. change I propose;
4. possible regression;
5. how I would test it.

Critique my reasoning before giving implementation help.

============================================================
SUCCESS CRITERIA
============================================================

The review is successful only if I can, without reading generated answers:

- explain the end-to-end data/model flow;
- explain T-Learner and X-Learner implementation;
- explain Causal Forest implementation and runner;
- explain metric orientation and row alignment;
- identify held-out/leakage boundaries;
- identify where persisted artifacts come from;
- trace a traceback to the likely layer;
- describe how I would modify a realistic requirement;
- explain one current implementation weakness honestly.

Do not optimize for making me feel prepared.
Try to expose what I still do not understand.