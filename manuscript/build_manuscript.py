"""Render the manuscript to .docx with python-docx (Aptos, navy headings, numbered references)."""

from __future__ import annotations

import os
import re
import sys

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from refs import REFS  # noqa: E402
import content_front as CF  # noqa: E402
import content_method as CM  # noqa: E402
import content_results as CR  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG_DIR = os.environ.get("PAER_FIGURES", os.path.join(ROOT, "figures"))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "PAER_JCP_manuscript.docx")

NAVY = RGBColor(0x1F, 0x38, 0x64)
FONT = "Aptos"
BODY_PT = 10.5

# --------------------------------------------------------------------------- #
# citation numbering
# --------------------------------------------------------------------------- #
order: list[str] = []


def cite_number(key: str) -> int:
    if key not in REFS:
        raise KeyError(f"unknown reference key {key}")
    if key not in order:
        order.append(key)
    return order.index(key) + 1


def render_cites(text: str) -> str:
    def repl(m):
        keys = [k.strip() for k in m.group(1).split(",")]
        nums = sorted(cite_number(k) for k in keys)
        # compress runs of 3+ consecutive numbers
        parts, i = [], 0
        while i < len(nums):
            j = i
            while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
                j += 1
            if j - i >= 2:
                parts.append(f"{nums[i]}–{nums[j]}")
            else:
                parts.extend(str(n) for n in nums[i:j + 1])
            i = j + 1
        return "[" + ",".join(parts) + "]"
    return re.sub(r"\{([A-Z][A-Za-z0-9_]*(?:\s*,\s*[A-Z][A-Za-z0-9_]*)*)\}", repl, text)


# --------------------------------------------------------------------------- #
# docx helpers
# --------------------------------------------------------------------------- #
def set_run_font(run, size=BODY_PT, bold=None, italic=None, color=None, name=FONT):
    run.font.name = name
    run.font.size = Pt(size)
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts"); rpr.append(rfonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rfonts.set(qn(attr), name)
    if bold is not None:
        run.font.bold = bold
    if italic is not None:
        run.font.italic = italic
    if color is not None:
        run.font.color.rgb = color


def para(doc, text="", size=BODY_PT, bold=False, italic=False, color=None, align=WD_ALIGN_PARAGRAPH.JUSTIFY,
         space_after=6, space_before=0, style=None, keep_next=False, first_indent=None, left_indent=None):
    p = doc.add_paragraph(style=style) if style else doc.add_paragraph()
    p.alignment = align
    pf = p.paragraph_format
    pf.space_after = Pt(space_after); pf.space_before = Pt(space_before); pf.line_spacing = 1.15
    if keep_next:
        pf.keep_with_next = True
    if first_indent is not None:
        pf.first_line_indent = Cm(first_indent)
    if left_indent is not None:
        pf.left_indent = Cm(left_indent)
    if text:
        add_text(p, text, size=size, bold=bold, italic=italic, color=color)
    return p


def add_text(p, text, size=BODY_PT, bold=False, italic=False, color=None):
    """Add text, honouring **bold** segments."""
    segs = re.split(r"(\*\*[^*]+\*\*)", text)
    for seg in segs:
        if not seg:
            continue
        if seg.startswith("**") and seg.endswith("**"):
            r = p.add_run(seg[2:-2]); set_run_font(r, size=size, bold=True, italic=italic, color=color)
        else:
            r = p.add_run(seg); set_run_font(r, size=size, bold=bold, italic=italic, color=color)


def heading(doc, text, level):
    sizes = {1: 13, 2: 11.5, 3: 10.5}
    p = para(doc, "", align=WD_ALIGN_PARAGRAPH.LEFT, space_before=12 if level == 1 else 8, space_after=4, keep_next=True)
    r = p.add_run(text); set_run_font(r, size=sizes[level], bold=True, italic=(level == 3), color=NAVY)
    # outline level for navigation pane
    ppr = p._element.get_or_add_pPr()
    ol = OxmlElement("w:outlineLvl"); ol.set(qn("w:val"), str(level - 1)); ppr.append(ol)
    return p


