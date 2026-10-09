"""Which of the three ways of finding passages (meaning, keyword, section number) found the passages that reached the top 5 of versions A and C in the tuning-half pool?
Re-runs only the retrieval step (query embeddings, a few hundred tokens; no re-ranking, nothing sealed) for the 19 tuning-half questions and, for the 12 that have one, the blind rewrite,
and checks each top-5 passage of the saved pool against the three candidate lists. PRIVATE (it reads the pool, which names versions)."""
import json, os, re, sys
import numpy as np
ROOT = "/home/user/recourse-sci-pool"
sys.path.insert(0, ROOT); sys.path.insert(0, ROOT + "/review_tools")
import pool_runner as P
import sci_index as si

OUT = os.path.dirname(os.path.abspath(__file__))
pool = json.load(open(ROOT + "/review_results/2026-10-09_real30_pool_dev/pool.json", encoding="utf-8"))
rewrites = json.load(open(ROOT + "/review_data/ruler/real30_rewrites_v1.json", encoding="utf-8"))["rewrites"]
metas, M, _ = si._load_index(P.DEFAULT_INDEX)
fts = P.build_fts(metas)
spend = P.Spend(10)
eng = P.Engine(metas, M, si.make_client(), spend, fts)


def paths(text):
    qv = eng.embed(text)
    sims = np.concatenate([M[i:i + 50000].astype(np.float32) @ qv for i in range(0, len(M), 50000)])
    sem = [int(i) for i in np.argsort(-sims)[:100]]
    toks = list(dict.fromkeys(t for t in re.findall(r"[A-Za-z0-9]{4,}", text.lower()) if t not in si.STOP))[:12]
    kw = [r[0] for r in fts.execute("select rowid from f where f match ? order by bm25(f) limit 50", (" OR ".join(f'"{t}"' for t in toks),))] if toks else []
    nums = sorted(si.section_numbers(text))
    sc = []
    for n in nums:
        sc += [r[0] for r in fts.execute("select rowid from f where f match ? order by bm25(f) limit 30", (f'"section {n}"',))]
    h = lambda lst: {metas[r]["h"] for r in lst}
    return {"sem": h(sem), "kw": h(kw), "sc": h(sc), "numbers": nums, "n_kw_terms": len(toks), "n_sc": len(sc)}


rows, tot = [], {"A": {}, "C": {}}
for q in pool["questions"]:
    for ver, text in (("A", q["question"]), ("C", q.get("rewrite"))):
        if not text:
            continue
        p = paths(text)
        top = [r for r in q["rows"] if r["variants"].get({"A": "A today", "C": "C rewrite"}[ver], 99) <= 5]
        found = [(r["h"] in p["sem"], r["h"] in p["kw"], r["h"] in p["sc"]) for r in top]
        rec = {"qid": q["qid"], "version": ver, "section_numbers_found_in_the_text": p["numbers"], "keyword_terms": p["n_kw_terms"], "section_search_passages": p["n_sc"], "top5_passages": len(top),
               "by_meaning": sum(f[0] for f in found), "by_keyword": sum(f[1] for f in found), "by_section": sum(f[2] for f in found),
               "meaning_only": sum(1 for f in found if f[0] and not f[1] and not f[2]), "keyword_only": sum(1 for f in found if f[1] and not f[0] and not f[2]), "section_only": sum(1 for f in found if f[2] and not f[0] and not f[1]),
               "found_by_two_or_three_ways": sum(1 for f in found if sum(f) >= 2), "found_by_none_of_the_three_lists": sum(1 for f in found if sum(f) == 0)}
        rows.append(rec)
        for k in ("top5_passages", "by_meaning", "by_keyword", "by_section", "meaning_only", "keyword_only", "section_only", "found_by_two_or_three_ways", "found_by_none_of_the_three_lists"):
            tot[ver][k] = tot[ver].get(k, 0) + rec[k]
        tot[ver]["questions"] = tot[ver].get("questions", 0) + 1
        tot[ver]["questions_where_a_section_number_was_found"] = tot[ver].get("questions_where_a_section_number_was_found", 0) + bool(p["numbers"])
json.dump({"spend": spend.as_dict(), "totals": tot, "per_question": rows}, open(OUT + "/retrieval_paths.json", "w"), indent=1)
for r in rows:
    print(r["qid"], r["version"], "numbers", r["section_numbers_found_in_the_text"], "| top5:", r["top5_passages"], "meaning", r["by_meaning"], "keyword", r["by_keyword"], "section", r["by_section"], "| meaning-only", r["meaning_only"], "keyword-only", r["keyword_only"], "section-only", r["section_only"], "two+", r["found_by_two_or_three_ways"])
print(json.dumps(tot, indent=1))
print("spend", spend.as_dict())
