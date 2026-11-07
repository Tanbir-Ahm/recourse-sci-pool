"""Tests for sci_store.py and the SCI_STORE switch of sci_search_service.py (FOLLOW_UPS 2dr): the passage text and the keyword index in a file on disk, only six small fields per passage in memory.
Everything is checked against the classic in-memory service on a small invented index on disk (main index + two side indexes). No network, no spend. Run: python test_sci_store.py"""
import io, contextlib, gzip, json, os, re, shutil, sqlite3, sys, tempfile, zlib
from types import SimpleNamespace
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sci_index as si
import sci_search_service as S
import sci_store as store

FAILS = []
def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{detail}]"))
    if not cond:
        FAILS.append(name)

DIM = 16
rng = np.random.default_rng(9)
tmp = tempfile.mkdtemp(prefix="store_")
os.environ["SCI_INDEX_COMMIT"] = "abc1234"
os.environ["SCI_NAMES_TABLE"] = os.path.join(tmp, "no_such_names_table.json.gz")
for k in ("SCI_STORE", "SCI_STORE_PATH", "SCI_LOAD_COPY", "SCI_SIM_BLOCK", "SCI_QUOTES", "SCI_AUTHORITY"):
    os.environ.pop(k, None)

TOPICS = ["anticipatory bail and arrest under section 438", "cheque dishonour compounding under section 138", "murder sentence and death penalty", "default bail on the chargesheet", "quashing an FIR on settlement",
          "हिन्दी पाठ: जमानत और गिरफ्तारी", "the court’s “curly quotes” and an en–dash — in the text"]

