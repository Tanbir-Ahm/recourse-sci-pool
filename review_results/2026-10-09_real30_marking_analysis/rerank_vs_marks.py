"""Lines the re-ranker up against the reviewers' marks (all marks are LLM-judged: ChatGPT and Gemini; no lawyer). PRIVATE. Run: python rerank_vs_marks.py   (no network, no spend)

Inputs: ../2026-10-09_real30_pool_dev/rerank_effect/fused_lists.json (the 60 candidates of each question in the order they have BEFORE the re-ranker, saved by save_fused_lists.py), the pool, the normalised replies.
Question answered: what did the re-ranker change, and do the marks say that what it put in the top 5 is better than what it left out?  The honest limit is built in: a passage that no version ever showed to the
reviewers has no mark, so the 'without the re-ranker' top 5 can only be scored on the passages that happened to be shown by some version.

Definitions
  fused top 5      = the five passages with the best merged (fused) rank before the re-ranker = "the search without the re-ranker".
  A's top 5        = version A as run: after the re-ranker, the passage-type weights and the section boost.
  kept             = a passage of A's top 5 that was already in the fused top 5.  promoted = one that came from the fused positions 6 to 60.
  pushed out       = a passage of the fused top 5 that is not in A's top 5.
  mark settlement  = 'cautious' (ties to the lower mark), 'generous' (ties to the higher mark), 'agreed' (ties dropped), or one tool alone.
"""
import collections, json, os, re, sys
ROOT = "/home/user/recourse-sci-pool"
sys.path.insert(0, ROOT + "/review_tools")
import ingest_llm_reviews as ing

HERE = os.path.dirname(os.path.abspath(__file__))
POOLF = ROOT + "/review_results/2026-10-09_real30_pool_dev/pool.json"
FUSED = json.load(open(ROOT + "/review_results/2026-10-09_real30_pool_dev/rerank_effect/fused_lists.json"))
pool, passages = ing.load_pool(POOLF)
runs, problems, ev = ing.load_replies(HERE + "/replies_for_the_reader", passages, pool)
poolq = {q["qid"]: q for q in pool}
row_by_h = {qid: {r["h"]: r for r in q["rows"]} for qid, q in poolq.items()}
votes = {p: [runs[k][p] for k in sorted(runs) if p in runs[k]] for p in passages}

def agreed(p):
    c = collections.Counter(votes[p]).most_common()
    return None if not c or (len(c) > 1 and c[0][1] == c[1][1]) else c[0][0]
SETTLE = {"cautious": lambda p: ing._resolve(votes[p], min), "generous": lambda p: ing._resolve(votes[p], max), "agreed": agreed,
          "ChatGPT": lambda p: runs[("ChatGPT", "A")].get(p), "Gemini": lambda p: runs[("Gemini", "A")].get(p)}

def mark_of(qid, h, how):
    r = row_by_h[qid].get(h)
    return None if r is None else SETTLE[how]((qid, r["n"]))

def shares(marks):
    j = [m for m in marks if m is not None]
    if not j:
        return None
    n = len(j)
    return {"n": n, "yes": sum(m == "Yes" for m in j) / n, "useful": sum(m in ("Yes", "Partly") for m in j) / n, "mis": sum(m == "Misleading" for m in j) / n}

out = {"note": "LLM-judged; the fused top 5 can be scored only on the passages some version showed to the reviewers"}
Q = sorted(FUSED["questions"])
out["questions_used"] = Q

# ---- 1. every passage of every fused top 5: what became of it, and was it marked?
acct = []
for qid in Q:
    fq = FUSED["questions"][qid]
    a_top = fq["A_top10_h"]
    for it in fq["fused"][:5]:
        h = it["h"]
        a_rank = a_top.index(h) + 1 if h in a_top else None
        fate = "in A's top 5" if a_rank and a_rank <= 5 else "in A's places 6 to 10" if a_rank else "outside A's top 10"
        acct.append({"qid": qid, "fused_pos": it["pos"], "a_rank": a_rank, "fate": fate, "marked": h in row_by_h[qid],
                     **{how: mark_of(qid, h, how) for how in SETTLE}})
fates = collections.OrderedDict((f, [a for a in acct if a["fate"] == f]) for f in ("in A's top 5", "in A's places 6 to 10", "outside A's top 10"))
out["fused_top5_accounting"] = {"passages": len(acct),
    "by_fate": {f: {"passages": len(v), "marked": sum(a["marked"] for a in v), "never_shown_to_reviewers": sum(not a["marked"] for a in v)} for f, v in fates.items()},
    "marks_of_those_that_were_marked": {f: {how: shares([a[how] for a in v if a["marked"]]) for how in ("cautious", "generous", "agreed", "ChatGPT", "Gemini")} for f, v in fates.items()}}

