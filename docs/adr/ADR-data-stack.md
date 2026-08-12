# ADR: Provisional data-stack implementation

**Status:** PROVISIONAL  
**Decision authority:** Owner-approved `decision_register.csv` decisions D09,
D19, D20, D21, and D23  
**Sprint 1 assessment:** PASS_WITH_LIMITATION  
**Execution status:** T01_DATA_ENGINEERING_VERIFIED; D20_FALLBACK_PROVISIONAL;
FULL_ENVIRONMENT_LOCK_UNAVAILABLE

## Context

The owner-approved direction uses Parquet for analytical storage and Pandas plus
PyArrow as the default data stack. Polars or DuckDB may be considered only under
the bounded benchmark fallback in D20. The technology direction does not replace
the higher-authority [data contract](../02_data_contract.md) or
[experiment protocol](../06_experiment_protocol.md). This ADR references the
recorded T01 data-engineering evidence without reinterpreting it as model,
causal, or held-out evaluation evidence.

## Provisional decision

- Use PyArrow for typed Parquet metadata and columnar I/O.
- Use PyArrow Dataset/Scanner projection and batching as the scalable low-level
  loading path. Use Pandas/NumPy with explicit configuration when a consumer
  genuinely requires materialization; full Pandas materialization is an
  explicit operation, not the default effect of opening the dataset.
- Evaluate Polars or DuckDB only if the default misses a predeclared
  correctness/resource bound and the alternative passes like-for-like identity,
  schema, precision, ordering, and determinism checks.
- Use an explicit manifest/configuration as the sole input selector for an
  auditable run.

T01 production manifests, exact run-environment records, benchmark evidence,
and full-scale execution evidence now exist. The ADR remains `PROVISIONAL`
because D20 still permits a bounded Polars/DuckDB fallback only after a concrete
default-path failure and like-for-like verification; no fallback technology is
promoted here, and a fully pinned environment lock remains unavailable.

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

The canonical compressed-source checksum/size, decompressed-CSV reconciliation,
and ordered CSV-to-Parquet semantic reconciliation are now recorded as Sprint 2
evidence. T01 scale/resource and Snappy-versus-ZSTD observations were reviewed
under [ADR-T01-data-engineering](ADR-T01-data-engineering.md). That accepted ADR
uses an operational resource-failure rule without a universal fixed RAM
percentage and selects ZSTD while retaining a fixed row-group layout. The codec
benchmark held `row_group_size = 1,048,576` constant; it did not test row-group
alternatives or establish an optimum. It does not promote another engine.
Production conversion configuration and immutable per-run data-manifest
snapshots are now recorded in T01 run evidence.

## Numeric representation

D09 and document 02 fix `float64` as the primary analytical precision.
`float32` is sensitivity-only unless a new owner-approved decision changes the
primary representation. No loader, conversion, engine fallback, or model path
may silently coerce primary `f0`–`f11` values to `float32`.

The T01 lineage manifest records source and processed identities, conversion
settings, and primary analytical precision. Future explicit casts must also be
recorded. Precision sensitivities remain separate from the primary population
and interpretation.

## Scale failure

D23 defines the 50K→500K→2M→full correctness/resource progression. Failure at a
scale gate does not authorize a silent 2M→1M or other unregistered fallback.

T01-D04 defines failure operationally: OOM/process termination, incorrect or
incomplete execution, sustained severe system-memory/pagefile pressure that
makes the declared environment unsuitable, or violation of a separately
declared operational budget. Process RSS alone is insufficient evidence of
machine safety, and this project has no universal `70%`, `80%`, or other fixed
RAM-percentage threshold.

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

T01 evidence verifies the manifest-selected file, processed-to-raw lineage,
SHA-256 values, schema, primary precision, row identity, and D23 data-engineering
resource gates. Before pre-test freeze, Sprint 2 must preserve those checks and
add the still-future deterministic split, model, and executable-environment
verification required by the experiment protocol.
An alternative engine must additionally reproduce the declared schema, rows,
identity, ordering or explicit order, and precision of the default path.

Current T01 checksum, conversion, benchmark, and scale-gate evidence is recorded
under immutable run directories. This ADR does not turn those observations into
model/data-quality conclusions or promote a D20 fallback engine.

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
- PyArrow projection/batching is preferred for scalable reads; Pandas
  materialization is explicit and operation-specific.
- ZSTD with the retained fixed row-group layout is the T01 physical Parquet
  convention; only the codec alternatives were benchmarked.
- Primary analytical precision is `float64`; legacy behavior does not rewrite
  the specification.
- Silent scale fallback and test-informed engine choice are prohibited.
- T01 manifests and execution evidence now exist. The missing full environment
  lock and the conditional D20 fallback remain limitations, so this broader ADR
  stays `PROVISIONAL`/`PASS_WITH_LIMITATION`.
