#!/usr/bin/env python3
"""A PRE-FREEZE LOOK at the candidate-pool change W and two alternatives, on questions that are already used (tuning 19 + sealed 11). Descriptive; it tunes nothing and proves nothing.

    python3 -P review_results/2026-10-10_wide_pool_look/wide_pool_look.py

For each question one retrieval (as Engine.retrieve builds it, nothing changed) and ONE rerank-3-lite call over the union of the candidates of all arms; every arm's list is then cut from the same scores
(a cross-encoder scores each passage on its own, so this equals separate calls [Likely]; the baseline is checked against the sealed run's saved lists). Arms, all with the recipe's passage-type weights and
section boost:
  B   fused top 60 (today)
  W   fused top 100
  Wd  fused top 100, passages from fused places 61 to 100 multiplied by 0.90 ("late entries must earn their place")
  L   fused top 60 plus the 15 best by meaning that are not already in it ("a lane for the meaning list")
  J   "case first": fused top 60 plus the 3 best-by-meaning passages of each of the 10 judgments with the highest summed 1/(60+rank) over the meaning list's top 300 (at most 30 extra); parameters fixed
      in advance (10 judgments, 3 passages, 300 deep), not tuned on any question
Reports, per arm against B: passages that change in the top 5 and top 10, where the entering passages came from, the named authority and known-stale counts, and the marks that entering passages
already have in the sealed pool (the only marked pool in one numbering). Spend: a few cents. PRIVATE.
"""
import collections
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "review_tools"))
sys.path.insert(0, ROOT)
import numpy as np
import ingest_llm_reviews as ing
import pool_runner as PR
import score_rerank_arms as SR
import sci_index as si

CH = "rerank-3-lite"
SEALED = os.path.join(ROOT, "review_results", "2026-10-10_sealed_run")
TUNING = os.path.join(ROOT, "review_results", "2026-10-10_real30_rerank_test_pack_v2", "pool_with_rerank_arms.json")
LANE, DISCOUNT = 15, 0.90

sealed_pool, sealed_passages = ing.load_pool(os.path.join(SEALED, "pool.json"))
runs, _, _ = ing.load_replies(os.path.join(SEALED, "replies_for_the_reader"), sealed_passages, sealed_pool)
settle = SR.settle_funcs(runs)
LO, HI = [k for k in settle if k.startswith("both")]
tun = json.load(open(TUNING, encoding="utf-8"))["questions"]
questions = {q["qid"]: q["question"] for q in tun}
questions.update({q["qid"]: q["question"] for q in sealed_pool})
sealed_ids = {q["qid"] for q in sealed_pool}
marks = {}                                              # (qid, passage hash) -> (lower, higher) for the sealed questions
for q in sealed_pool:
    for r in q["rows"]:
        marks[(q["qid"], r["h"])] = (settle[LO]((q["qid"], r["n"])), settle[HI]((q["qid"], r["n"])))
saved_R = {q["qid"]: [it["h"] for it in q["lists"]["R challenger re-ranker"][:5]] for q in sealed_pool}
key = json.load(open(os.path.join(ROOT, "review_data", "ruler", "real30_key_v1.json")))["questions"]
kq = {q: key[q] for q in questions}
del key

head = PR.index_head(PR.DEFAULT_INDEX)
metas, M, _ = si._load_index(PR.DEFAULT_INDEX)
for d in PR.FINAL_SIDE_INDEXES:
    metas, M, _, _ = PR.load_supplement(os.path.join(ROOT, d), metas, M, head)
spend = PR.Spend(8_000_000)
eng = PR.Engine(metas, M, si.make_client(), spend, PR.build_fts(metas), None)
H = lambda r: metas[r]["h"]
doc_idx = collections.defaultdict(list)
for _i, _m in enumerate(metas):
    doc_idx[_m["doc"]].append(_i)
J_DOCS, J_PER, J_DEEP = 10, 3, 300


def retrieve_all(q):
    """The same three lists and fusion as Engine.retrieve, returning the whole fused order and the meaning list."""
    qv = eng.embed(q)
    sims = np.concatenate([M[i:i + 50000].astype(np.float32) @ qv for i in range(0, len(M), 50000)])
    order = np.argsort(-sims)
    sem = [int(i) for i in order[:100]]
    deep = [int(i) for i in order[:J_DEEP]]
    toks = list(dict.fromkeys(t for t in re.findall(r"[A-Za-z0-9]{4,}", q.lower()) if t not in si.STOP))[:12]
    kw = [r[0] for r in eng.fts.execute("select rowid from f where f match ? order by bm25(f) limit 50", (" OR ".join(f'"{t}"' for t in toks),))] if toks else []
    nums = si.section_numbers(q)
    sc = []
    for n in nums:
        sc += [r[0] for r in eng.fts.execute("select rowid from f where f match ? order by bm25(f) limit 30", (f'"section {n}"',))]
    rr = {}
    for lst in (sem, kw, sc):
        for rank, rid in enumerate(lst):
            rr[rid] = rr.get(rid, 0.0) + 1.0 / (60 + rank)
    return [r for r, _ in sorted(rr.items(), key=lambda x: -x[1])], sem, nums, deep, sims


