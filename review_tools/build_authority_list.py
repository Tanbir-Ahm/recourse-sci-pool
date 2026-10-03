#!/usr/bin/env python3
"""Builds Authority_Check_List.xlsx, the workbook for the two checks an AI marking passages cannot do reliably:
(1) is each listed case still good law, and (2) what does a research tool show for the 12 questions, compared with our results.

Case names, numbers and years were copied by hand from the first lines of our own crawl text and checked against it (see the data below);
the order of "our results" per question comes from the pool (each judgment's best passage in the search called 'A today').

  python review_tools/build_authority_list.py --out DIR [--pool review_data/pool_all.json]
"""
import argparse
import math
import os
import sys

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.workbook.properties import CalcProperties
from openpyxl.worksheet.datavalidation import DataValidation

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import review_common as rc

D, C = "decision date", "case-number year (decision may be later)"

# id: (case name as in our text, case number as printed, year, year basis, topic from the first lines of our copy)
J = {
 36322: ("Rangappa v. Sri Mohan", "Criminal Appeal 1020 of 2010", 2010, C, "Cheque dishonour (s.138 NI Act); the presumption in s.139"),
 25607: ("Prabha Shankar Dubey v. State of Madhya Pradesh", "Appeals (crl.) 634 and 1122 of 2003", 2003, D, "NDPS Act s.18; s.50 (right to be searched before a Gazetted Officer or Magistrate)"),
 37060: ("Vijaysinh Chandubha Jadeja v. State of Gujarat", "Criminal Appeal 943 of 2005 (with 974 of 2003, 1809 of 2009)", 2005, C, "NDPS Act s.50: must the suspect be told of the right to be searched before a Gazetted Officer or Magistrate"),
 20273: ("Pankaj Mehra & Anr. v. State of Maharashtra & Ors.", "Appeal (crl.) 11 of 1999", 2000, D, "Cheque dishonour (s.138 NI Act); company with a winding-up petition pending"),
 20478: ("M. Krishnan v. Vijay Singh & Anr.", "Appeal (crl.) 1028 of 2001", 2001, D, "Complaint under IPC ss.193, 196, 197, 406, 465, 468, 471; issue of process"),
 20481: ("Kamaladevi Agarwal v. State of West Bengal & Ors.", "Appeal (crl.) 1059 of 2001", 2001, D, "High Court quashing a complaint (IPC ss.465, 467, 468, 471, 120-B)"),
 41736: ("Arnesh Kumar v. State of Bihar & Anr.", "Criminal Appeal 1277 of 2014", 2014, C, "s.498-A IPC and s.4 Dowry Prohibition Act; arrest"),
 35436: ("Md. Ibrahim & Ors. v. State of Bihar & Anr.", "Criminal Appeal 1695 of 2009", 2009, C, "Criminal complaint arising from a land dispute"),
 18713: ("Mahesh Chand v. B. Janardhan Reddy & Anr.", "Appeal (crl.) 1276 of 2002", 2002, D, "FIR alleging a forged sale deed and trespass on land"),
 31821: ("Noor Aga v. State of Punjab & Anr.", "Criminal Appeal 1034 of 2008", 2008, C, "NDPS Act: constitutional validity and burden of proof"),
 40613: ("C. Keshavamurthy v. H.K. Abdul Zabbar", "Criminal Appeal 1026 of 2013", 2013, C, "Cheque dishonour (four bounced cheques)"),
 17023: ("Ram Lal & Anr. v. State of Jammu & Kashmir", "(number not shown in our copy)", 1999, D, "Compounding of offences under IPC ss.326 and 324 after a compromise"),
 41778: ("Yogendra Yadav & Ors. v. State of Jharkhand & Anr.", "Criminal Appeal 1205 of 2014", 2014, C, "IPC ss.341, 323, 324, 504, 307 read with s.34; compromise"),
 42608: ("Mohan Lal v. State of Rajasthan", "Criminal Appeal 1393 of 2010", 2010, C, "Conviction under NDPS Act s.18"),
 42630: ("Nanda Gopalan v. State of Kerala", "Criminal Appeal 714 of 2015", 2015, C, "IPC ss.324 and 326; compromise after conviction"),
 42638: ("T. Vasanthakumar v. Vijayakumari", "Criminal Appeal 728 of 2015", 2015, C, "Cheque complaint; High Court acquittal in revision"),
 32693: ("Ishwar Singh v. State of Madhya Pradesh", "Criminal Appeal 1626 of 2008", 2008, C, "Appeal against conviction and sentence (offence not shown in the first lines)"),
 38847: ("Shiji @ Pappu & Ors. v. Radhika & Anr.", "Criminal Appeal 2094 of 2011", 2011, C, "Quashing an FIR under s.482 CrPC (IPC ss.354, 394)"),
 18068: ("K.N. Beena v. Muniyappan & Anr.", "Appeal (crl.) 1066 of 2001", 2001, D, "Cheque dishonour (s.138 NI Act)"),
 18070: ("Header reads: Commissioner of Income Tax, Mumbai (the body text is Kamaladevi Agarwal)", "Appeal (civil) 4126-50 of 2000 (as printed in the header)", 2001, D, "Header says income-tax civil appeal; body is a criminal complaint-quashing judgment"),
 29890: ("Hasi Mohan Barman & Anr. v. State of Assam & Anr.", "Appeal (crl.) 1534 of 2007", 2007, D, "Appeal from Gauhati High Court; sentence modified"),
 39772: ("M/s Laxmi Dyechem v. State of Gujarat & Ors.", "Criminal Appeals 1870-1909 of 2012", 2012, C, "Cheque dishonour; High Court quashed 40 complaints"),
 39838: ("Paramjeet Batra v. State of Uttarakhand & Ors.", "Criminal Appeal 2069 of 2012", 2012, C, "Petition under s.482 CrPC to quash proceedings (order)"),
 39909: ("Ashok Kumar Sharma v. State of Rajasthan", "Criminal Appeal 817 of 2008", 2008, C, "NDPS Act s.50: must the accused be told of the right to be searched before a Gazetted Officer or Magistrate"),
 38171: ("Joseph Salvaraj A. v. State of Gujarat & Ors.", "Criminal Appeal 1251 of 2011", 2011, C, "FIR under IPC ss.406, 420, 506(1); civil or criminal"),
 279:   ("Sri C. I. Emden v. State of U.P.", "(1960 AIR 548; 1960 SCR (2) 592)", 1959, D, "Prevention of Corruption: receipt of gratification and the statutory presumption"),
 43679: ("Dr. Rini Johar & Anr. v. State of M.P. & Ors.", "Writ Petition (Criminal) 30 of 2015", 2015, C, "Writ petition by two petitioners against the State (topic not clear from the first lines)"),
 39742: ("Suresh & Ors. v. State of Madhya Pradesh", "Criminal Appeal 300 of 2009", 2009, C, "Conviction by the Special Judge, NDPS Act, Guna"),
 30317: ("State of Punjab v. Baldev Singh", "Appeal (crl.) 396 of 1990", 1999, D, "NDPS Act s.50; five-judge bench named in the bench line"),
 33270: ("Puttaswamy v. State of Karnataka & Another", "Criminal Appeal 2015 of 2008", 2008, C, "IPC ss.279 and 304-A: death by rash and negligent driving"),
 39112: ("Lalita Kumari v. Government of U.P. & Others (with connected matters)", "Writ Petition (Criminal) 68 of 2008", 2012, D, "Registration of an FIR; this is the reference order dated 27 Feb 2012"),
 40960: ("Lalita Kumari v. Govt. of U.P. & Ors. (with connected matters)", "Writ Petition (Criminal) 68 of 2008", 2013, D, "Registration of an FIR; five-judge decision dated 12 Nov 2013"),
 39579: ("Gian Singh v. State of Punjab & Another (with connected petitions)", "SLP (Crl.) 8989 of 2010", 2010, C, "Compromise and quashing of criminal proceedings"),
}
# judgments that appear only in the 'Our results' sheet
EXTRA = {
 17272: ("Ahmed v. State of Gujarat", "(number not shown)", 2000, D), 17683: ("Prahlad Singh Bhati v. N.C.T., Delhi & Anr.", "Appeal (crl.) 324 of 2001", 2001, D),
 18117: ("M/s M.M.T.C. Ltd. & Anr. v. M/s Medchl Chemicals & Pharma P. Ltd. & Anr.", "Appeals (crl.) 1173-1174 of 2001", 2001, D),
 26940: ("State of Rajasthan v. Ram Chandra", "Appeal (crl.) 541 of 2005", 2005, D), 27807: ("M.S. Narayana Menon @ Mani v. State of Kerala & Anr.", "Appeal (crl.) 1012 of 1999", 2006, D),
 28663: ("Kamala S v. Vidyadharan M.J. & Anr.", "Appeal (crl.) 233 of 2007", 2007, D), 29599: ("Khursheed & Anr. v. State of U.P.", "Appeal (crl.) 1302 of 2007", 2007, D),
 29628: ("Inder Mohan Goswami & Anr. v. State of Uttaranchal & Ors.", "Appeal (crl.) 1392 of 2007", 2007, D), 29646: ("K. Prakashan v. P.K. Surenderan", "Appeal (crl.) 1410 of 2007", 2007, D),
 30108: ("Krishna Janardhan Bhat v. Dattatraya G. Hegde", "Appeal (crl.) 518 of 2006", 2008, D), 31325: ("Noorjahan v. State Rep. by D.S.P.", "Appeal (crl.) 706 of 2008", 2008, D),
 31628: ("V.R. Dalal & Ors. v. Yougendra Naranji Thakkar & Anr.", "Criminal Appeal 925 of 2008", 2008, C), 33341: ("M/s Kumar Exports v. M/s Sharma Carpets", "Criminal Appeal 2045 of 2008", 2008, C),
 33475: ("Hamidhbai Azambhai Malik v. State of Gujarat", "Criminal Appeal 164 of 2002", 2002, C), 34509: ("Sh. Vishnu Dutt Sharma v. Smt. Daya Sapra", "CIVIL Appeal 3238 of 2009", 2009, C),
 34973: ("Shakson Belthissor v. State of Kerala & Anr.", "Criminal Appeal 249 of 2004", 2004, C), 37743: ("Bhola Singh v. State of Punjab", "Criminal Appeal 448 of 2006", 2006, C),
 38214: ("State of Delhi v. Ram Avtar @ Rama", "Criminal Appeal 1101 of 2004", 2004, C), 38851: ("Gulab Das & Ors. v. State of M.P.", "Criminal Appeal 2126 of 2011", 2011, C),
 39168: ("Ushaben v. Kishorbhai Chunilal Talpada & Ors.", "Criminal Appeal 562 of 2012", 2012, C), 40209: ("M/s GHCL Employees Stock Option Trust v. M/s India Infoline Ltd.", "Criminal Appeal 488 of 2013", 2013, C),
 40376: ("Raj Kumar Singh @ Raju @ Batya v. State of Rajasthan", "Criminal Appeals 931-932 of 2009", 2009, C), 40439: ("Sujit Biswas v. State of Assam", "Criminal Appeal 1323 of 2011", 2011, C),
 40594: ("Gian Chand & Ors. v. State of Haryana", "Criminal Appeal 2302 of 2010", 2010, C), 40907: ("Gurjant Singh @ Janta v. State of Punjab", "Criminal Appeal 1868 of 2013", 2013, C),
 41024: ("State of Rajasthan v. Shambhu Kewat & Another", "Criminal Appeal 2018 of 2013", 2013, C), 41152: ("Km. Hema Mishra v. State of U.P. & Others", "Criminal Appeal 146 of 2014", 2014, C),
 41708: ("State of Rajasthan v. Thakur Singh", "Criminal Appeal 357 of 2005", 2005, C), 41903: ("State of Madhya Pradesh v. Deepak & Ors.", "Criminal Appeal 1985 of 2014", 2014, C),
 42081: ("K. Subramani v. K. Damodara Naidu", "Criminal Appeal 2402 of 2014", 2014, C), 42248: ("Sher Singh @ Partapa v. State of Haryana", "Criminal Appeal 1592 of 2011", 2011, C),
 42480: ("Ramdev Food Products Private Limited v. State of Gujarat", "Criminal Appeal 600 of 2007", 2007, C), 42499: ("Vesa Holdings P. Ltd. & Anr. v. State of Kerala & Ors.", "Criminal Appeal 2341 of 2011", 2011, C),
 42679: ("Mohar Singh v. State of Rajasthan", "Criminal Appeal 758 of 2015", 2015, C), 43105: ("Baldev Singh v. State of Haryana", "Criminal Appeal 167 of 2006", 2006, C),
 43732: ("Sekhar Suman Verma v. The Superintendent of N.C.B. & Anr.", "Criminal Appeal 317 of 2006", 2006, C), 44457: ("Jairam S/o Nathu Salunke v. State of Maharashtra & Anr.", "Criminal Appeal 985 of 2016", 2016, C),
 44679: ("K. Sitaram & Anr. v. CFL Capital Financial Service Ltd. & Anr.", "Criminal Appeal 2285 of 2011", 2011, C), 44724: ("Binoy Kumar Mishra v. State of Jharkhand & Another (with connected appeals)", "Criminal Appeal 246 of 2017", 2017, C),
}
ALLNAMES = {k: v[:4] for k, v in J.items()}; ALLNAMES.update(EXTRA)
LAND = {41736: "Q01, Q02", 35436: "Q03, Q04", 42630: "Q05, Q06", 36322: "Q07, Q08", 37060: "Q09, Q10", 31821: "Q11, Q12"}
PRIORITY_A = set(LAND) | {25607, 30317, 18070, 39112, 40960}
SPECIFIC = {
 25607: "Our copy of Jadeja (id 37060) says the idea of 'substantial compliance' with s.50 NDPS, used in this case (cited there as (2004) 2 SCC 56) and in Joseph Fernandez, is not borne out by the section or by Baldev Singh. Check how your tool shows this: overruled, partly overruled, or doubted? Which case does it name?",
 30317: "Cited in Jadeja as (1999) 6 SCC 172. Our index holds this decision twice (ids 30317 and 16795; the text is 96% identical). Check it is one judgment, its bench strength, and its status.",
 37060: "Check whether any later bench has doubted, limited or referred it to a larger bench. Also check its bench strength.",
 18070: "The header says 'Commissioner of Income Tax, Mumbai, Appeal (civil) 4126-50 of 2000', but the body text is the same as Kamaladevi Agarwal (id 20481, 87% identical). Search the tool for both names and tell us what each really is. Is there a Supreme Court judgment of 17 Oct 2001 with this tax title?",
 20481: "Our index also holds this body text under a tax-case header (id 18070). Check status and the citation.",
 39112: "Same case name as id 40960, but our copy of this one is dated 27 Feb 2012 (a three-judge reference order). The 12 Nov 2013 five-judge decision is id 40960. Check how the tool treats the two: is the 2012 order shown as superseded?",
 40960: "Five-judge decision dated 12 Nov 2013. Check its status and whether the tool shows the 2012 order (id 39112) as an earlier stage of the same case.",
 279:   "Old authority (1959). Check how it has been treated since: followed, distinguished, or doubted?",
 41736: "Landmark for the arrest questions. Check status and whether later benches have added to or limited it.",
 35436: "Landmark for the civil-dispute-as-crime questions. Check status.",
 42630: "Landmark for the compromise questions. Check status, and whether a later larger bench changed the law on compounding or quashing after a compromise.",
 36322: "Landmark for the s.139 presumption questions. Check status and bench strength.",
 31821: "Landmark for the NDPS burden-of-proof questions. Check status.",
 39579: "Appears in our results for the compromise questions. Check status and bench strength.",
}
DEFAULT_CHECK = "Is this still good law? Has a later Supreme Court bench overruled, doubted or limited it?"
STATUS = ["Good law", "Overruled", "Partly overruled", "Doubted", "Distinguished", "Not found", "Unsure"]
BENCH = ["Two judges", "Three judges", "Five or more (Constitution Bench)", "Unsure"]
HOW = ["Tool's own flag", "I read the later judgment", "Both", "Not confirmed"]
SRC = ["LawCentral AI", "Manupatra", "SCC Online", "Indian Kanoon", "Other"]
WHO = ["Non-lawyer using a tool", "Lawyer"]
VERDICT = ["Ours better", "Similar", "Ours worse", "Can't tell"]
PLAIN = ["Yes", "Partly", "No", "Not offered"]

