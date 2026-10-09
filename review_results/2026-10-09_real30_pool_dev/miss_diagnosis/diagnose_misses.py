"""Where was the named key authority lost? For the tuning-half questions whose key authority is not in version A's top 10, rerun A's retrieval and say, for the key judgment's passages:
  1. their best rank by plain meaning among all 236,155 passages (and whether one is in the 100 nearest);
  2. whether one is in the keyword top 50 or the section search;
  3. whether one is among the 60 candidates sent to the re-ranker;
  4. where the re-ranker puts the best of them, among the candidates and (if none was a candidate) when they are added to the 60.
Reads the private key. Tuning-half questions only. Costs a few thousand embedding tokens and about 4 x 2 re-rank calls (a few cents at most). PRIVATE."""
import json, os, re, sys
import numpy as np
ROOT = "/home/user/recourse-sci-pool"
sys.path.insert(0, ROOT); sys.path.insert(0, ROOT + "/review_tools")
import pool_runner as P
import real_questions as RQ
import sci_index as si

OUT = os.path.dirname(os.path.abspath(__file__))
real = RQ.load(ROOT + "/review_data/ruler/real30_v1.json")
key = json.load(open(ROOT + "/review_data/ruler/real30_key_v1.json"))["questions"]
QS = [q for q in real["questions"] if q["id"] in sys.argv[1:]] if len(sys.argv) > 1 else [q for q in real["questions"] if q["id"] in ("R09", "R14", "R20", "R22")]
assert all(q["half"] == "dev" for q in QS), "tuning half only"
metas, M, _ = si._load_index(P.DEFAULT_INDEX)
fts = P.build_fts(metas)
spend = P.Spend(3_000_000)
eng = P.Engine(metas, M, si.make_client(), spend, fts)
res = {}
for q in QS:
    kd = set(key[q["id"]]["key_docs"])
    kp = [i for i, m in enumerate(metas) if m["doc"] in kd]
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
    cand = [r for r, _ in sorted(rr.items(), key=lambda x: -x[1])][:60]
    rs = eng.rerank(text, cand)
    final = eng.order_by({r: s * eng.weight(r, nums) for r, s in rs.items()})
    in_cand = [r for r in kp if r in cand]
    forced = None
    if not in_cand and kp:
        extra = sorted(kp, key=lambda r: rank_of[r])[:8]
        rs2 = eng.rerank(text, cand + extra)
        fin2 = eng.order_by({r: s * eng.weight(r, nums) for r, s in rs2.items()})
        forced = {"key passages added": len(extra), "best key passage rank among 68": min(fin2.index(r) + 1 for r in extra), "its re-ranker score": round(max(rs2[r] for r in extra), 3), "score of the 5th result": round(rs2[fin2[4]], 3)}
    best = min(kp, key=lambda r: rank_of[r]) if kp else None
    res[q["id"]] = {"key_docs": sorted(kd), "key_passages_in_index": len(kp), "best_meaning_rank_of_any_key_passage": int(rank_of[best]) if best is not None else None,
                    "key_passage_in_100_nearest_by_meaning": any(r in sem for r in kp), "key_passage_in_keyword_top50": any(r in kw for r in kp), "key_passage_in_section_search": any(r in sc for r in kp),
                    "key_passage_among_60_candidates": bool(in_cand), "rank_after_rerank_if_candidate": min(final.index(r) + 1 for r in in_cand) if in_cand else None, "if_forced_in": forced,
                    "keyword_terms_used": toks, "section_numbers_seen": sorted(nums)}
    print(q["id"], json.dumps(res[q["id"]], ensure_ascii=False), flush=True)
json.dump({"spend": spend.as_dict(), "results": res}, open(OUT + "/miss_diagnosis.json", "w"), indent=1, ensure_ascii=False)
print("spend", spend.as_dict())
