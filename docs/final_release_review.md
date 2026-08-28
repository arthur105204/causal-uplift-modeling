# Final Release Review — Phase 5

Independent, fresh-context audit performed as an external reviewer seeing
this repository for the first time. Read-only: no file was modified to
produce this review. Findings below were re-derived directly from the
tracked files (PDF text extraction, notebook cell outputs, `git log`/`git
status`), not taken on faith from earlier phases' own conclusions.

## Release readiness score: 8 / 10 — NOT READY (one scoped fix required)

The deliverable itself is sound: every number, table, figure, and
conclusion in `reports/final_research_memo.pdf` traces exactly to
`reports/research_memo.md` and to `notebooks/reports/comparative_analysis_report.ipynb`'s
own stored cell outputs, with zero discrepancies found. Git hygiene is
clean, the `reports/` and `docs/` packages are both complete, and
`tests/test_reporting.py` is intact. The blocker is narrow and specific:
**README.md — the front door of this repository — never mentions that
`reports/research_memo.md` / `reports/final_research_memo.pdf` exist.** A
new reviewer following README alone would read `comparative_analysis_report.ipynb`
as "the notebook to read first for the actual result" and never discover
that a finished, reviewed research memo and PDF now sit one level above
`notebooks/`. This is the same class of gap the Phase 1 audit already
caught and fixed once (README not mentioning the notebooks that existed at
the time); it has recurred because README was last touched in the Phase
1.5 hardening pass, before the memo-writing phases (2 through 4.2) added
`reports/` at all.

**Recommendation: NOT READY until README.md is updated to point to
`reports/`.** This is a small, well-scoped documentation fix — no code,
notebook, or artifact change — and should take one short pass. Everything
else below is medium/low and does not need to block release.

---

## 1. PDF consistency — no defects found

| Check | Result | Severity |
|---|---|---|
| Table 3/4 numbers (PDF) vs. notebook's own Table 1/Table 2 cell outputs | Exact match, e.g. Response LightGBM `qini_above_random` 806.23915 → PDF "806.24"; Causal Forest visit `qini_above_random` 6642.20308 → PDF "6642.20" | None (confirmed correct) |
| Table 5 (bootstrap CIs, PDF) vs. notebook's own `BOOTSTRAP_TABLE` cell output | Exact match on all 6 rows, including sign and "includes zero"/"excludes zero" conclusions | None (confirmed correct) |
| All 4 figures present in PDF, captions match `reports/figures/figure_list.md` | Confirmed — 4 image XObjects, captions verbatim | None (confirmed correct) |
| PDF's Section 8 Conclusion vs. `reports/research_memo.md`'s Conclusion | Word-for-word match once page-footer/header boilerplate is stripped from the naive multi-page text extraction (that interleaving is an artifact of the verification method, not a defect in the PDF) | None (confirmed correct) |
| Terminology drift between PDF and .md | None — "sensitivity analysis" appears exactly once in both, in the same place (Final Self-Check item 6, explaining why the term is *not* used elsewhere) | None (confirmed correct) |

## 2. Repository reproducibility — one high-severity gap

A new reader following only README.md **can** correctly determine: the
research objective, that `kaggle_execution.ipynb` is the single entry
point, and how `notebooks/evidence/01-04`, `notebooks/experiments/*`, and
`notebooks/reports/comparative_analysis_report.ipynb` relate to each other
(README's Repository Structure section, rewritten in Phase 1.5, is
internally coherent on this).

**What a reader cannot determine from README alone: that
`reports/research_memo.md` and `reports/final_research_memo.pdf` exist at
all.** Confirmed by grepping README.md for `final_research_memo` and bare
`research_memo.md`: zero matches. README's own tree has a `└── reports/`
entry, but it is nested inside the `notebooks/` subtree (i.e.
`notebooks/reports/`, the notebook) — a different directory from the
top-level `reports/` package that contains the actual finished memo, PDF,
figures, and tables. README still directs a reader to
`comparative_analysis_report.ipynb` as "the notebook to read first for the
actual result," which was accurate through Phase 1.5 but is now
superseded by the reviewed, PDF-rendered memo.

