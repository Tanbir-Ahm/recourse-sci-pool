"""Time-boxed "shift" runner: crawls the next unfinished blocks of SC judgments and saves them as shard files in a git repo.

The shard files ARE the ledger: a block is done exactly when its shard is committed. Any machine can run a shift.
"""
import argparse
import glob
import gzip
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone

import sci_crawl

BLOCK_SIZE = 250
_SHARD_RE = re.compile(r"^(\d{6})-(\d{6})\.ok(\d+)\.gap(\d+)\.err(\d+)\.jsonl\.gz$")


def block_start(id_, block_size=BLOCK_SIZE):
    return id_ // block_size * block_size


def shard_name(start, block_size, ok, gap, err):
    return f"{start:06d}-{start + block_size - 1:06d}.ok{ok}.gap{gap}.err{err}.jsonl.gz"


def parse_shard_name(name):
    m = _SHARD_RE.match(name)
    return tuple(int(x) for x in m.groups()) if m else None


def pending_blocks(done_starts, from_id, to_id, block_size=BLOCK_SIZE):
    lo, hi = sorted((from_id, to_id))
    starts = [s for s in range(block_start(lo, block_size), block_start(hi, block_size) + 1, block_size) if s not in done_starts]
    return starts[::-1] if from_id > to_id else starts


def _ledger(data_dir):
    found = {}
    for path in glob.glob(os.path.join(data_dir, "shards", "*.jsonl.gz")):
        parsed = parse_shard_name(os.path.basename(path))
        if parsed:
            found[parsed[0]] = parsed
    return found


def _git(data_dir, *args):
    return subprocess.run(["git", "-C", data_dir, *args], capture_output=True, text=True, encoding="utf-8", errors="replace")


def _last_line(proc):
    lines = (proc.stderr or proc.stdout or "").strip().splitlines()
    return lines[-1] if lines else "no message"


