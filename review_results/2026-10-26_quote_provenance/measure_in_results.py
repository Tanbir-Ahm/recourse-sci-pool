"""How many of the passages the real recipe returned (the saved 2026-10-26 comparison on the newer index: 12 landmark questions and 9 spot questions, top 10 each) are numbered outside their
judgment's own sequence (sci_quotes)? The saved rows hold the document and the paragraph label, not the passage id, so a row is matched by (document, label): 'strict' = every passage of that document
with that label is flagged, 'loose' = at least one is. Run: python3 measure_in_results.py INDEX_DIR"""
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import sci_quotes as Q

index_dir = sys.argv[1]
found, stats = Q.build(Q._read_metas(index_dir))
labels = defaultdict(lambda: [0, 0])                         # (doc, label) -> [passages, flagged]
for m in Q._read_metas(index_dir):
    k = (m["doc"], str(m["pn"]))
    labels[k][0] += 1
    if f"{m['doc']}:{m['i']}" in found:
        labels[k][1] += 1

src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "2026-10-26_newer_index_staging", "compare_newer_d8811a9_rows.json")
d = json.load(open(src, encoding="utf-8"))
groups = {"landmark questions": [r for lm in d["landmarks"] for r in lm["rows"]], "spot questions": [r for s in d["spot"] for r in s["results"]]}
out = {"index_commit": d["index_commit"], "stats": stats, "groups": {}}
for name, rows in groups.items():
    strict = loose = numbered = 0
    hits = []
    for r in rows:
        if r.get("para") is None:
            continue
        numbered += 1
        n, f = labels.get((r["doc"], str(r["para"])), [0, 0])
        if n and f == n:
            strict += 1
        if f:
            loose += 1
            hits.append({"doc": r["doc"], "case": r["case"], "para": r["para"], "same_label_passages": n, "flagged": f})
    out["groups"][name] = {"rows": len(rows), "numbered": numbered, "flagged_strict": strict, "flagged_loose": loose, "hits": hits}
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "in_results.json"), "w"), indent=1)
for k, v in out["groups"].items():
    print(k, {x: v[x] for x in ("rows", "numbered", "flagged_strict", "flagged_loose")})
    for h in v["hits"]:
        print("   ", h)
