#!/usr/bin/env python3
"""Where does the right passage get lost? A DIAGNOSIS on questions that are already used up (the sealed 11); it proves nothing about any fix and tunes nothing.

    python3 -P review_results/2026-10-10_wrong_regime_diagnosis/diagnose.py [R16 R03 R10 R13 R23]

For each question the key judgment's best passage is followed through the stages of the search: meaning-rank in the whole index, keyword list, "section N" list, the fused order, the 60 candidates, the two
re-rankers (rerank-2, rerank-3-lite), and the final weighted order. An ORACLE step adds the key judgment's best three passages (by meaning) to the 60 candidates and re-ranks again, to see whether the
re-ranker would have put them first had retrieval brought them. Also counts, over the 60 candidates and over the whole index, how many passages mention the Act the question is about and how many mention
its neighbour. Questions come from the saved pool (already handed out); the key entries read are those of the pool's 11 questions (opened by stage 2). Spends a few cents of Voyage calls. PRIVATE.
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
import pool_runner as PR
import sci_index as si

RUN = os.path.join(ROOT, "review_results", "2026-10-10_sealed_run")
QIDS = [a for a in sys.argv[1:]] or ["R16", "R03", "R10", "R13", "R23"]
REGIMES = {                       # (the Act the question is about, a regex for its text) versus the neighbour that crowds it out
    "R16": ("Domestic Violence Act", r"domestic violence", "498A / limitation CrPC", r"498-?A|section 468|section 473|limitation"),
    "R03": ("CrPC arrest duties (41B, 41D, 50A)", r"41-?B|41-?D|50-?A|arrest memo|D\.?K\.? Basu", "NDPS section 50 searches", r"NDPS|narcotic|gazetted officer"),
    "R10": ("NDPS dual role (Mukesh Singh)", r"Mukesh Singh|dual role|informant.{0,40}investigat", "Mohan Lal (overruled)", r"Mohan\s*Lal"),
    "R13": ("settlement quashing, s.482/528", r"482|528|Bhajan Lal|Parbat", "-", r"$^"),
    "R23": ("single blow, s.304 / exception 4", r"single blow|one blow|Exception 4|304", "-", r"$^"),
}

pool = json.load(open(os.path.join(RUN, "pool.json"), encoding="utf-8"))["questions"]
byq = {q["qid"]: q for q in pool}
key = json.load(open(os.path.join(ROOT, "review_data", "ruler", "real30_key_v1.json")))
kq = {q: key["questions"][q] for q in QIDS}
del key

head = PR.index_head(PR.DEFAULT_INDEX)
metas, M, _ = si._load_index(PR.DEFAULT_INDEX)
for d in PR.FINAL_SIDE_INDEXES:
    metas, M, info, extra = PR.load_supplement(os.path.join(ROOT, d), metas, M, head)
fts = PR.build_fts(metas)
spend = PR.Spend(1_000_000)
eng = PR.Engine(metas, M, si.make_client(), spend, fts, None)
doc_of = [m["doc"] for m in metas]
title_of = {}
for m in metas:
    title_of.setdefault(m["doc"], m.get("title") or str(m["doc"]))


def snippet(i, n=170):
    return re.sub(r"\s+", " ", metas[i]["text"][:n])


def short_title(i):
    return (title_of.get(metas[i]["doc"]) or str(metas[i]["doc"]))[:60]


out = {}
# whole-index counts, once
alltext = [m["text"] for m in metas]
for qid in QIDS:
    q = byq[qid]["question"]
    kdocs = set(kq[qid]["key_docs"])
    kidx = [i for i, d in enumerate(doc_of) if d in kdocs]
    res = {"question": q, "key_docs": sorted(kdocs), "key_passages_in_index": len(kidx)}
    qv = eng.embed(q)
    sims = np.concatenate([M[i:i + 50000].astype(np.float32) @ qv for i in range(0, len(M), 50000)])
    order = np.argsort(-sims)
    pos = np.empty(len(order), dtype=np.int64)
    pos[order] = np.arange(len(order))
    best = sorted(kidx, key=lambda i: -sims[i])[:3]
    res["meaning_rank_of_best_key_passage"] = int(pos[best[0]]) + 1 if best else None
    res["meaning_rank_of_top3_key_passages"] = [int(pos[i]) + 1 for i in best]
    res["meaning_top10"] = [{"rank": r + 1, "title": short_title(int(i)), "text": snippet(int(i))} for r, i in enumerate(order[:10])]
    # the three lists and the fusion, as Engine.retrieve builds them
    sem = [int(i) for i in order[:100]]
    toks = list(dict.fromkeys(t for t in re.findall(r"[A-Za-z0-9]{4,}", q.lower()) if t not in si.STOP))[:12]
    kw = [r[0] for r in fts.execute("select rowid from f where f match ? order by bm25(f) limit 50", (" OR ".join(f'"{t}"' for t in toks),))] if toks else []
    nums = si.section_numbers(q)
    sc = []
    for n in nums:
        sc += [r[0] for r in fts.execute("select rowid from f where f match ? order by bm25(f) limit 30", (f'"section {n}"',))]
    rr = {}
    for lst in (sem, kw, sc):
        for rank, rid in enumerate(lst):
            rr[rid] = rr.get(rid, 0.0) + 1.0 / (60 + rank)
    ranked = [r for r, _ in sorted(rr.items(), key=lambda x: -x[1])]
    cand = ranked[:60]
    kset = set(kidx)
    first = lambda lst: next((p + 1 for p, r in enumerate(lst) if r in kset), None)
    res["stages"] = {"keyword_list_(top50)": first(kw), "section_list": first(sc), "section_numbers_read_from_the_question": sorted(nums), "meaning_list_(top100)": first(sem), "fused_order_position": first(ranked), "in_the_60_candidates": first(cand) is not None}
    res["keyword_terms_used"] = toks
    # the Act versus its neighbour among the 60 candidates and the whole index
    lab_a, re_a, lab_b, re_b = REGIMES[qid]
    ra, rb = re.compile(re_a, re.I), re.compile(re_b, re.I)
    res["candidates_60"] = {lab_a: sum(bool(ra.search(metas[r]["text"])) for r in cand), lab_b: sum(bool(rb.search(metas[r]["text"])) for r in cand)}
    if qid == "R16":
        res["whole_index"] = {"passages_mentioning_domestic_violence": sum(bool(ra.search(t)) for t in alltext), "judgments_mentioning_it": len({doc_of[i] for i, t in enumerate(alltext) if ra.search(t)}),
                              "passages_mentioning_498A_or_limitation": sum(bool(rb.search(t)) for t in alltext)}
        res["key_passages_best3"] = [{"meaning_rank": int(pos[i]) + 1, "text": re.sub(r"\s+", " ", metas[i]["text"][:600])} for i in best]
    # the re-rankers on the 60, and the oracle (the key judgment's best three added)
    for model_name, model in (("rerank-2", None), ("rerank-3-lite", "rerank-3-lite")):
        base = eng.rerank(q, cand, model=model)
        fin = {r: s * eng.weight(r, nums) for r, s in base.items()}
        o = eng.order_by(fin)
        raw_o = eng.order_by(base)
        stage = {"top5": [{"title": short_title(r), "regime_a": bool(ra.search(metas[r]["text"])), "regime_b": bool(rb.search(metas[r]["text"]))} for r in o[:5]],
                 "key_position_after_weights": next((p + 1 for p, r in enumerate(o) if r in kset), None), "key_position_raw_score": next((p + 1 for p, r in enumerate(raw_o) if r in kset), None)}
        extra = [i for i in best if i not in set(cand)]
        if extra:
            cand2 = cand + extra
            base2 = eng.rerank(q, cand2, model=model)
            fin2 = {r: s * eng.weight(r, nums) for r, s in base2.items()}
            o2 = eng.order_by(fin2)
            stage["ORACLE_if_retrieval_had_brought_the_key_passages"] = {"added": len(extra), "best_key_position_in_61_to_63": next((p + 1 for p, r in enumerate(o2) if r in kset), None),
                                                                         "key_position_raw_score": next((p + 1 for p, r in enumerate(eng.order_by(base2)) if r in kset), None)}
        res[model_name] = stage
    out[qid] = res
    print(f"\n=== {qid}: {q[:110]}")
    print("   key passages in index:", res["key_passages_in_index"], "| meaning rank of best key passage (of", len(M), "):", res["meaning_rank_of_best_key_passage"], res["meaning_rank_of_top3_key_passages"])
    print("   stages:", res["stages"])
    print("   among the 60 candidates:", res["candidates_60"])
    for mname in ("rerank-2", "rerank-3-lite"):
        s = res[mname]
        print(f"   {mname}: key position (raw / after weights) {s['key_position_raw_score']} / {s['key_position_after_weights']}; top5 regime_a/b:", [(int(x['regime_a']), int(x['regime_b'])) for x in s["top5"]], "oracle:", s.get("ORACLE_if_retrieval_had_brought_the_key_passages"))
    print("   meaning top 3:", [(x["title"], x["text"][:90]) for x in res["meaning_top10"][:3]])
    if "whole_index" in res:
        print("   whole index:", res["whole_index"])
        print("   key passage 1:", res["key_passages_best3"][0]["text"][:500])

out["_spend"] = spend.as_dict()
json.dump(out, open(os.path.join(HERE, "diagnosis.json"), "w"), indent=1, default=str)
print("\nspend:", spend.as_dict()["dollars_estimate"] if "dollars_estimate" in spend.as_dict() else spend.as_dict())