F = lambda **k: Font(name="Arial", size=k.pop("size", 10), **k)
thin = Side(style="thin", color="BFBFBF"); box = Border(left=thin, right=thin, top=thin, bottom=thin)
HEAD = PatternFill("solid", fgColor="1F3864"); QROW = PatternFill("solid", fgColor="D9E2F3"); INPUT = PatternFill("solid", fgColor="FFF2CC"); GREY = PatternFill("solid", fgColor="F2F2F2"); FLAGF = PatternFill("solid", fgColor="FCE4D6")
wrap = Alignment(wrap_text=True, vertical="top"); ctr = Alignment(horizontal="center", vertical="top", wrap_text=True)


def header(ws, cols, height=44):
    for i, (name, w) in enumerate(cols, 1):
        c = ws.cell(1, i, name); c.font = F(bold=True, color="FFFFFF"); c.fill = HEAD; c.border = box
        c.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
        ws.column_dimensions[ws.cell(1, i).column_letter].width = w
    ws.row_dimensions[1].height = height


def dv_list(ws, items, rng, title, msg=None):
    dv = DataValidation(type="list", formula1='"' + ",".join(items) + '"', allow_blank=True, showErrorMessage=True, errorTitle="Pick from the list",
                        error="Please choose one of: " + ", ".join(items), showInputMessage=bool(msg), promptTitle=title, prompt=msg or "")
    ws.add_data_validation(dv); dv.add(rng)