# ---- 2. A's top 5 by where each passage stood before the re-ranker
bands = [("kept: fused 1 to 5", 1, 5), ("promoted from fused 6 to 10", 6, 10), ("promoted from fused 11 to 20", 11, 20), ("promoted from fused 21 to 60", 21, 60)]
a_items = []
for qid in Q:
    fq = FUSED["questions"][qid]
    for rk, (h, fp) in enumerate(zip(fq["A_top10_h"][:5], fq["A_top10_fused_positions"][:5]), 1):
        a_items.append({"qid": qid, "a_rank": rk, "fused_pos": fp, "marked": h in row_by_h[qid], **{how: mark_of(qid, h, how) for how in SETTLE}})
out["A_top5_by_fused_position"] = {}
for name, lo, hi in bands:
    sel = [a for a in a_items if a["fused_pos"] is not None and lo <= a["fused_pos"] <= hi]
    out["A_top5_by_fused_position"][name] = {"passages": len(sel), **{how: shares([a[how] for a in sel]) for how in ("cautious", "generous", "agreed", "ChatGPT", "Gemini")}}
kept = [a for a in a_items if a["fused_pos"] is not None and a["fused_pos"] <= 5]
prom = [a for a in a_items if a["fused_pos"] is not None and a["fused_pos"] > 5]
out["A_top5_kept_vs_promoted"] = {"kept": {"passages": len(kept), **{how: shares([a[how] for a in kept]) for how in SETTLE}}, "promoted": {"passages": len(prom), **{how: shares([a[how] for a in prom]) for how in SETTLE}}}

# ---- 3. the questions where all five passages of the fused top 5 were marked: score the search without the re-ranker against A, question by question
cc = []
for qid in Q:
    fq = FUSED["questions"][qid]
    hs = [it["h"] for it in fq["fused"][:5]]
    if all(h in row_by_h[qid] for h in hs):
        row = {"qid": qid, "kind": poolq[qid]["kind"], "fused_top5_in_A_top5": sum(h in fq["A_top10_h"][:5] for h in hs)}
        for how in ("cautious", "generous"):
            f5 = shares([mark_of(qid, h, how) for h in hs])
            a5 = shares([mark_of(qid, h, how) for h in fq["A_top10_h"][:5]])
            row[how] = {"fused": f5, "A": a5}
        cc.append(row)
out["questions_where_the_fused_top5_is_fully_marked"] = {"count": len(cc), "detail": cc}
def avg(rows, how, side, key):
    vals = [r[how][side][key] for r in rows if r[how][side]]
    return sum(vals) / len(vals) if vals else None
out["questions_where_the_fused_top5_is_fully_marked"]["averages"] = {how: {side: {k: avg(cc, how, side, k) for k in ("yes", "useful", "mis")} for side in ("fused", "A")} for how in ("cautious", "generous")}

# ---- 4. bounds for the whole fused top 5 when the passages nobody showed are unknown (per question, then averaged): all unknown = No, and all unknown = Yes
bounds = {}
for how in ("cautious", "generous"):
    lo_yes, hi_yes, lo_use, hi_use, a_yes, a_use = [], [], [], [], [], []
    for qid in Q:
        fq = FUSED["questions"][qid]
        ms = [mark_of(qid, it["h"], how) for it in fq["fused"][:5]]
        known_yes, known_use, unknown = sum(m == "Yes" for m in ms if m), sum(m in ("Yes", "Partly") for m in ms if m), sum(m is None for m in ms)
        lo_yes.append(known_yes / 5); hi_yes.append((known_yes + unknown) / 5); lo_use.append(known_use / 5); hi_use.append((known_use + unknown) / 5)
        am = [mark_of(qid, h, how) for h in fq["A_top10_h"][:5]]
        a_yes.append(sum(m == "Yes" for m in am if m) / max(1, sum(m is not None for m in am))); a_use.append(sum(m in ("Yes", "Partly") for m in am if m) / max(1, sum(m is not None for m in am)))
    m_ = lambda v: sum(v) / len(v)
    bounds[how] = {"fused_top5_yes_between": [m_(lo_yes), m_(hi_yes)], "fused_top5_useful_between": [m_(lo_use), m_(hi_use)], "A_top5_yes": m_(a_yes), "A_top5_useful": m_(a_use)}
out["fused_top5_bounds_if_the_unmarked_are_all_No_or_all_Yes"] = bounds

