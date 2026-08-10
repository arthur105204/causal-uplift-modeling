# Sprint 1 literature grounding matrix

## Scope

This is a bounded project-grounding matrix, not a systematic or exhaustive
literature review. It records how four core primary sources inform the current
specifications and, equally importantly, what the project must not infer from
them. No paper substitutes for the repository's owner-approved decisions,
causal contract, executable verification gates, or held-out evaluation rules.

| Source | Research role | Key concepts used | Project decision supported | Limits / non-claims | Sections to read | Sprint relevance |
|---|---|---|---|---|---|---|
| [Diemert, Betlei, Renaudin, and Amini (2018), *A Large Scale Benchmark for Uplift Modeling*](https://ailab.criteo.com/criteo-uplift-prediction-dataset/) | CRITEO uplift dataset context, randomized incrementality-test setting, large-scale real-data uplift evaluation, and AUUC-family benchmark context | Treatment/control uplift framing, scale, visits/conversions, transformed-method benchmark context, real-data ranking evaluation | D01–D04, D10, D23–D27; `docs/01_causal_contract.md`, `docs/02_data_contract.md`, `docs/07_metric_specification.md` | Does not prove conversion is stable for every release or subgroup; does not expose both potential outcomes or true row-level ITE; publisher description does not replace local lineage/checksum evidence | Dataset construction/description; benchmark methods; uplift evaluation metrics; experiments and limitations | Grounds dataset and evaluation context in Sprint 1; exact release identity and executed checks remain Sprint 2 evidence |
| [Künzel, Sekhon, Bickel, and Yu (2019), *Metalearners for Estimating Heterogeneous Treatment Effects Using Machine Learning*](https://www.pnas.org/doi/10.1073/pnas.1804597116) | S-, T-, and X-Learner framework and motivation for reusing supervised learners to estimate CATE | Separate response surfaces, imputed treatment effects, X-Learner combination, role of arm imbalance and response/effect structure | D13, D14, D17, D18; `docs/05_methodology_scope.md`, `docs/adr/ADR-base-learner.md` | X-Learner is not uniformly best; arm imbalance does not guarantee it beats T-Learner; a flexible base learner does not automatically validate causal identification or finite-sample ranking | Meta-learner definitions; X-Learner construction; theoretical motivation; simulations and applications | Grounds formulas and roles; implementation, cross-fitting, objective, scale, and validation gates remain Sprint 2 work |
| [Wager and Athey (2018), *Estimation and Inference of Heterogeneous Treatment Effects Using Random Forests*](https://doi.org/10.1080/01621459.2017.1319839) | Causal Forest construction, honesty/sample splitting, heterogeneous-effect estimation, and inferential theory under stated conditions | Honest forests, treatment-effect-focused splitting/estimation, support and asymptotic conditions | D10, D15, D22, D23; `docs/adr/ADR-CF-implementation.md`, `docs/adr/ADR-CF-bridge.md` | A modern library named causal forest is not automatically an exact replication of the paper; honesty, inference, variance, support, and regularity claims require implementation-specific verification | Forest construction; honesty; consistency/inference assumptions; empirical illustrations | Grounds the accepted estimator family and ADR gates without preselecting a package or claiming current gate success |
| [Kennedy (2023), *Towards Optimal Doubly Robust Estimation of Heterogeneous Causal Effects*](https://projecteuclid.org/journals/electronic-journal-of-statistics/volume-17/issue-2/Towards-optimal-doubly-robust-estimation-of-heterogeneous-causal-effects/10.1214/23-EJS2157.full) | Two-stage/DR CATE learning, pseudo-outcome regression, nuisance estimation, sample splitting, and conditions for oracle-style error bounds | Cross-fitted nuisance functions, doubly robust pseudo-outcomes, second-stage regression, nuisance-error conditions | D16, D18, D29; `docs/05_methodology_scope.md`, `docs/06_experiment_protocol.md` | Double robustness or asymptotic/oracle theory does not guarantee finite-sample Qini, stable rare-outcome ranking, valid results under arbitrary LightGBM stages, or automatic promotion | Oracle inequality for pseudo-outcome regression; DR-Learner construction and analysis; examples; discussion | Grounds the conditional stretch design and strict promotion gate; exact nuisance/final-stage choices remain open for Sprint 2 |

## Cross-source synthesis

### Transformed method and T-Learner are not synonyms

The transformed method (TM) used in uplift-benchmark literature constructs a
single transformed supervised target from treatment and observed outcome under
its own assumptions and weighting convention. T-Learner, as formalized in the
meta-learner framework, fits two arm-specific factual-outcome surfaces and ranks
by their difference. Both target treatment-effect heterogeneity, but their
training targets, model structure, support behavior, and failure modes differ.
The repository therefore implements and names T-Learner according to document 05
and does not relabel it as TM.

### Real-data uplift metrics and semi-synthetic PEHE have different roles

On real CRITEO-UPLIFTv2.1, only one potential outcome is observed per row.
Accordingly, assigned-arm ranking summaries such as raw Qini, Qini above random,
and fixed-coverage uplift are the declared real-data evaluation family. PEHE
requires known or constructed treatment-effect ground truth and is permitted only
for explicitly synthetic or semi-synthetic fixtures. A good semi-synthetic PEHE
result would verify a bounded fixture behavior; it would not become empirical
true-ITE evidence for the real dataset.

## Repository routing

- Dataset, treatment, outcome, and estimand claims route to documents 01 and 02.
- Meta-learner and DR formulas/roles route to document 05.
- Causal Forest implementation claims route to its provisional ADR.
- Split, cross-fitting, validation, and test-use claims route to document 06.
- Real-data versus synthetic metric claims route to document 07.

Where a paper permits several implementations, the owner-approved decision
register and repository specifications select the project role; Sprint 2
verification determines whether a concrete implementation is executable and
promotable.
