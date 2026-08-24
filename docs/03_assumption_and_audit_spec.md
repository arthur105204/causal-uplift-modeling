# Assumption and audit specification

## Purpose and non-result status

This document defines what must be checked, how evidence is classified, and how
future audit results may be reported. It contains no actual data, audit, model, or
test result. A script's ability to print PASS, FAIL, WARNING, or a narrative does
not establish that result; every result must reference an executed artifact and
run manifest.

The causal assumptions are defined in the
[causal contract](01_causal_contract.md), the schema in the
[data contract](02_data_contract.md), and repeated-value handling in the
[duplicate-profile protocol](04_duplicate_profile_protocol.md).

## Required evidence taxonomy

Each audit item has exactly one primary class:

### HARD_GATE

A deterministic, mechanically verifiable requirement whose failure invalidates
the affected workflow. A failed gate stops before training or evaluation. It may
not be downgraded after inspecting results. A rerun is allowed only after the
cause is corrected and both attempts are retained in the evidence trail.

### EMPIRICAL_DIAGNOSTIC

A measured indication of support, imbalance, instability, or data quality. It
must identify the evaluated population, method, threshold if any, and artifact.
It can trigger investigation or a predeclared scope restriction, but it cannot by
itself prove a causal assumption or justify changing a rule on the final test set.

### ASSUMPTION_SUPPORT_OR_LIMITATION

Design documentation, domain/source evidence, or an irreducible limitation that
cannot be validated from observed columns alone. It is recorded as supported,
unsupported, or limited with a citation and rationale; it is not labeled PASS
merely because an empirical diagnostic looks favorable.

## Audit matrix

No result status is assigned in this matrix.

