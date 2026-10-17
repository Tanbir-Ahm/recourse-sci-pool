"""
build_shelf_sheet.py -- writes acts/ACT_SHELF_SHEET.docx, the sheet for Mr. Advocate for the Act shelf (STATUTE_COVERAGE_PLAN.md step 2): about ten sections of each of the five long loaded Acts, and EVERY section of the two
short ones (Muslim Women 2019, Public Property 1984: Recourse hands the answer model the whole Act for those), in full, as Recourse will hand them to the answer model, to be checked against the Act; the wording the site
will show; and four questions only a lawyer can answer (what the shelf cannot know).

The sections of the five long Acts are Claude's choice, not a statistical sample, and the sheet says so: the sections the Act Directory's appeal line for that Act cites, the sections a pointer names, the sections that were
the marked answer to the evaluation questions the Act Directory can detect, and the sections that carry the Act's main offence or protection (Claude's judgment). A column says why each is there. For a whole-Act entry of the
manifest the builder refuses to build unless the sheet lists every section that is not omitted.

Nothing here is recorded as confirmed by anyone. Claude records only what Mr. Advocate answers.
Run: python acts/build_shelf_sheet.py --recourse <Recourse checkout> [--out acts/ACT_SHELF_SHEET.docx]
"""
import argparse
import datetime
import json
import os
import re
import sys

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.shared import Pt, Cm, RGBColor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from build_directory_sheet import _hyperlink  # noqa: E402

