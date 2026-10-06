"""Tests for goodlaw/ik.py, the guarded Indian Kanoon client. No real call is ever made: a local server on 127.0.0.1 plays IK, with a fake key. Run: python test_goodlaw_ik.py"""
import contextlib
import http.server
import json
import os
import shutil
import socket
import tempfile
import threading

from goodlaw import ik as IK

FAILED = []
FAKE_KEY = "fakekey0123456789abcdef"
REAL_META = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "goodlaw", "data", "ik_sample_docmeta_151036912.json")))


def check(ok, msg):
    print(("[PASS] " if ok else "[FAIL] ") + msg)
    if not ok:
        FAILED.append(msg)


class Fake(http.server.ThreadingHTTPServer):
    """script: a list of (status, body, extra_headers) used in order; the last one repeats. requests: what arrived."""
    daemon_threads = True

    def __init__(self, script):
        self.script, self.requests = list(script), []
        super().__init__(("127.0.0.1", 0), _Handler)

    @property
    def url(self):
        return f"http://127.0.0.1:{self.server_address[1]}"


class _Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        srv = self.server
        srv.requests.append({"method": "POST", "path": self.path, "auth": self.headers.get("Authorization")})
        n = len(srv.requests) - 1
        status, body, hdrs = srv.script[min(n, len(srv.script) - 1)]
        if status == "drop":                                           # close without answering
            self.request.shutdown(socket.SHUT_RDWR)
            return
        data = body if isinstance(body, bytes) else (body if isinstance(body, str) else json.dumps(body)).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        for k, v in hdrs.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    do_GET = do_POST


@contextlib.contextmanager
def world(script, **kw):
    srv = Fake(script)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    tmp = tempfile.mkdtemp(prefix="ik-test-")
    logs = []
    try:
        c = IK.Client(env=kw.pop("env", {IK.KEY_ENV: FAKE_KEY}), cache_dir=os.path.join(tmp, "cache"), ledger_path=os.path.join(tmp, "ledger.jsonl"), base_url=srv.url,
                      allow_test_base=True, min_gap=0, stop_file=os.path.join(tmp, "IK_STOP"), log=logs.append, **kw)
        yield c, srv, tmp, logs
    finally:
        srv.shutdown()
        srv.server_close()
        shutil.rmtree(tmp, ignore_errors=True)


def raises(exc, fn, *a, **k):
    """The exception if fn raises exc; None if it raises nothing or something else (which is printed, and fails the check that uses the result)."""
    try:
        fn(*a, **k)
    except exc as e:
        return e
    except Exception as e:
        print(f"   (raised {type(e).__name__} instead: {e})")
    return None


def all_text(tmp):
    out = []
    for root, _, files in os.walk(tmp):
        for f in files:
            out.append(open(os.path.join(root, f), encoding="utf-8", errors="replace").read())
    return "\n".join(out)


OK_DOC = {"tid": 1, "doc": "<p>text</p>", "title": "A v B"}

# ---- calls are validated before anything can reach the network or a file name
check(raises(ValueError, IK.Call, "meta", tid="12; rm -rf /") is not None, "a tid that is not digits is refused")
check(raises(ValueError, IK.Call, "meta", tid="../../etc") is not None, "a path-like tid is refused (it would become a file name)")
check(raises(ValueError, IK.Call, "meta") is not None, "meta without a tid is refused")
check(raises(ValueError, IK.Call, "meta", tid="1", query="x") is not None, "meta takes no query")
check(raises(ValueError, IK.Call, "fragment", tid="1") is not None, "fragment needs a query")
check(raises(ValueError, IK.Call, "search", query="a\nb") is not None, "a multi-line query is refused")
check(raises(ValueError, IK.Call, "bogus", tid="1") is not None, "an unknown kind is refused")
check(raises(ValueError, IK.Call, "meta", tid="1", extra=(("maxcitedby", 5),)) is not None, "an extra parameter the kind does not list is refused")
check(raises(ValueError, IK.Call, "doc", tid="1", extra=(("maxcitedby", 5000),)) is not None, "an extra parameter out of range is refused")
check(raises(ValueError, IK.Call, "doc", tid="1", page=2) is not None, "only search takes a page")
a, b = IK.Call("doc", tid="5", extra={"maxcites": 1, "maxcitedby": 2}), IK.Call("doc", tid=5, extra=(("maxcitedby", 2), ("maxcites", 1)))
check(a == b and a.key() == b.key() and a.shape() == "doc+maxcitedby+maxcites", "the same call written two ways is one call; its shape names its extra parameters")
check(IK.Call("meta", tid="9").price == 0.02 and IK.Call("doc", tid="9").price == 0.20 and IK.Call("fragment", tid="9", query="x").price == 0.05 and IK.Call("search", query="x").price == 0.50,
      "prices are the ones on IK's page (meta confirmed on the dashboard)")

