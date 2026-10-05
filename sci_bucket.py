"""Time-boxed "shift" runner for the open Supreme Court bucket (s3://indian-supreme-court-judgments, CC-BY-4.0, Dattam Labs).

Downloads the PDFs named in the work list (coverage/bucket_match/worklist.csv.gz), extracts the text, and saves one shard file per block
of 250 judgments on the data branch `claude/sci-bucket`. The shard files ARE the ledger: a block is done exactly when its shard is
committed, so it is always safe to stop and safe to run again. PDFs are held in memory only; none is ever written to disk or committed.
The text is saved raw, as extracted, with an offset (`body_start`) where the court's own judgment seems to begin; `clean_text` below
turns a saved record into reading text without changing what was saved.

Source acknowledgement: the judgments come from the Supreme Court of India; the compilation and law-report formatting from the
Dattam Labs open dataset (CC-BY-4.0). Keep that attribution with anything reproduced.
"""
import argparse
import collections
import concurrent.futures as cf
import csv
import glob
import gzip
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone

import sci_relay

BLOCK_SIZE = 250
BRANCH = "claude/sci-bucket"
HOST = "https://indian-supreme-court-judgments.s3.ap-south-1.amazonaws.com/"
DEFAULT_WORKLIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "coverage", "bucket_match", "worklist.csv.gz")
_SHARD_RE = re.compile(r"^(after|none)-(\d{4})\.ok(\d+)\.miss(\d+)\.err(\d+)\.jsonl\.gz$")
META_FIELDS = ("scope", "decision_date", "path", "key", "title", "petitioner", "respondent", "citation", "case_id", "nc_display", "cnr",
               "judge", "disposal_nature", "available_languages", "tier")

_git = sci_relay._git
_sync = sci_relay._sync
_push = sci_relay._push
_commit = sci_relay._commit
_last_line = sci_relay._last_line


class Transient(Exception):
    """A network failure that survived the retries: the block is discarded and redone later."""


# ---------------------------------------------------------------- work list and ledger
def load_worklist(path, scope):
    """Rows of one scope in the file's order (the file is sorted by decision date then path, so block numbers are stable) and the file's sha256."""
    raw = open(path, "rb").read()
    text = gzip.decompress(raw).decode("utf-8") if raw[:2] == b"\x1f\x8b" else raw.decode("utf-8")
    rows = [r for r in csv.DictReader(text.splitlines()) if r["scope"] == scope]
    return rows, hashlib.sha256(raw).hexdigest()


def n_blocks(rows, block_size=BLOCK_SIZE):
    return (len(rows) + block_size - 1) // block_size


def shard_name(scope, n, ok, miss, err):
    return f"{scope}-{n:04d}.ok{ok}.miss{miss}.err{err}.jsonl.gz"


def _ledger(data_dir):
    found = {}
    for path in glob.glob(os.path.join(data_dir, "shards", "*.jsonl.gz")):
        m = _SHARD_RE.match(os.path.basename(path))
        if m:
            found[(m.group(1), int(m.group(2)))] = tuple(int(x) for x in m.groups()[2:])
    return found


