"""test_sci_checker_names.py -- sci_checker_names.py: the names file for Recourse's invented-case check. Offline and free (a small names table and a small library in a temporary folder).
Run: python test_sci_checker_names.py"""
import gzip
import json
import os
import sys
import tempfile

import sci_checker_names as SC

FAILURES = []


def check(cond, msg):
    print(f"[{'PASS' if cond else 'FAIL'}] {msg}")
    if not cond:
        FAILURES.append(msg)


tmp = tempfile.mkdtemp()
table = {"schema": "names-table-1", "index_commit": "abc1234", "documents": 6, "named": 5, "rows": [
    {"doc": 1, "name": "Arnesh Kumar v. State of Bihar", "date": "2014-07-02", "court": "Supreme Court of India"},
    {"doc": 2, "name": "Bimal Das v. State of Assam", "date": "2012-05-09", "court": "Gauhati High Court"},
    {"doc": 3, "name": "Bimal Das v. State of Assam", "date": "2012-05-09", "court": "Gauhati High Court"},            # the same judgment twice: one row
    {"doc": 4, "name": "Bimal Das v. State of Assam", "date": "2013-01-01", "court": "Gauhati High Court"},            # same name, another date: kept
    {"doc": 5, "name": None, "date": None, "court": "Supreme Court of India"},                                         # no name: left out and counted
    {"doc": 6, "name": "Zed v. Yan", "date": None, "court": None},
]}
tp = os.path.join(tmp, "table.json.gz")
with gzip.open(tp, "wt", encoding="utf-8") as fh:
    json.dump(table, fh)
rec = os.path.join(tmp, "rec")
os.makedirs(os.path.join(rec, "chunks"))
json.dump([{"case_name": "Deepa v S. Vijayalakshmi", "text": "x"}], open(os.path.join(rec, "chunks", "deepa_chunks.json"), "w"))
json.dump([{"case_name": "Arnesh Kumar v. State of Bihar", "text": "x"}], open(os.path.join(rec, "chunks", "arnesh_chunks.json"), "w"))     # already in the table: not added twice
json.dump([{"act_name": "Some Act", "text": "x"}], open(os.path.join(rec, "chunks", "some_act_chunks.json"), "w"))                            # an Act, not a case
open(os.path.join(rec, "chunks", "broken_chunks.json"), "w").write("{not json")

d = SC.build(tp, rec)
names = [r[0] for r in d["rows"]]
check(d["schema"] == SC.SCHEMA and d["index_commit"] == "abc1234" and d["unnamed_left_out"] == 1, "schema, index commit and the count of unnamed judgments are recorded")
check(d["wide_rows"] == 4 and d["library_rows"] == 1, f"four wide-index rows (a duplicate judgment is one row) and one library row ({d['wide_rows']}, {d['library_rows']})")
check(names.count("Bimal Das v. State of Assam") == 2 and "Deepa v S. Vijayalakshmi" in names and names.count("Arnesh Kumar v. State of Bihar") == 1, "same name on another date kept; library case added; a library case already in the table not added twice")
check("Some Act" not in names, "an Act's chunk file is not a case")
check(sorted(d["courts"]) == sorted({"Supreme Court of India", "Gauhati High Court", SC.LIBRARY_COURT}), f"courts are listed once each ({d['courts']})")

out, _ = SC.export(tp, rec, os.path.join(tmp, "out.json.gz"))
check(os.path.exists(out) and SC.verify(out, tp, rec) == [], "export then verify: no differences")
f = json.load(gzip.open(out, "rt", encoding="utf-8"))
f["rows"].append(["Invented v. Added", 0, None, 0])
with gzip.open(out, "wt", encoding="utf-8") as fh:
    json.dump(f, fh)
check(SC.verify(out, tp, rec) != [], "verify notices a row that is not in the sources")
f["rows"].pop()
f["index_commit"] = "other"
with gzip.open(out, "wt", encoding="utf-8") as fh:
    json.dump(f, fh)
check(any("index commit" in p for p in SC.verify(out, tp, rec)), "verify notices a file built for another index commit")
check(SC.main(["export", tp, rec, "--out", os.path.join(tmp, "o2.json.gz")]) == 0 and SC.main(["verify", os.path.join(tmp, "o2.json.gz"), tp, rec]) == 0, "the command line exports and verifies")

# the real names table, when it is in this checkout
here = os.path.dirname(os.path.abspath(__file__))
real = os.path.join(here, "names_table", "names_table_d8811a9.json.gz")
if os.path.exists(real):
    dd = SC.build(real, os.path.join(tmp, "rec"))
    check(dd["wide_rows"] > 19000 and dd["index_commit"].startswith("d8811a9") and dd["unnamed_left_out"] == 108, f"the real names table: {dd['wide_rows']} names, {dd['unnamed_left_out']} unnamed left out")

print("\nALL PASSED" if not FAILURES else f"\n{len(FAILURES)} FAILED: {FAILURES}")
sys.exit(1 if FAILURES else 0)
