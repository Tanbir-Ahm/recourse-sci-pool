"""Runs the Recourse site's own judgment search (semantic_retrieval.py, unmodified) over the wide index, for the 12 landmark questions.
Only the site's statute lookups are switched off (the wide index has no statutes). Also runs my own pipeline on the same index for comparison.
Read-only on the index. Costs: 12 x (a few query embeddings) + 12 reranks of 60 passages."""
import json, re, sqlite3, sys, time, resource
import numpy as np

sys.path.insert(0, "/home/user/recourse-sci-pool"); sys.path.insert(0, "/home/user/tanbir-ahm/recourse")
import sci_index as si
import semantic_retrieval as sr

SCR = "/tmp/claude-0/-home-user-recourse-sci-pool/33686f69-1895-5643-b31d-21bed3d4a6ee/scratchpad/cmp"
IDX = "/home/user/recourse-sci-index"
t0 = time.time()
mem = lambda: resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024
log = lambda *a: print(f"[{time.time() - t0:6.0f}s {mem():>5} MB]", *a, flush=True)

metas, M, _ = si._load_index(IDX)
log(f"index loaded: {len(metas):,} passages, {len({m['doc'] for m in metas}):,} judgments")
records = [{"chunk_id": f"{m['doc']}:{m['i']}", "text": m["text"], "type": "judgment", "case_name": str(m["doc"]), "paragraph_number": m["pn"],
            "section_number": None, "doc": m["doc"], "h": m["h"], "tag": m["section"]} for m in metas]
sr._corpus_cache = {"records": records, "matrix": M.astype(np.float32), "model": "voyage-law-2"}
sr._named_section_exact_match = lambda q: None          # statute lookups off: the wide index holds judgments only
sr._section_tables = lambda: {}

lm = json.load(open("/home/user/recourse-sci-pool/landmarks.json", encoding="utf-8"))["landmarks"]
pool = json.load(open(f"{SCR}/pool_raw_v2.json", encoding="utf-8"))
pool_h = {q["question"]: {r["h"] for r in q["rows"]} for q in pool}
pool_qid = {q["question"]: q["qid"] for q in pool}

t = time.time(); sr._build_lexical_index(); log(f"the site's own word-search index built over the wide index in {time.time() - t:.0f}s")

# my own pipeline (as in run_eval) for comparison
client = si.make_client()
fts = sqlite3.connect(":memory:"); fts.execute("create virtual table f using fts5(text, tokenize='porter unicode61')")
fts.executemany("insert into f(rowid, text) values(?,?)", ((i, m["text"]) for i, m in enumerate(metas)))
log("my word-search index built")


def mine(q, qv, L):
    sims = np.concatenate([M[i:i + 50000].astype(np.float32) @ qv for i in range(0, len(M), 50000)])
    sem = [int(i) for i in np.argsort(-sims)[:100]]
    toks = list(dict.fromkeys(t for t in re.findall(r"[A-Za-z0-9]{4,}", q.lower()) if t not in si.STOP))[:12]
    kw = [r[0] for r in fts.execute("select rowid from f where f match ? order by bm25(f) limit 50", (" OR ".join(f'"{t}"' for t in toks),))] if toks else []
    nums = si.section_numbers(q); sc = []
    for n in nums:
        sc += [r[0] for r in fts.execute("select rowid from f where f match ? order by bm25(f) limit 30", (f'"section {n}"',))]
    rr = {}
    for lst in (sem, kw, sc):
        for rank, rid in enumerate(lst):
            rr[rid] = rr.get(rid, 0.0) + 1.0 / (60 + rank)
    cand = [r for r, _ in sorted(rr.items(), key=lambda x: -x[1])][:60]
    resp = client.rerank(q, [metas[r]["text"][:3500] for r in cand], model="rerank-2", top_k=len(cand))
    rs = {cand[x.index]: x.relevance_score for x in resp.results}
    w = lambda rid: si.W.get(metas[rid]["section"], 1.0) * (1.10 if nums and si.has_section(metas[rid]["text"], nums) else 1.0)
    final = [r for r, _ in sorted(((r, s * w(r)) for r, s in rs.items()), key=lambda x: -x[1])]
    return final


out = []
for L in lm:
    pins = [si.shingles(p["text"]) for p in L["pinned"]]
    for qd in L["questions"]:
        q, kind = qd["q"], qd["kind"]
        ph = pool_h.get(q, set())
        qv = np.asarray(client.embed([q], model="voyage-law-2", input_type="query").embeddings[0], dtype=np.float32); qv /= (np.linalg.norm(qv) or 1.0)
        # ---- the site, main answer path (Lane A): its own function, unmodified
        res = sr.find_relevant_sections(q)
        jm = res.get("judgment_matches", [])
        top50 = sr.semantic_search(q)
        sc = [r["score"] for r in top50]
        lane_a = dict(n_passages=len(jm), docs=[r["doc"] for r in jm], distinct_docs=len({r["doc"] for r in jm}),
                      via=[r.get("retrieval", "semantic") for r in jm], scores=[round(r["score"], 3) for r in jm],
                      landmark_in=any(r["doc"] == L["doc"] for r in jm), pinned_in=any(si.is_pinned(r["text"], pins) for r in jm),
                      in_pool=[r["h"] in ph for r in jm], top_score=round(sc[0], 3), n_ge_040=sum(s >= .40 for s in sc), n_ge_050=sum(s >= .50 for s in sc), n_ge_060=sum(s >= .60 for s in sc),
                      top50_distinct_docs=len({r["doc"] for r in top50}), state=res.get("state"))
        # ---- the site, related-judgments candidate pool (Lane B, before its rerank): its own hybrid_search
        hy = sr.hybrid_search(q)
        hd = list(dict.fromkeys(r["doc"] for r in hy))
        lane_b = dict(distinct_docs=len(hd), landmark_rank=(hd.index(L["doc"]) + 1) if L["doc"] in hd else None, top10_docs=hd[:10],
                      pinned_in_top10_passages=any(si.is_pinned(r["text"], pins) for r in hy[:10]), in_pool_top10=sum(r["h"] in ph for r in hy[:10]),
                      retrieval=[r.get("retrieval") for r in hy[:10]])
        # ---- my pipeline on the same index
        fin = mine(q, qv, L)
        mdocs = list(dict.fromkeys(metas[r]["doc"] for r in fin))
        own = [r for r in fin if metas[r]["doc"] == L["doc"]][:3]
        mine_r = dict(top5_docs=mdocs[:5], landmark_rank=(mdocs.index(L["doc"]) + 1) if L["doc"] in mdocs else None,
                      pinned_top3=any(si.is_pinned(metas[r]["text"], pins) for r in own), in_pool_top10=sum(metas[r]["h"] in ph for r in fin[:10]))
        out.append(dict(name=L["name"], kind=kind, qid=pool_qid.get(q), landmark=L["doc"], question=q, site_main=lane_a, site_related_pool=lane_b, mine=mine_r))
        log(f"{pool_qid.get(q)} {L['name'][:14]:<14} {kind:<5} | site main: {len(jm)} passages from {lane_a['distinct_docs']} judgments, landmark {'IN' if lane_a['landmark_in'] else 'out'}, verified para {'IN' if lane_a['pinned_in'] else 'out'} | pool>=0.40: {lane_a['n_ge_040']}/50 | mine: landmark #{mine_r['landmark_rank']}")

json.dump(out, open(f"{SCR}/site_on_wide.json", "w"), indent=1)
log("done")
