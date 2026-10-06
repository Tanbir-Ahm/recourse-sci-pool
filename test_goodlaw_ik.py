"""Tests for goodlaw/ik.py, the guarded Indian Kanoon client. No real call is ever made: a local server on 127.0.0.1 (or an injected transport) plays IK, with a fake key.
Run: python test_goodlaw_ik.py"""
import contextlib
import http.server
import json
import math
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading

from goodlaw import ik as IK

HERE = os.path.dirname(os.path.abspath(__file__))
FAILED = []
FAKE_KEY = "fakekey0123456789abcdef"
REAL_META = json.load(open(os.path.join(HERE, "goodlaw", "data", "ik_sample_docmeta_151036912.json")))
OK_DOC = {"tid": 1, "doc": "<p>text</p>", "title": "A v B"}


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
        status, body, hdrs = srv.script[min(len(srv.requests) - 1, len(srv.script) - 1)]
        if status == "drop":                                           # close without answering
            self.request.shutdown(socket.SHUT_RDWR)
            return
        data = body if isinstance(body, bytes) else (body if isinstance(body, str) else json.dumps(body)).encode()
        h = {"Content-Type": "application/json"}
        h.update(hdrs)
        self.send_response(status)
        for k, v in h.items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    do_GET = do_POST


def mk(tmp, base_url=None, transport=None, env=None, **kw):
    logs = kw.pop("logs", [])
    return IK.Client(env={IK.KEY_ENV: FAKE_KEY} if env is None else env, cache_dir=os.path.join(tmp, "cache"), ledger_path=os.path.join(tmp, "ledger.jsonl"),
                     base_url=base_url or IK.BASE_URL, allow_test_base=bool(base_url), transport=transport, min_gap=0, stop_file=os.path.join(tmp, "IK_STOP"),
                     log=logs.append, sample_dir=kw.pop("sample_dir", None), **kw)


@contextlib.contextmanager
def world(script, **kw):
    srv = Fake(script)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    tmp = tempfile.mkdtemp(prefix="ik-test-")
    logs = []
    try:
        yield mk(tmp, base_url=srv.url, logs=logs, **kw), srv, tmp, logs
    finally:
        srv.shutdown()
        srv.server_close()
        shutil.rmtree(tmp, ignore_errors=True)


@contextlib.contextmanager
def scripted(answers, **kw):
    """A client with an injected transport. answers: a list of (status, body) or exceptions, used in order, the last repeating. hook(n) runs before each call is answered."""
    tmp = tempfile.mkdtemp(prefix="ik-test-")
    state = {"n": 0, "urls": []}
    hook = kw.pop("hook", None)

    def transport(method, url, headers, params, timeout):
        state["n"] += 1
        state["urls"].append(url)
        if hook:
            hook(state["n"], tmp)
        a = answers[min(state["n"] - 1, len(answers) - 1)]
        if isinstance(a, BaseException):
            raise a
        return a[0], (a[1] if isinstance(a[1], str) else json.dumps(a[1]))

    logs = []
    try:
        yield mk(tmp, transport=transport, logs=logs, **kw), state, tmp, logs
    finally:
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


def seed(c):
    """What Phase 0 left in the real ledger: one answered 'meta' call whose price the owner confirmed on the dashboard."""
    c.record_manual(IK.meta("1"), REAL_META, "seed", confirm_price=True)


def go(c, calls, cap=5.0, **kw):
    """The two-step path: read the plan, then run it with its cost and its id."""
    pl = c.plan(calls, cap, kw.get("retry_failed", False), kw.get("refetch", False))
    return c.run(calls, cap, pl.cost, pl.plan_id, **kw)


# ---- the numbers the plan rests on are pinned, so raising them is a visible edit
check(IK.TOTAL_CAP_RS == 150.0 and IK.MIN_GAP_SECONDS == 0.5, "the total cap (Rs 150) and the call gap (0.5 s) are the plan's")
check(IK.Call("meta", tid="9").price == 0.02 and IK.Call("doc", tid="9").price == 0.20 and IK.Call("fragment", tid="9", query="x").price == 0.05 and IK.Call("search", query="x").price == 0.50,
      "prices are the ones on IK's page (meta confirmed on the dashboard)")

# ---- calls are validated before anything can reach the network or a file name
for kw_, why in (({"tid": "12; rm -rf /"}, "a tid that is not digits"), ({"tid": "../../etc"}, "a path-like tid (it would become a file name)"),
                 ({"tid": "0123"}, "a tid with a leading zero (a second spelling of the same document)"), ({"tid": "١٢٣"}, "Arabic-Indic digits"),
                 ({"tid": "１２３"}, "full-width digits"), ({"tid": ""}, "an empty tid"), ({"tid": "1" * 13}, "a tid of 13 digits")):
    check(raises(ValueError, IK.Call, "meta", **kw_) is not None, why + " is refused")
