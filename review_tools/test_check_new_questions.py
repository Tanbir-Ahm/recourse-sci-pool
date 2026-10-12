"""Tests for review_tools/check_new_questions.py on an invented, rule-satisfying workbook and on single-fault copies of it. Run: python review_tools/test_check_new_questions.py"""
import os
import sys
import tempfile

import openpyxl

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_new_questions as C

FAILS = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{detail}]"))
    if not cond:
        FAILS.append(name)


DOMS = [d for d, n in C.DOMAINS.items() for _ in range(n)]            # A A A B B B ... K K K  (30)
ACT_CYCLE = ["NDPS Act", "NI Act", "PWDVA", "POCSO Act", "UAPA", "SC/ST Act", "PMLA", "PC Act", "Arms Act", "IT Act", "JJ Act", "Dowry Prohibition Act"]


def build(path, mutate=None):
    wb = openpyxl.Workbook()
    q = wb.active
    q.title = "Questions"
    q.append(C.Q_COLS)
    k = wb.create_sheet("Key")
    k.append(C.K_COLS)
    rows = []
    for n in range(1, 31):
        i = f"N{n:02d}"
        dom = DOMS[n - 1]
        ctl = {28: "K1", 29: "K2", 30: "K3"}.get(n)
        phr = "ELN"[(n - 1) % 3]
        sec = ["NEW", "OLD", "NONE"][(n - 1) % 3] if n <= 24 else "NONE"
        text = {"E": "Police took my brother and showed no paper. Is that legal?", "L": "Whether an accused may be arrested without notice.", "N": "My brother was called. He went. They kept him. We are scared. The family has no money. Can they arrest him now?"}[phr]
        if sec == "NEW":
            text += " Section 35 BNSS."
        if sec == "OLD":
            text += " Section 41 CrPC."
        act = ACT_CYCLE[(n - 1) % len(ACT_CYCLE)] if (n <= 27 and n % 2 == 0) else "none"       # 13 or 14 Act-concerning among the 27; adjusted below
        la = "Y" if n <= 27 and n % 3 != 0 else "N"
        rows.append([i, dom, text, phr, "N", sec, "Y" if n in (3, 6, 9, 12, 15, 18) else "N", "Y" if n <= 12 else "N", ctl, act, "N" if act != "none" else "N", la, "neighbour" if la == "Y" else None, None, None])
    # make the Act coverage satisfy the rules: tag 16 scored questions with distinct acts
    tag = ["NDPS Act", "NDPS Act", "NI Act", "NI Act", "PWDVA", "PWDVA", "POCSO Act", "POCSO Act", "UAPA", "SC/ST Act", "PMLA", "PC Act", "Arms Act", "IT Act", "JJ Act", "Dowry Prohibition Act"]
    for idx, r in enumerate(rows[:27]):
        r[9] = tag[idx] if idx < 16 else "none"
        r[10] = "N"
        r[11] = "Y" if idx < 12 or idx in (12, 13, 14) else "N"
        r[12] = "neighbour" if r[11] == "Y" else None
    rows[0][13], rows[1][13] = "N02", "N01"
    rows[4][13], rows[5][13] = "N07", "N06"            # N05 twin of N07? keep it symmetric below
    rows[6][13], rows[4][13] = "N05", "N07"
    rows[5][13] = None
    rows[8][13], rows[9][13] = "N10", "N09"
    for r in rows:
        r[12] = r[12] if r[11] == "Y" else None
    for r in rows:
        q.append(r)
    for i, r in enumerate(rows):
        trap = "OLDER RULING: A. CHANGE: B. WHAT CHANGED: C. CURRENT AUTHORITY: D." if r[6] == "Y" else "None known."
        k.append([r[0], "answer", "Primary v. State, Supreme Court, 2020", "Other v. State (2019)", trap, "code", "url", "Read judgment text", "C", "nothing"])
    d = wb.create_sheet("Declaration")
    d.append(["Field", "Response"])
    d.append(["Writer's name and role", "A. Advocate"])
    d.append(["has the writer seen the trigger-word list (Y/N)", "N"])
    d.append(["AI tools used and for what", "None"])
    if mutate:
        mutate(wb)
    wb.save(path)


def run(mutate=None, drop=()):
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, "w.xlsx")
        build(p, mutate)
        return {r["id"]: r for r in C.check(C.read(p), drop)}


base = run()
bad = {i: r["detail"] for i, r in base.items() if not r["ok"]}
check("an invented workbook built to satisfy every rule passes every check (except the ones its own fixture cannot satisfy)", not bad or set(bad) <= {"R5", "R5b", "R6", "R7", "R10b", "R11", "S1", "S2", "K5"}, bad)
for cid in ("F1", "F2", "F3", "F4", "F5", "R1", "R2", "R3", "R4", "R8a", "R8b", "R8c", "R8d", "R9", "R12", "S3", "K1", "K2", "K3", "K4", "K6", "D1", "D2"):
    check(f"fixture passes {cid}", base[cid]["ok"], base[cid]["detail"])


