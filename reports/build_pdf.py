"""Render reports/research_memo.md to reports/final_research_memo.pdf.

Research-memo typesetting (not a notebook export): serif body text,
numbered figures/tables with captions, footnoted evidence sources, page
numbers. Reads only reports/research_memo.md and reports/figures/*.png --
does not touch source code, notebooks, or artifacts.

This is a small, purpose-built markdown-to-PDF converter for this one
document's known structure (headings, tables, images, bullet lists,
italic source notes) -- not a general markdown renderer.
"""
from __future__ import annotations

import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image,
    HRFlowable, KeepTogether, ListFlowable, ListItem,
)
from reportlab.pdfgen import canvas as pdfcanvas
from PIL import Image as PILImage

REPO = Path(__file__).resolve().parent.parent
REPORTS_DIR = REPO / "reports"
MEMO_PATH = REPORTS_DIR / "research_memo.md"
OUT_PATH = REPORTS_DIR / "final_research_memo.pdf"

DOC_TITLE = "Does Outcome Sparsity Limit Uplift-Ranking Evidence?"

# ---------------------------------------------------------------- styles --

styles = {
    "Title": ParagraphStyle(
        "Title", fontName="Times-Bold", fontSize=17, leading=21,
        alignment=TA_CENTER, spaceAfter=4, textColor=colors.HexColor("#1a1a1a"),
    ),
    "Subtitle": ParagraphStyle(
        "Subtitle", fontName="Times-Italic", fontSize=9, leading=12,
        alignment=TA_CENTER, spaceAfter=14, textColor=colors.HexColor("#444444"),
    ),
    "H1": ParagraphStyle(
        "H1", fontName="Helvetica-Bold", fontSize=12, leading=14.5,
        spaceBefore=9, spaceAfter=4, textColor=colors.HexColor("#12315c"),
        keepWithNext=True,
    ),
    "H2": ParagraphStyle(
        "H2", fontName="Helvetica-Bold", fontSize=10.3, leading=12.5,
        spaceBefore=6, spaceAfter=3, textColor=colors.HexColor("#33507a"),
        keepWithNext=True,
    ),
    "ExecLabel": ParagraphStyle(
        # Base font is Times-Roman, matching Body -- only the "**Label.**"
        # run-in itself is bold, via inline_md's <b> tag. A bold *base* font
        # here would additionally bold the rest of the paragraph's text.
        "ExecLabel", fontName="Times-Roman", fontSize=9.6, leading=12.2,
        alignment=TA_JUSTIFY, spaceBefore=4, spaceAfter=4.5,
    ),
    "Body": ParagraphStyle(
        "Body", fontName="Times-Roman", fontSize=9.6, leading=12.2,
        alignment=TA_JUSTIFY, spaceAfter=4.5,
    ),
    "Caption": ParagraphStyle(
        "Caption", fontName="Helvetica-Bold", fontSize=8.8, leading=11,
        spaceBefore=6, spaceAfter=2, textColor=colors.HexColor("#12315c"),
    ),
    "SourceNote": ParagraphStyle(
        "SourceNote", fontName="Times-Italic", fontSize=7.6, leading=9.8,
        spaceBefore=1, spaceAfter=6, textColor=colors.HexColor("#555555"),
    ),
    "Bullet": ParagraphStyle(
        "Bullet", fontName="Times-Roman", fontSize=9, leading=11.4,
        alignment=TA_JUSTIFY, spaceAfter=2,
    ),
    "Numbered": ParagraphStyle(
        "Numbered", fontName="Times-Roman", fontSize=8.6, leading=10.8,
        alignment=TA_JUSTIFY, spaceAfter=3,
    ),
    "TableCell": ParagraphStyle(
        "TableCell", fontName="Times-Roman", fontSize=7.8, leading=9.6,
    ),
    "TableHeader": ParagraphStyle(
        "TableHeader", fontName="Helvetica-Bold", fontSize=7.8, leading=9.6,
        textColor=colors.white,
    ),
}

# ------------------------------------------------------------ inline md --

