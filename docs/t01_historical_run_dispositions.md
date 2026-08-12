# T01 historical run disposition index

## Scope and authority

This file is retrospective governance metadata created after formal T01 review.
It classifies historical benchmark attempt directories that did not contain a
closing `artifact_manifest.json`. It does not alter, complete, or replace their
original evidence, and it must not be interpreted as a retroactively generated
run manifest.

The original files under `outputs/runs/<run_id>/audit/` remain the historical
record. The completed decision-evidence benchmark
`t01_benchmark_20260812T040838Z_649715` and completed production run
`t01_production_20260812T073523Z_437823` are the superseding authoritative
evidence for their respective purposes.

## Dispositions

| Run ID | Observed status | Why it is not authoritative production evidence | Superseded by | Useful retained evidence | Retention disposition |
|---|---|---|---|---|---|
| `t01_benchmark_20260812T040601Z_717461` | `INCOMPLETE_BEFORE_RECONCILIATION`; only `environment.json` exists | No reconciliation, benchmark result, run configuration, or closing artifact manifest was produced. | Completed benchmark `t01_benchmark_20260812T040838Z_649715` | Environment and dirty-code-state record at attempt start | Retain the original small JSON unchanged as aborted-attempt evidence. |
| `t01_benchmark_20260812T040622Z_664558` | `INCOMPLETE_DIAGNOSTIC_FAILURE`; reconciliation reports `semantic_identity: FAIL` | It compared the raw CSV with the pre-T01 exploratory Parquet at the then-canonical filename (SHA-256 prefix `1f85ab37`) and stopped without benchmark/config/closing-manifest evidence. | Completed benchmark `t01_benchmark_20260812T040838Z_649715`; canonical production run `t01_production_20260812T073523Z_437823` | Exact environment, identities, semantic digests, first mismatch at `f0`/row 0, and resource observations | Retain both original JSON files unchanged as diagnostic failure evidence. |
| `t01_benchmark_20260812T043128Z_903896` | `INCOMPLETE_DIAGNOSTIC_FAILURE`; reconciliation reports `semantic_identity: FAIL` | Same exploratory-derivative reconciliation failure; no completed codec benchmark or closing manifest was produced. | Completed benchmark `t01_benchmark_20260812T040838Z_649715`; canonical production run `t01_production_20260812T073523Z_437823` | Exact environment, identities, mismatch location, semantic digests, and resource observations | Retain both original JSON files unchanged as diagnostic failure evidence. |
| `t01_benchmark_20260812T043513Z_884729` | `INCOMPLETE_DIAGNOSTIC_FAILURE`; reconciliation reports `semantic_identity: FAIL` | Same exploratory-derivative reconciliation failure; no completed codec benchmark or closing manifest was produced. | Completed benchmark `t01_benchmark_20260812T040838Z_649715`; canonical production run `t01_production_20260812T073523Z_437823` | Exact environment, identities, mismatch location, semantic digests, and resource observations | Retain both original JSON files unchanged as diagnostic failure evidence. |
| `t01_benchmark_20260812T072258Z_338096` | `INCOMPLETE_DIAGNOSTIC_FAILURE`; reconciliation reports `semantic_identity: FAIL` | It again inspected the surviving exploratory Parquet identity at the canonical filename and stopped before a completed benchmark package or closing manifest. | Completed benchmark `t01_benchmark_20260812T040838Z_649715`; corrected canonical production run `t01_production_20260812T073523Z_437823` | Exact environment/code state, identities, mismatch location, semantic digests, and resource observations | Retain both original JSON files unchanged as diagnostic failure evidence. |

No listed attempt contains a large temporary Parquet candidate. No cleanup is
required for these directories; their small JSON evidence remains retained.
