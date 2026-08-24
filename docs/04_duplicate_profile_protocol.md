# Duplicate-profile protocol

## Purpose and governing principle

This protocol defines repeatable-value and row-identity checks without assuming
that equal rows are duplicate people. The active public schema has no user ID.
No duplicate count or origin conclusion is recorded here.

The default analysis preserves all loaded rows. Removing, collapsing, grouping,
or reweighting rows is not permitted merely because values repeat.

**D33 scope note.** Only DP-01 (source-row identity: uniqueness, split
disjointness, row accounting) is mandatory — it is already covered by HG-07.
DP-02 through DP-07 (detailed profile taxonomy, cross-split profile overlap
beyond leakage interpretation, precision/collision reconciliation) are
optional/sensitivity diagnostics: useful when investigating a specific
question, never a required precondition for any P0 task. This document's
algorithms and definitions are unchanged; only their mandatory-vs-optional
status is reclassified.

`DEFERRED`: any alternative primary duplicate-removal or weighting policy. Sprint
1 keeps all loaded rows. A source-backed pipeline error is corrected at origin;
development-only sensitivity cannot change the primary policy without a future
ADR completed before a new freeze.

## Identities and duplicate definitions

All comparisons use explicit column lists and report rows in duplicate groups,
rows beyond the first, group count, largest group, and cross-split group count.

| ID | Definition | Columns | Class and interpretation |
|---|---|---|---|
| DP-01 | Source-row identity duplication | `_source_row_id` | **HARD_GATE**: canonical source ordinals must be complete and unique before splitting and disjoint across splits. Repetition is a split/data-pipeline failure. |
| DP-02 | Exact loaded-value profile | `f0`–`f11`, `treatment`, `conversion`, plus `visit`/`exposure` when present | **EMPIRICAL_DIAGNOSTIC**: equal processed values; not a person identity. Precision and conversion may create equality. |
| DP-03 | Feature profile | `f0`–`f11` | **EMPIRICAL_DIAGNOSTIC**: rows indistinguishable to permitted models. Expected or problematic status cannot be inferred from count alone. |
| DP-04 | Feature-plus-treatment profile | `f0`–`f11`, `treatment` | **EMPIRICAL_DIAGNOSTIC**: repeated model inputs within an arm. |
| DP-05 | Feature-plus-treatment-outcome profile | `f0`–`f11`, `treatment`, `conversion` | **EMPIRICAL_DIAGNOSTIC**: repeated analytical values excluding optional audit fields. |
| DP-06 | Cross-split value-profile overlap | Each DP-02 through DP-05 profile, grouped by split | **EMPIRICAL_DIAGNOSTIC**: repeated values across splits. This is not row leakage unless DP-01 identities overlap. |
| DP-07 | Source-to-processed collision | Source-precision values versus the same fields cast to processed precision and versus Parquet | **EMPIRICAL_DIAGNOSTIC**: distinguishes source repetition from equality introduced or changed by casting/conversion. |

Rows sharing `X` but differing in `T` or `Y` are not contradictory duplicates.
They are distinct observations with the same available feature profile and may be
informative about overlap and outcome variation. They must not be reconciled by
overwriting labels.

## Required sequence

### 1. Freeze comparison inputs

Record source and processed paths, checksums when available, row counts, schemas,
column order, numeric precision, conversion command, and tool versions. A
row-limited run is a smoke test only and cannot support a final origin conclusion.

The active source checksum is recorded in the execution manifest. T01-D03 uses
the zero-based canonical source-row ordinal as the durable released-row identity;
it is not a person identifier.

### 2. Establish source-row identity

Preserve `_source_row_id` from the checksum-identified canonical source through
conversion and any sampling, before any split. Verify it is complete and unique
in the active frame. Do not regenerate or renumber it inside a sample or split,
and do not call it a user ID.

### 3. Profile the unsplit loaded sample

Compute DP-02 through DP-05 before any optional row removal. Retain the original
sample and report definitions, columns, precision, counts, and hashes/methods.
Hash-based grouping must disclose hash width and collision limitations; exact
column comparison is preferred for any adjudicated group.