# ---- the real Phase 0 answer is read by its real field names
pm = IK.parse_meta(REAL_META)
check(pm["tid"] == "151036912" and pm["numcitedby"] == 41 and pm["numcites"] == 8 and pm["date"] == "2016-09-07" and "Daily Orders" in pm["doctype"], "parse_meta reads the real Phase 0 response")
check(raises(IK.IKBadResponse, IK.parse_meta, {"tid": 1, "title": "x"}) is not None, "a metadata answer with the fields missing is an error, not zeros")

# ---- plan: a dry run lists every call and its price, and sends nothing
with world([(200, REAL_META, {})]) as (c, srv, tmp, logs):
    c.record_manual(IK.meta("1"), {"seed": True}, "seed")                         # a confirmed 'meta' shape, as after Phase 0
    n_ledger = len(c.ledger())
    calls = [IK.meta("151036912"), IK.meta("151036912"), IK.meta("124664047")]
    pl = c.plan(calls, run_cap_rs=1.0)
    t = pl.text()
    check(len(pl.items) == 2 and pl.cost == 0.04 and pl.n_calls == 2 and not pl.problems, "duplicate calls are one call; cost is the sum of the uncached prices")
    check("151036912" in t and "124664047" in t and "Rs  0.02" in t and "COST OF THIS PLAN: Rs 0.04" in t and "--approved-rs 0.04" in t, "the dry run names each call, its price, the total and the approval to pass")
    check(srv.requests == [] and len(c.ledger()) == n_ledger, "planning sends nothing and writes nothing")
    check(c.status()["spent_rs"] == 0.02 and c.status()["key"] == "set", "status: only the seed is counted, key set")

# ---- a real round trip: header, method, path, cache, ledger; the second time costs nothing
with world([(200, REAL_META, {})]) as (c, srv, tmp, logs):
    c.record_manual(IK.meta("1"), {"seed": True}, "test seed")                    # confirms the 'meta' shape, as the Phase 0 seed does
    res = c.run([IK.meta("151036912")], run_cap_rs=0.05, approved_rs=0.02)
    r = res[IK.meta("151036912").key()]
    check(len(srv.requests) == 1 and srv.requests[0]["method"] == "POST" and srv.requests[0]["path"] == "/docmeta/151036912/", "one POST to /docmeta/<tid>/")
    check(srv.requests[0]["auth"] == "Token " + FAKE_KEY, "the key is sent as 'Authorization: Token <key>'")
    check(r["response"] == REAL_META and r["price_rs"] == 0.02 and os.path.exists(os.path.join(c.cache_dir, "meta", "151036912.json")), "the answer is returned and cached under its tid")
    rows = c.ledger()
    check(len(rows) == 2 and rows[1]["outcome"] == "ok" and rows[1]["tid"] == "151036912" and rows[1]["price_rs"] == 0.02 and c.spent_total() == 0.04, "the ledger counts the seed and the call")
    res2 = c.run([IK.meta("151036912")], run_cap_rs=0.0, approved_rs=None)
    check(len(srv.requests) == 1 and res2[IK.meta("151036912").key()]["response"] == REAL_META and c.spent_total() == 0.04, "the same call again is served from the cache: no request, no spend, no approval needed")
    blob = all_text(tmp)
    check(FAKE_KEY not in blob, "the key is in no file: not the ledger, not the cache")
    check(FAKE_KEY not in repr(c) and FAKE_KEY not in str(c._key) and FAKE_KEY not in " ".join(logs), "the key is in no repr, no str, no log line")

