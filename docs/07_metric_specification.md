# Metric specification

## Authority and scope

This document is the source of truth for Sprint 1 metric names, formulas, units,
ranking construction, edge cases, uncertainty, and permissible interpretation.
It defines no actual value or result.

The owner-approved [`decision_register.csv`](decision_register.csv) controls
metric and estimator-role decisions if a lower-precedence summary conflicts.

Metrics are computed separately for the declared `validation` or held-out `test`
population. Test metrics are available only after the release procedure in the
[experiment protocol](06_experiment_protocol.md). No metric changes the
[causal contract](01_causal_contract.md): predicted uplift is not true ITE, and
empirical PEHE against true ITE is unavailable.

## Notation

For an evaluation population of `N` rows:

- `T_i` is binary `treatment` assignment.
- `Y_i` is binary `conversion`.
- `s_i` is the frozen ranking score for one method.
- `N1`, `N0` are treated/control row counts.
- `Y1`, `Y0` are treated/control conversion counts.
- `p1=Y1/N1` and `p0=Y0/N0` when denominators are positive.

All rates and effects are stored in raw probability units. A displayed percentage
point value is exactly `100 * raw_probability_value` and is labeled `_pp` or
`percentage_points`.

## Common ranking convention

Every ranking metric uses the same deterministic order:

1. sort `s_i` descending;
2. break score ties by `_source_row_id` ascending;
3. assign one-based rank `r=1,...,N`.

`_source_row_id` affects only deterministic ordering and is never a model
feature. A missing/non-unique identity or non-finite score is a HARD_GATE failure.
Methods are compared on exactly the same rows.

Scores and labels are not clipped, smoothed, or jittered to improve metrics. The
seeded random method uses a uniform score generated with seed `42`; the
theoretical expected-random line remains the primary random reference.

## ATE

For the declared population:

```text
ate = p1 - p0
se = sqrt(p1*(1-p1)/N1 + p0*(1-p0)/N0)
ci_95_low  = ate - 1.96*se
ci_95_high = ate + 1.96*se
ate_percentage_points = 100*ate
relative_lift = ate/p0, only when p0 > 0
```

This is the unpooled normal difference-in-proportions interval. If either arm is
empty, ATE is undefined and evaluation fails. If `p0=0`, `relative_lift` is `NA`,
not infinity or zero. No continuity correction is applied.

Before test release, ATE may be reported for training plus validation only. The
primary held-out ATE uses test rows only after release; a full-sample ATE that
mixes development and test is not a substitute.

ATE is an aggregate estimand/RCT summary. It has no row-level ranking score and
must not be listed as a ranking estimator parallel to T-Learner, X-Learner, or
Causal Forest.

## Response-prediction diagnostics

These apply to `response_score=P_hat(Y=1|X)` and are not uplift metrics:

- **ROC-AUC:** probability that a randomly chosen converter has a higher score
  than a randomly chosen non-converter, with tied pairs contributing `0.5`.
- **Average precision:** the non-interpolated step integral
  `sum_n (recall_n - recall_(n-1))*precision_n` over decreasing thresholds.
- **Log loss:** mean binary negative log likelihood. Only for numerical
  evaluation of the logarithm, probabilities are bounded to
  `[1e-15, 1-1e-15]`; stored model scores remain unmodified.

Both outcome classes are required. Validation diagnostics may guide development;
test diagnostics are reported once and cannot trigger tuning.

## Decile uplift

Require `N >= 10`. With rank `r`, assign:

```text
decile(r) = 1 + floor(10*(r-1)/N)
```

This yields deciles `1` through `10`, with decile 1 containing the highest scores
and group sizes differing by at most one under the deterministic rank rule.

For each decile `b`, let `n1_b`, `n0_b`, `y1_b`, and `y0_b` be arm row/conversion
counts. Define:

```text
treatment_conversion_rate_b = y1_b/n1_b
control_conversion_rate_b   = y0_b/n0_b
observed_uplift_b = treatment_conversion_rate_b
                    - control_conversion_rate_b
estimated_incremental_conversions_b = n_b * observed_uplift_b
```

