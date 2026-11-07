"""Tests for the low-memory load of sci_search_service / sci_index (FOLLOW_UPS 2dq, 2026-11-07): the vectors are read straight into one pre-sized array instead of being collected and copied with np.vstack,
the metadata rows are trimmed as they are read, and a question is compared with the passages in blocks of 5000 rather than 50000. Everything is checked against the classic path on a small invented index
(main index + two side indexes) on disk. No network, no spend. Run: python test_sci_load_lowmem.py"""
import json, os, shutil, sys, tempfile
from types import SimpleNamespace
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sci_index as si
import sci_search_service as S

FAILS = []
def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{detail}]"))
    if not cond:
        FAILS.append(name)

DIM = 16
rng = np.random.default_rng(5)
tmp = tempfile.mkdtemp(prefix="lowmem_")
os.environ["SCI_INDEX_COMMIT"] = "abc1234"
for k in ("SCI_LOAD_COPY", "SCI_SIM_BLOCK", "SCI_NAMES_TABLE", "SCI_QUOTES", "SCI_AUTHORITY"):
    os.environ.pop(k, None)
os.environ["SCI_NAMES_TABLE"] = os.path.join(tmp, "no_such_names_table.json.gz")

def row(doc, i, text):
    # the four fields the service drops (method, basis, pos, prec) are there on purpose
    return {"doc": doc, "i": i, "pn": str(i + 1), "page": 1 + i // 3, "section": ["reasoning", "facts", "header", "argument"][i % 4], "h": f"h{doc}-{i}", "method": "m", "basis": "b", "pos": 0.5, "prec": 1, "text": f"{i + 1}. case {doc} para {i} {text}"}

def make_index(path, first_doc, shard_sizes, dtype=np.float16, dim=DIM, manifest=None):
    os.makedirs(path, exist_ok=True)
    si._claim_model(path, S.EMBED_MODEL)
    start, doc = 0, first_doc
    for n in shard_sizes:
        metas = [row(doc + k // 4, k % 4, "court considered bail and arrest") for k in range(n)]
        docs = [{"doc": doc + k, "hash": f"x{doc + k}"} for k in range((n + 3) // 4)]
        vecs = rng.normal(size=(n, dim)).astype(dtype)
        si.write_block_files(path, start, 10, docs, metas, vecs, 1)
        start += 10
        doc += (n + 3) // 4
    if manifest is not None:
        json.dump(manifest, open(os.path.join(path, "SUPPLEMENT.json"), "w"))
    return path

main = make_index(os.path.join(tmp, "main"), 1, [7, 5, 9])
sup = {"main_index_commit": "abc1234", "documents": 3, "passages": 6}
side1 = make_index(os.path.join(tmp, "side1"), 100, [6], manifest=sup)
side2 = make_index(os.path.join(tmp, "side2"), 200, [4, 3], manifest=sup)

# ---- vector_info reads headers only and says what np.vstack would give
rows, dt, width = si.vector_info(main)
check("vector_info: rows, dtype and width of an index from the file headers", (rows, str(dt), width) == (21, "float16", DIM), (rows, dt, width))
check("vector_info of an empty folder: no rows, no dtype, no width", si.vector_info(os.path.join(tmp, "nothing")) == (0, None, None))
mixed = make_index(os.path.join(tmp, "mixed"), 1, [3])
extra = rng.normal(size=(2, DIM + 1)).astype(np.float16)
si.write_block_files(mixed, 10, 10, [{"doc": 50, "hash": "q"}], [row(50, 0, "x"), row(50, 1, "y")], extra, 1)
check("vector_info says -1 for shards of different widths (the caller then keeps the old path)", si.vector_info(mixed)[2] == -1, si.vector_info(mixed))

# ---- _load_index: out= and keep=
mt, M1, dw1 = si._load_index(main)
out = np.empty((21, DIM), dtype=np.float16)
mt2, M2, dw2 = si._load_index(main, out=out)
check("_load_index(out=) fills the given array and returns it; the same vectors, metadata and documents as without", M2 is out and np.array_equal(M1, M2) and mt == mt2 and dw1 == dw2)
mt3, _, _ = si._load_index(main, out=np.empty((21, DIM), dtype=np.float16), keep=S._slim)
check("_load_index(keep=) trims each row as it is read: only the fields the service uses", mt3 == [S._slim(m) for m in mt] and all("method" not in m for m in mt3))
for bad, why in ((np.empty((20, DIM), dtype=np.float16), "too few rows"), (np.empty((22, DIM), dtype=np.float16), "too many rows"), (np.empty((21, DIM + 1), dtype=np.float16), "wrong width")):
    try:
        si._load_index(main, out=bad); ok = False
    except ValueError:
        ok = True
    check(f"_load_index(out=) refuses an array that does not fit ({why})", ok)

# ---- the service: new path equals the classic path, byte for byte
os.environ["SCI_LOAD_COPY"] = "on"
old = S.SearchService.load(main, side_dirs=[side1, side2], client=object())
os.environ.pop("SCI_LOAD_COPY")
new = S.SearchService.load(main, side_dirs=[side1, side2], client=object())
check("pre-sized load: the vectors are identical to the classic load (same dtype, shape and every value)", old.M.dtype == new.M.dtype and old.M.shape == new.M.shape and np.array_equal(old.M, new.M), (old.M.shape, new.M.shape))
check("pre-sized load: the metadata, titles, documents, court table and info are identical", old.metas == new.metas and old.info.keys() == new.info.keys() and
      {k: v for k, v in old.info.items() if k != "load_seconds"} == {k: v for k, v in new.info.items() if k != "load_seconds"})
check("pre-sized load: 21 + 6 + 7 = 34 passages, the side indexes' passages after the main index's", len(new.metas) == 34 and new.M.shape[0] == 34 and new.info["passages_main"] == 21, (len(new.metas), new.info.get("passages_main")))
check("pre-sized load: the keyword index holds every passage", new.fts.execute("select count(*) from f_docsize").fetchone()[0] == 34)
check("the service no longer carries the four unused fields", all(set(m) <= set(S.KEEP) for m in new.metas))
check("pre-sized load: the matrix is one array that owns its memory and is contiguous (nothing was stacked afterwards)", new.M.flags["OWNDATA"] and new.M.flags["C_CONTIGUOUS"] and new.M.shape[0] == 34, (new.M.flags["OWNDATA"], new.M.flags["C_CONTIGUOUS"]))
pa = S._preallocate(main, [side1, side2])
check("_preallocate: one array of 34 rows, float16, for the main index and both side indexes", pa is not None and pa.shape == (34, DIM) and pa.dtype == np.float16)
os.environ["SCI_LOAD_COPY"] = "on"
check("_preallocate: SCI_LOAD_COPY=on turns it off (the way back)", S._preallocate(main, [side1, side2]) is None)
os.environ.pop("SCI_LOAD_COPY")
check("_preallocate: shards of different widths: the classic path is kept (None)", S._preallocate(mixed, []) is None)

# ---- inconsistent side indexes: the same refusals as before, on either path
wide = make_index(os.path.join(tmp, "wide"), 300, [4], dim=DIM + 8, manifest=sup)
errs = []
for flag in ("on", None):
    if flag: os.environ["SCI_LOAD_COPY"] = flag
    else: os.environ.pop("SCI_LOAD_COPY", None)
    try:
        S.SearchService.load(main, side_dirs=[wide], client=object()); errs.append("no error")
    except ValueError as e:
        errs.append(str(e)[:60])
check("a side index of another vector width is refused with the same message on both paths", errs[0] == errs[1] and "width" in errs[0], errs)
wrongcommit = make_index(os.path.join(tmp, "wrongcommit"), 400, [3], manifest={"main_index_commit": "zzz", "documents": 1, "passages": 3})
errs = []
for flag in ("on", None):
    if flag: os.environ["SCI_LOAD_COPY"] = flag
    else: os.environ.pop("SCI_LOAD_COPY", None)
    try:
        S.SearchService.load(main, side_dirs=[wrongcommit], client=object()); errs.append("no error")
    except ValueError as e:
        errs.append(str(e)[:50])
check("a side index made for another main index is refused with the same message on both paths", errs[0] == errs[1] and "made for main index" in errs[0], errs)
clash = make_index(os.path.join(tmp, "clash"), 1, [3], manifest=sup)        # documents 1.. exist in the main index too
errs = []
for flag in ("on", None):
    if flag: os.environ["SCI_LOAD_COPY"] = flag
    else: os.environ.pop("SCI_LOAD_COPY", None)
    try:
        S.SearchService.load(main, side_dirs=[clash], client=object()); errs.append("no error")
    except ValueError as e:
        errs.append(str(e)[:50])
check("a side index repeating a document of the main index is refused with the same message on both paths", errs[0] == errs[1] and "already has passages" in errs[0], errs)
os.environ.pop("SCI_LOAD_COPY", None)
check("no side indexes at all: the load still works and equals the classic one", S.SearchService.load(main, client=object()).M.shape == (21, DIM))

# ---- the query block size
check("sim_block: default 5000", S.sim_block() == 5000)
for val, want in (("50000", 50000), ("1000", 5000), ("0", 5000), ("999999", 100000), ("junk", 5000), ('"20000"', 20000)):
    os.environ["SCI_SIM_BLOCK"] = val
    check(f"sim_block: SCI_SIM_BLOCK={val} gives {want}", S.sim_block() == want, S.sim_block())
os.environ.pop("SCI_SIM_BLOCK")

# a matrix of 23,000 rows spans several blocks of 5000; the candidates must be the same for 5000 and 50000
N = 23000
BM = rng.normal(size=(N, DIM)).astype(np.float16)
BM = (BM / np.linalg.norm(BM.astype(np.float32), axis=1, keepdims=True)).astype(np.float16)
bm_metas = [{"doc": 1 + i // 4, "i": i % 4, "pn": str(i), "page": 1, "section": "reasoning", "h": f"h{i}", "text": f"{i}. the court considered bail and arrest on the record number {i}"} for i in range(N)]
cur = {"v": None}
class Fake:
    def embed(self, texts, **k):
        return SimpleNamespace(embeddings=[cur["v"].tolist()], total_tokens=1)
sv = S.SearchService(bm_metas, BM, Fake(), lambda d: f"Case {d}", info={"index_commit": "abc1234", "passages": N}, sleep=lambda s: None)
same = 0
trials = 40
for t in range(trials):
    v = rng.normal(size=DIM).astype(np.float32); cur["v"] = v / np.linalg.norm(v)
    res = {}
    for blk in ("50000", "5000", "7000"):
        os.environ["SCI_SIM_BLOCK"] = blk
        r = sv.retrieve("bail and arrest", pool=60); res[blk] = (r["cand"], r["nums"])
    same += res["50000"] == res["5000"] == res["7000"]
os.environ.pop("SCI_SIM_BLOCK")
check("the candidate list for a question is identical for blocks of 5000, 7000 and 50000 (40 random questions over 23,000 passages, five blocks)", same == trials, f"{same}/{trials}")

shutil.rmtree(tmp, ignore_errors=True)
print("\nALL PASSED" if not FAILS else f"\n{len(FAILS)} FAILED: {FAILS}")
sys.exit(1 if FAILS else 0)