check(raises(ValueError, IK.Call, "meta", tid="1", query="x") is not None, "meta takes no query")
check(raises(ValueError, IK.Call, "fragment", tid="1") is not None, "fragment needs a query")
check(raises(ValueError, IK.Call, "search", query="  ") is not None, "a blank query is refused")
check(raises(ValueError, IK.Call, "bogus", tid="1") is not None, "an unknown kind is refused")
check(raises(ValueError, IK.Call, "meta", tid="1", extra=(("maxcitedby", 5),)) is not None, "an extra parameter the kind does not list is refused")
check(raises(ValueError, IK.Call, "doc", tid="1", extra=(("maxcitedby", 5000),)) is not None, "an extra parameter out of range is refused")
check(raises(ValueError, IK.Call, "doc", tid="1", extra=(("maxcitedby", 1), ("maxcitedby", 2))) is not None, "a parameter given twice is refused")
check(raises(ValueError, IK.Call, "doc", tid="1", page=2) is not None, "only search takes a page")
a, b = IK.Call("doc", tid="5", extra={"maxcites": 1, "maxcitedby": 2}), IK.Call("doc", tid=5, extra=(("maxcitedby", 2), ("maxcites", 1)))
check(a == b and a.key() == b.key() and a.shape() == "doc+maxcitedby=2+maxcites=1", "the same call written two ways is one call; its shape names its extra parameters and their values")
check(IK.Call("search", query="youth   bar\tassociation").key() == IK.Call("search", query="youth bar association").key(), "a query is one spelling: spaces are normalised")
check(IK.Call("doc", tid="5", extra={"maxcitedby": 10}).shape() != IK.Call("doc", tid="5", extra={"maxcitedby": 50}).shape(), "another value of an extra parameter is another shape")

# ---- the real Phase 0 answer is read by its real field names; odd answers are IKBadResponse, never another error
pm = IK.parse_meta(REAL_META)
check(pm["tid"] == "151036912" and pm["numcitedby"] == 41 and pm["numcites"] == 8 and pm["date"] == "2016-09-07" and "Daily Orders" in pm["doctype"], "parse_meta reads the real Phase 0 response")
check(raises(IK.IKBadResponse, IK.parse_meta, {"tid": 1, "title": "x"}) is not None, "a metadata answer with the fields missing is an error, not zeros")
for bad in ("many", None, True, 1.5, [], 10 ** 30, "١٢"):
    check(raises(IK.IKBadResponse, IK.parse_meta, dict(REAL_META, numcitedby=bad)) is not None, f"numcitedby={bad!r:.12} is an IKBadResponse")
check(raises(IK.IKBadResponse, IK.parse_meta, dict(REAL_META, title=5)) is not None, "a title that is not text is an IKBadResponse")
check(IK.parse_meta(dict(REAL_META, numcitedby="41"))["numcitedby"] == 41, "a count written as digits is accepted")

# ---- plan: a dry run lists every call and its price and a plan id, and sends nothing
with world([(200, REAL_META, {})]) as (c, srv, tmp, logs):
    seed(c)
    n_ledger = len(c.ledger())
    calls = [IK.meta("151036912"), IK.meta("151036912"), IK.meta("124664047")]
    pl = c.plan(calls, 1.0)
    t = pl.text()
    check(len(pl.items) == 2 and pl.cost == 0.04 and pl.n_calls == 2 and not pl.problems, "duplicate calls are one call; cost is the sum of the uncached prices")
    check("151036912" in t and "124664047" in t and "Rs  0.02" in t and "COST OF THIS PLAN: Rs 0.04" in t and f"--plan-id {pl.plan_id}" in t and "--approved-rs 0.04" in t,
          "the dry run names each call, its price, the total, the plan id and the approval to pass")
    check(srv.requests == [] and len(c.ledger()) == n_ledger, "planning sends nothing and writes nothing")
    check(c.plan([IK.meta("2"), IK.meta("1")], 1.0).plan_id != c.plan([IK.meta("3"), IK.meta("1")], 1.0).plan_id and pl.plan_id == c.plan(calls[::-1], 1.0).plan_id,
          "the plan id follows the list of calls, not their order")
    st = c.status()
    check(st["spent_rs"] == 0.02 and st["key"] == "set" and st["confirmed_shapes"] == ["meta"], "status: only the seed is counted, key set, meta confirmed")
    dr = c.plan([IK.Call("doc", tid="9")], 1.0)
    check("price NOT confirmed" in dr.text(), "a call whose price the owner has not confirmed is marked in the dry run")

# ---- a real round trip: header, method, path, cache, ledger (attempt before result); the second time costs nothing
with world([(200, REAL_META, {})]) as (c, srv, tmp, logs):
    seed(c)
    res = go(c, [IK.meta("151036912")], 0.05)
    r = res[IK.meta("151036912").key()]
    check(len(srv.requests) == 1 and srv.requests[0]["method"] == "POST" and srv.requests[0]["path"] == "/docmeta/151036912/", "one POST to /docmeta/<tid>/")
    check(srv.requests[0]["auth"] == "Token " + FAKE_KEY, "the key is sent as 'Authorization: Token <key>'")
    check(r["response"] == REAL_META and r["price_rs"] == 0.02 and os.path.exists(os.path.join(c.cache_dir, "meta", "151036912.json")), "the answer is returned and cached under its tid")
    rows = c.ledger()
    check([x["type"] for x in rows[-2:]] == ["attempt", "result"] and rows[-2]["id"] == rows[-1]["id"] and rows[-1]["outcome"] == "ok" and rows[-2]["tid"] == "151036912",
          "the ledger has the attempt, then its result, for the same id")
    check(c.spent_total() == 0.04, "the ledger counts the seed and the call")
    res2 = go(c, [IK.meta("151036912")], 0.0)
    check(len(srv.requests) == 1 and res2[IK.meta("151036912").key()]["response"] == REAL_META and c.spent_total() == 0.04,
          "the same call again is served from the cache: no request, no spend, no approval needed")
    check(not os.path.exists(c.ledger_path + ".lock"), "the lock file is gone after a run")
    blob = all_text(tmp)
    check(FAKE_KEY not in blob, "the key is in no file: not the ledger, not the cache")
    check(FAKE_KEY not in repr(c) and FAKE_KEY not in str(c._key) and FAKE_KEY not in " ".join(logs), "the key is in no repr, no str, no log line")

