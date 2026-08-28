# Research Memo — Planning Document

Phase 2 deliverable: structure only. No memo prose is drafted here — that is
Phase 3, after this plan is approved.

Source material for everything below:
`notebooks/experiments/conversion_experiment.ipynb`,
`notebooks/experiments/visit_experiment.ipynb`,
`notebooks/reports/comparative_analysis_report.ipynb`, `README.md`, and the
underlying artifacts in `outputs/{conversion,visit}/*/metrics.json` /
`qini_curve.csv`. Every number cited below was read directly from those
files, not estimated.

**Audience for this memo:** ML practitioners, applied researchers, technical
decision makers. This is narrower than the comparative report notebook's own
audience (which also targets non-technical readers) — the memo can assume
familiarity with uplift modeling, Qini/AUUC, and bootstrap confidence
intervals, and should not re-derive them from first principles the way the
notebook's glossary does. It should still state, not assume, which claims the
evidence supports.

---

## 1. Main research question

For which users does treatment (ad exposure) change behavior, and does
estimating that directly (`tau(X)`, via T-Learner/X-Learner/Causal Forest)
out-rank a simpler non-causal targeting baseline (`P(Y|X)`, Response
LightGBM) on held-out ranking quality? The memo evaluates this under two
outcome definitions on the same row partition — `conversion` (primary,
rare) and `visit` (secondary, dense) — to check whether any conclusion
reached under `conversion` is a real effect or an artifact of how few
positive labels that rare outcome gives every estimator to work with.

## 2. Central narrative

Point estimates alone always produce a "winner," so the memo's throughline
is: *what does the point-estimate leaderboard say, and does it survive a
paired bootstrap significance check?* Under `conversion`, Response LightGBM
edges out Causal Forest on point estimates, but the gap is statistically
indistinguishable from noise (CI includes zero on all three checked
metrics) — the primary result is genuinely inconclusive at this sample
size, not a win for either side. Under `visit` — same rows, same
estimators, only a denser outcome column — Causal Forest's point-estimate
lead over Response LightGBM becomes statistically significant on all three
metrics. The narrative is that outcome sparsity, not model choice, is the
binding constraint on what this evidence can support here — not that Causal
Forest is the better model.

## 3. Key findings

| # | Finding | Weight in memo |
|---|---|---|
| 1 | Under `conversion` (primary outcome), Response LightGBM's point estimate leads all three causal estimators, but its gap to the runner-up (Causal Forest) is not statistically distinguishable from resampling noise on any of the three checked metrics | Headline finding — the primary result |
| 2 | Under `visit` (secondary, ~16x denser outcome on the identical test rows), Causal Forest's point-estimate lead over Response LightGBM is statistically significant on all three checked metrics | Headline finding — the contrast that motivates the whole comparison |
| 3 | The same two estimators, the same test rows, the same protocol — only outcome prevalence differs between the two results above | Supporting finding — this is what makes finding 1 "inconclusive" rather than "no effect exists" |
| 4 | T-Learner and X-Learner trail both Response LightGBM and Causal Forest on point estimates in both outcomes | Secondary finding — reported for completeness, not a focus of the discussion |

## 4. Evidence supporting each finding

| Finding | Evidence |
|---|---|
| 1 | `outputs/conversion/baseline/metrics.json`: `test_qini_above_random = 806.23915`; `outputs/conversion/causal_forest/metrics.json`: `769.57579`. Bootstrap: `comparative_analysis_report.ipynb` Section 5 / `BOOTSTRAP_TABLE`, `conversion` rows — Qini gap 95% CI `[-37.85, 117.68]`, AUUC CI `[-42.90, 139.48]`, uplift@10% CI `[-0.00059, 0.00079]`; all include zero |
| 2 | `outputs/visit/causal_forest/metrics.json`: `test_qini_above_random = 6642.20308`; `outputs/visit/baseline/metrics.json`: `6226.73464`. Bootstrap `visit` rows — Qini CI `[-596.53, -252.30]`, AUUC CI `[-678.75, -277.28]`, uplift@10% CI `[-0.01249, -0.00370]`; all exclude zero (gap sign: Response minus Causal Forest, so entirely negative = Causal Forest ahead) |
| 3 | `comparative_analysis_report.ipynb` Section 2: both outcomes computed on the identical seeded 70/15/15 partition (`n_test = 2,096,939` both); `conversion` prevalence `0.2917%` vs. `visit` prevalence `4.6631%` (16.0x) |
| 4 | Table 1 (conversion): T-Learner `qini_above_random = 369.64571`, X-Learner `544.10964`, both below Response (`806.23915`) and Causal Forest (`769.57579`). Table 2 (visit): T-Learner `5653.94009`, X-Learner `5759.00153`, both below Response (`6226.73464`) and Causal Forest (`6642.20308`) |

