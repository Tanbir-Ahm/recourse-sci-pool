"""
Why does an expected section not reach the model?  For every question of a set, records for EVERY statute chunk of the library (BNS / BNSS / NI Act / IT Act):
  cosine score and rank by cosine among statute chunks; rank among ALL chunks (statutes + judgments; the search keeps the top 50 of those);
then the Voyage re-ranker scores (rerank-2, same model the relevance gate uses) of the top POOL statute chunks by cosine.
Writes diag_<set>.json.   cwd MUST be /home/user/recourse.   Usage: python3 diagnose.py <questions module> [pool size]
"""
import os, sys, json, importlib
os.environ.pop("RELEVANCE_GATE", None)
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/home/user/recourse"); sys.path.insert(0, here)
sys.path.insert(0, os.path.join(here, "..", "2026-11-03_relevance_neighbours")); sys.path.insert(0, os.path.join(here, "..", "2026-10-31_relevance_gate"))
import semantic_retrieval as SR

qmod = sys.argv[1]
POOL = int(sys.argv[2]) if len(sys.argv) > 2 else 30
qs = importlib.import_module(qmod).POS
N_ALL = 100000
out = []
for item in qs:
    q, exp = item[0], item[1]
    res = SR.semantic_search(q, top_k=N_ALL) or []
    stat = [(i, r) for i, r in enumerate(res) if r["type"] == "statute"]
    rows = []
    for rank_stat, (rank_all, r) in enumerate(stat):
        rows.append({"act": r.get("act"), "sec": str(r.get("section_number")), "cos": round(r["score"], 4), "rank_stat": rank_stat + 1, "rank_all": rank_all + 1})
    pool = [(rk, r) for rk, (ra, r) in enumerate(stat[:POOL])]
    rr = SR.rerank(q, [(r.get("text") or "")[:1500] for _, r in pool]) or []
    rrs = {}
    for item_ in rr:
        idx = item_.get("index") if isinstance(item_, dict) else getattr(item_, "index", None)
        sc = item_.get("score", item_.get("relevance_score")) if isinstance(item_, dict) else getattr(item_, "relevance_score", None)
        rrs[idx] = sc
    for j, (rk, r) in enumerate(pool):
        rows[rk]["rr"] = None if rrs.get(j) is None else round(float(rrs[j]), 4)
    out.append({"q": q, "exp": {k: sorted(v) for k, v in exp.items()}, "kind": item[2] if len(item) > 2 else "", "stat": rows,
                "top_all": [(r.get("type"), r.get("act") or r.get("case_name"), str(r.get("section_number") or ""), round(r["score"], 3)) for r in res[:12]]})
json.dump(out, open(os.path.join(here, f"diag_{qmod}.json"), "w"))
print("done", qmod, len(out))