# ---- approval: the amount AND the plan id, refused before any call
with world([(200, REAL_META, {})]) as (c, srv, tmp, logs):
    seed(c)
    two = [IK.meta("11"), IK.meta("12")]
    pl = c.plan(two, 1.0)
    for approved, pid, why in ((None, pl.plan_id, "no amount"), (0.03, pl.plan_id, "an amount below the cost"), (0.05, pl.plan_id, "an amount above the cost"), (0.0, pl.plan_id, "zero"),
                               (float("nan"), pl.plan_id, "nan"), (float("inf"), pl.plan_id, "inf"), (True, pl.plan_id, "a bool"), (0.04, None, "no plan id"), (0.04, "deadbeef", "a wrong plan id")):
        check(raises(IK.IKPlanError, c.run, two, 1.0, approved, pid) is not None, f"{why}: the run is refused")
    other = [IK.meta("13"), IK.meta("14")]
    check(c.plan(other, 1.0).cost == pl.cost and raises(IK.IKPlanError, c.run, other, 1.0, 0.04, pl.plan_id) is not None,
          "an approval read from one plan cannot be used for another list of the same cost")
    check(srv.requests == [], "nothing was sent by any refused run")
    check(c.run(two, 1.0, 0.04, pl.plan_id) and len(srv.requests) == 2, "the right amount with the right plan id runs")

# ---- caps: finite numbers only, fail closed, and the ledger is the memory for the total
with world([(200, REAL_META, {})]) as (c, srv, tmp, logs):
    seed(c)
    two = [IK.meta("11"), IK.meta("12")]
    e = raises(IK.IKPlanError, c.run, two, 0.03, 0.04, c.plan(two, 0.03).plan_id)
    check(e is not None and "run cap" in str(e), "a plan over the run cap is refused even when approved")
    for cap in (float("nan"), float("inf"), -1.0, True, "5", None):
        check(raises(IK.IKPlanError, c.plan, two, cap) is not None and raises(IK.IKPlanError, c.run, two, cap, 0.04, "x") is not None, f"a run cap of {cap!r} is refused")
    old = IK.TOTAL_CAP_RS
    IK.TOTAL_CAP_RS = 0.05
    try:
        e = raises(IK.IKPlanError, c.run, two, 1.0, 0.04, c.plan(two, 1.0).plan_id)
        check(e is not None and "total cap" in str(e), "a plan that would pass the total cap (counting the ledger) is refused")
    finally:
        IK.TOTAL_CAP_RS = old
    check(srv.requests == [], "and nothing was sent")
    old_price = IK.KINDS["meta"]["price"]
    pl = c.plan(two, 1.0)
    IK.KINDS["meta"]["price"] = 0.04                                          # IK raises its price after the owner approved Rs 0.04
    try:
        check(raises(IK.IKPlanError, c.run, two, 1.0, 0.04, pl.plan_id) is not None and srv.requests == [],
              "a changed price changes the plan's cost, id and the confirmed prices, so the earlier approval no longer works")
        check("meta" not in c.confirmed_shapes(), "a price that changed in the table lapses the owner's confirmation")
    finally:
        IK.KINDS["meta"]["price"] = old_price

# ---- the cap and the stop file are checked again before every call, with state that changes during the run
def drop_stop_file(n, tmp):
    if n == 1:
        open(os.path.join(tmp, "IK_STOP"), "w").close()


with scripted([(200, REAL_META)], hook=drop_stop_file) as (c, st, tmp, logs):
    seed(c)
    e = raises(IK.IKPlanError, go, c, [IK.meta("21"), IK.meta("22"), IK.meta("23")])
    check(e is not None and st["n"] == 1 and "IK_STOP" in str(e), "an IK_STOP file that appears mid-run stops it before the next call")


def spend_elsewhere(n, tmp):
    if n == 1:                                                                 # another process spends Rs 149.95 while this run is going
        with open(os.path.join(tmp, "ledger.jsonl"), "a") as fh:
            fh.write(json.dumps({"type": "attempt", "id": "other", "ts": "x", "kind": "meta", "shape": "meta", "key": "k", "price_rs": 9.0, "outcome": "pending"}) + "\n")
        for i in range(16):
            with open(os.path.join(tmp, "ledger.jsonl"), "a") as fh:
                fh.write(json.dumps({"type": "attempt", "id": f"o{i}", "ts": "x", "kind": "meta", "shape": "meta", "key": f"k{i}", "price_rs": 9.0, "outcome": "pending"}) + "\n")


with scripted([(200, REAL_META)], hook=spend_elsewhere) as (c, st, tmp, logs):
    seed(c)
    e = raises(IK.IKPlanError, go, c, [IK.meta("21"), IK.meta("22"), IK.meta("23")])
    check(e is not None and st["n"] == 1 and "cap would be passed" in str(e), "spending that appears in the ledger mid-run stops the run at the total cap")

