# GitHub Issue reconciliation drafts (not yet applied)

This file was produced by the documentation/planning reconciliation pass
described in `docs/agent_tasks/docs_reconciliation.md`. **No GitHub API write
credential was available in this session** (`$GITHUB_TOKEN` returned `Bad
credentials`, and no `gh` CLI is installed), so MASTER #20 and Issues #4-#19
could not be edited on GitHub directly. The content below is ready to paste
into each Issue by whoever has write access (`gh issue edit <n> --body-file
-` or the GitHub UI). Delete this file once applied.

Scope and method: only the parts flagged stale by
`docs/agent_tasks/docs_reconciliation.md` are changed — the old
per-notebook-series naming (`01_data_feasibility.ipynb` ...
`07_final_story.ipynb`), the D23 scale-rung wording superseded by D30, and the
missing D32 feature-semantics rule. GOAL/INPUT/PROCESS/OUTPUT/VERIFICATION/
DEPENDENCIES/DEFINITION OF DONE content, checklists, and methodological
requirements are left untouched.

---

## MASTER #20 — full replacement body

````markdown
# Goal

Authoritative execution overview for `causal-uplift-modeling`. Every other Issue is a small,
self-contained execution spec that inherits the rules on this page. Read this Issue once; then
work Issue-by-Issue without re-reading governance documents.

Architecture: **Kaggle-first + notebook-first + feasibility-first + learning-first.**

# Execution architecture

```text
Kaggle
├── primary heavy-compute environment (one run may span multiple sessions)
├── saved versions
├── full-data experiments
└── presentation

GitHub repository
├── notebook source / version history
├── reusable Python source
├── configs
├── focused tests
└── documentation

src/       reusable logic only when reuse / correctness / a contract justifies extraction
tests/     focused correctness and regression tests
outputs/   predictions, metrics, manifests, and downstream inputs as justified
```

Kaggle is the primary analytical execution environment, notebook runtime, and presentation
surface. A full pipeline does not have to fit inside one Kaggle notebook session: expensive
stages communicate through explicit, versioned, immutable artifacts under
`outputs/runs/<run_id>/`, and a downstream stage re-derives its input from a declared upstream
run rather than inheriting in-memory state. Heavy or held-out-sensitive computation may live in
`notebooks/internal/` (e.g. `notebooks/internal/t03_data_integrity_audit.ipynb`,
`t03b_development_integrity.ipynb`, `t04_preprocessing.ipynb`, `t05_frozen_split.ipynb`, with more
added as tasks reach that stage) rather than in a public notebook. GitHub remains task
management, version control, and the architecture/specification record.

**Notebook-first is not notebook-only, and it is not notebook-hidden.** The scientific
narrative — question, method, result, interpretation, downstream implication — stays visible in
the relevant notebook. Engineering plumbing (hashing, manifest writing, environment capture,
serialization, artifact registries) belongs in `src/` or an appendix. Do not hide research logic
behind opaque helper APIs, and do not create abstractions for architectural appearance.

# Task vs notebook

An Issue is an **execution task**. A notebook is an **artifact**. They are not 1:1, and heavy
stages may run across one or more Kaggle sessions and/or an internal notebook before a public
notebook consumes their frozen output. Several Issues write into the same public notebook; each
stays a separate task with its own checklist and Definition of Done.

The public reader-facing story is exactly four notebooks:

| Public notebook | Fed by |
|---|---|
| `kaggle/01_data_understanding.ipynb` | S01 #1, T01 #2, T02 #3, T03 #4 (A/B/C), T05 #6, T04 #5 — data / audit / split / preprocessing evidence |
| `kaggle/02_uplift_modeling.ipynb` | T06 #7, T07 #8, T08 #9, T09 #10, T10 #11, T11 #12 — metrics + Response + T-Learner + X-Learner + Causal Forest |
| `kaggle/03_validation_uncertainty.ipynb` | T12 #13, T13 #14 (conditional), T14 #15 (P1, optional segment analysis), T15 #16 — common validation comparison + diagnostics where triggered + bootstrap |
| `kaggle/04_final_evaluation.ipynb` | T16 #17, T17 #18, T18 #19 — pre-test freeze + one-shot held-out evaluation + final interpretation/defense |

