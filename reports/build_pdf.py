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
        "ExecLabel", fontName="Times-Bold", fontSize=9.6, leading=12.2,
        spaceBefore=4, spaceAfter=1.5,
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
    text = text.replace("\u2014", " -- ").replace("\u2013", "-")
    text = re.sub(r"\u00a7(\d)", r"Section \1", text)
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

        # bold caption line, e.g. "**Figure 1 -- ...**" or "**Executive Summary label.**"
        if re.match(r"^\*\*[^*]+\*\*\.?$", stripped) or re.match(r"^\*\*(Figure|Table) \d", stripped):
            flowables.append(para(stripped, "Caption"))
            i += 1
            continue

        # exec-summary bold lead-in labels like "**The business problem.** text..."
        if re.match(r"^\*\*[^*]+\.\*\*\s", stripped):
            flowables.append(para(stripped, "ExecLabel"))
            i += 1
            continue

        if stripped.startswith("*") and stripped.endswith("*") and not stripped.startswith("**"):
            flowables.append(para(stripped.strip("*"), "SourceNote"))
            i += 1
            continue

        if re.match(r"^\d+\.\s", stripped):
            items = []
            while i < n and re.match(r"^\d+\.\s", lines[i].strip()):
                item_text = re.sub(r"^\d+\.\s", "", lines[i].strip())
                j = i + 1
                while j < n and lines[j].strip() and not re.match(r"^\d+\.\s", lines[j].strip()) \
                        and not lines[j].strip().startswith(("#", "-", "*", "|")):
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
                while j < n and lines[j].strip() and not lines[j].strip().startswith(("-", "#", "|", "*", "!")):
                    item_text += " " + lines[j].strip()
                    j += 1
                items.append(ListItem(para(item_text, "Bullet"), leftIndent=14))
                i = j
            flowables.append(ListFlowable(items, bulletType="bullet", start="\u2022", leftIndent=16))
            flowables.append(Spacer(1, 4))
            continue

        # plain paragraph -- accumulate until blank line
        buf = [stripped]
        i += 1
        while i < n and lines[i].strip() and not lines[i].strip().startswith(("#", "|", "-", "!", "*", "1.")):
            buf.append(lines[i].strip())
            i += 1
        flowables.append(para(" ".join(buf), "Body"))

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
