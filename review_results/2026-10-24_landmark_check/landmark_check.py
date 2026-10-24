"""Landmark check on the whole index (owner asked 2026-10-24). 1) runs the index's own known-answer test (sci_index.run_eval: 6 verified landmarks, 12 questions; success = the case is among the top 5
cases AND its verified paragraph among its top 3 passages) and saves its record on the index branch like `sci_index.py eval --push`; 2) re-reads the SAME service answers from a cache (no new calls) to show
which judgments take the top places, by court; 3) repeats the test on a view of the index without the Guwahati judgments (new re-rank calls, a few cents) to see whether they are the cause.
Usage: python3 -I landmark_check.py CODE_DIR INDEX_DIR OUT.json"""
import collections, gzip, hashlib, json, os, re, sqlite3, sys, time
from datetime import datetime, timezone
import numpy as np
code, idx, out_path = sys.argv[1:4]
sys.path.insert(0, code)
import sci_index as si

class CachingClient:
    """Wraps the real client; identical calls are answered from memory (and not billed twice). Counts the billed tokens of the calls that were really made."""
    def __init__(self, real): self.real, self.cache, self.billed = real, {}, collections.Counter(); self.calls = collections.Counter()
    def embed(self, texts, model=None, input_type=None):
        k = ("e", tuple(texts), model, input_type)
        if k not in self.cache:
            r = self.real.embed(texts, model=model, input_type=input_type); self.cache[k] = r; self.billed["embed"] += getattr(r, "total_tokens", 0) or 0; self.calls["embed"] += 1
        return self.cache[k]
    def rerank(self, query, documents, model=None, top_k=None):
        k = ("r", query, hashlib.sha1("\x00".join(documents).encode("utf-8", "replace")).hexdigest(), model, top_k)
        if k not in self.cache:
            r = self.real.rerank(query, documents, model=model, top_k=top_k); self.cache[k] = r; self.billed["rerank"] += getattr(r, "total_tokens", 0) or 0; self.calls["rerank"] += 1
        return self.cache[k]

client = CachingClient(si.make_client())
t0 = time.time()
print("== 1. the index's own landmark test, on the whole index", flush=True)
res = si.run_eval(idx, client, out=print)
ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S"); rel = os.path.join("eval", f"landmark-{ts}.json")
os.makedirs(os.path.join(idx, "eval"), exist_ok=True); json.dump(res, open(os.path.join(idx, rel), "w"), indent=1)
si._commit(idx, [rel], "landmark evaluation"); pushed = si._push(idx)[0]; print("record saved and", "pushed" if pushed else "NOT pushed (see the index folder)", rel, flush=True)

# who is who
label = {}
for s, v in si.ledger(idx).items():
    for l in gzip.open(os.path.join(idx, "index", v["base"] + ".docs.jsonl.gz"), "rt", encoding="utf-8"):
        r = json.loads(l); d = r["doc"]; src = r.get("src") or {}; sc = src.get("scope")
        g = "SC crawl" if d < 1_000_000_000 else "SC bucket" if d < 2_000_000_000 else {"sci_newer": "SC newer", "ghc_court": "GHC", "ghc_bucket": "GHC", "ghc_post2017": "GHC"}[sc]
        c = r.get("case") or {}
        title = src.get("title") or ((c.get("pet", "") + " " + c.get("resp", "")).strip() or None)
        label[d] = (g, (title or "")[:46], (src.get("date") or c.get("date") or "")[:10], src.get("citation") or "")
metas, M, docs_with = si._load_index(idx)
lm = json.load(open(os.path.join(code, "landmarks.json"), encoding="utf-8"))["landmarks"]

