"""Runs questions.json (committed in 20fa99f before this file existed) through the REAL search service on the newer index (d8811a9) and reports, for every lead judgment, where its best passage stands at each stage:
dense rank by meaning, keyword top-50, the 60 candidates sent to the re-ranker, the final order WITHOUT the authority step (SCI_AUTHORITY off, recipe B) and WITH it (on). Costs about a cent in all (a query embedding and one or two re-rank calls per question).
  python3 run_retrieval.py --index-dir /home/user/audit_idx/new --names names_table/names_table_d8811a9.json.gz --table authority_table/authority_d8811a9.json.gz --side review_data/side_index_d8811a9/<x> ... --out results.json"""
import argparse
import json
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
os.chdir(ROOT)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index-dir", required=True)
    ap.add_argument("--names", required=True)
    ap.add_argument("--table", required=True)
    ap.add_argument("--side", action="append", default=[])
    ap.add_argument("--out", default=os.path.join(HERE, "results.json"))
    a = ap.parse_args()
    os.environ["SCI_NAMES_TABLE"] = a.names
    import authority_search as AS
    import sci_index as si
    import sci_search_service as ss
    svc = ss.SearchService.load(a.index_dir, a.side)
    tab = AS.AuthorityTable.load(a.table, svc.info.get("index_commit"))
    Q = json.load(open(os.path.join(HERE, "questions.json"), encoding="utf-8"))
    have = {m["doc"] for m in svc.metas}
    out = {"index_commit": svc.info.get("index_commit"), "judgments": svc.info.get("documents"), "authority_params": AS.params_from_env(), "rows": []}
    for q in Q["questions"]:
        leads = {int(d): n for d, n in Q["leads"][q["set"]].items()}
        qv = svc._embed(q["q"])
        sims = np.concatenate([svc.M[i:i + 50000].astype(np.float32) @ qv for i in range(0, len(svc.M), 50000)])
        order = np.argsort(-sims)
        dense_rank = {int(rid): r for r, rid in enumerate(order[:20000], 1)}
        toks = list(dict.fromkeys(t for t in re.findall(r"[A-Za-z0-9]{4,}", q["q"].lower()) if t not in si.STOP))[:12]
        kw = [r[0] for r in svc.fts.execute("select rowid from f where f match ? order by bm25(f) limit 50", (" OR ".join(f'"{t}"' for t in toks),))] if toks else []
        a_ = svc.retrieve(q["q"])
        cand = list(a_["cand"])
        svc.authority = None
        base, _ = svc.ranked_ex(q["q"], k=60)
        svc.authority, svc.auth_params = tab, AS.params_from_env()
        auth, ann = svc.ranked_ex(q["q"], k=60)

        def judgments(ranked):
            seen, lst = set(), []
            for rid, _s in ranked:
                c = tab.cluster_of(svc.metas[rid]["doc"])
                if c not in seen:
                    seen.add(c)
                    lst.append((c, svc.metas[rid]["doc"]))
            return lst

        jb, ja = judgments(base), judgments(auth)
        row = {"id": q["id"], "set": q["set"], "q": q["q"], "top5_without": [(svc.names.get(d) or {}).get("name") for _c, d in jb[:5]], "top5_with": [(svc.names.get(d) or {}).get("name") for _c, d in ja[:5]], "leads": {}}
        for d, name in leads.items():
            if d not in have:
                row["leads"][str(d)] = {"name": name, "in_index": False}
                continue
            rows = [i for i, m in enumerate(svc.metas) if m["doc"] == d]
            best = max(rows, key=lambda i: sims[i])
            cl = tab.cluster_of(d)
            pos = lambda lst: next((p for p, (c, _d) in enumerate(lst, 1) if c == cl), None)
            row["leads"][str(d)] = {"name": name, "in_index": True, "passages": len(rows), "best_dense_rank": dense_rank.get(best), "best_sim": round(float(sims[best]), 3),
                                    "any_in_keyword_top50": any(i in kw for i in rows), "any_in_60_candidates": any(i in cand for i in rows),
                                    "judgment_position_without": pos(jb), "judgment_position_with": pos(ja), "named_by_collection": (tab.cited_by.get(cl) if hasattr(tab, "cited_by") else None)}
        out["rows"].append(row)
        print(q["id"], "done", flush=True)
    json.dump(out, open(a.out, "w"), indent=1, default=str)
    # summary
    for s in ("D", "E"):
        rs = [r for r in out["rows"] if r["set"] == s]
        print(f"\n== set {s}: judgment position among the first 60 passages' judgments (None = not in them)")
        names = list(rs[0]["leads"].items())
        for d, info in names:
            vs = [r["leads"][d] for r in rs]
            if not info.get("in_index"):
                print(f"  {info['name']:42} NOT IN THIS INDEX")
                continue
            print(f"  {info['name']:42} dense best-rank {[v['best_dense_rank'] for v in vs]} | in 60 cand {[v['any_in_60_candidates'] for v in vs]} | pos without {[v['judgment_position_without'] for v in vs]} | with {[v['judgment_position_with'] for v in vs]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
