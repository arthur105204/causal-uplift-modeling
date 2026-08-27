# Research Artifact Audit and Refactoring Plan

## Context

This repository contains a causal uplift modeling benchmark inspired by:

Diemert et al.
"A Large Scale Benchmark for Individual Treatment Effect Prediction and Uplift Modeling"

The project currently contains:

- source code:
  - src/models.py
  - src/evaluation.py
  - src/preprocessing.py
  - src/artifacts.py

- experiment notebooks:
  - notebooks/experiments/01_conversion_experiment.ipynb
  - notebooks/experiments/02_visit_sensitivity_experiment.ipynb

- report notebook:
  - notebooks/reports/03_comparative_analysis_report.ipynb


The project has two experimental outcomes:

1. conversion
- sparse outcome
- strong class imbalance
- primary difficult uplift estimation scenario

2. visit
- denser outcome
- sensitivity analysis inspired by Criteo benchmark practice
- expected to provide stronger signal for ITE estimation


Important:
Do NOT change model implementation.
Do NOT tune hyperparameters.
Do NOT change evaluation methodology.

Only improve:
- experiment correctness
- notebook structure
- scientific interpretation
- reporting quality
- reproducibility.

---

# Phase 1 — Complete Read-only audit first

Before modifying anything:

Read:

- README.md
- configs/config.yaml
- src/*
- tests/*
- all experiment notebooks
- report notebook
- outputs/conversion/*
- outputs/visit/*

Inspect:

- all markdown cells
- all code cells
- stored outputs
- figures
- printed results


Produce an audit report:

## A. Notebook correctness

Verify:

01_conversion_experiment.ipynb

must contain:

OUTCOME = "conversion"


02_visit_sensitivity_experiment.ipynb

must contain:

OUTCOME = "visit"


Check:

- artifact paths
- output folders
- metrics.json
- model comparison tables


Detect:

- duplicated notebook
- wrong outcome parameter
- stale copied cells
- incorrect titles


---

# Phase 2 — Scientific narrative audit


Check every markdown cell.

Find statements written before final results.

Flag:

- "best model"
- "superior"
- "wins"
- "fails"
- "proves"
- "demonstrates"


For each:

Report:

1. Cell id
2. Current wording
3. Problem
4. Recommended replacement


The notebook must follow:

Question

↓

Dataset / Motivation

↓

Method

↓

Evaluation protocol

↓

Observed results

↓

Interpretation

↓

Limitations


Do not allow conclusions before evidence.


---

# Phase 3 — Experiment notebook redesign


The two experiment notebooks should become execution-focused.

They should contain:

## Section 1
Research question

Example:

"We evaluate whether uplift models can identify treatment-sensitive users under different outcome definitions."


## Section 2
Dataset

Include:

- sample size
- treatment/control distribution
- outcome prevalence


## Section 3
Methods

Explain:

Response model:

P(Y|X)


Uplift models:

tau(X)=E[Y(1)-Y(0)|X]


## Section 4
Training


## Section 5
Evaluation


Only report:

- Qini
- AUUC
- uplift@10%
- bootstrap comparison


## Section 6
Artifacts generated


Do NOT include final cross-experiment conclusions.


Remove:

- conversion vs visit comparison
- overall winner statement
- global conclusion


---

# Phase 4 — Create / improve comparative report notebook


Create:

notebooks/reports/03_comparative_analysis_report.ipynb


Purpose:

Reader-facing analysis only.

It should NOT train models.


It loads:

outputs/conversion/

outputs/visit/


Create:


## 1. Outcome comparison

Table:

Outcome
Prevalence
Treatment rate
Control rate


## 2. Model performance comparison


Columns:

Outcome

Model

Objective

Qini

AUUC

uplift@10%


Objective:

Response:

P(Y|X) naive targeting baseline


T/X Learner:

tau(X) CATE estimation


Causal Forest:

tau(X) CATE estimation


## 3. Statistical comparison


Include:

paired bootstrap:

Response vs Causal Forest


Report:

- confidence interval
- significance
- interpretation


## 4. Final scientific interpretation


Must NOT say:

"Causal Forest is the best model"


or:

"Response is the best model"


Instead:


Example:

"Model performance depends strongly on outcome definition and signal density. Under sparse conversion outcomes, Response LightGBM and Causal Forest show statistically indistinguishable ranking performance. Under denser visit outcomes, Causal Forest achieves stronger uplift ranking performance, although the magnitude should be interpreted within the evaluated dataset."


---

# Phase 5 — Visualization audit


Review all figures.

Requirements:


Every figure must answer:

"What question does this figure answer?"


Remove:

- duplicate charts
- unnecessary implementation plots


Keep:

- outcome prevalence
- Qini curves
- AUUC comparison
- uplift@10%
- CATE distribution


Labels:

Response LightGBM:

"Response LightGBM (naive targeting reference)"


Never mix:

P(Y|X)

and:

tau(X)


---

# Phase 6 — Implementation

After audit:

Apply fixes.

Allowed:

- notebook markdown changes
- notebook code refactoring
- report notebook creation
- artifact loading changes


Forbidden:

- model code changes
- evaluation changes
- preprocessing changes
- hyperparameter changes


---

# Phase 7 — Validation


Run:

pytest tests -q


Validate:

- notebooks compile
- notebooks execute with existing artifacts
- outputs are not overwritten
- conversion and visit artifacts remain isolated


Final response must contain:

1. Files changed
2. Scientific issues fixed
3. Notebook structure changes
4. Report improvements
5. Validation results
6. Remaining limitations