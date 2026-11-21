"""docx_kit.py -- small helpers for the two Word files of the lawyer validation (python-docx). Plain styles, A4, repeat-header tables, shaded cells, a page-number footer."""
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

INK = RGBColor(0x1F, 0x2A, 0x37)
BLUE = RGBColor(0x1F, 0x3A, 0x5F)
GREY = RGBColor(0x5F, 0x6B, 0x7A)
RED = RGBColor(0x9B, 0x2C, 0x2C)
FONT = "Calibri"


def new_doc(margin_cm=2.0, base_pt=10.5):
    d = Document()
    s = d.sections[0]
    s.page_width, s.page_height = Cm(21.0), Cm(29.7)
    s.left_margin = s.right_margin = Cm(margin_cm)
    s.top_margin, s.bottom_margin = Cm(1.8), Cm(1.8)
    st = d.styles["Normal"]
    st.font.name, st.font.size, st.font.color.rgb = FONT, Pt(base_pt), INK
    st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    st.paragraph_format.space_after, st.paragraph_format.space_before, st.paragraph_format.line_spacing = Pt(4), Pt(0), 1.08
    for name, size, before, after in (("Title", 20, 0, 4), ("Heading 1", 14, 14, 4), ("Heading 2", 11.5, 10, 3)):
        h = d.styles[name]
        h.font.name, h.font.size, h.font.bold, h.font.color.rgb = FONT, Pt(size), True, BLUE
        h.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
        h.element.rPr.rFonts.set(qn("w:ascii"), FONT)
        h.element.rPr.rFonts.set(qn("w:hAnsi"), FONT)
        h.paragraph_format.space_before, h.paragraph_format.space_after, h.paragraph_format.keep_with_next = Pt(before), Pt(after), True
    return d


def footer(d, text):
    p = d.sections[0].footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(text + "   ·   page ")
    r.font.size, r.font.color.rgb = Pt(8), GREY
    for kind, txt in (("begin", None), (None, "PAGE"), ("end", None)):
        run = p.add_run()
        run.font.size, run.font.color.rgb = Pt(8), GREY
        if kind:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), kind)
        else:
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = txt
        run._r.append(el)


def para(d_or_cell, text="", bold=False, italic=False, size=None, color=None, align=None, after=None, before=None, style=None, keep=False):
    p = d_or_cell.add_paragraph(style=style) if style else d_or_cell.add_paragraph()
    if text:
        add_runs(p, text, bold=bold, italic=italic, size=size, color=color)
    if align:
        p.alignment = align
    if after is not None:
        p.paragraph_format.space_after = Pt(after)
    if before is not None:
        p.paragraph_format.space_before = Pt(before)
    if keep:
        p.paragraph_format.keep_with_next = True
    return p


def add_runs(p, text, bold=False, italic=False, size=None, color=None):
    """text may hold **bold** pieces."""
    parts = text.split("**")
    for i, piece in enumerate(parts):
        if not piece:
            continue
        r = p.add_run(piece)
        r.bold = bold or (i % 2 == 1)
        r.italic = italic
        if size:
            r.font.size = Pt(size)
        if color is not None:
            r.font.color.rgb = color
    return p


def bullets(d, items, size=None, after=2):
    for t in items:
        p = d.add_paragraph(style="List Bullet")
        add_runs(p, t, size=size)
        p.paragraph_format.space_after = Pt(after)


def numbered(d, items, size=None, after=2):
    for t in items:
        p = d.add_paragraph(style="List Number")
        add_runs(p, t, size=size)
        p.paragraph_format.space_after = Pt(after)


def shade(cell, hex_fill):
    tcPr = cell._tc.get_or_add_tcPr()
    sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear")
    sh.set(qn("w:color"), "auto")
    sh.set(qn("w:fill"), hex_fill)
    tcPr.append(sh)


def cell_margins(table, top=50, bottom=50, left=80, right=80):
    tblPr = table._tbl.tblPr
    m = OxmlElement("w:tblCellMar")
    for k, v in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        e = OxmlElement(f"w:{k}")
        e.set(qn("w:w"), str(v))
        e.set(qn("w:type"), "dxa")
        m.append(e)
    tblPr.append(m)


def repeat_header(row):
    trPr = row._tr.get_or_add_trPr()
    e = OxmlElement("w:tblHeader")
    e.set(qn("w:val"), "true")
    trPr.append(e)


def no_split(row):
    trPr = row._tr.get_or_add_trPr()
    e = OxmlElement("w:cantSplit")
    e.set(qn("w:val"), "true")
    trPr.append(e)


def table(d, head, rows, widths_cm, size=9, head_fill="E3EAF3", zebra=None, first_col_bold=False):
    t = d.add_table(rows=1, cols=len(head))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    cell_margins(t)
    for i, h in enumerate(head):
        c = t.rows[0].cells[i]
        c.width = Cm(widths_cm[i])
        shade(c, head_fill)
        c.paragraphs[0].paragraph_format.space_after = Pt(0)
        add_runs(c.paragraphs[0], h, bold=True, size=size, color=BLUE)
    repeat_header(t.rows[0])
    for ri, row in enumerate(rows):
        cells = t.add_row().cells
        no_split(t.rows[-1])
        for i, val in enumerate(row):
            cells[i].width = Cm(widths_cm[i])
            if zebra and ri % 2 == 1:
                shade(cells[i], zebra)
            lines = val if isinstance(val, list) else [val]
            for li, line in enumerate(lines):
                p = cells[i].paragraphs[0] if li == 0 else cells[i].add_paragraph()
                p.paragraph_format.space_after = Pt(1)
                add_runs(p, str(line), size=size, bold=(first_col_bold and i == 0))
    return t


def box(d, text_lines, fill="FFF4E5", size=9.5, width_cm=17.0, bold_first=False):
    t = d.add_table(rows=1, cols=1)
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell_margins(t, 80, 80, 120, 120)
    c = t.rows[0].cells[0]
    c.width = Cm(width_cm)
    shade(c, fill)
    for i, line in enumerate(text_lines):
        p = c.paragraphs[0] if i == 0 else c.add_paragraph()
        p.paragraph_format.space_after = Pt(2)
        add_runs(p, line, size=size, bold=(bold_first and i == 0))
    d.add_paragraph().paragraph_format.space_after = Pt(2)
    return t
