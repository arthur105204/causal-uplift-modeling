# Research Memo — Readability & PDF Rendering Audit

**Scope:** `reports/research_memo.md`, `reports/final_research_memo.pdf`,
`reports/build_pdf.py` (rendering logic only). No source code, models,
notebooks, artifacts, metrics, or experimental results were reviewed or
modified. This is an audit only — no files have been changed.

**Method:** Read the markdown source in full; read `build_pdf.py` to
understand the rendering pipeline; extracted the actual PDF text with
`pypdf` and diff'd it against the markdown source to catch mismatches that
aren't visible from source alone; inspected all four referenced figures
directly.

---

## 1. Current strengths

- **The reader journey is already in the right order.** Executive Summary →
  Research Question → Data → Design → Results → Statistical Evidence →
  Discussion → Limitations → Conclusion matches the expected structure
  almost exactly, and the Executive Summary correctly front-loads the
  answer without hiding the hedges.
- **First-use glosses exist for the two most load-bearing formulas.**
  `P(Y|X)` and `tau(X)` are both introduced with a plain-language
  explanation the first time they appear (Executive Summary), not left to
  the reader to infer.
- **The hedging is disciplined and consistent.** "Inconclusive, not
  disproven," "robustness check, not a second finding," and "correlation,
  not causation"-style caveats are repeated verbatim at the point they're
  needed (Exec Summary, §6, §7, §8), which is unusually good practice for
  a memo that a non-ML reader might only skim in parts.
- **Every table has a preceding paragraph that motivates it** — a reader
  hitting Table 3 or Table 5 has already been told what question it
  answers, even though the tables themselves carry no inline takeaway (see
  §3.3 below).
- **Figure 4 (forest plot)** is the best-designed artifact in the report:
  it's titled as the question it answers, color-codes "distinguishable
  from zero" vs. not, and needs no caption to be understood.

---

## 2. Readability problems

### 2.1 Structure

| # | Finding | Where | Severity |
|---|---|---|---|
| S1 | §3 (Experimental Design) spends its second half defending *why Causal Forest was chosen as the comparator over T-/X-Learner* — a methodology self-defense — before the reader has seen any results. This is exactly the kind of implementation-justification detail a non-ML decision maker doesn't need before §4. | `research_memo.md:115-125` | Medium |
| S2 | The equation `tau(X) = E[Y(1) - Y(0) | X]` (§1) uses potential-outcomes notation (`Y(1)`, `Y(0)`) that is never glossed, even though `tau(X)` itself is. A reader who understood "incremental effect" from the Exec Summary hits unexplained bracket notation two paragraphs later. | `research_memo.md:65` | Medium |
| S3 | The closing "Robustness of Conclusions to Anticipated Critiques" section is written in author-defending-the-thesis voice ("critiques were anticipated during the preparation of this analysis") rather than reader-facing voice. For a non-ML decision maker this reads as meta-commentary about the writing process, not new information — everything in it is already stated in §6/§7/§8. | `research_memo.md:312-341` | Cosmetic |
| S4 | No table of contents / section number cross-reference aid for a 341-line, 8-section document with an appendix. Minor for a memo this length, but the PDF already numbers sections — the "§4"-style references (§5, §6, §4.1) could be made clickable in a future revision. | whole document | Cosmetic |

### 2.2 Language

Checklist items from the brief, verified against the source:

| Term | First use | Plain-language gloss present? |
|---|---|---|
| `P(Y|X)` | Exec Summary | **Yes** — "the outcome probability given the user's features" |
| `tau(X)` | Exec Summary | **Yes** — "the conditional average treatment effect" (itself jargon, but glossed as "each user's actual incremental response") |
| `CATE` | §7 Limitations, line 274 | **No.** The acronym is used exactly once, in a limitations bullet, and never tied back to the "conditional average treatment effect" phrase defined 200+ lines earlier. A reader who jumps to Limitations (a common skim pattern) meets an unglossed acronym cold. |
| `AUUC` | Exec Summary, line 35 | **No.** Never expanded (Area Under the Uplift Curve) or explained conceptually anywhere in the document. |
| `Qini` | Exec Summary, line 35 | **No.** Used as a proper noun throughout (`Qini above random`, `Qini curve`, `Qini coefficient`-adjacent) with zero explanation of what it measures, even in §3 where the metrics are formally introduced. |
| `uplift@10%` / `uplift@K` | §3, line 112 | **No**, and additionally uses code-identifier notation (`@`) rather than prose ("incremental conversions captured in the top 10% of ranked users") — reads as an API parameter name, not a report metric. |
| `bootstrap CI` | §5 | **Partial.** The *mechanism* is explained (500 resamples, paired, 95% CI), but not the *concept* — nothing tells a non-statistical reader what "the interval includes zero" means in plain terms before the surrounding prose leans on that framing repeatedly. |
| `PEHE` | §7 Limitations, line 276 | **No.** Introduced and used in the same breath as "not a validated causal mechanism" — a genuinely important limitation, undercut by being wrapped in an unexplained acronym. |
| "honest" (Causal Forest, Table 2) | §3, Table 2 | **No.** "Honest random forest" uses the causal-forest technical term "honesty" (a specific sample-splitting property) as a bare adjective. A non-ML reader will most likely read it as a value judgment ("trustworthy") rather than a modeling technique. |
| "cross-fitted correction" (X-Learner, Table 2) | §3, Table 2 | **No.** Unexplained ML jargon in a table row that a non-ML reader has no other context for. |

Other language issues:

- **Developer-register leakage:** `n_test = 2,096,939` (§2) uses a
  snake_case variable name in reader-facing prose instead of "test-set size
  (n = 2,096,939)." This is the clearest single instance of implementation
  vocabulary leaking into the narrative.
- **Sentence length:** several sentences in §6 (Discussion) and §7
  (Limitations) run 50–70 words with two or three embedded clauses (e.g.,
  the "It assumes visit is a denser view..." sentence, `research_memo.md:232-236`).
  They're logically sound and precisely hedged, but a non-ML or
  adjacent-field reader will need to re-read them. Splitting on the
  em-dash clauses (which already mark a natural break) would cost nothing
  in precision.