# ---------------------------------------------------------------- one judgment
def default_fetcher(key, timeout=120):
    """Returns (http status, body). Raises on network trouble. S3 answers 403 or 404 for a file that is not there."""
    req = urllib.request.Request(HOST + urllib.parse.quote(key), headers={"User-Agent": "recourse-sci-bucket/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""


def fetch_pdf(key, fetcher, retries=3, backoff=(2.0, 5.0, 10.0), sleep=time.sleep):
    last = "no attempt"
    for attempt in range(retries + 1):
        try:
            status, body = fetcher(key)
        except Exception as e:
            last = f"{type(e).__name__}: {e}"[:150]
        else:
            if status == 200:
                return 200, body
            if status in (403, 404):
                return status, b""
            last = f"HTTP {status}"
        if attempt < retries:
            sleep(backoff[min(attempt, len(backoff) - 1)])
    raise Transient(f"{key}: {last}")


def extract_pdf(body):
    """(raw text with pages joined by form feeds, page count, producer, number of pages that carry an image)."""
    try:
        import pymupdf as fitz
    except ImportError:
        import fitz
    if body[:5] != b"%PDF-":
        raise ValueError("not a PDF")
    doc = fitz.open(stream=body, filetype="pdf")
    try:
        pages = [p.get_text() for p in doc]
        scan_pages = sum(1 for p in doc if p.get_images())
        producer = (doc.metadata or {}).get("producer") or ""
    finally:
        doc.close()
    if not pages:
        raise ValueError("no pages")
    return "\f".join(pages), len(pages), producer, scan_pages


_BODY_MARKERS = (
    re.compile(r"(?i)(?:the\s+)?(?:judg(?:e)?ment|order)\s+of\s+the\s+(?:court|supreme\s+court)\s+was\s+delivered\s+by"),
    re.compile(r"(?im)^[ \t]*Judgment\s*/\s*Order\s+of\s+the\s+Supreme\s+Court[ \t]*$"),
    re.compile(r"(?m)^[ \t]*(?:JUDGMENT|J\s?U\s?D\s?G\s?M\s?E\s?N\s?T|ORDER)[ \t]*$"),
)


def find_body_start(text):
    """Offset where the court's own judgment seems to begin (after the law report's headnote), or (None, None) if no marker is found.
    Law-report PDFs put the editors' headnote and HELD summary first; those are not the court's words."""
    best = None
    for i, rx in enumerate(_BODY_MARKERS):
        for m in rx.finditer(text):
            if i == 2 and m.start() < 300:
                continue
            if best is None or m.start() < best[0]:
                best = (m.start(), ("delivered_by", "judgment_order_heading", "judgment_heading")[i])
            break
    return best if best else (None, None)


def process(row, fetcher, retries=3, backoff=(2.0, 5.0, 10.0), sleep=time.sleep):
    rec = {k: row[k] for k in META_FIELDS if row.get(k) not in (None, "")}
    if not row.get("key"):
        rec.update(status="missing", note="no file under the standard name in the bucket listing")
        return rec
    status, body = fetch_pdf(row["key"], fetcher, retries, backoff, sleep)
    if status != 200:
        rec.update(status="missing", note=f"HTTP {status}")
        return rec
    rec.update(bytes=len(body), sha256=hashlib.sha256(body).hexdigest())
    if row.get("size") and int(float(row["size"])) != len(body):
        rec["size_listed"] = int(float(row["size"]))
    try:
        text, pages, producer, scan_pages = extract_pdf(body)
    except Exception as e:
        rec.update(status="error", note=f"text extraction failed: {type(e).__name__}: {e}"[:200])
        return rec
    start, marker = find_body_start(text)
    rec.update(status="ok", pages=pages, scan_pages=scan_pages, producer=producer, text_chars=len(text), text=text)
    if start is not None:
        rec.update(body_start=start, body_marker=marker)
    return rec


# ---------------------------------------------------------------- reading text from a saved record
_HEADERS = (re.compile(r"^[A-H]$"), re.compile(r"^\d{1,4}$"), re.compile(r"(?i)^SUPREME COURT REPORTS$"),
            re.compile(r"^\[\d{4}\]\s*\d+\s*S\.?C\.?R\.?(?:\s*\d+)?(?:\s*:\s*\d{4}\s+INSC\s+\d+)?$"))


def clean_text(rec):
    """Reading text from a saved record: cuts the law report's headnote (when body_start is known), drops lone margin letters A to H,
    lone numbers (page and footnote marks), the law report's running headers, and short case-title lines repeated three or more times.
    Does not repair hyphenation or footnote text. Never changes the saved record."""
    text = rec.get("text") or ""
    start = rec.get("body_start")
    if start:
        text = text[start:]
    lines = [ln.strip() for ln in text.replace("\f", "\n").split("\n")]
    counts = collections.Counter(ln for ln in lines if 8 < len(ln) < 130 and re.search(r"\sv(?:s)?\.?\s", ln))
    repeated = {ln for ln, c in counts.items() if c >= 3}
    kept = [ln for ln in lines if ln and ln not in repeated and not any(rx.match(ln) for rx in _HEADERS)]
    return "\n".join(kept)


# ---------------------------------------------------------------- the shift
def _write_shard(data_dir, scope, n, records):
    counts = {"ok": 0, "missing": 0, "error": 0}
    for r in records:
        counts[r["status"]] += 1
    name = shard_name(scope, n, counts["ok"], counts["missing"], counts["error"])
    os.makedirs(os.path.join(data_dir, "shards"), exist_ok=True)
    final = os.path.join(data_dir, "shards", name)
    tmp = os.path.join(data_dir, "shards", ".tmp-" + name)
    with gzip.open(tmp, "wt", encoding="utf-8", errors="replace") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    os.replace(tmp, final)
    return name, counts


def _guard_worklist(data_dir, sha):
    """The block numbers only mean something for one exact work list; the first shift pins its hash on the data branch."""
    path = os.path.join(data_dir, "state", "worklist.sha256")
    if os.path.exists(path):
        pinned = open(path, encoding="utf-8").read().strip()
        return (pinned == sha), pinned
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(sha + "\n")
    _commit(data_dir, [os.path.join("state", "worklist.sha256")], "pin the work list")
    return True, sha


def shift(data_dir, worklist, scope, minutes=50, workers=8, fetcher=None, sleep=time.sleep, clock=time.monotonic,
          block_size=BLOCK_SIZE, est_block_seconds=120, max_blocks=None, retries=3, backoff=(2.0, 5.0, 10.0), out=print):
    if _git(data_dir, "rev-parse", "--is-inside-work-tree").returncode != 0:
        raise ValueError(f"{data_dir} is not a git repository")
    fetcher = fetcher or default_fetcher
    started_iso, t0 = datetime.now(timezone.utc).isoformat(timespec="seconds"), clock()
    totals = {"blocks_done": 0, "ok": 0, "missing": 0, "error": 0}
    reason, unpushed, est = None, 0, est_block_seconds
    stop_file = os.path.join(data_dir, "STOP")
    rows, sha = load_worklist(worklist, scope)

    ok, msg = _sync(data_dir)
    if not ok:
        reason = f"could not update from the remote: {msg}"
    elif os.path.exists(stop_file):
        reason = "STOP file present in the data repo"
    else:
        same, pinned = _guard_worklist(data_dir, sha)
        if not same:
            reason = f"the work list changed since the first shift (pinned {pinned[:12]}, now {sha[:12]}); block numbers would mean different judgments"
    try:
        todo = [] if reason else [n for n in range(n_blocks(rows, block_size)) if (scope, n) not in _ledger(data_dir)]
        if not reason and not todo:
            reason = f"nothing left to do in scope {scope}"
        for n in todo:
            if reason:
                break
            if os.path.exists(stop_file):
                reason = "STOP file present in the data repo"
                break
            if max_blocks is not None and totals["blocks_done"] >= max_blocks:
                reason = f"time budget used up (stopped after the {max_blocks} blocks asked for)"
                break
            remaining = minutes * 60 - (clock() - t0)
            if remaining < est:
                reason = f"time budget used up ({remaining:.0f}s left, a block takes about {est:.0f}s)"
                break
            batch = rows[n * block_size:(n + 1) * block_size]
            b0 = clock()
            try:
                with cf.ThreadPoolExecutor(workers) as ex:
                    records = list(ex.map(lambda r: process(r, fetcher, retries, backoff, sleep), batch))
            except Transient as e:
                reason = f"stopped inside block {scope}-{n:04d}: {e} (that block is discarded and will be redone)"
                break
            name, counts = _write_shard(data_dir, scope, n, records)
            _commit(data_dir, [os.path.join("shards", name)], f"shard {name}")
            for k in ("ok", "missing", "error"):
                totals[k] += counts[k]
            totals["blocks_done"] += 1
            unpushed += 1
            secs = clock() - b0
            est = max(secs * 1.25, 30)
            out(f"block {scope}-{n:04d}: ok {counts['ok']} missing {counts['missing']} errors {counts['error']} ({secs:.0f}s)")
            pushed_ok, msg = _push(data_dir)
            if not pushed_ok:
                reason = f"push failed: {msg}"
                break
            unpushed = 0
        if reason is None:
            reason = f"completed all pending blocks in scope {scope}"
    except Exception as e:
        reason = f"internal error: {type(e).__name__}: {e}"[:300]

    seconds = round(clock() - t0, 1)
    log = dict(started_at=started_iso, ended_at=datetime.now(timezone.utc).isoformat(timespec="seconds"), scope=scope, minutes=minutes,
               workers=workers, stop_reason=reason, seconds=seconds, **totals)
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


# ---------------------------------------------------------------- branch, status, guard
def init_branch(code_repo, data_dir):
    """Attach the data branch as its own folder (never mixed with code). Creates it empty (an orphan branch) the first time."""
    _git(code_repo, "fetch", "origin")
    if _git(code_repo, "ls-remote", "--exit-code", "--heads", "origin", BRANCH).returncode == 0:
        p = _git(code_repo, "worktree", "add", "-B", BRANCH, data_dir, f"origin/{BRANCH}")
        if p.returncode != 0:
            raise RuntimeError(f"could not attach {BRANCH}: {_last_line(p)}")
        return f"attached existing {BRANCH}"
    for args, where in ((("worktree", "add", "--detach", data_dir), code_repo), (("checkout", "--orphan", BRANCH), data_dir),
                        (("rm", "-rf", "-q", "."), data_dir), (("commit", "--allow-empty", "-m", "start of the bucket branch"), data_dir),
                        (("push", "-u", "origin", BRANCH), data_dir)):
        p = _git(where, *args)
        if p.returncode != 0:
            raise RuntimeError(f"git {args[0]} failed: {_last_line(p)}")
    return f"created {BRANCH}"


def active_check(code_repo, now=None, max_age=1500, ref=f"origin/{BRANCH}"):
    p = _git(code_repo, "log", "-1", "--format=%ct%x09%s", ref)
    if p.returncode != 0 or not p.stdout.strip():
        return "IDLE (no bucket branch yet)"
    ts, _, subject = p.stdout.strip().partition("\t")
    age = (now if now is not None else time.time()) - int(ts)
    if subject.startswith("shard ") and age < max_age:
        return f"ACTIVE (last block committed {int(age)}s ago)"
    return f"IDLE (newest commit: '{subject}', {int(age)}s ago)"


def status_summary(data_dir, worklist, block_size=BLOCK_SIZE):
    ledger = _ledger(data_dir)
    out = {}
    for scope in ("after", "none"):
        rows, _ = load_worklist(worklist, scope)
        done = {k: v for k, v in ledger.items() if k[0] == scope}
        out[scope] = {"judgments": len(rows), "blocks": n_blocks(rows, block_size), "blocks_done": len(done),
                      "ok": sum(v[0] for v in done.values()), "missing": sum(v[1] for v in done.values()), "error": sum(v[2] for v in done.values())}
    logs = sorted(glob.glob(os.path.join(data_dir, "state", "shifts", "*.json")))
    last = json.load(open(logs[-1], encoding="utf-8")) if logs else None
    return {"scopes": out, "shifts": len(logs), "last_shift": last}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init", help="attach (or create, the first time) the data branch as a folder")
    s = sub.add_parser("shift", help="run one time-boxed shift")
    s.add_argument("--scope", choices=["after", "none"], required=True)
    s.add_argument("--minutes", type=float, default=50)
    s.add_argument("--workers", type=int, default=8)
    s.add_argument("--max-blocks", type=int, default=None)
    sub.add_parser("status", help="show progress")
    sub.add_parser("active-check", help="say ACTIVE if another session looks active")
    for name, p in sub.choices.items():
        p.add_argument("--data-dir", default="../recourse-sci-bucket-data")
        p.add_argument("--worklist", default=DEFAULT_WORKLIST)
    args = ap.parse_args(argv)
    here = os.path.dirname(os.path.abspath(__file__))
    if args.cmd == "init":
        print(init_branch(here, args.data_dir))
        return 0
    if args.cmd == "active-check":
        print(active_check(here))
        return 0
    if args.cmd == "status":
        st = status_summary(args.data_dir, args.worklist)
        for scope, v in st["scopes"].items():
            print(f"{scope}: {v['blocks_done']}/{v['blocks']} blocks done ({v['ok']} judgments saved, {v['missing']} missing, {v['error']} errors, of {v['judgments']})")
        print(f"shifts run {st['shifts']}")
        if st["last_shift"]:
            ls = st["last_shift"]
            print(f"Last shift: {ls['blocks_done']} blocks in {ls['seconds']}s, ended: {ls['stop_reason']}")
        return 0
    res = shift(args.data_dir, args.worklist, args.scope, minutes=args.minutes, workers=args.workers, max_blocks=args.max_blocks)
    print(f"Shift finished: {res['blocks_done']} blocks (ok {res['ok']}, missing {res['missing']}, errors {res['error']}) in {res['seconds']}s. "
          f"Reason: {res['stop_reason']}. Pushed: {res['pushed']}")
    benign = ("completed", "nothing left", "time budget")
    return 0 if res["pushed"] and res["stop_reason"].startswith(benign) else 1


if __name__ == "__main__":
    sys.exit(main())
