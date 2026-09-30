"""Polite, resumable downloader for the Supreme Court's open judgment archive (api.sci.gov.in/jonew/judis/<id>.pdf)."""
import argparse
import hashlib
import os
import random
import sqlite3
import sys
import threading
import time
from datetime import datetime, timezone

BASE_URL = "https://api.sci.gov.in/jonew/judis/{id}.pdf"
USER_AGENT = "Recourse-research-crawler/1.0 (low-rate, resumable)"
MIN_PDF_BYTES = 1000
JITTER = 0.3
_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))


def classify_response(http_status, content_type, body, content_length):
    """Return (kind, note). The server answers 200 with an empty body for unused IDs, so status alone proves nothing."""
    ctype = (content_type or "").lower()
    if http_status in (403, 429):
        return "blocked", f"HTTP {http_status}"
    if 300 <= http_status < 400:
        return "challenge", f"redirect HTTP {http_status}"
    if http_status == 404:
        return "gap", "HTTP 404"
    if http_status >= 500:
        return "server_error", f"HTTP {http_status}"
    if http_status != 200:
        return "challenge", f"unexpected HTTP {http_status}"
    if len(body) == 0:
        return "gap", "empty body"
    # The real server prepends a 4-byte little-endian length (file size minus 4) before %PDF-.
    marker = body[:16].find(b"%PDF-")
    if marker in (0, 4):
        if marker == 4 and int.from_bytes(body[:4], "little") != len(body) - 4:
            return "truncated", f"prefix promises {int.from_bytes(body[:4], 'little')} bytes, got {len(body) - 4}"
        if len(body) < MIN_PDF_BYTES:
            return "bad", f"too small to be a real judgment ({len(body)} bytes)"
        if content_length is not None:
            try:
                if int(content_length) != len(body):
                    return "truncated", f"got {len(body)} bytes, server promised {content_length}"
            except ValueError:
                pass
        if b"%%EOF" not in body[-2048:]:
            return "truncated", "no %%EOF marker at the end"
        return "ok", ""
    if "html" in ctype:
        return "challenge", "unexpected HTML page where a PDF should be"
    return "bad", "body is not a PDF"


def shard_path(pool_dir, id_):
    return os.path.join(pool_dir, "pdfs", f"{id_ // 1000:03d}", f"{id_}.pdf")


