"""Fair comparison: if my pipeline showed the same number of passages the site shows (top 6), does it include the landmark / the verified paragraph?
Also: where does the verified paragraph sit in the plain meaning ranking (what the site's first step uses)?"""
import json, re, sqlite3, sys
import numpy as np
sys.path.insert(0, "/home/user/recourse-sci-pool")
import sci_index as si
SCR = "/tmp/claude-0/-home-user-recourse-sci-pool/33686f69-1895-5643-b31d-21bed3d4a6ee/scratchpad/cmp"
metas, M, _ = si._load_index("/home/user/recourse-sci-index")
lm = json.load(open("/home/user/recourse-sci-pool/landmarks.json", encoding="utf-8"))["landmarks"]
client = si.make_client()
fts = sqlite3.connect(":memory:"); fts.execute("create virtual table f using fts5(text, tokenize='porter unicode61')")
fts.executemany("insert into f(rowid, text) values(?,?)", ((i, m["text"]) for i, m in enumerate(metas)))
by_doc = {}
for i, m in enumerate(metas): by_doc.setdefault(m["doc"], []).append(i)
rows = []
for L in lm:
    pins = [si.shingles(p["text"]) for p in L["pinned"]]
    pinned_idx = [i for i in by_doc.get(L["doc"], []) if si.is_pinned(metas[i]["text"], pins)]
    for qd in L["questions"]:
        q = qd["q"]
        qv = np.asarray(client.embed([q], model="voyage-law-2", input_type="query").embeddings[0], dtype=np.float32); qv /= (np.linalg.norm(qv) or 1.0)
        sims = np.concatenate([M[i:i + 50000].astype(np.float32) @ qv for i in range(0, len(M), 50000)])
        order = np.argsort(-sims); rank_of = np.empty(len(order), dtype=np.int64); rank_of[order] = np.arange(1, len(order) + 1)
        sem = [int(i) for i in order[:100]]
        toks = list(dict.fromkeys(t for t in re.findall(r"[A-Za-z0-9]{4,}", q.lower()) if t not in si.STOP))[:12]
        kw = [r[0] for r in fts.execute("select rowid from f where f match ? order by bm25(f) limit 50", (" OR ".join(f'"{t}"' for t in toks),))] if toks else []
        nums = si.section_numbers(q); sc = []
        for n in nums: sc += [r[0] for r in fts.execute("select rowid from f where f match ? order by bm25(f) limit 30", (f'"section {n}"',))]
        rr = {}
        for lst in (sem, kw, sc):
            for rank, rid in enumerate(lst): rr[rid] = rr.get(rid, 0.0) + 1.0 / (60 + rank)
        cand = [r for r, _ in sorted(rr.items(), key=lambda x: -x[1])][:60]
        resp = client.rerank(q, [metas[r]["text"][:3500] for r in cand], model="rerank-2", top_k=len(cand))
        rs = {cand[x.index]: x.relevance_score for x in resp.results}
        w = lambda rid: si.W.get(metas[rid]["section"], 1.0) * (1.10 if nums and si.has_section(metas[rid]["text"], nums) else 1.0)
        fin = [r for r, _ in sorted(((r, s * w(r)) for r, s in rs.items()), key=lambda x: -x[1])]
        top6 = fin[:6]
        rows.append(dict(qid=None, kind=qd["kind"], name=L["name"][:14], mine6_landmark=any(metas[r]["doc"] == L["doc"] for r in top6), mine6_pinned=any(r in pinned_idx for r in top6),
                         mine6_docs=len({metas[r]["doc"] for r in top6}), verified_best_cosine_rank=int(min(rank_of[i] for i in pinned_idx)) if pinned_idx else None,
                         verified_in_rerank_candidates=any(i in cand for i in pinned_idx)))
json.dump(rows, open(f"{SCR}/site_on_wide2.json", "w"), indent=1)
for r in rows: print(r["name"], r["kind"], "| mine top-6: landmark", "IN " if r["mine6_landmark"] else "out", "verified", "IN " if r["mine6_pinned"] else "out", f"({r['mine6_docs']} judgments)", "| verified para's rank by plain meaning:", r["verified_best_cosine_rank"], "| in my 60 candidates:", r["verified_in_rerank_candidates"])
print("mine top-6: landmark in", sum(r["mine6_landmark"] for r in rows), "of 12; verified paragraph in", sum(r["mine6_pinned"] for r in rows), "of 12")
rk = [r["verified_best_cosine_rank"] for r in rows if r["verified_best_cosine_rank"]]
print("verified paragraph within the plain-meaning top 50:", sum(x <= 50 for x in rk), "of", len(rk), "| within top 6:", sum(x <= 6 for x in rk), "| median rank", int(np.median(rk)))