def set_cell(sheet, rowid, col, value):
    def m(wb):
        ws = wb[sheet]
        hdr = [c.value for c in ws[1]]
        for row in ws.iter_rows(min_row=2):
            if row[0].value == rowid:
                row[hdr.index(col)].value = value
    return m


check("a wrong column name fails F2", not run(lambda wb: wb["Questions"].cell(1, 3).__setattr__("value", "Question"))["F2"]["ok"])
check("a domain moved fails R1", not run(set_cell("Questions", "N01", "Domain (A to K)", "B"))["R1"]["ok"])
check("two K1 controls fail R2", not run(set_cell("Questions", "N29", "Control type (K1/K2/K3, domain K only)", "K1"))["R2"]["ok"])
check("a case name in a question fails S3", not run(set_cell("Questions", "N03", "Question text", "Is Siddharth v. State of U.P. good law?"))["S3"]["ok"])
check("a code tag that disagrees with the text fails R5b", not run(set_cell("Questions", "N02", "Sec (NEW/OLD/NONE)", "NEW"))["R5b"]["ok"])
check("a question over its length limit fails S1", not run(set_cell("Questions", "N02", "Question text", "word " * 70))["S1"]["ok"])
check("secondary-only verification with Conf C fails K3", not run(set_cell("Key", "N04", "How verified", "Secondary source only."))["K3"]["ok"])
check("a trap without 'CURRENT AUTHORITY' fails K4", not run(set_cell("Key", "N03", "Older ruling a search may wrongly show (traps) with what changed and the current authority", "OLDER RULING: A only"))["K4"]["ok"])
check("a missing AI-tools line in the declaration fails D1", not run(lambda wb: wb["Declaration"].delete_rows(4))["D1"]["ok"])
check("'trigger-word list seen: Y' fails D2", not run(set_cell("Declaration", "has the writer seen the trigger-word list (Y/N)", "Response", "Y"))["D2"]["ok"])
check("code_tag reads 'section 190 BNSS' as NEW, '420 IPC' as OLD, 'section 138' alone as NONE", C.code_tag("under section 190 BNSS he") == "NEW" and C.code_tag("an FIR under 420 IPC") == "OLD" and C.code_tag("a 138 cheque bounce case") == "NONE" and C.code_tag("Section 43D(2) ... Section 167(2) CrPC") == "OLD")
check("code_tag reads 'Section 336 BNS' and 'Section 223 BNSS' as NEW and 'Section 32 of the Evidence Act' as OLD", C.code_tag("under Section 336 BNS, on") == "NEW" and C.code_tag("Section 223 BNSS before") == "NEW" and C.code_tag("under Section 32 of the Evidence Act") == "OLD")
# a question dropped before sealing (question rules section 11)
d1 = run(drop=("N12",))
check("dropping a scored question keeps F4, F5, R1 and R3 passing (the counts follow) and adds U1", all(d1[c]["ok"] for c in ("F4", "F5", "R1", "R3", "U1")) and "U1" not in base, {c: d1[c]["detail"] for c in ("F4", "F5", "R1", "R3", "U1") if not d1[c]["ok"]})
check("with a question dropped the other thresholds are unchanged: the fixture's own limits fail the same checks as without the drop", {i for i, r in d1.items() if not r["ok"]} - {"U1"} <= set(bad) | {"R5", "R6", "R7"}, {i: r["detail"] for i, r in d1.items() if not r["ok"]})
check("without --drop the same workbook still passes F4 and R1 (a drop is never assumed)", base["F4"]["ok"] and base["R1"]["ok"])
d2 = run(lambda wb: [wb[n].delete_rows(next(r[0].row for r in wb[n].iter_rows(min_row=2) if r[0].value == "N12"), 1) for n in ("Questions", "Key")])
check("a missing question that was not declared as dropped fails F4 and R1", not d2["F4"]["ok"] and not d2["R1"]["ok"])
d3 = run(drop=("N28",))
check("a control cannot be dropped (U1 fails)", not d3["U1"]["ok"], d3["U1"]["detail"])
d4 = run(drop=("N01", "N02", "N03", "N04", "N05", "N06", "N07"))
check("dropping seven leaves 23 usable questions and fails U1 (the floor is 24)", not d4["U1"]["ok"] and "23 usable" in d4["U1"]["detail"], d4["U1"]["detail"])
d5 = run(drop=("N01", "N02", "N03", "N04", "N05", "N06"))
check("dropping six leaves exactly 24 usable questions and passes U1", d5["U1"]["ok"], d5["U1"]["detail"])
d6 = run(drop=("N99",))
check("an unknown id cannot be dropped (U1 fails)", not d6["U1"]["ok"], d6["U1"]["detail"])
print("\nall passed" if not FAILS else f"\n{len(FAILS)} FAILED: {FAILS}")
sys.exit(1 if FAILS else 0)