**Severity: High.** This is the single most consequential finding in this
review — the headline output of the entire multi-phase project (Phases 2
through 4.2) is undiscoverable from the project's front door.

## 3. Documentation consistency

| Check | Result | Severity |
|---|---|---|
| Conversion = primary/rare, visit = secondary/robustness-check, consistently framed | Confirmed across all three sources: README.md ("Primary Y is conversion; visit is an optional secondary outcome"), `reports/research_memo.md` (Table 1 + Executive Summary), and `conversion_experiment.ipynb`'s "Scope" cell ("This notebook evaluates the conversion outcome only... visit is evaluated independently") | None (confirmed correct) |
| Response-vs-causal model framing (`P(Y\|X)` vs. `tau(X)`) | Consistent in substance across README's Research Objective, the memo's Executive Summary, and the notebook's "The problem" cell — near-verbatim in spirit | None (confirmed correct) |
| No cross-source "which model wins" contradiction | Confirmed — README's Research Objective explicitly disclaims universal-superiority claims, matching the memo's hedging exactly | None (confirmed correct) |
| Terminology drift: "sensitivity check" (README) vs. "robustness check" (memo) | README.md uses "denser sensitivity/robustness check" and "visit sensitivity check" in two places, but the memo's own Final Self-Check item 6 explicitly states it "uses 'robustness check' throughout and does not use 'sensitivity analysis'... to preempt this critique." README was never updated to match this deliberate terminology decision made during the memo's reviewer-defensibility pass | **Medium** |

## 4. Final release hygiene

| Check | Result | Severity |
|---|---|---|
| `git status --short` | Clean, nothing uncommitted | None |
| `git log --oneline -20` | All forward progress on this release (Phase 1 audit → 1.5 hardening → Phase 2 plan → self-check → Phase 3 draft → Phase 4 preflight → 4.1 readability/Figure 4 fix → 4.2 captions/PDF render), preceded by pre-existing repo history; no stray/junk commits | None |
| `reports/` package completeness | `research_memo.md`, `final_research_memo.pdf`, `build_pdf.py`, `figures/` (4 PNGs + `figure_list.md`), `tables/` (5 CSVs + `table_list.md`) — all tracked and present | None |
| `build_pdf.py`'s permanence as a repo artifact | Reasonable to keep — self-documented purpose in its own docstring, not throwaway scratch code | None |
| `docs/` paper trail completeness | `final_release_audit.md`, `research_memo_plan.md`, `research_memo_draft.md`, `pdf_preflight_review.md` all present, alongside two pre-existing docs from before this workflow | None |
| Stale internal doc: `docs/pdf_preflight_review.md` | Still states "Blocking finding: Figure 4 is not available" and lists resolving it as an action item, but Figure 4 was fixed in commit `91346cf`, before the PDF-render commit `61fbf78`. Low external risk (clearly a dated, historical document if read carefully) but internally inconsistent with the current state | **Medium** |
| `tests/test_reporting.py` | Present (8,917 bytes), not reverted | None |

---

## Remaining risks (recap)

1. **[High]** README.md does not mention `reports/research_memo.md` or `reports/final_research_memo.pdf` — the actual headline deliverable is undiscoverable from the front door. **Blocks release.**
2. **[Medium]** README uses "sensitivity check" language in two places that the final memo deliberately moved away from ("robustness check") for reviewer-defensibility reasons — not a factual contradiction, but an inconsistency the memo's own review process was specifically designed to eliminate, still present one file over. Recommend fixing alongside item 1.
3. **[Medium]** `docs/pdf_preflight_review.md` still describes Figure 4 as unavailable/blocking, superseded by later commits. Recommend a one-line "RESOLVED — see commit 91346cf" annotation rather than a rewrite, since it's a historical paper-trail document, not a live deliverable.

## Final recommendation: **NOT READY**

Not ready to call this release complete as-is, but the gap is narrow and
well-understood: update README.md to name `reports/research_memo.md` /
`reports/final_research_memo.pdf` as the project's headline result (and,
while there, align its "sensitivity check" wording with the memo's
"robustness check" terminology). No code, notebook, model, or artifact
work remains — this is a documentation-only fix, and once applied this
repository is release-ready.
