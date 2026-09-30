"""Tests for sci_crawl.py (no network: a fake fetcher and fake sleep are injected). Run: python test_sci_crawl.py"""
import os
import shutil
import sqlite3
import tempfile
import threading
import time

import sci_crawl

FAILURES = []


def check(condition, description):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {description}")
    if not condition:
        FAILURES.append(description)


def good_pdf(size=2000, prefixed=True):
    # The real server puts a 4-byte little-endian length (file size minus 4) in front of %PDF-.
    pdf = b"%PDF-1.4\n" + (b"x" * size) + b"\n%%EOF\n"
    body = len(pdf).to_bytes(4, "little") + pdf if prefixed else pdf
    return (200, "application/pdf", body, str(len(body)))


EMPTY_HTML = (200, "text/html; charset=UTF-8", b"", "0")
EMPTY_PDF = (200, "application/pdf", b"", "0")


def make_fetcher(behaviors, default=None, calls=None, delay=0.0):
    lock = threading.Lock()
    calls = calls if calls is not None else []

    def fetch(id_):
        with lock:
            calls.append(id_)
        if delay:
            time.sleep(delay)
        b = behaviors.get(id_, default if default is not None else good_pdf())
        if isinstance(b, Exception):
            raise b
        return b

    return fetch


def no_sleep(_seconds):
    return None


def fresh_pool():
    return tempfile.mkdtemp(prefix="sci_pool_test_")


def db_rows(pool):
    c = sqlite3.connect(os.path.join(pool, "crawl.db"))
    rows = c.execute("select id, status, http, bytes, sha256, note from fetch_log order by id").fetchall()
    c.close()
    return rows


def part_files(pool):
    found = []
    for root, _dirs, files in os.walk(pool):
        found += [f for f in files if f.endswith(".part")]
    return found


# ---------------------------------------------------------------- classify_response
kind, _ = sci_crawl.classify_response(*good_pdf())
check(kind == "ok", "a complete file exactly as the real server sends it (4-byte length prefix, then %PDF-...%%EOF) is ok")
check(sci_crawl.classify_response(*good_pdf(prefixed=False))[0] == "ok", "a plain PDF with no prefix is also ok")
_cut = good_pdf()
check(sci_crawl.classify_response(200, "application/pdf", _cut[2][:600], None)[0] == "truncated",
      "a prefixed file cut short (prefix promises more bytes than arrived) is truncated, like the real partial 43300.pdf")
_junk = (2000).to_bytes(4, "little") + b"NOTAPDF" * 400
check(sci_crawl.classify_response(200, "application/pdf", _junk, None)[0] == "bad", "a prefixed body that does not contain %PDF- is bad")

check(sci_crawl.classify_response(*EMPTY_HTML)[0] == "gap",
      "HTTP 200 with a 0-byte text/html body is a GAP (unused ID), not a document")
check(sci_crawl.classify_response(*EMPTY_PDF)[0] == "gap",
      "HTTP 200 with a 0-byte application/pdf body is ALSO a gap (the server does both)")
check(sci_crawl.classify_response(404, "text/html", b"Not found", None)[0] == "gap",
      "a real 404 is treated as a gap, not an error")
check(sci_crawl.classify_response(200, "text/html", b"<html>Please verify you are human</html>", None)[0] == "challenge",
      "a NON-EMPTY html page where a PDF should be is a challenge/unexpected page -> stop signal")
check(sci_crawl.classify_response(302, "text/html", b"", None)[0] == "challenge",
      "a redirect is treated as a challenge (redirects are never followed)")
check(sci_crawl.classify_response(403, "text/html", b"Forbidden", None)[0] == "blocked",
      "HTTP 403 is 'blocked'")
check(sci_crawl.classify_response(429, "text/html", b"Too many", None)[0] == "blocked",
      "HTTP 429 is 'blocked'")
check(sci_crawl.classify_response(503, "text/html", b"oops", None)[0] == "server_error",
      "HTTP 5xx is a (retryable) server error")

trunc_body = b"%PDF-1.4\n" + b"x" * 3000
check(sci_crawl.classify_response(200, "application/pdf", trunc_body, None)[0] == "truncated",
      "a PDF with no %%EOF marker is truncated, never ok")
full = b"%PDF-1.4\n" + b"x" * 3000 + b"\n%%EOF\n"
check(sci_crawl.classify_response(200, "application/pdf", full, str(len(full) + 500))[0] == "truncated",
      "a PDF shorter than its own Content-Length is truncated")
check(sci_crawl.classify_response(200, "application/pdf", full, None)[0] == "ok",
      "a missing Content-Length does not, by itself, make a PDF suspicious")
check(sci_crawl.classify_response(200, "application/pdf", b"%PDF-1.4\n%%EOF\n", None)[0] == "bad",
      "an implausibly tiny 'PDF' is bad, not ok")
