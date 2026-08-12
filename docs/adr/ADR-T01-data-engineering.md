# ADR: T01 data-engineering implementation

**Status:** ACCEPTED

**Issue:** T01 — Dataset Loading & Data Engineering Pipeline

**Decision authority:** Owner-approved `decision_register.csv`, especially
D06, D09, D19, D20, D21, and D23

**Decision status:** T01-D01 through T01-D06 are `ACCEPTED`

**Implementation status:** `IMPLEMENTED_AWAITING_REVIEW`

## Context

T01 must turn the approved CRITEO-UPLIFTv2.1 raw artifact into a reusable
analytical Parquet derivative without creating a second data source of truth.
The higher-authority data and experiment contracts fix the schema, primary
`float64` precision, manifest-driven selection, row preservation, scale
progression, and held-out isolation. This ADR records only implementation
choices within those constraints.

The primary T01 human-readable artifact is
`notebooks/02_data_engineering_pipeline.ipynb`. It contains the predeclared
protocol, visible execution, checks, evidence links, observations, and
interpretation limits. `src/`, `tests/`, and `scripts/` are optional supporting
infrastructure only when concretely justified; this ADR does not require a
package, preparation script, or test suite merely for architectural symmetry.

The canonical compressed artifact has been independently reconciled with the
SHA-256 and byte size published in Criteo's public Hugging Face dataset
repository. Its streamed decompressed bytes also reconcile with the local
working CSV. T01 decision-evidence runs recorded exact ordered CSV-to-Parquet
semantic identity, repeated-write physical determinism in the benchmark
environment, full-data materialization observations, and the bounded
Snappy-versus-ZSTD comparison. The notebook-first production conversion has now
generated run-scoped lineage and verification evidence; independent review
remains open, so this ADR does not declare Issue #2 complete.

## Decision summary

| ID | Implementation decision | Status |
|---|---|---|
| T01-D01 | PyArrow Dataset/Scanner is the low-level loading path; conversion to Pandas is explicit at the consumer boundary. | `ACCEPTED` |
| T01-D02 | Byte identity is expected for reruns in a declared equivalent/pinned physical environment; semantic identity is mandatory. | `ACCEPTED` |
| T01-D03 | The zero-based canonical source-row ordinal is the provenance/observation identity and is never a feature. | `ACCEPTED` |
| T01-D04 | Use operation-specific resource failure rules; do not impose a universal fixed RAM-percentage threshold. | `ACCEPTED` |
| T01-D05 | A mutable environment-specific local selector is separate from the immutable normalized per-run manifest snapshot. | `ACCEPTED` |
| T01-D06 | Use ZSTD and retain the fixed row-group layout unless later evidence supports a separately reviewed change. | `ACCEPTED` |

No row in this table changes the frozen causal estimand, population, variable
roles, duplicate policy, split, metrics, model scope, uncertainty protocol, or
test boundary.

## T01-D01 — Loader contract

**Status: `ACCEPTED`.**

PyArrow Dataset/Scanner is the low-level path for schema inspection, column
projection, filtering permitted by an explicit caller, and record-batch
iteration. Pandas materialization is an explicit operation rather than an
automatic side effect of opening the dataset.

The public loader contract must therefore distinguish at least:

- generating and validating a processed derivative before its final checksum is
  available;
- consuming a manifest-selected Arrow dataset only after verifying its expected
  processed SHA-256;
- iterating deterministic batches or scanning selected columns; and
- explicitly materializing a declared population and column set as a Pandas
  DataFrame for consumers that require it.

This implements D20's Pandas + PyArrow default. It does not promote DuckDB or
Polars. Full-data materialization is used only when required by the consumer and
when the applicable D23 resource evidence supports it.

## T01-D02 — Determinism and identity

**Status: `ACCEPTED`.**

Two identity levels are required:

1. **Semantic identity — mandatory.** Source and processed artifacts must
   reconcile on canonical column order, physical/analytical types, row count,
   row order, null masks, and every parsed value. A streaming canonical content
   digest may summarize this comparison, but it does not replace mismatch
   reporting.
2. **Physical byte identity — expected in a pinned equivalent environment.**
   Repeating the same conversion with the same source hash, code, configuration,
   interpreter/packages, compression, row-group size, and writer settings is
   expected to produce the same Parquet SHA-256. If bytes differ while semantic
   identity passes, record the physical metadata difference and do not silently
   call the rerun byte-identical.

Semantic identity failure is a STOP condition. Physical inequality is also a
STOP for the claimed pinned-equivalent reproduction until explained and the
environment/configuration record is corrected. This is an engineering
reproducibility rule, not a statistical tolerance or causal-identification
claim.

