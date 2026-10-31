"""
build_evidence_sheet.py -- writes acts/EVIDENCE_BSA_SHEET.docx, the sheet for Mr. Advocate for the Indian Evidence Act, 1872 and the Bharatiya Sakshya Adhiniyam, 2023 on the Act shelf (2026-10-31, FOLLOW_UPS 2ct).

Contents: (1) what the two texts are and how they were checked, in plain words; (2) sections of each Act in full as Recourse hands them to the answer model, to be read against the Gazette; (3) the section map (Evidence Act -> Adhiniyam):
the pairs the owner named, every pair the program is unsure of, and a sample of the rest, each with a place for his tick; (4) the two words the program suspects are misprints in the PDF; (5) questions only a lawyer can answer.
Nothing is recorded as confirmed by anyone; Claude records only what Mr. Advocate answers.
Run: python acts/build_evidence_sheet.py --recourse <Recourse checkout> [--out acts/EVIDENCE_BSA_SHEET.docx]
"""
import argparse
import datetime
import json
import os
import sys

from docx import Document
from docx.shared import Pt

HERE = os.path.dirname(os.path.abspath(__file__))
EA_SECTIONS = [("3", "definitions: 'fact', 'relevant', 'evidence', 'proved' (the PDF's long section)"), ("8", "motive, preparation, conduct"), ("24", "confession caused by inducement, threat or promise"), ("25", "confession to a police officer"),
               ("26", "confession in police custody"), ("27", "how much of information received from the accused may be proved"), ("32", "statements of persons who cannot be called (dying declaration)"),
               ("45", "opinions of experts"), ("65B", "admissibility of electronic records"), ("101", "burden of proof"), ("105", "burden of proving exceptions"), ("106", "burden of proving a fact especially within knowledge"),
               ("113B", "presumption as to dowry death"), ("114", "court may presume certain facts"), ("133", "accomplice"), ("145", "cross-examination as to previous statements")]
BSA_SECTIONS = [("2", "definitions"), ("6", "motive, preparation, conduct"), ("22", "confession caused by inducement"), ("23", "confession to a police officer; the proviso on information leading to discovery"), ("26", "statements of persons who cannot be called"),
                ("39", "opinions of experts"), ("63", "admissibility of electronic records"), ("104", "burden of proof"), ("108", "burden of proving exceptions"), ("109", "burden of proving a fact especially within knowledge"),
                ("118", "presumption as to dowry death"), ("119", "court may presume certain facts"), ("138", "accomplice"), ("148", "cross-examination as to previous statements")]
NAMED_PAIRS = ["106", "27", "25", "24", "26", "65B", "114", "113B", "32", "45", "145"]