If either arm denominator is zero, the rates, uplift, and incremental conversion
estimate are `NA`. No pseudocount or borrowing across deciles is allowed. Fewer
than five control conversions in a decile produces an EMPIRICAL_DIAGNOSTIC
warning, not an alternative formula.

## Uplift at K

The fixed coverage grid is `K={0.10,0.20,0.30,0.50,1.00}`. For coverage `k`,
select the first:

```text
m_k = min(N, max(1, ceil(k*N)))
```

ranked rows. With counts `n1_k`, `n0_k`, `y1_k`, and `y0_k` in that set:

```text
uplift_at_k = y1_k/n1_k - y0_k/n0_k
incremental_conversions_at_k = m_k * uplift_at_k
```

`uplift_at_k` is stored in probability units; incremental conversions are
estimated conversion-count units. If either arm is absent, both values are `NA`
and comparison at that coverage is blocked. No interpolation or smoothing is
used. At `K=1.00`, all ranking methods select the same population.

## Cumulative uplift and gain

At every prefix `r`, calculate cumulative arm counts/conversions. For prefixes
with both arms present:

```text
cumulative_uplift_rate(r) = cum_y1(r)/cum_n1(r)
                            - cum_y0(r)/cum_n0(r)
cumulative_incremental_conversions(r) = r*cumulative_uplift_rate(r)
coverage(r) = r/N
```

Prefixes missing an arm have undefined rate/gain and are omitted rather than set
to zero. These cumulative incremental conversions are distinct from Qini gain.
For stored and plotted cumulative curves, apply the same 151-position selection
rule defined below to valid prefix rows; retain the final prefix and do not prepend
an artificial origin to a rate curve.

## Raw Qini gain and area

For every ranked prefix with `cum_n0(r)>0`:

```text
qini_gain(r) = cum_y1(r)
               - cum_y0(r)*cum_n1(r)/cum_n0(r)
coverage(r) = r/N
```

Qini gain has estimated incremental-conversion-count units. Prefixes with zero
cumulative controls are skipped. The point `(coverage=0, qini_gain=0)` is
prepended, and the full-population endpoint is retained.

### Curve grid

The scalar and plotted raw Qini curve use the same frozen 151-point convention:

1. calculate all valid ranked-prefix points;
2. if at most 151 are valid, keep all;
3. otherwise take 151 unique integer positions obtained by rounding
   `linspace(0, L-1, 151)` over the `L` valid points, retaining first and last;
4. prepend the origin; and
5. integrate the retained points by the trapezoidal rule over coverage.

Thus:

```text
qini_area = sum_j 0.5*(Q_j + Q_(j-1))*(c_j - c_(j-1))
```

The unit is incremental conversions times population fraction. This is an
unnormalized raw Qini area; it is not ROC-AUC, AUUC, a normalized Qini
coefficient, or PEHE.

### Expected-random comparison

Let `Q_full` be the full-population Qini gain. The theoretical expected-random
curve is the line:

```text
Q_random(c) = c*Q_full
theoretical_random_qini_area = Q_full/2
qini_above_random = qini_area - theoretical_random_qini_area
```

`qini_above_random` is the **primary ranking statistic**. Higher is better.
Because every method shares the same evaluation population and random-line area,
pairwise method differences in `qini_above_random` equal pairwise raw-Qini-area
differences.

One seeded random permutation is an illustrative method. Additionally, exactly
200 seeded random permutations produce a reference distribution. Its mean and
percentiles are secondary EMPIRICAL_DIAGNOSTIC context; neither replaces the
theoretical expected-random line.

## Model-comparison summary

For each method and stage, `model_summary.csv` contains at least:

- `qini_area`;
- `theoretical_random_qini_area`;
- `qini_above_random`;
- `qini_above_random_permutation` for the single seeded random ranking reference;
- `uplift_at_10pct`, `uplift_at_20pct`, `uplift_at_30pct`;
- `incremental_conversions_at_10pct`, `_20pct`, `_30pct`;
- `run_id`, `stage`, `population`, `ranking_method`, and units/version fields.

The accepted comparison reports Random, Response, T-Learner, and X-Learner for
the applicable frozen portfolio. DR-Learner appears on held-out test only if its
validation promotion gate passed before freeze. Causal Forest is an accepted
Sprint 2 `MAIN_COMPARATOR`, but its exact implementation must pass every gate in
its ADR before held-out entry. S-Learner is deferred.

