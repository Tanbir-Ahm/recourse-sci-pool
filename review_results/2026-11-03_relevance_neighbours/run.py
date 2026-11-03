"""Runs the library retrieval (RELEVANCE_GATE off) and the Voyage re-ranker on the fresh questions and writes scores_fresh.json (one record per question, one row per retrieved passage). Same protocol as ../2026-10-31_relevance_gate/run.py."""
import os, sys, json
os.environ.pop("RELEVANCE_GATE", None)
sys.path.insert(0, "/home/user/recourse")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import semantic_retrieval as SR
from questions_fresh import POS
out = []
for q, exp in POS:
    r = SR.find_relevant_sections(q)
    ms = [m for m in (list(r.get("matches") or []) + list(r.get("judgment_matches") or [])) if (m.get("text") or "").strip()]
    scores = {}
    if ms:
        rr = SR.rerank(q, [(m.get("text") or "")[:1500] for m in ms])
        for item in rr or []:
            idx = item.get("index") if isinstance(item, dict) else getattr(item, "index", None)
            sc = item.get("relevance_score", item.get("score")) if isinstance(item, dict) else getattr(item, "relevance_score", None)
            scores[idx] = sc
    rows = [{"type": m.get("type"), "act": m.get("act"), "sec": str(m.get("section_number") or ""), "case": m.get("case_name"), "cos": round(float(m.get("score", 0)), 3),
             "rr": None if scores.get(i) is None else round(float(scores[i]), 3)} for i, m in enumerate(ms)]
    out.append({"q": q, "state": r.get("state"), "exp": {k: sorted(v) for k, v in exp.items()}, "rows": rows})
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "scores_fresh.json"), "w"), indent=1)
print("done", len(out))