# ---- probe first: a shape runs alone until the owner has read the dashboard and confirmed its price
with world([(200, OK_DOC, {})]) as (c, srv, tmp, logs):
    docs = [IK.Call("doc", tid=str(i)) for i in (31, 32, 33)]
    e = raises(IK.IKPlanError, go, c, docs)
    check(e is not None and "no confirmed price" in str(e) and srv.requests == [], "three calls of an unconfirmed shape are refused; nothing sent")
    go(c, docs[:1])
    check(len(srv.requests) == 1 and "doc" not in c.confirmed_shapes() and "doc" in c.status()["answered_but_price_not_confirmed"],
          "one call is allowed; its answer alone does NOT confirm the shape (only the owner's price record does)")
    e = raises(IK.IKPlanError, go, c, docs[1:2])
    check(e is not None and "no confirmed price" in str(e) and len(srv.requests) == 1, "a second one-call run is refused too: many single probes cannot get round the rule")
    check(raises(IK.IKError, c.confirm_price, "doc", 0.50, "dashboard") is not None, "a dashboard price different from the table's is refused (the table is corrected first)")
    check(raises(IK.IKError, c.confirm_price, "fragment", 0.05, "dashboard") is not None, "a price cannot be confirmed for a shape that was never answered")
    c.confirm_price("doc", 0.20, "balance 100.00 to 99.80")
    go(c, docs[1:])
    check(len(srv.requests) == 3 and "doc" in c.confirmed_shapes(), "once the price is confirmed the rest may be planned together")
    cb = [IK.Call("doc", tid=str(i), extra={"maxcitedby": 10}) for i in (34, 35)]
    e = raises(IK.IKPlanError, go, c, cb)
    check(e is not None and "doc+maxcitedby=10" in str(e), "a doc call with an extra parameter is a different shape and needs its own probe and confirmation")
    cb2 = [IK.Call("doc", tid="36", extra={"maxcitedby": 10}), IK.Call("doc", tid="37", extra={"maxcitedby": 50})]
    check(c.plan(cb2[:1], 5.0).problems == [] and c.plan(cb2, 5.0).problems == [], "a single probe of an extra shape is allowed, one per shape")

# ---- every kind of error stops the run at once, is not retried, is not cached, and costs what the rules say
def stops(status, body, exc, msg, charged):
    with world([(200, REAL_META, {}), (status, body, {})]) as (c, srv, tmp, logs):
        seed(c)
        calls = [IK.meta("41"), IK.meta("42"), IK.meta("43")]
        e = raises(exc, go, c, calls)
        check(e is not None, msg + ": raises " + exc.__name__)
        check(len(srv.requests) == 2, msg + ": the run stopped at once, no retry (2 requests: the good one and the bad one)")
        last = c.attempts()[-1]
        want = 0.06 if charged else 0.04
        check(last["outcome"] == "error" and last["http"] == status and c.spent_total() == want, msg + f": recorded as an error and {'counted' if charged else 'not counted'} (Rs {want:.2f} in total)")
        check(c.cached(calls[1]) is None and c.cached(calls[0]) is not None, msg + ": the first answer is kept, the bad one is not cached")
        check(FAKE_KEY not in all_text(tmp) and FAKE_KEY not in str(e), msg + ": no key anywhere")
        return c, calls


stops(401, {"detail": "bad token"}, IK.IKAuthError, "401", False)
stops(403, "forbidden", IK.IKAuthError, "403", False)
stops(429, "slow down", IK.IKRateLimited, "429", False)
stops(402, "payment required", IK.IKBalanceError, "402", False)
stops(400, {"message": "Insufficient balance"}, IK.IKBalanceError, "a 400 that talks of balance", True)
stops(500, "oops", IK.IKBadResponse, "500", True)
c500, calls500 = stops(404, "not found", IK.IKBadResponse, "404", True)
stops(302, "", IK.IKBadResponse, "a redirect", True)

# ---- a call that failed is not simply retried by another run (it may have been charged each time)
with world([(200, REAL_META, {}), (500, "oops", {})]) as (c, srv, tmp, logs):
    seed(c)
    go(c, [IK.meta("51")])
    raises(IK.IKBadResponse, go, c, [IK.meta("52")])
    n = len(srv.requests)
    e = raises(IK.IKPlanError, go, c, [IK.meta("52")])
    check(e is not None and "failed before" in str(e) and len(srv.requests) == n, "the same call again after an error is refused")
    check(c.plan([IK.meta("53")], 1.0).problems == [], "a different call of a confirmed shape is not blocked")
    srv.script = [(200, REAL_META, {})]
    go(c, [IK.meta("52")], retry_failed=True)
    check(len(srv.requests) == n + 1 and go(c, [IK.meta("52")]) is not None, "retry_failed allows it, and once answered it is cached like any other")
with world([(500, "oops", {}), (200, OK_DOC, {})]) as (c, srv, tmp, logs):
    raises(IK.IKBadResponse, go, c, [IK.Call("doc", tid="61")])
    e = raises(IK.IKPlanError, go, c, [IK.Call("doc", tid="62")])
    check(e is not None and "failed before" in str(e), "after a failed probe, another call of the same shape is refused too")
    go(c, [IK.Call("doc", tid="62")], retry_failed=True)
    check(len(srv.requests) == 2, "retry_failed lets the probe be made again")

# ---- a 200 answer that is not a success: stopped, kept for reading, counted as spent, never confirms anything
for body, why in (({"error": "something went wrong"}, "an 'error' field"), ({"message": "nope"}, "a 'message' field"), ({"detail": "nope"}, "a 'detail' field"), ({"errmsg": ""}, "an empty 'errmsg'"),
                  ({"errors": []}, "an 'errors' field"), ({}, "an empty object"), ([], "a list"), (None, "null"), ('"text"', "a JSON string"), (json.dumps(REAL_META["title"]), "a bare title")):
    with scripted([(200, body)]) as (c, st, tmp, logs):
        e = raises(IK.IKBadResponse, go, c, [IK.Call("doc", tid="71")])
        a = c.attempts()
        check(e is not None and a[-1]["outcome"] == "error" and c.spent_total() == 0.20 and c.cached(IK.Call("doc", tid="71")) is None and not c.status()["answered_but_price_not_confirmed"],
              f"200 with {why}: stopped, counted, not cached, does not count as an answered probe")
        check(len(os.listdir(os.path.join(c.cache_dir, "_rejected"))) == 1, f"200 with {why}: the answer is kept in _rejected/ so the real error shape can be read")
