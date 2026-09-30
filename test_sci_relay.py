"""Tests for sci_relay.py (fake court server, real temporary git repos, no network). Run: python test_sci_relay.py"""
import glob
import gzip
import json
import os
import shutil
import subprocess
import tempfile
import threading

try:
    import pymupdf as fitz
except ImportError:
    import fitz

import sci_relay

FAILURES = []
BS = 10  # small blocks keep the tests fast

for k, v in (("GIT_AUTHOR_NAME", "t"), ("GIT_AUTHOR_EMAIL", "t@t"), ("GIT_COMMITTER_NAME", "t"), ("GIT_COMMITTER_EMAIL", "t@t")):
    os.environ[k] = v


def check(condition, description):
    print(f"[{'PASS' if condition else 'FAIL'}] {description}")
    if not condition:
        FAILURES.append(description)


def real_pdf(text):
    doc = fitz.open()
    while True:
        page = doc.new_page()
        page.insert_text((72, 72), f"{text}. " + "lorem ipsum dolor " * 60)
        data = doc.tobytes()
        if len(data) > 1500:
            doc.close()
            return data


def served(text):
    pdf = real_pdf(text)
    body = len(pdf).to_bytes(4, "little") + pdf
    return (200, "application/pdf", body, str(len(body)))


EMPTY = (200, "text/html; charset=UTF-8", b"", "0")


def make_fetcher(behaviors=None, calls=None):
    behaviors = behaviors or {}
    lock = threading.Lock()
    calls = calls if calls is not None else []

    def fetch(id_):
        with lock:
            calls.append(id_)
        b = behaviors.get(id_)
        if callable(b):
            return b(id_)
        return b if b is not None else served(f"Judgment number {id_}")

    return fetch


def sh(*args, cwd=None):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True)


def make_repo(with_remote=True):
    base = tempfile.mkdtemp(prefix="relay_test_")
    work = os.path.join(base, "work")
    remote = os.path.join(base, "remote.git")
    if with_remote:
        sh("git", "init", "--bare", "-b", "main", remote)
        sh("git", "clone", remote, work)
    else:
        os.makedirs(work)
        sh("git", "init", "-b", "main", work)
    sh("git", "checkout", "-B", "main", cwd=work)
    with open(os.path.join(work, "README.md"), "w") as f:
        f.write("data repo\n")
    sh("git", "add", "-A", cwd=work)
    sh("git", "commit", "-m", "init", cwd=work)
    if with_remote:
        sh("git", "push", "-u", "origin", "main", cwd=work)
    return base, work, remote


def shards(work):
    return sorted(os.path.basename(p) for p in glob.glob(os.path.join(work, "shards", "*.jsonl.gz")))


