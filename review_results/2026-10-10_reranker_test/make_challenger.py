"""Writes results/challenger_rerank3lite_top5.json: the top 5 passages (passage hash and judgment, best first) that rerank-3-lite gives (top5), and that rerank-2 gives today (baseline_top5), each of the 14 tuning questions on the saved candidate lists, ordered as
version A orders (score x passage-type weight x section boost). The marking-pack builder reads it (`--challenger`) so that the few passages nobody has marked yet ride along in the deferred marking round.
No network, no spend; reads results/raw_scores.json. The file holds no key information and no mark."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reranker_test as T       # noqa: E402

ARM, MODEL, BASE = "N2", "rerank-3-lite", "C1"
metas, qtext, qids, key_docs, cands, saved = T.load_world()
HERE = os.path.dirname(os.path.abspath(__file__))
raw = json.load(open(os.path.join(HERE, "results", "raw_scores.json")))
top5, base = {}, {}
for q in qids:
    nums = T.si.section_numbers(qtext[q])
    for arm, dest in ((ARM, top5), (BASE, base)):
        sc = {int(r): s for r, s in raw[f"{arm}|{q}"].items()}
        dest[q] = [{"h": metas[r]["h"], "doc": metas[r]["doc"]} for r in T.ordering(metas, cands[q], sc, nums)[:5]]
json.dump({"name": "R challenger re-ranker top 5", "model": MODEL, "run": "reranker_test.py arm N2 (first run; the second run was identical)", "top5": top5, "baseline_top5": base, "baseline": "rerank-2 run today (arm C1; the second run was identical)"}, open(os.path.join(HERE, "results", "challenger_rerank3lite_top5.json"), "w"), indent=1)
print("written;", sum(len(v) for v in top5.values()), "passages for", len(top5), "questions")
