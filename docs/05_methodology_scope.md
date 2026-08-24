# Methodology scope

## Authority and causal alignment

This document derives estimator roles from the owner-approved
[`decision_register.csv`](decision_register.csv). The register controls if this
document conflicts with it; the causal and experiment contracts control causal
and execution details. All methods use the analysis unit and canonical variables in the
[causal contract](01_causal_contract.md): `X` is exactly `f0`–`f11`, `T` is
`treatment`, and `Y` is `conversion`. `visit`, `exposure`, and `_source_row_id`
are never predictors or conditioning variables.

Every uplift score estimates a conditional average contrast. No method produces
an observed true ITE, and empirical PEHE against true ITE is prohibited.

D32 governs how `X` is *represented* to each estimator without changing what
`X` is: four features (`f0`, `f2`, `f7`, `f10`) are continuous and eight
(`f1`, `f3`, `f4`, `f5`, `f6`, `f8`, `f9`, `f11`) are categorical numeric
tokens with no ordinal interpretation. Every estimator below that consumes `X`
must use a representation consistent with that split; a representation is
estimator-specific implementation detail governed by the applicable ADR, not a
change to the estimator's role, formula, or scope in this document.

## Estimator portfolio and status

| Method | Decision status | Role | Score or estimand |
|---|---|---|---|
| Difference in assigned-arm means | **ACCEPTED** | Aggregate assignment-arm estimand/RCT summary; not a ranking estimator or a peer model to the CATE estimators. | `ATE = mean(Y|T=1) - mean(Y|T=0)`. |
| Seeded random ranking | **REQUIRED** | Policy sanity/reference ranking; not a causal estimator. | Seeded uniform random score independent of `X`, `T`, and `Y`. |
| Response model | **REQUIRED** | Non-causal targeting comparator and outcome-prediction diagnostic. It must not be described as an uplift estimator. | `P(Y=1|X)`. |
| T-Learner | **REQUIRED PRIMARY CAUSAL BASELINE** | Two arm-specific outcome surfaces used to estimate CATE ranking. | `mu1_hat(X) - mu0_hat(X)`. |
| X-Learner | **ACCEPTED MAIN COMPARATOR** | Cross-fitted LightGBM meta-learner for CATE ranking under D14 and D18. | Cross-fitted signed pseudo-effects with a regression final stage. |
| S-Learner | **DEFERRED** | Optional future causal comparator; not required, selected, trained, or evaluated for Sprint 1. | A single `m_hat(X,T)` evaluated at `T=1` and `T=0`; `T` is an estimator argument, not part of canonical `X`. |
| DR-Learner | **PROVISIONAL STRETCH COMPARATOR** | Development-only doubly robust comparator. It is excluded from held-out test evaluation unless every promotion gate below passes before freeze. | Cross-fitted doubly robust pseudo-outcome regressed on `X`. |
| Causal Forest | **ACCEPTED MAIN COMPARATOR; SPRINT 2** | The estimator role is accepted. Its exact implementation is **PROVISIONAL** and held-out-ineligible until its ADR gates pass. | Defined by the selected causal-forest implementation without adding `T` to canonical `X`. |

“Required” means the method is part of the applicable frozen comparison if all
HARD_GATE requirements pass. “Accepted main comparator” fixes the estimator
role; an implementation gate may still block held-out entry without silently
deferring the role. “Deferred” means the decision register has deferred the
method. “Provisional stretch comparator” means development work is allowed, but
promotion is forbidden by default.

## Required core methods

### Assigned-arm ATE

The ATE is computed by the exact convention in the
[metric specification](07_metric_specification.md). It is population-average and
does not validate individual ranking quality. It must be reported as an aggregate
estimand/RCT summary, not as a ranking estimator parallel to T-Learner,
X-Learner, or Causal Forest.

### Random ranking

The seeded random ranking is a reproducibility/sanity comparator. The theoretical
expected-random Qini line is the primary random reference; one seeded random
ranking and the predeclared permutation distribution are secondary references.

### Response comparator

The response model uses only `X` to predict `Y`. ROC-AUC, average precision, and
log loss are response diagnostics. Any uplift metric for response ranking
evaluates the policy induced by sorting on response probability; it does not
turn the response model into a CATE estimator.

### T-Learner

The T-Learner fits `mu1_hat(X)` on assigned-treatment rows and `mu0_hat(X)` on
assigned-control rows, with the same base-learner family and frozen configuration
for both surfaces. Predictions are probabilities in `[0,1]`; the un-clipped
contrast lies in `[-1,1]`. Treatment is used to partition arms, never as a member
of `X`.

The base-learner choice is controlled by
[ADR-base-learner](adr/ADR-base-learner.md). Both arm-specific surfaces use
D32 category-aware LightGBM representation (native categorical handling for
the eight categorical features; the four continuous features remain numeric).

### X-Learner

#### Role

**ACCEPTED MAIN_COMPARATOR** under D14. The role is not conditional on
outperforming another estimator; correctness and executable-scale gates control
whether a frozen implementation is eligible for held-out scoring.

#### Inputs