def shade(cell, hex_fill):
    tcPr = cell._element.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), hex_fill)
    tcPr.append(shd)


ORDER = ["tblStyle", "tblpPr", "tblOverlap", "bidiVisual", "tblStyleRowBandSize", "tblStyleColBandSize", "tblW", "jc",
         "tblCellSpacing", "tblInd", "tblBorders", "shd", "tblLayout", "tblCellMar", "tblLook", "tblCaption", "tblDescription"]


def _insert_ordered(tblPr, el):
    """Insert a tblPr child at its schema position."""
    name = el.tag.split("}")[1]
    idx = ORDER.index(name)
    for child in list(tblPr):
        cname = child.tag.split("}")[1]
        if cname in ORDER and ORDER.index(cname) > idx:
            child.addprevious(el); return
    tblPr.append(el)


def set_cell_margins(table, top=40, bottom=40, left=60, right=60):
    tblPr = table._element.tblPr
    mar = OxmlElement("w:tblCellMar")
    for side, val in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        el = OxmlElement(f"w:{side}"); el.set(qn("w:w"), str(val)); el.set(qn("w:type"), "dxa"); mar.append(el)
    _insert_ordered(tblPr, mar)


def set_table_borders(table, color="BFC7D5", sz=4):
    tblPr = table._element.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single"); el.set(qn("w:sz"), str(sz)); el.set(qn("w:space"), "0"); el.set(qn("w:color"), color)
        borders.append(el)
    _insert_ordered(tblPr, borders)


def add_table(doc, spec):
    caption = render_cites(spec["caption"])
    cp = para(doc, "", align=WD_ALIGN_PARAGRAPH.LEFT, space_before=8, space_after=4, keep_next=True)
    m = re.match(r"(Table \d+\.)\s*(.*)", caption, re.S)
    r = cp.add_run(m.group(1) + " "); set_run_font(r, size=9.5, bold=True, color=NAVY)
    r = cp.add_run(m.group(2)); set_run_font(r, size=9.5)
    header, rows, widths = spec["header"], spec["rows"], spec["widths"]
    fs = spec.get("font", 8)
    table = doc.add_table(rows=1 + len(rows), cols=len(header))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    set_table_borders(table); set_cell_margins(table)
    total = sum(widths)
    scale = 16.4 / total if total > 16.4 else 1.0
    for i, w in enumerate(widths):
        for cell in table.columns[i].cells:
            cell.width = Cm(w * scale)
    for j, h in enumerate(header):
        c = table.cell(0, j); c.text = ""
        p = c.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_after = Pt(0)
        rr = p.add_run(h); set_run_font(rr, size=fs, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF))
        shade(c, "1F3864")
    for i, row in enumerate(rows, start=1):
        for j, val in enumerate(row):
            c = table.cell(i, j); c.text = ""
            p = c.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_after = Pt(0)
            add_text(p, render_cites(str(val)), size=fs)
            if i % 2 == 0:
                shade(c, "EEF2F8")
    # repeat header row
    trPr = table.rows[0]._tr.get_or_add_trPr()
    th = OxmlElement("w:tblHeader"); th.set(qn("w:val"), "true"); trPr.append(th)
    if spec.get("note"):
        para(doc, spec["note"], size=8.5, italic=True, align=WD_ALIGN_PARAGRAPH.LEFT, space_before=2)
    para(doc, "", space_after=4)


def add_figure(doc, spec):
    path = os.path.join(FIG_DIR, spec["path"])
    p = para(doc, "", align=WD_ALIGN_PARAGRAPH.CENTER, space_before=8, space_after=2, keep_next=True)
    p.add_run().add_picture(path, width=Cm(spec.get("width_cm", 15)))
    caption = render_cites(spec["caption"])
    cp = para(doc, "", align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=10)
    m = re.match(r"(Figure \d+\.)\s*(.*)", caption, re.S)
    r = cp.add_run(m.group(1) + " "); set_run_font(r, size=9.5, bold=True, color=NAVY)
    r = cp.add_run(m.group(2)); set_run_font(r, size=9.5)


