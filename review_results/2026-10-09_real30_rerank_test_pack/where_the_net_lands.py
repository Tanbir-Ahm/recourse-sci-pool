"""Where do the passages of the merged top 5 land when they are simply ranked by the user's question under the rules already set (version A: re-ranker score times weights, 60 candidates)?
Uses the saved full ranking (rerank_effect/a_scores.json: one re-ranker call per question, re-run on 2026-10-09 for this) and the first batch's rows; no search, no network, no spend, no key.
Note: a re-run of the re-ranker is not exactly repeatable (10 of 19 lists came back with a neighbouring pair swapped, the top-5 set differed in 4), so ranks here carry about plus or minus one place.
Run: python where_the_net_lands.py  -> where_the_net_lands.json (PRIVATE)."""
import json
import os
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))
POOLDIR = os.path.normpath(os.path.join(HERE, "..", "2026-10-09_real30_pool_dev"))
sc = json.load(open(POOLDIR + "/rerank_effect/a_scores.json"))
fused = json.load(open(POOLDIR + "/rerank_effect/fused_lists.json"))["questions"]
pool = {q["qid"]: q for q in json.load(open(POOLDIR + "/pool.json"))["questions"]}
reach = json.load(open(HERE + "/safety_net_reach.json"))

rank_of = {qid: {c["h"]: c["final_rank"] for c in v["candidates"]} for qid, v in sc["questions"].items()}
groups = {"merged top 5 (all)": [], "merged top 5, never shown to a reviewer": [], "safety net (merged top 5 outside A's ten)": []}
not_found = 0
for qid in sc["questions"]:
    seen = {r["h"] for r in pool[qid]["rows"]}
    a10 = set(fused[qid]["A_top10_h"])
    for h in [it["h"] for it in fused[qid]["fused"][:5]]:
        r = rank_of[qid].get(h)
        if r is None:
            not_found += 1
            continue
        groups["merged top 5 (all)"].append(r)
        if h not in seen:
            groups["merged top 5, never shown to a reviewer"].append(r)
        if h not in a10:
            groups["safety net (merged top 5 outside A's ten)"].append(r)
bands = [("1-10", 1, 10), ("11-15", 11, 15), ("16-20", 16, 20), ("21-30", 21, 30), ("31-60", 31, 60)]
out = {"candidates_per_question": 60, "merged_top5_passages_not_found_in_the_rerun": not_found, "reproduction_of_A_recorded_ten": sc["reproduction"], "groups": {}, "if_the_list_shown_were_simply_A_top_K": {}}
for name, xs in groups.items():
    out["groups"][name] = {"passages": len(xs), "median_rank": statistics.median(xs), **{f"rank_{b}": sum(1 for r in xs if lo <= r <= hi) for b, lo, hi in bands}}
for K in (10, 15, 20, 30):
    out["if_the_list_shown_were_simply_A_top_K"][str(K)] = {name: sum(1 for r in xs if r <= K) for name, xs in groups.items()}
out["named_cases_not_shown_by_A_ten (recorded run)"] = {x["qid"]: x["A_rank"] for x in reach["detail"] if not x["in_A_ten"] and x["A_rank"] is not None}
json.dump(out, open(HERE + "/where_the_net_lands.json", "w"), indent=1)
print(json.dumps(out, indent=1))
