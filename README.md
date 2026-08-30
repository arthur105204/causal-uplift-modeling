# Causal Uplift Modeling on CRITEO-UPLIFTv2.1

## What this project does

An advertiser wants to know which users an ad actually *changes the mind
of* — not just which users were likely to buy anyway. Money spent
advertising to someone who would have converted regardless is wasted; the
useful signal is the *incremental* effect of showing the ad, not the raw
likelihood of the outcome.

This project compares two ways of targeting users on a large, real-world
advertising dataset (**CRITEO-UPLIFTv2.1**, ~13.9M rows from a randomized
ad-exposure test): a simple model that predicts who is likely to act
regardless of treatment, versus three "uplift" models built specifically to
estimate the *incremental* effect of treatment on each user. It asks
whether the added complexity of the uplift models measurably outranks the
simpler approach.

## Research question

Does modeling *who is influenced by an ad* (an uplift, or causal, model)
rank users for targeting any better than modeling *who is simply likely to
act* (a standard response model) — and is any answer to that stable across
a rare, business-relevant outcome and a denser, related one?

## Data

- **Dataset:** CRITEO-UPLIFTv2.1, a public randomized-controlled-trial
  advertising dataset (~13.9M rows). See
  [`data/README.md`](data/README.md) for the expected local layout — the
  raw data itself is not checked into this repository.
- **Treatment:** whether a user was shown the ad (assigned, not merely
  eligible — the standard randomized "intention-to-treat" setup).
- **Outcomes studied:**
  - **conversion** (primary) — the user completes a purchase. This is the
    outcome that matters for the business, but it's rare: about 0.29% of
    test rows.
  - **visit** (robustness check) — the user visits the advertiser's site,
    a much more common event (~4.66% of test rows, roughly 16x more
    common than conversion) on the same causal path — every conversion is
    preceded by a visit. It's used to check whether conclusions reached
    under conversion's rarity hold up once the models have a denser
    signal to learn from, not as a second business objective.
- Both outcomes are evaluated on the identical held-out test rows, so the
  comparison isolates the effect of outcome rarity rather than any
  difference in the underlying population.

## Models compared

| Model | In one sentence |
|---|---|
| **Response LightGBM** | Predicts how likely a user is to act, ignoring treatment entirely — a standard, non-causal targeting baseline. |
| **T-Learner** | Fits two separate models (treated, untreated) and takes the difference between their predictions as the estimated effect. |
| **X-Learner** | A refinement of T-Learner that corrects for having very different numbers of treated vs. untreated users. |
| **Causal Forest** | A decision-tree ensemble built to directly target the treatment effect itself, rather than differencing two separate models. |

Response LightGBM is the **baseline** every other model is compared
against — not the "best" or preferred model, just the common reference
point.

## Main findings

**Raw ranking performance** (how well each model ranks users by
incremental effect, on the held-out test rows — see the final report for
full tables):
- Under **conversion**, Response LightGBM's ranking score is numerically
  highest, with Causal Forest close behind.
- Under **visit**, the order flips: Causal Forest's ranking score is
  numerically highest, with Response LightGBM second.
- T-Learner and X-Learner trail both of the above under either outcome.

A leaderboard by raw score always has a top row, though — the real
question is whether that gap is likely to be a genuine difference or just
resampling noise. That's checked with a statistical test (a paired
bootstrap: repeatedly resampling the test rows and seeing how much the gap
moves around).

