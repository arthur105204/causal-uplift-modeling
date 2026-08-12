# Causal contract

## Contract status

This document is the source of truth for the causal question, notation,
estimands, identification requirements, and permissible claims. It defines no
audit result and does not authorize model training or final-test evaluation.

## Decision problem

For an eligible observation with pre-treatment covariates `X`, rank or select it
according to the expected change in conversion caused by assigning treatment.
This differs from ranking by the probability of conversion irrespective of
treatment.

The analysis unit is one public-dataset row. The row must not be described as a
unique user: no durable public user identifier exists in the active analytical
schema. The primary empirical unit and eligible population are locked below.
Definition of a different external deployment unit is **DEFERRED** and is
required only before making deployment or transport claims beyond the released
population.

## Canonical variables

| Role | Definition | Permitted use |
|---|---|---|
| `X` | exactly the ordered fields `f0` through `f11` | Model inputs and pre-treatment stratification/diagnostics only. |
| `T` | binary `treatment`, with `T=1` treated and `T=0` control | Treatment assignment, causal contrasts, and treatment-arm partitioning. Never a feature. |
| `Y` | binary `conversion` | Primary outcome. Never a feature. |
| `visit` | optional binary secondary outcome | Secondary robustness outcome under D02 when present and schema-valid; never `X`, `T`, primary `Y=conversion`, a selection condition, or an analysis-population filter. |
| `exposure` | optional audit-only observed field | Descriptive audit only; never `X`, a replacement for `T`, `Y`, a selection condition, or an analysis-population filter. |
| `_source_row_id` | zero-based ordinal of the row in the checksum-identified canonical decompressed CSV | Provenance, split integrity, deterministic tie-breaking, and artifact alignment only; never a person identifier or feature. |

`PROVISIONAL`: repository narratives classify `visit` and `exposure` as
post-assignment variables. Until source documentation confirms their semantics
and timestamps, the conservative prohibitions above control. Treating `visit`
as a secondary outcome does not permit using it as a predictor, selection rule,
or population filter. Analyses conditioned on actual exposure would generally
target a post-assignment subset and do not identify the same intention-to-treat
contrast.

## Potential outcomes and estimands

For row `i`:

- `Y_i(1)` is the potential conversion under treatment assignment.
- `Y_i(0)` is the potential conversion under control assignment.
- The individual treatment effect is `Y_i(1) - Y_i(0)`, but it is never observed
  for a row because only one treatment state is realized.
- The average treatment effect is `ATE = E[Y(1) - Y(0)]` over the specified
  analysis population.
- The conditional average treatment effect is
  `tau(x) = E[Y(1) - Y(0) | X=x]`.

The primary ranking estimand is `tau(x)` for the manifest-selected analysis
population, and the population ATE is a secondary summary. This estimator role is
hard-frozen. The eligible population is all released CRITEO-UPLIFTv2.1 rows that
pass the predeclared hard data-integrity gates in the primary eligibility
contract below. External transport claims remain out of scope until separately
justified.

A model score such as `tau_hat(x) = mu1_hat(x) - mu0_hat(x)` is an estimate of a
conditional average contrast. It must be called predicted uplift or estimated
CATE, not a true ITE.

## Treatment and estimand interpretation

The working causal contrast uses `treatment` as assignment. It does not replace
assignment with realized `exposure`, does not restrict to exposed rows, and does
not adjust for `visit` or `exposure`. This is the repository's conservative
intention-to-treat orientation.

`ASSUMPTION_SUPPORT_OR_LIMITATION`: randomized assignment is asserted in existing
repository narratives but lacks a primary-source citation in the documentation.
Until the assignment mechanism and deviations from assignment are sourced, causal
identification is conditional on that design claim rather than established by the
observed data.

## Identification requirements

The [audit specification](03_assumption_and_audit_spec.md) classifies evidence
for each requirement.

1. **Consistency and treatment versions.** Observed `conversion` equals the
   potential outcome under the row's recorded assignment, and relevant versions
   of treatment are well defined. This is
   **ASSUMPTION_SUPPORT_OR_LIMITATION**.
