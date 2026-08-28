# PDF Preflight Review — Phase 4

Editorial preflight of `docs/research_memo_draft.md` before PDF generation.
This is an audit only: no prose in the draft or plan was changed as a
result of this review; findings are recommendations for the next approval
step. `reports/research_memo.md` (see §3) carries the draft's prose
unchanged except for swapping bracketed figure placeholders for real image
embeds — a mechanical formatting step, not a wording change. No source
code, notebook, or artifact was modified to produce this review; the three
extracted figures (§3) were read out of the notebook's already-executed
outputs, not written into it.

---

## 1. Executive readability

**Scope note.** `docs/research_memo_plan.md` explicitly scoped this memo's
audience to "ML practitioners, applied researchers, technical decision
makers" — narrower than a fully non-technical reader, and narrower than the
comparative report notebook's own audience. The check below applies the
stricter "non-technical decision maker" bar Phase 4 asked for, so some
findings here are gaps relative to a bar the memo was not originally
written to clear, not contradictions of Phase 2's approved plan. Flagged as
recommendations, not defects.

| Check | Can a non-technical decision maker follow it? | Finding |
|---|---|---|
| Research question | Partially | Exec Summary's first sentence carries `P(Y\|X)` and `tau(X)` notation inline. The surrounding words ("non-causal response model," "causal uplift estimators") do carry the meaning even if the notation is skipped, but a reader unfamiliar with the notation may stall on the first sentence of the document |
| Why uplift modeling matters | Implicit, not explicit, in the Exec Summary | The business rationale ("don't waste spend on people who'd act anyway") is stated clearly in §1, but a reader who stops at the Executive Summary (the common case for a decision maker) does not see it there |
| Main findings | Yes, with effort | "Point-estimate ranking," "paired bootstrap," "statistically distinguishable from resampling noise" are used without an inline lay gloss. The high-level shape of the finding (inconclusive under conversion, resolved under visit) does come through even without fully parsing those terms |
| Practical implication | **No** | Neither the Executive Summary nor §8 (Conclusion) states what a decision maker should actually *do* with this result. Both are dense with correct, necessary hedges ("this is not a claim that...") but end without a forward-looking sentence (e.g., what changes, if anything, about targeting strategy, or what data/experiment would resolve the ambiguity) |

