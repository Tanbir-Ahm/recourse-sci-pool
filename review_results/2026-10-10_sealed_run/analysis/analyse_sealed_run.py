#!/usr/bin/env python3
"""A descriptive look at the sealed run, written AFTER score_sealed_run.py had fixed the outcome (stage 2 ran once; key_opened.json).

It changes no rule, no threshold and no outcome. Everything here is exploratory and LLM-judged (ChatGPT and Gemini marks); nothing is a lawyer's.

    python3 -P review_results/2026-10-10_sealed_run/analysis/analyse_sealed_run.py

Reads: pool.json, replies_for_the_reader/, the key entries of the pool's 11 questions only (the key was opened by stage 2). Writes analysis.json next to this file. PRIVATE.
"""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.normpath(os.path.join(HERE, ".."))
ROOT = os.path.normpath(os.path.join(RUN, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "review_tools"))
import ingest_llm_reviews as ing
import real30_lights as RL
import real30_score as RS
import score_rerank_arms as SR
import score_sealed_run as SS

A, R, S = "A today", "R challenger re-ranker", "S site shown"
GRADE = SS.GRADE

pool, passages = ing.load_pool(os.path.join(RUN, "pool.json"))
runs, _, _ = ing.load_replies(os.path.join(RUN, "replies_for_the_reader"), passages, pool)
settle = SR.settle_funcs(runs)
LO, HI = SS.BOTH
key = json.load(open(os.path.join(ROOT, "review_data", "ruler", "real30_key_v1.json")))
kq = {q["qid"]: key["questions"][q["qid"]] for q in pool}          # only the 11 questions of this pool
del key
chat = next(v for k, v in runs.items() if k[0] == "ChatGPT")
gem = next(v for k, v in runs.items() if k[0] == "Gemini")
out = {}

# 1. the two judges
pairs = [(chat[p], gem[p]) for p in sorted(passages)]
cm = collections.Counter(pairs)
marks = ["Yes", "Partly", "No", "Misleading"]
agree = sum(a == b for a, b in pairs) / len(pairs)
pa = {m: sum(a == m for a, _ in pairs) / len(pairs) for m in marks}
pb = {m: sum(b == m for _, b in pairs) / len(pairs) for m in marks}
pe = sum(pa[m] * pb[m] for m in marks)
out["judges"] = {"passages": len(pairs), "exact_agreement": agree, "kappa": (agree - pe) / (1 - pe),
                 "ChatGPT_share": pa, "Gemini_share": pb, "confusion_chatgpt_rows_gemini_cols": {a: {b: cm[(a, b)] for b in marks} for a in marks},
                 "agree_on_useful_vs_not": sum((a in ("Yes", "Partly")) == (b in ("Yes", "Partly")) for a, b in pairs) / len(pairs),
                 "chatgpt_misleading_gemini_not": sum(a == "Misleading" and b != "Misleading" for a, b in pairs), "gemini_misleading_chatgpt_not": sum(b == "Misleading" and a != "Misleading" for a, b in pairs),
                 "both_misleading": cm[("Misleading", "Misleading")]}

# 2. per question
per_q = {}
for q in pool:
    qid = q["qid"]
    k = kq[qid]
    wanted = set(k["key_docs"])
    row = {"domain": q["domain"], "question": q["question"], "answerable": bool(k["reachable"] is True and q["domain"] != "K"), "key_authority": [a["label"] for a in k["authorities"] if a.get("role") == "key"][:2],
           "stale_rulings": [x["label"] if "label" in x else x["doc"] for x in k["stale_docs"] if x["counts_as_stale"]], "passages": len(q["rows"])}
    for name, v in (("A", A), ("R", R), ("S", S)):
        items = q["lists"].get(v) or []
        row[name] = {"key_rank": RS.first_rank(items, wanted) if wanted else None}
        for sname, f in ((LO, settle[LO]), (HI, settle[HI])):
            st = SS.stats(q, v, f)
            row[name][sname] = None if st is None else {k2: round(st[k2], 3) for k2 in ("yes", "useful", "mis", "grade")}
        stale = {x["doc"] for x in k["stale_docs"] if x["counts_as_stale"]}
        row[name]["stale_in_top5"] = len([it for it in items[:5] if ({it["doc"], *it.get("also", [])} & stale)])
    a5 = {r["h"] for r in RL.slots(q, A)}
    r5 = {r["h"] for r in RL.slots(q, R)}
    row["top5_overlap_A_R"] = len(a5 & r5)
    per_q[qid] = row
out["per_question"] = per_q

# 3. Misleading passages in the top 5 of A or R (either tool), with both reasons
mis = []
reason = {}
for (tool, order), r_ in runs.items():
    pass
import re
for f in sorted(os.listdir(os.path.join(RUN, "replies_for_the_reader"))):
    d = json.load(open(os.path.join(RUN, "replies_for_the_reader", f), encoding="utf-8"))
    qid, tool = f.split("_")[0], f.split("_")[2].split(".")[0]
    for m in d["marks"]:
        reason[(tool, qid, m["no"])] = (m["mark"], m["reason"])
for q in pool:
    for r in q["rows"]:
        for name, v in (("A", A), ("R", R)):
            if v in r["variants"] and r["variants"][v] <= 5:
                c, g = reason[("ChatGPT", q["qid"], r["n"])], reason[("Gemini", q["qid"], r["n"])]
                if "Misleading" in (c[0], g[0]):
                    mis.append({"qid": q["qid"], "arm": name, "rank": r["variants"][v], "title": r["title"], "chatgpt": c[0], "gemini": g[0], "chatgpt_reason": c[1], "gemini_reason": g[1], "in_other_arm_top5": (R if name == "A" else A) in r["variants"] and r["variants"][(R if name == "A" else A)] <= 5})
out["misleading_in_top5_either_tool"] = mis

# 4. passages that differ between the arms' top 5 and how they were marked (lower / higher)
diff = {"A_only": collections.Counter(), "R_only": collections.Counter()}
for q in pool:
    a5 = {r["h"]: r for r in RL.slots(q, A)}
    r5 = {r["h"]: r for r in RL.slots(q, R)}
    for tag, own, other in (("A_only", a5, r5), ("R_only", r5, a5)):
        for h, r in own.items():
            if h not in other:
                diff[tag][settle[LO]((q["qid"], r["n"]))] += 1
out["passages_only_in_one_arms_top5_marked_both_lower"] = {k: dict(v) for k, v in diff.items()}

json.dump(out, open(os.path.join(HERE, "analysis.json"), "w"), indent=1, default=list)
print(json.dumps(out["judges"], indent=1))
for qid, r in per_q.items():
    print(f"\n{qid} [{r['domain']}] answerable={r['answerable']} passages={r['passages']} overlap top5={r['top5_overlap_A_R']} key={r['key_authority']} stale={r['stale_rulings']}")
    print("   Q:", r["question"][:150])
    for n in ("A", "R", "S"):
        x = r[n]
        print(f"   {n}: key rank {x['key_rank']}, stale in top5 {x['stale_in_top5']}, lower {x[LO]}, higher {x[HI]}")
print("\nMisleading in top 5 (either tool):", len(mis))
for m in mis:
    print(f"  {m['qid']} {m['arm']}#{m['rank']} {m['title'][:70]} | C:{m['chatgpt']} G:{m['gemini']} | other arm top5: {m['in_other_arm_top5']}\n      C: {m['chatgpt_reason'][:160]}\n      G: {m['gemini_reason'][:160]}")
print("\nonly in one arm's top 5, marks (both, ties lower):", out["passages_only_in_one_arms_top5_marked_both_lower"])
