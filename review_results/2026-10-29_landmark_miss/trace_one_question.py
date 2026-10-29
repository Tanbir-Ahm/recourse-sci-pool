"""Traces ONE question through recipe B (sci_search_service.py) on a loaded index and prints where chosen judgments' passages rank at every stage.

    python3 trace_one_question.py --index-dir DIR --doc 9517 --question "..." [--names ... --side ...] [--out trace.json]

Stages (as in SearchService.retrieve/_rerank/ranked): dense top-100 by meaning, keyword (BM25) top-50, the reciprocal-rank merge, the 60 candidates sent to the re-ranker, the re-ranker's order, the passage-type weights, the final top 10.
Costs about a tenth of a cent (one query embedding and one re-rank call).
"""
import argparse
import json
import os
import re
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import sci_index as si  # noqa: E402
import sci_search_service as ss  # noqa: E402


def trace(svc, q, docs):
    qv = svc._embed(q)
    sims = np.concatenate([svc.M[i:i + 50000].astype(np.float32) @ qv for i in range(0, len(svc.M), 50000)])
    order = np.argsort(-sims)
    dense_rank = {int(rid): r for r, rid in enumerate(order[:5000], 1)}
    sem = [int(i) for i in order[:100]]
    toks = list(dict.fromkeys(t for t in re.findall(r"[A-Za-z0-9]{4,}", q.lower()) if t not in si.STOP))[:12]
    kw = [r[0] for r in svc.fts.execute("select rowid from f where f match ? order by bm25(f) limit 50", (" OR ".join(f'"{t}"' for t in toks),))] if toks else []
    nums = si.section_numbers(q)
    rr = {}
    for lst in (sem, kw):
        for rank, rid in enumerate(lst):
            rr[rid] = rr.get(rid, 0.0) + 1.0 / (60 + rank)
    merged = [r for r, _ in sorted(rr.items(), key=lambda x: -x[1])]
    cand = merged[:60]
    rs = svc._rerank(q, cand)
    final = {r: s * svc._weight(r, nums) for r, s in rs.items()}
    final_sorted = sorted(final.items(), key=lambda x: -x[1])
    rerank_pos = {rid: p for p, (rid, _s) in enumerate(sorted(rs.items(), key=lambda x: -x[1]), 1)}
    final_pos = {rid: p for p, (rid, _s) in enumerate(final_sorted, 1)}
    out = {"question": q, "keyword_terms": toks, "sections": nums, "docs": {}, "top10": [], "n_passages": len(svc.metas)}
    for d in docs:
        rows = [i for i, m in enumerate(svc.metas) if m["doc"] == d]
        info = {"passages": len(rows), "best": []}
        for i in sorted(rows, key=lambda i: -sims[i])[:6]:
            info["best"].append({"row": i, "para": svc.metas[i]["pn"], "type": svc.metas[i]["section"], "sim": round(float(sims[i]), 4), "dense_rank": int((sims > sims[i]).sum()) + 1,
                                 "in_keyword_top50": i in kw, "merged_pos": (merged.index(i) + 1) if i in merged else None, "in_60": i in cand, "rerank_pos": rerank_pos.get(i), "rerank_score": round(float(rs[i]), 4) if i in rs else None,
                                 "final_pos": final_pos.get(i), "text": re.sub(r"\s+", " ", svc.metas[i]["text"])[:260]})
        out["docs"][str(d)] = info
    for rank, (rid, score) in enumerate(final_sorted[:12], 1):
        m = svc.metas[rid]
        nm = svc.names.get(m["doc"]) or {}
        out["top10"].append({"rank": rank, "doc": m["doc"], "name": nm.get("name") or svc.title(m["doc"]), "date": nm.get("date"), "court": ss.court_of(m["doc"], svc.names, svc.src_courts), "para": m["pn"], "type": m["section"],
                             "score": round(float(score), 4), "dense_rank": dense_rank.get(rid), "in_keyword_top50": rid in kw, "text": re.sub(r"\s+", " ", m["text"])[:200]})
    out["dense_top30"] = [{"rank": r, "doc": svc.metas[int(rid)]["doc"], "name": (svc.names.get(svc.metas[int(rid)]["doc"]) or {}).get("name"), "para": svc.metas[int(rid)]["pn"], "sim": round(float(sims[rid]), 4)} for r, rid in enumerate(order[:30], 1)]
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--index-dir", required=True)
    ap.add_argument("--doc", type=int, action="append", required=True)
    ap.add_argument("--question", required=True)
    ap.add_argument("--names", default="names_table/names_table_d8811a9.json.gz")
    ap.add_argument("--side", default=",".join(f"review_data/side_index_d8811a9/2026-10-09_{x}" for x in ("correcting_judgments", "fetched_documents", "fetched_shivangi_bansal")))
    ap.add_argument("--out")
    a = ap.parse_args()
    os.environ["SCI_NAMES_TABLE"] = a.names
    svc = ss.SearchService.load(a.index_dir, [s for s in a.side.split(",") if s])
    res = trace(svc, a.question, a.doc)
    print(json.dumps({k: v for k, v in res.items() if k not in ("docs", "top10", "dense_top30")}, indent=1))
    for d, info in res["docs"].items():
        print(f"\n== doc {d}: {info['passages']} passages; its 6 best by meaning")
        for b in info["best"]:
            print(f"  para {b['para']!s:>5} type={b['type']:<8} sim={b['sim']} dense_rank={b['dense_rank']:>6} kw50={b['in_keyword_top50']} merged_pos={b['merged_pos']} in60={b['in_60']} rerank_pos={b['rerank_pos']} final_pos={b['final_pos']}\n      {b['text']}")
    print("\n== final top 12")
    for t in res["top10"]:
        print(f"  {t['rank']:>2}. doc {t['doc']} {t['name'][:60]!s:<60} {t['date']} {t['court'][:14]:<14} para {t['para']!s:>4} dense_rank={t['dense_rank']} kw={t['in_keyword_top50']} score={t['score']}")
    if a.out:
        json.dump(res, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
