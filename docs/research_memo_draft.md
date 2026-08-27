# Does Outcome Sparsity Limit Uplift-Ranking Evidence? A Comparative Analysis on CRITEO-UPLIFTv2.1

*Research memo — draft. Sources: `notebooks/reports/comparative_analysis_report.ipynb`,
`notebooks/experiments/conversion_experiment.ipynb`, `notebooks/experiments/visit_experiment.ipynb`,
`README.md`, and `outputs/{conversion,visit}/*/metrics.json`. Every number below is
read directly from those artifacts.*

## Executive Summary

We compare four estimators — a non-causal response model (Response LightGBM,
`P(Y|X)`) and three causal uplift estimators (T-Learner, X-Learner, Causal
Forest, all estimating `tau(X)`) — on their ability to rank users by
incremental treatment effect on **conversion**, the primary business
outcome, using CRITEO-UPLIFTv2.1. Conversion is rare (0.29% prevalence), and
under it, Response LightGBM's point-estimate ranking edges out all three
causal estimators, but a paired bootstrap shows this gap is **not
statistically distinguishable from resampling noise** on any of the three
metrics checked (Qini above random, AUUC above random, uplift@10%). This
result is genuinely inconclusive, not evidence that the causal estimators
fail to add value.

As a robustness check, we repeat the identical comparison on **visit**, a
much denser behavioral outcome (4.66% prevalence, ~16x conversion's rate) on
the *same* test rows. There, Causal Forest's point-estimate lead over
Response LightGBM **is** statistically distinguishable from noise on all
three metrics. Read together, the two results suggest that the ambiguity
under conversion is consistent with an outcome-sparsity limit on this
comparison's statistical power, rather than evidence that no ranking
difference exists between the response baseline and the causal estimators.
This is not a claim that Causal Forest is the better model in general, that
visit substitutes for conversion as the business objective, or that the
bootstrap check establishes a causal mechanism — see Limitations.

## 1. Research Question

An advertiser wants to know for which users an ad *changes* behavior, not
merely which users are likely to act regardless of exposure. Response
LightGBM answers the latter question, `P(Y|X)`, ignoring treatment
entirely. T-Learner, X-Learner, and Causal Forest instead estimate the
conditional average treatment effect, `tau(X) = E[Y(1) - Y(0) | X]`, and
rank users by the effect ad exposure is estimated to have had on them. This
memo asks whether that additional causal machinery produces a measurably
better ranking than the simpler response baseline on held-out data — and
whether any answer to that question is stable across two related but
distinct outcome definitions on the same population.

*Evidence source: `comparative_analysis_report.ipynb` §1; README "Research objective."*

## 2. Data and Outcome Definitions

Both outcomes are evaluated on the identical seeded 70/15/15
train/validation/test partition of CRITEO-UPLIFTv2.1 (`n_test = 2,096,939`);
only which column is read as `Y` differs.

| Outcome | Definition | Prevalence (test) | Treatment rate |
|---|---|---|---|
| `conversion` (primary) | User completes a purchase following ad exposure | 0.2917% | 85% |
| `visit` (robustness check) | User visits the advertiser's site following ad exposure | 4.6631% | 85% |

`visit` is ~16.0x more prevalent than `conversion` on the same rows. Every
conversion is preceded by a visit, so visit sits on the same causal path,
one step upstream. A rarer outcome gives every estimator fewer positive
labels per treatment arm to learn from and to be evaluated against — this
is the basis for treating visit as a check on whether conversion's
conclusions are limited by label sparsity, addressed directly in §5–§6.

*[Figure 1 — outcome prevalence bar chart, conversion vs. visit; source:
`comparative_analysis_report.ipynb` §2, cell `d36f5c78`]*

*Evidence source: `comparative_analysis_report.ipynb` §2, `outcome_table`.*

## 3. Experimental Design

| Estimator | Estimates | Role |
|---|---|---|
| Response LightGBM | `P(Y\|X)` | Non-causal targeting baseline |
| T-Learner | `tau(X)` | Two independent per-arm outcome models, differenced |
| X-Learner | `tau(X)` | Cross-fitted correction of T-Learner's imbalanced-arm bias |
| Causal Forest | `tau(X)` | Honest random forest splitting directly on treatment-effect heterogeneity |

All four are scored on the test partition only (never touched during
fitting or model selection) with **Qini above the theoretical random
reference** as the primary ranking statistic, **AUUC** as a secondary,
differently-weighted view of the same ranking, and **uplift@K** at five
coverage levels.

Section 5's significance check compares **Response LightGBM against Causal
Forest** specifically. This pairing is fixed identically for both outcomes
— it is not chosen after seeing which model leads: Causal Forest is the
runner-up by point estimate under conversion and the leader under visit,
and the same two models are tested either way. Causal Forest is used as the
causal-side comparator (rather than T-/X-Learner) because it is the most
architecturally distinct of the three causal estimators — it splits
directly on treatment-effect heterogeneity rather than differencing two
separately-fit outcome models. T-Learner and X-Learner's point estimates
are reported in §4 for completeness but are not carried into the
significance check.

*Evidence source: `comparative_analysis_report.ipynb` §3, §5; README "Evaluation design," "Methodology notes."*

## 4. Results

### 4.1 Conversion Outcome

| Model | Objective | Qini above random | AUUC above random | uplift@10% |
|---|---|---|---|---|
| Response LightGBM | `P(Y\|X)` | 806.24 | 942.03 | 0.00832 |
| Causal Forest | `tau(X)` | 769.58 | 897.73 | 0.00821 |
| X-Learner | `tau(X)` | 544.11 | 636.21 | 0.00732 |
| T-Learner | `tau(X)` | 369.65 | 430.46 | 0.00634 |
| Random (reference) | — | 47.64 | 56.09 | 0.00117 |

All four models rank users better than random targeting. Response LightGBM
has the highest point estimate on every metric shown; Causal Forest is the
closest causal-model runner-up. Whether this point-estimate gap is real is
addressed in §5, not here — a leaderboard by construction always has a
top row.

*[Figure 2 — Qini-above-random bar chart, both outcomes; Figure 3 — Qini
curve, conversion panel; source: `comparative_analysis_report.ipynb` §4,
cells `2e1bc9b8`, `3c559c24`]*

*Evidence source: `outputs/conversion/{baseline,causal_forest,uplift/xlearner,uplift/tlearner}/metrics.json`; `comparative_analysis_report.ipynb` Table 1.*

### 4.2 Visit Robustness Check

| Model | Objective | Qini above random | AUUC above random | uplift@10% |
|---|---|---|---|---|
| Causal Forest | `tau(X)` | 6642.20 | 7746.52 | 0.06052 |
| Response LightGBM | `P(Y\|X)` | 6226.73 | 7280.12 | 0.05219 |
| X-Learner | `tau(X)` | 5759.00 | 6723.06 | 0.05499 |
| T-Learner | `tau(X)` | 5653.94 | 6591.47 | 0.05592 |
| Random (reference) | — | 186.67 | 219.93 | 0.00976 |

Under visit, Causal Forest's point estimate leads Response LightGBM's on
every metric shown — the ordering of the top two models inverts relative
to §4.1. This table is presented as a check on the conversion result's
reliability, not as a second, independent business finding: visit is not
the outcome the business optimizes for.

*[Figure 2 (visit panel); Figure 3 — Qini curve, visit panel; same source cells as §4.1]*

*Evidence source: `outputs/visit/{baseline,causal_forest,uplift/xlearner,uplift/tlearner}/metrics.json`; `comparative_analysis_report.ipynb` Table 2.*

## 5. Statistical Evidence

A point-estimate leaderboard always produces a "winner," even when two
models are statistically indistinguishable. We use a paired bootstrap
(500 resamples of the test rows with replacement; the same resample index
applied to both models on each draw) to compute a 95% CI on the
**Response LightGBM minus Causal Forest** gap, per outcome, for the three
metrics shown above.

| Outcome | Metric | 95% CI (Response − Causal Forest) | Conclusion |
|---|---|---|---|
| conversion | Qini above random | [−37.85, 117.68] | includes zero |
| conversion | AUUC above random | [−42.90, 139.48] | includes zero |
| conversion | uplift@10% | [−0.00059, 0.00079] | includes zero |
| visit | Qini above random | [−596.53, −252.30] | excludes zero |
| visit | AUUC above random | [−678.75, −277.28] | excludes zero |
| visit | uplift@10% | [−0.01249, −0.00370] | excludes zero |

Under conversion, all three intervals include zero: the data cannot rule
out that the true gap between Response LightGBM and Causal Forest is zero.
Under visit, all three intervals sit entirely below zero, i.e., in Causal
Forest's favor: the observed gap is unlikely to be explained by sampling
variation alone. Because Qini, AUUC, and uplift@10% are constructed from
the same ranking and the same cumulative outcome sums, these three results
should be read as **consistent with one another**, not as three
independent confirmations — no correction for multiple comparisons was
applied, and none was needed to reach that more modest reading.

*[Figure 4 — forest plot of the six CIs above; source: `comparative_analysis_report.ipynb` §5, cell `74ab5e45`]*

*Evidence source: `comparative_analysis_report.ipynb` §5, `BOOTSTRAP_TABLE`; `src.reporting.paired_bootstrap_gaps`.*

## 6. Discussion

The two results, read together, suggest that outcome sparsity — not model
choice — is a plausible binding constraint on what this particular
comparison's statistical power can resolve. The same estimators, fit and
scored the same way, on the same rows, produce an inconclusive gap under a
rare outcome and a resolvable one under a ~16x denser outcome on the
identical partition. This is consistent with a rare-event variance
explanation: conversion gives every estimator very few positive labels per
arm to learn from and to be scored against, which widens the bootstrap CI
regardless of whether a true ranking difference exists underneath it.

This explanation should not be treated as proven. It assumes visit is a
denser view of a related estimation problem, rather than a genuinely
different treatment-effect structure that happens to diverge from
conversion's for unrelated reasons — no artifact in this project directly
measures whether visit-ranked and conversion-ranked uplift scores agree
with each other, so that assumption is unverified (see Limitations). The
conversion result should therefore be read as **inconclusive**, not as
evidence that the causal estimators offer no benefit over the response
baseline: a confidence interval that includes zero is consistent with both
"no real difference" and "a real difference too small or too noisy to
detect at this sample size," and the data here cannot distinguish between
those.

T-Learner and X-Learner trail both Response LightGBM and Causal Forest on
point estimates under both outcomes. This memo does not draw a conclusion
about meta-learner estimators in general from that observation — it is
reported for completeness, and no bootstrap check was run on either of
these two models against the others.

*Evidence source: `comparative_analysis_report.ipynb` §6; README "Methodology notes."*

## 7. Limitations

- **Offline evaluation only.** Qini/AUUC are computed against the
  historical A/B test's logged outcomes; no online experiment confirms
  that acting on either model's ranking would reproduce the measured
  incremental effect.
- **The sparsity explanation in §6 is an inference, not a verified fact.**
  No artifact measures whether visit-ranked and conversion-ranked uplift
  scores are correlated; it remains possible that visit and conversion
  reflect partially different treatment-effect structures rather than one
  problem viewed at two densities.
- **Bootstrap coverage is partial.** Only the Response-LightGBM-vs-Causal-Forest
  gap was tested, on three (correlated) metrics, per outcome — not
  T-Learner vs. X-Learner, nor any other pairwise comparison.
- **Resample-count and seed sensitivity were not checked.** The bootstrap
  procedure is deterministic given a fixed seed, but how much the reported
  CIs — particularly conversion's, whose bounds sit only moderately from
  zero — would shift under a different seed or resample count was not
  tested.
- **Causal Forest's categorical representation is coarser** than the
  LightGBM-based estimators' (frequency-capped top-8 one-hot vs.
  full-cardinality native categorical splits), a memory/runtime tradeoff
  the comparison does not adjust for.
