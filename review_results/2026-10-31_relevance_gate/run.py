import sys, json, re
sys.path.insert(0, "/home/user/recourse"); sys.path.insert(0, "/tmp/claude-0/-home-user-recourse-sci-pool/33686f69-1895-5643-b31d-21bed3d4a6ee/scratchpad/gate")
import semantic_retrieval as SR
from questions import POS, NEG
out = []
def rec(q):
    r = SR.find_relevant_sections(q)
    ms = list(r.get("matches") or []) + list(r.get("judgment_matches") or [])
    ms = [m for m in ms if (m.get("text") or "").strip()]
    docs = [(m.get("text") or "")[:1500] for m in ms]
    scores = {}
    if docs:
        rr = SR.rerank(q, docs)
        if rr:
            for item in rr:
                idx = item.get("index") if isinstance(item, dict) else getattr(item, "index", None)
                sc = item.get("relevance_score", item.get("score")) if isinstance(item, dict) else getattr(item, "relevance_score", None)
                scores[idx] = sc
    rows = []
    for i, m in enumerate(ms):
        rows.append({"type": m.get("type"), "act": m.get("act"), "sec": str(m.get("section_number") or ""), "case": m.get("case_name"), "cos": round(float(m.get("score", 0)), 3), "rr": None if scores.get(i) is None else round(float(scores[i]), 3), "text": (m.get("text") or "")[:80].replace("\n", " ")})
    return {"q": q, "state": r.get("state"), "rows": rows}
for q, exp in POS:
    d = rec(q); d["exp"] = {k: sorted(v) for k, v in exp.items()}; d["kind"] = "pos"; out.append(d)
for q in NEG:
    d = rec(q); d["kind"] = "neg"; out.append(d)
json.dump(out, open("/tmp/claude-0/-home-user-recourse-sci-pool/33686f69-1895-5643-b31d-21bed3d4a6ee/scratchpad/gate/scores.json", "w"), indent=1)
print("done", len(out))