def compute_tops(pool):
    """Per question: the distinct judgments behind the 'A today' top-10 passages, in the order of their best passage."""
    tops = {}
    for q in pool:
        rows = sorted((r for r in q["rows"] if r["variants"].get("A today") is not None), key=lambda r: r["variants"]["A today"])
        order = []
        for r in rows:
            if r["doc"] not in order:
                order.append(r["doc"])
        tops[q["qid"]] = order
    return tops


def build_workbook(pool, tops, path):
    """pool: questions whose rows are the first-batch passages only. Writes the workbook; returns (judgments listed, priority A, rows of 'our results')."""
    missing = sorted({d for order in tops.values() for d in order} - set(ALLNAMES))
    if missing:
        raise ValueError(f"no case name recorded for judgment ids {missing}; add them to EXTRA first")
    wb = Workbook()
    # ------------------------------------------------------------------ Read me
    ws = wb.active; ws.title = "Read me"; ws.column_dimensions["A"].width = 28; ws.column_dimensions["B"].width = 110
    def put(r, a, b=None, h=None, bold=False, fill=None, italic=False):
        if a is not None: ws.cell(r, 1, a).font = F(bold=True); ws.cell(r, 1).alignment = wrap
        if b is not None: ws.cell(r, 2, b).font = F(bold=bold, italic=italic); ws.cell(r, 2).alignment = wrap
        if fill: ws.cell(r, 1).fill = fill; ws.cell(r, 2).fill = fill
        if h: ws.row_dimensions[r].height = h
    ws["A1"] = "Authority Check List: Criminal-Law Search Project"; ws["A1"].font = F(bold=True, size=14)
    ws["A2"] = "Two checks that an AI marking passages cannot do reliably: is a case still good law, and what does a trusted research tool show for the same questions."; ws["A2"].font = F(italic=True)
    r = 4
    put(r, "Who can do this", "Anyone with access to an Indian legal research platform (for example LawCentral AI, Manupatra, SCC Online) or the free Indian Kanoon site. You do not need to be a lawyer, but a lawyer's entries are worth more and are labelled separately (column 'Who filled this row').", 44); r += 1
    put(r, "Part 1: Judgments", "Sheet 'Judgments'. For each case, look it up in your tool and record whether it is still good law. Do the rows marked Priority A first. If your tool has an 'overruled / good law' flag, record what it says and which later case it names. If it has no flag, open the later cases that cite it and read how they treat it, and say so in 'How confirmed'.", 58); r += 1
    put(r, "Part 2: Questions", "Sheet 'Questions'. For each of the 12 questions, type the question into the tool the way a user would. Record the tool's leading authority and its top 5 cases FIRST. Only then open the last sheet 'Our results (open last)' and fill in how many of the tool's top 5 also appear in our list, and your overall verdict for someone who is not a lawyer.", 58); r += 2
    put(r, "Status meanings", None, fill=GREY); r += 1
    for k, v in [("Good law", "No later Supreme Court decision overruled, doubted or limited it (by the tool's flag or by your reading)."), ("Overruled", "A later bench of equal or larger strength held it wrong and does not follow it."),
                 ("Partly overruled", "Some of its propositions were overruled; others still stand. Name which in Notes."), ("Doubted", "A later bench expressed doubt or referred the point to a larger bench, but did not overrule."),
                 ("Distinguished", "Later cases limited it to its own facts, but it still stands."), ("Not found", "The tool could not find the case."), ("Unsure", "You looked but cannot tell.")]:
        put(r, k, v, 28 if len(v) > 100 else 16); r += 1
    r += 1
    put(r, "Please write in your own words", "In 'Notes' record short facts in your own words. Do not paste judgments, headnotes, summaries or long passages from the tool. Record only: status, citation, names of the later cases that overruled / doubted / limited it, and a short note.", 44); r += 1
    put(r, "Check the terms first", "Before you start, read the terms of use of the platform you are using. Do not scrape or bulk-download. Do not share your login. We have NOT read any platform's terms. If they forbid using its output to evaluate or build another search product, do not use that platform for this, and tell us. A free trial that expires is best used in one sitting (see the planning note).", 58, fill=FLAGF); r += 1
    put(r, "Planning a time-limited trial", "If you rely on a short free trial (LawCentral says it offers a 5-day trial on its Pro plan; that is the vendor's claim, not checked by us), do the work in this order: (1) the Priority A rows on 'Judgments'; (2) the 12 questions; (3) the remaining rows. Rough time, an estimate only: 5 to 10 minutes per case row and 5 to 10 minutes per question, so about 4 to 6 hours for everything. Save the file after every few rows.", 72); r += 1
    put(r, "How the results are labelled", "Rows filled in by a non-lawyer using a tool are reported as 'tool-checked'. Rows filled in by a lawyer are reported as 'expert-checked'. Nothing is described as lawyer-validated unless a lawyer filled it in. Nothing here is legal advice.", 44); r += 1
    put(r, "About the Year column", "Where our copy shows a decision date, 'Year' is the decision year ('Year is' = decision date). Otherwise it is the year in the case number, and the decision may have been later. Use the case name and number to find the case, not the year.", 44); r += 1
    put(r, "Colour guide", "Yellow cells are for you to fill in. Orange rows on 'Judgments' have a specific thing to check (column 'What to check'). Please do not edit white or grey cells, and do not insert, delete or sort rows. Save a copy with your initials in the file name and send it back.", 44); r += 2
    put(r, "Example (fictional, do not copy)", None, fill=GREY); r += 1
    for a, b in [("Case", "A v. B (an invented example, not a real case)"), ("Status", "Partly overruled"), ("Bench strength", "Three judges"), ("Citation", "(2001) 1 SCC 123"), ("Overruled / doubted by", "C v. D (2010), a five-judge bench, overruled it on the point about notice only"),
                 ("How confirmed", "Both"), ("Source used / Who", "Indian Kanoon / Non-lawyer using a tool"), ("Notes", "The point about limitation still stands; later cases follow it.")]:
        ws.cell(r, 1, a).font = F(bold=True); ws.cell(r, 2, b).font = F(italic=True); r += 1

    # ------------------------------------------------------------------ Judgments
    wj = wb.create_sheet("Judgments")
    cols = [("No.", 5), ("Priority", 9), ("Judgment id (ours)", 11), ("Case (as in our copy)", 40), ("Case number as printed", 26), ("Year", 7), ("Year is", 16), ("Topic (from the first lines of our copy)", 40), ("Why it is on the list", 30), ("What to check", 52),
            ("Status", 17), ("Bench strength", 20), ("Official citation (SCC / AIR)", 22), ("Overruled / doubted / limited by (case, year, bench)", 38), ("How confirmed", 20), ("Source used", 16), ("Who filled this row", 20), ("Date checked", 13), ("Notes (your own words)", 44)]
    header(wj, cols, 58)
    # why-on-list from the pool
    appear = {}
    for q in pool:
        for row in q["rows"]:
            d = appear.setdefault(row["doc"], set()); d.add(q["qid"])
    a5 = {}
    for qid, order in tops.items():
        for d in order[:5]:
            a5.setdefault(d, set()).add(qid)
    order_ids = sorted(J, key=lambda d: (0 if d in LAND else 1 if d in PRIORITY_A else 2, -(len(a5.get(d, ())) * 2 + len(appear.get(d, ()))), d))
    for i, d in enumerate(order_ids, 2):
        name, no, yr, basis, topic = J[d]
        why = []
        if d in LAND: why.append(f"Expected answer for {LAND[d]}")
        if a5.get(d): why.append("In our top 5 for " + ", ".join(sorted(a5[d])))
        elif appear.get(d): why.append("Shown for " + ", ".join(sorted(appear[d])))
        if d in PRIORITY_A and d not in LAND: why.append("Flagged")
        vals = [i - 1, "A" if d in PRIORITY_A else "B", d, name, no, yr, basis.split(" (")[0], topic, "; ".join(why), SPECIFIC.get(d, DEFAULT_CHECK)]
        for ci, v in enumerate(vals, 1):
            c = wj.cell(i, ci, v); c.font = F(bold=(ci == 4)); c.alignment = ctr if ci in (1, 2, 3, 6) else wrap; c.border = box
            if d in SPECIFIC and ci == 10: c.fill = FLAGF
        for ci in range(11, 20): c = wj.cell(i, ci); c.fill = INPUT; c.border = box; c.font = F(); c.alignment = wrap
        wj.cell(i, 18).number_format = "yyyy-mm-dd"
        wj.row_dimensions[i].height = max(44, 13 * math.ceil(len(SPECIFIC.get(d, DEFAULT_CHECK)) / 52) + 6, 13 * math.ceil(len(topic) / 40) + 6)
    lastj = len(order_ids) + 1
    dv_list(wj, STATUS, f"K2:K{lastj}", "Status", "Choose the case's current standing"); dv_list(wj, BENCH, f"L2:L{lastj}", "Bench strength"); dv_list(wj, HOW, f"O2:O{lastj}", "How confirmed"); dv_list(wj, SRC, f"P2:P{lastj}", "Source used"); dv_list(wj, WHO, f"Q2:Q{lastj}", "Who filled this row")
    dvd = DataValidation(type="date", operator="greaterThan", formula1="43831", allow_blank=True, showErrorMessage=True, error="Please enter a date, for example 2026-10-05."); wj.add_data_validation(dvd); dvd.add(f"R2:R{lastj}")
    wj.freeze_panes = "E2"; wj.auto_filter.ref = f"A1:S{lastj}"; wj.sheet_view.zoomScale = 90

    # ------------------------------------------------------------------ Questions
    wq = wb.create_sheet("Questions")
    cols = [("Q", 7), ("Kind", 13), ("Question (type it exactly like this)", 58), ("Tool used", 16), ("Tool's leading authority (case, citation)", 36), ("Tool's top 5 cases (one per line)", 46), ("Did the tool give an answer a non-lawyer could follow?", 18),
            ("How many of the tool's top 5 appear in 'Our results' (0 to 5)", 18), ("Verdict for someone who is not a lawyer", 18), ("Notes (your own words)", 44)]
    header(wq, cols, 72)
    for i, q in enumerate(pool, 2):
        for ci, v in enumerate([q["qid"], "Plain English" if q["kind"] == "lay" else "Legal wording", q["question"]], 1):
            c = wq.cell(i, ci, v); c.font = F(bold=(ci == 1)); c.alignment = wrap; c.border = box
        for ci in range(4, 11): c = wq.cell(i, ci); c.fill = INPUT; c.border = box; c.font = F(); c.alignment = wrap
        wq.row_dimensions[i].height = max(92, 14 * math.ceil(len(q["question"]) / 58) + 8)
    dv_list(wq, SRC, "D2:D13", "Tool used"); dv_list(wq, PLAIN, "G2:G13", "Plain language?"); dv_list(wq, VERDICT, "I2:I13", "Verdict", "Ours better / Similar / Ours worse / Can't tell, judged for a non-lawyer")
    dvn = DataValidation(type="whole", operator="between", formula1="0", formula2="5", allow_blank=True, showErrorMessage=True, error="Enter a whole number from 0 to 5."); wq.add_data_validation(dvn); dvn.add("H2:H13")
    wq.freeze_panes = "D2"; wq.sheet_view.zoomScale = 90

    # ------------------------------------------------------------------ Our results
    wo = wb.create_sheet("Our results (open last)")
    cols = [("Q", 7), ("Our order", 9), ("Judgment id (ours)", 11), ("Case (as in our copy)", 52), ("Case number as printed", 30), ("Year", 7), ("Year is", 16), ("Note", 70)]
    header(wo, cols, 40)
    NOTE = {18070: "Header says income tax, body is Kamaladevi Agarwal (see 'Judgments').", 20481: "Same text also held under id 18070.", 30317: "Also held as id 16795 (96% identical text).", 16795: "Same text as id 30317.",
            39112: "Reference order of 27 Feb 2012 in Lalita Kumari; the 2013 five-judge decision is id 40960.", 40960: "Five-judge decision of 12 Nov 2013 in Lalita Kumari.", 34509: "A CIVIL appeal that is in our criminal index.",
            25607: "Later criticised in Jadeja (id 37060), per our own text; see 'Judgments'."}
    row = 2
    for q in pool:
        wo.cell(row, 1, q["qid"]).font = F(bold=True)
        for ci in range(1, 9): wo.cell(row, ci).fill = QROW; wo.cell(row, ci).border = box
        c = wo.cell(row, 4, ("Plain English: " if q["kind"] == "lay" else "Legal wording: ") + q["question"]); c.font = F(bold=True); c.alignment = wrap
        wo.row_dimensions[row].height = max(30, 14 * math.ceil(len(q["question"]) / 55) + 6); row += 1
        for rank, d in enumerate(tops[q["qid"]], 1):
            name, no, yr, basis = ALLNAMES[d]
            for ci, v in enumerate([q["qid"], rank, d, name, no, yr, basis.split(" (")[0], NOTE.get(d)], 1):
                c = wo.cell(row, ci, v); c.font = F(); c.border = box; c.alignment = ctr if ci in (1, 2, 3, 6) else wrap
            row += 1
    wo.freeze_panes = "A2"
    wo.cell(row + 1, 4, "Our order is the order of each judgment's best passage in our search. A judgment that fills several of our top 10 slots appears once, so a question can list fewer than 10.").font = F(italic=True, color="7F7F7F")

    # ------------------------------------------------------------------ Summary
    sm = wb.create_sheet("Summary"); sm.column_dimensions["A"].width = 60; sm.column_dimensions["B"].width = 18
    sm["A1"] = "Summary (fills itself in)"; sm["A1"].font = F(bold=True, size=14)
    rowsum = [("Judgments to check", f"=COUNTA(Judgments!C2:C{lastj})"), ("Judgments checked", f"=COUNTA(Judgments!K2:K{lastj})"), ("Priority A judgments checked", f'=COUNTIFS(Judgments!B2:B{lastj},"A",Judgments!K2:K{lastj},"<>")')]
    rowsum += [(f"Status: {s}", f'=COUNTIF(Judgments!K2:K{lastj},"{s}")') for s in STATUS]
    rowsum += [("Rows filled by a lawyer", f'=COUNTIF(Judgments!Q2:Q{lastj},"Lawyer")'), ("Rows filled by a non-lawyer using a tool", f'=COUNTIF(Judgments!Q2:Q{lastj},"Non-lawyer using a tool")'),
               ("Questions with a verdict", '=COUNTA(Questions!I2:I13)')] + [(f"Verdict: {v}", f'=COUNTIF(Questions!I2:I13,"{v}")') for v in VERDICT]
    rowsum += [("Average overlap with our list (tool top 5 found in our results)", '=IF(COUNT(Questions!H2:H13)=0,"",AVERAGE(Questions!H2:H13))')]
    for i, (a, b) in enumerate(rowsum, 3):
        sm.cell(i, 1, a).font = F(bold=True); sm.cell(i, 1).border = box
        c = sm.cell(i, 2, b); c.font = F(); c.border = box; c.alignment = Alignment(horizontal="left")
    sm.cell(len(rowsum) + 4, 1, "Name of the person who filled this in, and the date:").font = F(bold=True)
    c = sm.cell(len(rowsum) + 4, 2); c.fill = INPUT; c.border = box
    sm.cell(len(rowsum) + 5, 1, "Platform terms read? (write Yes or No, and anything unusual you noticed)").font = F(bold=True)
    c = sm.cell(len(rowsum) + 5, 2); c.fill = INPUT; c.border = box
    sm.column_dimensions["B"].width = 50

    wb.properties.title = "Authority Check List: Criminal-Law Search Project"; wb.properties.creator = "Recourse SCI search project"
    wb.calculation = CalcProperties(fullCalcOnLoad=True)
    wb.save(path)
    return len(order_ids), sum(1 for d in order_ids if d in PRIORITY_A), sum(len(v) for v in tops.values())


def build(pool_path, out_dir):
    pool = [dict(q, rows=rc.rows_of(q, False)) for q in rc.load_pool(pool_path)]
    path = os.path.join(out_dir, "Authority_Check_List.xlsx")
    n_j, n_a, n_r = build_workbook(pool, compute_tops(pool), path)
    return path, n_j, n_a, n_r


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True, help="folder to write into")
    ap.add_argument("--pool", default=rc.DEFAULT_POOL)
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    path, n_j, n_a, n_r = build(a.pool, a.out)
    print(f"saved {path} | judgments: {n_j} | priority A: {n_a} | our-results rows: {n_r}")


if __name__ == "__main__":
    main()