- X: exactly f0–f11, represented per D32 (continuous numeric / categorical
  native representation) for the LightGBM nuisance and effect stages
- T: treatment assignment
- Y: conversion for the primary analysis

Forbidden variables follow the causal and data contracts.

#### Outcome nuisance models

Estimate:

- μ1(x) = E[Y | X=x, T=1]
- μ0(x) = E[Y | X=x, T=0]

The nuisance predictions used to construct training pseudo-outcomes
must be out-of-fold.

#### Imputed treatment effects

For treated observations:

D1 = Y - μ0_hat(X)

For control observations:

D0 = μ1_hat(X) - Y

D1 and D0 are continuous signed targets.

#### Effect models

- Fit τ1(x) on treated observations using D1.
- Fit τ0(x) on control observations using D0.
- Use a regression objective, not a binary classification objective.

#### Combination rule

Primary rule:

τ_hat(x) = g(x)τ0_hat(x) + [1-g(x)]τ1_hat(x)

Primary g(x):

- known assignment probability when supported by design metadata;
- otherwise empirical treatment rate estimated from training data only.

Estimated propensity is diagnostic or sensitivity analysis and must not
be selected using test results.

#### Cross-fitting

- Primary: deterministic two-fold training-only cross-fitting.
- Fold assignment must preserve adequate T×Y support.
- Every training observation must receive out-of-fold nuisance
  predictions.
- Five-fold cross-fitting is a predeclared sensitivity or promotion
  candidate, not an automatic requirement.
- Any D32 categorical representation state (e.g., a learned category
  vocabulary) is fit on a fold's training side only and applied unchanged to
  that fold's out-of-fold side; it never uses that fold's held-out rows.

#### Required tests

- 100% OOF coverage;
- zero fold leakage;
- correct D0/D1 signs;
- regression objective for effect stages;
- finite nuisance, pseudo-outcome and CATE predictions;
- stable observation alignment;
- forbidden variables rejected;
- same score orientation as the metric specification.

#### Validation-only acceptance and configuration rule

X-Learner enters the pre-test shortlist only when:

1. correctness tests pass;
2. the applicable D30 SMOKE→[RESOURCE GATE(S) if required]→FULL scale/resource
   gates pass for the intended run scope, or a documented pre-test amendment
   bounds the executable scope;
3. configuration is selected using validation only from the predeclared
   candidates that passed correctness/resource gates: choose the largest
   `qini_above_random`; differences within the scalar tolerance in document 06
   are ties, resolved by lower declared complexity and then lexicographic
   `config_hash`; top-K metrics are reported guardrails and an
   `UNSUPPORTED_METRIC` blocks only its affected comparison, not silent method
   removal;
4. primary seed `42` is complete and reported. Robustness seeds `123` and
   `2026` (D29, AMENDED_BY_D33) are supporting, non-blocking evidence:
   reported where computationally reasonable, but not a precondition for
   shortlist entry unless X-Learner's implementation specifically requires
   stochastic-stability verification for correctness. A favorable seed is
   never selected;
5. artifacts and manifests are complete;
6. no final-test information has been used.

A finite but unfavorable validation result is reported and does not revoke the
accepted comparator role or authorize omission. A correctness, support, or
resource failure is corrected or handled by a documented pre-test amendment;
test results never change the rule.

#### Required artifacts

Under `outputs/runs/<run_id>/`, retain and hash at least:

- `audit/xlearner_fold_manifest.parquet`;
- `predictions/development/xlearner/seed_<seed>/oof_nuisance.parquet` with OOF
  `mu0` and `mu1`;
- `predictions/development/xlearner/seed_<seed>/pseudo_outcomes.parquet` with
  signed `D0` and `D1`;
- `models/xlearner_<component>.txt` for nuisance and `tau0`/`tau1` effect stages;
- `predictions/development/xlearner/seed_<seed>/validation_predictions.parquet`;
- `tables/validation_selection.csv`;
- `audit/xlearner_correctness.json` and the applicable D30 SMOKE/RESOURCE
  runtime/resource report; and
- after authorized test release, the authoritative prediction path required by
  the experiment-artifact ADR.

`tables/xlearner_deciles.csv` is an optional/P1 (T14) artifact (D33) — useful
segment-level reporting, never a precondition for X-Learner's shortlist entry
or acceptance.

Every artifact records or resolves through the manifest to `run_id`, seed,
split/fold hashes, data/config/code hashes, stage, population, and producer.

#### Prohibited claims

- Do not call τ_hat a true ITE.
- Do not claim X-Learner must outperform T-Learner.
- Do not claim propensity weighting guarantees unbiased individual
  effects.

All correctness, validation, seed, artifact, and scale-gate evidence belongs to
Sprint 2. Sprint 1 freezes this contract and asserts no gate result.
## S-Learner status

The S-Learner is **DEFERRED**, not implicitly required and not equivalent to the
response comparator. A valid S-Learner must fit one outcome model with `T` as an
explicit estimator input and score every row twice, once with `T=1` and once with
`T=0`. The implementation must keep `T` separate from the canonical feature
contract so it cannot leak into methods that accept only `X`.