**Causal Forest vs. the Response baseline** (`Causal Forest − Response`;
positive favors Causal Forest, negative favors Response, and an interval
that straddles zero means the data can't tell the two apart):
- Under **conversion**: the interval straddles zero on every metric
  checked — **not** statistically distinguishable from noise at this
  sample size.
- Under **visit**: the interval sits entirely on the positive side on
  every metric checked — Causal Forest's advantage **is** statistically
  distinguishable from noise here.

This specific statistical test was only run for Causal Forest against the
Response baseline — not for T-Learner or X-Learner, and not as a
head-to-head between the two uplift-learner families.

**A separate, different question — "best vs. runner-up":** the experiment
notebooks also run a paired bootstrap on whichever two models happen to
rank 1st and 2nd by raw score for a given outcome. This is a different,
model-agnostic check ("is the current leaderboard's top spot real?"), not
a Response-baseline comparison — under conversion that happens to be
Response vs. Causal Forest (not statistically distinguishable), and under
visit it happens to be Causal Forest vs. Response (statistically
distinguishable) — the same pair, coincidentally, but asked for a
different reason.

## What the final result means

Read together, the two outcomes suggest that **conversion's rarity — not
which model is better — is a plausible reason the comparison is
inconclusive there**: the same models, fit and scored the same way, on the
same rows, produce an unresolved gap under the rare outcome and a
resolved one once given a denser signal. That explanation is a reasonable
inference from the evidence, not a proven fact — no artifact in this
project directly measures whether visit-ranked and conversion-ranked
scores actually agree with each other.

For a team deciding today: on conversion, the outcome that matters for the
business, this analysis does **not** give statistical grounds to prefer
either the response baseline or the causal models — the honest reading is
that the two approaches aren't distinguishable at this sample size, not
that either has been shown to beat the other.

**Limitations worth knowing before acting on this:**
- This is an offline evaluation against historical, logged outcomes — no
  online experiment confirms acting on either ranking would reproduce the
  measured effect.
- The "rarity explains it" explanation above is inferred, not verified.
- The statistical test only covers Causal Forest vs. Response, on three
  metrics, per outcome — not every possible pairwise comparison.
- Predicted uplift is not a validated individual causal effect: no ground
  truth exists to check it against, since only one of each user's two
  potential outcomes is ever observed.
- Causal Forest sees a coarser categorical feature representation than the
  LightGBM-based models, for memory reasons — a caveat on the comparison,
  not a claim either way.
- All conclusions are specific to this dataset, these implementations, and
  one hyperparameter setting each — not a universal claim about any
  method.

The [final research report](#final-research-report) below has the full
statistical evidence, all four models' complete numbers, and a more
detailed discussion of every limitation above.

## Final research report

| File | What it is |
|---|---|
| [`reports/final_research_memo.pdf`](reports/final_research_memo.pdf) | **Start here.** The primary, reader-facing report: research question, findings, statistical evidence, limitations, conclusion — no code required. |
| [`reports/research_memo.md`](reports/research_memo.md) | The same report's Markdown source, if you'd rather read it in a browser or editor. |
| [`notebooks/reports/comparative_analysis_report.ipynb`](notebooks/reports/comparative_analysis_report.ipynb) | The technical evidence behind every number in the report above — loads already-saved results and displays them; trains nothing. Read this to verify a specific number against its source. |

## How the analysis is organized

```
Data (load + validate CRITEO-UPLIFTv2.1, define treatment/outcomes, split)
    ↓
Response LightGBM  (non-causal baseline)
    ↓
T-Learner, X-Learner   (uplift models)
    ↓
Causal Forest          (uplift model)
    ↓
Model comparison + statistical significance check (held-out test rows only)
    ↓
Final research report
```

Each stage is run once per outcome (`conversion`, then `visit`), on the
same row split, so the two outcomes are directly comparable. The
comparison stage never re-fits a model — it only reads each stage's saved
results.

## Repository structure

- **`reports/`** — the final report (PDF and Markdown), plus the figures
  and tables it's built from. This is what most readers want.
- **`notebooks/`** — the Jupyter notebooks that run the analysis: a single
  entry point (`kaggle_execution.ipynb`), the saved records of running it
  once per outcome (`experiments/`), and the report-building notebook
  (`reports/`).
- **`src/`** — the Python code the notebooks call into (data loading,
  model definitions, evaluation metrics, reporting helpers).
- **`tests/`** — the automated test suite covering `src/`.

## Reproducibility

The full pipeline has been run end-to-end on Kaggle, once per outcome, and
its results are saved under `reports/`. The report notebook and PDF are
built entirely from those saved results — they load and display existing
numbers rather than retraining or re-scoring anything. A recent
presentation fix (correcting which direction a comparison's gap is
reported in, and a figure layout issue) was verified by re-deriving the
affected statistics algebraically from the already-computed results, and
by validating notebook structure and outputs directly, rather than by a
fresh full re-execution of the (multi-hour) statistical test.

## Validation

The automated test suite (`src/`'s data handling, evaluation metrics, and
reporting logic) currently passes in full: **136 passed**. See
[Local setup](#local-setup) below to run it yourself.

## Technical details

The sections below are for readers who want to run the code, reproduce a
result, or understand an implementation decision — not required to
understand the research itself.

### Quickstart on Kaggle

1. **Make the repository available** to the kernel — clone it into
   `/kaggle/working` or attach it as a dataset. The notebooks locate the
   repo root themselves; they do not assume the kernel's working
   directory.
2. **Attach the data**: any Kaggle dataset containing
   `criteo-uplift-v2.1.csv`. The dataset slug is *not* hardcoded — every
   attached input is searched.
3. **Dependencies**: Kaggle's stock image does not include `econml`, and
   may not match the pinned `lightgbm` version. `kaggle_execution.ipynb`
   (and every notebook that imports `src.models`) starts with a
   `%pip install -q econml==0.17.0 lightgbm==4.7.0` cell, right after the
   repo-root bootstrap — it's a no-op if the pinned versions are already
   present. No manual install step is required; just let that cell run.
4. **Run `notebooks/kaggle_execution.ipynb`:** set `OUTCOME`
   (`"conversion"` primary, `"visit"` robustness check) and `RUN_STAGE`,
   then Run All.

   | `RUN_STAGE` | Does |
   |---|---|
   | `data` | loads the CSV, validates it, states `X = f0..f11` / `T = treatment` / `Y = conversion` (or `visit`), builds the train/validation/test split, writes Parquet partitions |
   | `baseline` | LightGBM response model (non-causal comparator) |
   | `uplift` | T-Learner and X-Learner |
   | `causal_forest` | Causal Forest |
   | `report` | final test-set comparison of every available model, from saved artifacts only — fits nothing, so it's the stage to rerun after a kernel restart |
   | `all` | every stage above, in order, in one session |

   `notebooks/evidence/01`–`04` walk through the same pipeline one stage
   per notebook if you want to read the reasoning in isolation rather than
   run the staged version.

Each stage saves its test-set predictions under `outputs/<outcome>/...`,
and `report` reads them all to build the final comparison — so the models
can be run in separate kernel sessions without refitting anything. Run
once with `OUTCOME = "conversion"` and once with `OUTCOME = "visit"` to
reproduce both halves of `notebooks/reports/comparative_analysis_report.ipynb`,
which reads both outcomes' artifacts together. All generated files are
written under `/kaggle/working` (the only writable location on Kaggle).

### Evaluation design

| Partition | Share | Used for |
|---|---|---|
| train | 70% | model fitting |
| validation | 15% | early stopping and model selection |
| test | 15% | untouched until the final comparison in the `report` stage |

The `baseline` and `uplift` stages report validation numbers while
developing; the test partition is scored once, in the `report` stage's
final synthesis. That keeps the headline comparison off data the models
were selected against.

The primary ranking statistic is **Qini above the theoretical random
reference**, reported alongside **AUUC** (area under the uplift curve,
which weights arm imbalance differently), plus `uplift@K` and a decile
breakdown. Empirical PEHE against true individual treatment effect is not
reported — both potential outcomes are never observed for any one
individual.

### Local setup

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pytest tests/ -q
.venv\Scripts\jupyter.exe lab
```

Local runs are for development, unit tests, and small synthetic checks —
the full ~13.9M-row pipeline is meant to run on Kaggle. Place a local CSV
at `data/raw/criteo-uplift-v2.1.csv` if you want to exercise the notebooks
outside Kaggle.

### Data contract

`X` is exactly the ordered feature set `f0` through `f11`. `T` is binary
`treatment` assignment. Primary `Y` is `conversion`; `visit` is an
optional secondary outcome. `exposure` is post-assignment and must never
enter `X`, eligibility, or the treatment definition. See
[`data/README.md`](data/README.md) for the expected local layout — raw and
processed data are not committed.

### Methodology notes

These are the modeling decisions worth knowing before reading the
notebooks or `src/`. They're condensed from this project's earlier, more
heavily-documented research phase (full rationale archived under
`archive/docs/` and `archive/docs/adr/` for anyone who wants the original
derivation).

**Feature semantics (D32).** All twelve `f0`–`f11` columns are stored as
`float64`, but physical storage does not imply semantic type. Per the
CRITEO-UPLIFTv2.1 publisher documentation and the official benchmark
implementation: `f0`, `f2`, `f7`, `f10` are **continuous**; `f1`, `f3`,
`f4`, `f5`, `f6`, `f8`, `f9`, `f11` are **categorical numeric tokens** with
no ordinal meaning. Treating all twelve as plain continuous numbers (an
easy mistake given the shared dtype) silently miscalibrates every
downstream model that assumes ordering or scale on the categorical group —
do not compute SMD/mean/variance on them, and do not infer
categorical-vs-continuous status from cardinality. LightGBM is given the
categorical group via its native categorical-feature representation;
continuous features pass through unchanged.

**X-Learner fold-local preprocessing.** X-Learner's nuisance stage uses
two-fold cross-fitting. The categorical preprocessing transform (the
train-fitted vocabulary used to build LightGBM's categorical
representation) must be fit **only on each fold's own training rows** and
then applied, unchanged, to that fold's out-of-fold predictions and
validation set. Fitting one transform on the whole train partition and
reusing it across both folds leaks each fold's categorical vocabulary
information into the other (opposite) fold — a real bug that was found and
fixed during this project's development. The effect-stage transform
(tau1/tau0) has no cross-fitting boundary and is fit once on the full
train partition, which is correct as-is.

**Causal Forest categorical representation.** `econml.grf.CausalForest`
has no LightGBM-equivalent native categorical support — it consumes a
dense numeric matrix. Encoding the categorical tokens as raw ordinal
integers (the same mistake that mirrors the D32 issue) would fabricate a
false ordering the forest's splits would then exploit. The chosen
representation is **frequency-capped top-K one-hot**: for each categorical
feature, keep the top-`K` categories by train-set frequency, bucket
everything else (including categories unseen at train time) into an
explicit `OTHER` level, then one-hot encode; continuous features pass
through unchanged. `K` is chosen from a resource ladder (32 → 16 → 8,
picking the largest that fits available memory/runtime) — never by
comparing model performance across `K` values. Unbounded one-hot and
target/effect encoding were both rejected: unbounded one-hot is infeasible
at full data scale, and target/effect encoding would leak the outcome into
the same matrix the forest uses to place its splits.

The shipped default (`configs/config.yaml: causal_forest.categorical_top_k`)
is **`K=8`** — the conservative end of the ladder, `8*(8+1)+4 = 76` encoded
columns. This is a memory/fidelity tradeoff, not a free parameter: at
`K=32` the encoded matrix is 268 columns, which at full CRITEO scale
(~9.8M TRAIN rows) is a ~21GB dense `float64` matrix *before*
`CausalForest.fit()`'s own honest-splitting and bootstrap overhead — a
real OOM risk on a standard Kaggle kernel. `K=8` keeps every categorical
feature resolved down to its 8 most frequent levels (plus `OTHER`), which
is coarser than LightGBM's native full-cardinality categorical splits used
by the T-/X-Learner — so Causal Forest sees a lower-resolution categorical
representation than the other estimators, a real cross-model
comparability caveat worth keeping in mind when reading the final
comparison. Raising `K` back toward 16 or 32 is possible via config, but
should only be done after a measured memory/runtime benchmark at the
target row count — the code does not step `K` down automatically if a
higher value turns out to be infeasible.

**Other standing assumptions:**
- The estimand is assignment-based (intention-to-treat) CATE — models rank
  by the effect of *treatment assignment*, never by observed `exposure`,
  which is post-assignment and excluded from `X`.
- All released rows are kept for the primary analysis (no deduplication)
  to preserve the benchmark's actual population and empirical weights.
- Predicted uplift is not a true individual treatment effect, and
  `f0`–`f11` are anonymized with no known business meaning — so the CATE
  analysis describes *what the models believe*, not a validated causal
  mechanism.

**Statistical significance of model gaps.** A point-estimate leaderboard
always produces a "winner" by construction, even when two models are
statistically indistinguishable. `src.reporting.paired_bootstrap_gaps`
runs a paired bootstrap (500 resamples, the same resample applied to both
models each draw) over the fixed test predictions and reports a 95% CI on
the gap between two models' Qini/AUUC/uplift@K — a CI that excludes zero
is the bar for calling a gap real rather than resampling noise. This is
not a check against every pairwise combination of models and metrics: the
experiment notebooks each check the top two models on one metric (see
"best vs. runner-up" above), and
`notebooks/reports/comparative_analysis_report.ipynb` checks Causal Forest
against the Response LightGBM baseline on three metrics, per outcome — see
that notebook's Section 5 and Limitations for what is and is not covered.

## License

Repository code and documentation are MIT licensed. The CRITEO-UPLIFTv2.1
dataset itself is not covered by that license and remains subject to the
publisher's own terms.