## 5. Tables to include

| Table | Content | Source |
|---|---|---|
| T1 | Outcome definitions + prevalence/treatment-rate/n comparison (conversion vs. visit) | `comparative_analysis_report.ipynb` Section 2, `outcome_table` |
| T2 | Estimator objective table — Response LightGBM `P(Y\|X)` vs. T-/X-Learner/Causal Forest `tau(X)` | Section 3, `objective_table` / `OBJECTIVE_LABELS` |
| T3 | Model comparison, conversion outcome (qini/auuc above random, uplift@10/20/30/50/100pct) | Section 4, Table 1 |
| T4 | Model comparison, visit outcome (same columns) | Section 4, Table 2 |
| T5 | Bootstrap CI summary (both outcomes x 3 metrics: ci_low, ci_high, conclusion) | Section 5, `BOOTSTRAP_TABLE` |

Decile tables and validation-partition numbers (present in the experiment
notebooks) are not proposed for the memo body — they support the
notebooks' own internal development narrative but are not needed to carry
this memo's argument; mention their existence only in Limitations/pointer
language if at all.

## 6. Figures to include

| Figure | Content | Source | Why it earns a place |
|---|---|---|---|
| F1 | Outcome prevalence bar chart (conversion vs. visit) | Section 2, cell `d36f5c78` | Makes "conversion is rare" visually immediate before any model numbers appear |
| F2 | Qini-above-random bar chart, both outcomes, all models | Section 4, cell `2e1bc9b8` | The point-estimate leaderboard — sets up "but is this real?" |
| F3 | Qini curves, conversion vs. visit side by side | Section 4, cell `3c559c24` | Shows the full ranking, not just one number — the memo should not rely on point estimates alone even visually |
| F4 | Bootstrap forest plot (Response − Causal Forest CI, both outcomes x 3 metrics) | Section 5, cell `74ab5e45` | Carries the memo's central narrative in one image: bars crossing zero under conversion, bars clear of zero under visit |

**Considered and deliberately excluded from the main body:** the AUUC bar
chart and uplift@10% bar chart (cells `ff7a85bc`, `3c01b1a0`) tell
materially the same story as F2 with a different metric weighting — including
all three bar charts would pad the memo without adding a new conclusion.
Reference them in a footnote/appendix pointer for a reader who wants the
other metrics' point estimates, rather than reproducing them as figures.

## 7. Claims to avoid

- "Causal Forest always wins" / "Causal Forest is universally better" —
  visit's result is one outcome, one dataset, one implementation.
- "Visit is a better outcome than conversion" or any framing that could
  read as visit replacing conversion as the business objective — visit is
  a sensitivity check, not a substitute primary result.
- "Causal Forest proves causality" or treating predicted CATE as a
  validated individual treatment effect — both potential outcomes are
  never observed for the same user; no PEHE against ground truth exists.
- "No significant difference" under conversion being read as "the models
  are equivalent" or "causal modeling doesn't help" — absence of a
  statistically distinguishable gap at this sample size is inconclusive,
  not a null result proven.
- "AI found the best customers" or similar marketing framing.
- Any generalization beyond CRITEO-UPLIFTv2.1 / these specific
  implementations / this hyperparameter setting (this is README's own
  explicit scope boundary and should not be loosened in the memo).
- Presenting Table T3/T4 point estimates as sufficient evidence on their
  own, without the paired bootstrap check from T5/F4 alongside them.

## 8. Limitations to highlight

- Offline evaluation only — no online experiment confirms that acting on
  either model's ranking reproduces the measured incremental effect.
