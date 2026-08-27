# Figure list — captions and metadata

Figures 1–3 were extracted directly from
`notebooks/reports/comparative_analysis_report.ipynb`'s already-executed
cell outputs (read-only extraction — the notebook file itself was not
modified). Figure 4 could not be extracted; see the note below.

---

### Figure 1 — `fig1_outcome_prevalence.png`
- **Title:** Outcome prevalence: conversion vs. visit
- **Purpose:** Make "conversion is rare, visit is common" visually
  immediate before any model result appears
- **Source:** `comparative_analysis_report.ipynb` §2, cell `d36f5c78`
- **Reader takeaway:** The prevalence gap between the two bars is the
  reason visit can resolve what conversion's evidence alone cannot

### Figure 2 — `fig2_qini_bar.png`
- **Title:** Qini above random by model and outcome (test partition)
- **Purpose:** Show the point-estimate leaderboard for both outcomes side
  by side, in one figure
- **Source:** `comparative_analysis_report.ipynb` §4, cell `2e1bc9b8`
- **Reader takeaway:** The ordering of the top two bars (Response
  LightGBM, Causal Forest) visibly inverts between the conversion and
  visit groups — this is the pattern Table 5 / Figure 4 test for
  significance

### Figure 3 — `fig3_qini_curves.png`
- **Title:** Qini curves by model, conversion vs. visit (test partition)
- **Purpose:** Show the full ranking curve, not just the single-number
  summary in Figure 2 — a model can lead on the summary statistic while
  crossing another model's curve over part of the coverage range
- **Source:** `comparative_analysis_report.ipynb` §4, cell `3c559c24`
- **Reader takeaway:** Point estimates alone (Figure 2, Tables 3–4) do not
  fully characterize model ranking behavior; the curve shape matters and
  should be read before trusting a single summary number

### Figure 4 — `fig4_bootstrap_forest.png` — **NOT YET AVAILABLE**
- **Title:** Forest plot — is the Response-vs-Causal-Forest gap
  distinguishable from zero?
- **Purpose:** Carry the memo's central statistical evidence (Table 5) in
  one image — bars crossing zero under conversion, bars clear of zero
  under visit
- **Source:** `comparative_analysis_report.ipynb` §5, cell `74ab5e45`
- **Reader takeaway (intended):** The single clearest visual summary of
  "inconclusive under conversion, resolvable under visit"
- **Why it's missing:** this cell was added to the notebook in a prior
  session and validated only via `nbformat` and a separate temporary
  execution copy — the cell as committed had `execution_count: None` and
  `outputs: []`. A real, in-place re-execution of the full notebook
  (`BOOTSTRAP_MODE="final"` preserved, no artifact regeneration, no model
  training) was launched to fix this. Profiling found the paired
  bootstrap itself (not a bug) is the cost driver: `evaluate_ranking`
  takes ~4.4s/call on the real 2,096,939-row test partition, each
  bootstrap draw calls it twice, and 500 draws × 2 outcomes measures out
  to roughly **~3 hours** on this machine (vs. the notebook's own
  documented "~20 minutes" estimate, evidently calibrated on faster
  hardware). **Action once execution finishes:** re-extract this figure
  from the notebook's now-populated cell output the same way Figures 1–3
  were extracted, and update this entry.
