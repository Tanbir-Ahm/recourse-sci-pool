"""Counts what the big index holds (embedded = searchable) by court, source and decision year, at its current head. Read-only; spends nothing.
The decision year of a Supreme Court crawl judgment is not stored in the index: it is read from the crawled text (old-style header date, else the date near the end, else a year in the opening lines),
so crawl years are ESTIMATES (the accuracy is measured against the exact header dates where both exist).
Usage: python3 -I index_holdings_by_year.py CODE_DIR INDEX_DIR CRAWL_DATA_DIR OUT.json"""
import collections, glob, gzip, json, os, re, sys
code, idx, crawl, out = sys.argv[1:5]
sys.path.insert(0, code)
import sci_index as si
M = "January|February|March|April|May|June|July|August|September|October|November|December"
D1 = re.compile(rf"\b({M})\s+(\d{{1,2}})\s*,?\s*((?:19|20)\d\d)\b", re.I); D2 = re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({M})\s*,?\s*((?:19|20)\d\d)\b", re.I)
D3 = re.compile(r"\b(\d{1,2})[./-](\d{1,2})[./-]((?:19|20)\d\d)\b"); HDR = re.compile(r"DATE OF JUDGMENT:?\s*(\d{1,2})[/.-](\d{1,2})[/.-]((?:19|20)\d\d)", re.I)
def year_from_text(t):
    m = HDR.search(t[:2500])
    if m: return int(m.group(3)), "header date"
    tail = t[-900:]
    ys = [int(m.group(3)) for m in D1.finditer(tail)] + [int(m.group(3)) for m in D2.finditer(tail)]
    if ys: return ys[-1], "date near the end"
    ys = [int(m.group(3)) for m in D3.finditer(tail)]
    if ys: return ys[-1], "date near the end"
    ys = [int(y) for y in re.findall(r"\b((?:19[5-9]\d)|(?:20[01]\d))\b", t[:1500])]
    if ys: return max(ys), "year in the opening lines"
    return None, "none"
led = si.ledger(idx)
emb = {}                       # doc -> (group, year or None, how)
crawl_ids = set()
for s, v in sorted(led.items()):
    mc = collections.Counter()
    for l in gzip.open(os.path.join(idx, "index", v["base"] + ".meta.jsonl.gz"), "rt"): mc[json.loads(l)["doc"]] += 1
    for l in gzip.open(os.path.join(idx, "index", v["base"] + ".docs.jsonl.gz"), "rt"):
        r = json.loads(l)
        if r.get("skip") or mc.get(r["doc"], 0) == 0: continue
        d = r["doc"]; src = r.get("src") or {}
        if d < 1_000_000_000:
            c = r.get("case") or {}
            m = re.match(r"(\d{1,2})/(\d{1,2})/((?:19|20)\d\d)", c.get("date") or "")
            emb[d] = ("SC crawl", int(m.group(3)) if m else None, "header date (index record)" if m else None); crawl_ids.add(d)
        else:
            sc = src.get("scope"); g = {"sci_newer": "SC newer archive", "bucket": "SC bucket"}.get(sc) or ("SC bucket" if d < 2_000_000_000 else {"ghc_court": "GHC court files (B)", "ghc_bucket": "GHC bucket text (C)", "ghc_post2017": "GHC post-2017 (P1)"}[sc])
            ds = src.get("date") or ""
            m = re.match(r"(\d{4})-\d\d-\d\d", ds) or re.match(r"\d\d-\d\d-(\d{4})", ds)
            emb[d] = (g, int(m.group(1)) if m else None, "date in the record")
need = {d for d in crawl_ids if emb[d][1] is None}
how = collections.Counter(); acc = collections.Counter()
for f in sorted(glob.glob(os.path.join(crawl, "shards", "*.jsonl.gz"))):
    for l in gzip.open(f, "rt", encoding="utf-8"):
        r = json.loads(l)
        if r.get("status") != "ok": continue
        d = r["id"]
        if d in crawl_ids:
            y, h = year_from_text(r["text"])
            if emb[d][1] is None: emb[d] = ("SC crawl", y, h); how[h] += 1
            else:                                                     # accuracy check against the exact header date
                acc["checked"] += 1; acc["same year"] += (y == emb[d][1]); acc["within 1 year"] += (y is not None and abs(y - emb[d][1]) <= 1)
res = collections.defaultdict(collections.Counter)
for d, (g, y, h) in emb.items(): res[g][y if y else "unknown"] += 1
json.dump({"by_group_year": {g: {str(k): v for k, v in c.items()} for g, c in res.items()}, "crawl_year_method": dict(how), "crawl_year_accuracy_vs_header": dict(acc), "embedded_total": len(emb)}, open(out, "w"), indent=1)
print("embedded judgments:", len(emb), "| crawl year method:", dict(how), "| accuracy of the text-based year where the exact header date exists:", dict(acc))