with scripted([(200, {})]) as (c, st, tmp, logs):
    seed(c)
    e = raises(IK.IKBadResponse, go, c, [IK.meta(str(i)) for i in range(81, 91)])
    check(e is not None and st["n"] == 1, "ten meta calls answered with {}: the run stops after the first")
with scripted([(200, {"found": "0", "docs": "none"})]) as (c, st, tmp, logs):
    check(raises(IK.IKBadResponse, go, c, [IK.Call("search", query="x")]) is not None, "a search answer without a 'docs' list is not a success")
with scripted([(200, {"error": "Insufficient balance, please recharge"})]) as (c, st, tmp, logs):
    check(raises(IK.IKBalanceError, go, c, [IK.Call("doc", tid="72")]) is not None, "a 200 answer that talks of balance is a balance error")
with scripted([(200, "<html>not json</html>")]) as (c, st, tmp, logs):
    seed(c)
    e = raises(IK.IKBadResponse, go, c, [IK.meta("73")])
    check(e is not None and c.attempts()[-1]["outcome"] == "unknown" and c.spent_total() == 0.04 and c.cached(IK.meta("73")) is None,
          "a 200 that is not JSON stops, counts as spent (it may have been charged) and is not cached")

# ---- failures around the call itself
with scripted([IK.NotSent("ConnectTimeout")]) as (c, st, tmp, logs):
    seed(c)
    e = raises(IK.IKBadResponse, go, c, [IK.meta("91")])
    check(e is not None and c.attempts()[-1]["outcome"] == "notsent" and c.spent_total() == 0.02, "a call that never left is recorded and costs nothing")
with scripted([ConnectionResetError("boom")]) as (c, st, tmp, logs):
    seed(c)
    e = raises(IK.IKBadResponse, go, c, [IK.meta("92")])
    check(e is not None and c.attempts()[-1]["outcome"] == "unknown" and c.spent_total() == 0.04, "a dropped connection is counted as spent, since it may have been processed")
with scripted([KeyboardInterrupt()]) as (c, st, tmp, logs):
    seed(c)
    e = raises(KeyboardInterrupt, go, c, [IK.meta("93")])
    check(e is not None and c.attempts()[-1]["outcome"] == "pending" and c.spent_total() == 0.04 and not os.path.exists(c.ledger_path + ".lock"),
          "an interrupt during a call leaves the attempt on record (counted as spent) and releases the lock")
with scripted([(200, REAL_META)]) as (c, st, tmp, logs):
    seed(c)

    def boom(*a, **k):
        raise OSError("disk full")
    c._write_cache = boom
    e = raises(IK.IKError, go, c, [IK.meta("94")])
    check(e is not None and c.attempts()[-1]["outcome"] == "pending" and c.spent_total() == 0.04, "an answer that cannot be saved is an error and stays counted as spent")
with scripted([(200, REAL_META)]) as (c, st, tmp, logs):
    seed(c)
    open(os.path.join(tmp, "notadir"), "w").close()
    c.ledger_path = os.path.join(tmp, "notadir", "ledger.jsonl")
    check(raises(IK.IKError, go, c, [IK.meta("95")]) is not None and st["n"] == 0, "a ledger that cannot be written stops the run before anything is sent")
with scripted([(200, REAL_META)]) as (c, st, tmp, logs):
    seed(c)
    shutil.rmtree(c.cache_dir)
    open(c.cache_dir, "w").close()
    check(raises(IK.IKPlanError, go, c, [IK.meta("96")]) is not None and st["n"] == 0, "a cache folder that cannot be written stops the run before anything is sent")

# ---- the key never reaches a file or a message, however the server treats it
with world([(200, {"echo": "Token " + FAKE_KEY, "tid": 71, "publishdate": "2016-09-07", "doctype": "d", "title": "t", "numcites": 1, "numcitedby": 2}, {})]) as (c, srv, tmp, logs):
    seed(c)
    go(c, [IK.meta("71")])
    check(FAKE_KEY not in all_text(tmp) and "<IK key>" in c.cached(IK.meta("71"))["response"]["echo"], "a key echoed in an answer is scrubbed before it is saved")
with world([(500, "A" * 190 + FAKE_KEY + " tail", {})]) as (c, srv, tmp, logs):
    seed(c)
    e = raises(IK.IKBadResponse, go, c, [IK.meta("72")])
    check(e is not None and FAKE_KEY[:6] not in str(e) and FAKE_KEY not in all_text(tmp), "the key is scrubbed before an error text is shortened, so no prefix of it survives the cut")
other = Fake([(200, {"stolen": True}, {})])
threading.Thread(target=other.serve_forever, daemon=True).start()
try:
    with world([(302, "", {"Location": other.url + "/steal"})]) as (c, srv, tmp, logs):
        seed(c)
        raises(IK.IKBadResponse, go, c, [IK.meta("61")])
        check(other.requests == [], "a redirect is not followed, so the key never reaches the other host")
finally:
    other.shutdown()
    other.server_close()
for url, why in (("https://evil.example.com", "another host"), ("http://127.0.0.1:9", "a loopback base without the test flag"), ("https://api.indiankanoon.org.evil.com", "a look-alike host"),
                 ("https://api.indiankanoon.org@evil.com", "user-info in front of another host")):
    check(raises(IK.IKError, IK.Client, env={IK.KEY_ENV: FAKE_KEY}, base_url=url) is not None, why + " is refused")