- Bootstrap coverage is partial: only Response LightGBM vs. Causal Forest,
  on three metrics, per outcome — not every pairwise model comparison
  (e.g., T-Learner vs. X-Learner) or every metric.
- Causal Forest's categorical representation (`categorical_top_k=8`
  frequency-capped one-hot) is coarser than the LightGBM-based estimators'
  full-cardinality native categorical splits — a real cross-model
  comparability caveat the comparison does not adjust for.
- Not a validated causal mechanism — `f0`–`f11` are anonymized with no
  known business meaning, and predicted CATE describes what the models
  infer, not a ground-truth individual effect.
- Specific to this dataset, these implementations, one hyperparameter
  setting each — conclusions have the form "under outcome A, estimator X
  ranked better than estimator Y *here*," never a universal claim.

---

## Section-by-section plan

| Section | Purpose | Source evidence | Expected reader takeaway |
|---|---|---|---|
| **Title** | Name the comparison precisely enough that "conversion vs. visit, response vs. causal" is legible from the title alone | — | This is a comparative evaluation, not a single-model showcase |
| **Executive Summary** | 3–5 sentences: research question, what was compared, the two headline findings (inconclusive under conversion, significant under visit), and the one-line caveat against overclaiming | Findings 1–2 above | A decision maker who reads only this paragraph has the accurate headline, including its limits, in under a minute |
| **1. Problem and Motivation** | Explain response-model vs. uplift-model distinction (`P(Y\|X)` vs. `tau(X)`) and why ranking by predicted incremental effect is a different question than ranking by predicted likelihood | `comparative_analysis_report.ipynb` Section 1 (Research question), README Research objective | Reader understands why a strong response model is not automatically a strong uplift model, before seeing any numbers |
| **2. Data and Outcome Definitions** | Introduce CRITEO-UPLIFTv2.1, the train/val/test split, and both outcomes with prevalence figures (T1, F1) | Section 2; README Data section | Reader internalizes that conversion is rare (0.29%) and visit is common (4.66%, 16x), and that this asymmetry — not sample size — is the reason visit can resolve what conversion cannot |
| **3. Experimental Design** | Name the four estimators with T2's objective table, state the shared evaluation protocol (Qini above random primary, AUUC secondary, uplift@K, test partition only) | Section 3; README Evaluation design | Reader can place each estimator (baseline vs. three CATE estimators) and knows what "higher" means on the metrics before Results |
| **4. Results — 4.1 Conversion Outcome** | Present T3 + relevant slice of F2/F3 for conversion only; state the point-estimate ranking without yet claiming significance | Section 4, Table 1; qini curve (conversion panel) | Reader sees Response LightGBM point-estimate leads, but is primed (via wording, not yet the bootstrap) not to conclude superiority from this table alone |
| **4. Results — 4.2 Visit Sensitivity Analysis** | Present T4 + visit slice of F2/F3; explicitly frame as a robustness check on the identical rows, not a second primary result | Section 4, Table 2; qini curve (visit panel) | Reader sees Causal Forest's point-estimate lead here, and understands this outcome exists to stress-test conversion's conclusion, not to replace it |
| **5. Statistical Evidence** | Present T5 and F4 (forest plot); state the paired-bootstrap methodology in one paragraph (500 resamples, same resample applied to both models, 95% CI, exclusion of zero as the bar for "real") | Section 5; `src.reporting.paired_bootstrap_gaps` | Reader can independently verify, from the forest plot alone, which of the two headline claims (finding 1 vs. finding 2) is backed by a CI excluding zero and which is not |
| **6. Discussion** | Synthesize why conversion is inconclusive (rare-event variance) and why visit resolves it (denser signal, same rows) into one coherent explanation; briefly address T-/X-Learner's weaker showing without overclaiming a general meta-learner verdict | Sections 6–7 of the comparative report; README Methodology notes (D32, fold-local preprocessing, K=8 tradeoff) | Reader understands *why* the two outcomes diverge statistically, not just *that* they do, and does not walk away with an opinion on meta-learners in general |
| **7. Limitations** | State the five limitations above plainly, each in 1–2 sentences | Comparative report Limitations section | Reader knows exactly what this analysis does not establish before reaching the conclusion |
| **8. Conclusion** | Restate the two headline findings with their evidentiary support, the "not universal" caveat, and one sentence on what a reader should and should not do with this result | Findings 1–2; Claims to avoid | Reader leaves with a calibrated, bounded conclusion — not a "which model wins" takeaway |

