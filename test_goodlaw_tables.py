"""Tests for goodlaw/tables.py and its use in the report: the law reporters' case-law tables as evidence. Run: python test_goodlaw_tables.py"""
from goodlaw import mentions as M
from goodlaw import report as R
from goodlaw import tables as TB

FAILURES = []


def check(condition, description):
    print(f"[{'PASS' if condition else 'FAIL'}] {description}")
    if not condition:
        FAILURES.append(description)


TEXT = """headnote words.
Case Law Reference
[2006] 3 SCR 420
referred to
Para 4
[1953) 2 SCR 581
overruled
Para 14
[1999] 2 SCR 1033
relied on
Para 15
[1962] SCR 702
partly overruled
Paras 16, 17
(1994) 4 sec 260
not approved
Para 18
CIVIL APPELLATE JURISDICTION : Civil Appeal No. 7804 of 2019.
The court's own judgment follows here.
"""
BODY = len(TEXT) - 40
rows = TB.rows_for_target(TEXT, BODY, ["scr:1953:2:581", "scr:1962::702", "scc:1994:4:260", "scr:2006:3:420"])
check([(r["code"], r["code_text"]) for r in rows] == [("R", "referred to"), ("O", "overruled"), ("O", "partly overruled"), ("NF", "not approved")],
      "rows are kept only for the target's own citations, with the scanner's damage mended, each with its letter")
check(all(r["quote_verified"] for r in rows) and rows[1]["quote"] == "[1953) 2 SCR 581 overruled Para 14", "each row's quote is the table's own words and is found word for word in the text")
check(TB.rows_for_target(TEXT, BODY, ["scr:1980:1:1"]) == [] and TB.rows_for_target(TEXT, BODY, []) == [], "a target the table does not name has no rows")

T = M.Target("ALPHA", "BETA", 2010, ["scr:1953:2:581"], date="2010-01-01", doc_key="c1", bench_size=3, bench_source="report_line")


def row(doc, code, code_text, bench, source="report_line", **kw):
    r = {"doc_key": doc, "title": f"Case {doc}", "date": "2018-01-01", "year": 2018, "bench_size": bench, "bench_source": source, "source": "bucket", "code": code, "code_text": code_text,
         "para": "Para 3", "quote": f"[2010] 1 SCR 1 {code_text} Para 3", "quote_verified": True, "cite": "[2010] 1 SCR 1"}
    r.update(kw)
    return r


strong, possible = [], []
summary = R._table_into_lists([row("b1", "O", "overruled", 5), row("b2", "O", "overruled", 3), row("b3", "O", "overruled", 2), row("b4", "NF", "disapproved", 5), row("b5", "NF", "disapproved", 3),
                               row("b6", "RF", "relied on", 2, date="2020-05-05", year=2020), row("b7", "R", "referred to", 2), row("b8", "F", "followed", 2, date="2019-05-05", year=2019)], T, strong, possible)
check([m["doc_key"] for m in strong] == ["b1", "b2", "b4"], "'overruled' by a bench at least as large as the target's, and disapproval by a larger bench, are strong; the rest are not")
check([m["doc_key"] for m in possible] == ["b3", "b5"] and "smaller bench" in possible[0]["why_not_a_clean_overruling"][0], "an overruling by a smaller bench, and disapproval by an equal bench, go to the possible list with the reason")
check(strong[0]["tier"] == "table" and strong[0]["speaker"] == "the law report's case-law table" and "case-law table marks it overruled" in strong[0]["kind"], "the entry says whose statement it is")
check(summary["judgments_with_a_row"] == 8 and summary["by_what_the_reporter_marked"]["overruled"] == 3 and summary["by_what_the_reporter_marked"]["relied on"] == 1, "every row is counted by what the reporter marked")
check([r["title"] for r in summary["recent_relied_on"]] == ["Case b6", "Case b8"], "the most recent 'relied on' and 'followed' rows are listed, newest first")

strong2 = [{"doc_key": "b1"}]
possible2 = []
R._table_into_lists([row("b1", "O", "overruled", 5)], T, strong2, possible2)
check(len(strong2) == 1, "a judgment already in the strong list is not listed twice")

# unknown bench sizes: an overruling is still strong (bench unknown), disapproval is not
s3, p3 = [], []
R._table_into_lists([row("b9", "O", "overruled", None, source=None), row("b10", "NF", "not followed", None, source=None)], T, s3, p3)
check([m["doc_key"] for m in s3] == ["b9"] and [m["doc_key"] for m in p3] == ["b10"], "with the bench unknown, 'overruled' counts and 'not followed' is only a possibility")

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILED")
    for f in FAILURES:
        print(" -", f)
    raise SystemExit(1)
print("ALL PASSED")
