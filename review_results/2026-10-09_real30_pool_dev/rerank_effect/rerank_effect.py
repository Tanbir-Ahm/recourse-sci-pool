"""What does the re-ranker change? For the 19 tuning questions, version A's search is rerun up to the point where the re-ranker is called: the three searches (100 by meaning, 50 by keyword, up to 30 per
"section N") are merged by reciprocal rank fusion into 60 candidates. That fused order is "the search without the re-ranker". It is compared with version A's real result (from pool.json: after the
re-ranker, the passage-type weights and the section boost). Only the question embeddings are paid for (about 3,000 tokens); the re-ranker is NOT called (the spend cap is zero, so a call would be refused).
Checks first that the rerun reproduces the run: every passage of version A's recorded top 10 must be among the 60 recomputed candidates. Reads the private key. PRIVATE."""
import collections, json, os, sys
ROOT = "/home/user/recourse-sci-pool"
sys.path.insert(0, ROOT); sys.path.insert(0, ROOT + "/review_tools")
import pool_runner as P
import real_questions as RQ
import real30_score as S
import sci_index as si

OUT = os.path.dirname(os.path.abspath(__file__))
real = RQ.load(ROOT + "/review_data/ruler/real30_v1.json")
key = json.load(open(ROOT + "/review_data/ruler/real30_key_v1.json"))["questions"]
pool = {q["qid"]: q for q in json.load(open(ROOT + "/review_results/2026-10-09_real30_pool_dev/pool.json"))["questions"]}
metas, M, _ = si._load_index(P.DEFAULT_INDEX)
fts = P.build_fts(metas)
hdocs = collections.defaultdict(set)
for m in metas:
    hdocs[m["h"]].add(m["doc"])
spend = P.Spend(0)                                   # no re-ranking allowed here
eng = P.Engine(metas, M, si.make_client(), spend, fts)


def item(r):
    return {"doc": metas[r]["doc"], "h": metas[r]["h"], "also": sorted(hdocs[metas[r]["h"]] - {metas[r]["doc"]})}


rows, problems = [], []
for q in real["questions"]:
    if q["half"] != "dev":
        continue
    qid = q["id"]
    a = eng.retrieve(q["text"])
    fused = [item(r) for r in a["cand"]]                              # the 60 candidates, best fused rank first
    final = pool[qid]["lists"]["A today"]                             # version A as run: after the re-ranker, the weights and the section boost
    only = pool[qid]["lists"]["E no multiplier"]                      # version E as run: after the re-ranker alone (no weights, no boost)
    fpos = {it["h"]: i for i, it in enumerate(fused, 1)}
    missing = [it["h"] for it in final + only if it["h"] not in fpos]
    if missing:
        problems.append((qid, len(missing)))
    wanted = set(key[qid]["key_docs"])
    reachable = key[qid]["reachable"]
    top5_f, top5_a = [it["h"] for it in fused[:5]], [it["h"] for it in final[:5]]
    rows.append({"qid": qid, "kind": q["kind"], "reachable": reachable,
                 "key_rank_without_reranker": S.first_rank(fused, wanted) if wanted else None,
                 "key_rank_with_reranker": S.first_rank(final, wanted) if wanted else None,
                 "key_rank_reranker_only_E": S.first_rank(only, wanted) if wanted else None,
                 "top5_in_common_E": len(set(top5_f) & {it["h"] for it in only[:5]}),
                 "final_top5_fused_positions_E": [fpos.get(it["h"]) for it in only[:5]],
                 "top5_in_common": len(set(top5_f) & set(top5_a)),
                 "final_top5_fused_positions": [fpos.get(h) for h in top5_a],
                 "candidates": len(fused)})
res = {"spend": spend.as_dict(), "reproduction_problems": problems, "rows": rows}
bad = {q for q, _ in problems}
use = [r for r in rows if r["qid"] not in bad]
ans = [r for r in use if r["reachable"] is True]


def hit(r, k, which):
    v = r["key_rank_" + which]
    return v is not None and v <= k


summary = {"questions_reproduced": len(use), "questions_not_reproduced": sorted(bad), "answerable_questions": len(ans)}
for k in (1, 5, 10):
    summary[f"key_authority_in_top_{k}_without_reranker"] = sum(hit(r, k, "without_reranker") for r in ans)
    summary[f"key_authority_in_top_{k}_reranker_only_E"] = sum(hit(r, k, "reranker_only_E") for r in ans)
    summary[f"key_authority_in_top_{k}_reranker_with_weights_A"] = sum(hit(r, k, "with_reranker") for r in ans)
for tag, key_c, key_p in (("A", "top5_in_common", "final_top5_fused_positions"), ("E", "top5_in_common_E", "final_top5_fused_positions_E")):
    summary[f"{tag}_avg_top5_passages_in_common_with_the_fused_top5"] = round(sum(r[key_c] for r in use) / len(use), 2)
    summary[f"{tag}_final_top5_passages_total"] = sum(len(r[key_p]) for r in use)
    summary[f"{tag}_final_top5_passages_outside_the_fused_top5"] = sum(len([p for p in r[key_p] if p is None or p > 5]) for r in use)
    summary[f"{tag}_final_top5_passages_outside_the_fused_top10"] = sum(len([p for p in r[key_p] if p is None or p > 10]) for r in use)
    summary[f"{tag}_deepest_fused_position_that_reached_a_final_top5"] = max(p for r in use for p in r[key_p] if p)
res["summary"] = summary
json.dump(res, open(OUT + "/rerank_effect.json", "w"), indent=1)
print(json.dumps(summary, indent=1))
print("reproduction problems:", problems)
for r in rows:
    print(r["qid"], r["kind"][:5], "key rank before / E / A:", r["key_rank_without_reranker"], "/", r["key_rank_reranker_only_E"], "/", r["key_rank_with_reranker"], "| top-5 in common (A)", r["top5_in_common"], "| fused positions of A's top 5:", r["final_top5_fused_positions"])
print("spend", spend.as_dict())
