"""Saves, for each tuning question, the whole ranking of version A over its 60 candidates: fused (pre-re-ranker) position, the re-ranker's score, the passage-type weight (with the section boost), the final score
(score times weight) and the final rank 1..60. This is what the safety net uses to rank its passages by the user's question; here it is saved so that one can see where any passage lands when it is simply ranked
by the rules already set. Re-runs the retrieval and ONE re-ranker call per question (about 0.5 million tokens for the 19, about $0.03; the cap below refuses more). Checks the rerun against the recorded run:
version A's recorded top 10 must come out in the same order. No key is read. Writes a_scores.json next to this file. PRIVATE."""
import json, os, sys
ROOT = "/home/user/recourse-sci-pool"
sys.path.insert(0, ROOT); sys.path.insert(0, ROOT + "/review_tools")
import pool_runner as P
import real_questions as RQ
import sci_index as si

OUT = os.path.dirname(os.path.abspath(__file__))
CAP = 1_500_000
real = RQ.load(ROOT + "/review_data/ruler/real30_v1.json")
pool_doc = json.load(open(ROOT + "/review_results/2026-10-09_real30_pool_dev/pool.json"))
pool = {q["qid"]: q for q in pool_doc["questions"]}
head = P.index_head(P.DEFAULT_INDEX)
assert head == pool_doc["run"]["index_commit"], f"index at {head[:7]}, pool made on {pool_doc['run']['index_commit'][:7]}"
metas, M, _ = si._load_index(P.DEFAULT_INDEX)
fts = P.build_fts(metas)
spend = P.Spend(CAP)
eng = P.Engine(metas, M, si.make_client(), spend, fts)

res, repro = {}, {}
for q in real["questions"]:
    if q["half"] != "dev":
        continue
    qid = q["id"]
    a = eng.retrieve(q["text"])
    rs = eng.rerank(q["text"], a["cand"])
    rows = []
    for pos, r in enumerate(a["cand"], 1):
        w = eng.weight(r, a["nums"])
        rows.append({"fused_pos": pos, "h": metas[r]["h"], "doc": metas[r]["doc"], "rerank_score": round(float(rs[r]), 6), "weight": round(float(w), 4), "final_score": round(float(rs[r] * w), 6)})
    order = sorted(range(len(rows)), key=lambda i: (-rows[i]["final_score"], i))
    for rank, i in enumerate(order, 1):
        rows[i]["final_rank"] = rank
    only = sorted(range(len(rows)), key=lambda i: (-rows[i]["rerank_score"], i))
    for rank, i in enumerate(only, 1):
        rows[i]["rerank_only_rank"] = rank
    mine = [rows[i]["h"] for i in order[:10]]
    recorded = [it["h"] for it in pool[qid]["lists"]["A today"]]
    repro[qid] = {"same_ten_in_the_same_order": mine == recorded, "same_ten_as_a_set": set(mine) == set(recorded), "places_that_differ": sum(1 for x, y in zip(mine, recorded) if x != y)}
    res[qid] = {"candidates": rows}
json.dump({"spend": spend.as_dict(), "index_commit": head, "reproduction": repro, "questions": res}, open(OUT + "/a_scores.json", "w"), indent=1)
print("questions:", len(res), "| spend:", spend.as_dict())
print("reproduction of A's recorded ten:", {k: v["places_that_differ"] for k, v in repro.items()})