def inline_md(text: str) -> str:
    # Normalize to unambiguous ASCII for the PDF's base-14 fonts -- avoids any
    # risk of a mis-encoded/garbled glyph for characters outside plain ASCII
    # (true minus, em/en dash, section sign) that a text extractor or a
    # non-embedded-font viewer could render incorrectly.
    text = text.replace("\u2212", "-")
    # Section ranges ("\u00a75\u2013\u00a76") must be resolved before the
    # generic en-dash replacement below turns "\u2013" into a bare "-",
    # which would otherwise merge into "Section 5-Section 6".
    text = re.sub(r"\u00a7(\d+)\u2013\u00a7(\d+)", r"Sections \1-\2", text)
    text = re.sub(r"\u00a7(\d+)", r"Section \1", text)
    # Collapse any surrounding whitespace around an em-dash into exactly one
    # space per side -- the source already spaces its em-dashes ("word \u2014
    # word"), so a plain substitution would double that spacing.
    text = re.sub(r"\s*\u2014\s*", " -- ", text)
    text = text.replace("\u2013", "-")
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # Protect code spans (which may contain a literal "*", e.g. a glob path)
    # from the bold/italic passes below by swapping them for placeholders
    # first, then restoring the rendered <font> markup afterward.
    code_spans: list[str] = []

    def _stash_code(m: re.Match) -> str:
        code_spans.append(f'<font face="Courier" size="8.6">{m.group(1)}</font>')
        return f"\x00{len(code_spans) - 1}\x00"

    text = re.sub(r"`([^`]+)`", _stash_code, text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", text)
    text = re.sub(r"\x00(\d+)\x00", lambda m: code_spans[int(m.group(1))], text)
    return text


def para(text: str, style: str = "Body"):
    return Paragraph(inline_md(text), styles[style])


# --------------------------------------------------------- markdown -> flowables --

def _split_table_row(row: str) -> list[str]:
    # Split on "|" that is NOT escaped with a backslash (markdown uses "\|"
    # inside a cell -- e.g. a code span like `P(Y\|X)` -- to protect a
    # literal pipe from being read as a column delimiter), then unescape.
    cells = re.split(r"(?<!\\)\|", row.strip("|"))
    return [c.strip().replace("\\|", "|") for c in cells]


def parse_table(lines: list[str]) -> Table:
    rows = [ln.strip() for ln in lines if ln.strip().startswith("|")]
    rows = [r for r in rows if not re.match(r"^\|[\s:\-|]+\|$", r)]  # drop separator row
    cells = [_split_table_row(r) for r in rows]
    ncols = len(cells[0])
    data = []
    for i, row in enumerate(cells):
        style = "TableHeader" if i == 0 else "TableCell"
        data.append([Paragraph(inline_md(c), styles[style]) for c in row])
    avail_width = LETTER[0] - 2 * 0.75 * inch
    col_width = avail_width / ncols
    t = Table(data, colWidths=[col_width] * ncols, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#33507a")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#b7c2d6")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eef1f7")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 3.5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3.5),
    ]))
    return t


def build_image(md_line: str):
    m = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", md_line.strip())
    alt, relpath = m.group(1), m.group(2)
    img_path = REPORTS_DIR / relpath
    with PILImage.open(img_path) as im:
        w_px, h_px = im.size
    max_w = 5.6 * inch
    max_h = 2.5 * inch
    ratio = w_px / h_px
    w, h = max_w, max_w / ratio
    if h > max_h:
        h = max_h
        w = max_h * ratio
    img = Image(str(img_path), width=w, height=h)
    img.hAlign = "CENTER"
    return img


_CAPTION_LINE_RE = re.compile(r"^\*\*[^*]+\*\*\.?$")
_CAPTION_FIGTABLE_RE = re.compile(r"^\*\*(Figure|Table) \d")
_EXEC_LABEL_RE = re.compile(r"^\*\*[^*]+\.\*\*\s")
_NUMBERED_ITEM_RE = re.compile(r"^\d+\.\s")


def _is_new_block(line_stripped: str) -> bool:
    """True if this (already-stripped) line starts a new flowable block
    rather than continuing the paragraph/list-item being accumulated.

    Used instead of a naive "starts with '*'" check so that a hard-wrapped
    line that merely *contains* inline markdown -- e.g. a sentence that
    happens to wrap right before a `**bold**` span -- is not mistaken for
    the start of a new paragraph and split off into its own flowable.
    """
    if not line_stripped:
        return True
    if line_stripped.startswith(("#", "|", "!", "---")):
        return True
    if line_stripped.startswith("- ") or _NUMBERED_ITEM_RE.match(line_stripped):
        return True
    if _CAPTION_LINE_RE.match(line_stripped) or _CAPTION_FIGTABLE_RE.match(line_stripped):
        return True
    if line_stripped.startswith("*") and line_stripped.endswith("*") and not line_stripped.startswith("**"):
        return True  # whole-line italic source note
    return False


