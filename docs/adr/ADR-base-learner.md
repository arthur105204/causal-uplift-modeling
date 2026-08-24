# ADR: Provisional adoption of LightGBM as the default base learner

**Status:** PROVISIONAL  
**Decision authority:** Owner-approved `decision_register.csv` decisions D12,
D13, D14, D17, and D18  
**Sprint 1 assessment:** PASS_WITH_LIMITATION  
**Execution status:** OPEN_FOR_SPRINT2

## Context

The project needs supervised base learners that can operate at the declared
scale, represent nonlinear relationships in numeric covariates, and support
binary factual-outcome modeling. A base learner is not itself a causal
estimator: the causal role comes from the assigned-arm contrast, meta-learner,
forest, or pseudo-outcome architecture defined in
[methodology scope](../05_methodology_scope.md).

Meta-learner performance depends on both the meta-architecture and the base
learner. LightGBM is therefore not assumed to be universally optimal and has not
been shown here to dominate Random Forest, BART, Causal Forest, or another valid
learner family. Sprint 1 contains no comparative execution evidence.

## Provisional implementation decision

D17 owner-approves LightGBM as the selected default base-learner family. This
ADR remains `PROVISIONAL` because it governs the executable adoption of that
family, not because it reopens D17. Use LightGBM only for components whose roles
are already supported by the decision register and document 05:

- the response-model comparator;
- the two factual-outcome surfaces of T-Learner;
- X-Learner factual-outcome nuisance and signed effect-regression stages; and
- DR-Learner nuisance or final stages only if its separate provisional choices
  and promotion gate authorize those stages.

This ADR does not assign LightGBM to Causal Forest, does not change any estimator
role, and does not authorize a held-out comparison. The exact LightGBM package,
configuration, objectives, and serialization behavior remain
`OPEN_FOR_SPRINT2`.

Per D32, `X` is not a uniform numeric block: `f0`, `f2`, `f7`, `f10` are
continuous and `f1`, `f3`, `f4`, `f5`, `f6`, `f8`, `f9`, `f11` are categorical
numeric tokens with no ordinal interpretation. Every LightGBM component listed
above must use LightGBM's native categorical representation for the
categorical group and plain numeric representation for the continuous group;
passing all twelve columns as an undifferentiated continuous/numeric matrix is
not a conforming implementation of this ADR. D17's "12 numeric features"
rationale characterized column count and scale, not per-column semantic type;
D32 is the authoritative semantic characterization.

## Objective contract

- A model trained on factual binary `conversion` or another authorized binary
  factual outcome uses a binary classification objective and produces finite
  probabilities in `[0,1]`.
- A model trained on an X-Learner signed pseudo-effect or DR-Learner
  pseudo-outcome uses a regression objective that accepts continuous negative
  and positive targets.
- An objective cannot be selected from held-out performance or silently reused
  merely because two stages share a learner family.
- Sprint 2 objective tests must verify target type, finite outputs, sign
  convention, out-of-fold construction where required, and rejection of binary
  objectives for continuous pseudo-targets.

## Validation and promotion

Retention or promotion of an exact LightGBM implementation uses development
training and validation only under the
[experiment protocol](../06_experiment_protocol.md). The evidence must cover:

1. the applicable causal-ranking selection or promotion rule;
2. factual-outcome/nuisance diagnostics without interpreting them as causal
   ranking performance;
3. stability across the predeclared seeds;
4. correctness and resource feasibility at the applicable D30 SMOKE/RESOURCE
   scale gates;
5. feature allowlist, row alignment, and absence of fold/test leakage; and
6. serialization and reload behavior under the reproducibility rules in
   document 06.

No test feature, label, prediction, or metric may choose the package,
configuration, objective, iteration count, or hyperparameter.

## Verification gate

Before the pre-test executable freeze, Sprint 2 must produce versioned evidence
that:

- every model receives exactly its authorized inputs and objective;
- every model uses D32 category-aware representation, with any learned
  categorical vocabulary fit on training data only (or a fold's training side
  only, for cross-fitted components) and reused unchanged on the
  corresponding validation/held-out/out-of-fold rows;
- probability and effect outputs satisfy document 03's validity rules;
- X-Learner and any promoted DR-Learner use the required out-of-fold nuisance
  construction;
- development-only early stopping and final refit follow document 06;
- the primary and robustness seeds are complete and not cherry-picked; and
- saved/reloaded models meet the already-specified equality/tolerance policy in
  document 06.

The gate defines future evidence; it asserts no current PASS result.

## Consequences

- Every exact configuration must be explicit, versioned, hashed, and linked to
  its run manifest.
- Hyperparameters are not hard-coded in this ADR and remain
  `OPEN_FOR_SPRINT2`.
- The held-out test cannot be used for hyperparameter selection or learner
  replacement.
- Sharing a base-learner family improves comparability but does not erase
  estimator-specific objectives, nuisances, cross-fitting, or assumptions.
- Failure of an implementation gate is handled before test release and does not
  silently redefine an owner-approved estimator role.

## Status rationale

The owner-approved register locks LightGBM as the default family for the named
model roles. The ADR itself remains **PROVISIONAL** because exact package,
hyperparameters, objective validation, scale behavior, stability, and
serialization evidence have not been produced under the current protocol. This
is `PASS_WITH_LIMITATION` for the Sprint 1 specification and
`OPEN_FOR_SPRINT2` for execution, not a Sprint 1 blocker.
