"""Tests for review_tools/real30_authority_coverage.py on a tiny invented corpus store and index. Run: python review_tools/test_real30_authority_coverage.py"""
import gzip
import json
import os
import sqlite3
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import real30_authority_coverage as C

FAILS = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{detail}]"))
    if not cond:
        FAILS.append(name)


check("norm keeps letters and digits only", C.norm("D.K. Basu, 1997 (S.C.)") == "dkbasu1997sc")
check("every authority names a question Q1 to Q29, a known role and at least one token already in normal form",
      all(q[0] == "Q" and 1 <= int(q[1:]) <= 29 and role in ("key", "stale", "control", "extra") and toks and all(t == C.norm(t) for t in toks) for q, role, _, toks, _, _ in C.AUTHORITIES))
check("every question from Q1 to Q29 has at least one authority", {a[0] for a in C.AUTHORITIES} == {f"Q{i}" for i in range(1, 30)})

tmp = tempfile.mkdtemp()
os.makedirs(os.path.join(tmp, "index"))
con = sqlite3.connect(os.path.join(tmp, "corpus.sqlite"))
con.execute("create table docs (id integer primary key, doc_key text, source text, src_id text, bucket_path text, title text, pet text, resp text, date text, year integer, insc text)")
rows = [
    (1, "c1", "crawl", "11", None, "Arnesh Kumar v. State of Bihar & Anr", "Arnesh Kumar", "State of Bihar", "2014-07-02", 2014, "2014 INSC 463"),
    (2, "b1", "bucket", "0", "p/arjun.json", "ARJUN PANDITRAO KHOTKAR versus KAILASH KUSHANRAO GORANTYAL AND ORS.", "Arjun Panditrao Khotkar", "Kailash", "2020-07-14", 2020, "2020 INSC 453"),
    (3, "c2", "crawl", "12", None, "Arnesh Kumar v. State of Bihar & Anr (a different year)", "Arnesh Kumar", "State of Bihar", "1999-01-01", 1999, None),
]
con.executemany("insert into docs values (?,?,?,?,?,?,?,?,?,?,?)", rows)
con.commit()
con.close()
with gzip.open(os.path.join(tmp, "index", "000000.docs.jsonl.gz"), "wt", encoding="utf-8") as fh:
    fh.write(json.dumps({"doc": 11, "passages": 5}) + "\n")
    fh.write(json.dumps({"doc": 1000000001, "skip": "not_criminal", "src": {"path": "p/arjun.json"}}) + "\n")
    fh.write(json.dumps({"doc": 12, "passages": 3}) + "\n")

C.AUTHORITIES = [("Q2", "key", "Arnesh Kumar v. State of Bihar (2014)", ["arneshkumar", "bihar"], 2014, 0),
                 ("Q21", "key", "Arjun Panditrao (2020)", ["arjunpanditrao"], 2020, 0),
                 ("Q15", "key", "Shivangi Bansal (2025)", ["shivangibansal"], 2025, 0)]
res = C.run(os.path.join(tmp, "corpus.sqlite"), tmp)
by = {r["q"]: r for r in res}
check("a judgment with passages in the index is 'in_index'", by["Q2"]["where"] == "in_index" and [h["doc_key"] for h in by["Q2"]["hits"]] == ["c1"], by["Q2"])
check("the same name in another year is not taken for it", all(h["doc_key"] != "c2" for h in by["Q2"]["hits"]))
check("a judgment the criminal-law filter skipped is 'filtered_out'", by["Q21"]["where"] == "filtered_out", by["Q21"])
check("a name the corpus does not hold is 'not_in_collection'", by["Q15"]["where"] == "not_in_collection" and by["Q15"]["hits"] == [], by["Q15"])

out = os.path.join(tmp, "out", "cov.json")
check("main writes the JSON and returns 0", C.main(["--corpus", os.path.join(tmp, "corpus.sqlite"), "--index-dir", tmp, "--out", out]) == 0 and len(json.load(open(out))) == 3)

print()
print("FAILED: " + ", ".join(FAILS) if FAILS else "all passed")
sys.exit(1 if FAILS else 0)