for url, why in (("http://evil.example.com", "a non-loopback host"), ("http://127.0.0.1:80@evil.example.com", "user-info in front of another host"), ("http://localhost:80@evil.host/", "the same with localhost"),
                 ("https://127.0.0.1:5000", "https on loopback")):
    check(raises(IK.IKError, IK.Client, env={IK.KEY_ENV: FAKE_KEY}, base_url=url, allow_test_base=True) is not None, f"even with the test flag, {why} is refused")
check(IK.Client(env={IK.KEY_ENV: FAKE_KEY}).base_url == "https://api.indiankanoon.org", "the default base is IK's https host")

# ---- the key comes from the environment mapping only; a malformed key is refused without being shown and never reaches a transport
with scripted([(200, REAL_META)], env={}) as (c, st, tmp, logs):
    seed(c)
    check(c.status()["key"] == "NOT set" and c.plan([IK.meta("91")], 1.0).cost == 0.02, "no key: a dry run still works")
    check(raises(IK.IKError, go, c, [IK.meta("91")]) is not None and st["n"] == 0, "no key: a run is refused before any request")
for badkey in ("has a space\nand newline", 'quote"inside12345', "back\\slash12345", "short"):
    with scripted([(200, REAL_META)], env={IK.KEY_ENV: badkey}) as (c, st, tmp, logs):
        seed(c)
        e = raises(IK.IKError, go, c, [IK.meta("92")])
        s = c.status()["key"]
        check(e is not None and badkey not in str(e) and badkey not in s and st["n"] == 0 and s != "NOT set" and "is set but" in s, f"a malformed key ({badkey[:8]!r}) is refused, not shown, and never sent")

# ---- the kill switch: next to the code and in the working folder, whatever the current folder is
cl = IK.Client(env={})
check(os.path.join(IK.REPO_ROOT, "IK_STOP") in cl._stop_files and os.path.join(os.getcwd(), "IK_STOP") in cl._stop_files and all(os.path.isabs(f) for f in cl._stop_files),
      "by default the kill switch is IK_STOP in the repository folder and in the working folder")
with scripted([(200, REAL_META)]) as (c, st, tmp, logs):
    seed(c)
    open(os.path.join(tmp, "IK_STOP"), "w").close()
    e = raises(IK.IKPlanError, go, c, [IK.meta("101")])
    check(e is not None and "IK_STOP" in str(e) and st["n"] == 0 and c.status()["stop_file"], "an IK_STOP file refuses every call")
    pl = c.plan([IK.meta("101")], 1.0)
    check(any("IK_STOP" in p_ for p_ in pl.problems) and "REFUSED" in pl.text() and "--plan-id" not in pl.text(), "and the dry run says so, instead of offering an approval to give")

# ---- the lock: one run at a time
with scripted([(200, REAL_META)]) as (c, st, tmp, logs):
    seed(c)
    open(c.ledger_path + ".lock", "w").write("123 2026-01-01T00:00:00Z\n")
    e = raises(IK.IKPlanError, go, c, [IK.meta("102")])
    check(e is not None and "another run" in str(e) and st["n"] == 0, "a lock file left by another run (or a crash) refuses the run")

# ---- the cache is checked again before every call, and a call paid for earlier is not silently paid for again
def cache_second(n, tmp):
    if n == 1:                                                                  # another process saves the answer to call 2 meanwhile
        c_ = holder["c"]
        c_._write_cache(IK.meta("112"), REAL_META, 200, 0.02)


holder = {}
with scripted([(200, REAL_META)], hook=cache_second) as (c, st, tmp, logs):
    holder["c"] = c
    seed(c)
    go(c, [IK.meta("111"), IK.meta("112"), IK.meta("113")])
    check(st["n"] == 2, "an answer that appeared in the cache after the plan was made is not paid for again")
with scripted([(200, REAL_META)]) as (c, st, tmp, logs):
    seed(c)
    go(c, [IK.meta("121")])
    shutil.rmtree(c.cache_dir)                                                  # a new session: the ledger is committed, the cache is not
    pl = c.plan([IK.meta("121")], 1.0)
    check(pl.problems and "paid for before" in pl.problems[0] and "paid before" in pl.text() and raises(IK.IKPlanError, go, c, [IK.meta("121")]) is not None and st["n"] == 1,
          "a call the ledger says was paid for, but the cache lacks, is refused unless refetch is asked for")
    go(c, [IK.meta("121")], refetch=True)
    check(st["n"] == 2, "refetch pays again on purpose")
tmp_s = tempfile.mkdtemp(prefix="ik-sample-")
try:
    shutil.copy(os.path.join(HERE, "goodlaw", "data", "ik_sample_docmeta_151036912.json"), tmp_s)
    with scripted([(200, REAL_META)], sample_dir=tmp_s) as (c, st, tmp, logs):
        seed(c)
        c.record_manual(IK.meta("151036912"), REAL_META, "phase 0")
        shutil.rmtree(c.cache_dir)
        pl = c.plan([IK.meta("151036912")], 1.0)
        check(pl.cost == 0.0 and not pl.problems and go(c, [IK.meta("151036912")])[IK.meta("151036912").key()]["response"]["numcitedby"] == 41 and st["n"] == 0,
              "the committed sample stands in for a lost cache, so Phase 0's call is not bought again")
finally:
    shutil.rmtree(tmp_s, ignore_errors=True)

