"""Builds HEARING_PREP_SHEET.docx: page 1-2 = the sample sheet made from the SYNTHETIC test matter (invented names and facts, review_results/2026-11-19_matter_files/docs); page 3-4 = the blank worksheet we fill for a real matter.
Every page cite in the sample is checked here against the text of the source file (the quotation must stand on the page cited) and the build stops if one does not. Section words come from our library copy, the table from the BNSS First Schedule
rows (read by a program), the day counts are arithmetic on dates printed in the papers. Nothing in the sheet states a view on the merits."""
import datetime as dt
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REC = os.path.join(HERE, "..", "..", "recourse")
if not os.path.isdir(REC):
    REC = "/home/user/recourse"
sys.path.insert(0, REC)
os.environ["ACT_SHELF"] = "off"
HERE = os.path.abspath(HERE)
os.chdir(REC)                                  # the library reads its chunk files by relative path
import law_on_hand as L  # noqa: E402
import matter_files as MF  # noqa: E402
import offence_class  # noqa: E402
import retrieval  # noqa: E402
from docx_kit import *  # noqa: E402,F401

DOCS = os.path.join(HERE, "..", "review_results", "2026-11-19_matter_files", "docs")
FILES = {"CS": "chargesheet_214_2026.pdf", "RO": "remand_orders_214_2026.pdf", "BO": "bail_order_642_2026.docx", "LN": "lawyer_note.txt"}
NAMES = {"CS": "Final report (chargesheet), 6 pages", "RO": "Remand orders, 2 pages", "BO": "Bail order of 05-05-2026", "LN": "Your own working note"}
SRC = {}
for k, f in FILES.items():
    data = open(os.path.join(DOCS, f), "rb").read()
    ex = MF.extract(data, MF.sniff(data, f))
    SRC[k] = {p["loc"]: p["text"] for p in MF.passages(ex)}      # page (or paragraph block) -> text


def norm(t):
    return re.sub(r"[^a-z0-9]+", "", (t or "").lower())


def cite_ok(doc, page, quote):
    """The quotation must stand on the page cited (or, for a Word or text file, anywhere in the file)."""
    if doc in ("BO", "LN"):
        return norm(quote) in norm(" ".join(SRC[doc].values()))
    return norm(quote) in norm(SRC[doc].get(page, ""))


FAILS = []


def src(doc, page, quote):
    if not cite_ok(doc, page, quote):
        FAILS.append((doc, page, quote))
    return {"CS": f"chargesheet p. {page}", "RO": f"remand orders p. {page}", "BO": f"bail order {page}", "LN": "your note"}[doc]


def D(s):
    return dt.date(*map(int, s.split("-")[::-1]))


def f(d):
    return d.strftime("%d-%m-%Y")


ARREST, FIR, JC, TIP, FSL, REJ, CHS = (D(x) for x in ("15-03-2026", "14-03-2026", "18-03-2026", "22-03-2026", "25-03-2026", "05-05-2026", "10-06-2026"))
TODAY = D("21-11-2026")


def day(x):
    return (x - ARREST).days


# --- the charged sections, by code, from the real chargesheet
refs = MF.charged_refs([{"text": t} for t in SRC["CS"].values()])
assert refs == ["BNS 309(4)", "BNS 115(2)", "BNS 3(5)"], refs
items = {i["ref"]: i for i in L.items_for(refs)}


def sub_text(ref):
    """The sub-section's own words, word for word, taken from the library text."""
    it = items[ref]
    num, sub = it["num"], it["sub"]
    t = it["text"]
    m = re.search(r"(?m)^\(" + sub + r"\)\s", t)
    start = m.start() if m else 0
    nxt = re.search(r"(?m)^\(" + str(int(sub) + 1) + r"\)\s", t[start + 1:])
    out = t[start: start + 1 + nxt.start()] if nxt else t[start:]
    out = re.sub(r"^\[Section[^\]]*\]\n", "", out).strip()
    return " ".join(out.split())


def row_cells(ref):
    it = items[ref]
    if not it["rows"]:
        return "General provision: no First Schedule row.", "", "", ""
    r = it["rows"][0]
    one = lambda s: re.sub(r"\s+", " ", s).strip()
    summ = offence_class.summary(r)
    return one(r["punishment"]), summ.split(", ")[0].capitalize() if summ else one(r["cognizable"]), (summ.split(", ")[1].capitalize() if summ and ", " in summ else one(r["bailable"])), one(r["court"].split(". ")[0]).rstrip(".") + "."


b187 = retrieval.get_statute_section("BNSS", "187")["text"]
m3 = re.search(r"(?m)^\(3\) The Magistrate may authorise.*?(?=\n\(4\))", b187, re.S)
t187 = " ".join(m3.group(0).split())
assert "ninety days" in t187 and "released on bail" in t187
t187_whole = t187

