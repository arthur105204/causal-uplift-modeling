# Final Release Audit — Phase 1

Read-only audit of the repository ahead of producing a research memo. No
source, notebook, artifact, or preprocessing code was modified to produce
this report.

**Scope caveat.** This audit covers the git-tracked tree as checked out in an
isolated worktree branched from `main`. Three untracked files observed in the
primary checkout at session start (`docs/TEACHBACK.md`,
`docs/final_release_execution_plan.md`, `docs/lightweight_benchmark_version.md`)
are not tracked by git and were not present in this worktree, so they are not
covered below. If they are meant to ship, audit them directly in the primary
checkout before release.

## Release readiness score: 6 / 10 — not yet release-ready

The modeling, evaluation, and statistical layers are sound and internally
consistent: every number checked in the comparative report traces exactly to
`outputs/*/*/metrics.json`, the paired bootstrap is implemented correctly,
and both experiment notebooks describe the response/causal distinction
correctly with no overclaiming language. The blockers are entirely in
front-door documentation and test coverage, not in the science:

- **README.md misrepresents the project's own core contribution** (claims
  the bootstrap significance test doesn't exist; it does and is the main
  statistical result).
- **README.md's Quickstart and repository structure point at notebook paths
  that no longer exist**, and never mention the three notebooks that are
  the actual deliverable.
- **The statistical core (`paired_bootstrap_gaps`,
  `build_model_comparison_table`) has no unit test.**

None of these require touching model/evaluation code — they are
documentation and test-suite additions, but they should block calling this
release-ready until fixed.

---

## 1. Experiment notebooks (`conversion_experiment.ipynb`, `visit_experiment.ipynb`)

| Finding | Evidence | Severity | Recommended action |
|---|---|---|---|
| Both notebooks consistently and correctly label Response LightGBM as `P(Y\|X)` (non-causal) and T-/X-Learner/Causal Forest as `tau(X)` (CATE) throughout | cells 23, 27, 29, 36 in both notebooks | None (verified correct) | — |
| No overclaiming causal language found | grep for "proves/guarantee/always wins/best customers/definitively" returned only hedged negations (e.g. "should not be reported as definitively superior") | None | — |
| Final-summary outputs match each notebook's own tables and bootstrap conclusions exactly | conversion: 806.23915/942.02699 qini/auuc; visit: 6642.20308/7746.51869; significance conclusions match | None | — |
| Broken cross-reference: markdown points to a "Limitations section at the end of this notebook" that doesn't exist | both notebooks, cells 37 and 45; last sections are "## Scope" then a FINAL SUMMARY code cell — no "Limitations" heading anywhere | Medium | Either add a short Limitations section (the report notebook's can be adapted) or reword the pointer to reference `comparative_analysis_report.ipynb`'s Limitations section |
| Bootstrap cell has no explicit row-alignment assertion between the two models' test rows | cell 36, both notebooks — sorts each model's predictions by `row_id` independently with no equality check, unlike the report notebook's `assert (resp_test["row_id"] == cf_test["row_id"]).all()` in its own bootstrap cell | Low | Add the same explicit assertion for defense-in-depth; practically safe today given the shared pipeline |
| Visit notebook's FINAL SUMMARY prints "Primary outcome: visit," which in isolation could misread as visit being the primary business outcome | cell 55, from `OUTCOME_COLUMN`; mitigated by the adjacent "## Scope" cell correctly calling conversion primary | Low / nitpick | Reword to "Outcome evaluated: visit" to remove ambiguity |

## 2. Comparative report — artifact traceability

| Finding | Evidence | Severity | Recommended action |
|---|---|---|---|
| Every displayed number in Table 1/Table 2 and the bootstrap CI table matches the corresponding `outputs/{conversion,visit}/*/metrics.json` value exactly to displayed precision | e.g. `outputs/conversion/baseline/metrics.json`: `test_qini_above_random = 806.2391541262296` vs. notebook display `806.23915` | None (verified correct) | — |
| No fabricated, stale, or drifted figures found anywhere in the report | full cross-check across both outcomes | None | — |

## 3. Source code (`src/`) — statistical correctness

| Finding | Evidence | Severity | Recommended action |
|---|---|---|---|
| `paired_bootstrap_gaps` (`src/reporting.py:112-146`) applies the same resample indices to both models each draw (correctly paired), computes CI via 2.5/97.5 percentiles, and `excludes_zero = lo > 0 or hi < 0` | matches exactly what both experiment notebooks and the report notebook claim about it | None | — |
| Qini/AUUC/uplift@K definitions in `src/evaluation.py` match the plain-language descriptions given in both experiment notebooks and the report notebook | lines 1-25, 108-197 | None | — |
| No TODO/FIXME/HACK/XXX markers anywhere in `src/*.py` | full grep | None | — |