# ---- the ledger: damaged or missing
for bad, why in (("this is not json\n", "a line that is not JSON"), (json.dumps({"type": "mystery"}) + "\n", "an unknown row type"),
                 (json.dumps({"type": "result", "id": "zz", "outcome": "ok"}) + "\n", "a result with no attempt"),
                 ('{"type": "attempt", "id": "q", "kind": "meta", "shape": "meta", "key": "k", "price_rs": NaN, "outcome": "pending"}\n', "a NaN price"),
                 (json.dumps({"type": "attempt", "id": "q", "kind": "meta", "shape": "meta", "key": "k", "price_rs": -5, "outcome": "pending"}) + "\n", "a negative price")):
    with scripted([(200, REAL_META)]) as (c, st, tmp, logs):
        seed(c)
        with open(c.ledger_path, "a") as fh:
            fh.write(bad)
        e = raises(IK.IKError, go, c, [IK.meta("131")])
        check(e is not None and st["n"] == 0, f"{why} in the ledger stops spending")
with scripted([(200, REAL_META)], require_ledger=True) as (c, st, tmp, logs):
    e = raises(IK.IKPlanError, go, c, [IK.meta("132")])
    check(e is not None and "missing" in str(e) and st["n"] == 0, "a missing ledger refuses a run when the ledger is required (the CLI always requires it)")
    check(c.plan([IK.meta("132")], 1.0).cost == 0.02, "a dry run still works without a ledger")

# ---- the committed ledger is valid and records Phase 0
cl = IK.Client(env={}, cache_dir=tempfile.mkdtemp(prefix="ik-test-"), ledger_path=IK.DEFAULT_LEDGER, sample_dir=IK.SAMPLE_DIR)
s = cl.status()
check(s["spent_rs"] >= 0.02 and "meta" in s["confirmed_shapes"] and s["by_shape"]["meta"]["ok"] >= 1, "the committed ledger parses and holds the Phase 0 call with its confirmed price")
check(cl.plan([IK.meta("151036912")], 1.0).cost == 0.0, "so Phase 0's call is never bought again, even from an empty cache")
shutil.rmtree(cl.cache_dir, ignore_errors=True)

# ---- throttle: serial calls are spaced by the gap
slept = []
clock = {"t": 0.0}
srv = Fake([(200, REAL_META, {})])
threading.Thread(target=srv.serve_forever, daemon=True).start()
tmp = tempfile.mkdtemp(prefix="ik-test-")
try:
    c = IK.Client(env={IK.KEY_ENV: FAKE_KEY}, cache_dir=tmp + "/c", ledger_path=tmp + "/l.jsonl", base_url=srv.url, allow_test_base=True, min_gap=0.5,
                  clock=lambda: clock["t"], sleep=lambda s_: (slept.append(s_), clock.__setitem__("t", clock["t"] + s_)), stop_file=tmp + "/S", log=lambda m: None, sample_dir=None)
    seed(c)
    go(c, [IK.meta("111"), IK.meta("112"), IK.meta("113")])
    check(len(slept) == 2 and all(abs(s_ - 0.5) < 1e-9 for s_ in slept), "three calls: two waits of the full gap")
finally:
    srv.shutdown()
    srv.server_close()
    shutil.rmtree(tmp, ignore_errors=True)

# ---- the real transport: size, encoding, deadline
with world([(200, b'{"x": "' + b"a" * 5000 + b'"}', {})]) as (c, srv, tmp, logs):
    seed(c)
    old = IK.MAX_BYTES
    IK.MAX_BYTES = 1000
    try:
        e = raises(IK.IKBadResponse, go, c, [IK.meta("141")])
    finally:
        IK.MAX_BYTES = old
    check(e is not None and c.attempts()[-1]["outcome"] == "unknown" and c.spent_total() == 0.04, "an answer longer than the limit is refused (and counted as spent)")
with world([(200, b'\xff\xfe\x00{"a": 1}', {})]) as (c, srv, tmp, logs):
    seed(c)
    e = raises(IK.IKBadResponse, go, c, [IK.meta("142")])
    check(e is not None and c.attempts()[-1]["outcome"] == "unknown", "an answer that is not valid UTF-8 is refused, not guessed at")
text = "₹ हिन्दी"
body = json.dumps(dict(REAL_META, title=text), ensure_ascii=False).encode("utf-8")
with world([(200, body, {"Content-Type": "text/plain"})]) as (c, srv, tmp, logs):
    seed(c)
    go(c, [IK.meta("143")])
    check(c.cached(IK.meta("143"))["response"]["title"] == text, "UTF-8 is read as UTF-8 whatever the content type says")
import requests as _rq
_real = _rq.request
try:
    for exc, sent in ((_rq.exceptions.ConnectTimeout, False), (_rq.exceptions.SSLError, False), (_rq.exceptions.ProxyError, False), (_rq.exceptions.ReadTimeout, True), (_rq.exceptions.ConnectionError, True)):
        def fail(*a_, _e=exc, **k_):
            raise _e("simulated")
        _rq.request = fail
        got = raises(Exception, IK._requests_transport, "POST", "https://x/", {}, {}, 1)
        check(got is not None and isinstance(got, IK.NotSent) == (not sent), f"{exc.__name__} is {'a call that may have been processed' if sent else 'NotSent'}")
finally:
    _rq.request = _real

# ---- search carries its query and page; each page is its own cache entry
with world([(200, {"found": "1 - 1 of 1", "docs": []}, {})]) as (c, srv, tmp, logs):
    c.record_manual(IK.Call("search", query="seed"), {"found": "0", "docs": []}, "seed", confirm_price=True)
    go(c, [IK.Call("search", query="youth bar association", page=1)])
    check("formInput=youth+bar+association" in srv.requests[0]["path"] and "pagenum=1" in srv.requests[0]["path"], "search sends formInput and pagenum in the query string")
    check(c.cached(IK.Call("search", query="youth bar association", page=2)) is None and os.path.exists(c._cache_path(IK.Call("search", query="youth bar association", page=1))),
          "another page of the same query is a different cache entry")