def read_shard(work, name):
    with gzip.open(os.path.join(work, "shards", name), "rt", encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def remote_files(remote):
    return sh("git", "--git-dir", remote, "ls-tree", "-r", "--name-only", "main").stdout.split()


def quiet(*_a, **_k):
    return None


def no_sleep(_s):
    return None


# ------------------------------------------------------------ ledger helpers
check(sci_relay.block_start(37014, 250) == 37000 and sci_relay.block_start(0, 250) == 0, "block_start floors an ID to its block")
check(sci_relay.shard_name(37000, 250, 200, 40, 10) == "037000-037249.ok200.gap40.err10.jsonl.gz", "shard names carry range and counts")
check(sci_relay.parse_shard_name("037000-037249.ok200.gap40.err10.jsonl.gz") == (37000, 37249, 200, 40, 10), "shard names parse back")
check(sci_relay.parse_shard_name("README.md") is None, "non-shard files are ignored")
check(sci_relay.pending_blocks(set(), 25, 0, 10) == [20, 10, 0], "descending range gives newest block first")
check(sci_relay.pending_blocks({20}, 25, 0, 10) == [10, 0], "finished blocks are skipped")
check(sci_relay.pending_blocks(set(), 0, 25, 10) == [0, 10, 20], "ascending range gives oldest block first")

# ------------------------------------------------------------ a normal shift
base, work, remote = make_repo()
calls = []
res = sci_relay.shift(work, 29, 0, minutes=30, workers=1, pause=1.5, block_size=BS,
                      fetcher=make_fetcher({15: EMPTY, 3: EMPTY}, calls), sleep=no_sleep, out=quiet)
names = shards(work)
check(len(names) == 3, "three blocks give three shard files")
check(res["blocks_done"] == 3 and res["ok"] == 28 and res["gap"] == 2 and res["error"] == 0, "counts: 28 ok, 2 empty, 0 errors")
top = read_shard(work, [n for n in names if n.startswith("000020")][0])
check([r["id"] for r in top] == sorted(r["id"] for r in top), "records are sorted by ID")
r25 = [r for r in top if r["id"] == 25][0]
check(r25["status"] == "ok" and "Judgment number 25" in r25["text"] and r25["pages"] >= 1 and len(r25["sha256"]) == 64,
      "an ok record carries the extracted text, page count and fingerprint")
check(all(isinstance(r.get("ms"), int) and r["ms"] >= 0 for r in top), "every record carries how many milliseconds its request took")
mid = read_shard(work, [n for n in names if n.startswith("000010")][0])
r15 = [r for r in mid if r["id"] == 15][0]
check(r15["status"] == "gap" and "text" not in r15, "an empty ID is recorded as a gap with no text")
check(sh("git", "status", "--porcelain", cwd=work).stdout.strip() == "", "everything is committed (clean working tree)")
check(all(f"shards/{n}" in remote_files(remote) for n in names), "all shard files reached the remote")
logs = glob.glob(os.path.join(work, "state", "shifts", "*.json"))
check(len(logs) == 1 and json.load(open(logs[0]))["blocks_done"] == 3, "a shift log with the counts is written and committed")
check(any(f.startswith("state/shifts/") for f in remote_files(remote)), "the shift log reached the remote")

# resume: nothing left to do
calls2 = []
res2 = sci_relay.shift(work, 29, 0, minutes=30, workers=1, pause=1.5, block_size=BS, fetcher=make_fetcher({}, calls2), sleep=no_sleep, out=quiet)
check(calls2 == [] and res2["blocks_done"] == 0 and "nothing left" in res2["stop_reason"], "a second shift over a finished range fetches nothing")

# status
st = sci_relay.status_summary(work, 29, 0, block_size=BS)
check(st["blocks_done"] == 3 and st["ok"] == 28 and st["gap"] == 2 and st["blocks_pending"] == 0, "status counts blocks and documents from the file names alone")
check(st["min_id"] == 0 and st["max_id"] == 29 and st["shifts"] == 2, "status reports the ID span and number of shifts")

# a second runner (fresh clone) sees the ledger through git
other = os.path.join(base, "other")
sh("git", "clone", remote, other)
check(len(shards(other)) == 3, "a fresh clone sees the finished blocks, so any runner can continue")

# ------------------------------------------------------------ time budget
base2, work2, remote2 = make_repo()
calls3 = []
res3 = sci_relay.shift(work2, 29, 0, minutes=1, workers=1, pause=1.0, block_size=BS, est_block_seconds=600,
                       fetcher=make_fetcher({}, calls3), sleep=no_sleep, out=quiet)
check(calls3 == [] and "time" in res3["stop_reason"], "a block is not started when the remaining time is less than a block usually takes")

# ------------------------------------------------------------ a block stops midway: blocked
base3, work3, remote3 = make_repo()
blocked = (403, "text/html", b"Forbidden", None)
res4 = sci_relay.shift(work3, 29, 0, minutes=30, workers=1, pause=1.0, block_size=BS,
                       fetcher=make_fetcher({15: blocked}), sleep=no_sleep, out=quiet)
n4 = shards(work3)
check(len(n4) == 1 and n4[0].startswith("000020"), "blocks finished before the block are kept; the interrupted block writes NO shard")
check("blocked" in res4["stop_reason"], "the shift reports it was blocked")
check(any(f.endswith(n4[0]) for f in remote_files(remote3)), "finished work is still pushed after a block")

# ------------------------------------------------------------ persistent error inside a block
base4, work4, remote4 = make_repo()
def boom(_id):
    raise ConnectionError("down")
res5 = sci_relay.shift(work4, 9, 0, minutes=30, workers=1, pause=1.0, block_size=BS, retries=0,
                       fetcher=make_fetcher({4: boom}), sleep=no_sleep, out=quiet)
rec = read_shard(work4, shards(work4)[0])
check(res5["error"] == 1 and shards(work4)[0].endswith("ok9.gap0.err1.jsonl.gz"), "one failing ID is recorded as an error and the block still completes")
check([r for r in rec if r["id"] == 4][0]["status"] == "error", "the failing ID is marked error in the shard")

# ------------------------------------------------------------ unreadable PDF
base5, work5, remote5 = make_repo()
garbage = b"%PDF-1.4\n" + b"this is not a real pdf body " * 100 + b"\n%%EOF\n"
gbody = len(garbage).to_bytes(4, "little") + garbage
res6 = sci_relay.shift(work5, 9, 0, minutes=30, workers=1, pause=1.0, block_size=BS,
                       fetcher=make_fetcher({5: (200, "application/pdf", gbody, str(len(gbody)))}), sleep=no_sleep, out=quiet)
rec6 = read_shard(work5, shards(work5)[0])
r5 = [r for r in rec6 if r["id"] == 5][0]
check(r5["status"] == "error" and "extract" in r5["note"], "a PDF that downloads but cannot be read is recorded as an error, not silently lost")
check(len(r5.get("sha256", "")) == 64, "its fingerprint is still recorded")

# ------------------------------------------------------------ end of archive
base6, work6, remote6 = make_repo()
fetch_end = make_fetcher({i: EMPTY for i in range(30, 100)})
res7 = sci_relay.shift(work6, 0, 99, minutes=30, workers=1, pause=1.0, block_size=BS, empty_blocks_stop=3,
                       fetcher=fetch_end, sleep=no_sleep, out=quiet)
check("possible end of archive" in res7["stop_reason"], "three empty blocks in a row after real ones stop the shift as a possible end of the archive")
check(len(shards(work6)) == 6, "the real blocks and the empty blocks that proved the end are all recorded")

base7, work7, remote7 = make_repo()
res8 = sci_relay.shift(work7, 99, 0, minutes=30, workers=1, pause=1.0, block_size=BS, empty_blocks_stop=3,
                       fetcher=make_fetcher({i: EMPTY for i in range(60, 100)}), sleep=no_sleep, out=quiet)
check(res8["blocks_done"] == 10, "newest-first: empty blocks BEFORE any real block (above the end) do not stop the shift")

# ------------------------------------------------------------ stop file and repo checks
base8, work8, remote8 = make_repo()
open(os.path.join(work8, "STOP"), "w").close()
calls9 = []
res9 = sci_relay.shift(work8, 29, 0, minutes=30, workers=1, pause=1.0, block_size=BS, fetcher=make_fetcher({}, calls9), sleep=no_sleep, out=quiet)
check(calls9 == [] and "STOP" in res9["stop_reason"], "a STOP file in the data repo halts a shift before it fetches anything")

plain = tempfile.mkdtemp(prefix="relay_plain_")
try:
    sci_relay.shift(plain, 9, 0, minutes=1, block_size=BS, fetcher=make_fetcher({}), sleep=no_sleep, out=quiet)
    refused = False
except ValueError:
    refused = True
check(refused, "a folder that is not a git repository is refused")

# ------------------------------------------------------------ push failure keeps work committed
base9, work9, remote9 = make_repo(with_remote=False)
res10 = sci_relay.shift(work9, 9, 0, minutes=30, workers=1, pause=1.0, block_size=BS, fetcher=make_fetcher({}), sleep=no_sleep, out=quiet)
check("push failed" in res10["stop_reason"] and not res10["pushed"], "if pushing fails the shift says so plainly")
check(len(shards(work9)) == 1 and sh("git", "status", "--porcelain", cwd=work9).stdout.strip() == "", "the finished block is still committed locally")

for b in (base, base2, base3, base4, base5, base6, base7, base8, base9, plain):
    shutil.rmtree(b, ignore_errors=True)

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILED:")
    for f in FAILURES:
        print("  -", f)
    raise SystemExit(1)
print("ALL PASSED")
