"""The English of a page or a document as a Word file, with the marks the reader put in shown as marks (never tidied away) and the stamp on every page.

Needs python-docx (pip install python-docx); available() says whether it is there. A crossed-out word stays crossed out, a word written above the line is bold and green, a
doubtful reading and a value the readings disagree on are highlighted, and 'Read these first' comes before the English. Nothing here changes a word.
"""
import datetime, io, re

STAMP = "Machine draft. Not a certified translation."
TOKEN = re.compile(r"(~~.+?~~|\^[^^\n]+?\^|<doubtful:[^>]*>|\[[^\[\]\n]*?: check\]|\[(?:unclear|sic|stamp over text|seal over text|signature|struck: \?)\]|\(\?\))", re.S)
_BAD = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff]")


def available():
    try:
        import docx  # noqa: F401
        return True
    except ImportError:
        return False


def clean(s):
    return _BAD.sub("", s or "")


def segments(text):
    """[(kind, text)] for one paragraph: kind is plain, strike, insert, doubt, differ or mark. The text of a strike or insert has its ~~ or ^ signs removed."""
    out = []
    for part in TOKEN.split(text or ""):
        if not part:
            continue
        if part.startswith("~~") and part.endswith("~~") and len(part) > 4:
            out.append(("strike", part[2:-2]))
        elif part.startswith("^") and part.endswith("^") and len(part) > 2:
            out.append(("insert", part[1:-1]))
        elif part.startswith("<doubtful:"):
            out.append(("doubt", "[" + part[1:-1] + "]"))
        elif part.endswith(": check]"):
            out.append(("differ", part))
        elif TOKEN.fullmatch(part):
            out.append(("mark", part))
        else:
            out.append(("plain", part))
    return out


def make_docx(title, language, light, items, paras, glossary=(), must_check=(), note=""):
    """Bytes of a .docx. items: the 'Read these first' items [{'title','detail'}]; paras: the English as paragraphs; glossary: [{'word','english','note'}]; must_check: [{'type','a'}]."""
    from docx import Document
    from docx.enum.text import WD_COLOR_INDEX
    from docx.shared import Pt, RGBColor
    d = Document()
    st = d.styles["Normal"]; st.font.name = "Calibri"; st.font.size = Pt(11)
    sec = d.sections[0]
    sec.footer.paragraphs[0].text = STAMP
    sec.header.paragraphs[0].text = clean(title)
    d.add_heading(clean(title), level=1)
    p = d.add_paragraph(); r = p.add_run(STAMP); r.bold = True; r.font.color.rgb = RGBColor(0xB3, 0x26, 0x1E)
    d.add_paragraph("%s. Light: %s (a reading order, not a verdict). Prepared %s by the Reading Desk. A person who reads the language must check every name, date, number and amount against the original page." % (
        clean(language), (light or "").upper() or "none", datetime.date.today().isoformat()))
    if note:
        d.add_paragraph(clean(note))
    if items:
        d.add_heading("Read these first", level=2)
        for i in items:
            para = d.add_paragraph(style="List Number")
            para.add_run(clean(i.get("title", ""))).bold = True
            if i.get("detail"):
                para.add_run(" " + clean(i["detail"]))
    d.add_heading("English", level=2)
    key = d.add_paragraph(); kr = key.add_run("Key: crossed-out text was crossed out on the page; bold green text was written above the line; highlighted text is a doubtful reading or a value the readings disagree on."); kr.italic = True; kr.font.size = Pt(9)
    for text in paras or [""]:
        para = d.add_paragraph()
        for kind, seg in segments(clean(text)):
            run = para.add_run(seg)
            if kind == "strike":
                run.font.strike = True; run.font.color.rgb = RGBColor(0xB3, 0x26, 0x1E)
            elif kind == "insert":
                run.bold = True; run.font.color.rgb = RGBColor(0x1B, 0x7A, 0x4B)
            elif kind in ("doubt", "differ", "mark"):
                run.font.highlight_color = WD_COLOR_INDEX.YELLOW
                run.bold = kind == "differ"
    if glossary:
        d.add_heading("Glossary notes (words with a settled legal meaning; notes only)", level=2)
        t = d.add_table(rows=1, cols=3); t.style = "Table Grid"
        for c, h in zip(t.rows[0].cells, ("Word as read", "Normally means", "Note")):
            c.text = h
        for g in glossary:
            row = t.add_row().cells
            row[0].text, row[1].text, row[2].text = clean(g.get("word")), clean(g.get("english")), clean(g.get("note"))
    if must_check:
        d.add_heading("Must-check list (confirm each against the original)", level=2)
        t = d.add_table(rows=1, cols=2); t.style = "Table Grid"
        t.rows[0].cells[0].text, t.rows[0].cells[1].text = "Kind", "Value"
        for m in must_check:
            row = t.add_row().cells
            row[0].text, row[1].text = clean(str(m.get("type", ""))), clean(str(m.get("a") if m.get("a") is not None else ""))
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


def selftest():
    assert segments("a ~~victim~~ ^witness^ b [x or y: check] <doubtful: w 'a'> [unclear] c") == [
        ("plain", "a "), ("strike", "victim"), ("plain", " "), ("insert", "witness"), ("plain", " b "), ("differ", "[x or y: check]"), ("plain", " "), ("doubt", "[doubtful: w 'a']"),
        ("plain", " "), ("mark", "[unclear]"), ("plain", " c")]
    assert clean("a\x00b\x0bc") == "abc"
    if available():
        import docx
        data = make_docx("Test <b>x</b>", "Assamese", "amber", [{"title": "Date", "detail": "14/3 or 11/3"}], ["Dated [14/3 or 11/3: check] the ~~victim~~ ^witness^ spoke\x00."],
                         [{"word": "w", "english": "e", "note": "n"}], [{"type": "date", "a": "14/3"}])
        doc = docx.Document(io.BytesIO(data))
        text = "\n".join(p.text for p in doc.paragraphs)
        assert STAMP in text and "Dated [14/3 or 11/3: check] the victim witness spoke." in text and "Read these first" in text and "Test <b>x</b>" in text
        assert doc.sections[0].footer.paragraphs[0].text == STAMP and len(doc.tables) == 2
        struck = [r.text for p in doc.paragraphs for r in p.runs if r.font.strike]
        assert struck == ["victim"], struck
        print("docx_out selftest OK")
    else:
        print("docx_out selftest OK (python-docx missing: the Word file is switched off)")


if __name__ == "__main__":
    selftest()
