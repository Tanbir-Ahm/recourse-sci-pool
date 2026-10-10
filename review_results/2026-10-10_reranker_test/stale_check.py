"""Known-stale rulings in the top 5 of today's re-ranker (rerank-2) and of rerank-3-lite, and which of them ENTER or LEAVE (offline, no spend, no marks). Tuning half only: the key file is parsed whole and the sealed
entries dropped on the same line, unread. Uses the key's stale list (`stale_docs`: overruled, modified, recalled, replaced by statute, or only narrower or contested) as `real30_score.py` does.
Writes results/stale_check.json."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/user/recourse-sci-pool"
d = json.load(open(os.path.join(HERE, "results", "challenger_rerank3lite_top5.json")))
real = json.load(open(ROOT + "/review_data/ruler/real30_v1.json"))
dev = [q["id"] for q in real["questions"] if q["half"] == "dev"]
key_all = json.load(open(ROOT + "/review_data/ruler/real30_key_v1.json"))["questions"]
key = {q: key_all[q] for q in dev}
del key_all
out, tot = {}, {"baseline_stale_in_top5": 0, "R_stale_in_top5": 0, "stale_entering": 0, "stale_leaving": 0}
for q in d["top5"]:
    stale = {s["doc"]: s for s in key[q]["stale_docs"]}
    base, r = d["baseline_top5"][q], d["top5"][q]
    bh, rh = {x["h"] for x in base}, {x["h"] for x in r}
    flag = lambda items: [{"doc": x["doc"], "label": stale[x["doc"]]["label"], "kind": stale[x["doc"]]["kind"], "counts_as_stale": stale[x["doc"]]["counts_as_stale"], "h": x["h"]} for x in items if x["doc"] in stale]
    entering, leaving = [x for x in r if x["h"] not in bh], [x for x in base if x["h"] not in rh]
    rec = {"baseline_stale_in_top5": flag(base), "R_stale_in_top5": flag(r), "stale_entering": flag(entering), "stale_leaving": flag(leaving)}
    if any(rec.values()):
        out[q] = rec
    for k in tot:
        tot[k] += len(rec[k])
json.dump({"totals": tot, "per_question_with_any": out}, open(os.path.join(HERE, "results", "stale_check.json"), "w"), indent=1)
print(json.dumps(tot), "| questions with any:", {q: {k: [(x['label'], x['kind'], x['counts_as_stale']) for x in v] for k, v in r.items() if v} for q, r in out.items()})
