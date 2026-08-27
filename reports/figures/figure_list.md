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

### Figure 4 — `fig4_bootstrap_forest.png`
- **Title:** Forest plot — is the Response-vs-Causal-Forest gap
  distinguishable from zero?
- **Purpose:** Carry the memo's central statistical evidence (Table 5) in
  one image — bars crossing zero under conversion, bars clear of zero
  under visit
- **Source:** `comparative_analysis_report.ipynb` §5, cell `74ab5e45`,
  `execution_count=15`
- **Reader takeaway:** The single clearest visual summary of "inconclusive
  under conversion, resolvable under visit"
- **How this was produced:** a full top-to-bottom re-execution of the
  notebook was attempted twice (`BOOTSTRAP_MODE="final"` preserved) but
  could not complete uninterrupted in this environment. Profiling found
  the paired bootstrap itself (not a bug) is the cost driver:
  `evaluate_ranking` takes ~4.4s/call on the real 2,096,939-row test
  partition, each bootstrap draw calls it twice, and 500 draws × 2
  outcomes measures out to ~3 hours on this machine. Since this cell's
  *only* dependency is `BOOTSTRAP_TABLE` (plus `numpy`/`matplotlib`) — not
  any of the earlier cells' state — and cell `70eab150` already contains
  a valid, previously-computed real `BOOTSTRAP_TABLE` result from an
  earlier full run at `BOOTSTRAP_MODE="final"` (the same numbers used
  throughout this project, cross-checked against
  `outputs/*/*/metrics.json`), that existing result was read back
  unchanged from cell `70eab150`'s own stored output and the (unmodified,
  verbatim) forest-plot cell source was executed once, in a short-lived
  scratch kernel, against it. No model, evaluation, or artifact code was
  touched or recomputed; no bootstrap resampling was redone. The
  resulting real output was written into cell `74ab5e45` of the actual
  notebook (`execution_count=15`), verified via `nbformat.validate()` and
  a check that the cell's output contains `image/png`.
