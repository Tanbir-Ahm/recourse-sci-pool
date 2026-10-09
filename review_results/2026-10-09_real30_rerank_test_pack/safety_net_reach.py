"""Which named key authorities does the safety net bring up? For the 14 answerable tuning questions, from what is already saved (no search, no network, no spend, no new read of the key):
  rerank_effect.json  - where the named authority stands in the merged order before the re-ranker ("fused") and in version A's ten after it;
  miss_diagnosis.json - where the re-ranker puts it when it is a candidate but outside A's ten (R09, R20), and what would happen if it were added to the candidates (R14, R22).
The list shown is A's ten followed by the safety net (the merged top 5 that A's ten do not show); wider nets are shown to say what they would reach, not to recommend them: a depth chosen after seeing
which cases were missed proves nothing about new questions. PRIVATE (it uses the tuning half's key through those files). Run: python safety_net_reach.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
POOL = os.path.normpath(os.path.join(HERE, "..", "2026-10-09_real30_pool_dev"))
re_ = json.load(open(POOL + "/rerank_effect/rerank_effect.json"))
dg = json.load(open(POOL + "/miss_diagnosis/miss_diagnosis.json"))["results"]

rows = []
for r in re_["rows"]:
    if r["reachable"] is not True:
        continue
    f, a = r["key_rank_without_reranker"], r["key_rank_with_reranker"]
    d = dg.get(r["qid"], {})
    a_deeper = d.get("rank_after_rerank_if_candidate")           # A's rank when the named case is a candidate but outside A's ten
    rows.append({"qid": r["qid"], "merged_rank": f, "A_rank": a if a is not None else a_deeper, "in_A_top5": a is not None and a <= 5, "in_A_ten": a is not None and a <= 10,
                 "in_ten_plus_net5": (a is not None and a <= 10) or (f is not None and f <= 5)})


def reach(depth):
    return sum(1 for x in rows if x["in_A_ten"] or (x["merged_rank"] is not None and x["merged_rank"] <= depth))


out = {"answerable_questions": len(rows), "A_top5": sum(x["in_A_top5"] for x in rows), "A_ten": sum(x["in_A_ten"] for x in rows), "A_ten_plus_net_of_5": sum(x["in_ten_plus_net5"] for x in rows),
       "A_ten_plus_net_of_10": reach(10), "A_ten_plus_net_of_15": reach(15), "A_ten_plus_net_of_20": reach(20),
       "not_in_the_candidates_at_all": [x["qid"] for x in rows if x["merged_rank"] is None],
       "in_the_candidates_but_not_shown_by_ten_plus_net5": [x["qid"] for x in rows if not x["in_ten_plus_net5"] and x["merged_rank"] is not None],
       "detail": rows,
       "if_added_to_the_candidates": {q: dg[q]["if_forced_in"] for q in ("R14", "R22") if q in dg and dg[q].get("if_forced_in")},
       "best_meaning_rank_of_the_named_case": {q: dg[q]["best_meaning_rank_of_any_key_passage"] for q in dg}}
json.dump(out, open(HERE + "/safety_net_reach.json", "w"), indent=1)
print(json.dumps({k: v for k, v in out.items() if k not in ("detail",)}, indent=1))
for x in rows:
    print(x)