# =============================================================================== the sheet
d = new_doc(margin_cm=1.6, base_pt=9.5)
footer(d, "Recourse · hearing preparation sheet · sample (invented documents) and worksheet")
d.add_paragraph("Hearing preparation sheet", style="Title")
box(d, ["**SAMPLE.** Every name and fact on this sheet is invented (synthetic test documents). It shows the form of the sheet, not a real case. Initials only."], fill="FDECEC", size=9, width_cm=17.8)

table(d, ["Matter", "Court and stage", "Next date"], [[
    ["**State v. R.D.** (accused no. 1)", "Rangpur P.S. Case 214 of 2026", "G.R. Case 1187 of 2026"],
    ["Chief Judicial Magistrate, Kamrup (Metro)", "Stage: after chargesheet (10-06-2026)", "Bail application 642 of 2026 rejected 05-05-2026"],
    ["**Not in the papers.**", "Please enter: ____ / ____ / ______"]]],
    [6.2, 6.6, 5.0], size=9)
para(d, f"Sheet made on {f(TODAY)} from four documents: " + "; ".join(NAMES.values()) + ".", size=8.5, color=GREY, before=3, after=2)

d.add_heading("1. What is charged", level=1)
rows = []
for ref, name in (("BNS 309(4)", "robbery"), ("BNS 115(2)", "voluntarily causing hurt"), ("BNS 3(5)", "common intention")):
    pun, cog, bail, court = row_cells(ref)
    rows.append([f"**{ref}**\n{name}".split("\n"), sub_text(ref), ["Punishment: " + pun, f"{cog}; {bail}" if cog else "", ("Triable by: " + court) if court else ""]])
    src("CS", 1, "Sections: 309(4) and 115(2) of the Bharatiya Nyaya Sanhita, 2023, read with section 3(5)")
table(d, ["Section", "The section's own words (our library copy, word for word)", "First Schedule of the BNSS (read by a program; no person has read it yet)"], rows, [2.6, 9.4, 5.8], size=8.5)
para(d, f"Charged under these sections: {src('CS', 1, 'Sections: 309(4) and 115(2) of the Bharatiya Nyaya Sanhita, 2023')}. The section the report is filed under (193 of the BNSS) is not a charge.", size=8.5, color=GREY, before=3)

d.add_heading("2. Dates and days (Day 0 = arrest, 15-03-2026)", level=1)
drows = [
    [f(FIR), "FIR registered, 21:10", src("CS", 1, "registered on 14-03-2026 at 21:10 hours"), "-1"],
    [f(ARREST), "Arrested, 06:45", src("CS", 1, "Arrested on 15-03-2026 at 06:45 hours"), "0"],
    ["16-03-2026", "Produced; police custody granted for 2 days only (3 sought); defence objection on grounds of arrest recorded", src("RO", 1, "police custody is granted for 2 days only, not 3"), "1"],
    [f(JC), "Remanded to judicial custody for 14 days, till 01-04-2026", src("RO", 2, "remanded to judicial custody for 14 days, till 01-04-2026"), str(day(JC))],
    [f(TIP), "Test identification parade", src("CS", 3, "A test identification parade was held on 22-03-2026"), str(day(TIP))],
    [f(FSL), "CCTV hard disk sent to the FSL; report awaited", src("CS", 4, "sent to the Forensic Science Laboratory, Kahilipara, on 25-03-2026"), str(day(FSL))],
    [f(REJ), "Bail application 642 of 2026 rejected; liberty to apply afresh after the chargesheet is filed", src("BO", "para 7", "I do not find it a fit case for bail at this stage"), str(day(REJ))],
    [f(CHS), "Final report (chargesheet) submitted", src("CS", 6, "This final report is submitted on 10-06-2026"), f"{day(CHS)} ({(CHS - JC).days} from 18-03-2026)"],
    [f(TODAY), "Date of this sheet", "", str(day(TODAY))],
]
table(d, ["Date", "What the papers record", "Where", "Day"], drows, [2.3, 9.2, 4.0, 2.3], size=8.5)
para(d, "", after=1)
box(d, [
    "**Detention-period arithmetic.** The text of section 187(3) of the BNSS (our library copy, word for word):",
    "“" + t187_whole + "”",
    f"**Counted from arrest (15-03-2026):** day 60 falls on {f(ARREST + dt.timedelta(days=60))}; day 90 on {f(ARREST + dt.timedelta(days=90))}.   **Counted from the first judicial custody order (18-03-2026):** day 60 falls on {f(JC + dt.timedelta(days=60))}; day 90 on {f(JC + dt.timedelta(days=90))}.   The chargesheet was submitted on {f(CHS)}.",
    "**This sheet does not say which period applies or from which date it runs.** That is for you. No order extending custody after 01-04-2026 is in these papers.",
], fill="EEF3FA", size=8.5, width_cm=17.8)