def row(doc, i, text):
    return {"doc": doc, "i": i, "pn": str(i + 1), "page": 1 + i // 3, "section": ["reasoning", "facts", "header", "argument"][i % 4], "h": f"h{doc}-{i}", "method": "m", "basis": "b", "pos": 0.5, "prec": 1, "text": text}

def make_index(path, first_doc, shard_sizes, manifest=None, texts=None):
    os.makedirs(path, exist_ok=True)
    si._claim_model(path, S.EMBED_MODEL)
    start, doc, k = 0, first_doc, 0
    for n in shard_sizes:
        metas = []
        for j in range(n):
            t = f"{j % 4 + 1}. In case {doc + j // 4} para {j % 4} the court considered {TOPICS[(k + j) % len(TOPICS)]} and section {400 + (doc % 4)}." if texts is None else texts[k + j]
            metas.append(row(doc + j // 4, j % 4, t))
        docs = [{"doc": doc + j, "hash": f"x{doc + j}"} for j in range((n + 3) // 4)]
        si.write_block_files(path, start, 10, docs, metas, rng.normal(size=(n, DIM)).astype(np.float16), 1)
        start += 10; doc += (n + 3) // 4; k += n
    if manifest is not None:
        json.dump(manifest, open(os.path.join(path, "SUPPLEMENT.json"), "w"))
    return path

main = make_index(os.path.join(tmp, "main"), 1, [40, 30, 20])
sup = {"main_index_commit": "abc1234", "documents": 3, "passages": 6}
side1 = make_index(os.path.join(tmp, "side1"), 1000, [16], manifest=sup)
side2 = make_index(os.path.join(tmp, "side2"), 2000, [8, 5], manifest=sup)
SPATH = os.path.join(tmp, "store.sqlite")
os.environ["SCI_STORE_PATH"] = SPATH
os.environ["SCI_NAMES_TABLE"] = os.path.join(tmp, "none.json.gz")

def load(on, sides=(side1, side2), idx=main):
    if on: os.environ["SCI_STORE"] = "on"
    else: os.environ.pop("SCI_STORE", None)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        sv = S.SearchService.load(idx, side_dirs=list(sides), client=object())
    return sv, buf.getvalue()

classic, _ = load(False)
check("classic: the metadata rows hold their text in memory (the starting point)", isinstance(classic.metas, list) and "text" in classic.metas[0] and "store" not in classic.info)
lean, out = load(True)
check("SCI_STORE=on, no file yet: it is built, the service uses it", lean.info.get("store", {}).get("state") == "built" and os.path.exists(SPATH) and not os.path.exists(SPATH + ".building"), lean.info.get("store"))
check("lean metadata is a LeanMetas, not a list of dictionaries with text", isinstance(lean.metas, store.LeanMetas) and len(lean.metas) == len(classic.metas) == 40 + 30 + 20 + 16 + 13)
check("every row's six fields equal the classic row's, and the text read from the file equals the classic text (all rows, incl. Devanagari and curly quotes)",
      all({k: v for k, v in a.items() if k != "text"} == lean.metas[i] and a["text"] == lean._text(i) for i, a in enumerate(classic.metas)))
check("the vectors are identical", np.array_equal(classic.M, lean.M))
ci = {k: v for k, v in classic.info.items() if k not in ("load_seconds", "store")}
li = {k: v for k, v in lean.info.items() if k not in ("load_seconds", "store")}
check("the service info is identical (passages, documents, side indexes, dates)", ci == li)
check("the opening-lines table of documents with no case record is identical", classic.header_docs == lean.header_docs and classic.title(5) == lean.title(5))
check("iteration and slicing of LeanMetas give the same dictionaries", list(lean.metas)[7] == lean.metas[7] and lean.metas[3:6] == [lean.metas[3], lean.metas[4], lean.metas[5]] and lean.metas[-1] == lean.metas[len(lean.metas) - 1])
check("rows_with_text gives doc, i, pn and the text of every passage in order", all(r["doc"] == classic.metas[k]["doc"] and r["text"] == classic.metas[k]["text"] and r["pn"] == classic.metas[k]["pn"] and r["i"] == classic.metas[k]["i"] for k, r in enumerate(lean.metas.rows_with_text())))
check("the startup line says the text is on disk", "SCI_STORE on (built)" in S.startup_line(lean, "h", 1))

# ---- the same answers
cur = {}
class Cl:
    def embed(self, texts, model, input_type):
        return SimpleNamespace(embeddings=[cur["v"].tolist()], total_tokens=1)
    def rerank(self, query, docs, model, top_k):
        sc = [(zlib.crc32(d.encode("utf-8")) % 1000) / 1000.0 + 0.01 * len(set(re.findall(r"[a-z]{4,}", d.lower())) & set(re.findall(r"[a-z]{4,}", query.lower()))) for d in docs]
        order = sorted(range(len(docs)), key=lambda i: -sc[i])[:top_k]
        return SimpleNamespace(results=[SimpleNamespace(index=i, relevance_score=sc[i]) for i in order], total_tokens=len(docs) * 50)
classic.client = lean.client = Cl()
classic.sleep = lean.sleep = lambda s: None
qs = ["anticipatory bail arrest section 438", "cheque dishonour section 138 compounding", "section 401 murder sentence", "default bail chargesheet", "quash FIR settlement", "जमानत गिरफ्तारी", "curly quotes en-dash"]
same_r = same_s = tot = 0
for q in qs:
    for t in range(4):
        v = rng.normal(size=DIM).astype(np.float32); cur["v"] = v / np.linalg.norm(v)
        for court in (None, "sc", "hc"):
            a = classic.retrieve(q, 60, classic.court_mask(court)); b = lean.retrieve(q, 60, lean.court_mask(court))
            tot += 1; same_r += a["cand"] == b["cand"] and a["nums"] == b["nums"]
        ra, rb = classic.search(q, 10), lean.search(q, 10)
        for d in (ra, rb): d.pop("seconds", None)
        same_s += json.dumps(ra, sort_keys=True, default=str) == json.dumps(rb, sort_keys=True, default=str)
check(f"retrieve(): the same 60 candidates in the same order as the classic service ({tot} questions, with and without a court filter)", same_r == tot, (same_r, tot))
check(f"search(): the same reply (ranks, scores, passage text, names) as the classic service ({len(qs) * 4} questions)", same_s == len(qs) * 4, (same_s, len(qs) * 4))
kw_ok = True
for q in ('"bail" OR "arrest"', '"section 438"', '"जमानत"', '"cheque" OR "dishonour" OR "compounding"', '"quot"'):
    ra = [r[0] for r in classic.fts.execute("select rowid from f where f match ? order by bm25(f) limit 50", (q,))]
    rb = [r[0] for r in lean.fts.execute("select rowid from f where f match ? order by bm25(f) limit 50", (q,))]
    kw_ok = kw_ok and ra == rb
check("the keyword index returns the same rows in the same bm25 order from the file as from memory", kw_ok)

# ---- the next start reuses the file; a changed index rebuilds it; damage is repaired
lean2, _ = load(True)
check("second start: the file is reused (not rebuilt)", lean2.info["store"]["state"] == "reused")
mt0 = os.path.getmtime(SPATH)
info = store.read_info(SPATH)
check("the file's fingerprint says how many passages it holds", info and info["passages"] == 119 and info["total_chars"] == lean.metas.total_chars)
changed = os.path.join(tmp, "main_changed")
shutil.copytree(main, changed)
d_ = si._idx_dir(changed); f_ = sorted(g for g in os.listdir(d_) if g.endswith(".meta.jsonl.gz"))[0]
rows = [json.loads(l) for l in gzip.open(os.path.join(d_, f_), "rt", encoding="utf-8")]
rows[3]["text"] = rows[3]["text"] + " AND ONE WORD MORE"
with gzip.open(os.path.join(d_, f_), "wt", encoding="utf-8") as fh:
    for r in rows: fh.write(json.dumps(r, ensure_ascii=False) + "\n")
lean3, _ = load(True, idx=changed)
check("an index whose text differs by one word makes the old file stale: it is rebuilt, and the new text is what is served", lean3.info["store"]["state"].startswith("rebuilt") and lean3._text(3).endswith("AND ONE WORD MORE"))
lean4, _ = load(True)
check("and going back to the first index rebuilds again (the file never serves another index's text)", lean4.info["store"]["state"].startswith("rebuilt") and not lean4._text(3).endswith("AND ONE WORD MORE"))
open(SPATH, "wb").write(b"this is not a database")
lean5, _ = load(True)
check("a damaged file is replaced, not trusted", lean5.info["store"]["state"] == "built" and lean5._text(0) == classic.metas[0]["text"])
open(SPATH + ".building", "wb").write(b"half a file")
lean6, _ = load(True)
check("a leftover half-built file does not disturb a start that reuses the good file", lean6.info["store"]["state"] == "reused" and lean6._text(1) == classic.metas[1]["text"])
open(SPATH, "wb").write(b"damaged again")
lean7, _ = load(True)
check("a rebuild removes the leftover half-built file and replaces the damaged one", lean7.info["store"]["state"] == "built" and not os.path.exists(SPATH + ".building") and lean7._text(2) == classic.metas[2]["text"])

# ---- failures fall back to memory; refusals about the index still refuse
os.environ["SCI_STORE_PATH"] = os.path.join(tmp, "a_file_in_the_way", "x", "store.sqlite")
open(os.path.join(tmp, "a_file_in_the_way"), "w").write("not a directory")
fb, out = load(True)
fb.client = Cl(); fb.sleep = lambda s_: None; cur["v"] = np.ones(DIM, dtype=np.float32) / np.sqrt(DIM)
check("a store that cannot be written falls back to the in-memory service, says so, and answers the same", "stay in memory" in out and isinstance(fb.metas, list) and "store" not in fb.info and fb.search(qs[0], 10)["ok"])
os.environ["SCI_STORE_PATH"] = SPATH
wrongcommit = make_index(os.path.join(tmp, "wrongcommit"), 5000, [3], manifest={"main_index_commit": "zzz", "documents": 1, "passages": 3})
try:
    load(True, sides=(wrongcommit,)); ok = False
except ValueError as e:
    ok = "made for main index" in str(e)
check("a side index made for another main index is still refused with SCI_STORE on", ok)
os.environ.pop("SCI_STORE", None)

# ---- the store module on its own
c = store.Collector(os.path.join(tmp, "u.sqlite"))
c.keep(row(1, 0, "ab")); c.keep(row(1, 1, "c"))
d1 = c.digest(); c.abort()
c = store.Collector(os.path.join(tmp, "u2.sqlite"))
c.keep(row(1, 0, "a")); c.keep(row(1, 1, "bc"))
d2 = c.digest(); c.abort()
check("the fingerprint tells ('ab','c') from ('a','bc')", d1 != d2)
c = store.Collector(None)
c.keep({"doc": 1, "i": 0, "pn": "1", "section": "reasoning", "h": "x", "text": "no page key"})
check("a row that lacks one of the six fields is reported (the service then keeps the old path)", c.incomplete is not None)
c = store.Collector(None); r_ = row(3, 2, "the opening   lines\n of a header"); r_["section"] = "header"; c.keep(r_)
check("a header-type row is remembered with collapsed whitespace", c.header == {3: "the opening lines of a header"}, c.header)
check("SCI_STORE is off unless set to on", (os.environ.pop("SCI_STORE", None), store.enabled())[1] is False and (os.environ.__setitem__("SCI_STORE", "on"), store.enabled())[1] is True)
os.environ.pop("SCI_STORE", None)

# ---- the build-store command
os.environ.update(SCI_INDEX_DIR=main, SCI_SIDE_INDEXES=f"{side1},{side2}")
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    rc = S.main(["build-store"])
check("`sci_search_service.py build-store` builds or checks the file and prints its state", rc == 0 and '"state"' in buf.getvalue(), buf.getvalue()[:200])
os.environ.pop("SCI_STORE", None)

shutil.rmtree(tmp, ignore_errors=True)
print("\nALL PASSED" if not FAILS else f"\n{len(FAILS)} FAILED: {FAILS}")
sys.exit(1 if FAILS else 0)
