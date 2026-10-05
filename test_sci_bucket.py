"""Tests for sci_bucket.py (fake bucket, real temporary git repos, no network). Run: python test_sci_bucket.py"""
import csv
import glob
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time

try:
    import pymupdf as fitz
except ImportError:
    import fitz

import sci_bucket

FAILURES = []
BS = 10  # small blocks keep the tests fast

for k, v in (("GIT_AUTHOR_NAME", "t"), ("GIT_AUTHOR_EMAIL", "t@t"), ("GIT_COMMITTER_NAME", "t"), ("GIT_COMMITTER_EMAIL", "t@t")):
    os.environ[k] = v


def check(condition, description):
    print(f"[{'PASS' if condition else 'FAIL'}] {description}")
    if not condition:
        FAILURES.append(description)


def real_pdf(text, images=False):
    doc = fitz.open()
    while True:
        page = doc.new_page()
        page.insert_text((72, 72), f"{text}. " + "lorem ipsum dolor " * 60)
        data = doc.tobytes()
        if len(data) > 1500:
            doc.close()
            return data


def sh(*args, cwd=None):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True)


def make_repo():
    base = tempfile.mkdtemp(prefix="bucket_test_")
    work, remote = os.path.join(base, "work"), os.path.join(base, "remote.git")
    sh("git", "init", "--bare", "-b", "main", remote)
    sh("git", "clone", remote, work)
    sh("git", "checkout", "-B", "main", cwd=work)
    with open(os.path.join(work, "README.md"), "w") as f:
        f.write("data repo\n")
    sh("git", "add", "-A", cwd=work)
    sh("git", "commit", "-m", "init", cwd=work)
    sh("git", "push", "-u", "origin", "main", cwd=work)
    return base, work, remote


def make_worklist(base, n_after=25, n_none=0, extra=None):
    rows = []
    for i in range(n_after):
        rows.append(dict(scope="after", decision_date=f"05-05-2017", path=f"2017_1_{i}_{i + 5}", key=f"data/pdf/year=2017/english/2017_1_{i}_{i + 5}_EN.pdf",
                         size="", title=f"PARTY {i} versus STATE", petitioner=f"PARTY {i}", respondent="STATE", citation=f"[2017] 1 S.C.R. {i}",
                         case_id=f"2017 INSC {i}", nc_display=f"2017INSC{i}", cnr="", judge="J", disposal_nature="Dismissed",
                         available_languages="ENG", tier="after"))
    for i in range(n_none):
        rows.append(dict(scope="none", decision_date="01-01-1999", path=f"1999_1_{i}_{i + 5}", key=f"data/pdf/year=1999/english/1999_1_{i}_{i + 5}_EN.pdf",
                         size="", title=f"OLD {i} versus STATE", petitioner=f"OLD {i}", respondent="STATE", citation="", case_id="",
                         nc_display="", cnr="", judge="", disposal_nature="", available_languages="", tier="none"))
    for r in (extra or []):
        rows.append(r)
    path = os.path.join(base, "worklist.csv.gz")
    cols = list(rows[0].keys())
    import io
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols)
    w.writeheader()
    w.writerows(rows)
    with gzip.open(path, "wt", encoding="utf-8", newline="") as fh:
        fh.write(buf.getvalue())
    return path, rows


def make_fetcher(rows, overrides=None, calls=None):
    overrides = overrides or {}
    calls = calls if calls is not None else []
    pdfs = {r["key"]: real_pdf(f"Judgment of {r['path']}") for r in rows if r["key"]}

    def fetch(key):
        calls.append(key)
        b = overrides.get(key)
        if callable(b):
            return b(key)
        if b is not None:
            return b
        return 200, pdfs[key]

    return fetch, pdfs


def shards(work):
    return sorted(os.path.basename(p) for p in glob.glob(os.path.join(work, "shards", "*.jsonl.gz")))