# (section, why it is on the sheet).  Reasons that start with "appeal line" or "pointer" are checked against the data when the sheet is built.
CHOICE = {
    "pc_act_1988": [("2", "who is a 'public servant' (definitions; Claude's choice)"), ("7", "the main offence: a public servant taking an undue advantage"), ("8", "the main offence: giving one"),
                    ("13", "criminal misconduct (after the 2018 amendment)"), ("17", "who may investigate (evaluation question PC08)"), ("17A", "prior approval for an enquiry (evaluation question PC04)"),
                    ("19", "previous sanction (evaluation question PC03)"), ("20", "presumption (evaluation question PC06)"), ("27", "appeal line: the High Court's appeal and revision")],
    "pocso_act_2012": [("3", "penetrative sexual assault (the main offence)"), ("4", "its punishment (evaluation question PS01)"), ("19", "reporting (evaluation question PS03)"), ("24", "recording a child's statement (evaluation question PS05)"),
                       ("28", "appeal line: Special Courts"), ("29", "presumption (evaluation question PS06)"), ("31", "appeal line: the Code applies to a Special Court"), ("35", "time for the child's evidence and the trial (PS07)"),
                       ("42", "alternate punishment (PS13)")],
    "uapa_1967": [("2", "appeal line: the definition of 'court' (also the Act's other definitions)"), ("15", "terrorist act (evaluation question UA03)"), ("16", "its punishment"), ("17", "raising funds (UA04)"),
                  ("20", "membership of a terrorist gang (UA11)"), ("26", "appeal line: forfeiture ordered by the court"), ("28", "appeal line: appeal against forfeiture"), ("35", "designating an organisation or an individual (UA06)"),
                  ("43D", "bail and the 180-day extension (UA01, UA02)"), ("45", "previous sanction (UA05)")],
    "pmla_2002": [("2", "definitions, including 'proceeds of crime' (PM08)"), ("3", "the offence of money-laundering"), ("4", "its punishment (PM07)"), ("5", "attachment (PM03)"), ("19", "power to arrest (PM02)"),
                  ("26", "appeal line: to the Appellate Tribunal"), ("42", "appeal line: to the High Court"), ("44", "appeal line: offences triable by Special Courts"), ("45", "bail: the twin conditions (PM01)"),
                  ("46", "appeal line: the Code applies to a Special Court")],
    "sc_st_act_1989": [("2", "definitions (SS13)"), ("3", "the offences (SS01, SS08, SS11)"), ("4", "neglect of duties by a public servant (SS06)"), ("8", "presumption (SS07)"), ("14", "Special Courts (SS10)"),
                       ("14A", "appeal line: appeals"), ("15A", "rights of victims and witnesses (SS05)"), ("18", "pointer: anticipatory bail (section 438 of the Code)"), ("18A", "pointer: no enquiry or approval; section 438 again")],
    # The two short Acts are handed over WHOLE, so every section is here (the builder checks that none is missing).  The ids are the frozen evaluation questions of act_shelf/eval_questions_pair.json.
    "muslim_women_act_2019": [("1", "extent and commencement (MW06, MW12); the footnote on Jammu and Kashmir / Ladakh goes to the answer model with it"), ("2", "definitions: 'talaq' (MW10)"),
                              ("3", "talaq void and illegal (MW01, MW05)"), ("4", "punishment (MW02)"), ("5", "subsistence allowance (MW03, MW11)"), ("6", "custody of minor children (MW04)"),
                              ("7", "cognizable, compoundable, bail (MW07-MW09). CORRECTED against the PDF: see the note under this table"), ("8", "repeal of the Ordinance and savings")],
    "pdpp_act_1984": [("1", "extent and commencement; the footnote on Jammu and Kashmir goes to the answer model with it"), ("2", "definitions: 'mischief', 'public property' (PD04, PD05, PD07, PD10)"),
                      ("3", "mischief causing damage to public property (PD02, PD06, PD11)"), ("4", "by fire or explosive substance (PD01, PD08). Reads 'rigrous' as India Code's database has it: see the note under this table"),
                      ("5", "special provisions regarding bail (PD03, PD09)"), ("6", "saving (PD12). In the ordinary shelf path a 'saving' section is never found by meaning; here the whole Act is handed over"), ("7", "repeal of the Ordinance and saving")],
    # The Dowry (1961) and Juvenile Justice (2015) Acts are searched by meaning (not handed over whole: 11,904 and 153,183 characters). These Acts have NO appeal section and NO pointers, so no "appeal line" / "pointer" reasons here.
    # The ids are the frozen evaluation questions of act_shelf/eval_questions_jjdowry.json.
    "dowry_prohibition_act_1961": [("2", "the definition of “dowry” (evaluation question D04)"), ("3", "the offence of giving or taking dowry, and its punishment (D02, D03)"), ("4", "the offence of demanding dowry (D01)"),
                                   ("4A", "ban on advertising a dowry demand (D05)"), ("5", "an agreement to give or take dowry is void (D06)"), ("6", "dowry is for the benefit of the wife or her heirs (D07)"),
                                   ("7", "cognizance of offences: which court, and the time limit (D08)"), ("8", "offences cognizable, bailable and non-compoundable (D09)"), ("8A", "burden of proof in a dowry prosecution (D10)"),
                                   ("8B", "Dowry Prohibition Officers (D11)")],
    "jj_act_2015": [("2", "definitions, including who is a “child” (J17). CORRECTED against the PDF: the definition of “Child Welfare Officer” was garbled in India Code's database — see the note under this table"),
                    ("3", "the general principles to be followed in administering the Act (J16)"), ("8", "powers, functions and responsibilities of the Juvenile Justice Board (J04)"),
                    ("12", "bail to a person who is apparently a child in conflict with law (J03)"), ("15", "preliminary assessment into a heinous offence: when a child of 16+ may be tried as an adult (J01, J02)"),
                    ("27", "Child Welfare Committee: who decides on a child in need of care and protection (J09)"), ("57", "eligibility of prospective adoptive parents (J08)"), ("58", "procedure for adoption by Indian adoptive parents (J07)"),
                    ("74", "prohibition on disclosing a child's identity (J11)"), ("75", "punishment for cruelty to a child (J06)"), ("82", "corporal punishment (J15)"), ("94", "presumption and determination of age (J18)"),
                    ("101", "appeals against an order of the Board or the Committee (J14)")],
}
ORDER = ["pc_act_1988", "pocso_act_2012", "uapa_1967", "pmla_2002", "sc_st_act_1989", "muslim_women_act_2019", "pdpp_act_1984", "dowry_prohibition_act_1961", "jj_act_2015"]
NO_PDF_DATE = "not printed on the PDF"      # what build_act_chunks.py records as 'pdf_as_on' for a PDF with no "[As on the ...]" line (the Public Property Act's)


