"""Writes authorities_as_received.json (the table fix_test_set.py reads) from authorities.py, adjudication.py and the stale-ruling decisions, for the file as received 2026-10-12.
The final table (after the writer's replacements and Mr. Advocate's decisions) is made from this one by hand. Private."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from authorities import A
from adjudication import ADJ, STALE
out = []
for q, role, label, toks, year, slack in A:
    st, ds = ADJ[label]
    e = {"qid": q, "role": role, "label": label, "status": st, "docs": ds}
    if role in ("trap_old", "note"):
        hit = next((s for s in STALE.get(q, []) if s[0] == label), None)
        counts = bool(hit[2]) if hit else False
        e["stale"] = {"kind": hit[1] if hit else "narrower or contested", "counts_as_stale": counts and st == "IN"}
    out.append(e)
json.dump(out, open(os.path.join(HERE, "authorities_as_received.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(len(out), "entries;", sum(1 for e in out if e.get("stale", {}).get("counts_as_stale")), "count as stale")
