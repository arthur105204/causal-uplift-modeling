# ADR: Causal Forest implementation

**Status:** PROVISIONAL  
**Role:** MAIN_COMPARATOR  
**Planned sprint:** Sprint 2  
**Decision authority:** Owner-approved authoritative decision_register.csv

## Governing decisions

The owner-approved `decision_register.csv` controls this ADR:

- D10 accepts comparative uplift/CATE evaluation covering T-Learner,
  X-Learner, Causal Forest, and DR-Learner.
- D15 accepts Causal Forest's estimator role as a **MAIN_COMPARATOR** and makes
  selection of its exact implementation provisional through this ADR.
- D22 defers any Python–R or other cross-language bridge unless this ADR proves
  that it is required after Python options are evaluated.
- D30 requires `SMOKE → [RESOURCE GATE(S) if required] → FULL`; Causal Forest's
  materially greater complexity and resource risk relative to the already-
  validated Response/T-Learner/X-Learner paths means it requires SMOKE followed
  by one or more predeclared RESOURCE gates before FULL (superseded from the
  prior fixed `D23` 50K→500K→2M→full progression, superseded 2026-08-18).

This ADR implements those accepted decisions. It does not defer, omit, or
redefine Causal Forest itself. Causal Forest remains planned for Sprint 2 and is
not part of Sprint 1 model execution.

## Provisional implementation decision

Select the exact Causal Forest implementation during Sprint 2 using the criteria
and gates below. Until selection and promotion complete, the estimator is
planned but **not yet eligible for held-out evaluation**. This is an
implementation status, not a defer decision for the estimator role.

The implementation must not be described as an exact Wager–Athey estimator
unless its library, objective, honesty, inference, and support behavior justify
that claim.

## Categorical representation blocker (D32)

Per D32, `f1`, `f3`, `f4`, `f5`, `f6`, `f8`, `f9`, `f11` are categorical
numeric tokens with no ordinal interpretation; `f0`, `f2`, `f7`, `f10` are
continuous. Unlike LightGBM (`ADR-base-learner.md`), the qualifying
econml-family Causal Forest implementations have no built-in native
categorical representation equivalent to LightGBM's. Passing raw `f0`–`f11`
directly into `fit_causal_forest()` as an undifferentiated continuous/numeric
matrix is not a conforming implementation of this ADR and must fail closed
with an explicit error rather than proceed.

`OPEN_DECISION / IMPLEMENTATION_BLOCKER`: the concrete categorical
representation for Causal Forest (e.g., one-hot, ordinal, hashing, or target
encoding) is not selected here. This ADR does not invent one. A candidate
representation must be proposed as an explicit amendment to this ADR — not
assumed from the official Criteo benchmark's own preprocessing, which is
evidence about their benchmark, not automatic authorization for this
project's econml usage — and must document its correctness, honesty/support
compatibility, and memory/runtime cost at the ~9.8M-row training scale before
it can be exercised at any RESOURCE gate or FULL run. Until resolved, Causal
Forest fitting against real (non-synthetic-encoded) `f0`–`f11` input remains
blocked; this blocks gate progression, not the accepted `MAIN_COMPARATOR`
role.

## Implementation-selection criteria

The Sprint 2 selection record must compare maintained Python implementations
first and document:

1. treatment-effect rather than response-prediction semantics;
2. support for honest/sample-split forest construction and explicit treatment
   and outcome inputs without adding `T` to canonical `X`;
3. treatment/control support checks, nuisance behavior, weighting, and any
   variance or interval estimates actually claimed;
4. deterministic seeds, parallelism controls, serialization, reload equivalence,
   and exact prediction/artifact schemas;
5. compatibility with the D32 continuous/categorical `f0`–`f11` split (not a
   uniform numeric matrix), missing-value policy, source-row identity, and the
   frozen train/validation/test boundary;
6. feasibility at the applicable D30 SMOKE, RESOURCE gate(s), and full-data
   scale gates; and
7. license, maintenance, runtime, peak memory, and integration cost.

A Python–R or other cross-language bridge remains **DEFERRED**. It may be
proposed only if the comparison above demonstrates a required correctness,
honesty, or inference capability unavailable from qualifying Python options and
also proves row alignment and serialization across the boundary. Bridge
convenience or benchmark performance alone is insufficient.

## Promotion gates

Causal Forest may enter held-out evaluation only after all gates have been
evaluated and documented using synthetic or permitted development data before
test release:

1. **Correctness gate:** pin implementation/version/configuration and verify the
   exact `X/T/Y` contract, treatment coding, finite CATE scores, metric input
   schema, and the D32 categorical representation blocker above (raw
   undifferentiated `f0`–`f11` input is rejected, not silently accepted).
2. **Synthetic-effect gate:** recover direction/ranking on known positive,
   negative, zero, and heterogeneous-effect fixtures within predeclared
   tolerances; do not treat these fixtures as real-data results.
3. **Leakage gate:** prove that held-out test rows and labels enter neither
   fitting nor selection and that no row is used in an out-of-fold role that its
   selected algorithm forbids.
4. **Honesty/support gate:** verify the selected honesty/sample-splitting rule,
   treatment/control support, minimum leaf/arm behavior, nuisance handling, and
   any claimed variance/interval semantics.
5. **Resource gate(s):** pass a predeclared D30 `SMOKE → one or more RESOURCE
   gates → FULL` progression for correctness, runtime, and peak memory. Given
   Causal Forest's stronger resource-risk profile, this ADR requires at least
   one RESOURCE gate before FULL (never zero, unlike a simpler validated
   estimator); the exact number and workload size of RESOURCE gates is resolved
   in the Causal Forest CODE PLAN before execution, not selected after observing
   model performance. No gate, however many are declared, can select the final
   comparator from held-out performance.
6. **Validation gate:** compare against the frozen T-Learner and X-Learner using
   validation-only metrics and a promotion rule approved before the comparison.
   No held-out test value may influence promotion.
7. **Seed gate:** complete and report the configured `42`, `123`, and `2026`
   development retraining without choosing the most favorable seed. Per D31,
   under a declared one-shot resource constraint this development retraining
   occurs at a single predeclared bounded development scale common to all
   three seeds -- `500,000` rows, deterministic joint-`(T,Y)`-stratified,
   sampled with seed `42`, scored on the complete frozen validation cohort --
   rather than the full development population; the bounded scale and
   rationale are recorded in the task's config before execution, not selected
   after observing results.
8. **Pre-test-freeze gate:** serialize and reload the chosen model, freeze exact
   artifacts/configuration/seeds/claims, attach every gate result, and include
   the estimator in `pretest_freeze.json` before any test access.

No gate is asserted to have passed by this ADR.

## Fallback after documented gate failure

Before the gates are evaluated, omission is not an authorized fallback: Causal
Forest remains a planned Sprint 2 main comparator.

If a gate fails, retain the failure evidence and either correct the
implementation and repeat only pre-test gates or request a new owner-approved
decision. Exclusion or deferral is permitted only when that new decision names
the concrete failed gates, scope, decision authority, and next disposition. Without such a
decision, Causal Forest remains blocked from held-out evaluation but is not
silently removed from the planned comparator portfolio.

## Consequences

- The accepted estimator role is distinct from the provisional implementation.
- No current model, audit, validation, resource, or held-out result is claimed.
- Unevaluated gates prevent test promotion but do not block Sprint 1
  specification freeze or convert the estimator role to DEFERRED.