**Recommendation for the next revision pass (not applied in this phase):**
add one sentence to the Executive Summary defining `P(Y|X)` / `tau(X)` in
words before the notation appears (or move the notation to §1 only, as the
plan's audience note originally intended), and add one explicit
forward-looking sentence to §8 — e.g., stating that this result does not
yet support switching primary targeting away from the current baseline on
`conversion` grounds alone, and naming what would resolve the ambiguity
(more conversion data, or a pre-registered follow-up check). Both are
additive; neither requires removing or weakening an existing hedge.

## 2. Scientific wording

Searched `docs/research_memo_draft.md` for the four prohibited claim
patterns and their common phrasings:

| Pattern searched | Result |
|---|---|
| "proves causality" / "proves that" / "proof" / "definitive(ly)" | **0 matches** |
| "Causal Forest ... universally (better\|superior)" / "always wins" | **0 matches** as an assertion — the only match is the negation "This is not a claim that Causal Forest is universally superior" (§8), which is a disclaimer, not a violation |
| "visit replaces conversion" | **0 matches** as an assertion — same sentence as above, in negated form only |
| "sparsity is proven" / sparsity asserted as the only constraint | **0 matches** — §6 explicitly states "This explanation should not be treated as proven" and frames it as an inference |

Preferred hedge vocabulary ("suggests," "consistent with," "provides
evidence") appears at 8 distinct points across the Executive Summary, §5,
and §6 (verified by direct grep against the draft), including the two
places load-bearing for the central claim: the Executive Summary's
"suggest that the ambiguity... is consistent with" and §5's "should be read
as consistent with one another."

**Conclusion:** no overclaim was found. The draft's language passes this
check as written; no correction is required before promoting it to
`reports/research_memo.md`.

## 3. Figure/table readiness

Created `reports/` with the following contents.

```text
reports/
├── research_memo.md              draft prose, unchanged, with figure
│                                  placeholders replaced by real image
│                                  embeds (mechanical substitution only)
├── figures/
│   ├── fig1_outcome_prevalence.png
│   ├── fig2_qini_bar.png
│   ├── fig3_qini_curves.png
│   ├── figure_list.md            title / purpose / source / reader
│   │                              takeaway for all four figures
│   └── (fig4_bootstrap_forest.png -- not present; see below)
└── tables/
    ├── table1_outcome_definitions.csv
    ├── table2_model_objectives.csv
    ├── table3_conversion_comparison.csv
    ├── table4_visit_comparison.csv
    ├── table5_bootstrap_ci.csv
    └── table_list.md              title / purpose / source / reader
                                    takeaway for all five tables
```

Every number in the five CSVs was re-read directly from
`outputs/{conversion,visit}/*/metrics.json` (or, for the "Random
(reference)" rows, from the notebook's own already-executed cell output —
those are computed live each run, not saved to a JSON artifact) — not
retyped from the memo prose. See `reports/tables/table_list.md` and
`reports/figures/figure_list.md` for the full title/purpose/source/reader-takeaway
entries per item (not duplicated here to avoid drift between two copies).

**Blocking finding: Figure 4 is not available.** The bootstrap forest-plot
cell (`comparative_analysis_report.ipynb` §5, cell `74ab5e45`) was added in
a prior session and validated only via `nbformat.validate()` and a
separately-executed temporary copy of the notebook — the cell as committed
has `execution_count: None` and `outputs: []`. It has never been executed
in the actual committed notebook, so there is no rendered image to
extract. This is the single most consequential figure for the memo's
central argument (it is the visual carrier of Table 5 / §5's statistical
evidence), so **this should be resolved before final PDF generation**: the
notebook needs to be (re-)executed for real — it only reads existing
`outputs/` artifacts in this section, so this is fast and does not
retrain anything — after which this figure can be extracted the same way
Figures 1–3 were. `reports/research_memo.md` currently carries an explicit
note in place of this figure rather than a broken image reference.

> **Update (Phase 4.1): resolved.** This blocker was subsequently fixed —
> full top-to-bottom re-execution proved impractical in this environment
> (paired bootstrap alone costs ~3h; see that phase's notes), so cell
> `70eab150`'s already-valid, previously-computed real `BOOTSTRAP_TABLE`
> output was reused to produce Figure 4 without recomputing the bootstrap.
> The notebook's cell `74ab5e45` now has `execution_count=15` and a real
> `image/png` output; `reports/figures/fig4_bootstrap_forest.png` and
> `reports/research_memo.md` both carry the real figure. Left as-written
> above for the historical record of what this preflight found at the
> time — see `docs/final_release_review.md` for current status.

## 4. PDF layout plan (recommendation only — no PDF generated)

**Estimated length.** The prose is ~2,300 words. At a typical single-column,
11pt, 1-inch-margin academic layout (~550 words/page), the text alone is
~4.2 pages. Adding four figures and five tables at conventional inline
sizing (Figures 1–2 as half-page-width thumbnails, Figure 3 as a full-width
two-panel figure, Figure 4 similarly full-width, Tables 1–2 and 5 as small
in-body tables, Tables 3–4 as five-row tables) is estimated to bring the
total to **roughly 6 pages**. To hit closer to the originally targeted
3–4 pages: the in-body tables are already trimmed to the load-bearing
columns only (full 10-column detail lives in the CSVs, not the memo body),
which is the main lever already pulled; if a hard 4-page cap is required,
the next lever would be shrinking Figures 1 and 2 (the two simplest bar
charts) to quarter-page size rather than half-page, or moving Figure 3 (the
most visually dense figure) to a one-page appendix referenced from §4.
Recommend accepting ~5–6 pages rather than cutting further, given the
audience is technical and the figures carry real evidentiary weight.

**Section breaks.** Start a new page at:
- Title + Executive Summary (page 1 alone — this is what a skimming reader
  sees first and should not compete with §1's start)
- §5 Statistical Evidence (this section, plus Table 5 and Figure 4, is the
  evidentiary crux of the memo and should start clean on its own page
  rather than run on from §4.2)

Do not force a break before §6/§7/§8 — Discussion, Limitations, and
Conclusion are short enough to flow together and a forced break would
fragment the closing argument.

**Figure placement.**
- Figure 1: inline in §2, directly after Table 1 (small, two-bar chart —
  fits comfortably beside or below the outcome table)
- Figures 2 and 3: both currently show conversion and visit together in one
  image. Recommend placing them once, at the **top of §4** before the
  4.1/4.2 split (rather than nested under 4.1 as in this markdown draft),
  since they answer both subsections at once — repeating "see Figures 2–3
  above" in 4.2 as already done in `reports/research_memo.md`, rather than
  duplicating the images
- Figure 4: in §5, immediately after Table 5 (once the figure exists — see
  §3's blocking finding)

**Table placement.**
- Tables 1–2: inline, immediately following the paragraph that introduces
  each (already done)
- Tables 3–4: inline, one per subsection (4.1 / 4.2), immediately before
  that subsection's figure reference (already done)
- Table 5: inline in §5, immediately before Figure 4 (already done) — this
  ordering (table first, then the forest plot visualizing the same
  numbers) matches how §5's prose introduces them

---

## Summary of actions before PDF generation

1. Resolve the Figure 4 blocker (re-execute the report notebook's §5 forest-plot
   cell; re-extract the image). **Resolved in Phase 4.1** — see the update
   note under Section 3 above.
2. Decide whether to apply the two Executive-readability recommendations in
   §1 (notation placement, explicit practical-implication sentence) before
   finalizing — no scientific wording issue blocks this, it is a clarity
   improvement only.
3. Confirm the ~5–6 page estimate is acceptable, or approve one of the
   space-saving options in §4, before typesetting.

No PDF was generated in this phase, and no notebook, source file, or
artifact was modified.