# ---- 5. what the re-ranker did to the position of the passages the reviewers liked: average fused position of Yes passages in A's top 5 versus all of A's top 5
yes_pos = [a["fused_pos"] for a in a_items if a["cautious"] == "Yes" and a["fused_pos"]]
no_pos = [a["fused_pos"] for a in a_items if a["cautious"] in ("No", "Misleading") and a["fused_pos"]]
out["fused_position_of_A_top5_passages"] = {"Yes (cautious)": {"n": len(yes_pos), "median": sorted(yes_pos)[len(yes_pos) // 2], "share_from_beyond_fused_top5": sum(p > 5 for p in yes_pos) / len(yes_pos)},
                                             "No or Misleading (cautious)": {"n": len(no_pos), "median": sorted(no_pos)[len(no_pos) // 2], "share_from_beyond_fused_top5": sum(p > 5 for p in no_pos) / len(no_pos)}}

# ---- 6. the first result: where did it stand before the re-ranker, and how was it marked?
first = []
for qid in Q:
    fq = FUSED["questions"][qid]
    h, fp = fq["A_top10_h"][0], fq["A_top10_fused_positions"][0]
    first.append({"qid": qid, "fused_pos": fp, "cautious": mark_of(qid, h, "cautious"), "generous": mark_of(qid, h, "generous")})
out["A_first_result"] = {"was_also_first_before_the_reranker": sum(f["fused_pos"] == 1 for f in first), "was_in_fused_top5": sum(f["fused_pos"] is not None and f["fused_pos"] <= 5 for f in first),
                         "came_from_beyond_fused_top5": sum(f["fused_pos"] is not None and f["fused_pos"] > 5 for f in first), "questions": len(first),
                         "marks_when_it_came_from_beyond_fused_top5": {how: dict(collections.Counter(f[how] for f in first if f["fused_pos"] is not None and f["fused_pos"] > 5)) for how in ("cautious", "generous")},
                         "marks_when_it_was_in_fused_top5": {how: dict(collections.Counter(f[how] for f in first if f["fused_pos"] is not None and f["fused_pos"] <= 5)) for how in ("cautious", "generous")}}

# ---- 7. pushed-out passages that were marked (A's places 6 to 10 and outside A's top 10) against the promoted ones, and a central estimate for the search without the re-ranker
pushed = [a for a in acct if a["fate"] != "in A's top 5" and a["marked"]]
out["pushed_out_and_marked"] = {"passages": len(pushed), **{how: shares([a[how] for a in pushed]) for how in SETTLE}}
out["questions_with_never_shown_fused_top5_passages"] = {"questions": len({a["qid"] for a in acct if not a["marked"]}), "passages": sum(not a["marked"] for a in acct), "of_passages": len(acct)}
est = {}
for how in ("cautious", "generous", "ChatGPT", "Gemini"):
    rate = {}
    for f in ("in A's places 6 to 10", "outside A's top 10"):
        sel = [a for a in acct if a["fate"] == f and a["marked"]]
        pool_sel = sel if sel else pushed
        rate[f] = {"yes": sum(a[how] == "Yes" for a in pool_sel) / len(pool_sel), "useful": sum(a[how] in ("Yes", "Partly") for a in pool_sel) / len(pool_sel)}
    tot = {"yes": 0.0, "useful": 0.0}
    for a in acct:
        if a["fate"] == "in A's top 5":
            tot["yes"] += a[how] == "Yes"; tot["useful"] += a[how] in ("Yes", "Partly")
        elif a["marked"]:
            tot["yes"] += a[how] == "Yes"; tot["useful"] += a[how] in ("Yes", "Partly")
        else:
            tot["yes"] += rate[a["fate"]]["yes"]; tot["useful"] += rate[a["fate"]]["useful"]
    a_all = [a for a in a_items]
    est[how] = {"fused_top5_yes": tot["yes"] / len(acct), "fused_top5_useful": tot["useful"] / len(acct),
                "A_top5_yes": sum(a[how] == "Yes" for a in a_all) / len(a_all), "A_top5_useful": sum(a[how] in ("Yes", "Partly") for a in a_all) / len(a_all)}
out["central_estimate_if_the_never_shown_are_like_the_shown_but_pushed_out"] = est

def rf(x, nd=9):
    if isinstance(x, float):
        return round(x, nd)
    if isinstance(x, dict):
        return {k: rf(v, nd) for k, v in x.items()}
    if isinstance(x, list):
        return [rf(v, nd) for v in x]
    return x
json.dump(rf(out), open(HERE + "/rerank_vs_marks.json", "w"), indent=1, ensure_ascii=False)
print("written", HERE + "/rerank_vs_marks.json")
