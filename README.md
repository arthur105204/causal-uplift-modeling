# CRITEO-UPLIFTv2.1 causal uplift modeling

A Kaggle-first, notebook-driven comparison of causal uplift models on the
**CRITEO-UPLIFTv2.1** advertising benchmark: a response-model baseline,
T-Learner, X-Learner, and Causal Forest, evaluated on incremental-conversion
ranking (Qini / uplift@K) rather than plain response prediction.

## Read the result

- **[`reports/final_research_memo.pdf`](reports/final_research_memo.pdf)** —
  the primary reader-facing deliverable: a short, plain-language-first
  research memo (research question, findings, statistical evidence,
  limitations, conclusion) with the same content as
  [`reports/research_memo.md`](reports/research_memo.md), its markdown
  source. Start here if you want the result without reading code.
- **[`notebooks/reports/comparative_analysis_report.ipynb`](notebooks/reports/comparative_analysis_report.ipynb)**
  — the technical evidence and reproducibility layer the memo above is
  built from: every table, figure, and statistic in the memo is computed
  and displayed here, loading only already-saved artifacts (no
  training). Read this if you want to see the analysis actually run, or
  to verify a number in the memo against its source.

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
├── kaggle_execution.ipynb           single staged entry point: set OUTCOME
│                                    ("conversion" | "visit") and RUN_STAGE
│                                    ("data" / "baseline" / "uplift" /
│                                    "causal_forest" / "report" / "all"),
│                                    restart-safe artifact reuse
├── evidence/
│   ├── 01_data_processing.ipynb     load CSV, validate, define X/T/Y, train/val/test split
│   ├── 02_baseline_models.ipynb     LightGBM response model (non-causal baseline)
│   ├── 03_uplift_models.ipynb       T-Learner, X-Learner
│   └── 04_causal_forest.ipynb       Causal Forest + final test-set comparison
│                                    (the reasoning behind each pipeline step,
│                                    one notebook per stage; kaggle_execution.ipynb
│                                    is the notebook to actually run)
├── experiments/
│   ├── conversion_experiment.ipynb  full pipeline executed with OUTCOME="conversion"
│   │                                (primary, business-relevant outcome)
│   └── visit_experiment.ipynb       full pipeline executed with OUTCOME="visit"
│                                    (denser robustness check, same
│                                    row partition -- see Methodology notes)
└── reports/
    └── comparative_analysis_report.ipynb   technical evidence and reproducibility
                                             layer -- loads existing artifacts only,
                                             trains/fits nothing; every number in the
                                             memo below traces back to this notebook

reports/                    top-level -- distinct from notebooks/reports/ above
├── final_research_memo.pdf primary reader-facing deliverable, see "Read the result"
├── research_memo.md        markdown source of the PDF above
├── build_pdf.py            regenerates final_research_memo.pdf from research_memo.md
├── figures/                PNG figures embedded in the memo, with captions
└── tables/                 CSV tables embedded in the memo, with captions

src/
├── data.py              path resolution, config loading, CSV/Parquet I/O, schema checks
├── preprocessing.py     categorical feature handling, train/validation/test split
├── models.py             LightGBM response model, T-Learner, X-Learner, Causal Forest
├── evaluation.py          Qini, AUUC, uplift@K, decile and ATE metrics
├── reporting.py           model comparison table, paired bootstrap significance
│                          check, per-model artifact packaging
├── pipeline.py            stage-runner functions backing kaggle_execution.ipynb
├── notebook_setup.py      environment/dependency bootstrap helpers
└── artifacts.py           artifact I/O for staged execution: save/load, fingerprinting, path handling

configs/
└── config.yaml         seed, split ratios, model hyperparameters (kept in sync
                         with the code by tests/test_config.py)

archive/                condensed-and-superseded governance docs (ADRs, decision
                         register, prior contracts) kept for historical reference;
                         see "Methodology notes" below for what actually matters

