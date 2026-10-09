"""Why does Q15's search not bring up Shivangi Bansal (2025) although it is now in the library? Reruns version A's retrieval for Q15 over main index + the three side indexes and says, for the passages of
three judgments (Shivangi Bansal 2025, held only in a side index; Social Action Forum 2018; Rajesh Sharma 2017): their best rank by meaning among all passages, whether one is in the 100 nearest, the keyword
top 50 or the section search, whether one is among the 60 candidates, and where the re-ranker puts the best of them (candidates only; if none was a candidate, they are added to the 60 and re-ranked once).
Costs about 4,000 embedding tokens and two re-rank calls (about 1.5 cents). PRIVATE (uses the question file)."""
import json, os, re, sys
import numpy as np
ROOT = "/home/user/recourse-sci-pool"
sys.path.insert(0, ROOT); sys.path.insert(0, ROOT + "/review_tools")
import pool_runner as P
import real_questions as RQ
import sci_index as si

OUT = os.path.dirname(os.path.abspath(__file__))
real = RQ.load(ROOT + "/review_data/ruler/real30_v1.json")
q = [x for x in real["questions"] if x["id"] == "R15"][0]
assert q["half"] == "dev"
metas, M, _ = si._load_index(P.DEFAULT_INDEX)
head = P.index_head(P.DEFAULT_INDEX)
sides = [ROOT + "/review_data/side_index/2026-10-09_correcting_judgments", ROOT + "/review_data/side_index/2026-10-09_fetched_documents", ROOT + "/review_data/side_index/2026-10-09_fetched_shivangi_bansal"]
for d in sides:
    metas, M, _, _ = P.load_supplement(d, metas, M, head)
fts = P.build_fts(metas)
spend = P.Spend(1_000_000)
eng = P.Engine(metas, M, si.make_client(), spend, fts)
text = q["text"]
qv = eng.embed(text)
sims = np.concatenate([M[i:i + 50000].astype(np.float32) @ qv for i in range(0, len(M), 50000)])
order = np.argsort(-sims)
rank_of = np.empty(len(order), dtype=np.int64)
rank_of[order] = np.arange(1, len(order) + 1)
sem = [int(i) for i in order[:100]]
toks = list(dict.fromkeys(t for t in re.findall(r"[A-Za-z0-9]{4,}", text.lower()) if t not in si.STOP))[:12]
kw = [r[0] for r in fts.execute("select rowid from f where f match ? order by bm25(f) limit 50", (" OR ".join(f'"{t}"' for t in toks),))] if toks else []
nums = si.section_numbers(text)
sc = []
for n in nums:
    sc += [r[0] for r in fts.execute("select rowid from f where f match ? order by bm25(f) limit 30", (f'"section {n}"',))]
rr = {}
for lst in (sem, kw, sc):
    for rank, rid in enumerate(lst):
        rr[rid] = rr.get(rid, 0.0) + 1.0 / (60 + rank)
fused = [r for r, _ in sorted(rr.items(), key=lambda x: -x[1])]
cand = fused[:60]
rs = eng.rerank(text, cand)
final = eng.order_by({r: s * eng.weight(r, nums) for r, s in rs.items()})
res = {"question_terms_used_for_keyword_search": toks, "section_numbers_seen": sorted(nums), "authorities": {}}
for name, docs in (("Shivangi Bansal 2025 (side index)", {6000000002}), ("Social Action Forum 2018", {1000250996}), ("Rajesh Sharma 2017", {1000250111})):
    kp = [i for i, m in enumerate(metas) if m["doc"] in docs]
    in_c = [r for r in kp if r in cand]
    best = min(kp, key=lambda r: rank_of[r])
    entry = {"passages_in_library": len(kp), "best_meaning_rank_of_any_passage": int(rank_of[best]), "best_passage": {"pn": metas[best]["pn"], "text_start": metas[best]["text"][:140]},
             "one_in_100_nearest_by_meaning": any(r in sem for r in kp), "one_in_keyword_top50": any(r in kw for r in kp), "one_in_section_search": any(r in sc for r in kp),
             "one_among_60_candidates": bool(in_c), "best_position_in_fused_order": min([fused.index(r) + 1 for r in kp if r in fused] or [None]) if any(r in fused for r in kp) else None,
             "rank_after_reranker_and_weights_if_candidate": min(final.index(r) + 1 for r in in_c) if in_c else None,
             "reranker_score_of_best_candidate": round(max(rs[r] for r in in_c), 3) if in_c else None}
    if not in_c:
        extra = sorted(kp, key=lambda r: rank_of[r])[:8]
        rs2 = eng.rerank(text, cand + extra)
        fin2 = eng.order_by({r: s * eng.weight(r, nums) for r, s in rs2.items()})
        entry["if_added_to_the_60"] = {"passages_added": len(extra), "best_rank_among_68": min(fin2.index(r) + 1 for r in extra), "its_reranker_score": round(max(rs2[r] for r in extra), 3), "score_of_the_5th_result": round(rs2[fin2[4]], 3)}
    res["authorities"][name] = entry
res["spend"] = spend.as_dict()
json.dump(res, open(OUT + "/diagnose_r15.json", "w"), indent=1, ensure_ascii=False)
print(json.dumps(res, indent=1, ensure_ascii=False))