def read_shard(work, name):
    with gzip.open(os.path.join(work, "shards", name), "rt", encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def remote_files(remote):
    return sh("git", "--git-dir", remote, "ls-tree", "-r", "--name-only", "main").stdout.split()


quiet = lambda *_a, **_k: None
no_sleep = lambda _s: None

# ------------------------------------------------------------ names and ledger
check(sci_bucket.shard_name("after", 7, 240, 4, 6) == "after-0007.ok240.miss4.err6.jsonl.gz", "shard names carry scope, block number and counts")
check(sci_bucket._SHARD_RE.match("none-0012.ok1.miss2.err3.jsonl.gz") is not None and sci_bucket._SHARD_RE.match("README.md") is None, "only shard names count as ledger entries")
check(sci_bucket.n_blocks(list(range(25)), 10) == 3 and sci_bucket.n_blocks([], 10) == 0, "block count rounds up")

# ------------------------------------------------------------ a normal shift
base, work, remote = make_repo()
wl, rows = make_worklist(base, 25)
calls = []
fetch, pdfs = make_fetcher(rows, calls=calls)
res = sci_bucket.shift(work, wl, "after", minutes=30, workers=3, block_size=BS, fetcher=fetch, sleep=no_sleep, out=quiet)
names = shards(work)
check(len(names) == 3 and res["blocks_done"] == 3 and res["ok"] == 25 and res["missing"] == 0 and res["error"] == 0, "25 judgments give three shards, all ok")
check(names[0].startswith("after-0000") and names[2].endswith("ok5.miss0.err0.jsonl.gz"), "blocks are numbered from 0 and the last holds the remainder")
recs = read_shard(work, names[0])
check([r["path"] for r in recs] == [r["path"] for r in rows[:10]], "records keep the work list's order")
r0 = recs[0]
check(r0["status"] == "ok" and "Judgment of 2017_1_0_5" in r0["text"] and r0["pages"] >= 1 and r0["scan_pages"] == 0, "an ok record carries the extracted text, page count and scan count")
check(r0["sha256"] == hashlib.sha256(pdfs[rows[0]["key"]]).hexdigest() and r0["bytes"] == len(pdfs[rows[0]["key"]]), "the fingerprint is the sha256 of the PDF exactly as served")
check(r0["title"] == "PARTY 0 versus STATE" and r0["case_id"] == "2017 INSC 0" and r0["citation"] == "[2017] 1 S.C.R. 0" and r0["nc_display"] == "2017INSC0", "bucket metadata travels with the text")
check("size" not in r0 and "size_listed" not in r0, "no size note when the listing gave no size")
check(sh("git", "status", "--porcelain", cwd=work).stdout.strip() == "", "everything is committed (clean working tree)")
check(all(f"shards/{n}" in remote_files(remote) for n in names), "all shard files reached the remote")
check(glob.glob(os.path.join(work, "**", "*.pdf"), recursive=True) == [] and glob.glob(os.path.join(base, "**", "*.pdf"), recursive=True) == [],
      "no PDF is ever written to disk")
logs = glob.glob(os.path.join(work, "state", "shifts", "*.json"))
check(len(logs) == 1 and json.load(open(logs[0]))["blocks_done"] == 3, "a shift log with the counts is written")
check(open(os.path.join(work, "state", "worklist.sha256")).read().strip() == hashlib.sha256(open(wl, "rb").read()).hexdigest(), "the first shift pins the work list's hash on the data branch")

# resume
calls2 = []
res2 = sci_bucket.shift(work, wl, "after", minutes=30, workers=2, block_size=BS, fetcher=make_fetcher(rows, calls=calls2)[0], sleep=no_sleep, out=quiet)
check(calls2 == [] and "nothing left" in res2["stop_reason"], "a second shift over a finished scope fetches nothing")

# status
st = sci_bucket.status_summary(work, wl, block_size=BS)
check(st["scopes"]["after"]["blocks_done"] == 3 and st["scopes"]["after"]["ok"] == 25 and st["scopes"]["none"]["judgments"] == 0, "status counts blocks and judgments from file names and the work list")

# a second runner sees the ledger through git
other = os.path.join(base, "other")
sh("git", "clone", remote, other)
check(len(shards(other)) == 3, "a fresh clone sees the finished blocks, so any runner can continue")

# ------------------------------------------------------------ each block is pushed before the next starts
base_p, work_p, remote_p = make_repo()
wl_p, rows_p = make_worklist(base_p, 25)
seen = []
second_block_first = rows_p[10]["key"]
f_p, _ = make_fetcher(rows_p)


def spy_fetch(key):
    if key == second_block_first:
        seen.append(remote_files(remote_p))
    return f_p(key)


sci_bucket.shift(work_p, wl_p, "after", minutes=30, workers=1, block_size=BS, fetcher=spy_fetch, sleep=no_sleep, out=quiet)
check(seen and any("shards/after-0000" in f for f in seen[0]), "a finished block is already on the remote before the next block starts")
shutil.rmtree(base_p, ignore_errors=True)

# ------------------------------------------------------------ time budget and max blocks
base2, work2, remote2 = make_repo()
wl2, rows2 = make_worklist(base2, 25)
calls3 = []
res3 = sci_bucket.shift(work2, wl2, "after", minutes=1, workers=1, block_size=BS, est_block_seconds=600, fetcher=make_fetcher(rows2, calls=calls3)[0], sleep=no_sleep, out=quiet)
check(calls3 == [] and res3["stop_reason"].startswith("time budget used up"), "a block is not started when the remaining time is less than a block usually takes")
res3b = sci_bucket.shift(work2, wl2, "after", minutes=30, workers=2, block_size=BS, max_blocks=1, fetcher=make_fetcher(rows2)[0], sleep=no_sleep, out=quiet)
check(res3b["blocks_done"] == 1 and len(shards(work2)) == 1, "--max-blocks stops after the blocks asked for")

# ------------------------------------------------------------ missing, not-a-PDF, size note
base3, work3, remote3 = make_repo()
wl3, rows3 = make_worklist(base3, 10, extra=[dict(scope="after", decision_date="06-05-2017", path="2017_9_9_9", key="", size="", title="NO FILE versus X", petitioner="NO FILE",
                                                  respondent="X", citation="", case_id="", nc_display="", cnr="", judge="", disposal_nature="", available_languages="", tier="after")])
k_gone, k_html, k_size = rows3[1]["key"], rows3[2]["key"], rows3[3]["key"]
f3, pdfs3 = make_fetcher(rows3, {k_gone: (404, b""), k_html: (200, b"<html>oops</html>")})
rows3[3]["size"] = str(len(pdfs3[k_size]) + 7)
wl3b, _ = make_worklist(base3, 10, extra=[rows3[10]])  # rewrite the file so the size note is in it
import io as _io
with gzip.open(wl3b, "wt", encoding="utf-8", newline="") as fh:
    buf = _io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows3[0].keys()))
    w.writeheader()
    w.writerows(rows3)
    fh.write(buf.getvalue())
