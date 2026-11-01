"""
build_ni_it_sheet.py -- writes acts/NI_IT_SHEET.docx, the sheet for Mr. Advocate for the whole Negotiable Instruments Act, 1881 and Information Technology Act, 2000 on the Act shelf (2026-10-31, FOLLOW_UPS 2cv):
what was repaired from India Code's PDF (two substantive repairs), the readings where the database and the PDF disagree and neither is certain, a set of sections in full to read against the Gazette, and the finding about the
library's own IT Act sections 72 and 72A. Nothing is recorded as confirmed by anyone. Run: python acts/build_ni_it_sheet.py --recourse <Recourse checkout> [--out acts/NI_IT_SHEET.docx]
"""
import argparse
import datetime
import json
import os

from docx import Document
from docx.shared import Pt

HERE = os.path.dirname(os.path.abspath(__file__))
NI = [("6", "'cheque'"), ("118", "presumptions as to negotiable instruments"), ("138", "dishonour of cheque (the main offence)"), ("139", "presumption in favour of the holder"), ("141", "offences by companies"),
      ("142", "cognizance"), ("142A", "jurisdiction"), ("143", "summary trial"), ("143A", "interim compensation"), ("145", "evidence on affidavit"), ("147", "offences compoundable"), ("148", "deposit on appeal")]
IT = [("2", "definitions (clause (ta) was repaired)"), ("43", "compensation for damage to computers"), ("66", "computer related offences"), ("66B", "receiving stolen computer resource"), ("66C", "identity theft"),
      ("66D", "cheating by personation"), ("66E", "privacy"), ("66A", "omitted: struck down in 2015, omitted in 2023"), ("67", "obscene material"), ("67A", "sexually explicit material"), ("67B", "child sexual abuse material"),
      ("68", "Controller's directions (sub-section (2) was repaired)"), ("69", "interception and monitoring"), ("72", "breach of confidentiality (the library's copy is out of date)"), ("72A", "disclosure in breach of contract (the library's copy is out of date)"),
      ("79", "intermediaries"), ("84", "protection of action in good faith")]


def build(recourse, out):
    sh = os.path.join(recourse, "act_shelf")
    ni = {c["section_number"]: c for c in json.load(open(os.path.join(sh, "ni_act_1881.json"), encoding="utf-8"))}
    it = {c["section_number"]: c for c in json.load(open(os.path.join(sh, "it_act_2000.json"), encoding="utf-8"))}
    d = Document()
    d.styles["Normal"].font.name, d.styles["Normal"].font.size = "Calibri", Pt(10.5)
    d.add_heading("Negotiable Instruments Act, 1881 and Information Technology Act, 2000: sheet for Mr. Advocate", 1)
    d.add_paragraph(f"Prepared {datetime.date.today().isoformat()} by Claude. Nothing here is confirmed until you answer it. Reply by section number.")
    d.add_heading("1. Two repairs that change the law as the shelf states it", 2)
    d.add_paragraph("IT Act s.68(2): India Code's database still carries the OLD sub-section (imprisonment up to two years or fine up to one lakh rupees or both). India Code's PDF of 27 June 2025 has 'liable to penalty which may extend to twenty-five lakh rupees' "
                    "(Jan Vishwas (Amendment of Provisions) Act, 2023). The shelf uses the PDF. Please confirm.", style="List Bullet")
    d.add_paragraph("IT Act s.66A: the database keeps the whole struck-down text. The shelf keeps only the PDF's line: omitted by the Jan Vishwas Act, 2023 (w.e.f. 30-11-2023), with India Code's footnote that the Supreme Court struck it down on 24 March 2015 (Shreya Singhal). Please confirm.", style="List Bullet")
    d.add_heading("2. A finding about the library's own copy of the IT Act", 2)
    d.add_paragraph("The IT Act sections the library already held (10 of them) were compared with the checked text. Sections 72 and 72A in the library are the OLD wording ('punished with imprisonment ... two years / three years'). The PDF has 'liable to penalty which may extend to five lakh rupees' (s.72) and "
                    "'twenty-five lakh rupees' (s.72A), substituted by Act 18 of 2023 w.e.f. 30-11-2023. Please confirm which is the law today, so the library's two sections can be corrected (not done yet).")
    d.add_heading("3. Readings where the database and the PDF disagree and neither is certain", 2)
    for t in ("IT s.66B: 'dishonestly receive or retains' (database) against 'dishonestly received or retains' (PDF). The usual printing is 'receives'.", "IT s.66D: 'cheats by personation' (database) against 'cheats by personating' (PDF).",
              "IT s.84: 'adjudicating officer' (database) against 'adjudicating officers' (PDF).", "NI s.118(e): 'appear thereon' (database) against 'appear then on' (PDF).",
              "IT s.66E: 'pubic area' (database, following a Gazette corrigendum in India Code's footnote) against 'public area' (PDF). The shelf keeps 'pubic'."):
        d.add_paragraph(t, style="List Bullet")
    d.add_heading("4. What the PDF's contents list could not confirm", 2)
    d.add_paragraph("NI Act: sections 70 and 104A are in the Act's text but not in the PDF's printed arrangement of sections; their text was still compared with the PDF's running text. IT Act: the titles of ss.16, 72A and 82 in the printed arrangement are out of date; the PDF's running text was used.")
    d.add_heading("5. Sections to read against the Gazette", 2)
    for title, secs, src in (("Negotiable Instruments Act, 1881", NI, ni), ("Information Technology Act, 2000", IT, it)):
        d.add_heading(title, 3)
        t = d.add_table(rows=1, cols=4)
        t.style = "Table Grid"
        for i, h in enumerate(("Section", "Why", "Text as handed over", "Your answer")):
            t.rows[0].cells[i].text = h
        for num, why in secs:
            c = src.get(num)
            if c:
                r = t.add_row().cells
                r[0].text, r[1].text, r[2].text = num, why, c["text"][:3500]
    d.save(out)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--recourse", required=True)
    ap.add_argument("--out", default=os.path.join(HERE, "NI_IT_SHEET.docx"))
    a = ap.parse_args()
    print("wrote", build(a.recourse, a.out))
