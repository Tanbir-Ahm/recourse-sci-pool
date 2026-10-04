"""Finds the passages that the site's search (Lane A, its own function) or my pipeline (top 6) shows on the wide index but that are NOT in the
review pool, and writes them as continuation rows. Also tags every pool row with whether each method showed it, so both methods can be scored
on exactly what they show. Read-only on the index. Writes pool_topup.json (new rows only) and pool_all.json (pool + new rows + method tags)."""
import collections, copy, json, random, re, sqlite3, sys
import numpy as np

sys.path.insert(0, "/home/user/recourse-sci-pool"); sys.path.insert(0, "/home/user/tanbir-ahm/recourse")
import sci_index as si
import semantic_retrieval as sr

SCR = "/tmp/claude-0/-home-user-recourse-sci-pool/33686f69-1895-5643-b31d-21bed3d4a6ee/scratchpad/cmp"
IDX, POOLDIR = "/home/user/recourse-sci-index", "/home/user/recourse-sci-pool-data"
SITE, MINE = "S site shown", "M mine top 6"

metas, M, _ = si._load_index(IDX)
where = {(m["doc"], m["i"]): k for k, m in enumerate(metas)}
hdocs = collections.defaultdict(set)
for m in metas: hdocs[m["h"]].add(m["doc"])
records = [{"chunk_id": f"{m['doc']}:{m['i']}", "text": m["text"], "type": "judgment", "case_name": str(m["doc"]), "paragraph_number": m["pn"], "section_number": None, "doc": m["doc"], "h": m["h"]} for m in metas]
sr._corpus_cache = {"records": records, "matrix": M.astype(np.float32), "model": "voyage-law-2"}
sr._named_section_exact_match = lambda q: None
sr._section_tables = lambda: {}
sr._build_lexical_index()
client = si.make_client()
fts = sqlite3.connect(":memory:"); fts.execute("create virtual table f using fts5(text, tokenize='porter unicode61')")
fts.executemany("insert into f(rowid, text) values(?,?)", ((i, m["text"]) for i, m in enumerate(metas)))


def mine_final(q):
    qv = np.asarray(client.embed([q], model="voyage-law-2", input_type="query").embeddings[0], dtype=np.float32); qv /= (np.linalg.norm(qv) or 1.0)
    sims = np.concatenate([M[i:i + 50000].astype(np.float32) @ qv for i in range(0, len(M), 50000)])
    sem = [int(i) for i in np.argsort(-sims)[:100]]
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
    return [r for r, _ in sorted(((r, s * w(r)) for r, s in rs.items()), key=lambda x: -x[1])]


# titles, as in the original pool (opening header; the crawl text when the index has no header passage)
header_text = {}
for m in metas:
    if m["doc"] not in header_text and (m["section"] == "header" or str(m["pn"]).startswith("preamble")):
        header_text[m["doc"]] = re.sub(r"\s+", " ", m["text"])[:260]
case_meta = {}
import glob, gzip
for f in glob.glob(f"{IDX}/index/*.docs.jsonl.gz"):
    for l in gzip.open(f, "rt", encoding="utf-8"):
        r = json.loads(l)
        if r.get("case"): case_meta[r["doc"]] = r["case"]
blocks = si.pool_blocks(POOLDIR)


def title(doc):
    c = case_meta.get(doc)
    if c and (c.get("pet") or c.get("resp")):
        return (f"{c.get('pet', '?')} v. {c.get('resp', '?')}" + (f" ({c['date']})" if c.get("date") else ""))[:200]
    if header_text.get(doc):
        return header_text[doc]
    s = next(s for s, b in blocks.items() if s <= doc <= b["end"])
    rec = next(r for r in si._read_pool_block(blocks[s]["path"]) if r.get("id") == doc)
    return re.sub(r"\s+", " ", rec["text"])[:260]


pool = json.load(open(f"{SCR}/pool_raw_v2.json", encoding="utf-8"))
lm = json.load(open("/home/user/recourse-sci-pool/landmarks.json", encoding="utf-8"))["landmarks"]
allq = {qd["q"]: L for L in lm for qd in L["questions"]}
all_pool, new_pool, stats = copy.deepcopy(pool), [], []
for qi, q in enumerate(all_pool):
    question = q["question"]
    shown = sr.find_relevant_sections(question).get("judgment_matches", [])
    site_idx = [where[(r["doc"], int(r["chunk_id"].split(":")[1]))] for r in shown]
    mine_idx = mine_final(question)[:6]
    have = {r["h"]: r for r in q["rows"]}
    for name, lst in ((SITE, site_idx), (MINE, mine_idx)):
        for pos, k in enumerate(lst, 1):
            h = metas[k]["h"]
            if h in have:
                have[h]["variants"][name] = min(pos, have[h]["variants"].get(name, 99))
    fresh = collections.OrderedDict()
    for name, lst in ((SITE, site_idx), (MINE, mine_idx)):
        for pos, k in enumerate(lst, 1):
            h = metas[k]["h"]
            if h in have: continue
            g = fresh.setdefault(h, dict(primary=k, variants={}))
            g["variants"][name] = min(pos, g["variants"].get(name, 99))
    rows = []
    for h, g in fresh.items():
        m = metas[g["primary"]]
        rows.append(dict(h=h, doc=m["doc"], pn=m["pn"], page=m["page"], title=title(m["doc"]), text=m["text"], also=sorted(hdocs[h] - {m["doc"]}), variants=g["variants"], topup=True))
    random.Random(2027 + qi).shuffle(rows)               # blind, as before
    start = max(r["n"] for r in q["rows"])
    for i, row in enumerate(rows, start + 1): row["n"] = i
    q["rows"].extend(rows)
    new_pool.append(dict(qid=q["qid"], kind=q["kind"], question=question, landmark_doc=q["landmark_doc"], first_new_no=start + 1 if rows else None, rows=rows))
    both = sum(1 for r in rows if len(r["variants"]) == 2)
    stats.append((q["qid"], len(shown), len(mine_idx), len(rows), sum(SITE in r["variants"] for r in rows), sum(MINE in r["variants"] for r in rows), both))
    print(f"{q['qid']} {q['kind']:<5} site showed {len(shown)} | mine top-6 {len(mine_idx)} | NEW to the pool: {len(rows)} (site {stats[-1][4]}, mine {stats[-1][5]}, both {both}) | numbers {start + 1}-{start + len(rows)}" if rows else
          f"{q['qid']} {q['kind']:<5} site showed {len(shown)} | mine top-6 {len(mine_idx)} | NEW to the pool: 0", flush=True)
json.dump(new_pool, open(f"{SCR}/pool_topup.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(all_pool, open(f"{SCR}/pool_all.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
tot = sum(s[3] for s in stats)
print(f"\nNEW passages: {tot} | shown by the site only: {sum(1 for q in new_pool for r in q['rows'] if SITE in r['variants'] and MINE not in r['variants'])}, "
      f"by my pipeline only: {sum(1 for q in new_pool for r in q['rows'] if MINE in r['variants'] and SITE not in r['variants'])}, by both: {sum(s[6] for s in stats)}")
print("questions with no new passages:", [s[0] for s in stats if s[3] == 0])
print("site-shown passages total:", sum(s[1] for s in stats), "| mine top-6 total:", sum(s[2] for s in stats))