check(sci_crawl.classify_response(200, "application/pdf", b"garbage-not-a-pdf" * 200, None)[0] == "bad",
      "a body that does not start with %PDF- is bad even if labelled application/pdf")

# ---------------------------------------------------------------- shard_path / pool-dir guard
p = sci_crawl.shard_path("POOL", 37014)
check(p.replace("\\", "/") == "POOL/pdfs/037/37014.pdf", "shard_path groups files 1000 per folder: 37014 -> pdfs/037/37014.pdf")
check(sci_crawl.shard_path("POOL", 7).replace("\\", "/") == "POOL/pdfs/000/7.pdf", "shard_path handles single-digit IDs")

repo_root = os.path.dirname(os.path.abspath(sci_crawl.__file__))
for bad in (os.path.join(repo_root, "sci_pool"), os.path.join(repo_root, "chunks", "pool"), repo_root):
    try:
        sci_crawl.check_pool_dir(bad)
        refused = False
    except ValueError:
        refused = True
    check(refused, f"a pool folder inside the project folder is refused: {os.path.relpath(bad, os.path.dirname(repo_root))}")

try:
    sci_crawl.check_pool_dir(r"C:\Users\someone\OneDrive\Documents\sci_pool")
    refused = False
except ValueError:
    refused = True
check(refused, "a pool folder inside OneDrive is refused (it would sync gigabytes to the cloud)")

ok_dir = fresh_pool()
try:
    sci_crawl.check_pool_dir(ok_dir)
    accepted = True
except ValueError:
    accepted = False
check(accepted, "a normal folder outside the repo and outside OneDrive is accepted")
shutil.rmtree(ok_dir, ignore_errors=True)

# ---------------------------------------------------------------- run(): basic download
pool = fresh_pool()
calls = []
res = sci_crawl.run(pool, 10, 1, workers=1, pause=1.5, fetcher=make_fetcher({}, calls=calls), sleep=no_sleep)
rows = db_rows(pool)
check(res["attempted"] == 10 and res["ok"] == 10 and res["gap"] == 0 and res["error"] == 0,
      "10 good PDFs -> attempted 10, ok 10, gap 0, error 0")
check(calls == list(range(10, 0, -1)), "with one worker and from_id > to_id, IDs are fetched newest-first (descending)")
check(len(rows) == 10 and all(r[1] == "ok" for r in rows), "every fetched ID has an 'ok' row in the log")
files_ok = all(os.path.exists(sci_crawl.shard_path(pool, r[0])) for r in rows)
check(files_ok, "every 'ok' ID has its PDF saved at the sharded path")
import hashlib
sample = rows[0]
with open(sci_crawl.shard_path(pool, sample[0]), "rb") as fh:
    real_hash = hashlib.sha256(fh.read()).hexdigest()
check(sample[4] == real_hash, "the logged sha256 matches the saved file's real sha256")
check(part_files(pool) == [], "no half-written .part files are left behind")
check(res["stop_reason"] and "completed" in res["stop_reason"], "a run that covers its range reports it completed")

# ascending direction
pool_a = fresh_pool()
calls_a = []
sci_crawl.run(pool_a, 1, 5, workers=1, pause=1.0, fetcher=make_fetcher({}, calls=calls_a), sleep=no_sleep)
check(calls_a == [1, 2, 3, 4, 5], "from_id < to_id fetches ascending")
shutil.rmtree(pool_a, ignore_errors=True)

# ---------------------------------------------------------------- gaps
pool_g = fresh_pool()
beh = {3: EMPTY_HTML, 5: EMPTY_PDF}
res_g = sci_crawl.run(pool_g, 1, 6, workers=1, pause=1.0, fetcher=make_fetcher(beh), sleep=no_sleep)
rows_g = {r[0]: r for r in db_rows(pool_g)}
check(res_g["gap"] == 2 and res_g["ok"] == 4, "two empty answers are counted as gaps, four as ok")
check(rows_g[3][1] == "gap" and rows_g[5][1] == "gap", "gap IDs are logged with status 'gap'")
check(not os.path.exists(sci_crawl.shard_path(pool_g, 3)), "no file is written for a gap")
shutil.rmtree(pool_g, ignore_errors=True)

# ---------------------------------------------------------------- resume
pool_r = fresh_pool()
c1 = []
sci_crawl.run(pool_r, 1, 8, workers=1, pause=1.0, fetcher=make_fetcher({4: EMPTY_HTML}, calls=c1), sleep=no_sleep)
c2 = []
res_r = sci_crawl.run(pool_r, 1, 8, workers=1, pause=1.0, fetcher=make_fetcher({4: EMPTY_HTML}, calls=c2), sleep=no_sleep)
check(c2 == [] and res_r["attempted"] == 0, "re-running a finished range fetches NOTHING (ok and gap IDs are both done)")