- **Not a validated causal mechanism.** `f0`–`f11` are anonymized with no
  known business meaning, and predicted CATE is not a true individual
  treatment effect — both potential outcomes are never observed for the
  same user, so no PEHE against ground truth is reported. The bootstrap
  establishes statistical distinguishability of a ranking-metric gap; it
  does not establish or validate a causal mechanism.
- **Specific to this dataset, these implementations, one hyperparameter
  setting each.** A valid conclusion has the form "under outcome A,
  estimator X ranked better than estimator Y *here*," not a universal
  claim about either an outcome or a method.

*Evidence source: `comparative_analysis_report.ipynb` "Limitations"; `docs/research_memo_plan.md` Reviewer Attack Points.*

## 8. Conclusion

Under conversion, the primary business outcome, Response LightGBM's
point-estimate ranking lead over Causal Forest is not statistically
distinguishable from resampling noise on any metric checked — the
comparison is inconclusive at this sample size, not a demonstrated win for
either the response baseline or the causal estimators. The visit robustness
check, run on the identical rows with a much denser outcome, provides
evidence that this inconclusiveness is consistent with an outcome-sparsity
limit on statistical power, since the same comparison becomes resolvable
once given a denser signal. This is not a claim that Causal Forest is
universally superior, that visit replaces conversion as the business
objective, or that either result establishes a causal mechanism — see
Limitations for what this evidence does and does not support.

