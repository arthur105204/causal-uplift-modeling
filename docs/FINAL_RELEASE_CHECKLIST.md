# Final Release Checklist

Read-only verification pass — no files were modified to produce this
checklist. All checks below were run directly (pytest, `nbformat.validate`,
`git status`/`git log`, file existence), not recalled from earlier phases.

## Recommendation: **NOT READY** — one uncommitted fix away from ready

Everything substantive is done and verified working: all three deliverable
notebooks validate cleanly with zero errors, the full test suite passes,
and every deliverable file exists on disk. The only reason this isn't a
clean READY is procedural, not technical: **the README navigation and
terminology fix from the previous turn is still uncommitted** in this
worktree. Until it's committed and pushed, the repository's `HEAD` (what
anyone cloning the repo actually gets) still has the gap Phase 5 flagged —
`reports/final_research_memo.pdf` undiscoverable from README. The fix
itself is complete and validated; it just needs `git commit` + `git push`.

---

## 1. Repository state

**Git status:** not clean — 2 modified, uncommitted files:
```
 M README.md
 M docs/pdf_preflight_review.md
```
Both are the documentation fix from the prior turn (README navigation to
`reports/`, terminology alignment, historical-doc annotation) — reviewed,
validated, intentional, and awaiting an explicit commit instruction.

**Latest commits** (current `HEAD` = `14b1b2e`):

| Commit | Summary |
|---|---|
| `14b1b2e` | docs: add Phase 5 final release review (NOT READY — README gap) |
| `61fbf78` | feat: render final PDF research memo |
| `69e6127` | docs: add Table N captions to final memo, fix ambiguous table refs |
| `91346cf` | fix: populate Figure 4 (bootstrap forest plot) in comparative report |
| `8f20910` | docs: Phase 4.1 executive readability pass (findings/numbers unchanged) |
| `32dd6e9` | docs: Phase 4 editorial preflight + reports/ package |
| `2f994d0` | docs: add Phase 3 research memo draft |
| `07a5149` | docs: add skeptical-reviewer self-check to research memo plan |
| `a877eff` | docs: add Phase 2 research memo planning document |
| `929f4b1` | docs+test: fix release-blocking README staleness, add reporting tests |
| `bb1f6db` | docs: add Phase 1 final release repository audit |

All commits back to `bb1f6db` represent this release's forward progress
(audit → hardening → memo planning → drafting → review → PDF → final
review); no stray or unrelated commits found. Branch: `worktree-notebook-audit`,
remote `origin` set.

## 2. Deliverables

| File | Status |
|---|---|
| `reports/final_research_memo.pdf` | Exists, 218,615 bytes |
| `reports/research_memo.md` | Exists, 19,719 bytes |
| `notebooks/reports/comparative_analysis_report.ipynb` | Exists, 368,789 bytes |
| `notebooks/experiments/conversion_experiment.ipynb` | Exists, 793,943 bytes |
| `notebooks/experiments/visit_experiment.ipynb` | Exists, 792,148 bytes |

All five confirmed present on disk via direct `ls`.

## 3. Documentation

- **README points to the final memo:** yes, in the current *working tree*
  (uncommitted) — a "Read the result" section links
  `reports/final_research_memo.pdf` as the primary reader-facing
  deliverable and `notebooks/reports/comparative_analysis_report.ipynb`
  as the technical evidence/reproducibility layer, and the Repository
  Structure tree now lists the top-level `reports/` package. **This is
  not yet true of `HEAD` (commit `14b1b2e`)** — see Section 1.
- **Terminology consistent:** confirmed — `grep -c -i "sensitivity check"
  README.md` → `0` in the working tree. `reports/research_memo.md` (the
  memo itself, unedited this pass) already used "robustness check"
  exclusively throughout, per its own Reviewer Attack Point #6.

## 4. Validation

**pytest:**
```
136 passed in 77.14s
```
Full suite, including `tests/test_reporting.py` (the statistical-core
tests added during release hardening).

**Notebook validation** (`nbformat.validate`, zero output errors, zero
missing `execution_count` on any code cell):

| Notebook | Cells | Code cells | Missing exec_count | Errors |
|---|---|---|---|---|
| `comparative_analysis_report.ipynb` | 34 | 15 | none | 0 |
| `conversion_experiment.ipynb` | 56 | 27 | none | 0 |
| `visit_experiment.ipynb` | 56 | 27 | none | 0 |

**Known limitations** (unchanged from `reports/research_memo.md` §7 — not
re-derived here, just confirmed still accurate and still present):
- Offline evaluation only — no online experiment confirms the measured effect.
- The outcome-sparsity explanation (§6) is an inference, not verified —
  no artifact measures whether visit-ranked and conversion-ranked uplift
  scores actually correlate.
- Bootstrap coverage is partial — only Response LightGBM vs. Causal
  Forest, three correlated metrics, per outcome.
- Resample-count and seed sensitivity of the bootstrap were not checked.
- Causal Forest's categorical encoding is coarser than the LightGBM-based
  estimators' (top-8 frequency-capped one-hot vs. full-cardinality native
  splits) — a comparability caveat, not adjusted for.
- Not a validated causal mechanism — no PEHE against ground truth; CATE
  describes what the models infer, not a true individual treatment effect.
- Specific to this dataset, these implementations, one hyperparameter
  setting each — no universal claim about outcome or method.

---

## Release version recommendation

**`v1.0.0`** — this is the first complete, internally reviewed release of
the comparative analysis (conversion primary outcome + visit robustness
check, Response LightGBM vs. three causal estimators, paired bootstrap
significance evidence, full research memo with PDF). No prior tags exist
in this repository. Recommend tagging from the commit that includes the
pending README/terminology fix (not `14b1b2e`, which still has the
README gap) — i.e., tag the *next* commit once it lands.

## Commit reference

Current `HEAD`: `14b1b2e` — **do not tag this commit**; it predates the
README fix. Tag the commit that follows once the pending `README.md` /
`docs/pdf_preflight_review.md` changes are committed and pushed.

## Remaining risks

1. **[Blocks READY]** The README fix exists only in the working tree, not
   in any commit — anyone cloning the repo right now still hits the gap
   Phase 5 found. Purely procedural: commit + push resolves it.
2. **[Low, already documented]** The seven known limitations above are
   inherent to the analysis (offline evaluation, unverified sparsity
   inference, partial bootstrap coverage, etc.) — not release blockers,
   already disclosed prominently in the memo's own Limitations section
   and not newly discovered here.
3. **[Low]** No git tag/version scheme exists yet in this repository —
   first-time setup, not a defect, addressed by the recommendation above.

## Final recommendation: **NOT READY**

Technically complete and fully validated (136/136 tests pass, all three
notebooks error-free with complete execution records, all deliverables
present and internally consistent). Blocked on one procedural step: commit
and push the README navigation / terminology fix, then tag `v1.0.0`. No
further code, notebook, model, or content work is needed.