def _sync(data_dir):
    if not _git(data_dir, "remote").stdout.split():
        return True, ""
    branch = _git(data_dir, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    if _git(data_dir, "ls-remote", "--exit-code", "--heads", "origin", branch).returncode != 0:
        return True, ""
    p = _git(data_dir, "pull", "--rebase", "origin", branch)
    return p.returncode == 0, _last_line(p)


def _push(data_dir):
    p = _git(data_dir, "push", "origin", "HEAD")
    if p.returncode != 0 and _sync(data_dir)[0]:
        p = _git(data_dir, "push", "origin", "HEAD")
    return p.returncode == 0, _last_line(p)


def extract_pdf(body):
    try:
        import pymupdf as fitz
    except ImportError:
        import fitz

    data = body[4:] if body[4:9] == b"%PDF-" else body
    doc = fitz.open(stream=data, filetype="pdf")
    try:
        pages = [p.get_text() for p in doc]
        producer = (doc.metadata or {}).get("producer") or ""
    finally:
        doc.close()
    if not pages:
        raise ValueError("no pages")
    return "\f".join(pages), len(pages), producer


def _records_for_block(tmp_pool):
    import sqlite3

    conn = sqlite3.connect(os.path.join(tmp_pool, "crawl.db"))
    rows = conn.execute("SELECT id, status, http, bytes, sha256, note, ms FROM fetch_log ORDER BY id").fetchall()
    conn.close()
    records = []
    for id_, status, http, nbytes, sha, note, ms in rows:
        rec = {"id": id_, "status": status, "http": http, "ms": ms}
        if status == "ok":
            with open(sci_crawl.shard_path(tmp_pool, id_), "rb") as fh:
                body = fh.read()
            rec.update(bytes=nbytes, sha256=sha)
            try:
                text, pages, producer = extract_pdf(body)
                rec.update(pages=pages, producer=producer, text_chars=len(text), text=text)
            except Exception as e:
                rec.update(status="error", note=f"text extraction failed: {type(e).__name__}: {e}"[:200])
        elif status != "gap":
            rec.update(status="error", note=note)
        records.append(rec)
    return records


def _write_shard(data_dir, start, block_size, records):
    counts = {"ok": 0, "gap": 0, "error": 0}
    for r in records:
        counts[r["status"]] += 1
    name = shard_name(start, block_size, counts["ok"], counts["gap"], counts["error"])
    os.makedirs(os.path.join(data_dir, "shards"), exist_ok=True)
    final = os.path.join(data_dir, "shards", name)
    tmp = os.path.join(data_dir, "shards", ".tmp-" + name)
    with gzip.open(tmp, "wt", encoding="utf-8", errors="replace") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    os.replace(tmp, final)
    return name, counts


def _commit(data_dir, paths, message):
    for args in (("add", "--", *paths), ("commit", "-m", message)):
        p = _git(data_dir, *args)
        if p.returncode != 0:
            raise RuntimeError(f"git {args[0]} failed: {_last_line(p)}")


def shift(data_dir, from_id, to_id, minutes=50, workers=2, pause=1.5, block_size=BLOCK_SIZE, fetcher=None,
          sleep=time.sleep, clock=time.monotonic, push_every=1, est_block_seconds=360, empty_blocks_stop=3,
          retries=2, backoff=(2.0, 5.0), out=print):
    if _git(data_dir, "rev-parse", "--is-inside-work-tree").returncode != 0:
        raise ValueError(f"{data_dir} is not a git repository")
    started_iso, t0 = datetime.now(timezone.utc).isoformat(timespec="seconds"), clock()
    totals = {"blocks_done": 0, "ok": 0, "gap": 0, "error": 0}
    reason, unpushed, seen_real, consec_empty, est = None, 0, False, 0, est_block_seconds
    stop_file = os.path.join(data_dir, "STOP")

    ok, msg = _sync(data_dir)
    if not ok:
        reason = f"could not update from the remote: {msg}"
    elif os.path.exists(stop_file):
        reason = "STOP file present in the data repo"

    try:
        todo = [] if reason else pending_blocks(set(_ledger(data_dir)), from_id, to_id, block_size)
        if not reason and not todo:
            reason = "nothing left to do in this range"
        for start in todo:
            if reason:
                break
            if os.path.exists(stop_file):
                reason = "STOP file present in the data repo"
                break
            remaining = minutes * 60 - (clock() - t0)
            if remaining < est:
                reason = f"time budget used up ({remaining:.0f}s left, a block takes about {est:.0f}s)"
                break
            end = start + block_size - 1
            first, last = (end, start) if from_id > to_id else (start, end)
            tmp = tempfile.mkdtemp(prefix="sci_block_")
            b0 = clock()
            try:
                res = sci_crawl.run(tmp, first, last, workers=workers, pause=pause, max_minutes=remaining / 60,
                                    fetcher=fetcher, sleep=sleep, retries=retries, backoff=backoff,
                                    max_consecutive_gaps=10**9, out=lambda *_: None)
                if not res["stop_reason"].startswith("completed"):
                    reason = f"stopped inside block {start}: {res['stop_reason']} (that block is discarded and will be redone)"
                    break
                records = _records_for_block(tmp)
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
            name, counts = _write_shard(data_dir, start, block_size, records)
            _commit(data_dir, [os.path.join("shards", name)], f"shard {name}")
            for k in ("ok", "gap", "error"):
                totals[k] += counts[k]
            totals["blocks_done"] += 1
            unpushed += 1
            secs = clock() - b0
            est = max(secs * 1.25, 60)
            out(f"block {start:06d}: ok {counts['ok']} empty {counts['gap']} errors {counts['error']} ({secs:.0f}s)")
            if counts["ok"] or counts["error"]:
                seen_real, consec_empty = True, 0
            elif seen_real:
                consec_empty += 1
                if consec_empty >= empty_blocks_stop:
                    reason = f"possible end of archive: {consec_empty} empty blocks in a row after real ones"
                    break
            if unpushed >= push_every:
                pushed_ok, msg = _push(data_dir)
                if not pushed_ok:
                    reason = f"push failed: {msg}"
                    break
                unpushed = 0
        if reason is None:
            reason = "completed all pending blocks in the range"
    except Exception as e:
        reason = f"internal error: {type(e).__name__}: {e}"[:300]

    seconds = round(clock() - t0, 1)
    log = dict(started_at=started_iso, ended_at=datetime.now(timezone.utc).isoformat(timespec="seconds"), from_id=from_id,
               to_id=to_id, minutes=minutes, workers=workers, pause=pause, stop_reason=reason, seconds=seconds, **totals)
    log_rel = os.path.join("state", "shifts", f"{datetime.now(timezone.utc):%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:4]}.json")
    pushed = False
    try:
        os.makedirs(os.path.join(data_dir, "state", "shifts"), exist_ok=True)
        with open(os.path.join(data_dir, log_rel), "w", encoding="utf-8") as fh:
            json.dump(log, fh, indent=1)
        _commit(data_dir, [log_rel], "shift log")
        pushed, msg = _push(data_dir)
        if not pushed and "push failed" not in reason:
            reason += f"; push failed: {msg}"
    except Exception as e:
        reason += f"; could not save the shift log: {e}"[:200]
    return {**totals, "stop_reason": reason, "seconds": seconds, "pushed": pushed}


def status_summary(data_dir, from_id, to_id, block_size=BLOCK_SIZE):
    ledger = _ledger(data_dir)
    lo, hi = sorted((from_id, to_id))
    inside = [v for s, v in ledger.items() if block_start(lo, block_size) <= s <= block_start(hi, block_size)]
    logs = sorted(glob.glob(os.path.join(data_dir, "state", "shifts", "*.json")))
    last = None
    if logs:
        with open(logs[-1], encoding="utf-8") as fh:
            last = json.load(fh)
    return {"blocks_done": len(inside), "ok": sum(v[2] for v in inside), "gap": sum(v[3] for v in inside),
            "error": sum(v[4] for v in inside), "min_id": min((v[0] for v in inside), default=None),
            "max_id": max((v[1] for v in inside), default=None),
            "blocks_pending": len(pending_blocks(set(ledger), from_id, to_id, block_size)),
            "shifts": len(logs), "last_shift": last}


_BENIGN = ("time budget", "completed", "nothing left")


def active_check(data_dir, ref="origin/claude/sci-pool", now=None, max_age=1500):
    """Another session looks active if the branch's newest commit is a shard commit made under max_age seconds ago."""
    p = _git(data_dir, "log", "-1", "--format=%ct|%s", ref)
    if p.returncode != 0 or "|" not in p.stdout:
        return False, "no data branch yet"
    ts, subject = p.stdout.strip().split("|", 1)
    age = (now or datetime.now(timezone.utc)).timestamp() - int(ts)
    if subject.startswith("shard ") and age < max_age:
        return True, f"newest commit is a shard from {age:.0f}s ago, so another session looks active"
    return False, "no session appears to be active"


def _shift_logs(data_dir):
    logs = []
    for path in glob.glob(os.path.join(data_dir, "state", "shifts", "*.json")):
        try:
            with open(path, encoding="utf-8") as fh:
                d = json.load(fh)
            logs.append((datetime.fromisoformat(d["started_at"]), d.get("stop_reason", "")))
        except Exception:
            continue
    return sorted(logs)


def chain_guard(data_dir, from_id, to_id, block_size=BLOCK_SIZE, max_shifts_per_day=8, now=None):
    now = now or datetime.now(timezone.utc)
    if os.path.exists(os.path.join(data_dir, "STOP")):
        return False, "STOP file present"
    if not pending_blocks(set(_ledger(data_dir)), from_id, to_id, block_size):
        return False, "the crawl is finished"
    logs = _shift_logs(data_dir)
    if logs and not logs[-1][1].startswith(_BENIGN):
        return False, f"the last shift did not end normally: {logs[-1][1][:120]}"
    recent = [1 for started, _ in logs if (now - started).total_seconds() < 86400]
    if len(recent) >= max_shifts_per_day:
        return False, f"daily limit reached ({len(recent)} shifts in the last 24h, limit {max_shifts_per_day})"
    return True, "ok to chain"


def _default_poster(url, headers, payload):
    import requests

    r = requests.post(url, headers=headers, json=payload, timeout=30)
    try:
        body = r.json()
    except Exception:
        body = {"raw": r.text[:200]}
    return r.status_code, body


def chain_fire(url, token, text=None, poster=None):
    headers = {"Authorization": f"Bearer {token}", "anthropic-beta": "experimental-cc-routine-2026-04-01",
               "anthropic-version": "2023-06-01", "Content-Type": "application/json"}
    try:
        status, body = (poster or _default_poster)(url, headers, {"text": text} if text else {})
    except Exception as e:
        return False, f"fire failed: {type(e).__name__}: {e}"[:200]
    if status == 200:
        return True, f"started the next session: {body.get('claude_code_session_url', '(no link returned)')}"
    return False, f"fire refused: HTTP {status} {str(body)[:150]}"


def run_chain(data_dir, from_id, to_id, block_size=BLOCK_SIZE, env=None, poster=None, now=None, max_shifts_per_day=8):
    env = os.environ if env is None else env
    url, token = env.get("ROUTINE_FIRE_URL"), env.get("ROUTINE_FIRE_TOKEN")
    if not url or not token:
        return False, "chaining not configured (no ROUTINE_FIRE_URL / ROUTINE_FIRE_TOKEN)"
    allowed, why = chain_guard(data_dir, from_id, to_id, block_size, max_shifts_per_day, now)
    if not allowed:
        return False, f"chain stopped: {why}"
    return chain_fire(url, token, poster=poster)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("shift", help="run one time-boxed shift")
    s.add_argument("--minutes", type=float, default=50)
    s.add_argument("--workers", type=int, default=2)
    s.add_argument("--pause", type=float, default=1.5)
    sub.add_parser("status", help="show progress")
    c = sub.add_parser("chain", help="start the next session if it is safe to")
    c.add_argument("--max-shifts-per-day", type=int, default=8)
    a = sub.add_parser("active-check", help="say ACTIVE if another session looks active")
    a.add_argument("--ref", default="origin/claude/sci-pool")
    sub.add_parser("fire-test", help="fire the routine once with a TEST note (does nothing else)")
    for name, p in sub.choices.items():
        p.add_argument("--data-dir", default=".")
        if name in ("shift", "status", "chain"):
            p.add_argument("--from-id", type=int, required=True)
            p.add_argument("--to-id", type=int, default=0)
    args = ap.parse_args(argv)
    if args.cmd == "active-check":
        active, msg = active_check(args.data_dir, ref=args.ref)
        print(("ACTIVE: " if active else "IDLE: ") + msg)
        return 0
    if args.cmd == "chain":
        fired, msg = run_chain(args.data_dir, args.from_id, args.to_id, max_shifts_per_day=args.max_shifts_per_day)
        print(("CHAINED: " if fired else "NOT CHAINED: ") + msg)
        return 0
    if args.cmd == "fire-test":
        fired, msg = chain_fire(os.environ.get("ROUTINE_FIRE_URL", ""), os.environ.get("ROUTINE_FIRE_TOKEN", ""), text="TEST: chain test only")
        print(("FIRED: " if fired else "NOT FIRED: ") + msg)
        return 0 if fired else 1
    if args.cmd == "status":
        st = status_summary(args.data_dir, args.from_id, args.to_id)
        last = st["last_shift"]
        print(f"Blocks done {st['blocks_done']} (real judgments {st['ok']}, empty {st['gap']}, errors {st['error']}); "
              f"pending {st['blocks_pending']}; IDs covered {st['min_id']} to {st['max_id']}; shifts run {st['shifts']}")
        if last:
            print(f"Last shift: {last['blocks_done']} blocks in {last['seconds']}s, ended: {last['stop_reason']}")
        return 0
    res = shift(args.data_dir, args.from_id, args.to_id, minutes=args.minutes, workers=args.workers, pause=args.pause)
    print(f"Shift finished: {res['blocks_done']} blocks (ok {res['ok']}, empty {res['gap']}, errors {res['error']}) in {res['seconds']}s. "
          f"Reason: {res['stop_reason']}. Pushed: {res['pushed']}")
    benign = ("completed", "nothing left", "time budget", "possible end")
    return 0 if res["pushed"] and res["stop_reason"].startswith(benign) else 1


if __name__ == "__main__":
    sys.exit(main())