## 4. Artifacts (`outputs/`) — completeness

| Finding | Evidence | Severity | Recommended action |
|---|---|---|---|
| All 8 combinations (4 models × 2 outcomes) have non-empty `metrics.json`, `predictions.parquet`, `qini_curve.csv` | sizes checked, none zero/truncated (smallest `metrics.json` 680 bytes, largest `qini_curve.csv` ~79.6 MB, consistent across all 8) | None | — |

## 5. Documentation (`README.md`, `docs/`)

| Finding | Evidence | Severity | Recommended action |
|---|---|---|---|
| README's "Not implemented" section claims there is no confidence-interval / bootstrap check on metric differences | `README.md:207-211`: "There are no confidence intervals on the metric differences — a paired, arm-stratified bootstrap … would be the natural next addition." `paired_bootstrap_gaps` is fully implemented and used in Section 5 of all three notebooks | **High — treat as release blocker** | Remove/replace this paragraph; it directly contradicts the project's main statistical contribution and is the single most visible stale claim in the repo |
| README's "Repository structure" and "Quickstart" describe notebook paths that no longer exist (`notebooks/01_data_processing.ipynb` … `04_causal_forest.ipynb`, `kaggle_execution.ipynb` at notebook root) | `README.md:28-33, 82-92`; actual tracked files are `notebooks/evidence/01_...ipynb`-`04_...ipynb`, `notebooks/kaggle_execution.ipynb`, `notebooks/experiments/{conversion,visit}_experiment.ipynb`, `notebooks/reports/comparative_analysis_report.ipynb` | **High — release blocker** | Rewrite both sections to point at the current files and the staged `RUN_STAGE` workflow |
| README never names `comparative_analysis_report.ipynb`, `conversion_experiment.ipynb`, or `visit_experiment.ipynb` anywhere | full-text check | High | Add a pointer to the report notebook as the primary deliverable — currently invisible from the front door |
| `docs/notebook_research_artifact_audit.md` is a prior session's internal task-prompt document, not user-facing reference, and cites filenames that never matched reality (`01_conversion_experiment.ipynb`, `02_visit_sensitivity_experiment.ipynb`, `03_comparative_analysis_report.ipynb` — no numeric prefixes exist) | full read | Medium | Move to `archive/` or delete before release — reads like a spec but is stale |
| `docs/task4_create_comparative_report.md` is also an internal build-prompt document, but its content is accurate to what was actually built | full read | Low | Recommend relocating to `archive/` (process history, not reference documentation) — no correctness issue |
| `configs/config.yaml:76` (`categorical_top_k: 8`) matches README's Methodology-notes claim exactly | direct check | None | — |

## 6. Repository hygiene

| Finding | Evidence | Severity | Recommended action |
|---|---|---|---|
| Tracked file set is clean — no `__pycache__`, `.ipynb_checkpoints`, `.bak`/`.orig` files tracked; `git status --short` clean in this worktree; LICENSE present (MIT) | `git ls-files`, `git status --short` | None | — |
| No unit test file for the statistical core: `tests/` has 7 files but none named `test_reporting.py` — `paired_bootstrap_gaps` and `build_model_comparison_table` are exercised only end-to-end via notebooks | `tests/` listing: `test_artifacts.py`, `test_config.py`, `test_data.py`, `test_evaluation.py`, `test_models.py`, `test_notebook_bootstrap.py`, `test_notebook_setup.py`, `test_preprocessing.py` | **Medium-High — release readiness gap** | Add `tests/test_reporting.py` covering `paired_bootstrap_gaps` (paired resampling, CI/`excludes_zero` logic) and `build_model_comparison_table` before calling this release-ready — this is the single most decision-relevant code path in the repo |

---

## Release blockers (recap)

1. README's "Not implemented" section falsely claims no bootstrap significance check exists — fix before release.
2. README's Quickstart/Repository-structure sections point at nonexistent notebook paths and omit the three notebooks that are the actual deliverable — fix before release.
3. No unit test for `paired_bootstrap_gaps` / `build_model_comparison_table` — add before release.

Everything else above is medium/low and can reasonably be deferred past this
release if time-constrained, but should be tracked.