Promotion in a later phase requires an ADR, synthetic counterfactual tests,
validation-only comparison, deterministic artifact names, and a pre-test freeze
amendment. Until then, the fallback is omission of the S-Learner; the required
T-Learner remains the causal baseline.

## DR-Learner stretch comparator

The DR-Learner is **PROVISIONAL** and development-only. For observation `i`, its
cross-fitted pseudo-outcome is:

```text
psi_i = m1_i - m0_i
        + T_i * (Y_i - m1_i) / e_i
        - (1 - T_i) * (Y_i - m0_i) / (1 - e_i)
```

where `m1_i`, `m0_i`, and `e_i=P(T=1|X)` are predictions from nuisance models
that did not train on row `i`. A final-stage regressor maps `X` to `psi`.

`OPEN_DECISION / PROMOTION_BLOCKER`: choose and document before implementation
whether `e_i` is a known assignment probability or an estimated propensity,
the clipping/support rule, nuisance learners, final-stage loss/learner, and any
sample weights. No choice may be made from held-out test results.

### DR-Learner promotion gate

DR-Learner may enter the frozen held-out comparison only if all conditions pass
using training/validation data before test release:

1. The promotion blocker above is resolved in an ADR or approved amendment.
2. Five-fold cross-fitting, stratified by the joint `T`/`Y` stratum with fold seed
   `42`, is confined to the training partition during selection; no row receives
   a nuisance prediction from a model trained on that row.
3. Synthetic tests verify pseudo-outcome algebra, fold isolation, treatment
   coding, finite predictions, and a known-effect ranking case without asserting
   a result on the real dataset.
4. The primary-seed validation difference `DR-Learner minus T-Learner` in raw
   Qini area has a paired arm-stratified 500-draw percentile 95% interval whose
   lower endpoint is strictly greater than zero.
5. Validation `uplift@10%`, `uplift@20%`, and `uplift@30%` point estimates are
   each no lower for DR-Learner than for T-Learner under the exact shared ranking
   convention.
6. The validation raw-Qini-area difference is positive for each model seed
   `42`, `123`, and `2026`; all seed-specific retraining finishes before freeze.
7. All data, prediction, reproducibility, and artifact HARD_GATE checks pass.

This is a promotion rule, not a claim that the conditions currently pass. If any
condition fails or remains unresolved, the fallback is to exclude DR-Learner from
test scoring and retain T-Learner as the primary causal baseline. A failed DR
promotion does not authorize changing the gate after seeing results.

## Causal Forest main comparator

Causal Forest is an **ACCEPTED MAIN_COMPARATOR** planned for Sprint 2. Causal
Forest itself is not deferred. The exact implementation is **PROVISIONAL** under
[ADR-CF-implementation](adr/ADR-CF-implementation.md) and may enter held-out
evaluation only after its correctness, synthetic-effect, leakage,
honesty/support, resource, validation, seed, and pre-test-freeze gates pass.

Before those gates are evaluated, omission is not an authorized fallback. If a
gate fails, the failure evidence must be retained and a new owner-approved defer
decision must name the concrete failed gates before Causal Forest can be removed
from the planned Sprint 2 portfolio. A Python–R or other cross-language bridge
remains **DEFERRED** unless the implementation ADR proves it is required.

D32 applies to Causal Forest's `X` the same way it applies to every other
estimator, but Causal Forest has no LightGBM-equivalent native categorical
representation. The correctness gate above must therefore reject a raw
`f0`–`f11` frame passed directly as if all twelve columns were continuous.
The concrete categorical representation (encoding scheme and its
memory/runtime cost at the training scale) is an unresolved implementation
decision tracked by [ADR-CF-implementation](adr/ADR-CF-implementation.md); it
is not selected by this document and must not be guessed.

## Cross-fitting policy

- Cross-fitting is **required** for X-Learner and DR-Learner nuisance predictions and nowhere
  may it include held-out test rows.
- Cross-fitting is **not required** for the core response model or T-Learner;
  they use the outer training/validation protocol in document 06.
- S-Learner cross-fitting remains deferred. Causal Forest follows the
  honesty/sample-splitting behavior selected and verified by its provisional ADR;
  that implementation choice does not defer the estimator role.
- Cross-fitting is not a substitute for the outer held-out test partition.

## Robustness and selection boundary

All operations that can alter a fitted model or choose a method occur before the
pre-test freeze on training/validation data: hyperparameter decisions, early
stopping, cross-fitting, repeated-seed retraining, duplicate-policy sensitivity,
and DR promotion. A bootstrap of already-frozen predictions does not retrain a
model, but any development use of it also occurs before freeze.

After freeze, no model may be retrained because of held-out results. The
[experiment protocol](06_experiment_protocol.md) defines the exact sequence.

## Out of scope

- conditioning on `visit` or `exposure`;
- using optional `visit` secondary-outcome results to select models, estimators,
  thresholds, or the primary `conversion` claim;
- optimizing to true ITE or empirical PEHE;
- profit optimization without source-backed economic inputs;
- large hyperparameter searches;
- post-test estimator promotion, tuning, calibration, clipping, or retraining;
- causal claims based only on response-model performance;
- full-data or production deployment claims beyond the contracted population.