def _dmy(iso):
    """'2026-07-10T22:38:42Z' -> '10 July 2026'."""
    d = datetime.date.fromisoformat(iso[:10])
    return f"{d.day} {d.strftime('%B %Y')}"


def _clip(text, n=200):
    text = " ".join((text or "").split())
    return text if len(text) <= n else text[:n - 1].rstrip() + "…"


def _act_notes(m, shown):
    """Notes printed under an Act's table: the corrections made to India Code's database text, against the PDF, and the differences left as they are, in the sections that are on the sheet (from the manifest, word for word)."""
    notes = []
    fixes = [c for c in m.get("corrections", []) if str(c["section"]) in shown]
    if fixes:
        notes.append("Corrections made against India Code's PDF in the sections above (the text in the table is the corrected text). " + " ".join(
            f"({i}) s.{c['section']}: the database read \"{_clip(c['from'])}\"; the PDF reads \"{_clip(c['to'])}\". Why: {_clip(c['why'], 600).rstrip('.')}." for i, c in enumerate(fixes, 1)))
    acc = [c for c in m.get("accepted", []) if str(c["section"]) in shown]
    if acc:
        notes.append("Differences left as India Code's database has them, with the reason. " + " ".join(f"({i}) s.{c['section']} (\"{c['word']}\"): {_clip(c['why'], 600).rstrip('.')}." for i, c in enumerate(acc, 1)))
    return notes


def _small(cell, text, size=7, bold=False, italic=False, grey=False):
    cell.text = ""
    p = cell.paragraphs[0]
    r = p.add_run(text)
    r.font.size = Pt(size)
    r.bold = bold
    r.italic = italic
    if grey:
        r.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
    return p


def _check_choice(rec, directory, manifest, sections):
    """The sheet's own consistency: every section exists and is not a stub; 'appeal line' reasons are cited by that Act's appeal line; 'pointer' reasons are pointed to by the manifest."""
    problems = []
    for key, rows in CHOICE.items():
        appeal = (next(a for a in directory["acts"] if a["id"] == key).get("appeal") or {}).get("text") or ""
        entry = next(a for a in manifest["acts"] if a["key"] == key)
        pointed = {s for p in entry.get("pointers", []) for s in p["sections"]}
        if entry.get("whole_act"):                           # handed over whole: the sheet must show every section, or it would be a sample of something that is read in full
            missing = sorted({c["section_number"] for c in sections[key].values() if not c.get("omitted")} - {s for s, _ in rows})
            extra = sorted({s for s, _ in rows} - set(sections[key]))
            if missing or extra:
                problems.append(f"{key}: handed over whole, but the sheet lacks section(s) {missing} / lists unknown section(s) {extra}")
        for sec, why in rows:
            c = sections[key].get(sec)
            if c is None or c.get("omitted"):
                problems.append(f"{key} s.{sec}: not on the shelf or a stub")
            if why.startswith("appeal line") and not re.search(r"\bsections?\b[^.]*?(?<![0-9A-Za-z])" + re.escape(sec) + r"(?![0-9A-Za-z])", appeal):
                problems.append(f"{key} s.{sec}: the appeal line does not cite it")
            if why.startswith("pointer") and sec not in pointed:
                problems.append(f"{key} s.{sec}: no pointer names it")
    return problems