def add_bullets(doc, items):
    for it in items:
        p = para(doc, "", style="List Bullet", align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=3)
        add_text(p, render_cites(it))


def render_blocks(doc, blocks):
    for kind, payload in blocks:
        if kind in ("h1", "h2", "h3"):
            heading(doc, payload, int(kind[1]))
        elif kind == "p":
            para(doc, render_cites(payload))
        elif kind == "bullets":
            add_bullets(doc, payload)
        elif kind == "table":
            add_table(doc, payload)
        elif kind == "figure":
            add_figure(doc, payload)
        else:
            raise ValueError(kind)


def add_page_number(section):
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = footer.add_run()
    for tag, text in (("begin", None), (None, "PAGE"), ("end", None)):
        if tag:
            el = OxmlElement("w:fldChar"); el.set(qn("w:fldCharType"), tag); run._r.append(el)
        else:
            el = OxmlElement("w:instrText"); el.set(qn("xml:space"), "preserve"); el.text = text; run._r.append(el)
    set_run_font(run, size=9)


def main():
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    sec.left_margin = sec.right_margin = Cm(2.3); sec.top_margin = sec.bottom_margin = Cm(2.3)
    add_page_number(sec)
    # default style
    st = doc.styles["Normal"]; st.font.name = FONT; st.font.size = Pt(BODY_PT)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    lb = doc.styles["List Bullet"]; lb.font.name = FONT; lb.font.size = Pt(BODY_PT)

    # ---- title block ----
    para(doc, "Article", size=10, bold=True, color=NAVY, align=WD_ALIGN_PARAGRAPH.LEFT, space_after=6)
    para(doc, CF.TITLE, size=17, bold=True, color=NAVY, align=WD_ALIGN_PARAGRAPH.LEFT, space_after=10)
    p = para(doc, "", align=WD_ALIGN_PARAGRAPH.LEFT, space_after=2)
    r = p.add_run(CF.AUTHOR); set_run_font(r, size=11, bold=True)
    para(doc, CF.AFFIL, size=9.5, align=WD_ALIGN_PARAGRAPH.LEFT, space_after=10)
    p = para(doc, "", align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=8)
    r = p.add_run("Abstract: "); set_run_font(r, size=10, bold=True)
    r = p.add_run(render_cites(CF.ABSTRACT)); set_run_font(r, size=10)
    p = para(doc, "", align=WD_ALIGN_PARAGRAPH.LEFT, space_after=12)
    r = p.add_run("Keywords: "); set_run_font(r, size=10, bold=True)
    r = p.add_run(CF.KEYWORDS); set_run_font(r, size=10)

    # ---- body ----
    render_blocks(doc, CF.FRONT)
    add_table(doc, CM.TABLE1)
    render_blocks(doc, CM.METHOD)
    render_blocks(doc, CR.results_blocks())
    render_blocks(doc, CR.DISCUSSION)
    render_blocks(doc, CR.BACK)

    # ---- references ----
    heading(doc, "References", 1)
    for i, key in enumerate(order, start=1):
        p = para(doc, "", align=WD_ALIGN_PARAGRAPH.LEFT, space_after=3, left_indent=0.8, first_indent=-0.8)
        add_text(p, f"{i}.\t{REFS[key]}", size=9)
        p.paragraph_format.tab_stops.add_tab_stop(Cm(0.8))
    unused = [k for k in REFS if k not in order]
    # python-docx's default template omits the required w:percent on w:zoom
    zoom = doc.settings.element.find(qn("w:zoom"))
    if zoom is not None and zoom.get(qn("w:percent")) is None:
        zoom.set(qn("w:percent"), "100")
    doc.save(OUT)
    print(f"saved {OUT}; {len(order)} references cited; unused keys: {unused}")


if __name__ == "__main__":
    main()