2. **Exchangeability.** Assignment is independent of potential outcomes, either
   by documented randomization or by a justified conditional argument. This is
   **ASSUMPTION_SUPPORT_OR_LIMITATION**; balance and treatment-predictability
   checks are only **EMPIRICAL_DIAGNOSTIC** support.
3. **Positivity/overlap.** Both assignment arms occur in relevant feature
   regions. Global arm presence is a **HARD_GATE**; local overlap is an
   **EMPIRICAL_DIAGNOSTIC** and may limit the supported target population.
4. **Pre-treatment covariates.** Every field in `X` precedes assignment and is not
   caused by treatment. Source-backed timing is
   **ASSUMPTION_SUPPORT_OR_LIMITATION**; exact feature-list enforcement is a
   **HARD_GATE**.
5. **No interference.** One row's assignment does not affect another row's
   outcome. This is **ASSUMPTION_SUPPORT_OR_LIMITATION**, made especially
   uncertain by the absence of a public user or network identifier.
6. **Outcome observability.** `conversion` is consistently defined and observed
   over a suitable window. This is **ASSUMPTION_SUPPORT_OR_LIMITATION** plus
   schema/label **HARD_GATE** checks.

No empirical balance, propensity, duplicate, or predictive-performance result
can prove these assumptions.

## Permissible and prohibited claims

Permissible, conditional on the assumptions and metric protocol:

- population or subgroup average differences between assigned arms;
- predicted uplift/CATE rankings;
- randomized-arm outcome contrasts within predeclared ranked groups;
- predeclared secondary `visit` outcome summaries that do not alter primary
  model selection or the `conversion` conclusion;
- explicit limitations where identification or support is weak.

Prohibited:

- calling predicted uplift a true individual effect;
- claiming that an observed row is a unique person;
- reporting empirical PEHE against true ITE on this dataset;
- interpreting response-model ROC-AUC, average precision, or log loss as causal
  ranking quality;
- conditioning the primary effect or population on `visit` or `exposure`;
- claiming exchangeability, overlap, SUTVA, or feature timing was “proved” by an
  audit;
- using final-test outcomes or metrics to choose any upstream rule or model.

## Evaluation boundary

The final test partition is for one-time evaluation under the
[experiment protocol](06_experiment_protocol.md). Its labels and derived metrics
must not influence feature processing, duplicate policy, diagnostic thresholds,
method choice, hyperparameters, early stopping, model selection, ranking policy,
or claim thresholds. Validation data, not test data, is the development feedback
source.

Documents 05 through 07 now specify the estimator-to-metric mapping, uncertainty
procedure, pre-test freeze, and one-time test-release sequence. Their unresolved
items explicitly labeled as blockers must be closed before final evaluation.

## Primary eligibility and target population

### Unit of analysis

The unit of analysis is one released observation/row in
CRITEO-UPLIFTv2.1.

A released row is not assumed to represent a unique user, household or
persistent advertising identity.

### Primary eligible population

The primary eligible population contains all released observations that
pass the hard data-integrity gates defined in the data contract:

- the required schema is present;
- X consists exactly of f0–f11;
- treatment and the active outcome are observed and binary;
- all required model inputs satisfy the missing/non-finite policy;
- a stable observation identity can be established;
- the observation belongs to exactly one frozen split;
- no forbidden or post-treatment variable is included in X.

### Primary exclusions

Exclude an observation only when it fails a predeclared hard
data-integrity gate.

Do not exclude observations merely because:

- the same f0–f11 profile appears elsewhere;
- the row is an exact value duplicate;
- its estimated CATE is extreme;
- it belongs to a feature tail;
- its observed outcome is rare;
- removing it improves model performance.

Exact-row deduplication and grouped-profile analysis are sensitivity
analyses, not the primary population.

### Target population

The target population for the primary empirical claims is the eligible
released CRITEO-UPLIFTv2.1 population under its observed assignment and
covariate support.

The study does not automatically generalize to:

- unique users;
- other campaigns;
- other platforms;
- other time periods;
- other treatment policies;
- populations outside the released covariate support.

### Outcome-specific populations

The primary conversion analysis and the secondary visit analysis use separate
outcome pipelines, contracts, predictions, metrics, and artifacts.

`visit` is never used as a feature in the conversion analysis.
