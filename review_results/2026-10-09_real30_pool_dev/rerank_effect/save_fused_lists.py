"""Saves, for each tuning question, the 60 merged candidates in the order they have BEFORE the re-ranker (the three searches fused), so that they can be lined up against the reviewers' marks (see
review_results/2026-10-09_real30_marking_analysis/rerank_vs_marks.py). Same retrieval as rerank_effect.py; the re-ranker is NOT called (spend cap 0, a call would be refused); only the question embeddings are paid
for (about 1,200 tokens, a few hundredths of a cent). Checks that the rerun reproduces the run: every passage of version A's recorded top 10 must be among the 60 recomputed candidates (Q15 does not; it is left out).
No key is read. Writes fused_lists.json next to this file. PRIVATE."""
import collections, json, os, sys
ROOT = "/home/user/recourse-sci-pool"
sys.path.insert(0, ROOT); sys.path.insert(0, ROOT + "/review_tools")
import pool_runner as P
import real_questions as RQ
import sci_index as si

OUT = os.path.dirname(os.path.abspath(__file__))
real = RQ.load(ROOT + "/review_data/ruler/real30_v1.json")
pool = {q["qid"]: q for q in json.load(open(ROOT + "/review_results/2026-10-09_real30_pool_dev/pool.json"))["questions"]}
metas, M, _ = si._load_index(P.DEFAULT_INDEX)
fts = P.build_fts(metas)
spend = P.Spend(0)                                   # no re-ranking allowed here
eng = P.Engine(metas, M, si.make_client(), spend, fts)

res, problems = {}, []
for q in real["questions"]:
    if q["half"] != "dev":
        continue
    qid = q["id"]
    a = eng.retrieve(q["text"])
    fused = [{"pos": i, "h": metas[r]["h"], "doc": metas[r]["doc"]} for i, r in enumerate(a["cand"], 1)]
    fpos = {it["h"]: it["pos"] for it in fused}
    top10 = [it["h"] for it in pool[qid]["lists"]["A today"]]
    missing = [h for h in top10 if h not in fpos]
    if missing:
        problems.append((qid, len(missing)))
    res[qid] = {"fused": fused, "A_top10_h": top10, "A_top10_fused_positions": [fpos.get(h) for h in top10],
                "E_top10_h": [it["h"] for it in pool[qid]["lists"]["E no multiplier"]], "E_top10_fused_positions": [fpos.get(it["h"]) for it in pool[qid]["lists"]["E no multiplier"]]}
json.dump({"spend": spend.as_dict(), "reproduction_problems": problems, "index_commit": pool and json.load(open(ROOT + "/review_results/2026-10-09_real30_pool_dev/pool.json"))["run"]["index_commit"], "questions": res},
          open(OUT + "/fused_lists.json", "w"), indent=1)
print("questions:", len(res), "| reproduction problems:", problems, "| spend:", spend.as_dict())
