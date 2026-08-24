# CRITEO-UPLIFTv2.1 causal uplift modeling

## Project status

This project develops causal uplift models on CRITEO-UPLIFTv2.1 through a fixed
sequence of public Kaggle notebooks (`kaggle/01_data_understanding.ipynb` through
`kaggle/04_final_evaluation.ipynb`) that tell the data-science story; GitHub
Issues remain the internal execution/task system the notebooks draw on — the
two are deliberately not a 1:1 mirror. The causal, data, audit, methodology, experiment,
metric, and artifact contracts in `docs/` are frozen. Current task status and the
execution plan are tracked live in GitHub Issues, with
[Issue #20](https://github.com/arthur105204/causal-uplift-modeling/issues/20)
(`[MASTER]`) as the authoritative overview — that is the source of truth for what
is complete, in progress, or pending, rather than this file. No model training,
split construction, or held-out evaluation is authorized before its predecessor
tasks in that plan are complete.

## Research objective

This project is a controlled empirical comparison of selected causal-uplift
implementations under one common large-scale randomized advertising benchmark
(CRITEO-UPLIFTv2.1) and one fixed experimental protocol (D33). It is **not**
an attempt to identify a universally best CATE/uplift algorithm.

A response model asks *who is likely to convert*; the uplift models compared
here instead ask *where treatment changes conversion* — ranking eligible
observations by the conditional effect of treatment assignment on
`conversion`, rather than by response probability alone. The compared
portfolio is the theoretical random reference, a Response LightGBM comparator,
T-Learner, X-Learner, and Causal Forest, on a common validation cohort and one
frozen held-out evaluation. `conversion` is the primary outcome; when present
and schema-valid, `visit` is a secondary outcome that cannot change primary
selection or claims.

Conclusions are explicitly dataset-specific, implementation-specific,
protocol-specific, and metric-specific: a valid conclusion has the form "among
the evaluated implementations, estimator A achieved stronger held-out
uplift-ranking / treatment-allocation performance under the frozen
CRITEO-UPLIFTv2.1 protocol" — not a claim that one estimator is universally
better, that observed performance is intrinsic to a meta-learner family, or
that observed superiority explains *why* an estimator is theoretically better.

## Causal contract summary

- `X` is exactly the ordered feature set `f0` through `f11`.
- `T` is binary `treatment` assignment.
- Primary `Y` is binary `conversion`; optional secondary `Y` is `visit` in a
  separate outcome pipeline.
- `exposure` is treated conservatively as post-assignment and is prohibited from
  primary `X`, eligibility, population filtering, and the primary treatment
  definition.
- The primary estimand is assignment/intention-to-treat CATE for ranking over
  the eligible released population. Predicted uplift is not an observed true
  individual treatment effect.

The authoritative definitions and limitations are in the
[causal contract](docs/01_causal_contract.md) and
[data contract](docs/02_data_contract.md).

## Estimator scope

The specified comparison portfolio contains:

- a theoretical/seeded random ranking reference;
- a response-model baseline, which is not a causal estimator;
- T-Learner as the required primary causal baseline;
- X-Learner as an accepted main comparator;
- Causal Forest as an accepted main comparator planned for Sprint 2, with a
  provisional exact implementation; and
- DR-Learner as a conditional stretch comparator that enters held-out evaluation
  only if every development-only promotion gate passes before freeze.

S-Learner is deferred. No estimator is declared the winner in advance, and no
implementation status may silently redefine an owner-approved estimator role.
See the [methodology scope](docs/05_methodology_scope.md).

## Evaluation scope

The primary ranking statistic is Qini above the theoretical expected-random
reference under the exact convention in the
[metric specification](docs/07_metric_specification.md). Raw Qini area and fixed
`uplift@K`/incremental-conversion summaries have their documented secondary and
decision roles. The repository does not report empirical PEHE against true ITE
on real CRITEO-UPLIFTv2.1 because both potential outcomes are not observed.

Training and validation support development, early stopping, selection,
robustness, and promotion. The held-out test is used once only after the
[experiment protocol](docs/06_experiment_protocol.md) records a valid pre-test
freeze. Test information cannot select data handling, diagnostics, estimators,
hyperparameters, seeds, ranking rules, or claims.

## Repository structure

```text
kaggle/            public Kaggle notebook story (01 data understanding through 04 final evaluation)
notebooks/internal/  heavy or held-out-sensitive computation; not reader-facing
notebooks/legacy/     retained prior evidence, kept for provenance; inherited, not re-derived
configs/            non-secret example manifests/configurations
data/               local raw and processed data; only data/README.md is versioned
docs/               decision register, specifications, ADRs, and historical Sprint 1 records
outputs/            immutable run-scoped machine-readable empirical evidence; ignored by Git
src/                optional reusable machinery when concretely justified
tests/              optional or task-required automated regression verification when justified
scripts/            optional supporting automation when concretely justified
archive/            historical local material; ignored and non-authoritative
```

The project is notebook-first, not notebook-only. The relevant notebook must
expose the question, pre-execution protocol, code, checks, observations,
interpretation, and limitations. Reusable modules, scripts, and tests support
that narrative only when reuse, correctness, an authoritative contract, or
unreasonable notebook duplication justifies them.

## Data policy

Raw and processed CRITEO-UPLIFTv2.1 data must not be committed. Use an explicit
local manifest rather than filename heuristics, and preserve processed-to-raw
lineage. Setup and schema expectations are documented in
[data/README.md](data/README.md).

The repository source code and documentation use the MIT License. The Criteo
dataset is not covered by that repository license and remains subject to its own
publisher terms and license.

## Documentation map

The authority hierarchy, specification map, and ADR statuses are maintained in
[docs/index.md](docs/index.md). The owner-approved
[decision register](docs/decision_register.csv) has highest precedence.

## Reproducibility

Kaggle is the primary heavy-compute environment, and a full pipeline does not
have to fit inside one Kaggle notebook session. Expensive stages communicate
through explicit, versioned, immutable artifacts under
`outputs/runs/<run_id>/`: a downstream stage re-derives and checksum-verifies
its input from a declared upstream run rather than depending on shared
in-memory state, so stages can run in different Kaggle sessions, on different
machines, or months apart and still reproduce the same chain. Kaggle notebooks
under `kaggle/` detect their environment and run against a Kaggle-attached
input dataset or a local `data/raw/` copy with no other setup. For local
development against the full data pipeline, dependencies and test commands are
documented in [`CLAUDE.md`](CLAUDE.md#commands). No exact
interpreter/package/platform lockfile is frozen at this stage; environment
identity for consequential runs is captured in the corresponding immutable run
manifest, not in this file.