---

---

## Reviewer self-check (before drafting)

**1. Is the central narrative scientifically defensible?** Mostly, but it
currently overreaches in one place. "Outcome sparsity, not model choice, is
the binding constraint" is stated as settled fact. It is a reasonable
inference — same rows, same estimators, only prevalence differs, and the
statistical conclusion flips — but it is not the only possible explanation
for why `visit` resolves what `conversion` doesn't (see Attack Point 1
below). The narrative should be phrased as the best-supported explanation,
not the only one.

**2. Are claims separated from evidence?** Yes, structurally — "Key
findings" and "Evidence supporting each finding" are already split into
separate tables, and the per-finding evidence cites exact artifact values
and CIs rather than restating the claim. This separation should carry
through into the actual memo's prose (findings stated, then "see Table/CI
X" — not blended into one sentence).

**3. Are any conclusions too strong?** One: labeling finding 2 (visit
result) a co-equal "headline finding" next to finding 1 (conversion result)
risks the memo reading as "Causal Forest wins" by structural emphasis, even
though the prose correctly hedges it. See Attack Point 5.

**4. Would a skeptical reviewer challenge any statement?** Yes — six
concrete points identified below, not hypothetical ones. Two (Attack Points
1 and 3) do not have a fully satisfying evidence-based answer from what's
already computed; the honest response for those is to add the caveat to the
memo, not to argue it away.

**5. Are conversion and visit roles framed correctly?** Substantially yes —
"visit is a sensitivity check, not a substitute primary result" matches
every source document consistently. One terminology precision issue: see
Attack Point 6.

## Reviewer Attack Points

**1. "You're attributing the conversion/visit divergence to outcome
sparsity — how do you know it isn't that `visit` and `conversion` simply
have different, unrelated treatment-effect structures, and the comparison
is measuring two different things that happen to diverge?"**
- *Why it matters:* the entire central narrative rests on framing `visit`
  as a denser view of "the same underlying difficulty," not a different
  estimation problem. If a reviewer doesn't accept that framing, the
  "sparsity resolved the ambiguity" story collapses into "two unrelated
  results, no lesson connects them."
- *Evidence-based response:* the two outcomes share the exact same test
  rows, features, and estimators (Section 2, `comparative_analysis_report.ipynb`)
  and visit is causally upstream of conversion by construction (every
  conversion is preceded by a visit) — which supports treating them as
  related, not arbitrary. But **no artifact in this project directly
  measures whether visit-CATE rankings correlate with conversion-CATE
  rankings** (e.g., rank correlation between the two outcomes' predicted
  uplift scores). Without that, "denser view of the same problem" is a
  plausible but unverified assumption. **Recommended action for Phase 3:**
  state this explicitly as an assumption, not a proven fact, and add it to
  Limitations rather than asserting it as settled in the Discussion.

**2. "Why did you cherry-pick Response LightGBM vs. Causal Forest for the
bootstrap — did you choose the pairing because it's the most favorable
comparison for whichever model already looks ahead?"**
- *Why it matters:* choosing a comparison pair after seeing which model
  leads is a classic selection-bias / "look elsewhere" critique that would
  undermine the statistical evidence's credibility.
