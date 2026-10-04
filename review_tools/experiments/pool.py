"""Build the pooled review set: top 10 from several search variants for each of the 12 questions, de-duplicated by identical text,
plus the landmark case's own key passages. Read-only on the index. Writes pool_raw.json (everything) for the workbook builder."""
import collections, glob, gzip, json, random, re, sqlite3, sys
import numpy as np
sys.path.insert(0, "/home/user/recourse-sci-pool")
import sci_index as si
SCR = "/tmp/claude-0/-home-user-recourse-sci-pool/33686f69-1895-5643-b31d-21bed3d4a6ee/scratchpad/cmp"
IDX = "/home/user/recourse-sci-index"
CAP = 16
lm = json.load(open("/home/user/recourse-sci-pool/landmarks.json", encoding="utf-8"))["landmarks"]
rew = json.load(open(f"{SCR}/rewrites.json", encoding="utf-8"))
metas, M, _ = si._load_index(IDX)
client = si.make_client()
fts = sqlite3.connect(":memory:")
fts.execute("create virtual table f using fts5(text, tokenize='porter unicode61')")
fts.executemany("insert into f(rowid, text) values(?,?)", ((i, m["text"]) for i, m in enumerate(metas)))
hdocs = collections.defaultdict(set)
for m in metas: hdocs[m["h"]].add(m["doc"])
case_meta, header_text = {}, {}
for f in glob.glob(f"{IDX}/index/*.docs.jsonl.gz"):
    for l in gzip.open(f, "rt", encoding="utf-8"):
        r = json.loads(l)
        if r.get("case"): case_meta[r["doc"]] = r["case"]
for m in metas:
    if m["doc"] not in header_text and (m["section"] == "header" or str(m["pn"]).startswith("preamble")):
        header_text[m["doc"]] = re.sub(r"\s+", " ", m["text"])[:260]
def title(doc):
    c = case_meta.get(doc)
    if c and (c.get("pet") or c.get("resp")):
        return (f"{c.get('pet', '?')} v. {c.get('resp', '?')}" + (f" ({c['date']})" if c.get("date") else ""))[:200]
    return header_text.get(doc)
tokens = 0

def retrieve(q, dedupe=False, pool=60):
    global tokens
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
    ranked = [r for r, _ in sorted(rr.items(), key=lambda x: -x[1])]
    if dedupe:
        seen, cand = set(), []
        for r in ranked:
            if metas[r]["h"] in seen: continue
            seen.add(metas[r]["h"]); cand.append(r)
            if len(cand) == pool: break
    else:
        cand = ranked[:pool]
    return dict(q=q, cand=cand, nums=nums)

def rerank(q, cand):
    global tokens
    resp = client.rerank(q, [metas[r]["text"][:3500] for r in cand], model="rerank-2", top_k=len(cand))
    tokens += getattr(resp, "total_tokens", 0) or 0
    return {cand[x.index]: x.relevance_score for x in resp.results}

def weight(rid, nums):
    return si.W.get(metas[rid]["section"], 1.0) * (1.10 if nums and si.has_section(metas[rid]["text"], nums) else 1.0)

def order_by(scores):
    return [r for r, _ in sorted(scores.items(), key=lambda x: -x[1])]

out, key = [], []
qn = 0
for L in lm:
    pin_sets = [si.shingles(p["text"]) for p in L["pinned"]]
    own = [i for i, m in enumerate(metas) if m["doc"] == L["doc"]]
    for q in L["questions"]:
        qn += 1
        lay = q["kind"] == "lay"
        rw = next((v for k, v in rew.items() if q["q"].startswith(k)), None) if lay else None
        lists = {}
        a = retrieve(q["q"]); rs_a = rerank(q["q"], a["cand"])
        lists["A today"] = order_by({r: s * weight(r, a["nums"]) for r, s in rs_a.items()})[:10]
        lists["E no multiplier"] = order_by(rs_a)[:10]
        b = retrieve(q["q"], dedupe=True); rs_b = rerank(q["q"], b["cand"])
        lists["B no repeats"] = order_by({r: s * weight(r, b["nums"]) for r, s in rs_b.items()})[:10]
        if rw:
            c = retrieve(rw); rs_c = rerank(rw, c["cand"])
            lists["C rewrite"] = order_by({r: s * weight(r, c["nums"]) for r, s in rs_c.items()})[:10]
            union = list(dict.fromkeys(a["cand"] + c["cand"]))
            ro, rr_ = rerank(q["q"], union), rerank(rw, union)
            lists["F merged"] = order_by({r: max(ro[r] * weight(r, a["nums"]), rr_[r] * weight(r, c["nums"])) for r in union})[:10]
        # the landmark case's own key passages (so they are judged even if no variant returns them)
        land = []
        for ps in pin_sets:
            best = max(own, key=lambda i: len(si.shingles(metas[i]["text"]) & ps) / max(len(ps), 1))
            if best not in land: land.append(best)
        lists["L landmark key passages"] = land[:2]
        # collapse identical passages; first seen = primary
        groups = collections.OrderedDict()
        for vname, lst in lists.items():
            for rank, r in enumerate(lst, 1):
                g = groups.setdefault(metas[r]["h"], dict(primary=r, variants={}))
                g["variants"][vname] = min(rank, g["variants"].get(vname, 99))
        n_before = len(groups)
        mandatory = [h for h, g in groups.items() if g["variants"].get("A today", 99) <= 5 or "L landmark key passages" in g["variants"]]
        rest = sorted([h for h in groups if h not in mandatory], key=lambda h: (-len(groups[h]["variants"]), min(groups[h]["variants"].values())))
        keep = mandatory + rest[:max(0, CAP - len(mandatory))]
        rows = []
        for h in keep:
            r = groups[h]["primary"]; m = metas[r]
            others = sorted(hdocs[h] - {m["doc"]})
            rows.append(dict(h=h, doc=m["doc"], pn=m["pn"], page=m["page"], title=title(m["doc"]), text=m["text"], also=others, variants=groups[h]["variants"]))
        random.Random(2026 + qn).shuffle(rows)          # blind: no hint of which search found it or in what order
        for i, row in enumerate(rows, 1): row["n"] = i
        out.append(dict(qid=f"Q{qn:02d}", kind=q["kind"], question=q["q"], landmark_doc=L["doc"], rewrite=rw, rows=rows))
        print(f"Q{qn:02d} {q['kind']:5} variants={len(lists)} unique before trim={n_before:>3} mandatory={len(mandatory)} kept={len(rows)}", flush=True)
json.dump(out, open(f"{SCR}/pool_raw.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
tot = sum(len(q["rows"]) for q in out)
print(f"\nTOTAL passages in the sheet: {tot} | with identical text also in other judgments: {sum(1 for q in out for r in q['rows'] if r['also'])} | reranker tokens billed: {tokens:,} (about ${tokens*0.05/1e6:.2f} at $0.05 per 1M)")
print("passage length chars: min", min(len(r['text']) for q in out for r in q['rows']), "max", max(len(r['text']) for q in out for r in q['rows']), "| total characters to read:", f"{sum(len(r['text']) for q in out for r in q['rows']):,}")
