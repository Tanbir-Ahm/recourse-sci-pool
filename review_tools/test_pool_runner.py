"""Tests for review_tools/pool_runner.py on a small invented index and a fake service (no network, no spend). Run: python review_tools/test_pool_runner.py"""
import collections
import io
import json
import os
import re
import sys
import tempfile
from contextlib import redirect_stdout
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pool_runner as P
import real_questions as RQ

FAILS = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{detail}]"))
    if not cond:
        FAILS.append(name)


DIM = 32


def vec(text):
    v = np.zeros(DIM, dtype=np.float32)
    for w in re.findall(r"[a-z0-9]+", text.lower()):
        v[hash(w) % DIM] += 1.0
    return v / (np.linalg.norm(v) or 1.0)


class FakeClient:
    """embed: hashed bag of words; rerank: share of the question's words found in the passage, with fixed overrides. Counts calls and bills tokens as the real service does."""

    def __init__(self, overrides=None):
        self.overrides, self.embed_calls, self.rerank_calls = overrides or {}, 0, 0

    def embed(self, texts, model, input_type):
        self.embed_calls += 1
        return SimpleNamespace(embeddings=[vec(texts[0]).tolist()], total_tokens=len(texts[0]) // 4)

    def rerank(self, query, docs, model, top_k):
        self.rerank_calls += 1
        qw = set(re.findall(r"[a-z0-9]+", query.lower()))
        res = []
        for i, d in enumerate(docs):
            score = len(qw & set(re.findall(r"[a-z0-9]+", d.lower()))) / (len(qw) or 1)
            for frag, val in self.overrides.items():
                if frag in d:
                    score = val
            res.append(SimpleNamespace(index=i, relevance_score=score))
        res.sort(key=lambda r: -r.relevance_score)
        return SimpleNamespace(results=res[:top_k], total_tokens=sum(len(d) // 4 + len(query) // 4 for d in docs))


TOPICS = ["bail anticipatory arrest", "cheque dishonour compounding", "murder sentence death", "default bail chargesheet", "quash fir settlement", "ndps statement confession"]
metas = []
for d in range(12):
    for i in range(10):
        topic = TOPICS[(d + i) % len(TOPICS)]
        text = f"{i + 1}. In case {d} paragraph {i} the court considered {topic} and section {400 + (d % 4)} as it arose on the record."
        metas.append({"doc": 100 + d, "i": i, "pn": str(i + 1), "page": i // 3 + 1, "section": ["reasoning", "facts", "header", "argument"][i % 4], "h": f"h{d}-{i}", "text": text})
# an identical passage in two judgments (a copy), strongly relevant to the first topic
metas.append({"doc": 200, "i": 0, "pn": "1", "page": 1, "section": "reasoning", "h": "hdup", "text": "1. Anticipatory bail and arrest: the court held that bail anticipatory arrest must be decided on the facts. COPY"})
metas.append({"doc": 201, "i": 0, "pn": "1", "page": 1, "section": "reasoning", "h": "hdup", "text": "1. Anticipatory bail and arrest: the court held that bail anticipatory arrest must be decided on the facts. COPY"})
M = np.stack([vec(m["text"]) for m in metas]).astype(np.float16)
hdocs = collections.defaultdict(set)
for m in metas:
    hdocs[m["h"]].add(m["doc"])
fts = P.build_fts(metas)
title = lambda doc: f"Case {doc} v. State"
Q = "Can anticipatory bail and arrest be decided on the facts under section 400?"


def engine(client=None, cap=10**9, site=None):
    return P.Engine(metas, M, client or FakeClient(), P.Spend(cap), fts, site, sleep=lambda s: None)


# ---- the versions ------------------------------------------------------------------------------------------------------------------------------------
e = engine()
lists = e.lists_for(Q)
check("without a rewrite the versions are A, B and E only", sorted(lists) == ["A today", "B no repeats", "E no multiplier"], sorted(lists))
check("each list holds ten passages", all(len(v) == 10 for v in lists.values()))
check("A and E share one re-rank call and B has its own: two calls, one embedding each for A and B", e.client.rerank_calls == 2 and e.client.embed_calls == 2, (e.client.rerank_calls, e.client.embed_calls))
check("B has no two passages with identical text", len({metas[r]["h"] for r in lists["B no repeats"]}) == 10)
check("A can hold both copies of an identical passage", sum(1 for r in lists["A today"] if metas[r]["h"] == "hdup") in (0, 2) and any(metas[r]["h"] == "hdup" for r in lists["A today"]), [metas[r]["h"] for r in lists["A today"]])
e2 = engine()
l2 = e2.lists_for(Q, "Whether the protection of anticipatory bail may be refused on the facts (section 438 CrPC)")
check("with a rewrite C and F appear", {"C rewrite", "F merged"} <= set(l2) and len(l2) == 5, sorted(l2))
check("a rewritten question costs five re-rank calls (A/E, B, C, and two for F)", e2.client.rerank_calls == 5, e2.client.rerank_calls)
e3 = engine(site=lambda q: [3, 4, 5])
check("the site arm is whatever the site function shows, whole", e3.lists_for(Q)["S site shown"] == [3, 4, 5])

# weights: a header passage that the raw scores like a little more than a reasoning passage
ov = FakeClient({"HEADER-ONE": 0.60, "REASON-ONE": 0.58})
metas2 = [dict(m) for m in metas] + [
    {"doc": 300, "i": 0, "pn": "1", "page": 1, "section": "header", "h": "hx1", "text": "1. HEADER-ONE anticipatory bail arrest facts record section 400 court"},
    {"doc": 301, "i": 0, "pn": "1", "page": 1, "section": "reasoning", "h": "hx2", "text": "1. REASON-ONE anticipatory bail arrest facts record section 400 court"}]
M2 = np.stack([vec(m["text"]) for m in metas2]).astype(np.float16)
eng2 = P.Engine(metas2, M2, ov, P.Spend(10**9), P.build_fts(metas2), None, sleep=lambda s: None)
ls = eng2.lists_for(Q)
ia, ie = [metas2[r]["h"] for r in ls["A today"]], [metas2[r]["h"] for r in ls["E no multiplier"]]
check("E keeps the raw order (the header passage first); A, which applies the passage-type weight, puts reasoning above it or drops the header passage",
      "hx1" in ie and "hx2" in ie and ie.index("hx1") < ie.index("hx2") and "hx2" in ia and ("hx1" not in ia or ia.index("hx2") < ia.index("hx1")), (ia[:6], ie[:6]))

# ---- spend and the cap ------------------------------------------------------------------------------------------------------------------------------
sp = P.Spend(10)
cl = FakeClient()
eng3 = P.Engine(metas, M, cl, sp, fts, None, sleep=lambda s: None)
try:
    eng3.lists_for(Q)
    ok = False
except P.SpendCapReached:
    ok = cl.rerank_calls == 0
check("a re-rank call that would cross the cap is not made", ok, cl.rerank_calls)
sp2 = P.Spend(10**9)
engine_ok = P.Engine(metas, M, FakeClient(), sp2, fts, None, sleep=lambda s: None)
engine_ok.lists_for(Q)
check("tokens billed are the service's own counts, and the dollar estimate follows", sp2.rerank > 0 and abs(sp2.dollars() - (sp2.rerank * 0.05 + sp2.embed * 0.12) / 1e6) < 1e-12 and sp2.as_dict()["rerank_calls"] == 2)


class Flaky:
    def __init__(self):
        self.n = 0

    def go(self):
        self.n += 1
        if self.n < 3:
            err = type("RateLimitError", (Exception,), {})()
            raise err
        return "ok"


fl = Flaky()
check("a rate-limit error is retried and then succeeds", P.call(fl.go, sleep=lambda s: None) == "ok" and fl.n == 3)
try:
    P.call(lambda: (_ for _ in ()).throw(ValueError("bad")), sleep=lambda s: None)
    ok = False
except ValueError:
    ok = True
check("any other error is raised at once", ok)

# ---- the pool ------------------------------------------------------------------------------------------------------------------------------------------
q = {"id": "R99", "domain": "B", "kind": "legal", "text": Q, "half": "dev"}
rec = P.build_question(q, lists, metas, hdocs, title)
rows = rec["rows"]
top5 = {metas[r]["h"] for v, lst in lists.items() for r in lst[:5]}
check("the rows are the top five of every version, collapsed by identical text", {r["h"] for r in rows} == top5 and len(rows) == len(top5), (len(rows), len(top5)))
check("rows are numbered 1..n and carry the judgment, title, paragraph, page and identical-text copies", [r["n"] for r in rows] == list(range(1, len(rows) + 1)) and all(r["title"].startswith("Case ") for r in rows))
dup = [r for r in rows if r["h"] == "hdup"]
check("an identical passage appears once, with the other judgment listed", len(dup) == 1 and dup[0]["also"] == [201] or dup[0]["also"] == [200], dup[0]["also"] if dup else None)
check("the shuffle is fixed: the same input gives the same order", [r["h"] for r in rows] == [r["h"] for r in P.build_question(q, lists, metas, hdocs, title)["rows"]])
check("rows do not say which version found them in their order: the order is not A's own order", [r["h"] for r in rows][:5] != [metas[x]["h"] for x in lists["A today"][:5]])
check("each version's ordered results are kept for the scorer, with identical-text copies", all(len(v) == 10 for v in rec["lists"].values()) and {"doc", "h", "also"} == set(rec["lists"]["A today"][0]))
check("a passage found at rank 8 by one version only is not in the pool", all(not (metas[r]["h"] not in top5 and metas[r]["h"] in {x["h"] for x in rows}) for r in lists["A today"][5:]))
check("the record names no answer: no key, no stale label", not any(k in rec for k in ("key", "stale", "authorities")))

# ---- run, resume and cap ---------------------------------------------------------------------------------------------------------------------------
tmp = tempfile.mkdtemp()
qs = [{"id": "R90", "domain": "B", "kind": "legal", "text": Q, "half": "dev"}, {"id": "R91", "domain": "C", "kind": "everyday", "text": "cheque dishonour compounding costs", "half": "dev"}]
eng4 = engine()
logs = []
ordered, stopped = P.run({}, qs, {"R91": "Compounding of a cheque dishonour offence and costs"}, eng4, hdocs, title, tmp, log=logs.append)
check("both questions are run and saved one line each", [r["qid"] for r in ordered] == ["R90", "R91"] and stopped is None and len(open(os.path.join(tmp, "questions.jsonl")).read().strip().split("\n")) == 2)
check("the rewritten question has C and F, the other does not", "F merged" in ordered[1]["lists"] and "F merged" not in ordered[0]["lists"])
check("each record says what it spent", ordered[0]["spend"]["rerank_tokens"] > 0 and ordered[1]["spend"]["rerank_tokens"] > ordered[0]["spend"]["rerank_tokens"])
calls = eng4.client.rerank_calls
ordered2, _ = P.run({}, qs, {"R91": "x"}, eng4, hdocs, title, tmp, log=logs.append)
check("a second run on the same folder repeats nothing and makes no call", eng4.client.rerank_calls == calls and [r["qid"] for r in ordered2] == ["R90", "R91"])
tmp2 = tempfile.mkdtemp()
one = engine().spend
probe = engine()
probe.lists_for(Q)
cap = probe.spend.rerank + 1000                    # room for the first question, not for the second
eng5 = engine(cap=cap)
ordered3, stopped3 = P.run({}, qs, {"R91": "Compounding of a cheque dishonour offence and costs"}, eng5, hdocs, title, tmp2, log=logs.append)
check("at the cap the run stops before the next question, keeps what it has, and says so", [r["qid"] for r in ordered3] == ["R90"] and stopped3 and "R91" in stopped3 and len(open(os.path.join(tmp2, "questions.jsonl")).read().strip().split("\n")) == 1, stopped3)
check("the run never bills past the cap", eng5.spend.rerank <= cap)

# ---- titles ------------------------------------------------------------------------------------------------------------------------------------------------
import gzip as _gz
idx = tempfile.mkdtemp()
os.makedirs(os.path.join(idx, "index"))
with _gz.open(os.path.join(idx, "index", "000000.docs.jsonl.gz"), "wt", encoding="utf-8") as fh:
    fh.write(json.dumps({"doc": 1, "case": {"pet": "Arnesh Kumar", "resp": "State of Bihar", "date": "2014-07-02"}}) + "\n")
    fh.write(json.dumps({"doc": 2, "src": {"source": "bucket", "title": "MIHIR RAJESH SHAH   versus STATE OF MAHARASHTRA", "date": "2025-11-06"}}) + "\n")
    fh.write(json.dumps({"doc": 3}) + "\n")
tt = P.titles(idx, [{"doc": 3, "section": "header", "pn": "1", "text": "IN THE SUPREME COURT   OF INDIA header text"}])
check("a crawl judgment is titled from its case record, a bucket judgment from the title it arrived with, else from its header text",
      tt(1) == "Arnesh Kumar v. State of Bihar (2014-07-02)" and tt(2) == "MIHIR RAJESH SHAH versus STATE OF MAHARASHTRA (2025-11-06)" and tt(3) == "IN THE SUPREME COURT OF INDIA header text" and tt(4) is None, [tt(1), tt(2), tt(3), tt(4)])
pp = os.path.join(idx, "pool.json")
json.dump({"run": {}, "questions": [{"qid": "R1", "rows": [{"doc": 2, "title": None}, {"doc": 1, "title": "kept"}, {"doc": 9, "title": None}]}]}, open(pp, "w"))
check("retitle fills only the empty titles, counts those it could not fill, and leaves the rest alone", P.retitle(pp, idx) == (1, 1) and [r["title"] for r in json.load(open(pp))["questions"][0]["rows"]] == ["MIHIR RAJESH SHAH versus STATE OF MAHARASHTRA (2025-11-06)", "kept", None])
check("the run record says the titles were filled afterwards", json.load(open(pp))["run"]["titles_filled_afterwards"]["rows"] == 1)

# ---- a side index ------------------------------------------------------------------------------------------------------------------------------------
import shutil
import sci_index as si


def make_side(dirpath, docs=((900, "Side Case v. State"),), commit="abc123", model=None, width=DIM, extra_text=""):
    texts = [f"1. {extra_text} The side judgment {d} holds that sealing of electronic records requires a certificate under section 65B of the evidence act as a condition." for d, _ in docs]
    passages = [{"doc": d, "i": 0, "pn": "1", "page": 1, "method": "para", "section": "reasoning", "basis": "x", "pos": 0, "prec": 0, "h": f"side{d}", "text": t} for (d, _), t in zip(docs, texts)]
    vecs = np.stack([vec(t) if width == DIM else np.ones(width, dtype=np.float32) for t in texts]).astype(np.float16)
    si.write_block_files(dirpath, 5_000_000_000, 250, [{"doc": d, "hash": "h", "passages": 1} for d, _ in docs], passages, vecs, 100)
    with open(os.path.join(dirpath, "index", "MODEL"), "w") as fh:
        fh.write((model or si.MODEL) + "\n")
    with open(os.path.join(dirpath, "SUPPLEMENT.json"), "w") as fh:
        json.dump({"main_index_commit": commit, "documents": len(docs), "passages": len(docs), "built": "2026-10-09T00:00:00Z", "documents_detail": [{"doc": d, "title": t} for d, t in docs], "docs_list": None}, fh)
    return dirpath


side = make_side(tempfile.mkdtemp())
metas_before, rows_before = len(metas), M.shape[0]
m2, M2c, info, extra = P.load_supplement(side, metas, M, "abc123")
check("a side index is added after the main one: more passages, the same width, the main arrays untouched", len(m2) == metas_before + 1 and M2c.shape[0] == rows_before + 1 and len(metas) == metas_before and M.shape[0] == rows_before)
check("the run record names the side index and fingerprints its manifest", info["documents"] == 1 and info["passages"] == 1 and len(info["manifest_sha256"]) == 64 and info["made_for_main_index"] == "abc123")
check("its documents get the title from the list", extra == {900: "Side Case v. State"} and P.titles([side], m2, extra)(900) == "Side Case v. State")
eng_s = P.Engine(m2, M2c, FakeClient(), P.Spend(10 ** 9), P.build_fts(m2), None, sleep=lambda s: None)
found = eng_s.lists_for("Is a certificate under section 65B of the evidence act required for electronic records?")
check("a passage that only the side index holds can be found, and is among the results of a version", any(m2[r]["doc"] == 900 for lst in found.values() for r in lst), {v: [m2[r]["doc"] for r in lst[:5]] for v, lst in found.items()})
for name, kw, frag in (("another main-index commit", dict(head="zzz"), "made for main index"),):
    try:
        P.load_supplement(side, metas, M, kw["head"])
        raised = None
    except ValueError as e:
        raised = str(e)
    check(f"refused: {name}", raised and frag in raised, raised)
check("another main-index commit is accepted when the run says so", P.load_supplement(side, metas, M, "zzz", allow_other=True)[2]["documents"] == 1)
try:
    P.load_supplement(make_side(tempfile.mkdtemp(), model="some-other-model"), metas, M, "abc123")
    raised = None
except ValueError as e:
    raised = str(e)
check("refused: vectors made by another model", raised and "some-other-model" in raised, raised)
try:
    P.load_supplement(make_side(tempfile.mkdtemp(), docs=((100, "Clash"),)), metas, M, "abc123")
    raised = None
except ValueError as e:
    raised = str(e)
check("refused: a document the main index already has passages for", raised and "already has passages" in raised, raised)
try:
    P.load_supplement(make_side(tempfile.mkdtemp(), width=8), metas, M, "abc123")
    raised = None
except ValueError as e:
    raised = str(e)
check("refused: a different vector width", raised and "width" in raised, raised)
try:
    P.load_supplement(tempfile.mkdtemp(), metas, M, "abc123")
    raised = None
except ValueError as e:
    raised = str(e)
check("refused: a folder that is not a side index", raised and "SUPPLEMENT.json" in raised, raised)
side2 = make_side(tempfile.mkdtemp(), docs=((901, "Second Side v. State"),))
m3, M3c, info2, extra2 = P.load_supplement(side2, m2, M2c, "abc123")
check("a second side index is added after the first: both sets of passages are searchable, nothing already loaded is changed", len(m3) == len(m2) + 1 and M3c.shape[0] == M2c.shape[0] + 1 and {m["doc"] for m in m3} >= {900, 901} and len(m2) == metas_before + 1)
try:
    P.load_supplement(make_side(tempfile.mkdtemp(), docs=((900, "Again"),)), m2, M2c, "abc123")
    raised = None
except ValueError as e:
    raised = str(e)
check("refused: a second side index that repeats a document of the first", raised and "already has passages" in raised, raised)
buf = io.StringIO()
with redirect_stdout(buf):
    P.main(["--out", os.path.join(tmp, "s2"), "--max-rerank-tokens", "1000", "--dry-run", "--no-site", "--supplement", "/side/one", "--supplement", "/side/two"])
check("a dry run names every side index it would use", "side index /side/one" in buf.getvalue() and "side index /side/two" in buf.getvalue(), buf.getvalue())
buf = io.StringIO()
with redirect_stdout(buf):
    rc_s = P.main(["--out", os.path.join(tmp, "s"), "--max-rerank-tokens", "1000", "--dry-run", "--no-site", "--supplement", "/some/side/index"])
check("a dry run names the side index it would use", rc_s == 0 and "side index /some/side/index" in buf.getvalue(), buf.getvalue())

# ---- the guards in main ---------------------------------------------------------------------------------------------------------------------------
buf = io.StringIO()
with redirect_stdout(buf):
    rc_dry = P.main(["--out", os.path.join(tmp, "x"), "--max-rerank-tokens", "1000", "--dry-run", "--no-site"])
check("a dry run shows the plan and calls nothing", rc_dry == 0 and "questions (dev)" in buf.getvalue(), buf.getvalue())
buf = io.StringIO()
with redirect_stdout(buf):
    rc_sealed = P.main(["--out", os.path.join(tmp, "y"), "--max-rerank-tokens", "1000", "--half", "sealed", "--dry-run"])
check("the sealed half is refused without --final", rc_sealed == 3 and "refused" in buf.getvalue(), buf.getvalue())
real_head = P.index_head
P.index_head = lambda d: "0" * 40
buf = io.StringIO()
with redirect_stdout(buf):
    rc_head = P.main(["--out", os.path.join(tmp, "z"), "--max-rerank-tokens", "1000", "--dry-run"])
P.index_head = real_head
check("another index head is refused", rc_head == 1 and "refused" in buf.getvalue(), buf.getvalue())
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "pool_runner.py"), encoding="utf-8").read()
check("the runner never reads the private key", "real30_key" not in src.replace("The private key is never read here", "") and "real30_score" not in src)

print()
print("FAILED: " + ", ".join(FAILS) if FAILS else "all passed")
sys.exit(1 if FAILS else 0)
