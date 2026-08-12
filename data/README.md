# Data directory

## Data is not version controlled

Raw and processed data are local inputs and must not be committed. Only this
README is intended for version control under `data/`.

The repository MIT License applies to repository code and documentation. It
does not license or relicense CRITEO-UPLIFTv2.1; the dataset remains subject to
the publisher's separate terms and license.

## Expected local layout

```text
data/
├── README.md
├── raw/          local authoritative release input
└── processed/    local analytical derivative
```

Do not place row-level samples, predictions, models, audit outputs, or logs in a
version-controlled path.

## Authoritative dataset

The active analytical dataset is **CRITEO-UPLIFTv2.1**. The local canonical
compressed artifact has been reconciled to the SHA-256 and byte size published
for `criteo-research-uplift-v2.1.csv.gz` in Criteo's public Hugging Face dataset
repository. The local working CSV also matches the streamed decompressed content
of that compressed artifact. The evidence manifest records the exact values and
reference; this README does not duplicate them as a second source of truth.

The authoritative publisher license/citation and any environment-specific local
paths remain explicit manifest metadata and must not be invented. T01 has now
recorded ordered CSV-to-Parquet value/schema identity evidence and repeated-write
physical determinism in the benchmark environment. ZSTD with the retained fixed
row-group layout is selected for the production derivative. The codec benchmark
held `row_group_size = 1,048,576` constant and did not test or optimize
row-group-size alternatives. The T01 notebook has generated the
manifest-selected ZSTD derivative with source-row ordinals and immutable
run-scoped lineage/verification evidence; independent review remains pending.

The raw release is authoritative. Processed Parquet is a derived analytical
format and must preserve documented lineage to that raw release; the two files
are not independent sources with equal authority.

The stable local production derivative is
`data/processed/criteo-uplift-v2.1.parquet`. Task identifiers do not enter this
durable dataset filename. A conversion writes and verifies a run-scoped
temporary candidate before rollback-protected promotion to that path. Caught
exceptions restore the previous derivative; an interrupted or ambiguous backup
state fails closed for explicit validation and recovery. This is not claimed to
be a true crash-atomic filesystem replacement.

## Expected columns

- numeric features `f0` through `f11`;
- binary `treatment` assignment;
- optional post-assignment/audit field `exposure`;
- optional secondary outcome `visit`; and
- binary primary outcome `conversion`.

Additional columns do not enter `X` unless a future owner-approved contract
explicitly changes the feature set.

## Causal usage

- `X` is exactly ordered `f0`–`f11`.
- `treatment` is assignment and defines `T`.
- `conversion` is primary `Y`.
- `visit` is an optional secondary outcome in a separate pipeline.
- `exposure` is post-assignment/audit-only and cannot enter primary `X`, define
  eligibility, filter the primary population, or replace treatment assignment.

## Verification

Every executable run must use an explicit data manifest/configuration and fail
closed on missing or ambiguous input. Verification includes schema and label
validation, primary `float64` analytical precision, row-count reconciliation,
SHA-256 checksums, conversion configuration, tool versions, and processed-to-raw
lineage.

Generation may begin with `processed_sha256: null`; it records the final hash
only after the candidate passes validation and promotion. Before consumption,
copy that completed-run hash into the mutable selector. The reusable consumer
verifies it before opening Parquet and rejects missing or mismatched identity.

Input must not be selected by filename order, preferred substrings, extension,
or directory heuristics. Actual row counts and checksums are Sprint 2 execution
evidence, not Sprint 1 documentation claims.

Use [`configs/data_manifest.example.json`](../configs/data_manifest.example.json)
as the committed non-secret template and populate the ignored
`configs/data_manifest.json` as the mutable local selector. Each run copies its
resolved identities and conversion settings to the immutable
`outputs/runs/<run_id>/audit/data_manifest.json` snapshot. Do not commit the
populated selector if it contains machine-specific paths or restricted
metadata.

## Security and privacy

- Do not commit raw or processed rows.
- Do not commit row-level samples, predictions, pseudo-outcomes, fold outputs,
  bootstrap draws, or model artifacts.
- Do not commit logs or manifests containing personal local paths, credentials,
  tokens, or restricted source locations.
- Review every proposed artifact for aggregation, lineage, and publisher-license
  compliance before sharing.