## T01-D03 — Source-row ordinal

**Status: `ACCEPTED`.**

`_source_row_id` is the zero-based ordinal of the data row in the canonical
decompressed CSV, excluding the header. It is assigned or reconstructed during
conversion, preserved without modification in derived membership/manifests, and
serves as the stable observation identity for split and artifact alignment.

The identifier:

- is unique only at the released-row level, not at person or user level;
- carries no business semantics;
- is excluded from `X` and every model input;
- does not authorize deduplication or population filtering; and
- is meaningful only together with the canonical raw artifact checksum.

Any filtering or sampling retains the original source ordinal; it must not
renumber surviving rows. The frozen split procedure may use this identity for
disjointness and deterministic tie-breaking without changing the split policy.

## T01-D04 — Resource and fallback gate

**Status: `ACCEPTED`.**

There is no universal fixed RAM-percentage threshold. PyArrow Dataset/Scanner
with projection and batching is the default execution path. Full Pandas
materialization is permitted only as an explicit, operation-specific action when
the consumer genuinely requires it.

A scale/resource gate fails when the declared execution:

1. raises an out-of-memory condition or the process is killed;
2. cannot complete correctly;
3. exhibits sustained severe system-memory or pagefile pressure that makes the
   declared environment operationally unsuitable; or
4. violates a separately declared operational execution budget.

Process RSS alone is not sufficient evidence of machine safety. No `70%`, `80%`,
or other universal memory-percentage boundary is part of this project.

Evidence must be collected on the current 16-GB development machine using the
Pandas + PyArrow default and the frozen `50K → 500K → 2M → full` progression.
For each rung record wall-clock runtime, peak process RSS, row count, schema,
dtypes, and any OOM or obvious swapping/resource failure.

Observed development evidence includes the full frozen ladder and a separate
clean-kernel full-only confirmation. In the controlled confirmation, the
13,979,592-row operation completed with the required row/schema/dtype/order and
source-identity checks. Process RSS started at 154,152,960 bytes and peaked at
2,359,005,184 bytes; system-available memory started at 847,343,616 bytes and the
sampled minimum was 176,128 bytes; pagefile/swap used increased by
1,207,156,736 bytes while the available Windows I/O delta counters remained
zero. Runtime was 4.677 seconds. These are machine-state observations, not a
universal PASS/WARN/FAIL threshold or a claim that eager full-data Pandas is
generally safe. In approximate terms, peak process RSS was 2.20 GiB, the machine
began at 94.9% physical-memory usage, available physical memory approached
exhaustion, and pagefile usage increased by about 1.12 GiB. No OOM occurred.
This demonstrates feasibility under severe pressure, not a universally safe
memory percentage.

The first confirmation attempt,
`t01_d04_confirmation_20260812T043024Z_452058`, is retained but is not used as
the clean-process comparison because the full streaming source reconciliation
ran in the same process immediately beforehand and raised its starting RSS. The
reported controlled result is
`t01_d04_confirmation_20260812T043244Z_565265`, which instead verifies current
file hashes against the SHA-256-pinned full reconciliation artifact before the
isolated materialization.

The evidence run and this decision do not promote DuckDB or Polars. Any fallback
still requires the bounded D20 comparison and must be tied to a documented
failure of the default path under the operational rule above.

## T01-D05 — Manifest governance

**Status: `ACCEPTED`.**

Two artifacts have different responsibilities:

1. **Local selector.** The mutable, environment-specific, uncommitted
   `configs/data_manifest.json` supplies local paths and the intended run
   inputs. It may change when execution moves between local and Kaggle
   environments. The committed `configs/data_manifest.example.json` is only its
   path-free template and is not execution evidence.
2. **Per-run snapshot.** At run start, the pipeline resolves and normalizes the
   selector into `outputs/runs/<run_id>/audit/data_manifest.json`. The snapshot
   records portable artifact identities, checksums, schemas, conversion
   configuration, tool versions, and lineage. It is immutable with the run and
   is hashed by `audit/artifact_manifest.json`.

The snapshot is authoritative evidence for that run; the mutable selector is
not. Neither artifact may silently select input by filename order or directory
heuristics. Machine-specific absolute paths and restricted metadata must not be
committed.

Generation may start with `processed_sha256: null` because the derivative does
not yet exist. After validation and promotion, its SHA-256 is recorded in the
immutable run evidence. Before later analytical consumption, that completed-run
value is pinned into the mutable selector; the reusable loader verifies it before
opening the Parquet file. A missing or mismatched expected checksum fails closed.

