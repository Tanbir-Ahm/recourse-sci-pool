"""Tests for goodlaw/modern_gold.py: the answer key read from the reporters' case-law tables. Run: python test_goodlaw_modern_gold.py"""
from goodlaw import modern_gold as G

FAILURES = []


def check(condition, description):
    print(f"[{'PASS' if condition else 'FAIL'}] {description}")
    if not condition:
        FAILURES.append(description)


TEXT = """headnote text. Judicial Review of Administrative Action (1955) – referred to.
Case Law Reference
[2006] 3 SCR 420
referred to
Para 4
[1993] 3 SCR 128
overruled
Para 14
[1999] 2 SCR 1033 
relied on
Para 15
(2020) 15 SCC 460
held inapplicable
Para 30
[2006] 6 Suppl. SCR 512
stood overruled
Paras 16, 17
CIVIL APPELLATE JURISDICTION : Civil Appeal Nos. 7804 of 2019.
From the Judgment and Order dated 21.12.2015 of the High Court.
Para 99 in the body is not a table row.
"""
rows = G.table_rows(TEXT, body_start=len(TEXT) - 60)
check([(c, k) for c, k, _ in rows] == [("[2006] 3 SCR 420", "referred to"), ("[1993] 3 SCR 128", "overruled"), ("[1999] 2 SCR 1033", "relied on"), ("(2020) 15 SCC 460", "held inapplicable"), ("[2006] 6 Suppl. SCR 512", "stood overruled")],
      "rows are read as citation, treatment, paragraph, and stop at the first jurisdiction line")
check(G.table_rows("no table here at all") == [], "a judgment without the table gives no rows")
check(G.table_rows("Case Law Reference\nParas 3\nPara 4\n") == [], "lines that do not fit the three-line shape are skipped")

for text, letter in [("overruled", "O"), ("partly overruled", "O"), ("stood overruled", "O"), ("held not good law", "O"), ("not correct law", "O"), ("per incuriam", "O"),
                     ("not approved", "NF"), ("disapproved", "NF"), ("not followed", "NF"), ("dissented from", "NF"),
                     ("held inapplicable", "D"), ("distinguished", "D"), ("explained", "E"), ("clarified", "E"),
                     ("relied on.", "RF"), ("relied oil", "RF"), ("followed", "F"), ("approved", "F"), ("affirmed", "F"), ("held applicable", "F"),
                     ("referred to", "R"), ("referred", "R"), ("discussed", "R"), ("Para 10", None), ("", None)]:
    check(G.code_letter(text) == letter, f"code {text!r} -> {letter}")
check(G.code_letter("not approved") == "NF" and G.code_letter("approved") == "F", "'not approved' is read as disapproval, not approval")

pairs = [("c1", f"b{i}", "R", "x") for i in range(200)]
tune, kept = G.split(pairs)
check(len(tune) + len(kept) == 200 and not set(tune) & set(kept) and 60 < len(tune) < 140, "the split is a partition of roughly equal halves")
check(G.split(pairs) == (tune, kept), "the split is stable")
same = [("c1", "b7", "R", "x"), ("c2", "b7", "O", "y")]
t2, k2 = G.split(same)
check(len(t2) in (0, 2) and len(k2) in (0, 2), "every row of one judgment's table lands on the same side")

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILED")
    for f in FAILURES:
        print(" -", f)
    raise SystemExit(1)
print("ALL PASSED")
