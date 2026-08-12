# CRITEO-UPLIFTv2.1 causal uplift modeling

## Project status

Current phase: **Sprint 2 — T01 ready for implementation**.

Sprint 1 froze the causal, data, audit, methodology, experiment, metric, and
artifact contracts. T01 decision evidence has been reviewed and its loader,
determinism, row-identity, resource, manifest, and Parquet-layout decisions are
accepted. The full production data pipeline is not yet implemented. No official
held-out model evaluation has occurred or is authorized at this stage.

## Research objective

The project specifies large-scale causal uplift modeling on
CRITEO-UPLIFTv2.1. Its primary objective is to rank eligible observations by the
conditional effect of treatment assignment on `conversion`, rather than by
response probability alone. `conversion` is the primary outcome. When present
and schema-valid, `visit` is a secondary outcome that cannot change primary
selection or claims.

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
configs/       non-secret example manifests/configurations
data/          local raw and processed data; only data/README.md is versioned
docs/          decision register, specifications, ADRs, Sprint plan, and reviews
notebooks/      primary research execution, evidence, verification, and interpretation narrative
outputs/       immutable run-scoped machine-readable empirical evidence; ignored by Git
src/           optional reusable machinery when concretely justified
tests/         optional or task-required automated regression verification when justified
scripts/       optional supporting automation when concretely justified
archive/       historical local material; ignored and non-authoritative
```

From Sprint 2 empirical execution onward, the project is notebook-first, not
notebook-only. The relevant notebook must expose the question, pre-execution
protocol, code, checks, observations, interpretation, and limitations. Reusable
modules, scripts, and tests support that narrative only when reuse, correctness,
an authoritative contract, or unreasonable notebook duplication justifies them.

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

Sprint boundaries, local environment setup, configuration rules, and artifact
policy are documented in [REPRODUCIBILITY.md](REPRODUCIBILITY.md). Sprint 1 does
not provide an exact environment lockfile or claim execution evidence.