def evaluate(view, keep):
    sel = [i for i, m in enumerate(metas) if keep(m["doc"])]
    mm = [metas[i] for i in sel]; MM = M[sel]
    fts = sqlite3.connect(":memory:"); fts.execute("create virtual table f using fts5(text, tokenize='porter unicode61')")
    fts.executemany("insert into f(rowid, text) values(?,?)", ((i, m["text"]) for i, m in enumerate(mm)))
    rows = []
    for L in lm:
        pins = [si.shingles(p["text"]) for p in L["pinned"]]
        for q in L["questions"]:
            question = q["q"]
            qv = np.asarray(client.embed([question], model=si.MODEL, input_type="query").embeddings[0], dtype=np.float32); qv /= (np.linalg.norm(qv) or 1.0)
            sims = np.concatenate([MM[i:i + 50000].astype(np.float32) @ qv for i in range(0, len(MM), 50000)])
            sem = [int(i) for i in np.argsort(-sims)[:100]]
            toks = list(dict.fromkeys(t for t in re.findall(r"[A-Za-z0-9]{4,}", question.lower()) if t not in si.STOP))[:12]
            kw = [r[0] for r in fts.execute("select rowid from f where f match ? order by bm25(f) limit 50", (" OR ".join(f'"{t}"' for t in toks),))] if toks else []
            nums = si.section_numbers(question); sc = []
            for n in nums: sc += [r[0] for r in fts.execute("select rowid from f where f match ? order by bm25(f) limit 30", (f'"section {n}"',))]
            rr = {}
            for lst in (sem, kw, sc):
                for rank, rid in enumerate(lst): rr[rid] = rr.get(rid, 0.0) + 1.0 / (60 + rank)
            cand = [r for r, _ in sorted(rr.items(), key=lambda x: -x[1])][:60]
            resp = client.rerank(question, [mm[r]["text"][:3500] for r in cand], model="rerank-2", top_k=len(cand))
            rs = {cand[x.index]: x.relevance_score for x in resp.results}
            w = lambda rid: si.W.get(mm[rid]["section"], 1.0) * (1.10 if nums and si.has_section(mm[rid]["text"], nums) else 1.0)
            order = [r for r, _ in sorted(((r, s * w(r)) for r, s in rs.items()), key=lambda x: -x[1])]
            seen, ranked = set(), []
            for r in order:
                if mm[r]["doc"] not in seen: seen.add(mm[r]["doc"]); ranked.append(mm[r]["doc"])
            rank = ranked.index(L["doc"]) + 1 if L["doc"] in ranked else None
            own = [r for r in order if mm[r]["doc"] == L["doc"]][:3]; pinned = any(si.is_pinned(mm[r]["text"], pins) for r in own)
            rows.append({"landmark": L["name"], "kind": q["kind"], "doc_rank": rank, "pinned_in_top3": pinned, "success": bool(rank and rank <= 5 and pinned), "top5": [(d, label[d][0]) for d in ranked[:5]], "top10": [(d, label[d][0]) for d in ranked[:10]]})
    return rows

full = evaluate("whole index", lambda d: True)
print("\n== 2. the same answers, read again: who takes the top five places (whole index)")
slots = collections.Counter()
for r in full:
    names = " | ".join(f"{g}:{label[d][1][:22]}" if d != next(L['doc'] for L in lm if L['name'] == r['landmark']) else "**THE LANDMARK**" for d, g in r["top5"])
    print(f"[{r['kind']:5}] {r['landmark'][:30]:30} landmark rank {r['doc_rank']} {'OK' if r['success'] else 'miss'} :: {names}")
    for d, g in r["top5"]: slots[g] += 1
print("top-five places by source (12 questions x 5 = 60):", dict(slots))
sc_only = evaluate("Supreme Court only", lambda d: label[d][0].startswith("SC"))
def summ(rows): return {"case_top5": sum(1 for r in rows if r["doc_rank"] and r["doc_rank"] <= 5), "pinned_top3": sum(r["pinned_in_top3"] for r in rows), "full_success": sum(r["success"] for r in rows)}
print("\n== 3. the same test with the Guwahati judgments taken out (Supreme Court judgments only)")
for a, b in zip(full, sc_only): print(f"{a['landmark'][:34]:34} {a['kind']:5} whole index: rank {a['doc_rank']} {'OK' if a['success'] else 'miss'} | without Guwahati: rank {b['doc_rank']} {'OK' if b['success'] else 'miss'}")
print("whole index:", summ(full), "| without Guwahati:", summ(sc_only))
cost = client.billed["rerank"] / 1e6 * 0.05 + client.billed["embed"] / 1e6 * 0.12
print(f"\nbilled this run: {client.calls['embed']} embed calls ({client.billed['embed']} tokens), {client.calls['rerank']} re-rank calls ({client.billed['rerank']:,} tokens): about ${cost:.3f}; {time.time()-t0:.0f}s")
json.dump({"official": res["summary"], "whole_index": full, "supreme_court_only": sc_only, "summary_whole": summ(full), "summary_sc_only": summ(sc_only), "top5_slots_by_source": dict(slots), "billed": dict(client.billed), "dollars": round(cost, 4)}, open(out_path, "w"), indent=1)