**Issue != notebook.** A task's "Execution location" names its governed compute stage, not
necessarily a single public notebook cell; see each Issue for whether it runs in a Kaggle session,
an internal notebook, or both before its output reaches the public notebook above.

The legacy notebooks under `notebooks/legacy/` (`00_project_overview.ipynb`,
`01_sprint1_feasibility_evidence.ipynb`, `02_data_engineering_pipeline.ipynb`,
`03_exploratory_data_analysis.ipynb`) are **historical evidence** from the pre-reset architecture.
They are retained, not deleted. Their accepted results stay valid and are inherited rather than
re-derived.

# Critical path (P0)

```text
architecture / data feasibility
→ EDA
→ frozen split
→ minimal preprocessing
→ uplift metrics
→ Random + Response baseline
→ T-Learner
→ X-Learner
→ Causal Forest
→ common validation comparison
→ bootstrap uncertainty
→ pre-test freeze
→ one-shot held-out evaluation
→ final interpretation
```

```text
#1 S01 → #2 T01 → #4 T03-A → #3 T02 → #6 T05 → #5 T04 → #7 T06 → #8 T07
→ #9 T08 → #10 T09 → #11 T10 → #12 T11 → #13 T12 → #16 T15 → #17 T16
→ #18 T17 → #19 T18

off the blocking path, in parallel after #6 T05:
#4 T03-C  (mandatory; must complete before #17 T16)
#15 T14   (P1; after #13 T12)
#14 T13   (conditional; only if #13 T12 is surprising or unstable)
```

Nothing outside this path may block it.

## P0 — mandatory, blocking

S01, T01, T03-A, T02, T05, T04, T06, T07, T08, T09, T10, T11, T12, T15, T16, T17, T18.

## P0 — mandatory, non-blocking

**T03-C** (2,000-draw randomization calibration). Mandatory and frozen. It is *not* a
predecessor of T04 or of any modeling task, because `docs/06` Stage 0 item 3 states the
calibration algorithm is frozen early while "generated development-data thresholds are locked
later, before the pre-test executable freeze," and `docs/03` requires the generated percentiles
to be finalized before the pre-test executable freeze. Run it in parallel once T05 exists.
Deadline: before T16.

## P1 / conditional / deferred

| Item | Class | Rule |
|---|---|---|
| T13 root-cause diagnostics | Conditional | Execute only when T12 produces a surprising or unstable result. Not an unconditional predecessor of T15. |
| T14 decile/segment analysis | P1 | After T12; runs in parallel with downstream P0 work. Never blocks T15/T16/T17. |
| DR-Learner | Stretch / conditional | Development-only. Enters held-out evaluation only if every promotion gate passes before freeze. |
| S-Learner | Deferred | Not implemented; never silently substituted for Response or T-Learner. |
| Cross-language CF bridge | Conditional | Python-only unless documented evidence proves a required capability is missing (D22). |
| Extensive hyperparameter tuning | Noncritical | Bounded predeclared candidates only. |
| Decorative EDA | Noncritical | Every retained output must answer a stated question. |
| Excessive infrastructure / governance | Noncritical | Must not delay the mandatory path. |

**Causal Forest is a mandatory accepted main comparator (D15).** It may not be omitted,
substituted, or deferred for difficulty, runtime, or unfavorable performance. If every eligible
exact implementation fails its required gates, retain the failure evidence and STOP for explicit
owner methodology review. Its categorical-feature representation (D32) is a separate, currently
unresolved implementation blocker tracked by `docs/adr/ADR-CF-implementation.md` — see the next
section.

# Feature semantics (D32)

