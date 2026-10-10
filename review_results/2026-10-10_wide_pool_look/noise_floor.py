"""Noise floor: how many top-5 passages differ between the sealed run's saved rerank-3-lite list and the same recipe run again today (same code, same index, same 60 candidates)? PRIVATE, diagnosis only."""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "review_tools")); sys.path.insert(0, ROOT)
import pool_runner as PR, sci_index as si
pool = {q["qid"]: q for q in json.load(open(os.path.join(ROOT, "review_results/2026-10-10_sealed_run/pool.json")))["questions"]}
head = PR.index_head(PR.DEFAULT_INDEX)
metas, M, _ = si._load_index(PR.DEFAULT_INDEX)
for d in PR.FINAL_SIDE_INDEXES:
    metas, M, _, _ = PR.load_supplement(os.path.join(ROOT, d), metas, M, head)
eng = PR.Engine(metas, M, si.make_client(), PR.Spend(5_000_000), PR.build_fts(metas), None)
H = lambda r: metas[r]["h"]
tot_new = 0; res = {}
for qid, q in pool.items():
    out = eng.lists_for_final(q["question"], "rerank-3-lite")
    today = [H(r) for r in out["R challenger re-ranker"]]
    saved = [it["h"] for it in q["lists"]["R challenger re-ranker"]]
    cand_today = set(eng.retrieve(q["question"])["cand"])
    new5 = len(set(today[:5]) - set(saved[:5])); new10 = len(set(today[:10]) - set(saved[:10]))
    in_saved_10 = len(set(today[:5]) & set(saved[:10]))
    tot_new += new5
    res[qid] = {"top5_passages_that_differ": new5, "top10_passages_that_differ": new10, "today_top5_all_inside_saved_top10": in_saved_10 == 5}
    print(qid, res[qid])
print("total top-5 passages that differ between two runs of the SAME recipe on the same day:", tot_new, "over 11 questions =", round(tot_new / 11, 2), "per question")
json.dump(res, open(os.path.join(HERE, "noise_floor.json"), "w"), indent=1)
