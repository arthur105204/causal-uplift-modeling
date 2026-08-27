# Task 4 — Create Comparative Analysis Report Notebook

## Objective

Create a new reader-first comparative report notebook that synthesizes the completed conversion and visit experiments.

This notebook is NOT an experiment notebook.

It must:
- NOT train models;
- NOT rerun preprocessing;
- NOT modify source code;
- NOT generate new model artifacts;
- ONLY read existing experiment artifacts and produce scientific comparison/reporting.

The purpose is to create the final analysis layer similar to benchmark papers:
experiment notebooks generate evidence;
this notebook interprets evidence.

---

# Context

The repository now contains two independent outcome experiments:

1. Conversion experiment

Path:

outputs/conversion/

Outcome:
conversion

Characteristics:
- very sparse outcome (~0.29%)
- strong imbalance
- Response LightGBM and Causal Forest show comparable ranking performance
- Response point estimate may be higher but bootstrap does not show significant superiority


2. Visit experiment

Path:

outputs/visit/

Outcome:
visit

Characteristics:
- denser outcome (~4.7%)
- higher signal availability
- Causal Forest shows stronger uplift ranking performance


Do not assume results.
Always load values from artifacts.

---

# Create notebook

Create:

notebooks/reports/comparative_analysis_report.ipynb

The notebook should be executable from top to bottom without training.

---

# Notebook structure

Use the following reader-first structure.

---

# 1. Title and Research Question

Markdown:

Explain:

The goal is not to find a universal best model.

The goal is to understand:

"How does outcome definition affect uplift modeling performance and the ability to identify heterogeneous treatment effects?"

Explain that two outcomes are studied:

- conversion
- visit

because outcome sparsity affects causal estimation difficulty.

---

# 2. Artifact Loading

Create code cell.

Load:

outputs/conversion/
outputs/visit/

For each outcome load:

For Response:

baseline/metrics.json
baseline/predictions.parquet
baseline/qini_curve.csv
baseline/uplift_curve.csv


For uplift models:

uplift/tlearner/
uplift/xlearner/


For Causal Forest:

causal_forest/

Load:

metrics.json
predictions.parquet
qini_curve.csv
uplift_curve.csv


Do not hardcode metrics.

Everything must come from files.

---

# 3. Outcome Characteristics Comparison

Create table:

Columns:

Outcome

Sample size

Outcome prevalence

Treatment rate

Control rate


Example:

| Outcome | Prevalence | Treatment rate | Control rate |
|---|---|---|---|
| Conversion | ... | ... | ... |
| Visit | ... | ... | ... |


Add visualization:

bar chart comparing outcome prevalence.

Interpretation markdown:

Observation:
Visit is more frequent than conversion.

Evidence:
Show actual prevalence ratio.

Implication:
Higher event frequency provides more information for estimating treatment-effect heterogeneity.

---

# 4. Model Objective Reminder

Add markdown.

Important:

Do NOT mix objectives.

Explain:

Response LightGBM:

P(Y|X)

Predicts outcome probability.

It is a non-causal targeting baseline.


T-Learner:

tau(X)


X-Learner:

tau(X)


Causal Forest:

tau(X)


Explain:

Qini/AUUC ranking compares ability to prioritize users, but Response and uplift models have different interpretations.

---

# 5. Conversion Experiment Results

Load conversion artifacts.

Create table:

Columns:

Model

Objective

Qini above random

AUUC above random

uplift@10%


Include:

Response LightGBM

T-Learner

X-Learner

Causal Forest


Visualization:

Qini curves.

Important:

Response legend must say:

"Response LightGBM (naive targeting reference)"


Markdown interpretation:

Use:

Observation

Evidence

Interpretation


Required conclusion:

Do NOT say Response wins.

Use:

"Under the sparse conversion outcome, Response LightGBM and Causal Forest achieve comparable ranking performance. The observed difference should be interpreted cautiously because bootstrap uncertainty does not demonstrate statistically significant superiority."


---

# 6. Visit Experiment Results

Same structure.

Load visit artifacts.

Create:

comparison table

Qini curves

uplift@10% comparison


Markdown interpretation:

Observation

Evidence

Interpretation


Required conclusion:

"Under the denser visit outcome, Causal Forest achieves stronger uplift ranking performance, suggesting that increased outcome signal availability improves heterogeneous treatment effect identification."


Do NOT claim statistical superiority unless bootstrap CI excludes zero.

---

# 7. Cross Outcome Comparison

This is the core section.

Create table:

| Outcome | Best point estimate | Bootstrap conclusion | Interpretation |

Do not rank globally.

Explain:

The same model can behave differently depending on outcome definition.


Create visualization:

Grouped bar:

Outcome × Model × Qini

and:

Outcome × Model × uplift@10%


---

# 8. Statistical Evidence

Load bootstrap results if available.

Compare:

Response vs Causal Forest

For each outcome:

Metric:

Qini

AUUC

uplift@10%


Display:

95% confidence interval

Interpretation:

If CI contains zero:

"Difference is not statistically distinguishable."

If CI excludes zero:

"Difference is statistically significant under this bootstrap procedure."


Never use words:
winner
champion
best model

without statistical qualification.

---

# 9. Scientific Discussion

Write markdown.

Required message:

Outcome definition is a major factor in uplift modeling difficulty.

Conversion:

- rare outcome
- noisy estimation
- Response and Causal Forest comparable


Visit:

- denser outcome
- stronger signal
- Causal Forest better captures heterogeneous treatment effects


The conclusion is NOT:

"Causal Forest always wins."

The conclusion is:

"The choice of outcome definition changes the difficulty of the causal estimation problem."

---

# 10. Limitations

Add section:

Mention:

- Criteo observational benchmark characteristics
- binary outcomes
- sample-dependent uncertainty
- only two outcome definitions tested
- results should not be generalized universally


---

# 11. Final Takeaway

Final markdown:

Use wording close to:

"Across experiments, outcome sparsity strongly influences uplift modeling behavior. Sparse conversion outcomes make causal ranking difficult and produce comparable performance between response modeling and causal estimation. When using the denser visit outcome, Causal Forest demonstrates stronger ability to identify heterogeneous treatment effects. Therefore, uplift performance should be interpreted jointly with outcome definition, signal availability, and statistical uncertainty."


---

# Visualization requirements

All figures must:

- have clear titles;
- label Response as:
  "naive targeting reference";
- avoid misleading winner framing;
- include uncertainty notes where appropriate.

---

# Code quality requirements

Do:

- reuse existing evaluation functions if needed;
- reuse artifact paths;
- keep code simple;
- avoid duplicated training logic.


Do NOT:

- import training functions;
- call fit_* functions;
- regenerate predictions;
- modify outputs/.

---

# Validation

After implementation:

Run:

pytest tests -q

Validate notebook:

nbformat.validate()

Execute notebook with existing artifacts.

Confirm:

- zero execution errors;
- no files under outputs/ modified;
- notebook only creates report figures if needed.

Final response should provide:

1. Files created/changed.
2. Notebook structure.
3. Evidence loaded.
4. Validation results.
5. Confirmation no model retraining occurred.