`f0`, `f2`, `f7`, `f10` are **continuous**. `f1`, `f3`, `f4`, `f5`, `f6`, `f8`, `f9`, `f11` are
**categorical** numeric tokens with no ordinal interpretation — their physical `float64` storage
does not make them continuous. Do not infer category/continuous status from cardinality, and do
not compute SMD/mean/variance on a categorical token's raw value. LightGBM stages must use a
category-aware representation (native categorical handling) for the categorical group. Causal
Forest has no LightGBM-equivalent native categorical support; its representation is an explicit
open decision, not something to guess (`docs/adr/ADR-CF-implementation.md`). Any T07-T10 fitted
result produced before an estimator's categorical-representation fix is stale development
evidence and requires a corrected rerun before it can support a claim — this Issue does not
assert that any specific rerun has happened; check each Issue's own status and current
`configs/`/`outputs/` evidence.

# Incremental execution model

Each Issue carries small numbered sub-tasks. The intended loop is:

```text
read Issue → implement one or a few unchecked sub-tasks → verify → tick the checklist → next
```

Do not implement an entire task in one uncontrolled change. Do not tick a box that was not
verified.

# Frozen rules (inherited by every Issue)

These are not repeated in individual Issues. They always apply.

- `X` is exactly `f0`–`f11`, in that order, at primary `float64` precision (D09). Nothing else
  ever enters `X`. Per D32, `f0`,`f2`,`f7`,`f10` are continuous and `f1`,`f3`,`f4`,`f5`,`f6`,`f8`,
  `f9`,`f11` are categorical — see "Feature semantics (D32)" above.
- `T = treatment` (assignment / ITT, not exposure). Primary `Y = conversion`; `visit` is a
  secondary outcome in a separate pipeline.
- `exposure` is audit-only: excluded from `X`, from eligibility, from filtering, and from the
  treatment definition.
- `_source_row_id` is a zero-based CSV row ordinal used for provenance and alignment. It is not
  a person identifier and never enters `X`.
- Estimand is assignment/ITT CATE for ranking over the frozen eligible released-row population.
  **Predicted uplift is not a true individual treatment effect.** Empirical PEHE against true
  ITE is unavailable on this dataset and must not be reported (D28).
- Keep every released row by default (D07). Dedup/weighting is sensitivity-only; rows may be
  excluded only on a predeclared hard-integrity gate failure.
- Split: 70/15/15, joint `(T,Y)` stratification, seed `42`, source-row identity disjoint.
- **Held-out data is untouchable until T17.** No unofficial held-out diagnostics, no tuning on
  test-derived information. If an operation would read held-out performance, stop.
- Frozen portfolio: theoretical/seeded Random reference, Response LightGBM diagnostic baseline,
  T-Learner, X-Learner, mandatory Causal Forest.
- Primary ranking statistic is Qini above theoretical random (D24). Raw Qini/AUUC and
  top-K/incremental conversions are secondary (D25/D26). Response AUC/AP/log loss are
  diagnostic only and never select a causal winner (D27).
- Uncertainty: exactly 500 paired treatment-arm-stratified bootstrap draws with fixed
  predictions (D29). T17 is the first and only held-out evaluation, under the T16 freeze.
- D30 scale-gating policy applies: `SMOKE → [RESOURCE GATE(S) if required] → FULL`, task-declared
  sizes frozen before execution (supersedes the prior fixed `D23` `50K → 500K → 2M → full`
  ladder; T01-T06 evidence produced under D23 is retained unchanged). Execute only the current
  stage; promote only after its predeclared correctness/resource evidence passes.
- Balance diagnostics do not prove randomization. `f0`–`f11` are anonymized and carry no known
  business meaning — do not invent one.

# Data feasibility standards

- Kaggle is the primary benchmark environment. Do not encode a specific local machine's limits
  as a universal feasibility constraint.
- Raw `.csv.gz` is the provenance/ingestion source and the checksum anchor. It is not the
  repeated analytical storage format.
- Parquet (or another typed columnar representation) is the analytical store (D19).
- Avoid repeated full-data scans. Prefer one vectorized multi-column aggregation pass over many
  single-column passes.
