# CRITEO-UPLIFTv2.1 causal uplift modeling

A Kaggle-first, notebook-driven comparison of causal uplift models on the
**CRITEO-UPLIFTv2.1** advertising benchmark: a response-model baseline,
T-Learner, X-Learner, and Causal Forest, evaluated on incremental-conversion
ranking (Qini / uplift@K) rather than plain response prediction.

## Research objective

A response model asks *who is likely to convert*; the uplift models compared
here instead ask *where treatment changes conversion* — ranking observations
by the conditional effect of treatment assignment on `conversion`, rather than
by response probability alone.

Conclusions here are dataset-specific, implementation-specific, and
metric-specific: a valid conclusion has the form "among the evaluated
implementations, estimator A achieved stronger validation uplift-ranking
performance on CRITEO-UPLIFTv2.1" — not a claim that one estimator is
universally better, or that observed performance is intrinsic to a
meta-learner family in general.

## Repository structure

```text
data/
└── README.md              expected local layout; data itself is not versioned

notebooks/
├── 01_data_processing.ipynb   load CSV, validate shape, define X/T/Y, train/val split
├── 02_baseline_models.ipynb   LightGBM response model (non-causal baseline)
├── 03_uplift_models.ipynb     T-Learner, X-Learner
└── 04_causal_forest.ipynb     Causal Forest

src/
├── data.py            CSV/Parquet loading and basic shape/schema checks
├── preprocessing.py   D32 categorical/continuous feature handling, train/val split
├── models.py           LightGBM response model, T-Learner, X-Learner, Causal Forest
└── evaluation.py        Qini / AUUC / uplift@K metrics

configs/
└── config.yaml         seed, split ratios, model hyperparameters

archive/                condensed-and-superseded governance docs (ADRs, decision
                         register, prior contracts) kept for historical reference;
                         see "Methodology notes" below for what actually matters

requirements.txt
README.md
```

## Quickstart on Kaggle

1. **Attach the dataset.** Add the Kaggle dataset containing
   `criteo-uplift-v2.1.csv` to your notebook's inputs.
2. **Run `notebooks/01_data_processing.ipynb`.** Loads the CSV, checks shape,
   defines `X = f0..f11`, `T = treatment`, `Y = conversion`, builds the
   train/validation split, and optionally saves a processed Parquet file.
3. **Run `notebooks/02_baseline_models.ipynb`.** Fits the LightGBM response
   model, T-Learner, and X-Learner.
4. **Run `notebooks/03_uplift_models.ipynb`** for the T-Learner/X-Learner
   comparison, and **`notebooks/04_causal_forest.ipynb`** for Causal Forest.
5. Each notebook reports Qini/AUUC/uplift@K metrics, plots, and feature
   analysis for its models; conclusions are summarized at the end of
   `04_causal_forest.ipynb`.

## Local setup

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\jupyter.exe lab
```

Run notebooks from the repository root so `src.*` imports resolve.

## Data

`X` is exactly the ordered feature set `f0` through `f11`. `T` is binary
`treatment` assignment. Primary `Y` is `conversion`; `visit` is an optional
secondary outcome. `exposure` is post-assignment and must never enter `X`,
eligibility, or the treatment definition. See [`data/README.md`](data/README.md)
for the expected local layout — raw and processed data are not committed.

## Methodology notes

These are the modeling decisions worth knowing before reading the notebooks or
`src/`. They're condensed from this project's earlier, more heavily-documented
research phase (full rationale archived under `archive/docs/` and
`archive/docs/adr/` for anyone who wants the original derivation).

**Feature semantics (D32).** All twelve `f0`–`f11` columns are stored as
`float64`, but physical storage does not imply semantic type. Per the
CRITEO-UPLIFTv2.1 publisher documentation and the official benchmark
implementation: `f0`, `f2`, `f7`, `f10` are **continuous**; `f1`, `f3`, `f4`,
`f5`, `f6`, `f8`, `f9`, `f11` are **categorical numeric tokens** with no
ordinal meaning. Treating all twelve as plain continuous numbers (an easy
mistake given the shared dtype) silently miscalibrates every downstream model
that assumes ordering or scale on the categorical group — do not compute
SMD/mean/variance on them, and do not infer categorical-vs-continuous status
from cardinality. LightGBM is given the categorical group via its native
categorical-feature representation; continuous features pass through
unchanged.

**X-Learner fold-local preprocessing.** X-Learner's nuisance stage uses
two-fold cross-fitting. The categorical preprocessing transform (the
train-fitted vocabulary used to build LightGBM's categorical representation)
must be fit **only on each fold's own training rows** and then applied,
unchanged, to that fold's out-of-fold predictions and validation set. Fitting
one transform on the whole train partition and reusing it across both folds
leaks each fold's categorical vocabulary information into the other
(opposite) fold — a real bug that was found and fixed during this project's
development. The effect-stage transform (tau1/tau0) has no cross-fitting
boundary and is fit once on the full train partition, which is correct as-is.

**Causal Forest categorical representation.** `econml.grf.CausalForest` has no
LightGBM-equivalent native categorical support — it consumes a dense numeric
matrix. Encoding the categorical tokens as raw ordinal integers (the same mistake
that mirrors the D32 issue) would fabricate a false ordering the forest's
splits would then exploit. The chosen representation is **frequency-capped
top-K one-hot**: for each categorical feature, keep the top-`K` categories by
train-set frequency, bucket everything else (including categories unseen at
train time) into an explicit `OTHER` level, then one-hot encode; continuous
features pass through unchanged. `K` is chosen from a resource ladder
(32 → 16 → 8, picking the largest that fits available memory/runtime) — never
by comparing model performance across `K` values. Unbounded one-hot and
target/effect encoding were both rejected: unbounded one-hot is infeasible at
full data scale, and target/effect encoding would leak the outcome into the
same matrix the forest uses to place its splits.

**Other standing assumptions:**
- The estimand is assignment-based (intention-to-treat) CATE — models rank by
  the effect of *treatment assignment*, never by observed `exposure`, which is
  post-assignment and excluded from `X`.
- All released rows are kept for the primary analysis (no deduplication) to
  preserve the benchmark's actual population and empirical weights.
- Qini above the theoretical random reference is the primary ranking metric;
  no true individual treatment effect is observed on real data, so PEHE
  against ground truth is not reported.
- Uncertainty on the final model comparison is quantified with a paired,
  treatment-arm-stratified bootstrap over fixed predictions (no retraining
  inside bootstrap draws).

## License

Repository code and documentation are MIT licensed. The CRITEO-UPLIFTv2.1
dataset itself is not covered by that license and remains subject to the
publisher's own terms.
