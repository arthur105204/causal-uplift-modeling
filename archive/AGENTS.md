# Repository instructions

Operating contract for agents working in this repository. Durable rules only;
formulas, estimator configuration, and full ADR content live in `docs/` and are
referenced, not duplicated, here.

## 1. Authority order

When sources conflict, use this precedence:

1. `docs/decision_register.csv` (owner-approved decisions).
2. Frozen contracts/specs in `docs/01`-`docs/07` and ACCEPTED ADRs in `docs/adr/`.
3. Accepted task-specific empirical evidence (`outputs/runs/<run_id>/`).
4. GitHub Issue wording (execution tasks; MASTER #20 is the current plan).
5. Existing implementation.

Do not silently override a higher-authority source. If a GitHub Issue conflicts
with a higher-authority source, stop and report the conflict before making a
methodological or statistical change. See `docs/index.md` for the full map and
change-control rule.

## 2. Frozen methodological foundations

Do not reopen or silently modify: `X = f0...f11` (canonical order); `T =
treatment` (assignment/ITT, never exposure); primary `Y = conversion`, `visit`
as secondary; `exposure` as audit-only, excluded from `X`; assignment/ITT CATE
estimand; retain-all primary row policy (D07); frozen 70/15/15 split with joint
`(T,Y)` stratification; held-out isolation until T17; the T-Learner formula
(`mu1_hat - mu0_hat`); the X-Learner pseudo-outcome/cross-fitting logic; frozen
uplift metric conventions (`docs/07`); the 500-draw paired arm-stratified
bootstrap (D29, unaffected by D33); one-shot held-out evaluation. Causal Forest
remains a mandatory main comparator (D15). Per D33, the 2,000-draw
randomization-calibration protocol (T03-C) is no longer a mandatory
precondition for T16/pre-test freeze -- it is an optional/P1 internal
diagnostic. ED-03 (continuous SMD) and ED-03b (categorical proportions/TVD)
are required *descriptive* diagnostics but are explicitly **non-blocking**:
they are not P0 causal-validity or correctness gates, and an unusual value may
trigger investigation but must not automatically block modeling, freeze, or
held-out evaluation. Only genuine arm/support requirements (ED-05) remain P0
gates. Randomization evidence comes primarily from the documented experimental
design, not from balance testing (D33, `docs/03`). Robustness seeds `123`/
`2026` (D29, AMENDED_BY_D33) are supporting, non-blocking evidence, never a
precondition for an estimator's shortlist entry or acceptance; D31's Causal
Forest one-shot seed policy is unaffected.

Predicted uplift is not true ITE. `f0`-`f11` are anonymized with no known
business meaning. Balance diagnostics do not prove randomization.

## 3. Kaggle multi-session execution model

Kaggle is the primary heavy-compute environment. A full pipeline does not have
to fit inside one notebook session — expensive stages communicate through
explicit, versioned, immutable artifacts under `outputs/runs/<run_id>/`, and a
downstream stage must be reproducible from its declared upstream outputs alone.
Local execution is for editing, unit tests, synthetic/small verification, and
review, not primary heavy compute.

## 4. Public vs. internal notebooks

The public reader-facing story is exactly `kaggle/01_data_understanding.ipynb`
through `kaggle/04_final_evaluation.ipynb`. GitHub Issues are execution tasks
and are not required to map 1:1 to these notebooks — MASTER #20 carries the
current task-to-notebook mapping. Heavy or held-out-sensitive computation may
live in `notebooks/internal/`; it is not reader-facing. `notebooks/legacy/`
holds pre-reset notebooks as historical evidence, inherited and not re-derived.

Public notebooks show scientific reasoning, model logic, results,
interpretation, and limitations. They abstract engineering plumbing — path
resolution, manifest traversal, hashing internals, artifact registries,
serialization machinery, environment capture — rather than exposing it.

## 5. Feature-semantics rule (D32)

`f0`, `f2`, `f7`, `f10` are continuous. `f1`, `f3`, `f4`, `f5`, `f6`, `f8`,
`f9`, `f11` are categorical. Physical `float64` storage does not imply
continuous or ordinal semantics — see D32 in the decision register and
`docs/02_data_contract.md`. Do not infer categorical/continuous status from
cardinality. Do not compute SMD, means, or variances on categorical token
magnitudes. LightGBM requires a categorical-aware representation for the
categorical group. Causal Forest has no native LightGBM-equivalent categorical
support; do not invent an encoding for it — an unresolved representation is an
explicit blocker (see the CF implementation ADR), not something to guess.

## 6. Owner decision boundary

Agents may autonomously make engineering decisions that do not alter the
scientific experiment, estimand, statistical procedure, estimator semantics,
selection rule, or held-out protocol.

For consequential methodological/statistical decisions, an agent must:

1. identify the decision;
2. provide only genuinely viable options;
3. recommend one with concise trade-offs;
4. explain INPUT → OPERATION → OUTPUT → FAILURE MODE;
5. obtain owner approval before implementation.

Correctness fixes that merely restore an already-approved invariant (e.g.
preventing leakage or making learned preprocessing fold-local) do not require a
new methodology decision, but must be reported and verified.

Routine reruns under an already-approved corrected contract do not require
separate owner approval unless a gate fails or a methodology/config change
becomes necessary.

Before adding a new mandatory diagnostic, gate, artifact, calibration,
sensitivity, or infrastructure component, state which scientific conclusion
would become invalid or materially less defensible without it. If no concrete
answer exists, it must not become P0 (D33).

## 7. Deadline-mode lifecycle

Default lifecycle: DEPENDENCY READY → UNDERSTAND/TUTOR → RESOLVE REAL
DECISIONS → DECISION-EVIDENCE when genuinely required → CODE PLAN → OWNER
UNDERSTANDING GATE → IMPLEMENT → VERIFY → CLEAN RUN → INTERPRET → REVIEW/
FALSIFY → TEACH-BACK → ACCEPT → COMMIT/CLOSE as a separate explicit action. The
user controls phase transitions; do not auto-advance. In deadline mode,
conceptual understanding, CODE PLAN, and independent review remain required;
prioritize UNDERSTAND CORE LOGIC → CODE PLAN → IMPLEMENT → VERIFY → CODE MAP →
REVIEW → TEACH-BACK over prolonged pre-implementation syntax exercises.

## 8. CODE PLAN requirement

Before non-trivial implementation, produce or verify a blueprint identifying:
task input/output, main data/model flow, 5-10 major operations, important
functions/APIs, statistical/causal assumptions, leakage/alignment/support
failure modes, verification checks, and the notebook/`src/`/tests/artifact
split. Do not produce production implementation during `[CODE PLAN]`.

## 9. Notebook good practice

The designated notebook is the primary human-readable artifact: it must expose
the research question, core data/model flow, calculations, verification,
observations, interpretation, and limitations — not become a thin wrapper
around opaque helpers. `src/` holds reusable logic when reuse or correctness
justifies it; `tests/` holds regression checks; `configs/` holds reproducible
configuration; `outputs/runs/<run_id>/` holds immutable run evidence,
proportional to consequential experiments (training, persisted predictions,
comparison, bootstrap, frozen/held-out evaluation) — not routine EDA or
one-off exploration.

## 10. Held-out isolation

Before T17: do not inspect held-out performance, use held-out outcomes for
redesign, tune anything using held-out results, or generate unofficial
held-out diagnostics. T17 is the first and only authorized held-out
evaluation, under the T16 freeze. If an operation would access held-out
evidence before T17, stop.

## 11. Implementation boundaries

Implement only the current task's scope; keep diffs focused; do not silently
change methodology or perform unrelated refactors; do not start successor
work. Preserve deterministic row alignment and run-scoped evidence. Add only
the smallest justified reusable helpers/tests. Do not modify frozen project
documents merely to make implementation easier.

## 12. Verification / clean-run rules

Successful execution is not verification. Check task-relevant invariants:
input identity/checksum, row count, schema/dtypes, feature roles (including
D32 continuous/categorical split), `_source_row_id` alignment,
treatment/outcome encoding, denominators, arm support, sign/orientation,
leakage, determinism, artifact lineage. `notebook exists` ≠ `notebook parses`
≠ `tests pass` ≠ `clean Run All succeeds`. Where applicable, final
verification requires a fresh-kernel Run All with zero uncaught errors
reconciled to expected artifacts.

## 13. Review / falsification

During `[REVIEW]`, do not edit first — attempt to falsify the implementation
and interpretation, and record findings before fixes. Classify findings as
BLOCKER, MAJOR, MINOR, ACCEPTED LIMITATION, or NOT A BUG where useful. Only
fix findings accepted for remediation.

## 14. CODE MAP / teach-back

When implementation was accelerated, produce a focused CODE MAP covering the
10-15 blocks that explain most of the task logic, each as INPUT → OPERATION →
OUTPUT → WHY → FAILURE MODE. For statistical/modeling stages, also cover the
main formula, leakage risk, and verification. The owner is not required to
memorize generic engineering syntax.

## 15. Multi-agent coordination

Only one agent should act as writer on a given working tree at a time. Keep
parallel work isolated to its own branch/worktree. A reviewing/planning agent
reports findings and does not edit unless explicitly asked. When handing off,
summarize: current task, completed phase, frozen decisions, resolved/open
decisions, implementation and verification status, accepted findings, and the
exact next authorized action.

## 16. Repository hygiene

Do not `git add .` or stage unrelated files. Do not commit raw/processed data,
credentials, tokens, local manifests, cache files, or ignored run artifacts.
Do not rewrite immutable historical evidence or delete failed-run evidence
merely because the run failed. Do not change a source-of-truth document to
match an implementation mistake — fix the implementation, or raise the
decision. Before reporting completion, inspect the diff and working-tree
status. Commit, push, Issue closure, and starting the next task are separate
explicit actions requiring authorization.