- Cache and reuse expensive intermediate results; persist them as run artifacts when they feed
  a downstream task.
- Sampling is acceptable for **secondary** diagnostics when statistically justified and clearly
  labeled. Per `docs/03`, a row-limited check must be labeled as such and cannot support a
  full-data conclusion — so a sampled result may not be recorded as the evidence for a
  hard gate or for a required audit row.
- Optimize for scalable reasoning, not brute-force execution.

# Source code standards

```text
notebook   visible scientific narrative
src/       reusable, testable logic
tests/     targeted correctness verification
configs/   consequential reproducibility settings
```

Extract into `src/` when logic is reused across notebooks/tasks, is mathematically or
statistically important enough to deserve a test, or would otherwise be duplicated. Do not
extract for appearance.

# Evidence before optimization

Measure before you optimize; verify before you tune; report before you interpret. A run that
executed without error is not a verified run. Notebook exists ≠ notebook parses ≠ tests pass ≠
clean Run All passes. Where applicable, acceptance requires a fresh kernel, Run All in order,
zero uncaught errors, expected outputs, and invariant reconciliation. Bounded verification may
replace an expensive rerun only when the reason and evidence are stated explicitly.

A disappointing result is not a software defect. Only a demonstrated defect justifies a rerun,
and failed-run evidence is retained, never deleted.

# Run-artifact governance

Machine-readable evidence lives in immutable `outputs/runs/<run_id>/{audit,tables,figures,
predictions,metrics,models}/`. A rerun mints a new run id; it never mutates an existing run.
Stable copies outside `outputs/runs/<run_id>/` are inspection conveniences only and never
replace historical run evidence. This is what makes a multi-Kaggle-session pipeline reproducible
across sessions: a downstream session verifies and reads an upstream session's artifacts by
manifest/checksum rather than assuming shared state.

# Data path

```text
configs/data_manifest.json (environment-local selector)
  → validate source identity (raw SHA-256, exact header, sizes)
  → convert to Parquet, appending _source_row_id
  → validate processed Parquet (schema, layout, ordinal continuity, semantics)
  → open processed dataset (fails closed unless the expected SHA-256 matches)
```

Never bypass a link; never discover input by glob, filename order, or directory heuristic. The
manifest is environment-local — its **paths** differ between Kaggle and a local checkout, but
its **checksums are environment-invariant**, so identity checking holds in both. Semantic
identity is mandatory; byte-identical physical output is claimed only within one environment.

# Source precedence

1. `docs/decision_register.csv` (D01–D32, owner-approved)
2. Numbered contracts `docs/01`–`docs/07` and ACCEPTED ADRs
3. Accepted empirical evidence
4. GitHub Issue wording
5. Existing code

Issues are execution views. They are reconciled to higher-authority sources, never the reverse.
If an Issue conflicts with a frozen decision, the decision wins and the Issue is corrected. A
checked box on this page is not empirical truth by itself — verify against current
`configs/`/`outputs/` evidence before relying on it, especially for any task affected by the D32
feature-semantics correction.

# Working phases

`[TUTOR]` → `[CODE PLAN]` → `[IMPLEMENT]` → `[VERIFY]` → `[CLEAN RUN]` → `[REVIEW]` →
`[ACCEPT]`. Execute only the requested phase; do not auto-advance. `[REVIEW]` reports findings
and does not edit unless asked. Acceptance is separate from implementation; commit, push, Issue
closure, and starting the next task are separate explicit actions.

Before non-trivial implementation the owner should be able to state INPUT, OUTPUT, the main
data/model flow, its 5–10 major steps, and the important leakage/statistical failure modes. The
owner is not expected to reinvent generic engineering infrastructure.

# Board status

**Sprint 2 — data and engineering**