---

## Final Self-Check — Reviewer Attack Points

Carried forward from `docs/research_memo_plan.md`, checked against this
draft specifically:

1. **Sparsity vs. genuinely different effect structure** — addressed: §6
   explicitly states this as an inference and an unverified assumption,
   not settled fact; restated in §7 as a named limitation.
2. **Why Response vs. Causal Forest, and is the pairing cherry-picked** —
   addressed: §3 states the pairing is fixed identically across both
   outcomes (not chosen after seeing which model leads) and gives the
   architectural rationale for Causal Forest as the causal-side
   comparator.
3. **500 resamples — is that enough, and is it seed-sensitive** —
   addressed as an open limitation in §7; no evidence exists to rebut this,
   so the draft does not claim more precision than was checked.
4. **Multiple comparisons across three correlated metrics** — addressed:
   §5 explicitly frames the three metrics as "consistent with one another"
   rather than independent confirmations, and states no correction was
   applied or needed under that framing.
5. **Structural overweighting of the secondary (visit) result** —
   addressed: Executive Summary and §8 both state the conversion result
   first and frame the visit result as informing the conversion result's
   reliability, not as a co-equal second finding.
6. **"Sensitivity analysis" terminology precision** — addressed: this
   draft uses "robustness check" throughout and does not use "sensitivity
   analysis" as a label for the visit comparison.

No new attack points were identified specific to this draft's prose beyond
the six carried forward from the plan; all six have a stated resolution or
an explicit, honestly-flagged limitation above.