## T01-D06 — Parquet physical layout

**Status: `ACCEPTED`.**

Use ZSTD compression. Retain the fixed row-group size of `1,048,576` rows and
the held-constant writer layout unless later evidence justifies a separate,
explicitly reviewed change. The benchmark compared Snappy with ZSTD while this
row-group size was fixed; it did not evaluate row-group alternatives, so the
retained size is not claimed to be benchmark-optimized or optimal.

The stable production derivative is
`data/processed/criteo-uplift-v2.1.parquet`. `T01` identifies the task that
creates and verifies this derivative; it is not part of the durable dataset
filename. Run-scoped temporary candidates may use implementation-specific names
but are not authoritative consumer paths. Promotion is rollback-protected for
caught exceptions, not a true crash-atomic filesystem replacement: if startup
or a later promotion finds a `.previous.tmp` backup, it changes no files and
fails closed with explicit validation/restoration instructions. It never
silently discards an ambiguous backup left by an abrupt interruption.

The bounded benchmark compares exactly:

- A: Snappy; and
- B: ZSTD.

Row-group size, schema, column order, source order, writer version, and all
other writer settings remain identical. Where practical, run three repetitions
and report median write time, read time, peak RSS, file size, variability, and
failures. Every candidate must pass row-count, schema, dtype, ordering, and
semantic-identity checks.

The completed benchmark produced three verified repetitions for each candidate.
Snappy used 284,930,086 bytes with median write/read times of 4.546/1.887
seconds; ZSTD used 208,039,244 bytes with median write/read times of 4.862/1.247
seconds. All candidates passed row/schema/dtype/order and semantic-identity
checks, and repeated writes were physically deterministic in the declared
benchmark environment. Relative to Snappy in this bounded workload, ZSTD was
approximately 27% smaller, had materially lower median repeated-read time, and
had approximately 7% higher median write time. The write penalty is accepted
because conversion is infrequent while analytical reads recur.

Same-process RSS observations are order/allocator-confounded and did not select
the codec. This is a project- and workload-specific choice; it does not claim
that ZSTD is universally faster or universally lower-memory.

## Benchmark evidence contract

The protocol is written before execution in
`notebooks/02_data_engineering_pipeline.ipynb`. Machine-readable results live
under one immutable-style development run root:

```text
outputs/runs/<run_id>/audit/t01_resource_benchmark.json
outputs/runs/<run_id>/audit/t01_parquet_compression_benchmark.json
outputs/runs/<run_id>/audit/t01_d04_full_memory_confirmation.json
outputs/runs/<run_id>/audit/t01_source_reconciliation_reference.json
outputs/runs/<run_id>/audit/environment.json
outputs/runs/<run_id>/audit/run_config.json
outputs/runs/<run_id>/audit/artifact_manifest.json
```

Benchmark artifacts must record the source hashes, code revision or dirty-state
marker, environment, settings, repetitions, raw measurements, summaries, and
verification outcomes. They contain no held-out evaluation, model training, or
decision disguised as a PASS threshold.

Historical benchmark attempts without closing manifests are classified in the
[T01 historical run disposition index](../t01_historical_run_dispositions.md).
That retrospective index does not rewrite or promote their original evidence.

## Verification and status transition

The decision-evidence and owner-review conditions are satisfied, so this ADR is
**ACCEPTED**. Historical benchmark JSON and executed notebook outputs retain the
pre-decision `PENDING_EMPIRICAL_EVIDENCE` wording because they truthfully record
the state when generated; this ADR is the subsequent owner-approved resolution.

ADR acceptance freezes the T01 implementation choices only. The T01 notebook has
now executed production conversion, normalized run-manifest generation, D23,
semantic/determinism checks, and failure-path verification. Those implementation
claims remain subject to independent review under Issue #2 and are not promoted
to model, split, or held-out evidence.

## Consequences

- Consumers obtain a clear lazy/batch path and opt into Pandas materialization.
- Processed-data consumption verifies a pinned SHA-256 before Arrow opens the
  artifact; generation records the final checksum after validated promotion.
- Processed Parquet remains a derivative of the checksum-identified raw source.
- Stable row alignment is possible without claiming a person identifier.
- Resource suitability is judged operationally per declared environment and
  operation, without a fabricated universal RAM percentage.
- ZSTD is the accepted T01 codec under the retained fixed row-group layout; no
  row-group-size alternatives were benchmarked.
- No alternative data engine is promoted by this decision or benchmark.
- T01 implementation evidence is available and awaits independent Issue #2 review.
