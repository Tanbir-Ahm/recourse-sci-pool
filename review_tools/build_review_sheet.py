#!/usr/bin/env python3
"""Builds the pooled human review sheet (Search_Review_Sheet_Pooled_v2.xlsx): every first-batch passage of every question in a shuffled order, with a
dropdown mark, a comment, a per-question verdict sheet and a reviewer summary. It shows nothing about which search found a passage.

  python review_tools/build_review_sheet.py --out DIR [--pool review_data/pool_all.json] [--judgments 8236 --passages 156235]

--judgments and --passages only fill in the sentence in the Read me that describes the index; set them if the index has changed since the sheet was first made.
"""
import argparse
import math
import os
import sys

from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.workbook.properties import CalcProperties
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.properties import PageSetupProperties

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import review_common as rc

clean = rc.clean
MARKS = rc.MARKS
MEANING = {"Yes": "Answers the question directly.", "Partly": "On the topic and useful, but does not fully answer it.", "No": "Not helpful.",
           "Misleading": "Could give a wrong impression, for example a point made by counsel and rejected, or text taken out of context."}


def build_workbook(pool, path, judgments, passages):
    """pool: questions whose rows are the first-batch passages only. Writes the workbook to path and returns the last Review row."""
    F = lambda **k: Font(name="Arial", size=k.pop("size", 10), **k)
    thin = Side(style="thin", color="BFBFBF")
    box = Border(left=thin, right=thin, top=thin, bottom=thin)
    HEAD = PatternFill("solid", fgColor="1F3864"); QROW = PatternFill("solid", fgColor="D9E2F3"); INPUT = PatternFill("solid", fgColor="FFF2CC"); GREY = PatternFill("solid", fgColor="F2F2F2")
    wrap_top = Alignment(wrap_text=True, vertical="top"); center_top = Alignment(horizontal="center", vertical="top", wrap_text=True)
    lay = ", ".join(q["qid"] for q in pool if q["kind"] == "lay")
    legal = ", ".join(q["qid"] for q in pool if q["kind"] != "lay")
    n_pass = sum(len(q['rows']) for q in pool)
    lo_n = min(len(q['rows']) for q in pool); hi_n = max(len(q['rows']) for q in pool)
    wb = Workbook()

    # ---------------------------------------------------------------- Read me
    ws = wb.active; ws.title = "Read me"
    ws.column_dimensions["A"].width = 26; ws.column_dimensions["B"].width = 100
    def put(r, a=None, b=None, bold=False, size=10, fill=None, h=None):
        if a is not None: ws.cell(r, 1, a).font = F(bold=True, size=size); ws.cell(r, 1).alignment = wrap_top
        if b is not None: ws.cell(r, 2, b).font = F(bold=bold, size=size); ws.cell(r, 2).alignment = wrap_top
        if fill: ws.cell(r, 1).fill = fill; ws.cell(r, 2).fill = fill
        if h: ws.row_dimensions[r].height = h
    ws["A1"] = "Search Review Sheet: Criminal-Law Judgments"; ws["A1"].font = F(bold=True, size=14)
    ws["A2"] = "Please judge whether a legal search tool returns useful answers. Your marks will be used to measure and improve it."; ws["A2"].font = F(italic=True)
    r = 4
    put(r, "What is being tested", f"A search over {judgments:,} Supreme Court criminal-law judgments ({passages:,} passages). Civil and tax cases are not included. There are {len(pool)} questions: six topics, each asked twice, once in plain English ({lay}) and once in legal wording ({legal}). For each question you will see between {lo_n} and {hi_n} passages ({n_pass} in total) that different versions of the search returned.", h=64); r += 1
    put(r, "What to do", None, h=16); r += 1
    steps = ["1. Open the sheet 'Review'. Each question has a blue banner with the question, then its passages in a random order. The order says nothing about quality.",
             "2. Read each passage as if you had asked that question. In the yellow 'Your mark' cell pick one option from the dropdown (meanings below). Add a short comment in the next yellow cell if useful.",
             "3. After a question's passages, open 'Question verdicts' and fill that question's row: whether a good answer appears, the best passage number, and the leading authority you would expect for the question.",
             "4. Finish with 'Reviewer summary': your name, the date, and the three free-text lines. The counts there fill themselves in.",
             "5. Save the file under a new name (add your initials) and send it back. Do not rename the sheets and do not insert, delete or sort rows; filtering is fine."]
    for s in steps: put(r, None, s, h=30); r += 1
    r += 1
    put(r, "Your mark", "Choose one per passage", bold=True, fill=GREY); r += 1
    for k in MARKS:
        ws.cell(r, 1, k).font = F(bold=True); ws.cell(r, 2, MEANING[k]).font = F(); ws.cell(r, 2).alignment = wrap_top
        ws.cell(r, 1).fill = {"Yes": PatternFill("solid", fgColor="C6EFCE"), "Partly": PatternFill("solid", fgColor="FFEB9C"), "No": PatternFill("solid", fgColor="D9D9D9"), "Misleading": PatternFill("solid", fgColor="FFC7CE")}[k]
        ws.row_dimensions[r].height = 28 if k == "Misleading" else 16; r += 1
    r += 1
    put(r, "Colour guide", "Yellow cells are for you to fill in. White and grey cells are the material to read; please do not edit them. The column 'Ref (do not edit)' lets the project team match your marks to the right passage.", h=30); r += 1
    put(r, "Blind by design", "The sheet does not show which search version returned a passage, how it was ranked, or which case the project expected. Please do not look for that; judge on the text alone.", h=30); r += 1
    put(r, "Repeated text", "If the same text appears in more than one judgment it is shown once, and the column 'Same text also in judgment id(s)' lists the others. Mark it once.", h=30); r += 1
    put(r, "Time", "About 11 to 16 passages per question. Allow roughly 20 to 25 minutes per question, about 4 hours for the whole sheet. Two reviewers may split it: one takes Q01 to Q06, the other Q07 to Q12. If two reviewers can both mark Q03, Q04, Q09 and Q10, we can measure how much reviewers agree.", h=54); r += 1
    put(r, "Judgments", "The crawl stores no case names or links, so each judgment is identified by its opening header text, an internal id, and the paragraph and page where known.", h=30); r += 1
    put(r, "Version", "Version 2: opening headers were added for nine passages that had none. The passages, their order and their Ref codes are unchanged from version 1, so marks made on either version line up.", h=30); r += 2
    put(r, "Example (do not copy)", None, fill=GREY); r += 1
    ws.cell(r, 1, "Passage text").font = F(bold=True); ws.cell(r, 2, "\"The accused may rebut the presumption by raising a probable defence on the preponderance of probabilities.\" (a passage on who must prove a cheque debt)").font = F(italic=True); ws.cell(r, 2).alignment = wrap_top; ws.row_dimensions[r].height = 28; r += 1
    ws.cell(r, 1, "Your mark").font = F(bold=True); ws.cell(r, 2, "Partly").font = F(italic=True); r += 1
    ws.cell(r, 1, "Comment").font = F(bold=True); ws.cell(r, 2, "Right rule, but it says nothing about who proves the debt in the first place.").font = F(italic=True); ws.cell(r, 2).alignment = wrap_top

    # ---------------------------------------------------------------- Review
    rv = wb.create_sheet("Review")
    cols = [("Q", 7), ("No.", 6), ("Judgment (opening header, id, paragraph, page)", 40), ("Passage text", 100), ("Your mark", 13), ("Comment", 40), ("Same text also in judgment id(s)", 16), ("Ref (do not edit)", 26)]
    for i, (name, w) in enumerate(cols, 1):
        c = rv.cell(1, i, name); c.font = F(bold=True, color="FFFFFF"); c.fill = HEAD; c.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center"); c.border = box
        rv.column_dimensions[chr(64 + i)].width = w
    rv.row_dimensions[1].height = 32
    row = 2; qrows = {}
    for q in pool:
        kind = "Plain English" if q["kind"] == "lay" else "Legal wording"
        for ci in range(1, 9): rv.cell(row, ci).fill = QROW; rv.cell(row, ci).border = box
        rv.cell(row, 1, q["qid"]).font = F(bold=True); rv.cell(row, 3, kind).font = F(bold=True)
        c = rv.cell(row, 4, "QUESTION: " + clean(q["question"])); c.font = F(bold=True, size=11); c.alignment = wrap_top
        for ci in (1, 3): rv.cell(row, ci).alignment = wrap_top
        rv.row_dimensions[row].height = max(34, 15 * math.ceil(len(q["question"]) / 95) + 8)
        row += 1; first = row
        for p in q["rows"]:
            para = f"paragraph {p['pn']}" if p["pn"] else "unnumbered paragraph"
            j = f"{clean(p['title']) if p['title'] else 'Opening header not available'}\nJudgment id {p['doc']} · {para} · page {p['page']}"
            vals = [q["qid"], p["n"], j, clean(p["text"]), None, None, ", ".join(str(d) for d in p["also"]) or None, f"J{p['doc']}|p{p['page']}|{p['pn'] or '-'}|{p['h']}"]
            for ci, v in enumerate(vals, 1):
                c = rv.cell(row, ci, v); c.border = box; c.font = F(size=10, color="7F7F7F" if ci == 8 else "000000"); c.alignment = center_top if ci in (1, 2, 5) else wrap_top
                if v is not None and isinstance(v, str): c.data_type = "s"
            for ci in (5, 6): rv.cell(row, ci).fill = INPUT
            rv.row_dimensions[row].height = min(409, 13 * max(math.ceil(len(vals[3]) / 100), math.ceil(len(j) / 38) + 1, 3) + 6)
            row += 1
        qrows[q["qid"]] = (first, row - 1)
    last = row - 1
    dv = DataValidation(type="list", formula1='"' + ",".join(MARKS) + '"', allow_blank=True, showErrorMessage=True, errorTitle="Pick from the list", error="Please choose Yes, Partly, No or Misleading.", showInputMessage=True, promptTitle="Your mark", prompt="Yes = answers directly | Partly = useful, not complete | No = not helpful | Misleading = could give a wrong impression")
    rv.add_data_validation(dv)
    for q in pool:
        a, b = qrows[q["qid"]]; dv.add(f"E{a}:E{b}")
    rng = f"E2:E{last}"
    rv.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=['"Yes"'], fill=PatternFill("solid", bgColor="C6EFCE", fgColor="C6EFCE")))
    rv.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=['"Partly"'], fill=PatternFill("solid", bgColor="FFEB9C", fgColor="FFEB9C")))
    rv.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=['"No"'], fill=PatternFill("solid", bgColor="D9D9D9", fgColor="D9D9D9")))
    rv.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=['"Misleading"'], fill=PatternFill("solid", bgColor="FFC7CE", fgColor="FFC7CE"), font=Font(name="Arial", color="9C0006", bold=True)))
    rv.freeze_panes = "C2"; rv.auto_filter.ref = f"A1:H{last}"; rv.sheet_view.zoomScale = 90
    rv.page_setup.orientation = "landscape"; rv.page_setup.fitToWidth = 1; rv.page_setup.fitToHeight = 0; rv.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True); rv.print_title_rows = "1:1"

    # ---------------------------------------------------------------- Question verdicts
    qv = wb.create_sheet("Question verdicts")
    heads = [("Q", 7), ("Kind", 14), ("Question", 60), ("Does a good answer appear anywhere in the passages shown?", 22), ("Best passage number (type the No. from the Review sheet)", 22), ("Leading authority you would expect for this question (case name or citation)", 44), ("Is that leading authority among the passages shown?", 20), ("Comments", 44)]
    for i, (name, w) in enumerate(heads, 1):
        c = qv.cell(1, i, name); c.font = F(bold=True, color="FFFFFF"); c.fill = HEAD; c.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center"); c.border = box
        qv.column_dimensions[chr(64 + i)].width = w
    qv.row_dimensions[1].height = 62
    dvg = DataValidation(type="list", formula1='"Yes,No"', allow_blank=True, showErrorMessage=True, error="Please choose Yes or No."); dva = DataValidation(type="list", formula1='"Yes,No,Not sure"', allow_blank=True, showErrorMessage=True, error="Please choose Yes, No or Not sure.")
    qv.add_data_validation(dvg); qv.add_data_validation(dva)
    for i, q in enumerate(pool, 2):
        vals = [q["qid"], "Plain English" if q["kind"] == "lay" else "Legal wording", clean(q["question"])]
        for ci, v in enumerate(vals, 1):
            c = qv.cell(i, ci, v); c.font = F(); c.alignment = wrap_top; c.border = box
        for ci in range(4, 9): c = qv.cell(i, ci); c.fill = INPUT; c.border = box; c.font = F(); c.alignment = wrap_top
        qv.row_dimensions[i].height = max(32, 14 * math.ceil(len(q["question"]) / 60) + 6)
        dvg.add(f"D{i}"); dva.add(f"G{i}")
        n = len(q["rows"]); dvn = DataValidation(type="whole", operator="between", formula1="1", formula2=str(n), allow_blank=True, showErrorMessage=True, error=f"Enter a passage number from 1 to {n} for this question.")
        qv.add_data_validation(dvn); dvn.add(f"E{i}")
    qv.freeze_panes = "D2"; qv.sheet_view.zoomScale = 100

    # ---------------------------------------------------------------- Reviewer summary
    sm = wb.create_sheet("Reviewer summary")
    sm.column_dimensions["A"].width = 62; sm.column_dimensions["B"].width = 80
    sm["A1"] = "Reviewer summary"; sm["A1"].font = F(bold=True, size=14)
    sm["A2"] = "Fill in the yellow cells. The counts fill themselves in from your marks."; sm["A2"].font = F(italic=True)
    rows_ = [("Reviewer name and date:", None, True), ("Questions with a good answer in the passages shown (out of 12):", "=COUNTIF('Question verdicts'!D2:D13,\"Yes\")", False),
             ("Passages marked Yes", "=COUNTIF(Review!E2:E%d,\"Yes\")" % last, False), ("Passages marked Partly", "=COUNTIF(Review!E2:E%d,\"Partly\")" % last, False),
             ("Passages marked No", "=COUNTIF(Review!E2:E%d,\"No\")" % last, False), ("Passages marked Misleading", "=COUNTIF(Review!E2:E%d,\"Misleading\")" % last, False),
             ("Total passages to mark", "=COUNT(Review!B2:B%d)" % last, False), ("Passages still unmarked", "=B9-SUM(B5:B8)", False)]
    for i, (a, b, inp) in enumerate(rows_, 3):
        sm.cell(i, 1, a).font = F(bold=True); sm.cell(i, 1).alignment = wrap_top; sm.cell(i, 1).border = box
        c = sm.cell(i, 2, b); c.font = F(); c.border = box; c.alignment = Alignment(horizontal="left", vertical="top")
        if inp: c.fill = INPUT
    sm["B4"].number_format = "0"
    for i, label in enumerate(["Passages that could mislead a layperson (give question and passage numbers):", "Anything the search should never show a layperson:", "Other comments:"], 12):
        sm.cell(i, 1, label).font = F(bold=True); sm.cell(i, 1).alignment = wrap_top; sm.cell(i, 1).border = box
        c = sm.cell(i, 2); c.fill = INPUT; c.border = box; c.font = F(); c.alignment = wrap_top; sm.row_dimensions[i].height = 78
    sm["A16"] = "Counts are formulas over the 'Review' and 'Question verdicts' sheets: please do not overwrite them."; sm["A16"].font = F(italic=True, color="7F7F7F")

    wb.properties.title = "Search Review Sheet: Criminal-Law Judgments"; wb.properties.creator = "Recourse SCI search project"
    wb.calculation = CalcProperties(fullCalcOnLoad=True)
    wb.save(path)
    return last


def build(pool_path, out_dir, judgments=8236, passages=156235):
    pool = [dict(q, rows=rc.rows_of(q, False)) for q in rc.load_pool(pool_path)]
    path = os.path.join(out_dir, "Search_Review_Sheet_Pooled_v2.xlsx")
    last = build_workbook(pool, path, judgments, passages)
    return path, sum(len(q["rows"]) for q in pool), last


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True, help="folder to write into")
    ap.add_argument("--pool", default=rc.DEFAULT_POOL)
    ap.add_argument("--judgments", type=int, default=8236)
    ap.add_argument("--passages", type=int, default=156235)
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    path, n, last = build(a.pool, a.out, a.judgments, a.passages)
    print(f"saved {path} | passage rows: {n} | last Review row: {last}")


if __name__ == "__main__":
    main()
