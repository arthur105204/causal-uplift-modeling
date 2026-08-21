> **Learning note only — not an authoritative project contract.**
> This file records what the owner still needs to personally understand about
> Claude-assisted implementation work. It never outranks `docs/decision_register.csv`,
> the numbered contracts in `docs/`, accepted ADRs, configs, or accepted scientific
> evidence. If anything here conflicts with those sources, the higher-authority
> source wins and this file should be corrected.

# Scope and cutoff

- **Rebuild boundary commit:** `c23dc7a` — "chore: reconcile governance docs to
  the Kaggle-first architecture" (2026-08-18 11:40:25 +0700).
- **Why this is the correct cutoff:** it is the first commit of a same-morning,
  five-commit sequence (`c23dc7a` → `212b706` → `2e1feae` → `28758fe` →
  `153f394`, all 2026-08-18, 11:40–12:23) that (a) replaced `REPRODUCIBILITY.md`
  with the current `AGENTS.md`/`CLAUDE.md` governance pair, (b) established the
  `kaggle/` notebook series, (c) moved the pre-reset notebooks into
  `notebooks/legacy/` (the commit message literally says "pre-reset
  notebooks"), and (d) simplified the notebook plan to the current 4-notebook
  story. Every commit before it (`f1a1c30` … `f0b8da5`, 2026-08-10 to
  2026-08-13) belongs to the prior architecture and is INHERITED, not
  post-reset debt.
- **Current `HEAD` / `origin/main`:** `810a3f11c9cfda26ef1c859493a7bbb52918e222`
  ("feat: complete T08 LightGBM T-Learner").
- **Latest implemented/accepted task:** T08 (T-Learner), accepted, committed,
  pushed.
- **Next task not yet incurred:** T09 (X-Learner) — not started; no CODE PLAN,
  no implementation, no commit exists for it as of this log.
- **Held-out state:** untouched. No task in this project has read held-out
  data; T17 is the first authorized held-out access and has not occurred.

---

# How to close a learning debt

A debt may be marked `CLOSED` only when the owner, **without reading Claude's
old chat report**, can do all five:

1. Explain the task's `INPUT → OPERATION → OUTPUT` flow out loud or in writing.
2. Explain *why* the design exists (what decision/contract/risk it responds to).
3. Name at least two concrete failure/leakage risks for that task, unprompted.
4. Have actually read the main implementation file(s) listed under
   *Code/files nên đọc*.
5. Answer the *Teach-back gates* questions correctly.

Closing a debt is a statement about the **owner's** understanding, not about
whether the code passed tests or was accepted into `main`. A task can be
`Status: OPEN` even though it is fully implemented, reviewed, and merged.

---

# Priority queue

Study order follows **conceptual dependency**, not commit chronology. Metric
correctness must be understood before any estimator that is scored by it;
data/split/preprocessing must be understood before anything that consumes
`X`/`T`/`Y`; governance mechanisms (D30, erratum policy) are useful context but
sit lowest-priority since they don't change scientific conclusions.

1. **LD-01 — Pre-split causal integrity audit (T03-A/T03-B)** — everything
   downstream assumes this population is clean and the split-identity
   guarantees hold.
2. **LD-02 — Frozen split (T05)** — every later task's train/validation/held-out
   partition depends on this being understood, especially the held-out seal.
3. **LD-03 — Preprocessing contract (T04)** — small but foundational; explains
   why `X` is exactly `f0`-`f11` and why missing values are never imputed.
4. **LD-04 — Uplift/Qini metrics (T06)** — must be understood before *any*
   estimator, because every estimator (T07, T08, and future T09-T11) is scored
   through this one interface and nothing else.
5. **LD-07 — Random reference + Response baseline (T07)** — the first thing
   actually scored by T06; teaches the "response ≠ uplift" distinction that
   recurs for every later estimator.
6. **LD-08 — T-Learner (T08)** — the first genuine causal estimator; depends on
   T06 (metrics) and T07 (shared LightGBM fitting primitive, comparison
   pattern) directly.
7. **LD-00 — Governance rebuild** / **LD-05 — D30 scale-gating** /
   **LD-06 — Audit-only erratum policy** — read once, referenced as needed;
   these don't change any scientific number and can be studied last or
   in parallel.

**Why this order is efficient:** LD-01/02/03 are pure prerequisites nothing
else can be checked without; LD-04 is a hard gate because both LD-07 and LD-08
are literally *defined* in terms of it (you cannot understand "T-Learner did
not rank uplift well" without first understanding what `qini_above_random`
means); LD-07 before LD-08 because T08 explicitly reuses T07's fitting module,
comparison-table pattern, and SMOKE/FULL scale-gating precedent — reading T08
first would mean constantly back-referencing undefined T07 concepts. The three
governance LDs are deliberately last: they matter for *process* trustworthiness
(can you trust what's in `outputs/runs/`?) but contain zero causal/statistical
content and don't block understanding any estimator.

---

# Minimum owner checkpoints

Derived from the current project architecture (`docs/05_methodology_scope.md`,
MASTER Issue #20) — what must be true *before* starting to study each future
task:

- **Before X-Learner (T09):** closed LD-04 (T06 metrics), LD-07/LD-08 (you must
  be able to explain why X-Learner's cross-fitting requirement exists and how
  it differs from T-Learner's *lack* of a cross-fitting requirement —
  docs/05's Cross-fitting policy explicitly says cross-fitting is required for
  X-Learner/DR-Learner and *not* for Response/T-Learner; if you can't state
  why, you're not ready).
- **Before Causal Forest (T10/T11):** closed LD-08, plus understanding of
  honesty/sample-splitting as a *distinct* concept from cross-fitting (they are
  not the same mechanism, per `docs/adr/ADR-CF-implementation.md`).
- **Before uncertainty (T15, 500-draw bootstrap):** closed all estimator LDs
  through whichever is current, plus understanding why a *paired,
  arm-stratified* bootstrap is required instead of an independent one per
  model (D29).
- **Before the pre-test freeze (T16) / held-out release (T17):** every LD in
  this file must be `CLOSED`, not just `OPEN`-and-implemented. T17 is
  one-shot; there is no "come back and re-learn this later."

---

# Progress tracker

| Debt ID | Topic | Priority | Status | Suggested time |
|---|---|---|---|---|
| LD-00 | Kaggle-first governance rebuild & notebook restructure | P2 | OPEN | 30 min |
| LD-01 | Pre-split causal integrity audit (T03-A/T03-B) | P0 | OPEN | 90 min |
| LD-02 | Frozen train/validation/held-out split (T05) | P0 | OPEN | 45 min |
| LD-03 | Preprocessing contract (T04) | P1 | OPEN | 20 min |
| LD-04 | Uplift/Qini metrics (T06) | P0 | OPEN | 120 min |
| LD-05 | D23→D30 scale-gating governance refactor | P2 | OPEN | 30 min |
| LD-06 | Audit-only erratum correction policy | P2 | OPEN | 20 min |
| LD-07 | Random reference + Response LightGBM baseline (T07) | P0 | OPEN | 90 min |
| LD-08 | T-Learner LightGBM (T08) | P0 | OPEN | 90 min |

**Total estimated study time (post-reset debt only): ~9 hours (535 minutes).**

Inherited and not-yet-incurred items (not counted in the total above):

| Item | Class | Note |
|---|---|---|
| Sprint-1 causal/data contracts freeze | INHERITED | `f1a1c30`, pre-boundary |
| T01 data engineering pipeline | INHERITED | `10dee33` + earlier, pre-boundary |
| T02 exploratory data analysis | INHERITED | `ccce06a`, pre-boundary |
| T03-C final 2,000-draw calibration execution | NEXT (partially implemented) | mechanism/code landed in `0d7c97b`, but `execution_state: DEFERRED_T03_C` in `configs/t03_audit.json` — the production run has not executed |
| T09 X-Learner | NEXT | not started; no CODE PLAN exists yet |
| T10/T11 Causal Forest | NEXT | not started |
| T12-T18 | NEXT | not started |

---

# Update rule after each Claude task

```
## LD-XX — <Task>

- Status:
- Priority:
- Task / Issue:
- Commit(s):
- Authoritative run(s):
- Dependencies:
- AI work đã làm:
- Core flow phải tự giải thích được:
- Cần hiểu bắt buộc:
- Code/files nên đọc:
- Empirical result cần diễn giải:
- Failure/leakage risks:
- Teach-back gates:
- Target study time:
- Closed on:
```

---

# Current baseline for next task

- **HEAD / origin/main:** `810a3f11c9cfda26ef1c859493a7bbb52918e222` (identical,
  confirmed pushed).
- **Latest accepted task:** T08 (T-Learner) — FULL executed, comparative
  `model_summary.csv` label erratum applied, committed, pushed.
- **Held-out state:** untouched throughout the project to date.
- **Next not-yet-started task:** T09 (X-Learner), per MASTER Issue #20 /
  `docs/05_methodology_scope.md`. No implementation exists.

---
---

# POST-RESET LEARNING DEBT

---

## LD-00 — Kaggle-first governance rebuild & notebook restructure

- **Status:** OPEN
- **Priority:** P2
- **Task / Issue:** `.claude/PROJECT_REBUILD_PROMPT.md`,
  `.claude/restructure_kaggle_project.md` (internal orchestration prompts, not
  numbered GitHub Issues)
- **Commit(s):** `c23dc7a`, `212b706`, `2e1feae`, `28758fe`, `153f394`
- **Authoritative run(s):** N/A — documentation/architecture task, no
  `outputs/runs/` evidence
- **Dependencies:** none (this *is* the boundary)

### AI work đã làm
Claude replaced the prior `REPRODUCIBILITY.md` governance document with the
current `AGENTS.md` (repository-wide operating contract) and `CLAUDE.md`
(operational summary), reconciling both to a "Kaggle-first" execution model.
It then built the `kaggle/` notebook series from scratch: first an 8-notebook
draft (`00_project_overview.ipynb`, `01_data_feasibility.ipynb`,
`02_eda_split_preprocessing.ipynb`), then — in the very next commits —
collapsed that into the current 4-notebook plan
(`01_data_understanding.ipynb` → `02_uplift_modeling.ipynb` →
`03_validation_and_uncertainty.ipynb` → `04_final_evaluation.ipynb`, the last
two not yet created as of T08). The pre-reset notebooks were moved intact to
`notebooks/legacy/` (never edited since) and a new `notebooks/internal/`
convention was established for heavy/held-out-sensitive compute.

### Core flow phải tự giải thích được
```
INPUT: prior REPRODUCIBILITY.md + 8-notebook draft + pre-reset notebooks/
  ↓
OPERATION 1: write AGENTS.md (operating contract) + CLAUDE.md (summary)
  ↓
OPERATION 2: draft kaggle/00-02 (8-notebook plan)
  ↓
OPERATION 3: move pre-reset notebooks → notebooks/legacy/ (frozen, historical)
  ↓
OPERATION 4: collapse to the 4-notebook plan; kaggle/01_data_understanding.ipynb
             absorbs S01, T01, T02, T03-A, T05, T04
  ↓
OUTPUT: current kaggle/ + notebooks/{legacy,internal}/ + AGENTS.md/CLAUDE.md
```
Not a statistical task — no equations.

### Cần hiểu bắt buộc
- **Why `notebooks/legacy/` is never edited going forward**: it is retained as
  historical evidence of accepted pre-reset results, not re-derived. Editing it
  would silently rewrite what was actually accepted.
- **Why `notebooks/internal/` exists as a separate category from `kaggle/`**:
  heavy or held-out-sensitive compute (audit calibration, frozen split
  construction) needs runtime isolation/repeatability the public narrative
  notebook shouldn't be burdened with — but this is a judgment call per task,
  never automatic just because a task has a number.
- **Why GitHub Issue task IDs (`T05`, `HG-01`, …) never appear in
  reader-facing notebook headings**: the public notebook is a first-time
  presentation of the current study, not a project-history narrative.

### Code/files nên đọc
1. `CLAUDE.md` (operational summary, read first every session)
2. `AGENTS.md` (full operating contract, especially §1 source precedence, §6
   notebook-first policy)
3. `docs/index.md` (documentation map and authority hierarchy)
4. `kaggle/01_data_understanding.ipynb` (the one fully-built product of this
   restructure)

### Empirical result cần diễn giải
N/A — implementation/governance task.

### Failure/leakage risks
1. Silently rewriting `notebooks/legacy/`'s accepted historical results instead
   of treating them as frozen evidence.
2. Exposing internal task codes (`T05`, `HG-01`) in reader-facing prose,
   turning the public notebook into a project-history document instead of a
   science document.
3. Routing heavy/held-out-sensitive compute into the public `kaggle/` notebook
   "because it's easier," defeating the isolation `notebooks/internal/` exists
   for.
4. Treating `AGENTS.md`/`CLAUDE.md` as higher authority than the decision
   register or numbered contracts — they are operational guidance only.

### Teach-back gates
1. What does "Kaggle is the primary execution environment" actually constrain
   about where code is allowed to live?
2. Why does the public notebook series not mirror the GitHub Issue/task
   structure 1:1?
3. What's the difference in *purpose* between `notebooks/legacy/` and
   `notebooks/internal/`?
4. If AGENTS.md said something that contradicted `docs/decision_register.csv`,
   which wins, and why?

### Target study time
90 min → **30 min** (small, low-conceptual-density; corrected to match
tracker)

- **Closed on:** —

---

## LD-01 — Pre-split causal integrity audit (T03-A / T03-B)

- **Status:** OPEN
- **Priority:** P0
- **Task / Issue:** T03 (GitHub Issue #4)
- **Commit(s):** `0d7c97b` — "feat: complete pre-split causal integrity audit
  and development diagnostics"
- **Authoritative run(s):** T03-A → `t03a_audit_20260818T072125Z_409014`;
  T03-B → `t03b_devint_20260818T073803Z_243755` (both per
  `configs/t03_audit.json`'s `lifecycle_state_history`)
- **Dependencies:** T01 (`t01_production_20260812T091631Z_224672`), T02
  (`t02_eda_20260813T094750Z_546902`) — both INHERITED, pre-boundary

### AI work đã làm
Claude implemented `src/audit.py` (1,420 lines) — by far the largest single
module in the project — covering: duplicate-profile auditing (DP-01..DP-07 per
`docs/04_duplicate_profile_protocol.md`), cross-split profile overlap,
precision reconciliation (float64 vs float32 sensitivity), binary-completeness
assertions, source-row identity validation, and the **full mechanism** for
T03-C's randomization calibration (`conditional_permute_treatment`,
`build_treatment_stratified_folds`, `cross_fitted_treatment_predictability`,
order-statistic/Monte-Carlo interval functions, evidence-record validation) —
even though T03-C's actual 2,000-draw production run has **not** executed
(`execution_state: DEFERRED_T03_C` in `configs/t03_audit.json`; only
`UNIT_FIXTURE`/`SMOKE_ONLY` modes are currently allowed). Two notebooks were
built: `notebooks/internal/t03_data_integrity_audit.ipynb` (T03-A, pre-split)
and `t03b_development_integrity.ipynb` (T03-B, post-split identity checks).
`tests/test_audit.py` (46 tests) covers this module.

### Core flow phải tự giải thích được
```
INPUT: validated_unsplit_released_rows (from T01/T02, manifest-selected Parquet)
  ↓
OPERATION 1 (T03-A): duplicate-profile audit DP-01..DP-07
      (identity dupes, full-row dupes, feature-only dupes, feature+T dupes, ...)
  ↓
OPERATION 2 (T03-A): precision reconciliation (float64 primary vs float32 sensitivity)
  ↓
OPERATION 3 (T03-A): balance diagnostics
      SMD = (mean_treated - mean_control) / sqrt((var_treated_ddof1 + var_control_ddof1)/2)
  ↓
OPERATION 4 (T03-B, post-split): source-row identity disjointness across
      train/validation (held-out sealed: DP-06 = SEALED_DEFERRED_BY_TEST_ISOLATION)
  ↓
OUTPUT: T03_PRE_SPLIT_COMPLETE evidence (authorizes T05) →
        T03_DEVELOPMENT_INTEGRITY_COMPLETE evidence (authorizes T04)
[T03-C mechanism implemented but its production run remains DEFERRED]
```

### Cần hiểu bắt buộc
- **Why the SMD formula uses `ddof=1` equal-arm variance weighting**: a
  documented, frozen convention (`docs/03_assumption_and_audit_spec.md`) — not
  an arbitrary choice, and changing it would silently redefine what "balanced"
  means for every downstream audit claim.
- **Why balance diagnostics never "prove" randomization**: AGENTS.md §13
  explicitly forbids this claim — SMD/balance is consistent-with, not
  proof-of, a valid RCT design.
- **Why DP-06 (train/validation vs held-out overlap) is `SEALED_DEFERRED_BY_TEST_ISOLATION`
  rather than computed now**: computing it would require reading held-out row
  identities before T17 — forbidden regardless of how harmless the *count*
  alone might seem.
- **Why T03-C exists as a *separate*, non-blocking task from T03-A/B**: it's a
  randomization-assumption calibration (permute treatment labels, refit a
  classifier, compare observed treatment-predictability to a null
  distribution) — a fundamentally different question ("is treatment
  assignment actually independent of `X`?") from T03-A/B's row-identity and
  duplicate-profile checks.

### Code/files nên đọc
1. `src/audit.py` — read in this order: `duplicate_audit`/`duplicate_profile_summary`
   (T03-A core), `balance_diagnostics`/`smd_feature_record` (T03-A core),
   `cross_split_profile_overlap` (T03-B core), `conditional_permute_treatment`
   through `monte_carlo_action_stability` (T03-C mechanism, not yet executed
   in production)
2. `tests/test_audit.py` (46 tests — read the ones for `smd_feature_record`
   and `conditional_permute_treatment` first)
3. `configs/t03_audit.json` (decision record + `lifecycle_state_history` +
   the full `randomization_calibration` block)
4. `docs/03_assumption_and_audit_spec.md` (the authoritative HG-01..HG-07 gate
   definitions this module implements)
5. `notebooks/internal/t03_data_integrity_audit.ipynb`,
   `t03b_development_integrity.ipynb`

### Empirical result cần diễn giải
**Observed:** T03-A and T03-B both completed with "zero infractions" per
`configs/t03_audit.json`'s `checklist_verified` notes — all HARD_GATE checks
(HG-01 through HG-07) passed on the real released population.
**Can conclude:** the released population, as loaded, passes the predeclared
integrity gates this project requires before any modeling work begins.
**Cannot conclude:** that randomization assignment is proven valid (balance
passing is consistent-with, not proof-of); cannot conclude anything about
T03-C's calibration result, because it has not run.

### Failure/leakage risks
1. Computing DP-06 (train/validation-vs-held-out overlap) before T17 — would
   be a direct held-out isolation violation.
2. Treating passing balance/SMD diagnostics as proof the RCT design is valid.
3. Silently including `exposure` in any audit computation meant to inform
   modeling decisions (it's audit-only, must never leak into `X` or
   eligibility).
4. Using T03-C's calibration mechanism in `FULL_MAPPING` mode before its
   production run is authorized — `full_mapping_allowed_modes` is currently
   restricted to `UNIT_FIXTURE`/`SMOKE_ONLY` for exactly this reason.
5. Confusing T03-C's `CONDITIONAL_PERMUTATION_APPROXIMATION` (treatment-label
   permutation for randomization calibration) with T06/T07's random-ranking
   score generation (`seeded_random_scores`) — they permute/generate
   completely different things for completely different questions.

### Teach-back gates
1. What does DP-04 check for that DP-03 doesn't, and why does that distinction
   matter for detecting a *treatment-coding* problem specifically?
2. Why is "the SMD is small" not the same claim as "randomization worked"?
3. What would have to be true about the held-out partition before DP-06 could
   ever be computed, and why isn't that true yet?
4. What's the actual causal question T03-C's calibration is trying to answer,
   and how is that different from what T03-A/B already checked?
5. Why does `full_mapping_allowed_modes` exist as an explicit allow-list
   instead of the code just running whatever mode is requested?

### Target study time
**90 min**

- **Closed on:** —

---

## LD-02 — Frozen train/validation/held-out split (T05)

- **Status:** OPEN
- **Priority:** P0
- **Task / Issue:** T05 (GitHub Issue #6)
- **Commit(s):** `85a9ae3` — "feat: implement and seal the frozen
  train/validation/held-out split"
- **Authoritative run(s):** `t05_split_20260818T073132Z_534290`
  (`configs/t05_split.json`'s `lifecycle_state_evidence`)
- **Dependencies:** LD-01 (T03-A authorizes T05)

### AI work đã làm
Claude implemented `src/split.py` (229 lines): a one-time seeded, jointly
`(T,Y)`-stratified 70/15/15 split (`assign_split`), disjointness/full-accounting
verification (`verify_disjoint_and_complete`), a deterministic-regeneration
check (`verify_deterministic_regeneration`), non-sealed `(T,Y)` support
summaries for train/validation only (`support_summary`, explicitly refuses
`held_out`), an *opaque* held-out support gate that returns only PASS/FAIL with
no count exposed (`held_out_support_gate`), and the `SplitDataset` dataclass
whose `held_out_ids()` method fails closed structurally — it requires a
release-marker file that literally does not exist until T17, not a flag that
could be flipped by accident. `tests/test_split.py` (17 tests) exercises all of
this, including the fail-closed held-out guard specifically.

### Core flow phải tự giải thích được
```
INPUT: validated_unsplit_released_rows, seed=42
  ↓
OPERATION 1: joint strata key = treatment.astype(str) + "_" + conversion.astype(str)
  ↓
OPERATION 2: two-stage sklearn train_test_split
      (a) 70% train vs 30% remainder, stratified on the joint key
      (b) remainder split 50/50 into validation/held_out (=15%/15% of total),
          stratified on the joint key
  ↓
OPERATION 3: verify pairwise disjointness + union == full expected population
  ↓
OPERATION 4: hash the (source_row_id -> split) membership deterministically
      (order-independent, sha256)
  ↓
OPERATION 5: regenerate from scratch, confirm hash matches (proves the split
      is a pure function of (population, seed), not incidental randomness)
  ↓
OUTPUT: split_membership.csv (train/validation/held_out labels for every row)
        + membership_sha256 (frozen, referenced by every downstream task)
```

### Cần hiểu bắt buộc
- **Why the split is stratified on the *joint* `(T,Y)` key, not `T` and `Y`
  separately**: guarantees every partition preserves the same
  arm-by-outcome cell proportions simultaneously — stratifying on `T` alone
  wouldn't guarantee `Y`'s distribution is preserved within each arm, which
  matters for metric estimability (e.g., no partition accidentally starving a
  rare cell like control-arm converters).
- **Why `held_out_ids()`'s guard is a *missing file*, not a boolean flag**: a
  flag can be flipped by a typo or a copy-pasted cell; a file that genuinely
  doesn't exist until an authorized T17 process creates it cannot be
  accidentally satisfied.
- **Why `support_summary()` explicitly raises on `split_label='held_out'`**:
  even a row *count* by `(T,Y)` cell for held-out would be an "unofficial
  held-out diagnostic," forbidden by AGENTS.md §8 regardless of how
  innocuous a count seems.
- **Why the membership hash must be order-independent**: two functionally
  identical splits produced by different row-iteration orders must hash
  identically, or the "deterministic regeneration" proof would be
  meaningless (comparing hashes that differ only by incidental row order).

### Code/files nên đọc
1. `src/split.py` — read `assign_split`, `verify_disjoint_and_complete`, and
   `SplitDataset.held_out_ids()` first; those three are the entire
   safety-critical surface
2. `tests/test_split.py` — especially
   `test_held_out_ids_fail_closed_without_release_marker` and
   `test_deterministic_regeneration_reproduces_identical_hash`
3. `configs/t05_split.json` (frozen split parameters + authorizing run)
4. `notebooks/internal/t05_frozen_split.ipynb`

### Empirical result cần diễn giải
**Observed:** `train=9,785,714`, `validation=2,096,938`, `held_out=2,096,940`
rows (from `configs/t05_split.json`'s `row_counts` and the run evidence),
summing to the full released population with zero overlap.
**Can conclude:** the frozen partition is complete, disjoint, and
deterministically reproducible from `(population, seed=42)`.
**Cannot conclude:** anything about held-out `(T,Y)` support or outcome rates —
those remain sealed by design until T17.

### Failure/leakage risks
1. Re-running the split with a different seed "because a result looked
   unfavorable" — explicitly prohibited (docs/06: "No resplit is allowed
   because validation results are unfavorable").
2. Any code path calling `held_out_ids()` before the T17 release marker
   exists (structurally should fail, but a bypass — e.g., reading
   `split_membership.csv` directly instead of going through `SplitDataset` —
   would defeat the guard; T07's own SMOKE isolation defect, later corrected,
   was exactly this mistake made once and then fixed).
3. Row renumbering before or during split assignment — `_source_row_id` must
   stay the original zero-based ordinal throughout.
4. Silently changing the stratification key (e.g., stratifying on `T` only)
   without an owner-approved decision change.

### Teach-back gates
1. Why does stratifying on the joint `(T,Y)` key matter more than
   stratifying on `T` alone?
2. What specifically would have to go wrong in the code for `held_out_ids()`
   to leak held-out identities before T17?
3. Why is "the membership hash is order-independent" a genuinely necessary
   property, not just a nice-to-have?
4. If you needed the held-out row count *right now*, what's the correct
   answer, and why?

### Target study time
**45 min**

- **Closed on:** —

---

## LD-03 — Preprocessing contract (T04)

- **Status:** OPEN
- **Priority:** P1
- **Task / Issue:** T04 (GitHub Issue #5)
- **Commit(s):** `1ae3f54` — "feat: finalize the T04 no-op preprocessing
  contract"
- **Authoritative run(s):** `t04_preprocessing_20260818T080330Z_043364`
  (`configs/t04_preprocessing.json`)
- **Dependencies:** LD-01 (T03-B), LD-02 (T05)

### AI work đã làm
Claude implemented `src/preprocessing.py` (82 lines) — deliberately the
smallest module in the project. `IdentityFeatureTransform` selects exactly
`f0`-`f11` in frozen order at `float64`, with `fit()` a documented no-op (no
learned state exists) kept only so a *future* learner-specific transform can
share the same fit-on-train-only calling convention without a breaking
change. Missing values pass through unimputed for LightGBM's native handling
— no imputation, no missingness-indicator feature, because T03-A's own
evidence showed zero missing values across the full released population, so
there is nothing to impute even in principle. `tests/test_preprocessing.py`
(11 tests) covers column/dtype/order/fit-boundary behavior.

### Core flow phải tự giải thích được
```
INPUT: train_frame (fit only), any frame with f0..f11 (transform)
  ↓
OPERATION 1 (fit, train rows only): assert f0..f11 present; mark fitted
  ↓
OPERATION 2 (transform, any partition): select exactly [f0,...,f11] in order,
      cast to float64; missing values (if any) pass through unimputed
  ↓
OUTPUT: X with frozen column order/dtype, identical whether the caller is
        development or (eventually) held-out data
```

### Cần hiểu bắt buộc
- **Why this is a no-op and not "preprocessing for tidiness"**: Issue #5
  explicitly prohibits adding scaling/imputation/encoding without a *concrete*
  requirement from evidence or a learner's API — and neither exists yet.
- **Why `fit()` exists at all if it does nothing**: enforces the
  fit-boundary calling convention (`fit(train_only)` then `transform(any)`)
  now, so a future estimator-specific transform can slot into the same
  contract without changing every caller's code shape.
- **Why missing values are preserved, not imputed**: LightGBM has native
  missing-value handling; imputing would be inventing information the data
  doesn't have, purely to satisfy a constraint (no missing values allowed)
  that no downstream learner actually has.

### Code/files nên đọc
1. `src/preprocessing.py` (the entire file — it's short)
2. `tests/test_preprocessing.py::test_fit_uses_train_rows_only_then_applies_unchanged_to_validation`
3. `configs/t04_preprocessing.json` (the `decision_record` block explaining
   *why* no-op was chosen)

### Empirical result cần diễn giải
N/A in the numeric sense — the only "result" is a decision record: zero
missing values across all 12 features on the full released population
(inherited from T03-A's ED-01 evidence), which is why no imputation branch
was built.

### Failure/leakage risks
1. Fitting on validation or held-out rows instead of train-only (the contract
   forbids it structurally, but a careless caller could still pass the wrong
   frame to `fit()`).
2. Silently reordering `f0`-`f11` (would break `assert_model_feature_contract`
   downstream and could silently corrupt every trained model's feature
   semantics without an obvious error).
3. Adding an imputation/scaling branch later "just in case" without a new
   piece of evidence or learner requirement to justify it — this repo
   explicitly treats that as scope creep.

### Teach-back gates
1. Why is a no-op transform still worth having a `fit()`/`transform()` API
   instead of just slicing the DataFrame inline everywhere it's needed?
2. What concrete piece of evidence licenses "preserve missing values, don't
   impute" as the frozen rule, rather than it being an assumption?
3. What would have to change for this module to stop being a no-op?

### Target study time
**20 min**

- **Closed on:** —

---

## LD-04 — Uplift/Qini metrics (T06)

- **Status:** OPEN
- **Priority:** P0
- **Task / Issue:** T06 (GitHub Issue #7)
- **Commit(s):** `f67d89e` — "feat: implement T06 uplift/Qini metrics
  (production + reference)"
- **Authoritative run(s):** `t06_metrics_20260818T091844Z_167215`
  (synthetic-fixture verification only — T06 never touches real data)
- **Dependencies:** none (T06 is pure metric machinery; its inputs are
  scores/labels supplied by whichever estimator calls it)

### AI work đã làm
Claude built the entire metric layer as **two independently-written
implementations** cross-checked for exact numeric agreement:
`src/metrics.py` (production, vectorized pandas/numpy) and
`src/metrics_reference.py` (reference, explicit row-by-row loop, intentionally
slower but hand-auditable), sharing only frozen constants, result dataclasses,
the exception type, and the purely mechanical 151-point curve-selection rule
(`src/metrics_common.py`) — never the actual Qini/uplift arithmetic, so a
formula bug in one cannot hide behind the other. Implements: `compute_ate`
(assigned-arm ATE with 95% CI), `evaluate_ranking` (Qini area, theoretical
random line, `qini_above_random`, uplift@K for K∈{10,20,30,50,100%}, decile
table), `response_diagnostics` (ROC-AUC/AP/log-loss, sklearn-backed,
single-implementation by design), `seeded_random_scores` +
`random_ranking_reference_distribution` (the frozen 200-draw random-ranking
reference, explicitly distinct from T03-C's treatment-permutation
calibration). 50 tests in `tests/test_metrics.py` cover orientation, ties,
sparse/zero-arm edge cases, and the reference↔production cross-check itself.
Includes a resolved conflict: Issue #7's literal wording said a missing arm at
top-K is `"UNSUPPORTED_METRIC"` (a string); `docs/07_metric_specification.md`
(higher authority) says the value is simply `NA`. Resolved in favor of
docs/07: the numeric field stays `None`, and a separate `top_k_status` field
(`TOP_K_STATUS_OK`/`TOP_K_STATUS_UNSUPPORTED`) records the reason without
overloading the numeric type.

### Core flow phải tự giải thích được
```
INPUT: scores (any ranking, causal or not), treatment, outcome, source_row_id
  ↓
OPERATION 1: sort by score descending, tie-break by source_row_id ascending
      (the one frozen ranking convention every method shares)
  ↓
OPERATION 2: cumulative sums per rank r: cum_n1(r), cum_n0(r), cum_y1(r), cum_y0(r)
  ↓
OPERATION 3: raw Qini gain (skip prefixes where cum_n0(r)=0):
      qini_gain(r) = cum_y1(r) - cum_y0(r) * cum_n1(r) / cum_n0(r)
  ↓
OPERATION 4: select <=151 curve points (round(linspace(0, L-1, 151)));
      trapezoidal integration -> qini_area
  ↓
OPERATION 5: theoretical_random_qini_area = Q_full / 2   (Q_full = qini_gain at 100% coverage)
      qini_above_random = qini_area - theoretical_random_qini_area   <- PRIMARY STATISTIC
  ↓
OPERATION 6: uplift@K, K in {10,20,30,50,100%}: m_k = min(N, max(1, ceil(k*N)))
      uplift@K = (y1/n1) - (y0/n0) at prefix m_k, or NA + top_k_status=UNSUPPORTED
      if either arm has zero rows in that prefix
  ↓
OUTPUT: RankingMetrics(qini_area, theoretical_random_qini_area, qini_above_random,
        uplift_at_k, top_k_status, decile_table, qini_curve)
```

### Cần hiểu bắt buộc
- **Why `qini_above_random`, not raw `qini_area`, is the primary statistic**:
  raw `qini_area` scales with the population's own conversion counts and is
  not comparable across populations/scales; subtracting the theoretical
  no-skill line normalizes for that.
- **Why the theoretical random line is `Q_full/2`, and why that's the *primary*
  random reference (not the 200-draw distribution)**: it's an exact,
  seed-independent expectation, so it introduces zero sampling noise into the
  comparison every method is judged against; the 200 draws are secondary
  empirical context about *how much a random ranking's realized value
  wobbles*, never the benchmark itself.
- **Why a missing arm at top-K must be `NA`, never fabricated**: docs/07's
  explicit rule, and the reason two review turns in this project spent real
  effort resolving Issue #7's conflicting literal wording in favor of the
  higher-authority contract — a good worked example of the source-precedence
  rule in AGENTS.md §1 actually mattering in practice.
- **Why ROC-AUC/AP/log-loss (`response_diagnostics`) are diagnostic-only and
  never a ranking claim (D27)**: they measure factual-outcome prediction
  quality, a completely different question from "does sorting by this score
  produce a good policy."
- **Why the reference/production split shares curve-point selection but not
  Qini arithmetic**: curve-point selection is index bookkeeping (mechanical),
  not causal math — sharing it can't hide a formula bug; sharing the formula
  itself would defeat the entire point of having two implementations.

### Code/files nên đọc
1. `src/metrics_reference.py` (read this *before* `metrics.py` — it's the
   loop-based, hand-auditable version, closest to the docs/07 formulas
   line-for-line)
2. `src/metrics.py` (the vectorized production version, same logic,
   different implementation strategy)
3. `src/metrics_common.py` (frozen constants + `RankingMetrics`/`AteResult`
   dataclasses + the shared curve-selection function)
4. `tests/test_metrics.py` — read `_good_fixture`/`_reversed_fixture`
   (hand-computable expected values) and
   `test_reference_and_production_agree_exactly` first
5. `docs/07_metric_specification.md` (the authoritative formula source)

### Empirical result cần diễn giải
N/A in the "real data" sense — T06 never touches real or held-out data; its
only verification evidence (`t06_metrics_20260818T091844Z_167215`) is a
synthetic-fixture cross-check confirming production and reference agree
exactly and the 200-draw distribution genuinely produces 200 draws. The
"empirical results" worth interpreting belong to T07/T08 below, which are the
first tasks to *call* this module on real data.

### Failure/leakage risks
1. Sign inversion: swapping which label means "treated" is **not** a simple
   sign flip of `qini_above_random` under arm imbalance — this project has an
   explicit regression test (`test_treatment_coding_swap_is_not_a_simple_sign_flip`)
   for exactly this failure mode.
2. Overloading the numeric `uplift_at_k` field with a status string instead of
   keeping it `float | None` — the exact defect this task's review process
   caught and fixed via the `top_k_status` field.
3. Confusing the 200-draw random-ranking reference with T03-C's treatment-label
   permutation calibration — different seeding purpose, different question,
   explicitly documented as non-interchangeable in code comments.
4. Reporting empirical PEHE against a "true" ITE on real data — forbidden
   (D28); there is no ground truth to compare against outside synthetic tests.
5. `_source_row_id` missing values reaching the `int64` cast uncontrolled
   instead of raising `MetricContractError` first — a real bug this project's
   review process found and fixed (checking `isnan` before casting).
6. Treating `response_diagnostics`'s AUC/AP/logloss as if they could select
   a causal winner between methods.

### Teach-back gates
1. Why does `qini_above_random`, not `qini_area`, let you compare two
   different validation populations fairly?
2. Concretely, what breaks if `uplift_at_k`'s missing-arm case is silently
   set to `0.0` instead of `None`?
3. Why can't you conclude "Response is a bad model" just from a negative
   `qini_above_random` if you haven't also checked its ROC-AUC?
4. What's the difference in *purpose* between the theoretical random line and
   the 200-draw empirical distribution, and why does the project treat one as
   primary and the other as secondary?
5. Why does having two independent implementations catch bugs that code
   review alone might miss?

### Target study time
**120 min**

- **Closed on:** —

---

## LD-05 — D23 → D30 scale-gating governance refactor

- **Status:** OPEN
- **Priority:** P2
- **Task / Issue:** owner-directed governance refactor (not a numbered T-task;
  affects D20, D22, D23→D30 in `docs/decision_register.csv`)
- **Commit(s):** `f527f0b` — "docs: replace fixed D23 scale ladder with D30
  risk-based gating"
- **Authoritative run(s):** N/A — documentation/decision-register change only
- **Dependencies:** LD-01 through LD-04 (motivated directly by T07 CODE PLAN
  work exposing that D23's fixed `50K→500K→2M→full` ladder didn't fit a
  two-model estimator's actual resource-risk profile)

### AI work đã làm
Claude superseded D23 (a fixed four-rung scale progression applied uniformly
to every task) with D30: a risk-based `SMOKE → [RESOURCE GATE(S) if
required] → FULL` policy where the number of resource gates (zero, one, or
more) and the SMOKE/RESOURCE workload sizes are declared per-task, justified
by that task's actual resource risk, and recorded before execution — never
chosen after seeing results. Updated `docs/06_experiment_protocol.md`,
`docs/05_methodology_scope.md`, five ADRs, `CLAUDE.md`, and
`docs/00_project_overview.md` to the new language, while explicitly
preserving D23's original row (all fields unchanged except status →
"Superseded by D30") and leaving every pre-existing task's historical
evidence (T01-T06) untouched.

### Core flow phải tự giải thích được
```
INPUT: D23's fixed 50K->500K->2M->full ladder (applied identically to every task)
  ↓
OPERATION 1: recognize a two-model task (T-Learner) doesn't fit a ladder sized
      for a single pooled model -- per-arm data availability differs sharply
  ↓
OPERATION 2: replace with SMOKE (mandatory, correctness/mechanism only) ->
      [0, 1, or N RESOURCE GATE(S), justified per task] -> FULL
  ↓
OPERATION 3: mark D23 Superseded (not deleted); add D30; update every doc/ADR
      that cited D23's fixed numbers
  ↓
OUTPUT: T07 uses SMOKE(50K)->FULL, 0 resource gates;
        T08 uses SMOKE(200K)->FULL, 0 resource gates, independently justified
```
Not a statistical task — no equations; this is a resource/process policy.

### Cần hiểu bắt buộc
- **Why the SMOKE workload size is task-specific, not inherited**: T08's SMOKE
  (200,000) is larger than T07's (50,000) because a two-arm estimator's
  *per-arm* rare-cell support (specifically the control-arm converter cell)
  is the binding constraint, and that constraint doesn't exist for a single
  pooled model — an inherited number would have silently under-provisioned
  T08's SMOKE.
- **Why "0 resource gates" is a *justified decision*, not an omission**: the
  fitting mechanism was already proven at full scale by a prior task (T07),
  so re-proving it via an intermediate resource gate would be redundant
  ceremony, not rigor — but this reasoning has to be written down, not
  assumed.
- **Why D23 is marked Superseded rather than deleted**: historical evidence
  (what T01-T06 actually ran under) must never be rewritten to match a later
  policy change.

### Code/files nên đọc
1. `docs/decision_register.csv` (D23's status field, D30's full row)
2. `docs/06_experiment_protocol.md` (the "Fixed defaults" table's Scale
   progression row)
3. `configs/t07_baselines.json` and `configs/t08_tlearner.json`'s
   `decision_record` blocks (see how each task *justifies* its own D30 path)

### Empirical result cần diễn giải
N/A — implementation/governance task.

### Failure/leakage risks
1. Choosing a SMOKE size or resource-gate count based on which choice
   produces a favorable *model* result — explicitly forbidden; the decision
   must be recorded before execution from population-support arithmetic
   alone.
2. Treating "0 resource gates" as a default assumption rather than a
   case-by-case justified decision for each new task.
3. Silently rewriting D23's historical decision-register row instead of
   marking it superseded.

### Teach-back gates
1. Why couldn't T08 safely reuse T07's exact SMOKE size?
2. What's the actual test for whether a task needs a RESOURCE gate at all?
3. Why does the project keep D23's row instead of deleting it now that D30
   exists?

### Target study time
**30 min**

- **Closed on:** —

---

## LD-06 — Audit-only erratum correction policy

- **Status:** OPEN
- **Priority:** P2
- **Task / Issue:** owner-directed governance mechanism (amends
  `docs/adr/ADR-experiment-artifacts.md`'s Immutability section)
- **Commit(s):** `6b1b6f0` — "docs: add audit-only erratum correction policy"
- **Authoritative run(s):** N/A for the policy itself; used in practice by
  `t07_audit_erratum_20260818T150917Z_995999`,
  `t08_smoke_audit_erratum_20260818T155806Z_642086`, and
  `t07_t08_random_label_erratum_20260818T162445Z_587615`
- **Dependencies:** LD-07 (the T07 SMOKE metadata defect that motivated this
  policy)

### AI work đã làm
Claude formalized a generic two-class correction mechanism for governed
`outputs/runs/` evidence: **Class A (scientific correction)** — anything
touching model/config/population/predictions/metrics requires full run
invalidation and a genuine replacement run; **Class B (audit-only erratum)** —
metadata/labeling-only defects may be corrected by a *new*, separately
governed erratum run that (1) proves every scientific artifact's hash is
unchanged, (2) proves the original run's file set and hashes are completely
untouched, (3) names exactly which fields are superseded with old/new values
and a reason, and (4) fails closed to Class A if any scientific hash doesn't
reconcile. The original run's files are never edited in place. Three real
errata were produced under this policy in T07/T08's own history (see
Dependencies), each independently reconciling every applicable scientific
artifact before writing anything.

### Core flow phải tự giải thích được
```
INPUT: a discovered defect in an already-COMPLETED run's evidence
  ↓
OPERATION 1: classify -- does it touch model/config/population/predictions/
      metrics (Class A) or only metadata/labels (Class B)? Ambiguity -> Class A.
  ↓
OPERATION 2 (Class B only): recompute SHA-256 for every scientific artifact in
      the affected run from the untouched original file; compare to the
      run's own recorded manifest hash
  ↓
OPERATION 3: if ANY hash mismatches -> refuse, escalate to Class A
  ↓
OPERATION 4: if all match -> write a NEW governed run (its own run_id) naming
      the affected run_id, exact field(s), old/new values, reason, and the
      full reconciliation proof
  ↓
OUTPUT: original run bytes unchanged; new erratum run is the corrected-metadata
        record; a reader consults both together
```

### Cần hiểu bắt buộc
- **Why immutability is preserved even for a "trivial" label fix**: an
  editable "immutable" run is not actually immutable — the whole point of
  `outputs/runs/<run_id>/` is that anyone can trust its contents didn't change
  after the fact; a Class B erratum gets the correction without breaking that
  guarantee.
- **Why the reconciliation check covers *every* scientific artifact in the
  affected run, not just the one field being corrected**: proves the
  *entire* run's scientific content is still trustworthy, not just that the
  one touched file happens to hash-match.
- **Why ambiguity defaults to Class A**: a wrong Class-B classification could
  quietly hide a real scientific defect behind "it's just a label" — the
  fail-closed default protects against that.

### Code/files nên đọc
1. `docs/adr/ADR-experiment-artifacts.md`'s "Immutability" section (the
   generic policy text)
2. Any one erratum's `audit/erratum.json` (e.g.
   `outputs/runs/t07_t08_random_label_erratum_20260818T162445Z_587615/audit/erratum.json`)
   as a worked example — note: this is git-ignored run evidence, not tracked
   in the repo, so read it from disk if still present locally

### Empirical result cần diễn giải
N/A — implementation/governance task. (The erratum *contents* correct real
defects found in T07/T08 — see LD-07/LD-08 for what those defects actually
were.)

### Failure/leakage risks
1. Classifying a defect that could plausibly affect a metric value as
   Class B "to save time" instead of Class A.
2. Writing an erratum without first re-verifying every scientific hash —
   skipping the reconciliation step defeats the entire mechanism.
3. Accidentally opening the original run's file in write mode during the
   "verify it's unchanged" step (must be strictly read-only).

### Teach-back gates
1. What's the exact test for whether a defect is Class A or Class B?
2. Why does a Class B erratum re-hash artifacts that have nothing to do with
   the field actually being corrected?
3. If a Class B erratum's scientific-hash-reconciliation step found even one
   mismatch, what should happen, and why?

### Target study time
**20 min**

- **Closed on:** —

---

## LD-07 — Random reference + Response LightGBM baseline (T07)

- **Status:** OPEN
- **Priority:** P0
- **Task / Issue:** T07 (GitHub Issue #8)
- **Commit(s):** `a942256` — "feat: complete T07 random and response
  baselines"; erratum corrections in `6b1b6f0`'s policy application (run-level,
  not code-level)
- **Authoritative run(s):** SMOKE `t07_smoke_20260818T111252Z_867633`; FULL
  `t07_full_20260818T111446Z_593205`; audit-only errata
  `t07_audit_erratum_20260818T150917Z_995999` (data-access + resource-metadata
  fields) and `t07_t08_random_label_erratum_20260818T162445Z_587615`
  (random-reference label)
- **Dependencies:** LD-02 (T05 split), LD-03 (T04 preprocessing), LD-04 (T06
  metrics), LD-05 (D30 scale path)

### AI work đã làm
Claude built `src/lightgbm_baseline.py` — a small, causal-agnostic LightGBM
binary-classifier fitting primitive (`FROZEN_BINARY_CONFIG`, `config_hash`,
`fit_binary_classifier`, `predict_probabilities`) deliberately kept generic
enough for T08 to reuse unchanged — and used it to fit a single Response
model (`P(Y=1|X)`, trained on train rows only, no `T`) on the complete frozen
train partition. Alongside it, generated the theoretical random-Qini
reference line, one deterministic seed-42 illustrative random ranking, and
the full frozen 200-draw random-ranking reference distribution, entirely via
T06's existing public interface (no metric logic reimplemented). Both methods
were scored on the identical frozen validation cohort through
`metrics.evaluate_ranking`. Built `kaggle/02_uplift_modeling.ipynb` as the
first real content in the public notebook series, executed a SMOKE stage
(50,000 rows) before a FULL run on the complete 9,785,714/2,096,938-row
train/validation partitions, and — after review found two governance
defects (a data-access boolean that conflated "no held-out access" with "no
data access at all," and a resource-measurement field mislabeling a
same-process before/after sample as a stage-scoped "peak") — corrected both
via Class-B errata (LD-06) rather than mutating the completed runs.

### Core flow phải tự giải thích được
```
INPUT: frozen train partition (9,785,714 rows), frozen validation partition
       (2,096,938 rows), X=f0..f11, T=treatment, Y=conversion
  ↓
OPERATION 1: fit Response = LightGBM binary classifier on train X,Y only
      (T never enters X); early-stop against validation X,Y only
  ↓
OPERATION 2: predict P(Y=1|X) on the full validation cohort
  ↓
OPERATION 3: generate Random = seeded_random_scores(n_validation, seed=42)
      (independent by construction -- takes no X/T/Y argument)
  ↓
OPERATION 4: score BOTH Random and Response through the identical
      metrics.evaluate_ranking() interface -- no separate formula for either
  ↓
OUTPUT: qini_above_random for Random (~ -18.5, one illustrative draw) and
        Response (~ -2139.3); response_diagnostics (ROC-AUC=0.904, diagnostic
        only, never a ranking claim)
```

### Cần hiểu bắt buộc
- **Why Response's high ROC-AUC (0.90) and terrible `qini_above_random`
  (-2139.3) are not a contradiction**: they measure different questions.
  ROC-AUC asks "does this model separate converters from non-converters,"
  which it does well because "sure things" and "lost causes" dominate
  factual conversion prediction; `qini_above_random` asks "does sorting by
  this score produce a good *targeting policy*," and sure-things/lost-causes
  contribute zero incremental value regardless of how confidently they're
  identified.
- **Why the Random reference is generated with zero dependence on `X`/`T`/`Y`**:
  that independence is the entire basis for calling it a "no-skill" floor —
  if it used any of those, it wouldn't be a valid baseline.
- **Why `best_iteration=1` for the Response FULL fit is not evidence
  training "only ran once"**: with `stopping_rounds=50`, the training loop
  necessarily attempted at least 51 candidate rounds before round 1's
  validation logloss went unbeaten for 50 consecutive rounds; LightGBM's
  standard early-stopping behavior then retains only the best-iteration
  prefix in the returned/serialized model — this is ordinary library
  mechanics, not an anomaly, and this project's own review process initially
  overclaimed the opposite before correcting it.
- **Why the notebook reuses T06's `evaluate_ranking`/`random_ranking_reference_distribution`
  rather than reimplementing anything**: T07 has zero new metric logic; its
  only genuinely new work is the model fit and the orchestration around it.

### Code/files nên đọc
1. `src/lightgbm_baseline.py` (the entire file — the shared fitting
   primitive T08 also depends on)
2. `kaggle/02_uplift_modeling.ipynb` — sections "1. Modeling Objective"
   through "5. Response LightGBM Baseline" (skip the guard/reproducibility
   cells on a first read; they're technical, not conceptual)
3. `configs/t07_baselines.json` (decision record: why SMOKE=50,000,
   resource_gates=0)
4. `tests/test_lightgbm_baseline.py` (8 tests — confirms train-only fitting,
   early-stopping sanity, bounds, determinism)
5. `docs/decision_register.csv` D12 (response baseline role) and D11 (random
   baseline role)

### Empirical result cần diễn giải
**Observed (FULL run, real validation cohort):** Random (one seed-42 draw)
`qini_above_random ≈ -18.49`; Response `qini_above_random ≈ -2139.31`;
Response ROC-AUC ≈ 0.904, average precision ≈ 0.203, log-loss ≈ 0.021.
**Can conclude:** on this development validation cohort, a factual-outcome
classifier with strong discriminative ability (high AUC) produces a *worse*
uplift ranking than pure noise — exactly the "response ≠ uplift" failure mode
this task exists to demonstrate.
**Cannot conclude:** that Response is a "bad model" in any general sense
(it's not being asked to solve the uplift problem); cannot conclude anything
about held-out performance; cannot conclude the random reference's realized
`-18.49` is "the" benchmark value — the *theoretical* line (`qini_above_random
= 0` by construction) is the actual primary reference, a labeling distinction
this project's review process had to explicitly fix after first drafting it
ambiguously.

### Failure/leakage risks
1. Fitting Response on anything but train rows (including accidental
   validation leakage into the training call).
2. `_source_row_id` misalignment between predictions and the frozen
   validation set.
3. `T`/`exposure`/`visit`/`_source_row_id` entering `X`.
4. Random scores generated from anything other than `(n, seed)` — i.e., any
   accidental dependence on `X`/`T`/`Y`.
5. Held-out access at any point (`SplitDataset.held_out_ids()` must never be
   called; this task's own SMOKE stage originally proved isolation by reading
   the held-out label directly from `split_membership.csv` — a real defect,
   later corrected to prove isolation *positively*, by construction, from
   the sanctioned partitions only, never by inspecting what's excluded).
6. Conflating the seed-42 illustrative random draw's realized value with the
   theoretical random reference's defined value of exactly 0 — a real
   labeling defect found and corrected via LD-06's erratum mechanism.
7. Mislabeling a same-process before/after memory sample as a genuine
   stage-scoped "peak" — a real defect found and corrected.

### Teach-back gates
1. Why can a model with ROC-AUC 0.90 still be a *worse-than-random* uplift
   ranker? Name the specific mechanism (sure-things/lost-causes).
2. What's wrong with proving held-out isolation by reading which rows *are*
   held out, even if you never use their values?
3. Why is `qini_above_random = 0` for the theoretical reference not a
   coincidence or an approximation — walk through why it's exactly zero by
   construction.
4. If someone told you "T07 shows Response is a bad model," what would you
   correct about that claim?
5. Why does `best_iteration=1` not mean "training stopped after one round"?

### Target study time
**90 min**

- **Closed on:** —

---

## LD-08 — T-Learner LightGBM (T08)

- **Status:** OPEN
- **Priority:** P0
- **Task / Issue:** T08 (GitHub Issue #9)
- **Commit(s):** `810a3f1` — "feat: complete T08 LightGBM T-Learner"
- **Authoritative run(s):** SMOKE `t08_smoke_20260818T154813Z_381508`
  (audit-only resource-metadata erratum:
  `t08_smoke_audit_erratum_20260818T155806Z_642086`); FULL
  `t08_full_20260818T160823Z_081282` (random-label erratum shared with T07:
  `t07_t08_random_label_erratum_20260818T162445Z_587615`)
- **Dependencies:** LD-04 (T06 metrics), LD-07 (shared `src/lightgbm_baseline.py`
  primitive and comparison-table pattern), LD-05 (D30 scale path)

### AI work đã làm
Claude implemented `src/tlearner.py` (136 lines) — a small, testable
correctness surface separate from the LightGBM fitting mechanism:
`partition_by_arm` (boolean-mask treated/control split with missing-arm
rejection), `assert_aligned_predictions` (row-identity alignment check),
`compute_tau` (the authoritative, exact `mu1_hat - mu0_hat` construction,
with bounds/finiteness validation on both inputs first), and
`reconcile_reloaded_tau` (a *derived* tolerance for comparing a reloaded tau
against the stored one — `2*atol + rtol*(|mu1_stored|+|mu0_stored|)` — instead
of an unjustified exact-equality or a naive flat tolerance that would misfire
near cancellation). Fitted `mu1` on all 8,317,858 treated train rows and
`mu0` on all 1,467,856 control train rows, each early-stopping only against
its own arm's validation subset, both scoring the complete 2,096,938-row
validation cohort. Extended `kaggle/02_uplift_modeling.ipynb` with T08's
SMOKE/FULL sections, a `RUN_T07_STAGE`/`RUN_T08_SMOKE_STAGE`/`RUN_T08_FULL_STAGE`
reuse-guard chain (each fail-closed on missing/hash-invalid accepted evidence,
never silently re-executing an already-accepted stage), a comparative
`model_summary.csv` carrying explicit `source_run_id`/`source_prediction_sha256`/
`source_metric_artifact_sha256` lineage columns (Random/Response values
inherited byte-for-byte from T07, never recomputed), and a final unguarded
Comparison + Interpretation section.

### Core flow phải tự giải thích được
```
INPUT: frozen train partition, frozen validation partition, X=f0..f11, T, Y
  ↓
OPERATION 1: partition_by_arm(T, train rows) -> treated-only, control-only
      training views (8,317,858 treated / 1,467,856 control)
  ↓
OPERATION 2: fit mu1_hat(x) = LightGBM(X_train_treated, Y_train_treated),
      early-stop on X_val_treated, Y_val_treated ONLY
     fit mu0_hat(x) = LightGBM(X_train_control, Y_train_control),
      early-stop on X_val_control, Y_val_control ONLY
      (identical frozen config for both -- no tuning, no arm-specific difference)
  ↓
OPERATION 3: BOTH mu1_hat and mu0_hat predict on the FULL validation cohort
      (every row, both arms -- mu1 on control rows is a counterfactual
      prediction, mu0 on treated rows likewise)
  ↓
OPERATION 4: tau_hat(x) = mu1_hat(x) - mu0_hat(x), exact elementwise,
      asserted not merely constructed
  ↓
OPERATION 5: metrics.evaluate_ranking(tau_hat, T, Y, source_row_id) -- T06 only
  ↓
OUTPUT: qini_above_random ≈ -1272.08; uplift@10-100%; tau sign counts
        (2,074,682 positive / 22,256 negative / 0 zero)
```

### Cần hiểu bắt buộc
- **Why T-Learner is two *separately fit* models, not one model with `T` as a
  feature**: that's the definitional line between T-Learner and S-Learner
  (deferred in this project). `T` partitions which rows train which model; it
  never enters `X` for either.
- **Why both models must score the *entire* validation cohort, not just their
  own arm**: `tau_hat = mu1 - mu0` is only meaningful if both surfaces are
  evaluated on the same rows — a control row's `mu1_hat` prediction is a
  genuine counterfactual estimate, not a factual one, and that's the whole
  point of the construction.
- **Why `tau_hat` is a predicted CATE, not an observed individual effect**:
  no row has both a treated and control outcome; the subtraction combines two
  separately-trained *regression surfaces'* predictions, never a measured
  fact about any one person.
- **Why the derived reload-tolerance formula is necessary, not
  over-engineering**: `tau` can be near zero from cancellation of two
  comparably-sized `mu1`/`mu0` values; a naive tolerance built from `tau`'s
  own (possibly tiny) magnitude would be far too strict, while an unjustified
  exact-equality check on a *reloaded* (re-derived) quantity has no
  principled basis — the propagated bound from each surface's own
  independently-verified reload tolerance is the actually correct
  construction.
- **Why `qini_above_random ≈ -1272` (worse than random, better than Response)
  supports no strong claim either way**: it says this *fitted model's
  ranking* didn't beat the no-skill floor on *this* validation cohort — it
  says nothing about whether real treatment heterogeneity exists, doesn't
  invalidate the T-Learner method or this implementation, and doesn't license
  post-hoc tuning.

### Code/files nên đọc
1. `src/tlearner.py` (the entire file — small, and this is the actual
   correctness-critical logic for the task)
2. `src/lightgbm_baseline.py` (reused unchanged from T07 — read LD-07 first)
3. `kaggle/02_uplift_modeling.ipynb` — the T08 SMOKE/FULL sections plus the
   final "Comparison"/"Interpretation and limitations" sections
4. `tests/test_tlearner.py` (16 tests — especially
   `test_compute_tau_hand_computed_sign_orientation` and
   `test_reconcile_reloaded_tau_near_zero_cancellation_case`)
5. `configs/t08_tlearner.json` (decision record: why SMOKE=200,000, the
   arm-conditional rare-cell reasoning)

### Empirical result cần diễn giải
**Observed (FULL run, real validation cohort, 2,096,938 rows):**
`qini_area = -247.41`, `qini_above_random = -1272.08` (theoretical reference:
exactly 0); `tau_hat` sign split 2,074,682 positive / 22,256 negative / 0
zero; `mu1` diagnostics (treated-arm factual) ROC-AUC=0.902; `mu0` diagnostics
(control-arm factual) ROC-AUC=0.890; both `mu1` and `mu0` reached
`best_iteration=1` (same early-stopping mechanics as T07's Response, not an
anomaly).
**Can conclude:** this fitted T-Learner did not produce a useful uplift
ranking relative to the theoretical random reference on this development
validation cohort; its `qini_above_random` is less negative than Response's
on the same cohort (a numeric fact only).
**Cannot conclude:** that treatment heterogeneity is absent from the true data
generating process; cannot conclude the T-Learner *method* or this
*implementation* is invalid; cannot conclude T-Learner is "better than
Random" (both rank below the no-skill floor here); cannot authorize any
post-hoc tuning from this result.

### Failure/leakage risks
1. Arm cross-contamination — control rows leaking into `mu1`'s fit or vice
   versa.
2. Row misalignment when combining `mu1_hat`/`mu0_hat` into `tau_hat` —
   mitigated by an explicit exact-equality assertion in this project, but the
   generic risk exists for any two-model combination.
3. Differential arm sample size (`mu0` trains on ~5.7× fewer rows than
   `mu1`) creating asymmetric estimation variance between the two surfaces —
   not itself bias, but a real, structural imbalance worth watching in
   decile/support diagnostics.
4. Sign inversion from mixing up which model is `mu1` vs `mu0`.
5. Recomputing T06's random reference or T07's Response metrics "for
   comparison" instead of reusing the accepted, hash-verified evidence — this
   project built an explicit reuse-guard chain specifically to prevent this.
6. Calling `tau_hat` an observed individual treatment effect in any
   reader-facing text.
7. Using a naive tolerance (either exact-equality or a flat `rtol`/`atol` on
   `tau` itself) when verifying a reloaded model's reproduced `tau` — proven
   wrong for near-cancellation cases in this task's own test suite.

### Teach-back gates
1. Why does a control-arm row still get a `mu1_hat` prediction, and is that
   prediction "real" in any sense?
2. What exactly would go wrong if `mu0` accidentally trained on a few
   treated rows?
3. Why is `tau_hat`'s reload-comparison tolerance derived from `mu1`/`mu0`'s
   *own* stored magnitudes rather than from `tau_hat`'s own magnitude?
4. Given `qini_above_random ≈ -1272` for T-Learner and `≈ -18.5` for the
   random illustrative draw, what is the one correct conclusion, and name two
   incorrect conclusions someone might be tempted to draw?
5. Why does the arm sample-size imbalance (8.3M vs 1.5M) not, by itself,
   imply the resulting `tau_hat` is biased?
6. Why does this task reuse T07's `model_summary.csv` values by hash
   reference instead of recomputing them?

### Target study time
**90 min**

- **Closed on:** —

---
---

# INHERITED (pre-boundary, not counted as post-reset debt)

These predate commit `c23dc7a` and are useful to review, but are not
post-reset vibe-code debt under this log's inclusion rules.

- **Sprint-1 causal/data contracts freeze** — `f1a1c30` (2026-08-10) and the
  `docs/01`-`docs/07` numbered contracts they established. Everything in
  LD-01 through LD-08 above is built directly on top of these frozen
  definitions (`X=f0-f11`, `T=treatment`, `Y=conversion`, the estimand, etc.);
  understanding them is a genuine prerequisite even though they're not
  counted in the post-reset total.
- **T01 — Data engineering pipeline** — `10dee33` and related commits
  (2026-08-12). Produces the checksummed, validated processed Parquet every
  later task loads via `configs/data_manifest.json` → `load_selector()` →
  `open_processed_dataset()`. Authoritative run:
  `t01_production_20260814T070821Z_898748` (most recent `t01_production_*`
  run on disk; UNKNOWN / NOT VERIFIED whether this is the exact one every
  current config cites — cross-check `configs/data_manifest.json`'s
  `processed_sha256` against a specific run's evidence before treating this
  run_id as authoritative).
- **T02 — Exploratory data analysis** — `ccce06a` (2026-08-13). Authoritative
  run: UNKNOWN / NOT VERIFIED — several `t02_eda_*` runs exist on disk
  (`t02_eda_20260813T092312Z_615472` through `t02_eda_20260814T070842Z_712619`);
  which one is cited as authoritative by a current config was not checked in
  this reconstruction.

---
---

# NEXT / NOT YET INCURRED

No implementation exists for these; they are not learning debt yet under this
log's rules (planning-only or fully unstarted work is never counted as
coding debt).

- **T03-C final 2,000-draw randomization calibration production run** —
  *partially* an exception: the full mechanism (`conditional_permute_treatment`,
  the order-statistic/Monte-Carlo interval functions, evidence-record schema)
  **is** implemented and tested as part of LD-01 (`0d7c97b`). What has *not*
  happened is the actual production execution —
  `configs/t03_audit.json`'s `randomization_calibration.execution_state` is
  literally `"DEFERRED_T03_C"`, `evidence_status: null`, and
  `full_mapping_allowed_modes` currently permits only `UNIT_FIXTURE`/
  `SMOKE_ONLY`, not `FINAL_CALIBRATION`. When this eventually runs, it earns
  its own empirical-result addendum to LD-01, not a new LD (the code is
  already covered there).
- **T09 — X-Learner** — not started. No CODE PLAN exists. Per
  `docs/05_methodology_scope.md`, requires deterministic two-fold
  training-only cross-fitting (a genuinely new mechanism T07/T08 didn't need)
  and out-of-fold pseudo-effect construction (`D1 = Y - mu0_hat(X)` on treated
  rows, `D0 = mu1_hat(X) - Y` on control rows) — read LD-08 first, since the
  contrast with T-Learner's *lack* of cross-fitting is exactly what makes
  X-Learner's requirement legible.
- **T10/T11 — Causal Forest verification & training** — not started.
- **T12-T18** — not started (common validation comparison, root-cause
  diagnostics, decile/segment analysis, 500-draw bootstrap uncertainty,
  pre-test freeze, one-shot held-out evaluation, final interpretation).

---
---

# Self-audit (per the reconstruction instructions)

1. **Rebuild boundary found:** `c23dc7a` (2026-08-18 11:40:25 +0700),
   confirmed by commit message content ("Kaggle-first architecture") and the
   immediately-following commit's message literally saying "pre-reset
   notebooks."
2. **Chronological post-reset LD IDs/tasks:** LD-00 (`c23dc7a`, `212b706`,
   `2e1feae`, `28758fe`, `153f394`) → LD-01 (`0d7c97b`) → LD-02 (`85a9ae3`) →
   LD-03 (`1ae3f54`) → LD-04 (`f67d89e`) → LD-05 (`f527f0b`) → LD-06
   (`6b1b6f0`) → LD-07 (`a942256`) → LD-08 (`810a3f1`). This accounts for
   all 13 commits from `c23dc7a` through `810a3f1` inclusive — no gap.
3. **Inherited items:** Sprint-1 contract freeze (`f1a1c30`), T01
   (`10dee33` + earlier same-day commits), T02 (`ccce06a`) — all dated before
   `c23dc7a`.
4. **Next/not-yet-incurred item:** T03-C's production run (mechanism already
   covered under LD-01), T09 (X-Learner) as the next genuinely unstarted
   task, then T10 onward.
5. **Estimated total study time:** ~9 hours (535 minutes) across the 9
   post-reset LD items.
6. **Exact file created:** `docs/learning/learning_debt_log.md` (new file;
   `docs/learning/` did not previously exist).
7. **History gaps / uncertainties found, named explicitly:**
   - T01's and T02's exact authoritative run IDs were **not** independently
     cross-checked against a citing config's checksum in this reconstruction
     (both are INHERITED and out of this log's required scope, but flagged
     here as UNKNOWN / NOT VERIFIED rather than guessed).
   - Two `t01_d04_confirmation_*` and six `t01_benchmark_*` runs exist on disk
     with no reconciliation attempted here to which (if any) are still
     considered authoritative versus superseded development evidence — same
     UNKNOWN / NOT VERIFIED treatment.
   - One orphaned, non-finalized run directory exists on disk,
     `outputs/runs/t08_full_20260818T160333Z_733020` (a failed first FULL
     attempt, empty, no manifest) — correctly *not* cited as evidence
     anywhere in this log, retained on disk as failed-run evidence per
     project convention, mentioned here only for completeness.
