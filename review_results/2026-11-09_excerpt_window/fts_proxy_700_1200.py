"""Lexical proxy for the wider search: for each question, the 12 best passages by the index's keyword table (BM25), then: are the question's words inside the 600 characters the page shows, and inside the 900 characters the answer model sees?
(The real search also ranks by meaning and re-ranks; this proxy shows only where the words sit inside a passage.) Usage: python3 fts_proxy.py <lean.sqlite> <passages json> <out json>"""
import sqlite3, json, re, sys, zlib, importlib, glob, os
sys.path.insert(0, "/home/user/recourse")
import sci_search_tier as T
import passage_window as W
lean, pj, out = sys.argv[1], sys.argv[2], sys.argv[3]
rows = json.load(open(pj))
docof = {r[0]: r[1] for r in rows}
STOP = set("the a an and or of to in on for is are was were be been do does did can could will would should may might what which who whom whose how why when where that this these those with without from by at as it its my me i we you your he she they them his her their our not no any if then than there here about into over under after before can cannot have has had having also only just very more most such other some".split())
def terms(q):
    ws = re.findall(r"[a-z]{4,}", q.lower())
    return [w for w in dict.fromkeys(ws) if w not in STOP][:12]
def fts_query(ts):
    return " OR ".join('"%s"' % t for t in ts)
qs = []
base = "/home/user/recourse-sci-pool/review_results"
for d in [base + "/2026-11-03_retrieval_misses", base + "/2026-10-31_relevance_gate", base + "/2026-11-03_relevance_neighbours", base + "/2026-11-09_harbouring_alias", base + "/2026-11-09_bail_alias"]:
    sys.path.insert(0, d)
    for f in sorted(glob.glob(d + "/questions*.py")):
        m = os.path.basename(f)[:-3]
        try: mod = importlib.import_module(m)
        except Exception: continue
        for name in dir(mod):
            v = getattr(mod, name)
            if isinstance(v, list):
                for it in v:
                    s = it[0] if isinstance(it, (tuple, list)) and it else it
                    if isinstance(s, str) and len(s) > 25: qs.append(s)
qs = list(dict.fromkeys(qs))
c = sqlite3.connect("file:" + lean + "?mode=ro", uri=True)
res = []
for qi, q in enumerate(qs):
    ts = terms(q)
    if len(ts) < 3: continue
    try:
        ids = [r[0] for r in c.execute("select rowid from f where f match ? order by rank limit 12", (fts_query(ts),))]
    except Exception as e:
        continue
    for rank, rid in enumerate(ids):
        z = c.execute("select z from t where id=?", (rid,)).fetchone()
        if not z: continue
        text = zlib.decompress(z[0]).decode("utf-8", "surrogatepass")
        low = text.lower()
        shown_old = low[:700]
        win_old = low[:1200]
        shown = W.window(text, qs[qi], 700)[0].lower()
        win = W.window(text, qs[qi], 1200)[0].lower()
        hit = lambda s: sum(1 for t in ts if re.search(r"\b" + re.escape(t[:5]), s))
        res.append({"q": qi, "rank": rank, "row": rid, "doc": docof.get(rid), "len": len(text), "terms": len(ts), "all": hit(low), "shown": hit(shown), "window": hit(win), "shown_old": hit(shown_old), "window_old": hit(win_old), "shown_len": len(shown), "win_len": len(win)})
json.dump({"questions": len(qs), "rows": res}, open(out, "w"))
print("questions", len(qs), "passages", len(res))