# an ID that ended in error is retried on the next run
pool_e = fresh_pool()
sci_crawl.run(pool_e, 1, 4, workers=1, pause=1.0, retries=1,
              fetcher=make_fetcher({2: ConnectionError("boom")}), sleep=no_sleep)
rows_e = {r[0]: r for r in db_rows(pool_e)}
check(rows_e[2][1] == "error" and rows_e[1][1] == "ok", "an ID that keeps failing is logged as 'error', neighbours are unaffected")
c3 = []
sci_crawl.run(pool_e, 1, 4, workers=1, pause=1.0, retries=1, fetcher=make_fetcher({}, calls=c3), sleep=no_sleep)
check(c3 == [2], "on the next run ONLY the errored ID is fetched again")
check({r[0]: r[1] for r in db_rows(pool_e)}[2] == "ok", "the previously errored ID is 'ok' after the retry succeeds")
shutil.rmtree(pool_e, ignore_errors=True)

# ---------------------------------------------------------------- retries / error handling
pool_t = fresh_pool()
calls_t = []
sleeps_t = []
res_t = sci_crawl.run(pool_t, 3, 1, workers=1, pause=1.0, retries=2, backoff=(2.0, 5.0),
                      fetcher=make_fetcher({2: ConnectionError("net down")}, calls=calls_t),
                      sleep=lambda s: sleeps_t.append(s))
check(calls_t.count(2) == 3, "a failing ID is tried 1 + retries(2) = 3 times, then given up on")
check(2.0 in sleeps_t and 5.0 in sleeps_t, "retries wait with the configured backoff (2s then 5s)")
check(res_t["error"] == 1 and res_t["ok"] == 2, "one errored ID does not stop the run; the others complete")
shutil.rmtree(pool_t, ignore_errors=True)

pool_tr = fresh_pool()
res_tr = sci_crawl.run(pool_tr, 2, 1, workers=1, pause=1.0, retries=1,
                       fetcher=make_fetcher({}, default=(200, "application/pdf", trunc_body, None)), sleep=no_sleep)
rows_tr = db_rows(pool_tr)
check(all(r[1] == "error" for r in rows_tr), "truncated downloads end as 'error', never 'ok'")
check(not any(os.path.exists(sci_crawl.shard_path(pool_tr, r[0])) for r in rows_tr), "no final file exists for a truncated download")
check(part_files(pool_tr) == [], "no .part file is left behind after a truncated download")
shutil.rmtree(pool_tr, ignore_errors=True)

pool_ce = fresh_pool()
res_ce = sci_crawl.run(pool_ce, 30, 1, workers=1, pause=1.0, retries=0, max_consecutive_errors=5,
                       fetcher=make_fetcher({}, default=ConnectionError("down")), sleep=no_sleep)
check(res_ce["stop_reason"] and "too many errors" in res_ce["stop_reason"], "5 errors in a row stop the run with a clear reason")
check(res_ce["attempted"] == 5, "the run stops promptly at the 5th consecutive error (does not grind on through all 30 IDs)")
shutil.rmtree(pool_ce, ignore_errors=True)

# ---------------------------------------------------------------- stop signals
pool_b = fresh_pool()
calls_b = []
res_b = sci_crawl.run(pool_b, 10, 1, workers=1, pause=1.0,
                      fetcher=make_fetcher({6: (403, "text/html", b"Forbidden", None)}, calls=calls_b), sleep=no_sleep)
check(res_b["stop_reason"] and "blocked" in res_b["stop_reason"], "an HTTP 403 stops the whole run, reason says blocked")
check(calls_b == [10, 9, 8, 7, 6], "after the block, NO further IDs are requested (no retry-hammering)")
st_b = {r[0]: r[1] for r in db_rows(pool_b)}
check(st_b.get(6) not in ("ok", "gap"), "the blocked ID is NOT recorded as done, so it is retried on the next run")
shutil.rmtree(pool_b, ignore_errors=True)

pool_c = fresh_pool()
calls_c = []
res_c = sci_crawl.run(pool_c, 10, 1, workers=1, pause=1.0,
                      fetcher=make_fetcher({8: (200, "text/html", b"<html>captcha</html>", None)}, calls=calls_c), sleep=no_sleep)
check(res_c["stop_reason"] and "challenge" in res_c["stop_reason"], "an unexpected non-empty HTML page stops the run (challenge)")
check(calls_c == [10, 9, 8], "nothing is requested after a challenge page appears")
shutil.rmtree(pool_c, ignore_errors=True)

pool_end = fresh_pool()
res_end = sci_crawl.run(pool_end, 50, 1, workers=1, pause=1.0, max_consecutive_gaps=6,
                        fetcher=make_fetcher({}, default=EMPTY_HTML), sleep=no_sleep)