requirements.txt
README.md
```

`kaggle_execution.ipynb` is the single entry point: set `OUTCOME` and
`RUN_STAGE` and Run All. Each stage loads a cached artifact instead of
recomputing it whenever one already matches the current config, so a kernel
restart between stages does not retrain anything. `notebooks/evidence/01`–`04`
are the same pipeline split across one notebook per stage, kept as the place
to read the reasoning behind each step in isolation. `notebooks/experiments/`
holds the already-executed record of running the full pipeline once per
outcome; `notebooks/reports/comparative_analysis_report.ipynb` is the
cross-outcome synthesis built from those two runs' saved artifacts, and is
the technical evidence behind the top-level `reports/final_research_memo.pdf`
(see "Read the result" above) — read the PDF first for the result, this
notebook to see it computed and verify a number against its source.

`data/processed/` contains processed datasets generated by the data
pipeline, while `outputs/` stores runtime artifacts generated by
`kaggle_execution.ipynb`. Runtime outputs are gitignored. The top-level
`reports/` directory (PDF memo, its markdown source, figures, tables) is
checked in, unlike `outputs/`.

## Quickstart on Kaggle

1. **Make the repository available** to the kernel — clone it into
   `/kaggle/working` or attach it as a dataset. The notebooks locate the repo
   root themselves; they do not assume the kernel's working directory.
2. **Attach the data**: any Kaggle dataset containing
   `criteo-uplift-v2.1.csv`. The dataset slug is *not* hardcoded — every
   attached input is searched.
3. **Dependencies**: Kaggle's stock image does not include `econml`, and may
   not match the pinned `lightgbm` version. `kaggle_execution.ipynb` (and
   every `notebooks/evidence/02`–`04` / `notebooks/experiments/*` notebook
   that imports `src.models`) starts with a
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

   `notebooks/evidence/01`–`04` walk through the same pipeline one stage per
   notebook if you want to read the reasoning in isolation rather than run
   the staged version.

Each stage saves its test-set predictions under `outputs/<outcome>/...`, and
`report` reads them all to build the final comparison — so the models can be
run in separate kernel sessions without refitting anything. Run once with
`OUTCOME = "conversion"` and once with `OUTCOME = "visit"` to reproduce both
halves of `notebooks/reports/comparative_analysis_report.ipynb`, which reads
both outcomes' artifacts together. All generated files are written under
`/kaggle/working` (the only writable location on Kaggle).

## Evaluation design

| Partition | Share | Used for |
|---|---|---|
| train | 70% | model fitting |
| validation | 15% | early stopping and model selection |
| test | 15% | untouched until the final comparison in the `report` stage |

The `baseline` and `uplift` stages report validation numbers while
developing; the test partition is scored once, in the `report` stage's final
synthesis (`notebooks/evidence/02`/`03` do the same, split across two
notebooks). That keeps the headline comparison off data the models were
selected against.

The primary ranking statistic is **Qini above the theoretical random
reference**, reported alongside **AUUC** (area under the uplift curve), which
weights arm imbalance differently, plus `uplift@K` and a decile breakdown.
Empirical PEHE against true ITE is not reported — both potential outcomes are
never observed for any individual.

## Local setup

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pytest tests/ -q
.venv\Scripts\jupyter.exe lab
```

Local runs are for development, unit tests, and small synthetic checks — the
full ~13.9M-row pipeline is meant to run on Kaggle. Place a local CSV at
`data/raw/criteo-uplift-v2.1.csv` if you want to exercise the notebooks
outside Kaggle.

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

The shipped default (`configs/config.yaml: causal_forest.categorical_top_k`)
is **`K=8`** — the conservative end of the ladder, `8*(8+1)+4 = 76` encoded
columns. This is a memory/fidelity tradeoff, not a free parameter: at `K=32`
the encoded matrix is 268 columns, which at full CRITEO scale (~9.8M TRAIN
rows) is a ~21GB dense `float64` matrix *before* `CausalForest.fit()`'s own
honest-splitting and bootstrap overhead — a real OOM risk on a standard
Kaggle kernel. `K=8` keeps every categorical feature resolved down to its 8
most frequent levels (plus `OTHER`), which is coarser than LightGBM's native
full-cardinality categorical splits used by the T-/X-Learner — so Causal
Forest sees a lower-resolution categorical representation than the other
estimators, a real cross-model comparability caveat worth keeping in mind
when reading the final comparison in the `report` stage / `comparative_analysis_report.ipynb`. Raising `K` back toward
16 or 32 is possible via config, but should only be done after a measured
memory/runtime benchmark at the target row count — the code does not step
`K` down automatically if a higher value turns out to be infeasible.

**Other standing assumptions:**
- The estimand is assignment-based (intention-to-treat) CATE — models rank by
  the effect of *treatment assignment*, never by observed `exposure`, which is
  post-assignment and excluded from `X`.
- All released rows are kept for the primary analysis (no deduplication) to
  preserve the benchmark's actual population and empirical weights.
- Predicted uplift is not a true individual treatment effect, and `f0`–`f11`
  are anonymized with no known business meaning — so the CATE analysis in
  the `report` stage / experiment notebooks describes *what the models
  believe*, not a validated causal mechanism.

**Statistical significance of model gaps.** A point-estimate leaderboard
always produces a "winner" by construction, even when two models are
statistically indistinguishable. `src.reporting.paired_bootstrap_gaps` runs
a paired bootstrap (500 resamples, the same resample applied to both models
each draw) over the fixed test predictions and reports a 95% CI on the gap
between two models' Qini/AUUC/uplift@K — a CI that excludes zero is the bar
for calling a gap real rather than resampling noise. This is not a check
against every pairwise combination of models and metrics: the experiment
notebooks each check the top two models on one metric, and
`notebooks/reports/comparative_analysis_report.ipynb` checks Response
LightGBM vs. Causal Forest on three metrics, per outcome — see that
notebook's Section 5 and Limitations for what is and is not covered.

## License

Repository code and documentation are MIT licensed. The CRITEO-UPLIFTv2.1
dataset itself is not covered by that license and remains subject to the
publisher's own terms.
