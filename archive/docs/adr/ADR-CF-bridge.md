# ADR: Causal Forest cross-language bridge

**Status:** DEFERRED  
**Decision authority:** Owner-approved decision register  
**Decision ID:** D22  
**Scope:** Cross-language integration only; this ADR does not defer or alter the
accepted Causal Forest `MAIN_COMPARATOR` role.

## Decision

Use a Python implementation for Causal Forest unless the provisional
[Causal Forest implementation ADR](ADR-CF-implementation.md) demonstrates that
a required correctness, honesty, support, or inference capability is unavailable
from qualifying Python implementations.

A Python–R or other cross-language bridge is not part of the default Sprint 2
implementation. It remains **DEFERRED** until the activation condition below is
met and documented before held-out access.

## Activation condition

The bridge may be proposed only when all of the following are documented:

1. the CF implementation review identifies a specific required capability that
   qualifying Python candidates cannot provide;
2. the cross-language candidate provides that capability and passes the same CF
   correctness, synthetic-effect, leakage, honesty/support, resource,
   validation, seed, and pre-test-freeze gates;
3. a task-declared SMOKE benchmark (D30) proves deterministic transfer, row
   alignment, treatment/outcome coding, and prediction return; and
4. the applicable D30 RESOURCE gate(s), if the bridge is ever activated, show
   that integration cost and resource use are acceptable.

(Execution criterion amended by D30, superseded 2026-08-18, from the prior
fixed `D23` 50K-benchmark wording; this ADR's `DEFERRED` status and
Python-first/cross-language fallback semantics are unchanged.)

Activation changes the implementation boundary and therefore requires an ADR
amendment linked to the owner-approved register. Test results cannot activate the
bridge.

## Row-alignment and serialization requirements

Any activated bridge must:

- send and return a complete, unique `_source_row_id` for every transferred row;
- preserve the exact ordered `X=f0`–`f11`, `T=treatment`, and `Y=conversion`
  contract without index- or sort-based implicit joins;
- prove one-to-one row-count and identity reconciliation before accepting scores;
- preserve declared `float64` analytical precision and missing-value semantics;
- pin Python, bridge, R, package, platform, locale, thread, and seed versions;
- serialize the fitted model, configuration, feature order, component metadata,
  and reload instructions in stable declared formats;
- verify saved/reloaded prediction equivalence on a development-only fixture;
  and
- record checksums and producer/consumer run IDs in the artifact manifest.

Any missing, duplicated, reordered, non-finite, or unmatched returned row is a
HARD_GATE failure. It cannot be repaired by positional reassignment.

## Python fallback

If the activation condition is not met or any bridge gate fails, retain the
qualifying Python implementation selected by the CF implementation ADR. The
bridge remains deferred. This fallback concerns integration only and does not
omit or defer the accepted Causal Forest estimator role.

## Consequences

- Sprint 2 begins with Python candidates and no cross-language dependency.
- A bridge adds operational and reproducibility obligations only when it supplies
  a demonstrated required capability.
- Bridge failure cannot trigger held-out tuning or remove Causal Forest from the
  planned comparator portfolio.
- No current bridge, benchmark, model, audit, or held-out result is claimed.

## Affected artifacts

If activated, the freeze and artifact manifests must include exact paths for:

- the bridge environment and dependency lock;
- transferred development input/output schemas;
- row-alignment reconciliation results;
- smoke and scale benchmark reports;
- serialized cross-language model components and reload metadata;
- prediction-equivalence evidence; and
- run IDs and SHA-256 checksums for every boundary artifact.

The D22 reference artifact is `artifacts/cf_bridge_report.json`; the final
repository path and schema must be mapped in the experiment artifact manifest
before activation. While the bridge remains deferred, that artifact is not
required and no placeholder result is generated.