- *Evidence-based response:* verified directly in
  `comparative_analysis_report.ipynb` cell 25/26 — the Response-vs-Causal-Forest
  pairing is **hardcoded identically for both outcomes**, decided in advance
  of and independent of which model leads in either table (Causal Forest is
  runner-up under `conversion` but leads under `visit` — the pairing itself
  never changes). This is a genuine defense against the cherry-picking
  charge for the memo's primary evidence. It does **not** answer the
  narrower question of why Causal Forest specifically (vs. T-/X-Learner) was
  chosen as "the" causal contender in the first place — that rationale
  (most architecturally distinct / most sophisticated estimator, per
  README's Methodology notes) is currently implicit and should be stated
  explicitly in Phase 3's Experimental Design section.

**3. "500 bootstrap resamples — is that enough for a stable 95% CI,
especially for the conversion-outcome intervals whose bounds sit only
moderately far from zero (e.g., Qini CI `[-37.85, 117.68]`)? Would a
different seed meaningfully change whether these exclude zero?"**
- *Why it matters:* if the conversion-outcome "inclusive of zero" result is
  sensitive to resample count or seed, the memo's headline "inconclusive"
  finding is less solid than presented.
- *Evidence-based response:* this cannot be fully answered from what's
  already computed — no seed-sensitivity or resample-count-sensitivity
  check exists in any notebook or artifact. `tests/test_reporting.py`'s
  `test_paired_bootstrap_is_deterministic_given_a_fixed_seed` confirms the
  procedure is deterministic given a seed, which rules out non-reproducibility,
  but says nothing about how much the CI would move under a different seed
  or n_boot. **Recommended action:** do not claim precision beyond what was
  checked; this is a legitimate addition to Limitations rather than a point
  the memo can rebut with existing evidence.

**4. "Are you correcting for testing three metrics per outcome? Could
'significant on all three' under `visit` partly reflect that the three
metrics are correlated, rather than three independent confirmations?"**
- *Why it matters:* uncorrected multiple comparisons can overstate the
  strength of "significant on every metric checked" language.
- *Evidence-based response:* Qini above random, AUUC above random, and
  uplift@10% are constructed from the same ranking and the same
  cumulative outcome sums (`src/evaluation.py`), so they are expected to be
  highly correlated, not independent tests — "three separate confirmations"
  overstates it. The visit-outcome CIs are also far from zero relative to
  their width (e.g., Qini CI `[-596.53, -252.30]`), which is reassuring on
  its own terms, but the memo should describe the three metrics as
  "consistent with each other" rather than "three independent pieces of
  evidence," and should not claim a multiple-comparison correction was
  applied, because none was.

**5. "By presenting the conversion result (inconclusive) and the visit
result (significant) as two co-equal 'headline findings,' doesn't the memo
structurally overweight a secondary sensitivity analysis relative to the
primary business outcome — even if the prose hedges correctly?"**
- *Why it matters:* README and every notebook agree conversion is primary
  and visit is secondary; a memo that gives visit's positive result equal
  visual/structural billing risks readers remembering "Causal Forest won"
  and forgetting it was on the secondary outcome.
- *Evidence-based response:* this is a valid framing risk, not a factual
  error — there is no evidence to "rebut," only a presentation choice to
  fix. **Recommended action for Phase 3:** in the Executive Summary and
  Section 8 (Conclusion), state the conversion result first and as the
  primary takeaway, with the visit result explicitly introduced as *what it
  tells us about the conversion result's reliability* (i.e., "the ambiguity
  under conversion is not evidence of no effect — the same comparison
  becomes resolvable once given denser signal") rather than as a
  free-standing second win.

**6. "Is 'sensitivity analysis' the right term here? A classical
sensitivity analysis perturbs an assumption while holding the estimand
fixed; this instead swaps the outcome variable itself — that's a different
kind of check."**
- *Why it matters:* precise terminology matters for a technical/academic
  reviewer audience; using "sensitivity analysis" loosely invites a
  correction that distracts from the substantive finding.
- *Evidence-based response:* the project's own documents already hedge
  toward "robustness check" in places (`comparative_analysis_report.ipynb`
  Section 1: "a sensitivity/robustness analysis run on the exact same row
  partition"). **Recommended action:** Phase 3 should consistently use
  "robustness check across a related outcome" as the primary description,
  reserving "sensitivity analysis" only if used loosely and defined on
  first use, to preempt this critique rather than trigger it.

## Open questions before drafting (Phase 3)

- Confirm target length: this structure supports either a ~3–4 page memo
  (tables/figures carrying most of the evidentiary weight, prose kept tight)
  or a longer form with more discussion in Section 6. Recommend the shorter
  form given the stated audience and "concise memo, not a notebook export"
  instruction — flag if a longer form is wanted instead.
- Confirm whether Section 4's two subsections should share one combined
  discussion paragraph at the end, or stay fully separate until Section 6 —
  plan above keeps them separate (matching the "sensitivity check, not a
  second primary result" framing) and defers synthesis to Discussion.
