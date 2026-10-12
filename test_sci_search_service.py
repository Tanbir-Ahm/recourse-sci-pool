"""Tests for sci_search_service.py on a small invented index and a fake Voyage client (no network beyond localhost, no spend). Run: python test_sci_search_service.py"""
import json, os, re, sys, threading, urllib.error, urllib.request
from types import SimpleNamespace
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "review_tools"))
import sci_search_service as S
import pool_runner as P

FAILS = []
def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{detail}]"))
    if not cond:
        FAILS.append(name)

DIM = 32
def vec(text):
    v = np.zeros(DIM, dtype=np.float32)
    for w in re.findall(r"[a-z0-9]+", text.lower()):
        v[sum(map(ord, w)) % DIM] += 1.0          # stable across runs
    return v / (np.linalg.norm(v) or 1.0)

class FakeClient:
    def __init__(self, fail=None):
        self.embed_calls = self.rerank_calls = 0
        self.fail = fail
    def embed(self, texts, model, input_type):
        self.embed_calls += 1
        if self.fail == "embed":
            raise RuntimeError("voyage down")
        return SimpleNamespace(embeddings=[vec(texts[0]).tolist()], total_tokens=len(texts[0]) // 4)
    def rerank(self, query, docs, model, top_k):
        self.rerank_calls += 1
        qw = set(re.findall(r"[a-z0-9]+", query.lower()))
        res = [SimpleNamespace(index=i, relevance_score=len(qw & set(re.findall(r"[a-z0-9]+", d.lower()))) / (len(qw) or 1)) for i, d in enumerate(docs)]
        res.sort(key=lambda r: -r.relevance_score)
        return SimpleNamespace(results=res[:top_k], total_tokens=sum(len(d) // 4 + len(query) // 4 for d in docs))

TOPICS = ["bail anticipatory arrest", "cheque dishonour compounding", "murder sentence death", "default bail chargesheet", "quash fir settlement", "ndps statement confession"]
metas = []
for d in range(12):
    for i in range(10):
        topic = TOPICS[(d + i) % len(TOPICS)]
        metas.append({"doc": 100 + d, "i": i, "pn": str(i + 1), "page": i // 3 + 1, "section": ["reasoning", "facts", "header", "argument"][i % 4], "h": f"h{d}-{i}",
                      "method": "x", "basis": "y", "pos": 0, "prec": 0, "text": f"{i + 1}. In case {d} paragraph {i} the court considered {topic} and section {400 + (d % 4)} as it arose on the record."})
M = np.stack([vec(m["text"]) for m in metas]).astype(np.float16)
Q = "Can anticipatory bail and arrest be decided on the facts under section 400?"
title = lambda doc: f"Case {doc} v. State (01/02/2020)"
slim = [S._slim(m) for m in metas]
def svc(client=None, **kw):
    return S.SearchService(slim, M, client or FakeClient(), title, info={"index_commit": "abc123", "as_of": "2026-07-13", "passages": len(slim)}, sleep=lambda s: None, **kw)

# ---- the same list as the experiments' code (recipe B) ----
fts_ref = P.build_fts(metas)
eng = P.Engine(metas, M, FakeClient(), P.Spend(10**9), fts_ref, None, sleep=lambda s: None)
a = eng.retrieve(Q)
final = {r: s * eng.weight(r, a["nums"]) for r, s in eng.rerank(Q, a["cand"]).items()}
ref = eng.order_by(final)[:10]
s1 = svc()
check("the service ranks exactly as pool_runner.Engine does (recipe B), ten passages", [r for r, _ in s1.ranked(Q, 10)] == ref and len(ref) == 10, (ref, [r for r, _ in s1.ranked(Q, 10)]))
s1c = svc(); s1c.ranked(Q, 10)
check("one embedding and one re-rank call per question", s1c.client.embed_calls == 1 and s1c.client.rerank_calls == 1, (s1c.client.embed_calls, s1c.client.rerank_calls))
check("the candidates (merged first stage) are the same too", s1.retrieve(Q)["cand"] == a["cand"] and len(a["cand"]) == 60)
for q in ("section 401 cheque", "murder sentence death penalty", "ndps"):
    ra = eng.retrieve(q)["cand"]
    check(f"contentless keyword index gives the same candidates ({q!r})", svc().retrieve(q)["cand"] == ra)

# ---- the answer ----
res = s1.search(Q)
check("the answer says what it is: tier, recipe, index commit, as-of date, disclaimer", res["tier"] == S.TIER and res["recipe"] == "B" and res["index_commit"] == "abc123" and res["as_of"] == "2026-07-13" and "does not say whether a decision is still good law" in res["disclaimer"])
check("each result has rank, case name with date, paragraph, page, passage type, score, text", all(set(r) >= {"rank", "doc", "case_name", "paragraph", "page", "passage_type", "score", "text", "passage_id"} for r in res["results"]) and [r["rank"] for r in res["results"]] == list(range(1, 11)))
check("the only mention of 'good law' is the disclaimer saying the search does not decide it", "good law" not in json.dumps(res["results"]) and res["disclaimer"].count("good law") == 1 and "does not say whether" in res["disclaimer"])
s2 = svc(max_text=40)
check("passage text is cut to SCI_MAX_TEXT", all(len(r["text"]) <= 43 for r in s2.search(Q)["results"]) and s2.search(Q)["results"][0]["text"].endswith("..."))
check("k limits the list (1 to 20)", len(svc().search(Q, 3)["results"]) == 3 and len(svc().search(Q, 99)["results"]) == 20 and len(svc().search(Q, 0)["results"]) == 1)

# ---- refusals ----
def refused(fn):
    try:
        fn()
    except S.Refused as r:
        return r.status
    return None
check("an empty question is refused (400)", refused(lambda: svc().search("   ")) == 400 and refused(lambda: svc().search(None)) == 400)
check("a very long question is refused (400)", refused(lambda: svc().search("x" * 2001)) == 400)
check("a bad k is refused (400)", refused(lambda: svc().search(Q, "ten")) == 400)
off = svc(enabled=False)
check("switched off: 503 and no Voyage call", refused(lambda: off.search(Q)) == 503 and off.client.embed_calls == 0)
cap = svc(daily_rerank_tokens=1)
cap.search(Q)
check("daily cap: the question that finds the allowance spent gets 429, with no further call", refused(lambda: cap.search(Q)) == 429 and cap.client.rerank_calls == 1)
clock = [1_000_000.0]
c2 = svc(daily_rerank_tokens=1, clock=lambda: clock[0])
c2.search(Q); clock[0] += 86400
check("the allowance renews on the next UTC day", refused(lambda: c2.search(Q)) is None)

# ---- HTTP ----
from http.server import ThreadingHTTPServer
def start(service, token):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), S.make_handler(service, token))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"
def req(url, body=None, token=None, raw=None):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    r = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", **({"X-Search-Token": token} if token else {})})
    try:
        with urllib.request.urlopen(r, timeout=20) as f:
            return f.status, json.loads(f.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())
srv, base = start(svc(), "sekrit")
st, h = req(base + "/health")
check("/health answers without the secret and carries index, memory and today's spend, but no question", st == 200 and h["ok"] and h["index"]["index_commit"] == "abc123" and "today" in h and "memory_mb" in h)
check("/search without the token is 401", req(base + "/search", {"question": Q})[0] == 401 and req(base + "/search", {"question": Q}, token="wrong")[0] == 401)
st, r = req(base + "/search", {"question": Q, "k": 5}, token="sekrit")
check("/search with the token returns the results", st == 200 and len(r["results"]) == 5 and r["tier"] == S.TIER)
check("bad JSON is 400, an empty question is 400, an unknown path is 404", req(base + "/search", raw=b"{nope", token="sekrit")[0] == 400 and req(base + "/search", {"question": ""}, token="sekrit")[0] == 400 and req(base + "/other", {"q": 1}, token="sekrit")[0] == 404)
check("the health numbers moved: one search counted", req(base + "/health")[1]["today"]["searches"] == 1)
srv.shutdown()
bad = svc(FakeClient(fail="embed"))
srv, base = start(bad, None)
st, r = req(base + "/search", {"question": Q})
check("a failing Voyage call is 502 with a plain reason (the caller answers without the tier), and does not leak the error text", st == 502 and "voyage down" not in json.dumps(r) and "answer without it" in r["reason"])
srv.shutdown()
srv, base = start(svc(enabled=False), None)
check("the kill switch shows in /health and /search is 503", req(base + "/health")[1]["enabled"] is False and req(base + "/search", {"question": Q})[0] == 503)
srv.shutdown()

# ---- the command line refuses to start open ----
env = dict(os.environ); env.pop("SCI_SEARCH_TOKEN", None)
import subprocess
p = subprocess.run([sys.executable, os.path.join(HERE, "sci_search_service.py"), "serve", "--host", "0.0.0.0"], capture_output=True, text=True, env={**env, "SCI_INDEX_DIR": "/nonexistent"}, timeout=60)
check("serve without SCI_SEARCH_TOKEN does not start", p.returncode != 0)
print("\nALL PASSED" if not FAILS else f"\n{len(FAILS)} FAILED: {FAILS}")
sys.exit(1 if FAILS else 0)