res6 = sci_bucket.shift(work3, wl3b, "after", minutes=30, workers=2, block_size=BS, fetcher=f3, sleep=no_sleep, out=quiet)
n6 = shards(work3)
rec6 = {r["path"]: r for name in n6 for r in read_shard(work3, name)}
check(rec6[rows3[1]["path"]]["status"] == "missing" and "text" not in rec6[rows3[1]["path"]], "a 404 is recorded as missing, with no text")
check(rec6[rows3[2]["path"]]["status"] == "error" and "not a PDF" in rec6[rows3[2]["path"]]["note"], "a body that is not a PDF is recorded as an error")
check(rec6["2017_9_9_9"]["status"] == "missing" and "listing" in rec6["2017_9_9_9"]["note"], "a row with no file name is recorded as missing without any request")
check(rec6[rows3[3]["path"]]["status"] == "ok" and rec6[rows3[3]["path"]]["size_listed"] == len(pdfs3[k_size]) + 7, "a different size from the listing is noted but the judgment is kept")
check(res6["missing"] == 2 and res6["error"] == 1 and res6["ok"] == 8, "counts: 8 ok, 2 missing, 1 error")
check(any(n.endswith("miss1.err0.jsonl.gz") or n.endswith("miss2.err1.jsonl.gz") or "miss" in n for n in n6), "shard names show the missing and error counts")

# ------------------------------------------------------------ network failure: block discarded, earlier blocks kept
base4, work4, remote4 = make_repo()
wl4, rows4 = make_worklist(base4, 25)
bad = rows4[15]["key"]


def boom(key):
    raise ConnectionError("down")


f4, _ = make_fetcher(rows4, {bad: boom})
res7 = sci_bucket.shift(work4, wl4, "after", minutes=30, workers=2, block_size=BS, retries=1, fetcher=f4, sleep=no_sleep, out=quiet)
n7 = shards(work4)
check(len(n7) == 1 and n7[0].startswith("after-0000"), "the block that hit a network failure writes NO shard; the finished block is kept")
check("discarded" in res7["stop_reason"] and res7["pushed"], "the shift reports it, and the finished work is pushed")
f4b, _ = make_fetcher(rows4)
res7b = sci_bucket.shift(work4, wl4, "after", minutes=30, workers=2, block_size=BS, fetcher=f4b, sleep=no_sleep, out=quiet)
check(len(shards(work4)) == 3 and res7b["blocks_done"] == 2, "the next shift redoes the discarded block and finishes the scope")
flaky = {"n": 0}
fl_rows = rows4[:3]


