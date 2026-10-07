"""The extra reading of the full reply set, 2026-10-07 (a record of what was run, not a tool): per search version, in how many questions the passages it showed
held a direct answer (consensus Yes) or a Misleading passage, the plain-language questions on their own, the passages only the site's method showed, and the
consensus-Misleading passages. Usage: python review_tools/experiments/read_full_set_2026-10-07.py RESULTS_DIR   (RESULTS_DIR holds llm_marks.csv from ingest_llm_reviews.py)."""
import collections
import csv
import json
import os
import re
import sys

results = sys.argv[1]
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
pool = json.load(open(os.path.join(root, "review_data", "pool_all.json"), encoding="utf-8"))
marks = {(r["Q"], int(r["No"])): r for r in csv.DictReader(open(os.path.join(results, "llm_marks.csv"), encoding="utf-8"))}
VERSIONS = ["A today", "B no repeats", "C rewrite", "E no multiplier", "F merged", "S site shown", "M mine top 6"]


def shown(row, v):
    rk = row["variants"].get(v)
    return rk is not None and (True if v.startswith(("S", "M")) else rk <= 5)


def table(kind=None):
    print(f"{'version':16} questions | consensus Yes somewhere in what it showed | a consensus-Misleading passage | Yes share, disagreements dropped (the reader's figure) | Yes share, disagreements count as not Yes")
    for v in VERSIONS:
        nq = hy = hm = 0
        sh, sh_low = [], []
        for Q in pool:
            if kind and Q["kind"] != kind:
                continue
            rows = [r for r in Q["rows"] if shown(r, v)]
            if not rows:
                continue
            cons = [marks[(Q["qid"], r["n"])]["consensus"] for r in rows]
            nq, hy, hm = nq + 1, hy + ("Yes" in cons), hm + ("Misleading" in cons)
            agreed = [c for c in cons if c != "split"]
            if agreed:
                sh.append(cons.count("Yes") / len(agreed))
            sh_low.append(cons.count("Yes") / len(cons))
        if nq:
            print(f"{v:16} {nq:9d} | {hy:2d} | {hm:2d} | {sum(sh) / len(sh):.2f} | {sum(sh_low) / len(sh_low):.2f}")


print("ALL 12 QUESTIONS"); table()
print("\nPLAIN-LANGUAGE QUESTIONS ONLY"); table("lay")
print("\nLEGAL-WORDING QUESTIONS ONLY"); table("legal")
S = [(Q["qid"], r) for Q in pool for r in Q["rows"] if "S site shown" in r["variants"]]
top = [(Q["qid"], r) for Q in pool for r in Q["rows"] if r.get("topup")]
print("\nthe 24 passages only the site's method showed:", dict(collections.Counter(marks[(q, r["n"])]["consensus"] for q, r in top)))
print("site-shown passages outside today's top 5:", dict(collections.Counter(marks[(q, r["n"])]["consensus"] for q, r in S if not shown(r, "A today"))))
print("\nCONSENSUS-MISLEADING PASSAGES")
for (qid, n), r in sorted(marks.items()):
    if r["consensus"] == "Misleading":
        Q = next(q for q in pool if q["qid"] == qid)
        row = next(x for x in Q["rows"] if x["n"] == n)
        print(f"{qid} ({Q['kind']}) no.{n} doc {row['doc']} shown by {sorted(row['variants'])}\n    {re.sub(chr(92) + 's+', ' ', row['text'])[:240]}")