# ---- approval and caps refuse before any call
with world([(200, REAL_META, {})]) as (c, srv, tmp, logs):
    c.record_manual(IK.meta("1"), {"seed": True}, "seed")
    two = [IK.meta("11"), IK.meta("12")]
    for approved, why in ((None, "no approval"), (0.03, "the wrong amount"), (0.0, "zero")):
        e = raises(IK.IKPlanError, c.run, two, 1.0, approved)
        check(e is not None, f"{why}: the run is refused")
    e = raises(IK.IKPlanError, c.run, two, 0.03, 0.04)
    check(e is not None and "run cap" in str(e), "a plan over the run cap is refused even when approved")
    check(srv.requests == [], "nothing was sent by any refused run")
    old = IK.TOTAL_CAP_RS
    IK.TOTAL_CAP_RS = 0.05
    try:
        e = raises(IK.IKPlanError, c.run, two, 1.0, 0.04)
        check(e is not None and "total cap" in str(e), "a plan that would pass the total cap (counting the ledger) is refused")
    finally:
        IK.TOTAL_CAP_RS = old
    check(srv.requests == [], "and nothing was sent")

# ---- a price change after approval cannot overspend: run() plans again at the current price
with world([(200, REAL_META, {})]) as (c, srv, tmp, logs):
    c.record_manual(IK.meta("1"), {"seed": True}, "seed")
    calls = [IK.meta("21"), IK.meta("22"), IK.meta("23")]
    old_price = IK.KINDS["meta"]["price"]
    IK.KINDS["meta"]["price"] = 0.04                                          # IK raises its price after the owner approved Rs 0.06
    try:
        e = raises(IK.IKPlanError, c.run, calls, 0.06, 0.06)                  # run() re-plans at the current price: Rs 0.12, over both the approval and the cap
        check(e is not None and srv.requests == [], "a changed price changes the plan's cost, so an approval made at the old price no longer matches")
    finally:
        IK.KINDS["meta"]["price"] = old_price

# ---- probe first: an unconfirmed shape runs alone
with world([(200, OK_DOC, {})]) as (c, srv, tmp, logs):
    docs = [IK.Call("doc", tid=str(i)) for i in (31, 32, 33)]
    e = raises(IK.IKPlanError, c.run, docs, 5.0, 0.60)
    check(e is not None and "no successful call in the ledger" in str(e) and srv.requests == [], "three calls of a shape with no success yet are refused; nothing sent")
    one = c.run(docs[:1], 5.0, 0.20)
    check(len(srv.requests) == 1 and "doc" in c.confirmed_shapes(), "one call of it is allowed, and its success confirms the shape")
    c.run(docs[1:], 5.0, 0.40)
    check(len(srv.requests) == 3, "after that the rest may be planned together")
    cb = [IK.Call("doc", tid=str(i), extra={"maxcitedby": 10}) for i in (34, 35)]
    e = raises(IK.IKPlanError, c.run, cb, 5.0, 0.40)
    check(e is not None and "doc+maxcitedby" in str(e), "a doc call with an extra parameter is a different shape and needs its own first call")

# ---- the first error of any kind stops the run, is not retried, and is not cached
def stops(status, body, exc, msg):
    with world([(200, REAL_META, {}), (status, body, {})]) as (c, srv, tmp, logs):
        c.record_manual(IK.meta("1"), {"seed": True}, "seed")
        calls = [IK.meta("41"), IK.meta("42"), IK.meta("43")]
        e = raises(exc, c.run, calls, 1.0, 0.06)
        check(e is not None, msg + ": raises " + exc.__name__)
        check(len(srv.requests) == 2, msg + ": the run stopped at once, no retry (2 requests: the good one and the bad one)")
        rows = c.ledger()
        check(rows[-1]["outcome"] == "error" and rows[-1]["http"] == status and c.spent_total() == 0.04, msg + ": the error is in the ledger and counts nothing")
        check(c.cached(calls[1]) is None and c.cached(calls[0]) is not None, msg + ": the first answer is kept, the bad one is not cached")
        check(FAKE_KEY not in all_text(tmp) and FAKE_KEY not in str(e), msg + ": no key anywhere")
        return c


stops(401, {"detail": "bad token"}, IK.IKAuthError, "401")
stops(403, "forbidden", IK.IKAuthError, "403")
stops(429, "slow down", IK.IKRateLimited, "429")
stops(402, "payment required", IK.IKBalanceError, "402")
stops(400, {"message": "Insufficient balance"}, IK.IKBalanceError, "a 400 that talks of balance")
stops(500, "oops", IK.IKBadResponse, "500")
stops(404, "not found", IK.IKBadResponse, "404")
stops(302, "", IK.IKBadResponse, "a redirect")