summary = collections.defaultdict(lambda: collections.defaultdict(list))
detail = {}
valid = []
for qid in sorted(questions):
    q = questions[qid]
    ranked, sem, nums, deep, sims = retrieve_all(q)
    fused_rank = {r: i for i, r in enumerate(ranked)}
    base_set = ranked[:60]
    lane = [r for r in sem if r not in set(base_set)][:LANE]
    agg = collections.defaultdict(float)
    for rank, rid in enumerate(deep):
        agg[metas[rid]["doc"]] += 1.0 / (60 + rank)
    jextra = []
    for d_ in sorted(agg, key=lambda d: -agg[d])[:J_DOCS]:
        jextra += sorted(doc_idx[d_], key=lambda i: -sims[i])[:J_PER]
    jextra = [r for r in jextra if r not in set(base_set)]
    arms_cand = {"B": base_set, "W": ranked[:100], "Wd": ranked[:100], "L": base_set + lane, "J": base_set + jextra}
    union = list(dict.fromkeys(ranked[:100] + lane + jextra))
    scores = eng.rerank(q, union, model=CH)
    lists = {}
    for arm, cand in arms_cand.items():
        fin = {}
        for r in cand:
            s = scores[r] * eng.weight(r, nums)
            if arm == "Wd" and fused_rank[r] >= 60:
                s *= DISCOUNT
            fin[r] = s
        lists[arm] = eng.order_by(fin)[:10]
    kdocs = set(kq[qid]["key_docs"])
    stale = {x["doc"] for x in kq[qid]["stale_docs"] if x["counts_as_stale"]}
    answerable = kq[qid]["reachable"] is True and not qid.startswith("R30")
    row = {}
    for arm, lst in lists.items():
        t5, t10 = [H(r) for r in lst[:5]], [H(r) for r in lst[:10]]
        b5, b10 = [H(r) for r in lists["B"][:5]], [H(r) for r in lists["B"][:10]]
        enter5 = [r for r in lst[:5] if H(r) not in set(b5)]
        enter10 = [r for r in lst[:10] if H(r) not in set(b10)]
        origin = lambda r: ("case-first extra" if arm == "J" and r in set(jextra) else ("meaning lane" if r in set(lane) and r not in set(ranked[:100]) else ("fused 61-100" if fused_rank.get(r, 999) >= 60 else "fused 1-60")))
        first = next((p + 1 for p, r in enumerate(lst) if metas[r]["doc"] in kdocs), None)
        row[arm] = {"changed_top5": len(enter5), "changed_top10": len(enter10), "entering_top5_origin": [origin(r) for r in enter5], "key_rank_top10": first,
                    "stale_in_top5": sum(1 for r in lst[:5] if metas[r]["doc"] in stale),
                    "entering_top5_marks_(lower,higher)": [marks.get((qid, H(r)), "unmarked") for r in enter5] if qid in sealed_ids else None}
        if answerable:
            summary[arm]["named_top10"].append(first is not None)
            summary[arm]["named_top5"].append(first is not None and first <= 5)
        summary[arm]["changed_top5"].append(len(enter5))
        summary[arm]["changed_top10"].append(len(enter10))
        summary[arm]["stale5"].append(row[arm]["stale_in_top5"])
    if qid in sealed_ids:
        valid.append(qid)
        row["B_matches_sealed_run_R_top5"] = set(H(r) for r in lists["B"][:5]) == set(saved_R[qid])
    detail[qid] = row
    print(f"{qid:4}" + "".join(f"  {a}: top5 +{row[a]['changed_top5']} top10 +{row[a]['changed_top10']} key@{row[a]['key_rank_top10']}" for a in ("W", "Wd", "L", "J")), "| B reproduces the sealed list" if row.get("B_matches_sealed_run_R_top5") else ("| B DIFFERS from sealed list" if qid in sealed_ids else ""))

print("\nSUMMARY over", len(questions), "questions (named authority: answerable questions only)")
tab = {}
for arm in ("B", "W", "Wd", "L", "J"):
    s = summary[arm]
    n = len(s["changed_top5"])
    tab[arm] = {"questions": n, "passages_changing_in_top5_per_question": round(sum(s["changed_top5"]) / n, 2), "questions_with_any_top5_change": sum(1 for x in s["changed_top5"] if x), "passages_changing_in_top10_per_question": round(sum(s["changed_top10"]) / n, 2),
                "named_authority_top5": f"{sum(s['named_top5'])} of {len(s['named_top5'])}", "named_authority_top10": f"{sum(s['named_top10'])} of {len(s['named_top10'])}", "stale_in_top5": sum(s["stale5"])}
    print(arm, tab[arm])
ent = collections.Counter()
mk = collections.Counter()
for qid, row in detail.items():
    for arm in ("W", "Wd", "L", "J"):
        for o in row[arm]["entering_top5_origin"]:
            ent[(arm, o)] += 1
        if row[arm]["entering_top5_marks_(lower,higher)"]:
            for m in row[arm]["entering_top5_marks_(lower,higher)"]:
                mk[(arm, "unmarked" if m == "unmarked" else m[0])] += 1
print("\nwhere the entering top-5 passages come from:", dict(ent))
print("marks (both, ties lower) of entering top-5 passages in the sealed questions:", dict(mk))
print("B reproduces the sealed run's saved top 5 on", sum(1 for q in valid if detail[q]["B_matches_sealed_run_R_top5"]), "of", len(valid), "sealed questions")
print("spend:", spend.as_dict().get("dollars_estimate"), "rerank tokens", spend.rerank)
json.dump({"arms": tab, "detail": detail, "entering_origin": {f"{a}|{o}": n for (a, o), n in ent.items()}, "entering_marks": {f"{a}|{m}": n for (a, m), n in mk.items()}}, open(os.path.join(HERE, "wide_pool_look.json"), "w"), indent=1, default=str)
