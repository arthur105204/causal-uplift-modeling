# Table list — captions and metadata

All values reproduced here were re-read directly from
`outputs/{conversion,visit}/*/metrics.json` (and, for the "Random
(reference)" rows, from the executed cell output in
`comparative_analysis_report.ipynb` Section 4, since the random-reference
metrics are computed live each run rather than saved to a JSON artifact).
No number here was retyped from memory or rounded from the memo prose.

---

### Table 1 — `table1_outcome_definitions.csv`
- **Title:** Outcome definitions and test-partition prevalence
- **Purpose:** Establish that conversion (primary) is rare and visit
  (robustness check) is ~16x denser, on the identical test rows
- **Source:** `comparative_analysis_report.ipynb` §2, `outcome_table`
- **Reader takeaway:** The two outcomes are not two unrelated business
  metrics — they are the same population, same partition, different
  outcome columns, with a large prevalence gap between them

### Table 2 — `table2_model_objectives.csv`
- **Title:** Estimator objectives
- **Purpose:** Distinguish the one non-causal baseline from the three
  causal (CATE) estimators before any performance number appears
- **Source:** `comparative_analysis_report.ipynb` §3, `objective_table` /
  `src.reporting.OBJECTIVE_LABELS`
- **Reader takeaway:** A model predicting `P(Y|X)` and a model predicting
  `tau(X)` are answering different questions; a comparison between them is
  a comparison of *approaches*, not just of scores

### Table 3 — `table3_conversion_comparison.csv`
- **Title:** Model comparison, conversion outcome (test partition)
- **Purpose:** Show the point-estimate leaderboard under the primary
  outcome
- **Source:** `comparative_analysis_report.ipynb` §4, Table 1;
  `outputs/conversion/*/metrics.json`
- **Reader takeaway:** Response LightGBM's point estimate leads on every
  metric shown; whether that lead is real is answered in Table 5, not here

### Table 4 — `table4_visit_comparison.csv`
- **Title:** Model comparison, visit outcome (test partition)
- **Purpose:** Show the identical comparison under the denser robustness-check
  outcome, on the same rows
- **Source:** `comparative_analysis_report.ipynb` §4, Table 2;
  `outputs/visit/*/metrics.json`
- **Reader takeaway:** The top-two ordering inverts relative to Table 3 —
  Causal Forest leads here — which is the empirical basis for the memo's
  central question, not a second primary result

### Table 5 — `table5_bootstrap_ci.csv`
- **Title:** Paired bootstrap 95% CI, Response LightGBM minus Causal Forest
- **Purpose:** State, for each outcome and metric, whether the point-estimate
  gap in Tables 3–4 is statistically distinguishable from resampling noise
- **Source:** `comparative_analysis_report.ipynb` §5, `BOOTSTRAP_TABLE`;
  `src.reporting.paired_bootstrap_gaps`
- **Reader takeaway:** This is the table that actually supports the memo's
  conclusion — Tables 3–4 alone cannot; a CI that includes zero (conversion)
  vs. excludes zero (visit) is the entire statistical basis for the memo's
  central claim