# ---- a 200 that is not JSON or that reports an error
with world([(200, "<html>not json</html>", {})]) as (c, srv, tmp, logs):
    c.record_manual(IK.meta("1"), {"seed": True}, "seed")
    e = raises(IK.IKBadResponse, c.run, [IK.meta("51")], 1.0, 0.02)
    check(e is not None and c.ledger()[-1]["outcome"] == "unknown" and c.spent_total() == 0.04 and c.cached(IK.meta("51")) is None,
          "a 200 that is not JSON is an error, counts as spent (it may have been charged) and is not cached")
with world([(200, {"errmsg": "Insufficient balance for this call"}, {})]) as (c, srv, tmp, logs):
    c.record_manual(IK.meta("1"), {"seed": True}, "seed")
    e = raises(IK.IKBadResponse, c.run, [IK.meta("52")], 1.0, 0.02)
    check(e is not None and c.cached(IK.meta("52")) is None and c.ledger()[-1]["outcome"] == "error", "a 200 whose JSON carries an errmsg is an error and is not cached")

# ---- the key is never sent anywhere else: a redirect is not followed
other = Fake([(200, {"stolen": True}, {})])
threading.Thread(target=other.serve_forever, daemon=True).start()
try:
    with world([(302, "", {"Location": other.url + "/steal"})]) as (c, srv, tmp, logs):
        c.record_manual(IK.meta("1"), {"seed": True}, "seed")
        raises(IK.IKBadResponse, c.run, [IK.meta("61")], 1.0, 0.02)
        check(other.requests == [], "a redirect is not followed, so the key never reaches the other host")
finally:
    other.shutdown()
    other.server_close()

# ---- a server that echoes the key in an answer does not get it into the cache; a dropped connection counts as spent
with world([(200, {"echo": "Token " + FAKE_KEY, "tid": 71}, {})]) as (c, srv, tmp, logs):
    c.record_manual(IK.meta("1"), {"seed": True}, "seed")
    c.run([IK.meta("71")], 1.0, 0.02)
    check(FAKE_KEY not in all_text(tmp) and "<IK key>" in c.cached(IK.meta("71"))["response"]["echo"], "a key echoed in an answer is scrubbed before it is saved")
with world([("drop", "", {})]) as (c, srv, tmp, logs):
    c.record_manual(IK.meta("1"), {"seed": True}, "seed")
    e = raises(IK.IKBadResponse, c.run, [IK.meta("81"), IK.meta("82")], 1.0, 0.04)
    check(e is not None and len(srv.requests) == 1, "a dropped connection stops the run")
    check(c.ledger()[-1]["outcome"] == "unknown" and c.spent_total() == 0.04 and FAKE_KEY not in all_text(tmp), "and it is counted as spent, since it may have been processed")

# ---- the key goes only to IK
check(raises(IK.IKError, IK.Client, env={IK.KEY_ENV: FAKE_KEY}, base_url="https://evil.example.com") is not None, "another host is refused")
check(raises(IK.IKError, IK.Client, env={IK.KEY_ENV: FAKE_KEY}, base_url="http://127.0.0.1:9") is not None, "a loopback base is refused unless the test flag is passed")
check(raises(IK.IKError, IK.Client, env={IK.KEY_ENV: FAKE_KEY}, base_url="http://evil.example.com", allow_test_base=True) is not None, "the test flag allows loopback only")
check(IK.Client(env={IK.KEY_ENV: FAKE_KEY}).base_url == "https://api.indiankanoon.org", "the default base is IK's https host")

# ---- the key comes from the environment mapping only, and a bad key is not echoed
with world([(200, REAL_META, {})], env={}) as (c, srv, tmp, logs):
    check(c.status()["key"] == "NOT set" and c.plan([IK.meta("91")], 1.0).cost == 0.02, "no key: a dry run still works")
    e = raises(IK.IKError, c.run, [IK.meta("91")], 1.0, 0.02)
    check(e is not None and srv.requests == [], "no key: a run is refused before any request")