def build_flowables(md_text: str):
    lines = md_text.splitlines()
    flowables = []
    i = 0
    n = len(lines)
    first_h1_seen = False

    while i < n:
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        if stripped.startswith("# "):
            i += 1
            continue  # document title handled separately (cover block)

        if stripped.startswith("*Research memo"):
            # multi-line italic source note right after title -- consume until
            # blank. Subtitle style is already italic via font, so the
            # wrapping markdown "*" markers are stripped, not converted.
            buf = [stripped[1:]]
            i += 1
            while i < n and lines[i].strip():
                buf.append(lines[i].strip())
                i += 1
            joined = " ".join(buf)
            if joined.endswith("*"):
                joined = joined[:-1]
            flowables.append(para(joined, "Subtitle"))
            continue

        if stripped == "---":
            flowables.append(Spacer(1, 6))
            flowables.append(HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#b7c2d6")))
            flowables.append(Spacer(1, 6))
            i += 1
            continue

        if stripped.startswith("## "):
            if first_h1_seen:
                flowables.append(Spacer(1, 2))
            first_h1_seen = True
            flowables.append(para(stripped[3:], "H1"))
            i += 1
            continue

        if stripped.startswith("### "):
            flowables.append(para(stripped[4:], "H2"))
            i += 1
            continue

        if stripped.startswith("!["):
            flowables.append(build_image(stripped))
            i += 1
            continue

        if stripped.startswith("|"):
            table_lines = []
            while i < n and lines[i].strip().startswith("|"):
                table_lines.append(lines[i])
                i += 1
            flowables.append(Spacer(1, 3))
            flowables.append(parse_table(table_lines))
            flowables.append(Spacer(1, 6))
            continue

        # bold caption line, e.g. "**Figure 1 -- ...**" or "**Table 1 -- ...**"
        if _CAPTION_LINE_RE.match(stripped) or _CAPTION_FIGTABLE_RE.match(stripped):
            flowables.append(para(stripped, "Caption"))
            i += 1
            continue

        if stripped.startswith("*") and stripped.endswith("*") and not stripped.startswith("**"):
            flowables.append(para(stripped.strip("*"), "SourceNote"))
            i += 1
            continue

        if _NUMBERED_ITEM_RE.match(stripped):
            items = []
            while i < n and _NUMBERED_ITEM_RE.match(lines[i].strip()):
                item_text = _NUMBERED_ITEM_RE.sub("", lines[i].strip())
                j = i + 1
                while j < n and lines[j].strip() and not _NUMBERED_ITEM_RE.match(lines[j].strip()) \
                        and not _is_new_block(lines[j].strip()):
                    item_text += " " + lines[j].strip()
                    j += 1
                items.append(ListItem(para(item_text, "Numbered"), leftIndent=14))
                i = j
            flowables.append(ListFlowable(items, bulletType="1", start="1", leftIndent=16))
            flowables.append(Spacer(1, 4))
            continue

        if stripped.startswith("- "):
            items = []
            while i < n and lines[i].strip().startswith("- "):
                item_text = lines[i].strip()[2:]
                j = i + 1
                while j < n and lines[j].strip() and not _is_new_block(lines[j].strip()):
                    item_text += " " + lines[j].strip()
                    j += 1
                items.append(ListItem(para(item_text, "Bullet"), leftIndent=14))
                i = j
            flowables.append(ListFlowable(items, bulletType="bullet", start="\u2022", leftIndent=16))
            flowables.append(Spacer(1, 4))
            continue

        # plain paragraph, including "**Label.** text..." lead-ins (Executive
        # Summary, "Practical implication.") -- accumulate every line until a
        # new block starts, THEN decide styling from the merged text. Deciding
        # per-line here (as a prior version did) orphaned the "**Label.**"
        # line into its own mis-aligned paragraph and cut its sentence in two.
        buf = [stripped]
        i += 1
        while i < n and lines[i].strip() and not _is_new_block(lines[i].strip()):
            buf.append(lines[i].strip())
            i += 1
        merged = " ".join(buf)
        style = "ExecLabel" if _EXEC_LABEL_RE.match(merged) else "Body"
        flowables.append(para(merged, style))

    return flowables


# --------------------------------------------------------------- footer --

_max_page_seen = [0]


def footer(canvas: pdfcanvas.Canvas, doc):
    _max_page_seen[0] = max(_max_page_seen[0], doc.page)
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#777777"))
    canvas.drawString(0.75 * inch, 0.4 * inch, "CRITEO-UPLIFTv2.1 comparative analysis -- research memo")
    canvas.drawRightString(LETTER[0] - 0.75 * inch, 0.4 * inch, f"Page {doc.page}")
    canvas.restoreState()


def main():
    md_text = MEMO_PATH.read_text(encoding="utf-8")

    doc = SimpleDocTemplate(
        str(OUT_PATH), pagesize=LETTER,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
        topMargin=0.6 * inch, bottomMargin=0.6 * inch,
        title=DOC_TITLE, author="Comparative analysis research memo",
    )

    story = [
        Paragraph(inline_md(DOC_TITLE), styles["Title"]),
    ]
    story += build_flowables(md_text)

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(f"wrote {OUT_PATH}")
    print(f"page count: {_max_page_seen[0]}")


if __name__ == "__main__":
    main()