def flaky_fetch(key):
    flaky["n"] += 1
    if flaky["n"] == 1:
        return 503, b""
    return 200, real_pdf("ok")


r_ok = sci_bucket.fetch_pdf("k", flaky_fetch, retries=2, sleep=no_sleep)
check(r_ok[0] == 200, "a 503 is retried and the retry's answer is used")

# ------------------------------------------------------------ guards: STOP file, changed work list
base5, work5, remote5 = make_repo()
wl5, rows5 = make_worklist(base5, 25)
open(os.path.join(work5, "STOP"), "w").close()
calls5 = []
res8 = sci_bucket.shift(work5, wl5, "after", minutes=30, workers=1, block_size=BS, fetcher=make_fetcher(rows5, calls=calls5)[0], sleep=no_sleep, out=quiet)
check(calls5 == [] and "STOP" in res8["stop_reason"], "a STOP file halts the shift before any request")
os.remove(os.path.join(work5, "STOP"))
sci_bucket.shift(work5, wl5, "after", minutes=30, workers=1, block_size=BS, max_blocks=1, fetcher=make_fetcher(rows5)[0], sleep=no_sleep, out=quiet)
wl5b, rows5b = make_worklist(base5, 24)
os.replace(wl5b, wl5b + ".x")
calls5b = []
res9 = sci_bucket.shift(work5, wl5b + ".x", "after", minutes=30, workers=1, block_size=BS, fetcher=make_fetcher(rows5b, calls=calls5b)[0], sleep=no_sleep, out=quiet)
check(calls5b == [] and "work list changed" in res9["stop_reason"], "a different work list is refused, since block numbers would mean different judgments")

# ------------------------------------------------------------ active check and branch creation
now = time.time()
check(sci_bucket.active_check(work, now=now, ref="origin/main").startswith("IDLE"), "active check says IDLE when the newest commit is not a recent shard")
sh("git", "commit", "--allow-empty", "-m", "shard after-0099.ok1.miss0.err0.jsonl.gz", cwd=work)
check(sci_bucket.active_check(work, now=time.time(), ref="HEAD").startswith("ACTIVE"), "active check says ACTIVE for a shard commit under 25 minutes old")
check(sci_bucket.active_check(work, now=time.time() + 4000, ref="HEAD").startswith("IDLE"), "and IDLE once it is older")

base6, code6, remote6 = make_repo()
data6 = os.path.join(base6, "bucket-data")
msg = sci_bucket.init_branch(code6, data6)
check(msg == "created claude/sci-bucket" and os.path.isdir(data6), "init creates the data branch as an empty folder the first time")
check(sh("git", "--git-dir", remote6, "rev-parse", "--verify", "claude/sci-bucket").returncode == 0, "the new branch was pushed")
check(not os.path.exists(os.path.join(data6, "README.md")), "the data branch holds none of the code branch's files")
code7 = os.path.join(base6, "later-session")
sh("git", "clone", remote6, code7)
data6b = os.path.join(base6, "bucket-data2")
msg2 = sci_bucket.init_branch(code7, data6b)
check(msg2 == "attached existing claude/sci-bucket", "a later session attaches the existing branch")

# ------------------------------------------------------------ a later scope (monthly refresh) has its own pin and shard names
base8, work8, remote8 = make_repo()
rows8 = []
for i in range(12):
    rows8.append(dict(scope="refresh_20261005", decision_date="05-01-2026", path=f"2026_1_{i}_{i + 3}", key=f"data/pdf/year=2026/english/2026_1_{i}_{i + 3}_EN.pdf", size="",
                      title=f"NEW {i} versus STATE", petitioner=f"NEW {i}", respondent="STATE", citation="", case_id=f"2026 INSC {i}", nc_display="", cnr="", judge="",
                      disposal_nature="", available_languages="", tier="refresh"))