Validation selection uses `qini_above_random` as primary and the three fixed
top-K uplift estimates as guardrails. DR promotion uses the exact stricter rule
in [methodology scope](05_methodology_scope.md); no visual curve judgment or
test metric may override it.

## Secondary `visit` outcome

When `visit` is present, binary, and frozen before development under D02,
compute its assigned-arm mean difference and the same fixed ranking summaries
using already-frozen primary-method rankings. Store and label these results as
secondary `visit` outcomes. They cannot select a model, promote an estimator,
change a threshold, redefine `Y=conversion`, or replace any primary conversion
metric. No visit-based retraining is permitted after pre-test freeze.

## Ranking uncertainty

Use exactly 500 paired, treatment-arm-stratified bootstrap draws for each
predeclared comparison:

1. sample treated row indices with replacement within the treated arm;
2. independently sample control row indices with replacement within the control
   arm;
3. apply the same draw/multiplicity to every compared method so comparisons are
   paired;
4. keep model scores fixed and do not retrain; and
5. recompute raw Qini area and fixed top-K metrics using the common ranking rules.

The 95% interval is the `2.5%` and `97.5%` empirical percentile interval using
linear quantile interpolation. Report the point estimate, interval, number of
finite draws, total draws, stage, and seed. A draw with an undefined denominator
for a required metric is excluded for that metric and counted; if fewer than 95%
of draws are finite, that interval is `NA` and comparison is blocked.

The bootstrap quantifies row-sampling uncertainty conditional on fixed fitted
models and the evaluation population. It does not include model-training,
hyperparameter, split, or dataset uncertainty. Seed retraining is a separate
pre-freeze robustness analysis under document 06.

## Edge-case and failure rules

- Empty evaluation population, missing arm, non-binary label, non-finite score,
  or mismatched prediction length is a HARD_GATE failure.
- Missing treatment/control denominator within a decile or top-K set yields `NA`,
  never zero or infinity.
- Ties use `_source_row_id`; random jitter is forbidden.
- `uplift_score` is not clipped. Probability scores must remain in `[0,1]`.
- Negative uplift, incremental conversions, Qini gain, or area are valid values
  and are not truncated.
- A small positive point difference is not “superiority” without the applicable
  predeclared interval/promotion rule.
- Test uncertainty is reported after release and never triggers retraining.

## Terminology and units

| Term | Required meaning | Unit |
|---|---|---|
| ATE / observed uplift | Assigned-treatment outcome mean minus assigned-control outcome mean. | Probability; optionally labeled percentage points after multiplying by 100. |
| Predicted uplift / estimated CATE score | Model-based contrast used for ranking; not true ITE. | Probability contrast. |
| Incremental conversions | Selected row count times observed uplift rate. | Estimated conversion count. |
| Raw Qini gain | Arm-size-adjusted cumulative treated conversions minus control reference. | Estimated incremental conversion count. |
| Raw Qini area | Trapezoidal area under raw Qini gain over coverage. | Incremental conversions times population fraction. |
| Qini above random | Raw Qini area minus theoretical expected-random line area. | Same as raw Qini area. |
| ROC-AUC / average precision / log loss | Response-prediction diagnostics only. | Unitless. |

D25 records the curve-metric family as “AUUC/raw Qini”; this specification
implements that accepted decision with the exact unnormalized **raw Qini**
formula above. To avoid an ambiguous second formula, do not label this value
“AUUC,” “normalized Qini,” “Qini coefficient,” “uplift AUC,” “ITE accuracy,” or
“PEHE.” A different formula requires a versioned metric-spec amendment and, when
it changes an accepted decision, owner approval before test release.

## Metric artifacts

Exact filenames are controlled by
[ADR-experiment-artifacts](adr/ADR-experiment-artifacts.md). The required
machine-readable metric-definition artifact is
`outputs/audit/metric_definitions.csv`, containing formula version, inputs,
units, direction, edge-case behavior, curve points, coverages, seeds, and
uncertainty convention. It must match this document before freeze.