for _q in ("The chargesheet has not yet been filed and the investigation is at a crucial stage", "yet to be arrested", "The recovery memo bears the signatures of two independent witnesses",
           "The test identification parade was held within a week of the arrest", "daily-wage carpenter with an old mother to support, that he has no criminal antecedents"):
    src("BO", "order", _q)
d.add_heading("3. What changed since the last bail order (05-05-2026)", level=1)
table(d, ["The order gave these reasons", "The papers now show"], [
    ["“The chargesheet has not yet been filed and the investigation is at a crucial stage.” (para 6)", f"Chargesheet submitted {f(CHS)} ({src('CS', 6, 'This final report is submitted on 10-06-2026')}). A supplementary report is to follow for accused no. 2; the FSL report is awaited ({src('CS', 4, 'The FSL report is awaited')})."],
    ["Co-accused “yet to be arrested”; release may help him evade arrest. (para 5)", f"Accused no. 2 still not arrested; a warrant was obtained and a proclamation applied for under section 84 of the BNSS ({src('CS', 5, 'proclamation under section 84 of the BNSS')})."],
    ["Recovery memo bears the signatures of two independent witnesses. (para 4)", f"Chain recovered on 16-03-2026 on the accused's disclosure statement, in the presence of two independent witnesses ({src('CS', 3, 'in the presence of two independent witnesses')})."],
    ["Test identification parade held within a week of the arrest. (para 4)", f"Held on {f(TIP)}, day {day(TIP)} ({src('CS', 3, 'A test identification parade was held on 22-03-2026')}). Your note says the accused's photograph was published on 17-03-2026, before the parade: that is in your note only, not in the court papers ({src('LN', 1, 'photograph was published in a local newspaper on 17-03-2026')})."],
    ["Submissions for the petitioner: daily-wage carpenter, old mother to support, no antecedents. (para 2)", f"Your note says the mother's medical papers are to be attached; they are not in these papers ({src('LN', 1, 'Mother')})."],
], [7.0, 10.8], size=8.5)

d.add_heading("4. What the papers say about the alleged event", level=1)
facts = [
    ("On 14-03-2026 at about 7:40 pm the pillion rider of a red motorcycle snatched the complainant's gold chain (about 18 grams) from her neck and pushed her; she fell on the footpath.", "CS", 2, "snatched her gold chain weighing about 18 grams"),
    ("She noted part of the registration number (AS-01 and 4421). The rider wore a black helmet; the pillion rider had no helmet and wore a blue checked shirt.", "CS", 2, "pillion rider had no helmet"),
    ("16-03-2026: the chain was recovered from a steel trunk under the bed in the accused's rented room, on his disclosure statement. 17-03-2026: the motorcycle was seized from a garage at Beltola; its registered owner is accused no. 2.", "CS", 3, "gold chain was recovered from a steel trunk"),
    ("Test identification parade: the complainant identified accused no. 1 as the pillion rider.", "CS", 3, "correctly identified Accused No. 1"),
    ("A shopkeeper saw a red motorcycle with two young men speed away but “could not see their faces”. The garage owner says accused no. 2 left the motorcycle with him on the night of 14-03-2026 for a puncture repair.", "CS", 4, "could not see their faces"),
    ("Medical report: an abrasion of 3 cm on the left side of the neck and a bruise on the right elbow, “both simple in nature”.", "CS", 5, "both simple in nature"),
]
for t, dc, pg, q in facts:
    p = d.add_paragraph(style="List Bullet")
    add_runs(p, t + f" ({src(dc, pg, q)})", size=9)
    p.paragraph_format.space_after = Pt(1)

d.add_heading("5. What the papers do not show", level=1)
nots = [
    "The next hearing date, and any order extending custody after 01-04-2026.",
    f"The FSL report on the CCTV hard disk, and a certificate under section 63 of the Bharatiya Sakshya Adhiniyam, 2023 for the footage: “No certificate ... has yet been obtained” ({src('CS', 4, 'No certificate under section 63')}).",
    f"The jeweller to whom a second chain was said to have been offered was not found ({src('CS', 3, 'did not find the jeweller')}).",
    f"The grounds-of-arrest memo itself. The remand order records the defence saying the grounds were not given in writing, and the case diary showing a memo signed at 07:05 on 15-03-2026 ({src('RO', 1, 'grounds of arrest were not given to him in writing')}; {src('RO', 1, 'memo of grounds signed by the accused at 07:05 am')}).",
]
for t in nots:
    p = d.add_paragraph(style="List Bullet")
    add_runs(p, t, size=9)
    p.paragraph_format.space_after = Pt(1)