### 4. Verify split integrity

Apply DP-01 after splitting. Any `_source_row_id` overlap or row-accounting loss is
a **HARD_GATE** failure: stop, correct the split pipeline, and rerun. Do not solve
identity overlap by dropping rows from validation or test.

Compute DP-06 for descriptive leakage risk. Cross-split equality of anonymous
feature profiles is not itself a gate failure because distinct rows can share
features. Its interpretation must account for profile frequency and the absence
of person identity.

### 5. Investigate origin when source data are available

For the same declared columns and row universe, compare:

1. source values at source precision;
2. source values after applying the legacy/sensitivity numeric cast, currently
   `float32` for `f0`–`f11` in repository code; primary analytical precision is
   `float64` under D09;
3. processed Parquet values.

Also reconcile source and processed row counts. Differences can indicate casting
collisions, filtering, duplication, deduplication, parsing changes, or a mismatched
file; they do not identify a cause without further evidence. The repository's
`scripts/check_duplicate_origin.py` is an implementation aid, not an audit result.

### 6. Compare duplicate-group characteristics

As **EMPIRICAL_DIAGNOSTIC** evidence, compare treatment and outcome support for
members and non-members of each profile definition using a predeclared
development population. Do not use final-test outcomes to decide whether to keep
or remove repeated profiles.

### 7. Decide action before final-test release

The allowed default is **keep all loaded rows**. A source-backed pipeline error
must be corrected at its origin and fully reprocessed. A deduplication or weighting
sensitivity, if later authorized, must:

- define the exact columns and keep/drop/weight rule in advance;
- be fit and assessed only within the permitted development process;
- preserve the no-removal Sprint 1 primary analysis;
- report changed sample composition and estimand implications;
- avoid using final-test results to select the primary policy.

The existing code path that compares a deduplicated sensitivity on a test
partition is non-conforming. Document 06 confines this sensitivity to training
and validation before freeze; it is not run on the held-out test even as a
post-final model-selection analysis.

## Decision table

| Observation | Required classification | Required action |
|---|---|---|
| Repeated `_source_row_id` within or across splits | HARD_GATE failure | Stop; correct identity/split construction; retain evidence of the failed run. |
| Exact source rows repeated at source precision | EMPIRICAL_DIAGNOSTIC finding | Preserve by default; investigate publisher/design semantics; do not call duplicate users. |
| New equalities appear only after `float32` casting | EMPIRICAL_DIAGNOSTIC finding | Qualify duplicates as sensitivity-only precision collisions; preserve D09 primary `float64` unless a new owner-approved decision changes it. |
| Processed counts/profiles disagree with like-for-like transformed source | HARD_GATE for lineage if input is intended for a final run | Stop; identify conversion, filtering, or file mismatch before proceeding. |
| Feature profiles span splits but row IDs do not | EMPIRICAL_DIAGNOSTIC | Report frequency and possible memorization/uncertainty implications; do not delete automatically. |
| Same `X` has different `T` or `Y` | EMPIRICAL_DIAGNOSTIC, not label conflict | Preserve observations; summarize arm/outcome support. |
| No source file or durable identity is available | ASSUMPTION_SUPPORT_OR_LIMITATION | State that origin and person-level duplication cannot be resolved. |

## Required artifacts for an executed duplicate audit

- input manifest and checksums;
- DP-01 source-row identity result (mandatory: uniqueness, split disjointness,
  row accounting);
- status, interpretation, limitations, and decision IDs;
- explicit statement that no result identifies duplicate users without an
  appropriate source identity.

Optional/sensitivity, when DP-02 through DP-07 are run (D33): definition table
with exact column lists and precision, machine-readable DP-02 through DP-07
summaries, source/processed row-count reconciliation, group-characteristic
summaries on the permitted population, and any investigated example groups
with sensitive values excluded.

No numeric value, PASS/FAIL result, or origin conclusion belongs in this protocol.