- [x] [S01 — Sprint-1 feasibility evidence](https://github.com/arthur105204/causal-uplift-modeling/issues/1)
- [x] [T01 — Data engineering pipeline](https://github.com/arthur105204/causal-uplift-modeling/issues/2)
- [x] [T02 — Exploratory data analysis](https://github.com/arthur105204/causal-uplift-modeling/issues/3)
- [ ] [T03 — Data quality & causal integrity](https://github.com/arthur105204/causal-uplift-modeling/issues/4) — A: P0 blocking · C: P0 non-blocking
- [ ] [T05 — Frozen split](https://github.com/arthur105204/causal-uplift-modeling/issues/6)
- [ ] [T04 — Preprocessing strategy](https://github.com/arthur105204/causal-uplift-modeling/issues/5)
- [ ] [T06 — Uplift metrics](https://github.com/arthur105204/causal-uplift-modeling/issues/7)

**Sprint 3 — modeling**

- [ ] [T07 — Random & Response baselines](https://github.com/arthur105204/causal-uplift-modeling/issues/8)
- [ ] [T08 — T-Learner](https://github.com/arthur105204/causal-uplift-modeling/issues/9)
- [ ] [T09 — X-Learner](https://github.com/arthur105204/causal-uplift-modeling/issues/10)
- [ ] [T10 — Causal Forest verification](https://github.com/arthur105204/causal-uplift-modeling/issues/11)
- [ ] [T11 — Causal Forest training](https://github.com/arthur105204/causal-uplift-modeling/issues/12)

**Sprint 4 — validation and uncertainty**

- [ ] [T12 — Common validation comparison](https://github.com/arthur105204/causal-uplift-modeling/issues/13)
- [ ] [T13 — Root-cause diagnostics](https://github.com/arthur105204/causal-uplift-modeling/issues/14) — conditional
- [ ] [T14 — Decile & segment analysis](https://github.com/arthur105204/causal-uplift-modeling/issues/15) — P1
- [ ] [T15 — Bootstrap uncertainty](https://github.com/arthur105204/causal-uplift-modeling/issues/16)

**Sprint 5 — final evaluation**

- [ ] [T16 — Pre-test freeze](https://github.com/arthur105204/causal-uplift-modeling/issues/17)
- [ ] [T17 — One-shot held-out evaluation](https://github.com/arthur105204/causal-uplift-modeling/issues/18)
- [ ] [T18 — Final interpretation & defense](https://github.com/arthur105204/causal-uplift-modeling/issues/19)

Board checkboxes are a status view, not authoritative evidence — reconcile against current
`configs/`/`outputs/runs/` state, especially for T07-T11 pending the D32 categorical-
representation rework.

# Open owner decisions

These are flagged, not decided. The architecture reset did **not** change any of them, and
neither did the D32 feature-semantics correction.

1. **T03 sampled distributional diagnostics.** `docs/03` ED-03 requires per-feature quantiles,
   quantile differences, and the empirical CDF/KS distance. `docs/03` also states a row-limited
   check cannot support a full-data conclusion. Recording a *sampled* ED-03 distributional
   result as the audit evidence therefore needs owner approval and a `docs/03` amendment. The
   current Issue wording keeps these full-data but requires a single vectorized pass.
2. **2,000-draw calibration count.** Frozen by `docs/03` (initial 2,000 draws from master seed
   42) and `docs/06` (diagnostic null calibration row). Reducing the initial count would need
   owner approval and a document amendment. It has **not** been reduced — only rescheduled off
   the blocking path, which `docs/06` Stage 0 already permits.
3. **Residual sequencing risk from that rescheduling.** `docs/03` audit ordering item 6 asks for
   material diagnostics to be bounded before the affected estimator is promoted. If T03-C runs
   very late and returns `MATERIAL_CONCERN`, the predeclared `ROBUSTNESS_REQUIRED` sensitivity
   would land after promotion. Mitigation adopted here: schedule T03-C immediately after T05, in
   parallel with T06–T09, rather than at T16.
4. **Legacy notebook placement.** The four pre-reset notebooks live under `notebooks/legacy/`.
5. **T03/T03-B mixed-type calibration joint action rule.** D32 requires ED-03 (continuous SMD)
   and ED-03b (categorical TVD) to stay separate diagnostics. No joint null-calibrated action
   threshold combining them is defined, and none should be invented without an owner-approved
   decision — see `docs/03_assumption_and_audit_spec.md`.
6. **Causal Forest categorical representation.** Unresolved; tracked by
   `docs/adr/ADR-CF-implementation.md`. Blocks T10/T11 correctness-gate completion against real
   (non-synthetic-encoded) data until a representation is proposed and accepted.
````

---

## Issue #4 — [T03] Data Quality, Duplicate & Causal Integrity Audit

Replace the "# Execution location" section body:

```markdown
Kaggle-primary governed stage; internal notebooks already exist for this task:
`notebooks/internal/t03_data_integrity_audit.ipynb` (T03-A/T03-B) and
`notebooks/internal/t03b_development_integrity.ipynb`. May use one or more Kaggle sessions.
Public presentation: consumed by `kaggle/01_data_understanding.ipynb` (Issue != notebook — see
MASTER #20).
```

Append to "# Frozen rules":

```markdown
- Per D32, ED-03 (SMD) applies only to continuous `f0`,`f2`,`f7`,`f10`; ED-03b (TVD-style
  category-distribution diagnostic) applies only to categorical `f1`,`f3`,`f4`,`f5`,`f6`,`f8`,
  `f9`,`f11`. Do not compute SMD on a categorical feature and do not combine ED-03/ED-03b via
  `max()` — see `docs/03_assumption_and_audit_spec.md`. This reopens the feature-semantics-
  dependent parts of T03; unaffected identity/duplicate/permutation mechanics are not affected.
```

## Issue #5 — [T04] Preprocessing & Feature Engineering Strategy

Replace "# Execution location" body (keep any existing trailing sentence about `src/`
extraction as-is if present):

```markdown
Kaggle-primary governed stage; internal notebook `notebooks/internal/t04_preprocessing.ipynb`
already exists for this task. May use one or more Kaggle sessions. Public presentation: consumed
by `kaggle/01_data_understanding.ipynb` (Issue != notebook — see MASTER #20).
```

Append to "# Frozen rules":

```markdown
- Per D32, preprocessing is estimator-aware, not a single no-op/identity transform: continuous
  features (`f0`,`f2`,`f7`,`f10`) stay numeric; categorical features (`f1`,`f3`,`f4`,`f5`,`f6`,
  `f8`,`f9`,`f11`) get an estimator-specific categorical representation, fit on training data
  only and reused unchanged on validation/held-out rows. Any prior no-op/identity-transform
  acceptance for T04 is superseded and requires a corrected rerun.
```

## Issue #6 — [T05] Implement Frozen Train / Validation / Held-out Test Split

Replace "# Execution location" body:

```markdown
Kaggle-primary governed stage; internal notebook `notebooks/internal/t05_frozen_split.ipynb`
already exists for this task. Split mechanics and the access guard belong in `src/` as before.
May use one or more Kaggle sessions. Public presentation: consumed by
`kaggle/01_data_understanding.ipynb` (Issue != notebook — see MASTER #20).
```

No D32 addendum needed — the split is defined over rows, not feature semantics.

## Issue #7 — [T06] Implement & Validate Uplift Metrics

Replace "# Execution location" body:

```markdown
Kaggle-primary governed stage. May use one or more Kaggle sessions; the production metric
implementation belongs in `src/` as before. Public presentation: consumed by
`kaggle/02_uplift_modeling.ipynb` (Issue != notebook — see MASTER #20).
```

No D32 addendum needed — metric formulas are feature-representation-independent.

## Issue #8 — [T07] Random Ranking & Response LightGBM Baselines

Replace "# Execution location" body:

```markdown
Kaggle-primary governed stage. May use one or more Kaggle sessions. Public presentation:
consumed by `kaggle/02_uplift_modeling.ipynb` (Issue != notebook — see MASTER #20).
```

Append to "# Frozen rules":

```markdown
- Response LightGBM must use D32 category-aware representation (native categorical handling for
  `f1`,`f3`,`f4`,`f5`,`f6`,`f8`,`f9`,`f11`; numeric for `f0`,`f2`,`f7`,`f10`). Any prior fitted
  Response model trained on all twelve columns as undifferentiated continuous/numeric input is
  stale development evidence and requires a corrected rerun.
```

## Issue #9 — [T08] T-Learner LightGBM

Replace "# Execution location" body:

```markdown
Kaggle-primary governed stage. May use one or more Kaggle sessions. Public presentation:
consumed by `kaggle/02_uplift_modeling.ipynb` (Issue != notebook — see MASTER #20).
```

Append to "# Frozen rules":

```markdown
- Both T-Learner arm surfaces must use D32 category-aware LightGBM representation. The
  `tau_hat = mu1_hat - mu0_hat` formula is unchanged. Any prior fitted T-Learner trained on all
  twelve columns as undifferentiated continuous/numeric input is stale development evidence and
  requires a corrected rerun.
```

## Issue #10 — [T09] X-Learner LightGBM

Replace "# Execution location" body:

```markdown
Kaggle-primary governed stage. May use one or more Kaggle sessions. Public presentation:
consumed by `kaggle/02_uplift_modeling.ipynb` (Issue != notebook — see MASTER #20).
```

Append to "# Frozen rules":

```markdown
- Nuisance and effect-regression stages must use D32 category-aware LightGBM representation. Any
  learned categorical-representation state is fit on a fold's training side only and applied
  unchanged to that fold's out-of-fold side — it must obey the same OOF leakage boundary as the
  pseudo-outcome construction. D1/D0 pseudo-outcome formulas and the combination rule are
  unchanged. Any prior fitted X-Learner trained on all twelve columns as undifferentiated
  continuous/numeric input is stale development evidence and requires a corrected rerun.
```

## Issue #11 — [T10] Causal Forest Scale & Implementation Verification

Replace "# Execution location" body (keep the existing sentence about Kaggle being the
benchmark environment):

```markdown
Kaggle-primary governed stage; may use one or more Kaggle sessions. Kaggle is the benchmark
environment — its measured [... keep existing continuation unchanged ...]
```

Replace the D23 rung references:

- `"D23 scale rungs `50K → 500K → 2M → full` apply. Execute only the current rung; promote only ..."`
  → `"D30 SMOKE → [RESOURCE GATE(S) if required] → FULL applies (supersedes the prior fixed D23
  50K → 500K → 2M → full ladder). Execute only the current stage; promote only after its
  predeclared correctness/resource evidence passes."`
- `"Run train-only scale benchmarks at the D23 rungs"` → `"Run train-only scale benchmarks at the
  declared D30 SMOKE/RESOURCE stage(s)"`
- `"Scale evidence exists at the executed D23 rungs on Kaggle hardware."` → `"Scale evidence
  exists at the executed D30 SMOKE/RESOURCE stage(s) on Kaggle hardware."`

Append to "# Frozen rules":

```markdown
- Per D32, raw `f0`–`f11` must not be passed to Causal Forest as an undifferentiated
  continuous/numeric matrix — `f1`,`f3`,`f4`,`f5`,`f6`,`f8`,`f9`,`f11` are categorical tokens.
  Causal Forest has no LightGBM-equivalent native categorical representation; the correctness
  gate must fail closed on raw real-data input rather than accept it silently. The concrete
  categorical representation is an unresolved implementation decision tracked by
  `docs/adr/ADR-CF-implementation.md` — do not invent one here. This blocks T10's correctness
  gate against real data until that ADR is amended; it does not defer the Causal Forest
  estimator role (D15).
```

## Issue #12 — [T11] Causal Forest Training & Validation

Replace "# Execution location" body:

```markdown
Kaggle-primary governed stage, explicitly multi-session: `scripts/t11_run_stage.py` and
`configs/t11_causal_forest_full.json` / `configs/t11_gcp_parity.json` already implement the
cross-machine/cross-session execution path, with stages connected by explicit immutable
artifacts under `outputs/runs/<run_id>/` rather than shared session state. Public presentation:
consumed by `kaggle/02_uplift_modeling.ipynb` (Issue != notebook — see MASTER #20).
```

Append to "# Frozen rules":

```markdown
- T11 inherits T10's D32 categorical-representation blocker (see Issue #11) — it cannot fit
  against real `f0`–`f11` until Causal Forest's categorical representation is resolved by
  `docs/adr/ADR-CF-implementation.md`. D31's one-shot compute policy is unchanged by D32.
```

## Issue #13 — [T12] Common Validation Model Comparison

Replace "# Execution location" body:

```markdown
Kaggle-primary governed stage. May use one or more Kaggle sessions. Public presentation:
consumed by `kaggle/03_validation_uncertainty.ipynb` (Issue != notebook — see MASTER #20).
```

No further D32 addendum beyond what T07-T11 already carry — T12 consumes their frozen
predictions and does not itself choose a feature representation.

## Issue #14 — [T13] Root-Cause Diagnostics & Stability (conditional)

Replace "# Execution location" body:

```markdown
Kaggle-primary governed stage; conditional on T12 (#13) triggering it. May use one or more
Kaggle sessions. Public presentation: consumed by `kaggle/03_validation_uncertainty.ipynb`
("diagnostics where triggered" — Issue != notebook, see MASTER #20).
```

## Issue #15 — [T14] Uplift Decile & Segment Analysis (P1)

Replace "# Execution location" body:

```markdown
Kaggle-primary governed stage. May use one or more Kaggle sessions. Public presentation:
consumed by `kaggle/03_validation_uncertainty.ipynb` as the optional segment-analysis section
(Issue != notebook — see MASTER #20).
```

## Issue #16 — [T15] Bootstrap Uncertainty & Paired Comparison

Replace "# Execution location" body (keep the existing sentence about the bootstrap/T17 reuse):

```markdown
Kaggle-primary governed stage; may use one or more Kaggle sessions. The bootstrap belongs in
`src/` — T17 reuses [... keep existing continuation unchanged ...]. Public presentation:
consumed by `kaggle/03_validation_uncertainty.ipynb` (Issue != notebook — see MASTER #20).
```

## Issue #17 — [T16] Pre-Test Implementation Freeze

Replace "# Execution location" body:

```markdown
Kaggle-primary governed stage. May use one or more Kaggle sessions. Public presentation:
consumed by `kaggle/04_final_evaluation.ipynb` (Issue != notebook — see MASTER #20).
```

Append to "# Frozen rules" (or wherever the freeze checklist enumerates estimators):

```markdown
- The freeze manifest must record each estimator's D32 feature-representation status
  (continuous/categorical split honored, and for Causal Forest, whether its categorical
  representation blocker from `docs/adr/ADR-CF-implementation.md` is resolved) alongside the
  existing estimator-role/gate evidence.
```

## Issue #18 — [T17] One-Shot Held-out Evaluation

Replace "# Execution location" body (keep "in a single controlled run" if present):

```markdown
Kaggle-primary governed stage, in a single controlled run; may use one or more Kaggle sessions
for setup, but the held-out scoring pass itself is one authorized run per T16 §6. Public
presentation: consumed by `kaggle/04_final_evaluation.ipynb` (Issue != notebook — see MASTER
#20).
```

## Issue #19 — [T18] Final Interpretation, Reproducibility & Defense

Replace "# Execution location" body (keep the "presentation artifact" continuation):

```markdown
Kaggle-primary governed stage — this is also the presentation artifact, so it must read
[... keep existing continuation unchanged ...]. Public presentation: this task *is*
`kaggle/04_final_evaluation.ipynb`'s closing narrative (Issue != notebook — see MASTER #20).
```
