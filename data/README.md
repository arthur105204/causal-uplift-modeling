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

The active analytical dataset is **CRITEO-UPLIFTv2.1**. The owner-approved
documentation does not yet freeze an authoritative download URL, publisher
license text, release identifier, or checksum value. Those values must not be
invented here. Sprint 2 records them in an explicit manifest before an auditable
run.

The raw release is authoritative. Processed Parquet is a derived analytical
format and must preserve documented lineage to that raw release; the two files
are not independent sources with equal authority.

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

Input must not be selected by filename order, preferred substrings, extension,
or directory heuristics. Actual row counts and checksums are Sprint 2 execution
evidence, not Sprint 1 documentation claims.

Use [`configs/data_manifest.example.json`](../configs/data_manifest.example.json)
as a non-secret template. Do not commit the populated local manifest if it
contains machine-specific paths or restricted metadata.

## Security and privacy

- Do not commit raw or processed rows.
- Do not commit row-level samples, predictions, pseudo-outcomes, fold outputs,
  bootstrap draws, or model artifacts.
- Do not commit logs or manifests containing personal local paths, credentials,
  tokens, or restricted source locations.
- Review every proposed artifact for aggregation, lineage, and publisher-license
  compliance before sharing.