- **Passive voice** is used consistently for methodology statements ("is
  computed," "was applied," "is reported," "was not checked") — appropriate
  register for a research memo and not a real problem on its own, but
  compounds the sentence-length issue in §6–§7 where several
  passive-voice, multi-clause sentences stack back to back.

### 2.3 Tables and figures

None of the five tables or four figures carries an explicit
Title/Purpose/Interpretation triplet the way the brief asks for — each
relies on the paragraph *before* the table/figure to supply that context,
which mostly works (see Strengths) but leaves two gaps:

- **Figure 2 (Qini bar chart)** plots `conversion` and `visit` on one
  shared y-axis. Because visit's Qini values (~5,600–6,600) are roughly
  8x conversion's (~370–806), the conversion bars are visually flattened
  to near-zero next to the visit bars. For a reader who looks at the chart
  before reading the surrounding text, this risks the opposite impression
  from the one the memo argues for — that conversion "barely registers" —
  when the report's actual point is that conversion's gap is statistically
  inconclusive, not small. A split-axis or two-panel layout (matching
  Figure 3's approach, which already does this correctly) would remove the
  risk. **This is a figure-generation change, not a markdown/PDF text
  change — flagged here for visibility but out of this audit's file
  scope** (`reports/figures/*.png` are pipeline artifacts).
- **No table has an inline one-line takeaway row/footer.** Tables 3, 4,
  and 5 each require the reader to hold 4–6 rows of numbers in mind and
  find the right sentence in the surrounding paragraph. A single bolded
  takeaway line under each table (e.g., under Table 5: "Bottom line:
  visit's gap is real; conversion's isn't, yet.") would reduce the burden
  for the non-ML audience without touching the underlying numbers.

---

## 3. PDF rendering problems

Found by rendering `build_pdf.py`'s actual output and diffing extracted
PDF text against the markdown source — not just by reading the converter
code.

| # | Finding | Evidence | Severity |
|---|---|---|---|
| **P1** | **Executive Summary paragraphs are silently split in two**, mid-sentence, for all five bold-lead-in blocks ("The business problem.", "Two ways to target.", "What we found.", "What this means in practice.", "Practical implication."). The `**Label.** text...` regex branch in `build_flowables()` only wraps the *first source line* of each block as its own `ExecLabel`-styled `Paragraph`; it does not consume the continuation lines the way the plain-paragraph branch does. Every continuation line falls through and becomes a *second*, separately-spaced, differently-aligned (`Body`/justified vs. `ExecLabel`/left) paragraph. In the rendered PDF, "**The business problem.** An advertiser wants to know which users an ad" appears as a short stub paragraph, followed by a visually distinct new paragraph starting "actually changes the mind of...". This affects the single most-read section of the document (Executive Summary) and reads as broken/truncated text to any reader. | `build_pdf.py:250-254`; confirmed in extracted PDF text at lines 8–9, 12–13, 19–24, 30–35, 289–291 of `final_research_memo.pdf` | **Critical** |
| **P2** | **A body sentence is broken into two paragraphs** because it happens to line-wrap in the markdown source right before a `**bold**` span. `"...to compute a 95% CI on the\n**Response LightGBM minus Causal Forest** gap, per outcome..."` — the plain-paragraph accumulation loop treats any line starting with `*` (including `**`) as a stop condition, so `**Response LightGBM minus Causal Forest** gap...` gets flowed as its own paragraph instead of continuing the prior sentence. One confirmed instance in §5; the same regex bug can recur any time a future edit reflows the markdown so a line happens to start with `**`. | `build_pdf.py:290-296` (stop-prefix tuple includes `"*"`); confirmed in extracted PDF text, `final_research_memo.pdf` p.4, "...on the / Response LightGBM minus Causal Forest gap..." | Critical |
| **P3** | **`§5–§6` renders as "Section 5-Section 6"** instead of "Sections 5–6." The section-reference regex (`§(\d)` → `Section \1`) runs *after* the em/en-dash replacement, so each `§N` converts independently and the connecting en-dash collapses to a bare hyphen with no surrounding space, producing a confusing "Section 5-Section 6" (reads like subtraction) rather than a range. | `build_pdf.py:97-99`; confirmed in extracted PDF text, `final_research_memo.pdf` p.2: "addressed directly in Section 5-Section 6." | Medium |
| **P4** | **Redundant spaces around every em-dash.** The source markdown already spaces its em-dashes as `word — word`; `inline_md()` replaces the dash character alone with `" -- "` (itself space-padded), yielding `word  --  word` (double space on both sides) at the character level, at all ~30+ em-dash occurrences in the body text. ReportLab's `Paragraph` may partially absorb this in justified text, but it's a genuine double-space bug in the generated markup, not a formatting choice — it should be a single-spaced `" -- "` (i.e., strip the source's existing surrounding spaces first, or use a non-spaced replacement and rely on the source spacing). Worth a visual check in the rendered PDF at 100% zoom to confirm how visible the gap is. | `build_pdf.py:98`; confirmed by re-simulating `inline_md()` against the full source: 32 occurrences of doubled whitespace around `--` | Medium |
| **P5** | **Table 5's CI column header wraps awkwardly** ("95% CI (Response - Causal" / "Forest)" split across two lines) because the column is one of four equal-width columns on a letter page and the header text is long. Not broken, but cramped — consider shortening the header to "95% CI (Resp. - Causal Forest)" or widening that column at the expense of "Conclusion." | `build_pdf.py:141-143` (equal `col_width` for all columns); confirmed in extracted PDF text, `final_research_memo.pdf` p.4 | Cosmetic |
| **P6** | **Figure 3 (two-panel Qini curves) is shrunk to the same max-height (2.5in) as single-panel figures**, despite carrying two full subplots with legends each. At the resulting print size the legend text is small. Consider a larger `max_h` specifically for multi-panel images, or let `build_image()` take a per-figure size hint. | `build_pdf.py:163-164` | Cosmetic |
| **P7** | **The "Random (reference)" row's Objective cell renders as a bare `--`** (from the source's em-dash placeholder meaning "not applicable"). Legible, but inconsistent with how "not applicable" is communicated nowhere else in the document — confirm this reads clearly rather than as a typo. | `build_pdf.py:97-98`; confirmed in extracted PDF text at "Random (reference) / -- / 47.64 / 56.09 / 0.00117" | Cosmetic |

No missing figures, no missing tables, no font-embedding issues, and no
code-formatting leakage (the one code-span table cell, `` `P(Y\|X)` ``,
round-trips correctly through the escaped-pipe table parser). Section
headings, bullet lists, and numbered lists all render with correct
structure — the pypdf extraction shows numbers/bullets as separate "lines"
from their item text, but that's a text-extraction artifact of how
ReportLab draws `ListFlowable` bullets, not evidence of a rendering
defect; worth a one-time visual (not text-extraction) confirmation before
treating it as fully clear.

---

## 4. Recommended fixes

In order of what to fix first:

1. **Fix P1** (Exec Summary paragraph splitting) — highest impact, affects
   the section every reader sees first. Fix: make the `ExecLabel` branch
   consume continuation lines the same way the plain-paragraph branch
   does (accumulate until a blank line or a real block-start token), then
   render the merged text as a single `Paragraph` that applies the bold
   run-in via `inline_md()`'s existing `**...**` → `<b>` handling. This
   likely means deleting the separate `ExecLabel`-only branch and instead
   letting the plain-paragraph branch detect and apply `ExecLabel` style
   when the accumulated paragraph starts with a bold run-in.
2. **Fix P2** (mid-sentence paragraph break on `**`) — same root cause
   category as P1; the general paragraph-accumulation stop condition
   should not stop on a line starting with `**` unless that line is *also*
   a recognized standalone block (caption, exec-label, source-note). A
   targeted fix: only stop accumulation on `*` if the line matches one of
   the standalone-block regexes already defined, not on any line starting
   with `*`.
3. **Fix P3** (`§5–§6` → "Sections 5-6") — reorder or extend the regex to
   match a `§N–§M` (or `§N-§M`) pair before falling back to single-section
   replacement, and prefer "Sections N-M" phrasing.
4. **Fix P4** (double-spaced em-dashes) — strip one space from each side
   of the em-dash character before substitution, or trim the result post-hoc
   with a `re.sub(r" {2,}", " ", text)` pass at the end of `inline_md()`.
5. **Define AUUC, Qini, uplift@K, CATE, and PEHE on first use** in the
   markdown (content fix, not a renderer fix) — one clause each is enough,
   e.g. "AUUC (Area Under the Uplift Curve, a companion metric to Qini
   that weights the ranking differently)". Tie `CATE` explicitly back to
   the `tau(X)` definition in §1 rather than introducing it fresh in §7.
6. **Rephrase `uplift@10%` and `n_test`** into prose-friendly forms in
   body text (table headers can keep the compact form) — e.g. "top-10%
   uplift capture" and "test-set size (n = 2,096,939)."
7. **Cosmetic pass** (P5-P7, §2.3 table takeaways, §2.1 S1/S3): defer
   until after 1-6; none of these affect correctness or the core reading
   experience.

---

## 5. Priority summary

**Critical**
- P1 — Executive Summary paragraphs silently split mid-sentence (all 5 lead-in blocks)
- P2 — §5 sentence broken into two paragraphs at a bold span

**Medium**
- S1 — Methodology self-defense in §3 appears before Results
- S2 — Potential-outcomes notation `Y(1)`, `Y(0)` unglossed
- Language table — CATE, AUUC, Qini, uplift@K, PEHE undefined/unexpanded; "honest," "cross-fitted" unglossed jargon
- Developer-register leakage (`n_test`, `uplift@K` notation)
- Long, multi-clause sentences in §6–§7
- P3 — "Section 5-Section 6" mis-rendering
- P4 — Double-spaced em-dashes throughout body text
- Figure 2 shared-axis visual flattening of conversion bars (out of file scope — flagged for the figure-generation owner)

**Cosmetic**
- S3 — Author-facing voice in the closing "Anticipated Critiques" appendix
- S4 — No clickable cross-references for §-style citations
- Tables lack an inline one-line takeaway
- P5 — Table 5 header wrap
- P6 — Figure 3 legend size at print scale
- P7 — "Random (reference)" objective cell renders as bare `--`

---

**No files were modified in the course of this audit.** Awaiting approval
before implementing any of the fixes above.
