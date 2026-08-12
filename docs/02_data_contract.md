# Data contract

## Contract status and dataset identity

This document is the source of truth for the active analytical data, schema,
column roles, validation gates, and lineage requirements. It contains no measured
dataset statistics.

The active released population is **CRITEO-UPLIFTv2.1**, consistent with the
[causal population contract](01_causal_contract.md#primary-eligibility-and-target-population).
The authoritative download location, license/citation, compressed-source
checksum, and processed-file checksum are Sprint 2 manifest evidence. Their
actual values are not required to complete the Sprint 1 specification, but they
must be recorded before an auditable executable run.

`archive/README_original_attribution_dataset.md` describes a different
impression-level attribution dataset with timestamp, user, campaign, and cost
fields. It is historical context and is not an allowed substitute for the active
uplift data. A file matching that archived schema fails this contract.

## Row unit and population

The analytical unit is one row in the active public uplift file. The schema does
not contain a durable public user identifier, so equal-value rows are not evidence
of a duplicated user and a row must not be called a unique user.

The [primary eligibility and target-population contract](01_causal_contract.md#primary-eligibility-and-target-population)
locks the unit as one released CRITEO-UPLIFTv2.1 row and the primary population
as all released rows passing hard data-integrity gates. Publisher metadata about
the collection window and sampling design remains source evidence for external
validity, not an open primary-population decision. No external transport claim
is permitted without that additional evidence.

## Canonical schema and roles

| Columns | Presence | Type/value contract | Role |
|---|---|---|---|
| `f0`–`f11` | required | Numeric; infinite values forbidden. Missingness is reported and handled only under a predeclared policy. | `X`, exactly in canonical numeric order. |
| `treatment` | required | Complete binary values in `{0,1}`; labels are never silently remapped or imputed. | `T`, treatment assignment; forbidden from `X`. |
| `conversion` | required | Complete binary values in `{0,1}`; labels are never silently remapped or imputed. | `Y`, primary outcome; forbidden from `X`. |
| `visit` | optional | If used under D02, complete binary values in `{0,1}`; retained without using it to define `X`, `T`, primary `Y=conversion`, or the primary population. | Secondary robustness outcome; otherwise descriptive audit field. |
| `exposure` | optional | If present, retained without using it to define `X`, replace `T`, define `Y`, or filter the primary population. | Audit-only. |
| `_source_row_id` | generated from the canonical source | Complete and unique zero-based data-row ordinal in the checksum-identified decompressed CSV, excluding the header. | Provenance/observation identity, split integrity, deterministic tie-breaking, and artifact alignment only; forbidden from `X`. |

Thus the only valid mappings are:

```text
X = [f0, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11]
T = treatment
Y = conversion
```

Any other mapping is a contract violation, not an experimental variant.

`PROVISIONAL`: `f0`–`f11` are treated operationally as pre-treatment features,
while `visit` and `exposure` are treated conservatively as post-assignment
variables. Primary-source definitions and timestamps are still required. This
uncertainty strengthens, rather than relaxes, their exclusion from `X`.

## Processed-data location and selection

The confirmed repository convention is a Parquet file under `data/processed/`.
T01-D05 requires an explicit mutable local selector for environment-specific
paths and a separate immutable normalized snapshot at
`outputs/runs/<run_id>/audit/data_manifest.json`. Heuristic selection by
filename, extension, directory order, or preferred substring is non-conforming.

If a selector is missing, ambiguous, checksum-incompatible, or points to a
schema-incompatible candidate, the workflow stops. The immutable per-run
snapshot records the resolved raw and processed identities and is hashed by the
run artifact manifest. Implementation details are controlled by
[ADR-T01-data-engineering](adr/ADR-T01-data-engineering.md).

## HARD_GATE validation

Before modeling or any outcome-based evaluation, record each gate and its
evidence location. Failure stops the affected run.

1. The selected input is readable Parquet and is the manifest-selected file for
   an auditable final run.
2. The sample is non-empty.
3. All required columns exist: exactly the twelve feature names plus
   `treatment` and `conversion`. Additional columns may be loaded only when their
   roles are declared; they do not expand `X`.
4. `X` supplied to every model is exactly `f0` through `f11` in canonical order.
5. `treatment`, `conversion`, `visit`, `exposure`, `_source_row_id`, and all
   undeclared columns are absent from `X`.
6. `treatment` and `conversion` are complete and contain only `0` and `1`; no
   label is modified, imputed, or inferred.
   If `visit` is frozen as the D02 secondary outcome, it must independently be
   complete and binary on the declared evaluation population; failure disables
   the secondary analysis but cannot redefine primary `Y=conversion`.
7. All `f0`–`f11` fields are numeric and contain no positive or negative infinity.
   Missing feature values are not silently filled; they are reported and may be
   retained only under the frozen handling rule in the experiment protocol.
8. `_source_row_id` preserves the original zero-based canonical source-row
   ordinal through conversion and any sampling, is complete and unique in the
   active frame before splitting, and is disjoint across train, validation, and
   test. Sampling or filtering must not renumber retained observations. Row
   counts reconcile across the split.
9. Each split contains treatment and control observations and both outcome
   classes in both arms where the configured learner/evaluator requires them.
10. The final-test partition is not used to select data transformations,
    imputation, duplicate policy, audit thresholds, features, methods,
    hyperparameters, early stopping, models, or targeting rules.

The [audit specification](03_assumption_and_audit_spec.md) defines reporting and
classification. Duplicate-related checks follow the
[duplicate-profile protocol](04_duplicate_profile_protocol.md).

## EMPIRICAL_DIAGNOSTIC data summaries

The following are reported, not prefilled in this specification:

- row and column counts, physical schema, row groups, file sizes, and checksums;
- missing counts/fractions and finite-value checks by column;
- treatment/control and outcome support, without treating observed balance as
  proof of randomization;
- feature distributions and ranges by arm;
- duplicate-profile summaries under every named definition in document 04;
- source-to-processed row-count and precision comparisons when the source file is
  available.

No diagnostic value is supplied or implied here.

## Data lineage and numeric precision

An auditable conversion record must contain source and destination paths,
cryptographic checksums, source/processed row counts, schemas, tool versions,
conversion command/configuration, timestamps, and any cast or filter.

Current loading code casts `f0`–`f11` to `float32`. Because this can merge values
that were distinct at higher precision, exact duplicate conclusions on processed
data alone cannot establish source duplication. The origin procedure in document
04 compares source precision, the corresponding `float32` projection, and the
processed Parquet.

D09 fixes `float64` as the primary analytical precision. `float32` is a
sensitivity projection only unless a new owner-approved register decision
changes the primary precision. The manifest must record physical and analytical
precision, and duplicate interpretations must remain precision-qualified.

## `_source_row_id` scope and limitation

T01-D03 resolves the prior implementation question: `_source_row_id` is the
zero-based ordinal of the data row in the checksum-identified canonical
decompressed CSV, excluding the header. Its identity is therefore meaningful
only together with that raw checksum. It can locate and align a released row
across deterministic derivatives, samples, splits, predictions, and runs that
share the same canonical source.

It cannot establish a unique person, infer user identity, or show that distinct
rows with equal values are accidental duplicates. It is forbidden from `X` and
from eligibility or deduplication decisions. The implementation and verification
details are controlled by
[ADR-T01-data-engineering](adr/ADR-T01-data-engineering.md).

## ASSUMPTION_SUPPORT_OR_LIMITATION items

- Publisher evidence for treatment assignment and field timing is missing from
  the documentation.
- Anonymous features restrict substantive interpretation and transport claims.
- Absence of a public user identifier prevents person-level duplication and
  within-person interference audits.
- The observational record cannot reveal both potential outcomes or true ITE.
- Data quality and balance diagnostics cannot prove the causal assumptions.