def check_pool_dir(pool_dir):
    p = os.path.normcase(os.path.abspath(pool_dir))
    root = os.path.normcase(_REPO_ROOT)
    if p == root or p.startswith(root + os.sep):
        raise ValueError("the pool folder must be outside the project folder (it would be git-tracked and auto-loaded)")
    parts = [x for x in p.replace("\\", "/").split("/") if x]
    if any(x.startswith("onedrive") for x in parts):
        raise ValueError("the pool folder must be outside OneDrive (it would sync gigabytes to the cloud)")


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _connect(pool_dir):
    os.makedirs(pool_dir, exist_ok=True)
    conn = sqlite3.connect(os.path.join(pool_dir, "crawl.db"), check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS fetch_log (id INTEGER PRIMARY KEY, status TEXT NOT NULL, http INTEGER,"
        " content_type TEXT, bytes INTEGER, sha256 TEXT, ms INTEGER, fetched_at TEXT, note TEXT)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS run_log (run_id INTEGER PRIMARY KEY AUTOINCREMENT, started_at TEXT, ended_at TEXT,"
        " workers INTEGER, pause REAL, from_id INTEGER, to_id INTEGER, attempted INTEGER, ok INTEGER, gap INTEGER,"
        " error INTEGER, stop_reason TEXT)"
    )
    conn.commit()
    return conn


def http_fetcher():
    import requests

    local = threading.local()

    def fetch(id_):
        session = getattr(local, "session", None)
        if session is None:
            session = requests.Session()
            session.headers.update({"User-Agent": USER_AGENT})
            local.session = session
        r = session.get(BASE_URL.format(id=id_), timeout=(15, 90), allow_redirects=False)
        # Content-Length describes the compressed size when the server gzips, so only trust it when it does not.
        clen = None if r.headers.get("Content-Encoding") else r.headers.get("Content-Length")
        return r.status_code, r.headers.get("Content-Type", ""), r.content, clen

    return fetch


def run(pool_dir, from_id, to_id, workers=2, pause=1.5, limit=None, max_minutes=None, fetcher=None,
        sleep=time.sleep, retries=2, backoff=(2.0, 5.0), max_consecutive_gaps=300, max_consecutive_errors=5,
        progress_every=50, out=print):
    check_pool_dir(pool_dir)
    fetcher = fetcher or http_fetcher()
    step = -1 if from_id > to_id else 1
    conn = _connect(pool_dir)
    done = {r[0] for r in conn.execute("SELECT id FROM fetch_log WHERE status IN ('ok', 'gap')")}
    todo = [i for i in range(from_id, to_id + step, step) if i not in done]

    lock = threading.Lock()
    state = {"i": 0, "attempted": 0, "ok": 0, "gap": 0, "error": 0, "consec_gap": 0, "consec_err": 0, "stop": None}
    started, started_iso, rng = time.monotonic(), _now(), random.Random()
    stop_file = os.path.join(pool_dir, "STOP")

    def request_stop(reason):
        if state["stop"] is None:
            state["stop"] = reason

    def next_id():
        with lock:
            if state["stop"]:
                return None
            if os.path.exists(stop_file):
                request_stop("stop file found in the pool folder")
                return None
            if max_minutes is not None and time.monotonic() - started >= max_minutes * 60:
                request_stop("time limit reached")
                return None
            if limit is not None and state["attempted"] >= limit:
                request_stop("attempt limit reached")
                return None
            if state["i"] >= len(todo):
                return None
            id_ = todo[state["i"]]
            state["i"] += 1
            state["attempted"] += 1
            return id_

    def fetch_with_retries(id_):
        attempt = 0
        while True:
            t0 = time.monotonic()
            try:
                status, ctype, body, clen = fetcher(id_)
                kind, note = classify_response(status, ctype, body, clen)
            except Exception as e:
                status, ctype, body, clen = None, "", b"", None
                kind, note = "error", f"{type(e).__name__}: {e}"[:200]
            ms = int((time.monotonic() - t0) * 1000)
            if kind in ("ok", "gap", "blocked", "challenge") or attempt >= retries:
                return status, ctype, body, kind, note, ms
            sleep(backoff[min(attempt, len(backoff) - 1)])
            attempt += 1

    def save_pdf(id_, body):
        final = shard_path(pool_dir, id_)
        os.makedirs(os.path.dirname(final), exist_ok=True)
        tmp = final + ".part"
        try:
            with open(tmp, "wb") as fh:
                fh.write(body)
            os.replace(tmp, final)
        except Exception as e:
            if os.path.exists(tmp):
                os.remove(tmp)
            return f"write failed: {e}"[:200]
        return None

    def record(id_, status, ctype, body, kind, note, ms):
        sha = None
        if kind == "ok":
            write_error = save_pdf(id_, body)
            if write_error:
                kind, note = "error", write_error
            else:
                sha = hashlib.sha256(body).hexdigest()
        logged = kind if kind in ("ok", "gap", "blocked", "challenge") else "error"
        if logged == "error" and note and kind != "error":
            note = f"{kind}: {note}"
        with lock:
            conn.execute(
                "INSERT OR REPLACE INTO fetch_log VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (id_, logged, status, ctype, len(body) if kind == "ok" else 0, sha, ms, _now(), note or None),
            )
            conn.commit()
            if logged == "ok":
                state["ok"] += 1
                state["consec_gap"] = state["consec_err"] = 0
            elif logged == "gap":
                state["gap"] += 1
                state["consec_gap"] += 1
                state["consec_err"] = 0
                if state["consec_gap"] >= max_consecutive_gaps:
                    request_stop(f"{state['consec_gap']} empty answers in a row: end of the archive, or the site has changed")
            else:
                state["error"] += 1
                state["consec_gap"] = 0
                state["consec_err"] += 1
                if logged == "blocked":
                    request_stop(f"blocked by the server ({note}); stopped rather than push harder")
                elif logged == "challenge":
                    request_stop(f"challenge or unexpected page from the server ({note}); stopped")
                elif state["consec_err"] >= max_consecutive_errors:
                    request_stop(f"too many errors in a row ({state['consec_err']}); last: {note}")
            finished = state["ok"] + state["gap"] + state["error"]
            if progress_every and finished % progress_every == 0:
                out(f"[{_now()}] finished {finished} | ok {state['ok']} | empty {state['gap']}"
                    f" | errors {state['error']} | last id {id_}")

    def worker():
        try:
            while True:
                id_ = next_id()
                if id_ is None:
                    return
                record(id_, *fetch_with_retries(id_))
                sleep(pause * (1 + JITTER * rng.random()))
        except Exception as e:
            with lock:
                request_stop(f"internal error: {type(e).__name__}: {e}"[:200])

    threads = [threading.Thread(target=worker, daemon=True) for _ in range(max(1, workers))]
    for t in threads:
        t.start()
    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        with lock:
            request_stop("interrupted by the user (Ctrl+C)")
        for t in threads:
            t.join()

    if state["stop"] is None:
        state["stop"] = f"completed the requested range ({from_id} to {to_id})"
    elapsed = time.monotonic() - started
    conn.execute(
        "INSERT INTO run_log (started_at, ended_at, workers, pause, from_id, to_id, attempted, ok, gap, error, stop_reason)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (started_iso, _now(), workers, pause, from_id, to_id, state["attempted"], state["ok"], state["gap"],
         state["error"], state["stop"]),
    )
    conn.commit()
    conn.close()
    return {"attempted": state["attempted"], "ok": state["ok"], "gap": state["gap"], "error": state["error"],
            "stop_reason": state["stop"], "elapsed_s": round(elapsed, 1)}