def build(recourse, out):
    shelf = os.path.join(recourse, "act_shelf")
    ea = {c["section_number"]: c for c in json.load(open(os.path.join(shelf, "evidence_act_1872.json"), encoding="utf-8"))}
    bsa = {c["section_number"]: c for c in json.load(open(os.path.join(shelf, "bsa_2023.json"), encoding="utf-8"))}
    mp = json.load(open(os.path.join(shelf, "section_map_ea_bsa.json"), encoding="utf-8"))
    man = {a["key"]: a for a in json.load(open(os.path.join(shelf, "manifest.json"), encoding="utf-8"))["acts"]}
    pairs = {p["ea"]: p for p in mp["pairs"]}
    d = Document()
    st = d.styles["Normal"]
    st.font.name, st.font.size = "Calibri", Pt(10.5)
    d.add_heading("Evidence Act, 1872 and Bharatiya Sakshya Adhiniyam, 2023: sheet for Mr. Advocate", 1)
    d.add_paragraph(f"Prepared {datetime.date.today().isoformat()} by Claude. Nothing on this sheet is confirmed until you answer it. Reply by section number; a tick, a cross or a corrected wording is enough.")
    d.add_heading("1. What the two texts are", 2)
    d.add_paragraph("Bharatiya Sakshya Adhiniyam, 2023 (170 sections): loaded from India Code's database and compared word by word, in order, both ways, against India Code's own PDF of the Act. Five faults of the database were found and "
                    "repaired from the PDF: s.2 lost an apostrophe ('Bs death' for 'B's death'); s.45 and s.121 headed a single illustration 'Illustrations'; s.94 LACKED illustration (c) (the bill of exchange drawn in a set of three); "
                    "s.119 printed illustration (a) twice. Status: machine_checked (a program compared; nobody has read it).")
    d.add_paragraph(f"Indian Evidence Act, 1872 (185 sections, repealed from 1 July 2024): India Code keeps this repealed Act only as one PDF (the archive copy, A1872-1.pdf, {man['evidence_act_1872'].get('pdf_as_on')}); it has no section records, so there is ONLY ONE source. "
                    "The text was cut into sections by program: the sections equal the PDF's own arrangement of sections in number and order, and a second PDF reader (Poppler) agrees with the first on every word. That shows the cutting is complete and in order; "
                    "it does NOT show that the PDF's own text is free of misprints. Status: machine_extracted, weaker than machine_checked. State amendments (Arunachal Pradesh at 53A and 146, Chhattisgarh at 114A) are set aside, not loaded.")
    d.add_paragraph("Not loaded for either Act: the Schedule of the Evidence Act (a list of repealed enactments) and any Rules.")
    d.add_heading("2. Sections to read against the Gazette", 2)
    d.add_paragraph("Each is printed exactly as Recourse hands it to the answer model. Please say whether it is the text of the Act as it stood at the date shown on the PDF.")
    for title, secs, src in (("Evidence Act, 1872", EA_SECTIONS, ea), ("Bharatiya Sakshya Adhiniyam, 2023", BSA_SECTIONS, bsa)):
        d.add_heading(title, 3)
        t = d.add_table(rows=1, cols=4)
        t.style = "Table Grid"
        for i, h in enumerate(("Section", "Why it is here", "Text as handed over", "Your answer")):
            t.rows[0].cells[i].text = h
        for num, why in secs:
            c = src.get(num)
            if not c:
                continue
            r = t.add_row().cells
            r[0].text, r[1].text, r[2].text, r[3].text = num, why, c["text"], ""
    d.add_heading("3. The section map: which section of the Adhiniyam carries which section of the Evidence Act", 2)
    d.add_paragraph("Made by a program from the shared wording of the two Acts, NOT from a table in the Gazette. 'Share' is the part of the Evidence Act section's three-word runs that the Adhiniyam paragraph also holds. A high share means the words "
                    "are alike, not that the law is the same. Please confirm or correct the Adhiniyam section (and sub-section or proviso) for each pair.")
    rows = [pairs[n] for n in NAMED_PAIRS if n in pairs]
    rows += [p for p in mp["pairs"] if p["kind"] in ("partly_carried", "split_or_merged", "no_counterpart_found") and p["ea"] not in NAMED_PAIRS]
    t = d.add_table(rows=1, cols=5)
    t.style = "Table Grid"
    for i, h in enumerate(("Evidence Act", "Title", "Program's pairing", "Kind", "Your answer")):
        t.rows[0].cells[i].text = h
    for p in rows:
        r = t.add_row().cells
        where = "; ".join(f"s.{b['section']}{b.get('bsa_subsection', '')} ({b['share']:.0%})" + (" proviso" if b.get("bsa_part", "").lower().startswith("provided") else "") for b in p["bsa"][:3]) or "none found"
        r[0].text, r[1].text, r[2].text, r[3].text, r[4].text = "s." + p["ea"], p["ea_title"], where, p["kind"].replace("_", " "), ""
    d.add_paragraph(f"The map has {len(mp['pairs'])} pairs; the other {len(mp['pairs']) - len(rows)} have nearly the same wording or reworded text and are not listed. Ask Claude for the full table if you want to see them.")
    d.add_heading("4. Two words the program suspects are misprints in the PDF", 2)
    d.add_paragraph("These are kept as the PDF prints them. If you confirm a misprint, Claude records a correction with your name; it does not change them by itself.")
    d.add_paragraph("s.27: the PDF reads 'discovered inconsequence of information received' (the Adhiniyam, s.23(2) proviso, reads 'in consequence').", style="List Bullet")
    d.add_paragraph("s.6, illustration (a): the PDF reads 'goals are broken open' (the usual printing is 'gaols').", style="List Bullet")
    d.add_heading("5. Questions only a lawyer can answer", 2)
    for q in ("Is the PDF's text of the Evidence Act the Act as amended up to its repeal? (the program cannot tell which amendments the archive copy includes.)",
              "Are the pairings in the table in section 3 the ones a practitioner would use when a judgment before July 2024 cites the Evidence Act? Which are wrong?",
              "The Adhiniyam repeals and saves the old Act: which section says what happens to a trial begun before 1 July 2024? (the program does not hold that section's effect; the answer model is told not to say which Act governs.)",
              "Are there sections where the Adhiniyam changed the law, not just the number, that the answer should flag? (section 63 on electronic records is the one the program knows of.)"):
        d.add_paragraph(q, style="List Number")
    d.save(out)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--recourse", required=True)
    ap.add_argument("--out", default=os.path.join(HERE, "EVIDENCE_BSA_SHEET.docx"))
    a = ap.parse_args()
    print("wrote", build(a.recourse, a.out))