| ID | Requirement | Class | Required evidence and action |
|---|---|---|---|
| HG-01 | Input identity and lineage | HARD_GATE | Before an executable run, record manifest-selected source/processed paths, SHA-256 checksums, schemas, row counts, conversion configuration and versions. The checksum algorithm and manifest fields are frozen in Sprint 1; actual checksum values are generated in Sprint 2 after the source files are frozen. Missing, ambiguous or unreconciled identity stops the affected run. |
| HG-02 | Required schema | HARD_GATE | Require `f0`–`f11`, `treatment`, and `conversion`; require a non-empty sample; reject an attribution-schema file. |
| HG-03 | Canonical `X/T/Y` | HARD_GATE | Require ordered `X=[f0,...,f11]`, `T=treatment`, and `Y=conversion`. Reject `treatment`, `conversion`, `visit`, `exposure`, `_source_row_id`, or undeclared fields in `X`. |
| HG-04 | Label integrity | HARD_GATE | Require complete `0/1` values for `treatment` and `conversion`; never silently remap or impute labels. |
| HG-05 | Feature type safety | HARD_GATE | Require numeric `f0`–`f11` and reject infinities. Preserve missing feature values for the LightGBM native handling fixed by document 06; do not impute or add missingness features. |
| HG-06 | Arm/outcome support | HARD_GATE | Require both assignment arms globally and the class/arm support needed by each configured train, validation, and evaluation operation. If a required stratum is empty, stop rather than fabricate a metric. |
| HG-07 | Split identity integrity | HARD_GATE | Require complete, unique canonical source-ordinal `_source_row_id` before splitting, pairwise-disjoint identities after splitting, and exact row-accounting reconciliation. Sampling or filtering must not renumber retained observations. |
| HG-08 | Final-test isolation | HARD_GATE | Final-test features, labels, and derived metrics must not select transformations, duplicate policy, thresholds, features, methods, hyperparameters, early stopping, models, ranking rules, or claims. Test labels remain sealed until document 06 authorizes one-time evaluation after a valid freeze. |
| HG-09 | Prediction validity | HARD_GATE | Require equal-length, row-aligned and finite predictions. Probability fields must lie in `[0,1]`. Uplift/CATE scores are continuous signed effect estimates and are not required to be probabilities. Estimator-specific theoretical bounds must be documented; unconstrained effect learners may produce values outside `[-1,1]`, which must be reported and audited rather than silently clipped. Score orientation must be consistent with descending-uplift ranking. |
| HG-10 | Claim validity | HARD_GATE | Do not label predicted uplift as true ITE, do not call equal-value rows duplicate users, and do not report empirical PEHE against unobserved true ITE. |
| ED-01 | Missingness and feature distributions | EMPIRICAL_DIAGNOSTIC | Report counts/fractions and arm-specific distributions on the permitted development population. Do not use final-test patterns to select handling. |
| ED-02 | Treatment/outcome support | EMPIRICAL_DIAGNOSTIC | Report arm and outcome counts/rates for the declared population and split, without hard-coding values in the specification. |
| ED-03 | Covariate balance (D32 continuous features) | EMPIRICAL_DIAGNOSTIC | Applies only to the D32 continuous features `f0`, `f2`, `f7`, `f10`. Report each continuous feature's SMD, maximum absolute SMD across continuous features, variance ratio, and the selected distributional diagnostics defined below. `abs(SMD)=0.10` may be shown only as a conventional literature-reference value, never as a causal-validity or action gate. Calibrate the maximum absolute SMD against the predeclared design-consistent development-data null distribution: at or below its 95th percentile is `INFO`; above its 95th percentile is `WARNING`; above its 99th percentile is `ROBUSTNESS_REQUIRED`. SMD/mean/variance are not computed on D32 categorical features; see ED-03b. |
| ED-03b | Covariate balance (D32 categorical features) | EMPIRICAL_DIAGNOSTIC | Applies only to the D32 categorical features `f1`, `f3`, `f4`, `f5`, `f6`, `f8`, `f9`, `f11`. Report a per-feature category-distribution diagnostic such as total variation distance between arms, `TVD = 0.5 * sum_c abs(P(X=c\|T=1) - P(X=c\|T=0))`, together with category count and missing counts by arm. Categorical numeric tokens are never given an SMD, mean, or variance interpretation, and are never combined with ED-03 via `max()` across the two families — they are different quantities on different scales. `OPEN_DECISION / BLOCKED_PENDING_MIXED_TYPE_SPEC`: no null-calibrated action threshold (a categorical analog of the ED-03 95th/99th percentile mapping) is defined here; this document does not invent one. Report TVD as `INFO`-only evidence until a future decision adopts a calibrated threshold. |
| ED-04 | Treatment predictability | EMPIRICAL_DIAGNOSTIC | Report out-of-fold ROC-AUC and log loss from the fixed `X→T` classifier pipeline below, fit with D32 category-aware representation (categorical features passed through the estimator's native categorical handling, not as raw continuous tokens). Rerun the complete pipeline under each design-consistent null assignment and calibrate the high-direction statistics against their null distributions: at or below the 95th percentile is `INFO`; above the 95th percentile is `WARNING`; above the 99th percentile is `ROBUSTNESS_REQUIRED`. High predictability is an investigation signal; low predictability does not prove randomization. Accuracy is not an accepted substitute. |
| ED-05 | Observable arm support and overlap | EMPIRICAL_DIAGNOSTIC | Observable arm support is primary. Zero treated or zero control rows globally is `STOP`; missing arm support required by a training or cross-fitting fold is `STOP` for that fit; zero treated or zero control rows in a subgroup or top-K set is `UNSUPPORTED_METRIC` for that estimate. Report local arm counts, outcome counts, treatment fractions, cross-fitted propensity summaries, and sparse-region mass. Fixed propensity bands, clipping, or trimming are not primary population gates. Any trimming is a separately declared sensitivity estimand because it changes the target population. |
| ED-06 | Duplicate profiles and origin | EMPIRICAL_DIAGNOSTIC | Apply every named definition and source/precision comparison in document 04. Do not infer duplicated people. |
| ED-07 | Reproducibility | EMPIRICAL_DIAGNOSTIC | Re-run deterministic data selection/splitting with the declared environment and seeds; compare manifests and canonical source-ordinal identities. Cross-run equivalence is valid only when the canonical raw checksum also matches. |
| ASL-01 | Assignment mechanism/exchangeability | ASSUMPTION_SUPPORT_OR_LIMITATION | Cite publisher or experiment documentation for randomization, allocation, exclusions, and deviations. Balance/predictability diagnostics are supporting signals only. |
| ASL-02 | Feature timing | ASSUMPTION_SUPPORT_OR_LIMITATION | Cite source definitions showing all `f0`–`f11` precede assignment. Until then their pre-treatment status is `PROVISIONAL`. |
| ASL-03 | `visit`/`exposure` timing | ASSUMPTION_SUPPORT_OR_LIMITATION | Cite their definitions and timestamps. `visit` may be a D02 secondary outcome but cannot enter `X`, replace primary `Y=conversion`, select a model, or condition the primary population/effect. `exposure` remains audit-only and cannot replace assignment or condition the primary effect. |
| ASL-04 | Consistency/treatment versions | ASSUMPTION_SUPPORT_OR_LIMITATION | Document what treatment assignment means and whether relevant versions or noncompliance exist. |
| ASL-05 | No interference | ASSUMPTION_SUPPORT_OR_LIMITATION | Document design support and the limitation caused by absent public user/network identity. |
| ASL-06 | Outcome definition/measurement | ASSUMPTION_SUPPORT_OR_LIMITATION | Cite conversion definition, attribution/observation window, censoring, and missing-outcome behavior. |
| ASL-07 | External validity | ASSUMPTION_SUPPORT_OR_LIMITATION | State that anonymous covariates and unresolved source sampling constrain transport beyond represented eligible rows. |
| ASL-08 | Fundamental causal observability | ASSUMPTION_SUPPORT_OR_LIMITATION | Only one potential outcome is observed per row; true ITE and empirical PEHE against it are unavailable. |

The SMD, treatment-predictability, and propensity summaries are diagnostics, not
causal-identification theorems. Sprint 1 freezes their derivation algorithms and
evidence requirements, not universal numerical cutoffs. The generated null
percentiles are Sprint 2 development artifacts and must be finalized before the
pre-test executable freeze without held-out-test access.

## Design-calibrated diagnostic protocol

### Shared randomization reference

ED-03 and ED-04, and any contextual calibration reported for ED-05, use one
predeclared development-only assignment reference:

1. If the exact assignment mechanism is available, simulate assignments from
   that mechanism while preserving its documented probabilities, blocks,
   strata, clusters, and arm-count constraints.
2. If it is unavailable, conditionally permute treatment labels while preserving
   the observed development arm count and every documented design block or
   stratum. The manifest must label this reference
   `CONDITIONAL_PERMUTATION_APPROXIMATION`; it must not be presented as the true
   assignment mechanism.
3. Keep rows, `X`, outcomes, preprocessing, folds algorithm, model configuration,
   and scoring code fixed. Generate an initial `2,000` null assignments from
   master seed `42`; derive and store a deterministic sub-seed for every
   replication. Increasing the replication count is allowed only to reduce
   Monte Carlo uncertainty, must use a predeclared continuation of the same seed
   stream, and cannot depend on the observed diagnostic's desirability.
4. For each generated 95th and 99th percentile, report the order statistic,
   replication count, exceedance count, and a 95% Monte Carlo interval obtained
   from the binomial/order-statistic method. Do not hide an unstable tail
   estimate; increase replications or retain the uncertainty as a limitation
   before freezing the generated thresholds.

The calibration configuration is fixed before computing the observed
development diagnostic. Its record must include the assignment mechanism or
approximation, conditioning variables, population and split hashes, classifier
and fold configuration, master and replication seeds, replication count, Monte
Carlo method and interval, generated threshold values, code revision, package
environment, and SHA-256 hashes for every configuration, draw, threshold, and
summary artifact.

Within `outputs/runs/<run_id>/`, the required calibration artifacts are:

- `audit/randomization_calibration/config.json`;
- `audit/randomization_calibration/null_draws.parquet`;
- `audit/randomization_calibration/thresholds.json`; and
- `audit/randomization_calibration/manifest.json`.

These artifacts contain no held-out rows or held-out-derived values.

### ED-03 calculation and action mapping

ED-03 applies only to the D32 continuous features `f0`, `f2`, `f7`, `f10`. For
each, compute the treated-minus-control SMD using the pooled within-arm
standard deviation. Report the sign and absolute value. Use the feature's
non-missing observations within each arm, report both denominators and
missingness by arm, and do not impute for this diagnostic. Explicitly report
zero-denominator or undefined cases rather than coercing them. Define the
variance ratio as treated-arm variance divided by control-arm variance and
report undefined/zero-denominator cases. Also report arm quantiles at
`{0.01,0.05,0.25,0.50,0.75,0.95,0.99}`, quantile differences, and the empirical
CDF/KS distance. The maximum absolute SMD (over the four continuous features
only) is the predeclared operational summary for null calibration; the
remaining measures diagnose scale, tail, and shape differences that a
mean-standardized statistic can miss.

A feature-level SMD/mean/variance computation must fail closed if invoked on a
D32 categorical feature — see ED-03b.

### ED-03b calculation and action mapping

ED-03b applies only to the D32 categorical features `f1`, `f3`, `f4`, `f5`,
`f6`, `f8`, `f9`, `f11`. For each, using non-missing observations within each
arm, report the per-category proportion in the treated and control arms, the
total variation distance `TVD = 0.5 * sum_c abs(P(X=c|T=1) - P(X=c|T=0))`, the
maximum single-category proportion gap, the observed category count, and
missing counts by arm. Do not impute for this diagnostic; report
zero-denominator or undefined cases explicitly. Category tokens are never
ranked, averaged, or treated as ordinal for this computation.

`OPEN_DECISION / BLOCKED_PENDING_MIXED_TYPE_SPEC`: unlike ED-03, no
null-calibrated 95th/99th-percentile action mapping is defined for ED-03b in
this document, and none is invented here. Until a future owner-approved
decision adopts one, report TVD and the accompanying counts as contextual
`INFO` evidence only, and do not combine ED-03 and ED-03b into a single joint
statistic (for example, do not take `max()` across SMD and TVD — they are
different quantities on different scales).

The conventional reference line `|SMD|=0.10` may appear in plots and tables only
with the label `LITERATURE_REFERENCE_NOT_GATE`. It does not override the
design-calibrated disposition:

| Observed maximum absolute SMD | `evidence_status` | `required_action` |
|---|---|---|
| At or below the generated 95th null percentile | `INFO` | `PASS` |
| Above the 95th and at or below the 99th null percentile | `WARNING` | `WARNING`; inspect feature-level, tail, split, and leakage evidence |
| Above the 99th null percentile | `MATERIAL_CONCERN` | `ROBUSTNESS_REQUIRED`; execute the predeclared balance/support sensitivity before promotion |

### ED-04 calculation and action mapping

The treatment-predictability diagnostic uses exactly `X=[f0,...,f11]` and a
fixed, hashed LightGBM binary-classifier configuration with native
missing-value handling and D32 category-aware representation: the four
continuous features are passed as numeric, and the eight categorical features
use LightGBM's native categorical handling rather than raw numeric tokens.
It uses five-fold treatment-stratified cross-fitting, fold seed `42`,
out-of-fold predictions for every evaluated row, and no tuning or early stopping.
The classifier configuration, feature order, folds algorithm, and scoring code
are locked before the observed diagnostic and reused unchanged. Each null
replication reruns the full fold construction, fitting, prediction, and scoring
pipeline under that replication's treatment assignment.

Report ROC-AUC and log loss, together with the constant-probability log loss
computed from training-fold treatment prevalence. For action calibration use two
high-direction statistics: ROC-AUC and
`log_loss_gain = constant_log_loss - cross_fitted_log_loss`. Compare each with
its own null distribution and take the more severe predeclared disposition:

| Null-relative statistic | `evidence_status` | `required_action` |
|---|---|---|
| Both at or below their generated 95th null percentiles | `INFO` | `PASS` |
| Either above its 95th and neither above its 99th null percentile | `WARNING` | `WARNING`; investigate leakage, split construction, and local imbalance |
| Either above its 99th null percentile | `MATERIAL_CONCERN` | `ROBUSTNESS_REQUIRED`; execute the predeclared assignment/balance sensitivity before promotion |

No fixed ROC-AUC cutoff is permitted. A high null-relative result indicates that
`X` predicts the recorded assignments more strongly than expected under the
declared reference; it does not identify the cause. A low result can reflect a
weak classifier or limited power and does not prove randomization.

### ED-05 observable support protocol

Before any propensity summary, report global, split, fold, subgroup, and each
top-K set's treated/control row counts, treatment fractions, and treated/control
outcome counts. Apply these primary rules:

- zero global support for either arm: `STOP` the causal workflow;
- missing required arm support in a training or cross-fitting fold: `STOP` that
  fit and rebuild or amend the pre-test design without test information; and
- zero treated or zero control rows in a subgroup or top-K set:
  `UNSUPPORTED_METRIC` for that local estimate, with no smoothing, borrowing,
  or fabricated replacement.

Fit propensity summaries out of fold on development data using the same frozen
classifier-pipeline discipline as ED-04. Report distribution quantiles by arm
and overall, calibration summaries, and the mass and arm/outcome counts in
predeclared sparse regions. A sparse region is an estimator-defined reporting
cell, tree leaf, subgroup, or top-K set whose local arm count is below the
minimum required by that estimator's frozen fitting or metric rule; it is not
defined by a universal propensity interval. Null-relative propensity summaries
may be reported as contextual `INFO`, `WARNING`, or `ROBUSTNESS_REQUIRED`
evidence using the same generated 95th/99th-percentile convention, but they do
not supersede the observable-support rules or exclude rows from the primary
population.

No fixed propensity interval, clipping, or trimming is a primary population
gate. If clipping is required inside a conditional estimator, its value and
effect are estimator-specific promotion evidence. Any trimmed analysis must
declare a separate sensitivity population and estimand, selection rule, retained
mass, and interpretation before execution; it cannot replace the primary
eligible-population estimand after results are seen.

## Diagnostic rationale and evidence table

| Failure mode | Selected metric | Alternative metrics | Supporting primary literature | Applicability and limitations | Threshold derivation method | Required action | Calibration artifact |
|---|---|---|---|---|---|---|---|
| Marginal covariate imbalance inconsistent with the declared design (D32 continuous features only: `f0`,`f2`,`f7`,`f10`) | Per-feature signed/absolute SMD and maximum absolute SMD; variance ratios and ECDF/quantile diagnostics are always co-reported | Mahalanobis balance, higher-moment contrasts, graphical balance checks | [Austin (2009)](https://pubmed.ncbi.nlm.nih.gov/19757444/); [Hansen and Bowers (2008)](https://projecteuclid.org/journals/statistical-science/volume-23/issue-2/Covariate-Balance-in-Simple-Stratified-and-Clustered-Comparative-Studies/10.1214/08-STS254.full) | SMD is scale-stable and descriptive, but neither a favorable SMD nor the conventional `0.10` reference proves assignment validity; the maximum statistic is multiplicity-aware only through the simulated design reference; not meaningful on categorical numeric tokens, so it is not applied to the eight D32 categorical features | Empirical 95th/99th percentiles of maximum absolute SMD under the shared design-consistent null, with Monte Carlo intervals | `PASS`/`WARNING`/`ROBUSTNESS_REQUIRED` according to the mapping above | `audit/randomization_calibration/thresholds.json` plus `null_draws.parquet` |
| Marginal category-distribution imbalance inconsistent with the declared design (D32 categorical features only: `f1`,`f3`,`f4`,`f5`,`f6`,`f8`,`f9`,`f11`) | Per-feature total variation distance (TVD) between arms; category count and missing counts by arm are co-reported | Chi-squared/G-test of independence, Jensen-Shannon divergence | [Austin (2009)](https://pubmed.ncbi.nlm.nih.gov/19757444/) (general balance-diagnostic framing; not specific to token categoricals) | TVD does not assume ordinal structure and does not treat category tokens as numeric magnitude; no null-calibrated action threshold is defined yet | `OPEN_DECISION / BLOCKED_PENDING_MIXED_TYPE_SPEC`: not yet derived; this document does not invent one | `INFO`-only until a future decision adopts a calibrated threshold | Reported alongside the ED-03 calibration artifacts; no dedicated artifact name is frozen yet |
| Multivariate treatment predictability inconsistent with the declared design | Cross-fitted ROC-AUC and log-loss gain from a fixed classifier pipeline | Classification accuracy, Brier score, multivariate mean tests, energy/MMD tests | [Gagnon-Bartsch and Shem-Tov (2016)](https://arxiv.org/abs/1611.06408); [Hansen and Bowers (2008)](https://projecteuclid.org/journals/statistical-science/volume-23/issue-2/Covariate-Balance-in-Simple-Stratified-and-Clustered-Comparative-Studies/10.1214/08-STS254.full) | Can detect nonlinear joint predictability, but depends on classifier power and implementation; low predictability is not proof of randomization | Rerun the full cross-fitted pipeline for each null assignment; use each statistic's generated 95th/99th percentiles and the more severe result | `PASS`/`WARNING`/`ROBUSTNESS_REQUIRED`; investigate before promotion when elevated | Same four randomization-calibration artifacts, including classifier/fold hashes |
| Missing or sparse observable arm support for a requested fit or local estimate | Global/fold/local arm and outcome counts, treatment fractions, cross-fitted propensity summaries, sparse-region mass | Fixed propensity bands, effective sample size, density ratios, trimming rules | [Crump et al. (2009)](https://academic.oup.com/biomet/article-abstract/96/1/187/235329) | Counts directly establish whether the requested comparison is observable. Propensity summaries are model-dependent; trimming changes the target population and therefore cannot be a silent primary fix | Deterministic count gates are primary; any contextual continuous diagnostic uses the shared design-reference percentiles, not universal propensity bands | `STOP` for global/required-fold failure; `UNSUPPORTED_METRIC` for an unsupported subgroup/top-K estimate; contextual escalation otherwise | Support tables in the audit artifact plus the randomization-calibration manifest when contextual calibration is used |

## Audit ordering

1. Freeze the intended input and create the lineage manifest.
2. Run HG-01 through HG-07 before any model fit.
3. Freeze the development-only calibration method in Sprint 1; in Sprint 2,
   generate and hash its null thresholds on development data before the pre-test
   executable freeze.
4. Run ED-01 through ED-07 only on populations permitted by the
   [experiment protocol](06_experiment_protocol.md).
5. Record ASL-01 through ASL-08 with citations and explicit limitations.
6. Resolve or bound hard-gate failures and material diagnostics before
   the affected estimator is promoted and before the Sprint 2 pre-test
   executable freeze.
7. Keep final-test data sealed until all upstream choices and the release
procedure are fixed.

No later favorable result can retroactively validate a failed gate or an
unsupported assumption.

## Reporting contract

Each executed audit row must record:

- audit ID and evidence class;
- run ID, timestamp, code revision if available, environment, and command;
- input manifest/checksums and evaluated population/split;
- method, parameters, predeclared threshold, and units;
- artifact path and machine-readable result;
- `evidence_status`:
  - HARD_GATE: `PASS` or `FAIL`;
  - EMPIRICAL_DIAGNOSTIC: `INFO`, `WARNING` or `MATERIAL_CONCERN`;
  - ASSUMPTION_SUPPORT_OR_LIMITATION:
    `SUPPORTED`, `UNSUPPORTED` or `LIMITED`;
- `required_action`:
  `PASS`, `WARNING`, `ROBUSTNESS_REQUIRED`, `STOP`,
  `LIMITATION` or `UNSUPPORTED_METRIC`;
- interpretation and unresolved-decision ID.

`evidence_status` and `required_action` are separate machine-readable fields.
The former records what the evidence shows under its evidence class; the latter
records what the project must do. Neither field may be inferred from the other
without applying the predeclared rule for that audit ID.

Hard-coded prose such as “verified,” “corrected,” or “no issue” is prohibited
unless it is generated from and links to the same run's evidence. Smoke tests and
row-limited checks must be labeled as such and cannot support full-data
conclusions.

## Test-set protection

Schema-only checks that do not reveal distributions may be applied to a sealed
test artifact when operationally necessary. All label access, distribution
inspection, duplicate-policy selection, model comparison, uncertainty analysis,
and metric interpretation on the final test set are prohibited until the
experiment protocol authorizes evaluation. After release, test findings are
reported; they do not trigger tuning or a replacement “final” model on the same
test set.

Document 06 defines custody, permitted opaque/schema checks, release authority,
and what consumes the test set. Its pre-test freeze is a HARD_GATE.

## Action taxonomy
| Action | Meaning |
|---|---|
| PASS | Check completed and no material issue identified |
| WARNING | Diagnostic concern; report and inspect, but do not automatically stop |
| ROBUSTNESS_REQUIRED | Primary analysis may continue, but a specified sensitivity analysis is mandatory |
| STOP | Hard data-integrity or leakage failure; model training/evaluation must stop |
| LIMITATION | Assumption cannot be fully verified and must constrain interpretation |
| UNSUPPORTED_METRIC | Required treatment/control or outcome support is absent for the affected local population or top-K segment; report the support failure and do not fabricate, smooth, or silently replace that metric. |

## Frozen project action rules

These rules map evidence to `required_action`. They are specification defaults;
their execution evidence belongs to Sprint 2.

| Check | Frozen condition | Required action |
|---|---|---|
| Schema and feature allowlist | Required schema missing, undeclared input present, or model `X` differs from ordered `f0`–`f11`. | `STOP` the affected pipeline. |
| Forbidden variables | `treatment`, active outcome, `visit`, `exposure`, `_source_row_id`, or another undeclared field enters canonical `X`. | `STOP`; correct the feature builder and rerun before training. |
| Binary/missing `T` and active `Y` | `T` or the active outcome is missing, remapped, imputed, or outside `{0,1}`. | `STOP` the affected outcome pipeline. Failure of optional `visit` disables that separate secondary pipeline and does not redefine primary `Y=conversion`. |
| Source-row overlap | A `_source_row_id` occurs in more than one outer split or row accounting does not reconcile. | `STOP`; rebuild and re-freeze the split. |
| Fold leakage | A row's nuisance prediction comes from a model trained on that row, or a test row enters a training fold. | `STOP` the affected estimator; rebuild fold membership and all dependent pseudo-outcomes. |
| Row alignment | Prediction length, order, or observation identity fails one-to-one reconciliation with its declared population. | `STOP`; positional repair or silent reordering is forbidden. |
| Independent ATE reconciliation | Independent assigned-arm calculations agree within the scalar tolerance in document 06. | `PASS`; a difference above tolerance is `STOP` until the formula, population, or alignment error is resolved. |
| Covariate balance (D32 continuous features) | Maximum absolute SMD at/below the generated design-null 95th percentile, above the 95th through the 99th, or above the 99th. | `INFO` evidence with `PASS`, `WARNING`, or `MATERIAL_CONCERN` evidence with `ROBUSTNESS_REQUIRED`, respectively. The conventional `abs(SMD)=0.10` line is reference-only. |
| Covariate balance (D32 categorical features) | Per-feature TVD and category-distribution summary reported; no calibrated action threshold defined. | `INFO`-only; `OPEN_DECISION / BLOCKED_PENDING_MIXED_TYPE_SPEC` for any escalation rule until a future decision adopts one. Never combined with the continuous-feature SMD result via `max()`. |
| `X→T` predictability | Cross-fitted ROC-AUC and log-loss gain are each compared with their generated full-pipeline null distributions. | At/below both 95th percentiles: `INFO` evidence with `PASS`; either above its 95th: `WARNING`; either above its 99th: `MATERIAL_CONCERN` with `ROBUSTNESS_REQUIRED`. |
| Observable/local support | Either global arm count is zero; a required fit/fold lacks an arm; or a subgroup/top-K set lacks an arm. | `STOP` globally, `STOP` the affected fit, or `UNSUPPORTED_METRIC` for the affected local estimate, respectively. Cross-fitted propensity summaries and sparse-region mass are reported without a universal interval gate. |
| No local arm support | A local region or top-K set has no treated or no control rows. | `UNSUPPORTED_METRIC` for the affected estimate; do not smooth, borrow, or fabricate it. |
| Top-K converter support | Both arms exist but either arm has zero converters in the selected set. | `WARNING` and explicit low-event support reporting; if the required statistic or interval is undefined, use `UNSUPPORTED_METRIC`. |
| Profile repetition | Equal values or repeated `f0`–`f11` profiles occur within a split. | `WARNING`; retain rows in the primary population. Cross-split feature-profile repetition additionally triggers the predeclared grouped-profile sensitivity via `ROBUSTNESS_REQUIRED`, but is not row leakage unless source IDs overlap. |
| Consistency and treatment versions | Source/design evidence is absent, partial, or identifies multiple unresolved versions. | `LIMITATION`; empirical diagnostics cannot upgrade it to causal proof. |
| No interference | Source/design evidence is absent or row dependence cannot be assessed. | `LIMITATION`; retain the restricted claim scope. |
| External validity | Claims extend beyond eligible released CRITEO-UPLIFTv2.1 rows or supported covariate regions without transport evidence. | `LIMITATION`; prohibit the unsupported transport claim. |

SMD, AUC/log-loss, and propensity summaries use project reporting/action rules,
not causal-identification theorems. Their design-null derivation algorithm is
frozen here. Sprint 2-generated threshold values and Monte Carlo uncertainty
must be recorded in the calibration manifest before the pre-test executable
freeze and cannot be revised after test access.