def status_summary(pool_dir):
    summary = {"ok": 0, "gap": 0, "error": 0, "total_bytes": 0, "min_id": None, "max_id": None, "last_run": None}
    db = os.path.join(pool_dir, "crawl.db")
    if not os.path.exists(db):
        return summary
    conn = sqlite3.connect(db)
    counts = dict(conn.execute("SELECT status, COUNT(*) FROM fetch_log GROUP BY status"))
    summary["ok"] = counts.get("ok", 0)
    summary["gap"] = counts.get("gap", 0)
    summary["error"] = sum(n for k, n in counts.items() if k not in ("ok", "gap"))
    summary["total_bytes"] = conn.execute("SELECT COALESCE(SUM(bytes), 0) FROM fetch_log WHERE status = 'ok'").fetchone()[0]
    summary["min_id"], summary["max_id"] = conn.execute("SELECT MIN(id), MAX(id) FROM fetch_log").fetchone()
    last = conn.execute(
        "SELECT started_at, ended_at, attempted, ok, gap, error, stop_reason FROM run_log ORDER BY run_id DESC LIMIT 1"
    ).fetchone()
    if last:
        keys = ("started_at", "ended_at", "attempted", "ok", "gap", "error", "stop_reason")
        summary["last_run"] = dict(zip(keys, last))
    conn.close()
    return summary


def _default_pool_dir():
    return os.environ.get("SCI_POOL_DIR") or os.path.join(os.path.expanduser("~"), "sci_pool")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="download a range of IDs (safe to stop and restart)")
    r.add_argument("--from-id", type=int, required=True)
    r.add_argument("--to-id", type=int, required=True)
    r.add_argument("--workers", type=int, default=2)
    r.add_argument("--pause", type=float, default=1.5)
    r.add_argument("--limit", type=int)
    r.add_argument("--max-minutes", type=float)
    for name, help_ in (("status", "show progress"), ("stop", "ask a running crawl to stop after its current files")):
        sub.add_parser(name, help=help_)
    for p in sub.choices.values():
        p.add_argument("--pool-dir", default=_default_pool_dir())
    args = ap.parse_args(argv)
    try:
        check_pool_dir(args.pool_dir)
    except ValueError as e:
        print(f"Refused: {e}")
        return 2
    stop_file = os.path.join(args.pool_dir, "STOP")

    if args.cmd == "stop":
        os.makedirs(args.pool_dir, exist_ok=True)
        open(stop_file, "w").close()
        print("Stop requested: the running crawl will halt after its current downloads.")
    elif args.cmd == "status":
        s = status_summary(args.pool_dir)
        print(f"Pool: {args.pool_dir}")
        print(f"Done: {s['ok'] + s['gap']} IDs (real judgments {s['ok']}, empty {s['gap']}, need retry {s['error']})")
        print(f"IDs covered: {s['min_id']} to {s['max_id']}; downloaded {s['total_bytes'] / 1e6:.1f} MB")
        if s["last_run"]:
            lr = s["last_run"]
            print(f"Last run: {lr['attempted']} IDs, ended {lr['ended_at']}: {lr['stop_reason']}")
    else:
        if os.path.exists(stop_file):
            os.remove(stop_file)
        res = run(args.pool_dir, args.from_id, args.to_id, workers=args.workers, pause=args.pause,
                  limit=args.limit, max_minutes=args.max_minutes)
        print(f"Finished: {res['attempted']} IDs in {res['elapsed_s']}s "
              f"(ok {res['ok']}, empty {res['gap']}, errors {res['error']}). Reason: {res['stop_reason']}")
        return 0 if res["error"] == 0 else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
