   # Repository instructions

   ## 1. Source precedence

   When project sources conflict, use this authority order:

   1. `docs/decision_register.csv`
   2. Frozen contracts, experiment protocol, metric specification, and accepted ADR decisions
   3. Accepted task-specific empirical evidence
   4. GitHub Issue wording
   5. Existing implementation details

   Do not silently override a higher-authority source.

   If a GitHub Issue conflicts with a higher-authority source, stop and report the
   conflict before making a methodological or statistical change.

   ---

   ## 2. Frozen project foundation

   Sprint 1 is completed and frozen.

   Do not reopen or silently modify frozen decisions including:

   - research question and decision context;
   - released-row analysis population;
   - `X = f0...f11`;
   - `T = treatment`;
   - primary `Y = conversion`;
   - `visit` as secondary outcome;
   - `exposure` as audit-only and excluded from `X`;
   - assignment / ITT CATE estimand;
   - retain-all primary duplicate policy;
   - primary `float64` analytical precision;
   - 70/15/15 outer split;
   - joint `(T,Y)` stratification;
   - frozen seed conventions;
   - held-out isolation until T17;
   - mandatory T-Learner, X-Learner, and Causal Forest scope;
   - Response model as a non-causal diagnostic baseline;
   - S-Learner as deferred;
   - DR-Learner as conditional/stretch only;
   - frozen uplift metric conventions;
   - 500-draw paired treatment-arm-stratified evaluation bootstrap;
   - one-shot held-out evaluation at T17.

   Predicted uplift is not true individual treatment effect.

   Do not invent business semantics for anonymized `f0...f11`.

   ---

   ## 3. Sprint 2+ execution architecture

   For T02–T18, follow the current GitHub Issue and the MASTER execution
   architecture (Issue #20). Kaggle is the primary execution environment; the active
   notebook series is `kaggle/01_data_understanding.ipynb` through
   `kaggle/04_final_evaluation.ipynb` — a reader-facing story, deliberately
   different from the GitHub Issue/task structure it draws on (see MASTER #20 for
   the exact task-to-notebook mapping). Heavy or held-out-sensitive computation may
   live in `notebooks/internal/` when justified; it is not reader-facing.
   `notebooks/legacy/*.ipynb` holds the pre-reset notebooks as historical
   evidence — inherited, not re-derived, and not edited going forward. Do not
   invent a second planning system: GitHub Issues are the execution plan.

   Default lifecycle:

   DEPENDENCY READY
   → UNDERSTAND / TUTOR
   → RESOLVE REAL DECISIONS
   → DECISION-EVIDENCE when genuinely required
   → CODE PLAN / IMPLEMENTATION BLUEPRINT
   → OWNER UNDERSTANDING GATE
   → IMPLEMENT
   → VERIFY
   → CLEAN RUN / REPRODUCIBILITY
   → INTERPRET
   → REVIEW / FALSIFY
   → TEACH-BACK
   → ACCEPT
   → COMMIT / CLOSE as a separate explicit action

   Do not automatically advance to the next phase.

   The user controls phase transitions.

   If the user requests `[TUTOR]`, `[CODE PLAN]`, `[IMPLEMENT]`, `[REVIEW]`,
   or `[ACCEPT]`, execute only that phase unless explicitly authorized otherwise.

   ---

   ## 4. Deadline mode

   The project may operate in deadline mode.

   In deadline mode:

   - conceptual/statistical understanding remains required;
   - consequential open decisions must still be resolved before implementation;
   - CODE PLAN remains required before non-trivial implementation;
   - the owner must understand the main
   `INPUT → OPERATION → OUTPUT` flow;
   - production implementation may proceed before the owner masters all Python/API
   syntax;
   - pre-implementation micro-coding may be shortened, replaced by prediction or
   pseudocode, or deferred when the remaining gap is syntax rather than
   methodology;
   - syntax/code learning may occur after implementation through a focused
   POST-IMPLEMENTATION CODE MAP.

   Deadline mode does NOT permit:

   - methodology changes without approval;
   - held-out leakage;
   - skipping verification;
   - skipping independent review;
   - accepting code the owner cannot later explain at the core-flow level;
   - treating successful execution as scientific correctness.

   When deadline mode is active, prioritize:

   UNDERSTAND CORE LOGIC
   → CODE PLAN
   → IMPLEMENT
   → VERIFY
   → CODE MAP
   → REVIEW
   → TEACH-BACK
   → ACCEPT

   over prolonged pre-implementation syntax exercises.

   ---

   ## 5. CODE PLAN gate

   Before non-trivial implementation, produce or verify an implementation blueprint.

   At minimum identify:

   1. task input;
   2. task output;
   3. main data/model flow;
   4. 5–10 major operations;
   5. important functions/APIs;
   6. statistical or causal assumptions;
   7. leakage/alignment/support failure modes;
   8. verification checks;
   9. what belongs in:
      - notebook core logic;
      - reusable `src/`;
      - tests;
      - run-artifact plumbing.

   Do not produce production implementation during `[CODE PLAN]`.

   ---

   ## 6. Notebook-first policy

   The designated task notebook is the primary human-readable research artifact.

   The notebook must expose:

   - the research question being answered;
   - core data/model flow;
   - important calculations;
   - verification;
   - empirical observations;
   - interpretation and limitations.

   Do not turn the notebook into a thin wrapper around opaque helper code.

   Use:

   - `src/` for reusable logic when reuse or correctness materially justifies it;
   - `tests/` for focused correctness/regression checks;
   - `configs/` for reproducible configuration where appropriate;
   - `outputs/runs/<run_id>/` for immutable machine-readable run evidence.

   Notebook-first does not mean notebook-only.

   The `outputs/runs/<run_id>/` immutable-manifest machinery (D21) is proportional to
   consequential experiments — model training, persisted predictions, model
   comparison, bootstrap uncertainty, and frozen/held-out evaluation. It is not
   required around routine EDA tables, temporary figures, or one-off exploratory
   calculations; do not build custom lifecycle engines or artifact registries around
   those.

   ---

   ## 7. T01 downstream data contract

   T02+ data-consuming tasks must inherit the accepted T01 data path:

   authoritative selector / immutable T01 evidence
   → expected processed checksum verification
   → validated processed Parquet
   → task-specific operation

   Do not select input through filename order, glob preference, or directory
   heuristics.

   Reuse the accepted T01 consumer loader where appropriate.

   `_source_row_id`:

   - is released-row provenance/alignment metadata;
   - is not a person, customer, or user identifier;
   - must never enter `X`.

   Do not bypass checksum validation with an arbitrary direct file path.

   ---

   ## 8. Held-out isolation

   Before T17:

   - do not inspect held-out model performance;
   - do not use held-out outcomes for EDA-driven redesign;
   - do not tune models, preprocessing, thresholds, seeds, or feature choices using
   held-out results;
   - do not generate unofficial held-out diagnostics.

   T17 is the first and only authorized held-out evaluation under the T16 freeze.

   If an operation would access held-out evaluation before T17, stop.

   ---

   ## 9. Implementation rules

   During `[IMPLEMENT]`:

   - implement only the current Issue scope;
   - keep the diff focused;
   - do not silently change methodology;
   - do not perform unrelated refactors;
   - do not start the successor Issue;
   - preserve deterministic row alignment;
   - preserve run-scoped evidence;
   - add only the smallest justified reusable helpers/tests;
   - avoid unnecessary abstraction and framework-building;
   - retain core research/statistical logic visibly in the notebook.

   Do not modify frozen project documents merely to make implementation easier.

   ---

   ## 10. Verification and clean-run rules

   Successful execution is not sufficient verification.

   Check task-relevant invariants including, where applicable:

   - input identity/checksum;
   - row count;
   - schema and dtypes;
   - feature roles;
   - `_source_row_id` alignment;
   - treatment/outcome encoding;
   - denominators;
   - treatment-arm support;
   - signs and prediction alignment;
   - metric orientation;
   - leakage;
   - deterministic outputs;
   - artifact lineage.

   Distinguish:

   notebook exists
   ≠ notebook parses
   ≠ tests pass
   ≠ clean Run All succeeds

   Where applicable, final verification requires a fresh-kernel Run All with zero
   uncaught errors and reconciliation to expected artifacts/invariants.

   Do not rerun computationally expensive work unnecessarily if bounded
   verification already proves the required property; document the limitation.

   ---

   ## 11. Review / falsification

   During `[REVIEW]`, do not edit first.

   Attempt to falsify the implementation and interpretation.

   Review task-relevant risks such as:

   - frozen-protocol compliance;
   - wrong population or denominator;
   - row/prediction misalignment;
   - leakage;
   - causal/statistical errors;
   - sign errors;
   - unsupported extrapolation;
   - incorrect metric implementation;
   - artifact inconsistency;
   - nondeterminism;
   - overclaiming;
   - edge cases;
   - compute assumptions.

   Record findings before fixes.

   Classify findings when useful as:

   - BLOCKER
   - MAJOR
   - MINOR
   - ACCEPTED LIMITATION
   - NOT A BUG

   Only fix findings accepted for remediation.

   ---

   ## 12. Post-implementation code understanding

   When implementation was accelerated in deadline mode, produce a focused CODE MAP.

   Prefer the 10–15 blocks that explain most of the task logic.

   For each important block explain:

   INPUT
   → OPERATION
   → OUTPUT
   → WHY IT EXISTS
   → FAILURE MODE

   Prioritize understanding:

   - core DS/statistical transformations;
   - estimator equations and row flow;
   - metrics;
   - data alignment;
   - causal interpretation.

   Do not require the owner to independently reinvent generic infrastructure such
   as hashing, environment capture, serialization, resource monitoring, or GitHub
   API plumbing unless it affects correctness.

   ---

   ## 13. Interpretation rules

   Separate:

   - observation;
   - statistical interpretation;
   - causal interpretation;
   - limitation;
   - downstream implication.

   Do not claim that descriptive EDA establishes causal effects.

   Do not infer business meaning from anonymized features.

   Do not claim randomization is proven by balance diagnostics.

   Do not describe model predictions as true ITE.

   Do not claim an estimator is superior without the frozen comparison evidence.

   ---

   ## 14. Acceptance and repository closure

   Implementation completion is not acceptance.

   Before `[ACCEPT]`, verify that:

   - required decisions are resolved;
   - implementation is complete;
   - verification passes;
   - clean execution/reproducibility passes where applicable;
   - review findings are resolved or explicitly accepted;
   - interpretation is appropriately bounded;
   - the owner understands the core flow;
   - expected immutable evidence exists;
   - no unrelated changes are included.

   Commit, push, Issue closure, and starting the successor task are separate
   explicit actions.

   Do not commit, push, close an Issue, or begin the next Issue unless explicitly
   authorized.

   ---

   ## 15. Multi-agent coordination

   Only one agent should act as writer on the same working tree at a time.

   If another agent is being used as tutor, architect, or reviewer:

   - do not overwrite its work blindly;
   - during independent review, do not edit unless explicitly asked;
   - preserve a clear handoff between phases.

   When handing work to another agent, summarize:

   - current task;
   - completed phase;
   - frozen decisions;
   - resolved decisions;
   - remaining open decisions;
   - implementation status;
   - verification status;
   - accepted findings;
   - exact next authorized action.

   ---

   ## 16. General repository hygiene

   Do not:

   - use `git add .`;
   - stage unrelated files;
   - commit raw data, processed local data, credentials, tokens, local manifests,
   cache files, or run artifacts that are intentionally ignored;
   - rewrite immutable historical evidence;
   - delete failed-run evidence merely because the run failed;
   - change source-of-truth documents to match an implementation mistake.

   Before reporting repository completion, inspect the diff and working-tree status.