check(res_end["stop_reason"] and "empty answers" in res_end["stop_reason"],
      "a long unbroken run of empty answers stops the run (end of archive, or the site changed)")
check(res_end["attempted"] == 6, "the empty-run stop triggers exactly at the configured limit")
shutil.rmtree(pool_end, ignore_errors=True)

pool_s = fresh_pool()
open(os.path.join(pool_s, "STOP"), "w").close()
calls_s = []
res_s = sci_crawl.run(pool_s, 10, 1, workers=1, pause=1.0, fetcher=make_fetcher({}, calls=calls_s), sleep=no_sleep)
check(calls_s == [] and res_s["stop_reason"] and "stop file" in res_s["stop_reason"],
      "a STOP file in the pool folder halts the run before it fetches anything")
shutil.rmtree(pool_s, ignore_errors=True)

pool_l = fresh_pool()
calls_l = []
res_l = sci_crawl.run(pool_l, 100, 1, workers=1, pause=1.0, limit=3, fetcher=make_fetcher({}, calls=calls_l), sleep=no_sleep)
check(len(calls_l) == 3 and res_l["attempted"] == 3, "limit=3 attempts exactly 3 IDs")
check(res_l["stop_reason"] and "limit" in res_l["stop_reason"], "the limit stop is reported as such")
shutil.rmtree(pool_l, ignore_errors=True)

pool_m = fresh_pool()
calls_m = []
res_m = sci_crawl.run(pool_m, 100, 1, workers=1, pause=1.0, max_minutes=0, fetcher=make_fetcher({}, calls=calls_m), sleep=no_sleep)
check(calls_m == [] and res_m["stop_reason"] and "time limit" in res_m["stop_reason"], "max_minutes=0 stops before fetching anything")
shutil.rmtree(pool_m, ignore_errors=True)

# ---------------------------------------------------------------- politeness + concurrency
pool_p = fresh_pool()
sleeps = []
sci_crawl.run(pool_p, 8, 1, workers=1, pause=1.5, fetcher=make_fetcher({}), sleep=lambda s: sleeps.append(s))
check(len(sleeps) == 8, "one courtesy pause after every fetch (8 fetches -> 8 pauses)")
check(all(1.5 <= s <= 1.5 * 1.3 + 1e-9 for s in sleeps), "every pause is at least the configured 1.5s (plus a little random jitter, never less)")
shutil.rmtree(pool_p, ignore_errors=True)

pool_w = fresh_pool()
calls_w = []
res_w = sci_crawl.run(pool_w, 90, 1, workers=3, pause=0.0, fetcher=make_fetcher({}, calls=calls_w, delay=0.002), sleep=no_sleep)
check(sorted(calls_w) == list(range(1, 91)), "3 workers fetch every ID exactly once (no duplicates, none missed)")
check(len(db_rows(pool_w)) == 90 and res_w["ok"] == 90, "3 workers log exactly one row per ID")
shutil.rmtree(pool_w, ignore_errors=True)

# ---------------------------------------------------------------- an unexpected bug must never look like success
pool_i = fresh_pool()


def exploding_sleep(_seconds):
    raise RuntimeError("disk exploded")


res_i = sci_crawl.run(pool_i, 10, 1, workers=1, pause=1.0, fetcher=make_fetcher({}), sleep=exploding_sleep)
check(res_i["stop_reason"] and "internal error" in res_i["stop_reason"],
      "an unexpected exception inside a worker stops the run and says 'internal error' (never a false 'completed')")
check(res_i["attempted"] < 10, "after an internal error the run does not carry on regardless")
shutil.rmtree(pool_i, ignore_errors=True)

# ---------------------------------------------------------------- status_summary
pool_x = fresh_pool()
sci_crawl.run(pool_x, 1, 6, workers=1, pause=1.0, fetcher=make_fetcher({2: EMPTY_HTML}), sleep=no_sleep)
sm = sci_crawl.status_summary(pool_x)
check(sm["ok"] == 5 and sm["gap"] == 1 and sm["error"] == 0, "status_summary counts ok / gap / error correctly")
check(sm["total_bytes"] > 5 * 2000, "status_summary reports the total downloaded size")
check(sm["min_id"] == 1 and sm["max_id"] == 6, "status_summary reports the ID span covered")
check(sm["last_run"] and "completed" in sm["last_run"]["stop_reason"], "status_summary includes the last run's stop reason")
empty = sci_crawl.status_summary(fresh_pool())
check(empty["ok"] == 0 and empty["gap"] == 0 and empty["last_run"] is None, "status_summary on a brand-new pool is all zeros, no crash")

for d in (pool, pool_r, pool_x):
    shutil.rmtree(d, ignore_errors=True)

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILED:")
    for f in FAILURES:
        print("  -", f)
    raise SystemExit(1)
print("ALL PASSED")