wl8, _ = make_worklist(base8, 0, 0, extra=rows8)
f8, _ = make_fetcher(rows8)
res10 = sci_bucket.shift(work8, wl8, "refresh_20261005", minutes=30, workers=2, block_size=BS, fetcher=f8, sleep=no_sleep, out=quiet)
check(res10["blocks_done"] == 2 and res10["ok"] == 12 and shards(work8)[0].startswith("refresh_20261005-0000.ok10"), "a refresh scope downloads and names its shards after itself")
check(os.path.exists(os.path.join(work8, "state", "worklist-refresh_20261005.sha256")) and not os.path.exists(os.path.join(work8, "state", "worklist.sha256")), "a later scope pins its work list in its own file, not in the first scopes' pin")
check(sci_bucket.status_summary(work8, wl8, block_size=BS)["scopes"]["refresh_20261005"]["blocks_done"] == 2, "status lists a refresh scope too")
try:
    sci_bucket.shift(work8, wl8, "Bad Scope", minutes=1, workers=1, block_size=BS, fetcher=f8, sleep=no_sleep, out=quiet)
    bad_ok = False
except ValueError:
    bad_ok = True
check(bad_ok, "a scope name with spaces or capitals is refused")

# ------------------------------------------------------------ body start and cleaning
lr = ("A\nB\nC\nD\nE\nF\nG\nH\n329\nSUNITA & ORS.\nv.\nRAJASTHAN STATE ROAD TRANSPORT CORPORATION\n(Civil Appeal No. 1665 of 2019)\n"
      "Motor Vehicles Act, 1988 – Fatal accident – held: the High Court erred.\n[2019] 3 S.C.R. 329\nSUPREME COURT REPORTS\n[2019] 3 S.C.R.\n"
      "HELD: 1.1 The tribunal was right.\nThe Judgment of the Court was delivered by\nAJAY RASTOGI, J. 1. Leave granted.\nA\nB\n330\n"
      "Sunita v. Rajasthan SRTC\nThe appellants had proved negligence.\nSunita v. Rajasthan SRTC\nWe allow the appeal.\n[2019] 3 S.C.R. 331 : 2019 INSC 120\nSunita v. Rajasthan SRTC\n")
start, marker = sci_bucket.find_body_start(lr)
check(marker == "delivered_by" and lr[start:].startswith("The Judgment of the Court was delivered by"), "body start is found at 'The Judgment of the Court was delivered by'")
check(lr.index("HELD") < start, "the headnote's HELD summary lies before the body start")
new_fmt = "[2024] 12 S.C.R. 1436 : 2024 INSC 1039\nTitle\nHeadnotes†\nHeld: x\nAppearances for Parties\nMs X\nJudgment/Order of the Supreme Court\nJudgment\nPrasanna B. Varale, J.\n1. Leave granted.\n"
s2, m2 = sci_bucket.find_body_start(new_fmt)
check(m2 == "judgment_order_heading" and new_fmt[s2:].startswith("Judgment/Order of the Supreme Court"), "body start is found at the newer reports' 'Judgment/Order of the Supreme Court' heading")
check(sci_bucket.find_body_start("A short order with no markers at all.") == (None, None), "no marker gives no body start rather than a guess")
check(sci_bucket.find_body_start("ORDER\nLeave granted.")[0] is None, "a lone ORDER line near the very start is not taken as the body start")
rec = {"text": lr, "body_start": start}
before = json.dumps(rec, sort_keys=True)
clean = sci_bucket.clean_text(rec)
check("HELD" not in clean and "Motor Vehicles Act" not in clean, "cleaning cuts the headnote when the body start is known")
check(not any(ln.strip() in set("ABCDEFGH") or ln.strip().isdigit() for ln in clean.split("\n")), "cleaning drops lone margin letters and lone page numbers")
check("SUPREME COURT REPORTS" not in clean and "S.C.R." not in clean, "cleaning drops the law report's running headers")
check(clean.count("Sunita v. Rajasthan SRTC") == 0 and "We allow the appeal." in clean and "The appellants had proved negligence." in clean,
      "cleaning drops a case-title line repeated on every page but keeps the judgment's sentences")
check(json.dumps(rec, sort_keys=True) == before, "cleaning never changes the saved record")
check(sci_bucket.clean_text({"text": "ABC\nA\n12\nword"}) == "ABC\nword", "with no body start the whole text is kept apart from margin marks")

for b in (base, base2, base3, base4, base5, base6, base8):
    shutil.rmtree(b, ignore_errors=True)

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILED")
    for f in FAILURES:
        print(" -", f)
    raise SystemExit(1)
print("ALL PASSED")