def build(recourse, out):
    shelf_dir = os.path.join(recourse, "act_shelf")
    manifest = json.load(open(os.path.join(shelf_dir, "manifest.json"), encoding="utf-8"))
    directory = json.load(open(os.path.join(recourse, "acts_directory.json"), encoding="utf-8"))
    sections = {k: {c["section_number"]: c for c in json.load(open(os.path.join(shelf_dir, f"{k}.json"), encoding="utf-8"))} for k in ORDER}
    load_report = json.load(open(os.path.join(shelf_dir, "LOAD_REPORT.json"), encoding="utf-8"))["reports"]
    problems = _check_choice(None, directory, manifest, sections)
    if problems:
        raise SystemExit("the sheet's choice of sections is inconsistent with the data:\n  " + "\n  ".join(problems))
    sys.path.insert(0, recourse)
    import act_directory as AD
    import act_shelf as S
    held = {k: {"state": "used", "loaded_on": next(a for a in manifest["acts"] if a["key"] == k)["loaded_on"]} for k in ORDER}
    short_words = sum(load_report[k]["ordered_check"]["words_compared"] for k in ("muslim_women_act_2019", "pdpp_act_1984"))      # the two short Acts added 2026-10-17
    latest_words = sum(load_report[k]["ordered_check"]["words_compared"] for k in ("dowry_prohibition_act_1961", "jj_act_2015"))  # the Dowry and JJ Acts added later that day
    pm = [{"id": "pmla_2002", "short": next(a for a in directory["acts"] if a["id"] == "pmla_2002")["short"], "how": "named"}]
    notice = AD.notice(pm, "answer", held={"pmla_2002": held["pmla_2002"]})["text"]
    notice_unused = AD.notice(pm, "answer", held={"pmla_2002": {"state": "unused", "loaded_on": held["pmla_2002"]["loaded_on"]}})["text"]
    caption = f"Official text from India Code, loaded {S.loaded_label(held['pmla_2002']['loaded_on'])}; not yet read by our reviewer"
    mwk = "muslim_women_act_2019"
    mw = [{"id": mwk, "short": next(a for a in directory["acts"] if a["id"] == mwk)["short"], "how": "named"}]
    notice_whole = AD.notice(mw, "answer", held={mwk: {"state": "used", "loaded_on": held[mwk]["loaded_on"], "whole": True}})["text"]

    doc = Document()
    sec = doc.sections[0]
    sec.orientation = WD_ORIENT.LANDSCAPE
    sec.page_width, sec.page_height = sec.page_height, sec.page_width
    for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(sec, side, Cm(1.4))
    st = doc.styles["Normal"]
    st.font.name = "Calibri"
    st.font.size = Pt(9.5)

    doc.add_heading("Act shelf v1: sheet for Mr. Advocate", level=1)
    p = doc.add_paragraph()
    p.add_run("What this is. ").bold = True
    p.add_run("Recourse can now keep the full text of an Act that is not in its BNS/BNSS library, and hand the sections that bear on a question to the answer model, when the question names that Act "
              "(for example \"section 45 of the PMLA\", \"POCSO\", \"SC/ST Act\"). Nine Acts are loaded: the Prevention of Corruption Act, 1988; POCSO, 2012; the UAPA, 1967; the PMLA, 2002; the SC/ST (Prevention of Atrocities) Act, 1989; "
              "the Muslim Women (Protection of Rights on Marriage) Act, 2019; the Prevention of Damage to Public Property Act, 1984; the Dowry Prohibition Act, 1961; and the Juvenile Justice (Care and Protection of Children) Act, 2015. "
              "Two of them — the Muslim Women Act (8 sections) and the Public Property Act (7) — are short, so when a question names one of those Recourse hands the answer model the whole Act, not the sections closest to the question; this sheet shows every section of those two. "
              "For the other seven (including the Dowry Act's 13 sections and the Juvenile Justice Act's 112), the answer model gets the sections closest to the question, and this sheet shows a selection with the reason each is here. "
              "The text comes from India Code's own database. A program then compared it with India Code's PDF of the same Act: the arrangement of sections is identical, and every section was read against the PDF's own text word by word, in order, "
              "in both directions (so a doubled word, a lost apostrophe or a whole lost proviso is found, not only an unknown word). It found, and the loader now corrects against the PDF, among others: a proviso of the PMLA's section 44 that the database had lost, "
              "the words \"is said to commit aggravated sexual assault\" that POCSO's section 9 had in the wrong place, in section 7 of the Muslim Women Act a piece of clause (a) copied into clauses (b) and (c) "
              "(as the database has it, her relatives could compound the offence and be heard on bail; the PDF says only the woman), and in the Juvenile Justice Act's definitions the term \"child care institution\" overwritten by a stray fragment in the definition of \"Child Welfare Officer\". The differences left are listed against what the PDF reads. "
              "Not on the shelf: the Schedules at the back of POCSO (the armed and security forces), the PMLA (the scheduled offences), the UAPA (the listed organisations and individuals) and the SC/ST Act (the IPC offences); the State or Union Territory amendments that India Code prints inside three sections (PC Act 17A, POCSO 42, SC/ST 14) and the Haryana amendments the PDF appends to the Dowry Act; and the Rules made under any of the Acts (the Juvenile Justice Model Rules among them). "
              "Both two-way comparisons and the Schedules are explained in the last section of the sheet. "
              "A program cannot tell whether a provision has since been amended, struck down or read down, or whether the text is the one a court would apply. ")
    p.add_run("That is why this sheet exists. Nothing on it is treated as checked by a person until you say so.").bold = True
    p = doc.add_paragraph()
    p.add_run("What we ask. ").bold = True
    p.add_run("(1) For each section below: does the text match the Act as in force today? Write OK, or write the correction. (2) Say whether the wording the site will show (the part headed \"Wording\", near the end) is fair. "
              "(3) Answer the four questions at the end. For the five longer Acts the sections are Claude's choice, not a statistical sample: a column says why each is here (the Act Directory's appeal line for the Act cites it, a pointer names it, "
              "it answered one of our test questions, or it carries the Act's main offence or protection). If there is a section you would check first and it is not here, name it. For the two short Acts every section is here.")
    p = doc.add_paragraph()
    p.add_run("What your answer changes. ").bold = True
    p.add_run("A sample check is recorded as a sample (which sections, by whom, when). The status of an Act's text stays \"not yet read by our reviewer\" unless you tell us you have read all of it. "
              "Claude records only what you answer, never on your behalf, and corrections to the text are made by reloading the Act with the correction listed against India Code's PDF, so they can be checked.")
    p = doc.add_paragraph()
    p.add_run("What the shelf cannot know. ").bold = True
    p.add_run("It holds the words of the Act, not what the courts have held about them (for example the Supreme Court's reading of the PMLA's section 45 or section 19, or of the UAPA's section 43D). "
              "The answer model is told to use only the sections it is given and not to state a case's holding that is not in the material; nobody has measured how well it obeys with these Acts, because the environment this was built in cannot call the answer model. "
              "The shelf is searched only when the question names the Act or uses a listed phrase (about two in five of our test questions did).")

    for key in ORDER:
        m = next(a for a in manifest["acts"] if a["key"] == key)
        d = next(a for a in directory["acts"] if a["id"] == key)
        doc.add_heading(f"{m['name']} ({m['citation']})", level=2)
        p = doc.add_paragraph()
        _hyperlink(p, d["url"], "open the Act on India Code")
        p.add_run("   |   ")
        _hyperlink(p, sections[key][CHOICE[key][0][0]]["source_url"], "its section list")
        fixes = len(m.get("corrections", []))
        oc = load_report[key]["ordered_check"]
        p2 = doc.add_paragraph()
        if m["pdf_as_on"] == NO_PDF_DATE:                    # the PDF has no "as on" date: say so rather than print 'as on not printed on the PDF', and do not claim the record is newer
            pdf_part = "compared with India Code's PDF of the Act (the PDF prints no \"as on\" date)"
            newer = f" India Code's database record was last changed on {_dmy(load_report[key]['record_last_modified']['max'])}; with no date on the PDF, nothing says which of the two is newer."
        else:
            pdf_part = f"compared with India Code's PDF \"as on {m['pdf_as_on']}\""
            newer = " India Code's database record is newer than the PDF."
        whole = " The whole Act is handed over to the answer model (every section below)." if m.get("whole_act") else ""
        r = p2.add_run(f"{m['sections_loaded']} sections loaded on {m['loaded_on']} (some are omitted or repealed and shown as such); {pdf_part}: arrangement of sections identical; "
                       f"{oc['sections_compared']} sections ({oc['words_compared']:,} words) read against the PDF word by word in both directions, {oc['differences']} difference(s) left, each explained; "
                       f"{fixes} correction(s) of India Code's database against the PDF, {len(m.get('accepted', []))} difference(s) accepted with a reason.{newer} Status: {m['text_status']} (not read by a person).{whole}")
        r.font.size = Pt(8)
        r.italic = True
        r.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
        t = doc.add_table(rows=1, cols=4)
        t.style = "Table Grid"
        heads = ["Section", "Why it is on the sheet", "The text as Recourse holds it", "Your check: OK, or the correction"]
        widths = [Cm(1.5), Cm(4.0), Cm(15.5), Cm(5.2)]
        for i, h in enumerate(heads):
            _small(t.rows[0].cells[i], h, size=8, bold=True)
        for sec_no, why in CHOICE[key]:
            c = sections[key][sec_no]
            row = t.add_row().cells
            _small(row[0], f"s.{sec_no}", size=8, bold=True)
            _small(row[1], why, size=7, italic=True, grey=True)
            _small(row[2], c["text"], size=7)
            fn = (c.get("footnotes") or "").strip()
            if fn:
                para = row[2].add_paragraph()
                rr = para.add_run("Amendment notes India Code prints: " + fn.replace("\n", " "))
                rr.font.size = Pt(6.5)
                rr.italic = True
                rr.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
            _small(row[3], "", size=7)
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = w
        for note in _act_notes(m, {s for s, _ in CHOICE[key]}):
            pn = doc.add_paragraph()
            rn = pn.add_run(note)
            rn.font.size = Pt(8)
            rn.italic = True
            rn.font.color.rgb = RGBColor(0x55, 0x55, 0x55)

    doc.add_heading("Wording: what the site will show", level=2)
    doc.add_paragraph("When the shelf's text reached the answer, the notice above the answer reads (this is the PMLA; the others are the same with their own names and links):")
    q = doc.add_paragraph(notice)
    q.paragraph_format.left_indent = Cm(1)
    doc.add_paragraph("Under each statute in \"Read the source\", one line:")
    q = doc.add_paragraph(caption + "; shortened here (when the section is longer than the excerpt); a link to the whole Act on India Code.")
    q.paragraph_format.left_indent = Cm(1)
    doc.add_paragraph("When the Act is loaded but nothing from it reached the answer (nothing close enough was found):")
    q = doc.add_paragraph(notice_unused)
    q.paragraph_format.left_indent = Cm(1)
    doc.add_paragraph("For the two short Acts, which are handed over whole, the notice says so (this is the Muslim Women Act; the Public Property Act is the same with its own name and link):")
    q = doc.add_paragraph(notice_whole)
    q.paragraph_format.left_indent = Cm(1)
    doc.add_paragraph("To the answer model, for those two Acts, the sentence about \"the sections our search found closest\" is replaced by: the material includes EVERY section of that Act; it does not include any rules made under the Act, or what the courts have held about it, "
                      "and if the question needs those the model must say in one sentence that the material does not show them and that the full text is on India Code. The rules in the next paragraph are the same.")
    doc.add_paragraph("To the answer model, in addition to the rules it always has: use only the sections it is given for anything it says about the Act; name each with the Act shown in its label, not as a BNS or BNSS section; do not state another section number, punishment, procedure or route of appeal from memory; "
                      "if the question needs a provision that is not among them, say so in one sentence and say that the full text is on India Code; a provision missing from the material does not mean the Act has none; where a section's words "
                      "and the person's facts do not clearly match, say so instead of stretching the section.")
    p = doc.add_paragraph()
    p.add_run("Is this fair? Anything to add or strike? ").bold = True
    p.add_run("____________________________________________________________________________")

    doc.add_heading("How the text was checked, and what is not on the shelf", level=2)
    doc.add_paragraph("The check is a comparison of two texts that India Code publishes: its database and its PDF of the same Act. It cannot find an error that both share, and it cannot tell whether either is the law today. "
                      "Run on the first five Acts it compared about 54,000 words and found nine places where the database was wrong (two doubled words, two lost apostrophes, a lost proviso, a misplaced phrase, three headings), which the loader now corrects against the PDF. "
                      f"Run on the two short Acts added afterwards ({short_words:,} words) it found one more defect, in two clauses: the piece of clause (a) copied into clauses (b) and (c) of section 7 of the Muslim Women Act (see the note under that Act's table), also corrected against the PDF; "
                      "in the Public Property Act it found only the one spelling slip noted under its table. "
                      f"Run on the Dowry Prohibition Act and the Juvenile Justice Act ({latest_words:,} words) it found: in the Juvenile Justice Act the \"Child Welfare Officer\" definition garbled (corrected, see the note under its table) and the possessive apostrophe dropped throughout (child's, children's, person's, parent's) with a few hyphens, 30 corrections against the PDF in all; the Dowry Act's section 8A is in the PDF body but missing from the PDF's printed list of sections (an amendment-inserted section the index was not updated for), which the loader is told to expect while still checking the section's text against the PDF. "
                      "Everything else it found is listed in the loader's manifest next to what the PDF reads.")
    doc.add_paragraph("What is NOT loaded: the Schedules of POCSO (the list of armed forces and security forces that section 2(c) refers to), the PMLA (the list of scheduled offences, Parts A to C, on which \"scheduled offence\" in section 2 depends), the UAPA (the organisations and individuals listed) and the SC/ST Act (the offences section 3(2)(va) refers to); "
                      "the State or Union Territory amendments inside PC Act 17A (Jammu and Kashmir and Ladakh), POCSO 42 (Arunachal Pradesh) and SC/ST 14 (Karnataka); the Rules made under any of the seven Acts. "
                      "The Muslim Women Act and the Public Property Act have no Schedules.")

    doc.add_heading("Four questions only you can answer", level=2)
    qs = ["1. Everyday words that the statute never uses. Example already in: \"anticipatory bail\" means sections 18 and 18A of the SC/ST Act (they say only \"section 438 of the Code shall not apply\"). "
          "What others should we add, for any of the seven Acts (up to ten)? Write the everyday phrase and the section(s) it means.",
          "2. Provisions the text above does not show as they stand: an amendment not yet on India Code, a provision struck down or read down by a court, an ordinance. Which, if any, in these seven Acts? And: should the Schedules (see above) be loaded, which of them first?",
          "3. The five questions people most often ask about each Act (in their own words). We will use them as the next test of the search.",
          "4. Old statutes named in the text. Section 2 of the Public Property Act refers to section 425 of the Indian Penal Code (\"mischief\") and to section 617 of the Companies Act, 1956; sections 2 and 7 of the Muslim Women Act refer to the Code of Criminal Procedure, 1973. "
          "Those statutes have since been replaced (the Indian Penal Code and the Code by the BNS and the BNSS; the Companies Act, 1956 by the Companies Act, 2013). The shelf shows each Act's words only, and the answer model is told to use only the sections it is given. "
          "Should a reader be told what such a reference now reads as, and which provision? Write the wording you would accept for each; Claude adds nothing of this kind to the text without your answer."]
    for text in qs:
        doc.add_paragraph(text)
        doc.add_paragraph("____________________________________________________________________________")
        doc.add_paragraph("____________________________________________________________________________")
    doc.add_paragraph("Please send the sheet back (a photo of a marked printout is fine). Claude records only what you confirm; an unconfirmed Act stays \"not yet read by our reviewer\".")
    doc.save(out)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--recourse", required=True, help="a Recourse checkout that has act_shelf/")
    ap.add_argument("--out", default=os.path.join(HERE, "ACT_SHELF_SHEET.docx"))
    args = ap.parse_args()
    print("wrote", build(os.path.abspath(args.recourse), args.out))