d.add_heading("6. Your own note, checked against the papers", level=1)
table(d, ["Point in your note", "In the papers?"], [
    ["1. Chargesheet filed on 10-06-2026", f"Yes ({src('CS', 6, 'This final report is submitted on 10-06-2026')})"],
    ["2. The FSL report on the CCTV is still awaited", f"Yes ({src('CS', 4, 'The FSL report is awaited')})"],
    ["3. TIP held seven days after arrest; photograph published on 17-03-2026", f"TIP: yes, day {day(TIP)}. The newspaper photograph: not in the court papers."],
    ["4. Mother's medical papers to be attached", "Not in the papers."],
], [9.0, 8.8], size=8.5)

d.add_heading("7. Authorities", level=1)
para(d, "Not on this sheet. Ask for them. They are kept off so that the sheet stays short and cheap. Each case shows where it stands on our register of overruled cases, or says plainly that we have not checked it.", size=9)

d.add_heading("How this sheet was made, and what it is not", level=1)
box(d, [
    "**Read from your documents** (pages as printed in them). **Section words** are our library's copy, shown word for word. **The table** is read by a program from the First Schedule of the BNSS; no person has read it. **Dates and day numbers** are arithmetic on dates printed in the papers. In a real sheet a person checks every date and page against the original before it is sent; in this sample a program checked every page cite against the text of the invented documents.",
    "This is not legal advice and not a view on the merits. It does not say which detention period applies, whether bail should be granted, or what to argue. **Recourse can be wrong: check against the original.** Our copy of the law has known gaps in other sections, and no hallucination rate has been measured.",
], fill="F3F4F6", size=8.5, width_cm=17.8)

d.add_heading("Three questions for you (please be blunt)", level=2)
table(d, ["Question", "Your answer"], [
    ["1. What is wrong, or missing? What would you cross out?", "\n\n"],
    ["2. Would you have used this before your hearing? (yes / no / only if ...)", ""],
    ["3. Who prepares something like this for you today, and how long does it take?", "\n"],
], [9.0, 8.8], size=9)

# =============================================================================== the blank worksheet
d.add_page_break()
d.add_paragraph("Worksheet: one per real matter (internal)", style="Title")
box(d, [
    "**Who fills what.** Sections 1 and the law text: by program (charged sections from the 'Sections:' line, text from our library, the Schedule table). Dates, facts and gaps: read from the papers by a person or by Claude, and **every date and page checked against the original by a second person before the sheet goes out**. Day numbers: arithmetic only. No view on the merits, no choice of detention period, no authorities unless asked.",
    "**Redaction.** Initials only; no addresses, phone, Aadhaar, bank or vehicle numbers. Staging only; delete the papers after the test. Written consent first.",
], fill="FFF4E5", size=9, width_cm=17.8)
table(d, ["Matter", "Court and stage", "Next date"], [[["Accused: ______ (initials)", "Police station and case no.: ______", "Other case no.: ______"], ["Court: ______", "Stage: FIR / arrest / remand / bail / chargesheet / trial"], "Enter: ____ / ____ / ______"]], [6.2, 6.6, 5.0], size=9)
para(d, "Sheet made on ___ from these documents: ______________________________________", size=8.5, color=GREY, before=3)
for title, hint in (
    ("1. What is charged", "Section | its own words (library) | Schedule row. Source of the sections: the 'Sections:' line, page __."),
    ("2. Dates and days", "Date | what the papers record | where | day number from arrest. Add the 187(3) box (text and the four arithmetic dates). Note any custody order that is missing."),
    ("3. What changed since the last order", "Left: the order's reasons with para numbers. Right: what the papers now show, with pages. No argument."),
    ("4. What the papers say about the alleged event", "Six to eight lines, each with a page. Quote words that matter."),
    ("5. What the papers do not show", "Hearing date, FSL, certificates, memos, orders after the last custody date, anything the note or the order mentions that is not in the file."),
    ("6. The lawyer's own note, checked", "Each point: in the papers (page) / not in the papers."),
    ("7. Authorities", "Only if asked. Library cases with their register status; wider-search cases marked 'not independently verified'."),
):
    d.add_heading(title, level=2)
    para(d, hint, size=8.5, color=GREY, after=2)
    table(d, [" ", " ", " "], [["", "", ""], ["", "", ""], ["", "", ""]], [5.0, 8.0, 4.8], size=9, head_fill="FFFFFF")

d.save(os.path.join(HERE, "HEARING_PREP_SHEET.docx"))
if FAILS:
    print("CITATION CHECK FAILED:")
    for x in FAILS:
        print("  ", x)
    sys.exit(1)
print("saved; every page cite in the sample was found on the page cited")