with scripted([(200, REAL_META)]) as (c, st, tmp, logs):
    seed(c)
    go(c, [IK.meta("151")])
    p = c._cache_path(IK.meta("151"))
    rec = json.load(open(p))
    rec["request"]["tid"] = "999"
    json.dump(rec, open(p, "w"))
    check(c.cached(IK.meta("151")) is None and any("does not match" in m for m in logs), "a cache file that belongs to another request is ignored and reported")
    open(p, "w").write("{ broken")
    check(c.plan([IK.meta("151")], 1.0).n_calls == 1, "a damaged cache file is reported and treated as not cached")

# ---- the command line: refusals and plans, with no key and no network
ENV = {k: v for k, v in os.environ.items() if k != IK.KEY_ENV}


def cli(*args):
    r = subprocess.run([sys.executable, os.path.join(HERE, "sci_goodlaw.py"), "ik", *args], capture_output=True, text=True, cwd=HERE, env=ENV, timeout=120)
    return r.returncode, r.stdout, r.stderr


ctmp = tempfile.mkdtemp(prefix="ik-cli-")
try:
    rc, out, err = cli("status", "--cache", ctmp)
    check(rc == 0 and '"confirmed_shapes"' in out and "meta" in out and FAKE_KEY not in out, "ik status prints the ledger's totals")
    rc, out, err = cli("plan", "--kind", "meta", "--tids", "151036912,999999991", "--run-cap", "1", "--cache", ctmp)
    check(rc == 0 and "999999991" in out and "COST OF THIS PLAN: Rs 0.02" in out and "plan id" in out, "ik plan prints a dry run (the committed sample covers the Phase 0 call)")
    rc, out, err = cli("run", "--kind", "meta", "--tids", "999999991", "--run-cap", "1", "--cache", ctmp)
    check(rc == 1 and "IKPlanError" in err and not os.path.exists(os.path.join(ctmp, "meta", "999999991.json")), "ik run without an approval is refused")
    rc, out, err = cli("run", "--kind", "meta", "--tids", "999999991", "--run-cap", "1", "--approved-rs", "0.02", "--plan-id", "00000000", "--cache", ctmp)
    check(rc == 1 and "plan id" in err, "ik run with the right amount and a wrong plan id is refused")
    for args, why in ((("plan", "--kind", "meta", "--run-cap", "nan"), "--run-cap nan"), (("plan", "--kind", "meta", "--tids", "1", "--run-cap", "inf"), "--run-cap inf"),
                      (("plan", "--kind", "meta", "--tids", "1", "--run-cap", "-3"), "a negative cap"), (("plan", "--kind", "meta", "--run-cap", "1"), "no ids"),
                      (("plan", "--kind", "meta", "--tids", "1", "--run-cap", "1", "--ledger", "/tmp/x"), "--ledger (not an option: the ledger is fixed)"),
                      (("plan", "--kind", "doc", "--tids", "1", "--extra", "maxcitedby=abc", "--run-cap", "1"), "a non-numeric --extra"),
                      (("plan", "--kind", "doc", "--tids", "1", "--extra", "maxcitedby=1", "--extra", "maxcitedby=2", "--run-cap", "1"), "a repeated --extra"),
                      (("plan", "--kind", "meta", "--tids", "1", "--page", "2", "--run-cap", "1"), "--page on meta"), (("plan", "--kind", "meta", "--tids", "x1", "--run-cap", "1"), "a bad id")):
        rc, out, err = cli(*args, "--cache", ctmp) if "--ledger" not in args else cli(*args)
        check(rc == 2 and "Traceback" not in err, f"{why}: refused with a message (exit 2), not a traceback")
    rc, out, err = cli("plan", "--kind", "doc", "--tids", "1,2,3", "--run-cap", "5", "--cache", ctmp)
    check(rc == 1 and "REFUSED" in out and "no confirmed price" in out, "ik plan of three unconfirmed doc calls is refused")
    rc, out, err = cli("plan", "--kind", "search", "--tids", "111,222", "--query-template", "citedby:{tid} doctypes:supremecourt", "--run-cap", "5", "--cache", ctmp)
    check(rc == 0 and "citedby:111 doctypes:supremecourt" in out and "citedby:222 doctypes:supremecourt" in out and "COST OF THIS PLAN: Rs 1.00" in out, "ik plan --query-template makes one search per id")
    for args, why in ((("--tids", "111", "--query-template", "citedby:{tid} {tid}"), "a template with {tid} twice"), (("--tids", "111", "--query-template", "citedby:{x}"), "a template without {tid}"),
                      (("--tids", "1;2", "--query-template", "citedby:{tid}"), "an id that is not digits"), (("--tids", "111", "--query", "a", "--query-template", "citedby:{tid}"), "both --query and --query-template"),
                      (("--query-template", "citedby:{tid}"), "a template with no ids")):
        rc, out, err = cli("plan", "--kind", "search", *args, "--run-cap", "5", "--cache", ctmp)
        check(rc == 2 and "Traceback" not in err, f"{why}: refused with a message (exit 2)")
    rc, out, err = cli("confirm", "--shape", "doc", "--price", "0.2", "--note", "x", "--cache", ctmp)
    check(rc == 1 and "IKError" in err, "ik confirm for a shape that was never answered is refused")
finally:
    shutil.rmtree(ctmp, ignore_errors=True)

print()
print("FAILED:" if FAILED else "all passed", *FAILED, sep="\n" if FAILED else " ")
raise SystemExit(1 if FAILED else 0)
