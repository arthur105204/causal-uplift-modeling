# ADR: Provisional data-stack implementation

**Status:** PROVISIONAL  
**Decision authority:** Owner-approved `decision_register.csv` decisions D09,
D19, D20, D21, and D23  
**Sprint 1 assessment:** PASS_WITH_LIMITATION  
**Execution status:** OPEN_FOR_SPRINT2

## Context

The owner-approved direction uses Parquet for analytical storage and Pandas plus
PyArrow as the default data stack. Polars or DuckDB may be considered only under
the bounded benchmark fallback in D20. The technology direction does not replace
the higher-authority [data contract](../02_data_contract.md) or
[experiment protocol](../06_experiment_protocol.md), and no real-data benchmark
result is asserted here.

## Provisional decision

- Use PyArrow for typed Parquet metadata and columnar I/O.
- Use Pandas/NumPy with explicit configuration as the default table path.
- Evaluate Polars or DuckDB only if the default misses a predeclared
  correctness/resource bound and the alternative passes like-for-like identity,
  schema, precision, ordering, and determinism checks.
- Use an explicit manifest/configuration as the sole input selector for an
  auditable run.

The exact package versions, threading behavior, benchmark evidence, and
large-scale execution remain `OPEN_FOR_SPRINT2`.

## Authoritative input

The manifest identifies one authoritative CRITEO-UPLIFTv2.1 raw release and its
processed derivative. A workflow must not select an input because it appears
first, has a preferred filename, matches an extension, or happens to be the only
file in a directory. Missing, ambiguous, or schema-incompatible manifest input
fails closed.

Raw CSV and processed Parquet are not independent sources with equal authority.
The processed file is an analytical derivative whose lineage must resolve to the
manifest-selected raw release, conversion configuration, tool versions, row and
schema reconciliation, and checksums.

## Release and provenance

The active dataset and schema are CRITEO-UPLIFTv2.1 as defined by document 02.
Sprint 1 freezes the required provenance/checksum fields and SHA-256 algorithm.
It does not invent an authoritative URL, publisher license, release identifier,
or checksum value that the owner-approved sources have not supplied.

Actual paths, release metadata, row counts, checksums, and manifest evidence are
`OPEN_FOR_SPRINT2`. Their absence as execution evidence is not a Sprint 1 blocker
because the specification and fail-closed behavior are defined.

## Numeric representation

D09 and document 02 fix `float64` as the primary analytical precision.
`float32` is sensitivity-only unless a new owner-approved decision changes the
primary representation. No loader, conversion, engine fallback, or model path
may silently coerce primary `f0`–`f11` values to `float32`.

The future lineage manifest records source physical types, processed physical
types, analytical types, and every explicit cast. Precision sensitivities remain
separate from the primary population and interpretation.

## Scale failure

D23 defines the 50K→500K→2M→full correctness/resource progression. Failure at a
scale gate does not authorize a silent 2M→1M or other unregistered fallback.

Any scale reduction must:

1. record the failed scale, exception/resource evidence, configuration, and run
   identity;
2. create the required failure or promotion-gate artifact;
3. use a new explicit run configuration for the bounded development scope; and
4. remain in development until the applicable promotion or owner-approved
   disposition is recorded before test access.

## Schema and forbidden variables

- `X` is exactly ordered `f0` through `f11`.
- `treatment` is binary treatment assignment and never a feature.
- `conversion` is the primary outcome and never a feature.
- `visit` is an optional secondary outcome in a separate pipeline and never a
  primary feature or selection condition.
- `exposure` is post-assignment/audit-only and is forbidden from primary `X`,
  eligibility, and the primary treatment definition.
- `_source_row_id` is identity metadata only and never a feature.

Schema mismatch, ambiguous input, forbidden-column inclusion, invalid labels,
non-finite prohibited values, or unreconciled row identity fails closed.

## Verification gate

Before pre-test freeze, Sprint 2 must verify the manifest-selected file,
processed-to-raw lineage, SHA-256 values, schema, primary precision, row identity,
deterministic sampling/splitting, package environment, and D23 resource gates.
An alternative engine must additionally reproduce the declared schema, rows,
identity, ordering or explicit order, and precision of the default path.

No current checksum, benchmark, data-quality, or scale-gate result is claimed.

## Alignment

- [Document 02](../02_data_contract.md) is authoritative for dataset identity,
  schema, column roles, validation, lineage, and numeric precision.
- [Document 06](../06_experiment_protocol.md) is authoritative for sampling,
  splitting, scale progression, execution sequence, test isolation, and freeze.
- This ADR records only the provisional technology/data-stack rationale and its
  implementation gate. It cannot weaken either higher-authority specification.

## Consequences

- Final input selection is manifest-driven and fail-closed.
- Processed Parquet must remain traceable to the authoritative raw release.
- Primary analytical precision is `float64`; legacy behavior does not rewrite
  the specification.
- Silent scale fallback and test-informed engine choice are prohibited.
- Exact versions and execution evidence are `OPEN_FOR_SPRINT2`, yielding
  `PASS_WITH_LIMITATION` rather than a Sprint 1 blocker.