with world([(200, REAL_META, {})], env={IK.KEY_ENV: "has a space\nand newline"}) as (c, srv, tmp, logs):
    e = raises(IK.IKError, c.run, [IK.meta("92")], 1.0, 0.02)
    check(e is not None and "has a space" not in str(e) and srv.requests == [] and "not set" not in c.status()["key"].replace("is set but", ""), "a malformed key is refused without being shown")

# ---- the stop file
with world([(200, REAL_META, {})]) as (c, srv, tmp, logs):
    open(c.stop_file, "w").close()
    e = raises(IK.IKPlanError, c.run, [IK.meta("101")], 1.0, 0.02)
    check(e is not None and "IK_STOP" in str(e) and srv.requests == [], "an IK_STOP file refuses every call")

# ---- throttle: serial calls are spaced by the gap
slept = []
clock = {"t": 0.0}
srv = Fake([(200, REAL_META, {})])
threading.Thread(target=srv.serve_forever, daemon=True).start()
tmp = tempfile.mkdtemp(prefix="ik-test-")
try:
    c = IK.Client(env={IK.KEY_ENV: FAKE_KEY}, cache_dir=tmp + "/c", ledger_path=tmp + "/l.jsonl", base_url=srv.url, allow_test_base=True, min_gap=0.5,
                  clock=lambda: clock["t"], sleep=lambda s: (slept.append(s), clock.__setitem__("t", clock["t"] + s)), stop_file=tmp + "/S", log=lambda m: None)
    c.record_manual(IK.meta("1"), {"seed": True}, "seed")
    c.run([IK.meta("111"), IK.meta("112"), IK.meta("113")], 1.0, 0.06)
    check(len(slept) == 2 and all(abs(s - 0.5) < 1e-9 for s in slept), "three calls: two waits of the full gap")
finally:
    srv.shutdown()
    srv.server_close()
    shutil.rmtree(tmp, ignore_errors=True)

# ---- damaged ledger and cache
with world([(200, REAL_META, {})]) as (c, srv, tmp, logs):
    c.record_manual(IK.meta("1"), {"seed": True}, "seed")
    with open(c.ledger_path, "a") as fh:
        fh.write("this is not json\n")
    e = raises(IK.IKError, c.run, [IK.meta("121")], 1.0, 0.02)
    check(e is not None and "damaged ledger" in str(e) and srv.requests == [], "a damaged ledger stops spending")
with world([(200, REAL_META, {})]) as (c, srv, tmp, logs):
    c.record_manual(IK.meta("1"), {"seed": True}, "seed")
    c.run([IK.meta("131")], 1.0, 0.02)
    with open(os.path.join(c.cache_dir, "meta", "131.json"), "w") as fh:
        fh.write("{ broken")
    pl = c.plan([IK.meta("131")], 1.0)
    check(pl.n_calls == 1 and any("unreadable" in m for m in logs), "a damaged cache file is reported and treated as not cached")

# ---- the Phase 0 seed
with world([(200, REAL_META, {})]) as (c, srv, tmp, logs):
    check("meta" not in c.confirmed_shapes() and c.plan([IK.meta("1"), IK.meta("2")], 1.0).problems, "before any success, two meta calls are not allowed together")
    c.record_manual(IK.meta("151036912"), REAL_META, "phase 0, by hand")
    check(c.spent_total() == 0.02 and c.plan([IK.meta("151036912")], 0.0).cost == 0.0 and "meta" in c.confirmed_shapes(), "a call made by hand is counted, cached and confirms its shape")

# ---- the search call carries its query and page, and each page is its own cache entry
with world([(200, {"found": "1 - 1 of 1", "docs": []}, {})]) as (c, srv, tmp, logs):
    c.record_manual(IK.Call("search", query="seed"), {"docs": []}, "seed")
    c.run([IK.Call("search", query="youth bar association", page=1)], 1.0, 0.50)
    check("formInput=youth+bar+association" in srv.requests[0]["path"] and "pagenum=1" in srv.requests[0]["path"], "search sends formInput and pagenum in the query string")
    f = c._cache_path(IK.Call("search", query="youth bar association", page=1))
    check(c.cached(IK.Call("search", query="youth bar association", page=2)) is None and os.path.exists(f), "another page of the same query is a different cache entry")

print()
print("FAILED:" if FAILED else "all passed", *FAILED, sep="\n" if FAILED else " ")
raise SystemExit(1 if FAILED else 0)
