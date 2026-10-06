"""Tests for index_dedupe.py (fake Voyage service, real temporary git repos, no network, costs nothing). Run: python test_index_dedupe.py"""
import gzip
import json
import os
import random
import re
import shutil
import subprocess
import tempfile
from types import SimpleNamespace

import numpy as np

import index_dedupe as dd
import sci_index as si

FAILURES = []
BS = 10
for k, v in (("GIT_AUTHOR_NAME", "t"), ("GIT_AUTHOR_EMAIL", "t@t"), ("GIT_COMMITTER_NAME", "t"), ("GIT_COMMITTER_EMAIL", "t@t")):
    os.environ[k] = v


def check(condition, description):
    print(f"[{'PASS' if condition else 'FAIL'}] {description}")
    if not condition:
        FAILURES.append(description)


def git(cwd, *a):
    return subprocess.run(["git", "-C", cwd, *a], capture_output=True, text=True, encoding="utf-8", errors="replace")


def bow_vec(text, dim=64):
    v = np.zeros(dim)
    for w in re.findall(r"[a-z0-9]+", text.lower()):
        v[hash(w) % dim] += 1.0
    n = np.linalg.norm(v)
    return (v / n if n else v).tolist()


class FakeClient:
    def __init__(self):
        self.calls = 0

    def embed(self, texts, model=None, input_type=None):
        self.calls += 1
        return SimpleNamespace(embeddings=[bow_vec(t) for t in texts], total_tokens=sum(len(t) for t in texts) // 4 + 1)


WORDS = [f"w{i:03d}" for i in range(400)]


def body(seed, paras=14, words=45, mutate=0.0):
    """Numbered paragraphs of seeded random words with criminal-law cue words, so the judgment counts as criminal and has many distinct shingles."""
    rnd = random.Random(seed)
    out = []
    for i in range(1, paras + 1):
        w = [rnd.choice(WORDS) for _ in range(words)]
        if mutate:
            mr = random.Random(seed * 7 + i)
            w = [x if mr.random() > mutate else "zz" + x for x in w]
        out.append(f"\n{i}. The accused and the prosecution witnesses on the FIR {' '.join(w)} under Section 420 IPC.")
    return "".join(out)


def old_header(pet, resp, number, date="01/02/2000", extra=""):
    return f"http://JUDIS.NIC.IN SUPREME COURT OF INDIA Page 1 of 6 CASE NO.: Appeal (crl.) {number} {extra}PETITIONER: {pet} Vs. RESPONDENT: {resp} DATE OF JUDGMENT: {date} BENCH: A & B JUDGMENT: "


def write_pool_shard(pool, start, records):
    os.makedirs(os.path.join(pool, "shards"), exist_ok=True)
    ok = sum(1 for r in records if r["status"] == "ok")
    name = f"{start:06d}-{start + BS - 1:06d}.ok{ok}.gap0.err0.jsonl.gz"
    with gzip.open(os.path.join(pool, "shards", name), "wt", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")


def doc(id_, text):
    return {"id": id_, "status": "ok", "pages": 6, "text": text}


# ================================================================ 1. header rules
print("--- header rules")
a = "http://JUDIS.NIC.IN SUPREME COURT OF INDIA Page 1 of 6 CASE NO.: Appeal (crl.) 1029 of 2001 PETITIONER: SUNIL BAJAJ... APPELLANT Vs. RESPONDENT: STATE OF M.P. DATE OF JUDGMENT: 11/10/2001"
b = "http://JUDIS.NIC.IN SUPREME COURT OF INDIA Page 1 of 6 CASE NO.: Appeal (crl.) 1029 of 2001 Special Leave Petition (crl.) 4537 of 2000 PETITIONER: SUNIL BAJAJ Vs. RESPONDENT: STATE OF M.P. DATE OF JUDGMENT: 11/10/2001"
check(dd.party_sim(a, b) == 1.0, "the same parties with different punctuation match")
check(dd.case_numbers(b) == [("1029", "2001")], "an SLP number in the header is not taken for the case number")
check(not dd.numbers_conflict(a, b), "a header with an extra SLP number does not conflict with one without")
c = a.replace("1029 of 2001", "1030 of 2001")
check(dd.numbers_conflict(a, c), "two different appeal numbers conflict")
d = "IN THE SUPREME COURT OF INDIA CRIMINAL APPEAL NO. ______ OF 2008 @ S.L.P. (Crl.) NO.5473 of 2006 Indu Jain …Appellant Vs. State"
check(dd.case_numbers(d) == [] and not dd.numbers_conflict(d, "CRIMINAL APPEAL NO. 1683 OF 2008 Indu Jain …Appellant Vs. State"), "a header with a blank appeal number never conflicts")
check(dd.case_numbers("CRIMINAL APPEAL No. 2031 2012 [Arising out of SLP (CRL.) No. 9775 of 2012") == [("2031", "2012")], "an appeal number written without 'of' is still read")
check(not dd.numbers_conflict("CASE NO.: Appeal (crl.) 1174 of 1998 PETITIONER", "CASE NO.: Appeal (crl.) 1173-74 of 1998 PETITIONER") and not dd.numbers_conflict("Appeal (crl.) 1156-1157 of 2001", "Appeal (crl.) 1156-57 of 2001"), "a single number inside a range, and a range written two ways, are the same case")
check(dd.numbers_conflict("CRIMINAL APPEAL No. 2031 2012 (Crl.A. 3432 of 2011)", "CRIMINAL APPEAL No. 2093-2094 OF 2012 (Crl.A. 3432 of 2011)"), "a number both headers merely mention does not hide that the appeals themselves differ")
e1 = old_header("State of Zeta", "Anil", "21 of 2005"); e2 = old_header("State of Zeta", "Balram", "22 of 2005")
check(dd.party_sim(e1, e2) < dd.MIN_PARTY_SIM, "same petitioner but a different respondent is a different case")

# ================================================================ 2. plan(): keeper rules, force / never / merge
print("--- plan")
P = lambda a, b, la=1000, lb=1000, ov=0.95: {"a": a, "b": b, "a_in_b": ov, "b_in_a": ov, "len_a": la, "len_b": lb}
H = lambda pet, num: old_header(pet, "STATE OF ZETA", num)
heads = {1: H("RAMESH KUMAR", "5 of 2000"), 2: H("RAMESH KUMAR", "5 of 2000"), 3: H("RAMESH KUMAR", "5 of 2000"), 4: H("PRIYA SHARMA", "6 of 2000"), 5: H("PRIYA SHARMA", "7 of 2000"),
         6: H("LATTU MAHTO", "8 of 2000"), 7: "MAHTO LATU v. STATE (Criminal Appeal No. 8 of 2000) MAY 16, 2000", 8: H("OSMAN", "9 of 2000"), 9: H("OSMAN", "9 of 2000")}
lens = {1: 1000, 2: 1200, 3: 1000, 4: 1000, 5: 1000, 6: 1000, 7: 1000, 8: 1000, 9: 1000}
stats = {d: {"passages": 10, "numbered": 10} for d in lens}
stats[2]["numbered"] = 0                      # the longest copy has no paragraph numbers
sr = {"pairs": [P(1, 2, 1000, 1200), P(2, 3, 1200, 1000), P(4, 5), P(6, 7), P(8, 9)], "heads": heads, "lens": lens}
pl = dd.plan(sr, stats)
g = {x["keep"]: x for x in pl["groups"]}
check(1 in g and sorted(g[1]["members"]) == [1, 2, 3] and g[1]["remove"] == [2, 3], "three copies of one case form one group; a copy with paragraph numbers beats a longer one without, and lengths within 10% count as equal (1 kept)")
check(4 not in g and 5 not in g and any(r["pair"] == [4, 5] for r in pl["review"]), "same parties but different case numbers are left in place and listed for review")
check(6 not in g and any(r["pair"] == [6, 7] for r in pl["review"]), "a differently spelled party name is not decided by the rules")
check(8 in g and g[8]["remove"] == [9], "identical headers: the lower id is kept when nothing else separates the copies")
pl2 = dd.plan(sr, stats, force=[[6, 7]], keep=[3], never=[[8, 9]])
g2 = {x["keep"]: x for x in pl2["groups"]}
check(3 in g2 and g2[3]["remove"] == [1, 2], "a judgment on the keep list is the copy that survives")
check(any(x["keep"] == 6 for x in pl2["groups"]) and not any(8 in x["members"] for x in pl2["groups"]), "force joins a pair the rules cannot; never keeps a pair apart")
pl3 = dd.plan(sr, stats, merge=[{"keep": 5, "remove": [4], "reason": "body under the wrong header"}])
check({"keep": 5, "remove": [4]} == {k: v for k, v in next(x for x in pl3["groups"] if x["keep"] == 5).items() if k in ("keep", "remove")}, "an explicit merge decision is honoured")
try:
    dd.plan(sr, stats, keep=[1, 2])
    refused = False
except ValueError:
    refused = True
check(refused, "two judgments on the keep list that the plan would merge is refused, not silently resolved")
sr2 = {"pairs": [P(1, 2, 1000, 1500)], "heads": heads, "lens": lens}
check(not dd.plan(sr2, stats)["groups"], "texts whose lengths differ by more than 30% are not the same case")

# ================================================================ 3. a real index, scanned, planned, applied
print("--- real index in temporary git repos")
base = tempfile.mkdtemp(prefix="dedupe_")
remote, code, idx, pool = os.path.join(base, "remote.git"), os.path.join(base, "code"), os.path.join(base, "idx"), os.path.join(base, "pool")
subprocess.run(["git", "init", "--bare", "-b", "main", remote], capture_output=True)
subprocess.run(["git", "clone", remote, code], capture_output=True)
open(os.path.join(code, "README"), "w").write("code\n"); git(code, "add", "."); git(code, "commit", "-m", "code"); git(code, "push", "origin", "HEAD:main")
si.init_index_branch(code, idx)

B1, B3, B5, B7, B9 = body(1), body(3), body(5), body(7), body(9)
docs_a = [doc(0, old_header("RAMESH KUMAR", "STATE OF ZETA", "15 of 2000") + B1),
          doc(1, old_header("RAMESH KUMAR", "STATE OF ZETA", "15 of 2000", "02/03/2000", "Special Leave Petition (crl.) 99 of 1999 ") + body(1, mutate=0.01)),   # same case, header typo, a few OCR changes
          doc(2, old_header("State of Zeta", "Anil", "21 of 2005") + B3),
          doc(3, old_header("State of Zeta", "Balram", "22 of 2005") + B3),                                                                                   # same text, different case
          doc(4, old_header("PRIYA SHARMA", "STATE OF ZETA", "30 of 2001") + B5),
          doc(5, old_header("PRIYA SHARMA", "STATE OF ZETA", "31 of 2001") + B5),                                                                             # same parties, different appeal number
          doc(6, old_header("OSMAN", "STATE OF ZETA", "40 of 2002") + B7),
          doc(7, "http://JUDIS.NIC.IN SUPREME COURT OF INDIA Page 1 of 8 CASE NO.: Appeal (crl.) 4126-50 of 2000 PETITIONER: COMMISSIONER OF INCOME TAX, MUMBAI Vs. RESPONDENT: VERSUS DATE OF JUDGMENT: 17/10/2001 " + body(7, mutate=0.01)),   # wrong header
          doc(8, old_header("UNRELATED PERSON", "STATE OF ZETA", "50 of 2003") + B9)]
write_pool_shard(pool, 0, docs_a)
write_pool_shard(pool, 10, [doc(10, old_header("LATTU MAHTO", "STATE OF BIHAR", "60 of 2004") + body(11)),
                            doc(11, "MAHTO LATU v. STATE OF BIHAR (Criminal Appeal No. 923 of 2008) May 16, 2008 [A and B, JJ.] CRIMINAL APPELLATE JURISDICTION " + body(11, mutate=0.01))])   # other layout, other spelling
c = FakeClient()
r = si.shift(pool, idx, client=c, block_size=BS, sleep=lambda s: None, pause=0, out=lambda *_: None, minutes=50)
check(r["blocks_done"] == 2, "setup: two blocks indexed")
spent0, led0 = si.tokens_spent(idx), si.ledger(idx)
metas0, M0, _ = si._load_index(idx)
vec0 = {(m["doc"], m["i"]): M0[i].copy() for i, m in enumerate(metas0)}
head0 = git(idx, "rev-parse", "HEAD").stdout.strip()
n_pass = {d: sum(1 for m in metas0 if m["doc"] == d) for d in range(0, 12)}

sc = dd.scan(pool, idx, out=lambda *_: None)
pairs = {(p["a"], p["b"]) for p in sc["pairs"]}
check((0, 1) in pairs and (2, 3) in pairs and (4, 5) in pairs and (6, 7) in pairs, "scan finds every near-identical pair, including different cases with the same text")
check((10, 11) in pairs, "scan finds a copy in a different layout")
check(not any(8 in p for p in pairs), "scan does not pair an unrelated judgment")
pl = dd.plan(sc, dd.doc_stats(idx, {d for p in pairs for d in p}), force=[[10, 11]], merge=[{"keep": 6, "remove": [7], "reason": "body under the wrong header (income tax)"}])
removed = {d for g in pl["groups"] for d in g["remove"]}
check(removed == {1, 7, 11}, f"the plan removes the same-case copy, the mislabelled copy and the forced copy, nothing else (got {sorted(removed)})")
check({tuple(r["pair"]) for r in pl["review"]} >= {(2, 3), (4, 5)}, "different cases that share text, and same parties with different case numbers, are left in place and listed")

tot = dd.apply_plan(idx, pl, out=lambda *_: None)
rel = dd.write_record(idx, pl, tot, head0)
si._commit(idx, ["index", rel], "index fix: test")
led1 = si.ledger(idx)
metas1, M1, with1 = si._load_index(idx)
check(set(led1) == set(led0), "the same blocks are valid after the fix")
check(si.tokens_spent(idx) == spent0, "tokens spent on file are unchanged (the money was spent)")
check(tot["docs_removed"] == 3 and tot["passages_removed"] == n_pass[1] + n_pass[7] + n_pass[11], "totals equal the passages those judgments had")
check(not ({1, 7, 11} & with1) and {0, 2, 3, 4, 5, 6, 8, 10} <= with1, "removed judgments have no passages left; every other judgment keeps its own")
check(len(metas1) == len(metas0) - tot["passages_removed"] and M1.shape[0] == len(metas1), "passage rows and vector rows still line up one to one")
same = all(np.array_equal(M1[i], vec0[(m["doc"], m["i"])]) for i, m in enumerate(metas1))
check(same, "every surviving passage still has exactly the vector it had before")
for start, v in led1.items():
    if start in led0 and v["base"] != led0[start]["base"]:
        check(v["docs"] == led0[start]["docs"] and v["tokens"] == led0[start]["tokens"] and v["passages"] < led0[start]["passages"], f"block {start}: doc count and tokens unchanged in the file name, passage count down")
old_files = [f for f in os.listdir(os.path.join(idx, "index")) if f.endswith(".jsonl.gz") or f.endswith(".npy")]
check(all(si._IDX_RE.match(f.replace(".docs.jsonl.gz", ".meta.jsonl.gz").replace(".vec.npy", ".meta.jsonl.gz")) for f in old_files) and len(old_files) == 3 * len(led1), "no stale files from the old block names are left behind")
seen = si.load_seen(idx)
dochash = {}
for v in led1.values():
    for line in gzip.open(os.path.join(idx, "index", v["base"] + ".docs.jsonl.gz"), "rt", encoding="utf-8"):
        r = json.loads(line); dochash[r["doc"]] = r
check(all(dochash[d].get("skip") == "near_duplicate" and dochash[d].get("dup_of") in (0, 6, 10) and dochash[d]["passages"] == 0 and "of" not in dochash[d] for d in (1, 7, 11)), "removed judgments stay in the docs files, marked near_duplicate with the copy that was kept")
check(all(dochash[d]["hash"] in seen for d in (1, 7, 11)), "their content hashes are still 'seen', so a re-crawl of the same text is never embedded again")
check(dochash[1]["dup_of"] == 0 and dochash[7]["dup_of"] == 6 and dochash[11]["dup_of"] == 10, "each removed copy points at the right surviving copy")
rec = json.load(open(os.path.join(idx, rel)))
check(rec["previous_commit"] == head0 and rec["totals"]["docs_removed"] == 3 and len(rec["groups"]) == 3, "the fix record names the commit to return to and every decision")
check(git(idx, "status", "--porcelain").stdout.strip() == "", "everything is committed")
check(git(idx, "rev-parse", "HEAD").stdout.strip() != head0 and git(code, "ls-remote", "--heads", "origin", "claude/sci-index").stdout.split()[0] == head0, "the fix is a new commit and nothing was pushed")

sc2 = dd.scan(pool, idx, out=lambda *_: None)
ids2 = {d for p in sc2["pairs"] for d in (p["a"], p["b"])}
check(not ({1, 7, 11} & ids2), "a second scan no longer sees the removed copies")
pl2 = dd.plan(sc2, dd.doc_stats(idx, ids2))
check(not pl2["groups"], "a second plan has nothing left to remove (running it twice is safe)")
try:
    dd.apply_plan(idx, pl)
    refused = False
except ValueError:
    refused = True
check(refused, "applying the same plan again is refused rather than corrupting the index")
c2 = FakeClient()
r2 = si.shift(pool, idx, client=c2, block_size=BS, sleep=lambda s: None, pause=0, out=lambda *_: None, minutes=50)
check(r2["blocks_done"] == 0 and c2.calls == 0, "a shift after the fix finds nothing to do and spends nothing")
shutil.rmtree(base, ignore_errors=True)

# a block whose passages are all removed loses its vector file but stays valid
base = tempfile.mkdtemp(prefix="dedupe2_")
remote, code, idx, pool = os.path.join(base, "remote.git"), os.path.join(base, "code"), os.path.join(base, "idx"), os.path.join(base, "pool")
subprocess.run(["git", "init", "--bare", "-b", "main", remote], capture_output=True)
subprocess.run(["git", "clone", remote, code], capture_output=True)
open(os.path.join(code, "README"), "w").write("code\n"); git(code, "add", "."); git(code, "commit", "-m", "code"); git(code, "push", "origin", "HEAD:main")
si.init_index_branch(code, idx)
write_pool_shard(pool, 0, [doc(0, old_header("RAMESH KUMAR", "STATE OF ZETA", "15 of 2000") + body(1))])
write_pool_shard(pool, 10, [doc(10, old_header("RAMESH KUMAR", "STATE OF ZETA", "15 of 2000") + body(1, mutate=0.01))])
si.shift(pool, idx, client=FakeClient(), block_size=BS, sleep=lambda s: None, pause=0, out=lambda *_: None, minutes=50)
sc = dd.scan(pool, idx, out=lambda *_: None)
pl = dd.plan(sc, dd.doc_stats(idx, {0, 10}), keep=[0])
dd.apply_plan(idx, pl, out=lambda *_: None)
led = si.ledger(idx)
check(set(led) == {0, 10} and led[10]["passages"] == 0 and not any(f.startswith("000010") and f.endswith(".vec.npy") for f in os.listdir(os.path.join(idx, "index"))), "a block that loses all its passages stays valid and has no vector file")
shutil.rmtree(base, ignore_errors=True)

# ================================================================ 4. the command line: landmarks are protected, apply can push, and refuses when it should
print("--- command line")
lm_file = os.path.join(tempfile.mkdtemp(prefix="lm_"), "landmarks.json")
json.dump({"landmarks": [{"doc": 10, "name": "x"}]}, open(lm_file, "w"))
check(dd.landmark_ids(lm_file) == [10], "landmark ids are read from landmarks.json")
check(len(dd.landmark_ids()) == 6 and all(isinstance(x, int) for x in dd.landmark_ids()), "the repository's own landmarks.json gives the six verified cases")


def fresh_env(prefix):
    base = tempfile.mkdtemp(prefix=prefix)
    remote, code, idx, pool = os.path.join(base, "remote.git"), os.path.join(base, "code"), os.path.join(base, "idx"), os.path.join(base, "pool")
    subprocess.run(["git", "init", "--bare", "-b", "main", remote], capture_output=True)
    subprocess.run(["git", "clone", remote, code], capture_output=True)
    open(os.path.join(code, "README"), "w").write("code\n"); git(code, "add", "."); git(code, "commit", "-m", "code"); git(code, "push", "origin", "HEAD:main")
    si.init_index_branch(code, idx)
    write_pool_shard(pool, 0, [doc(0, old_header("RAMESH KUMAR", "STATE OF ZETA", "15 of 2000") + body(1))])
    write_pool_shard(pool, 10, [doc(10, old_header("RAMESH KUMAR", "STATE OF ZETA", "15 of 2000") + body(1, mutate=0.01))])
    si.shift(pool, idx, client=FakeClient(), block_size=BS, sleep=lambda s: None, pause=0, out=lambda *_: None, minutes=50)
    return base, remote, code, idx, pool


base, remote, code, idx, pool = fresh_env("dedupe3_")
scan_json, plan_json = os.path.join(base, "scan.json"), os.path.join(base, "plan.json")
led0, head0 = si.ledger(idx), git(idx, "rev-parse", "HEAD").stdout.strip()
dd.main(["scan", "--pool-dir", pool, "--index-dir", idx, "--out", scan_json])
dd.main(["plan", "--index-dir", idx, "--scan", scan_json, "--out", plan_json])
pl_plain = json.load(open(plan_json))
check(pl_plain["groups"][0]["keep"] == 0 and pl_plain["groups"][0]["remove"] == [10], "without --keep-landmarks the lower id is the surviving copy")
dd.main(["plan", "--index-dir", idx, "--scan", scan_json, "--out", plan_json, "--keep-landmarks", "--landmarks", lm_file])
pl_lm = json.load(open(plan_json))
check(pl_lm["groups"][0]["keep"] == 10 and pl_lm["groups"][0]["remove"] == [0], "--keep-landmarks makes the landmark the surviving copy")

with open(os.path.join(idx, "scratch.txt"), "w") as fh:
    fh.write("uncommitted")
try:
    dd.main(["apply", "--index-dir", idx, "--plan", plan_json, "--commit"])
    refused = False
except SystemExit as e:
    refused = "uncommitted" in str(e)
check(refused and si.ledger(idx) == led0 and git(idx, "rev-parse", "HEAD").stdout.strip() == head0, "apply --commit refuses when the index folder has uncommitted changes, and changes nothing")
os.remove(os.path.join(idx, "scratch.txt"))
with open(os.path.join(idx, "STOP"), "w") as fh:
    fh.write("")
try:
    dd.main(["apply", "--index-dir", idx, "--plan", plan_json])
    refused = False
except SystemExit as e:
    refused = "STOP" in str(e)
check(refused and si.ledger(idx) == led0, "apply refuses while a STOP file is present, even without --commit")
os.remove(os.path.join(idx, "STOP"))

dd.main(["apply", "--index-dir", idx, "--plan", plan_json, "--push"])
local, remote_head = git(idx, "rev-parse", "HEAD").stdout.strip(), git(code, "ls-remote", "--heads", "origin", "claude/sci-index").stdout.split()[0]
check(local != head0 and local == remote_head, "apply --push commits and pushes: the remote branch now holds the fix commit")
check(git(idx, "log", "-1", "--format=%s").stdout.strip() == "index fix: remove 1 duplicate judgments (%d passages)" % json.load(open(os.path.join(idx, "state", "fixes", os.listdir(os.path.join(idx, "state", "fixes"))[0])))["totals"]["passages_removed"]
      and git(idx, "status", "--porcelain").stdout.strip() == "", "the commit message names the count and nothing is left uncommitted")
metas_after = si._load_index(idx)[0]
check({m["doc"] for m in metas_after} == {10}, "the landmark copy is the one that kept its passages")
shutil.rmtree(base, ignore_errors=True)

# apply --commit without --push leaves the remote alone
base, remote, code, idx, pool = fresh_env("dedupe4_")
scan_json, plan_json = os.path.join(base, "scan.json"), os.path.join(base, "plan.json")
head0 = git(idx, "rev-parse", "HEAD").stdout.strip()
dd.main(["scan", "--pool-dir", pool, "--index-dir", idx, "--out", scan_json])
dd.main(["plan", "--index-dir", idx, "--scan", scan_json, "--out", plan_json])
dd.main(["apply", "--index-dir", idx, "--plan", plan_json, "--commit"])
check(git(idx, "rev-parse", "HEAD").stdout.strip() != head0 and git(code, "ls-remote", "--heads", "origin", "claude/sci-index").stdout.split()[0] == head0, "apply --commit alone commits locally and does not push")
shutil.rmtree(base, ignore_errors=True)

# the plan can be saved on the index branch for review, and a saved plan can be applied later
base, remote, code, idx, pool = fresh_env("dedupe5_")
scan_json, plan_json = os.path.join(base, "scan.json"), os.path.join(base, "plan.json")
led0, head0 = si.ledger(idx), git(idx, "rev-parse", "HEAD").stdout.strip()
dd.main(["scan", "--pool-dir", pool, "--index-dir", idx, "--out", scan_json])
dd.main(["plan", "--index-dir", idx, "--scan", scan_json, "--out", plan_json, "--save-to-index"])
saved = os.path.join(idx, "state", "fixes", "plans")
local, remote_head = git(idx, "rev-parse", "HEAD").stdout.strip(), git(code, "ls-remote", "--heads", "origin", "claude/sci-index").stdout.split()[0]
check(len(os.listdir(saved)) == 1 and local != head0 and local == remote_head and git(idx, "log", "-1", "--format=%s").stdout.startswith("dedupe plan (not applied)"),
      "plan --save-to-index commits and pushes the plan file and nothing else")
check(si.ledger(idx) == led0 and {m["doc"] for m in si._load_index(idx)[0]} == {0, 10}, "saving a plan changes no index data")
saved_plan = os.path.join(saved, os.listdir(saved)[0])
check(json.load(open(saved_plan)) == json.load(open(plan_json)), "the saved plan is the plan that was made")
dd.main(["apply", "--index-dir", idx, "--plan", saved_plan, "--push"])
check({m["doc"] for m in si._load_index(idx)[0]} == {0} and git(idx, "rev-parse", "HEAD").stdout.strip() == git(code, "ls-remote", "--heads", "origin", "claude/sci-index").stdout.split()[0], "a plan saved on the index branch can be applied from there")
with open(os.path.join(idx, "scratch.txt"), "w") as fh:
    fh.write("uncommitted")
try:
    dd.main(["plan", "--index-dir", idx, "--scan", scan_json, "--out", plan_json, "--save-to-index"])
    refused = False
except SystemExit as e:
    refused = "uncommitted" in str(e)
check(refused, "plan --save-to-index refuses when the index folder has uncommitted changes")
shutil.rmtree(base, ignore_errors=True)

# ================================================================ 4. a judgment in the crawl and the same one in the bucket (law-report layout)
print("--- crawl and bucket")
import csv as _csv
base = tempfile.mkdtemp(prefix="dedupe_bkt_")
remote, code, idx, pool = os.path.join(base, "remote.git"), os.path.join(base, "code"), os.path.join(base, "idx"), os.path.join(base, "pool")
bk = os.path.join(base, "bucket")
subprocess.run(["git", "init", "--bare", "-b", "main", remote], capture_output=True)
subprocess.run(["git", "clone", remote, code], capture_output=True)
open(os.path.join(code, "README"), "w").write("code\n"); git(code, "add", "."); git(code, "commit", "-m", "code"); git(code, "push", "origin", "HEAD:main")
si.init_index_branch(code, idx)
def alpha_body(seed, paras=14, words=45):
    """Like body(), but the random words are letters only, so no passage is dropped as noise (digits in the words lower the share of letters)."""
    rnd = random.Random(seed)
    return "".join(f"\n{i}. The accused and the prosecution witnesses on the FIR {' '.join(''.join(rnd.choice('abcdefghijklmnopqrstuvwxyz') for _ in range(7)) for _ in range(words))} under Section 420 IPC." for i in range(1, paras + 1))


BODY = alpha_body(21)
write_pool_shard(pool, 0, [doc(0, old_header("RAMESH KUMAR", "STATE OF ZETA", "15 of 2000") + BODY), doc(1, old_header("OTHER PERSON", "STATE OF ZETA", "16 of 2000") + alpha_body(22))])
head = "A \n.B \n[2000] 1 S.C.R. 1 \nRAMESH KUMAR \nv. \nSTATE OF ZETA \n(Criminal Appeal No. 15 of 2000) \nThe accused and the prosecution - FIR - offence.\n\f"
brec = {"scope": "after", "path": "2000_1_1_9", "title": "RAMESH KUMAR versus STATE OF ZETA", "decision_date": "05-05-2000", "citation": "[2000] 1 S.C.R. 1", "case_id": "2000 INSC 1",
        "status": "ok", "pages": 4, "text": head + "R.F. NARIMAN, J. " + BODY, "body_start": len(head)}
os.makedirs(os.path.join(bk, "shards"))
with gzip.open(os.path.join(bk, "shards", "after-0000.ok1.miss0.err0.jsonl.gz"), "wt", encoding="utf-8") as fh:
    fh.write(json.dumps(brec) + "\n")
si.shift(pool, idx, client=FakeClient(), block_size=BS, sleep=lambda s: None, pause=0, out=lambda *_: None, minutes=50, bucket_dir=bk, skip_paths=frozenset())
bid = si.BUCKET_BASE + si.bucket_ordinal("after", 0) * si.BLOCK_SIZE
check(any(m["doc"] == bid for m in si._load_index(idx)[0]) and any(m["doc"] == 0 for m in si._load_index(idx)[0]), "setup: the crawl judgment and its bucket copy are both in the index")
lines = []
sc_no = dd.scan(pool, idx, out=lines.append)
check(not any(bid in (p["a"], p["b"]) for p in sc_no["pairs"]) and any("NOT compared" in l for l in lines), "a scan without --bucket-dir leaves the bucket's judgments out and says how many")
sc_b = dd.scan(pool, idx, out=lambda *_: None, bucket_dir=bk, skip_paths=frozenset())
check({(p["a"], p["b"]) for p in sc_b["pairs"]} == {(0, bid)}, "with the bucket attached, the copy in the law-report layout is paired with the crawl's text, and the other judgment is not")
check("RAMESH KUMAR" in sc_b["heads"][bid] and "Criminal Appeal No. 15" in sc_b["heads"][bid], "the bucket judgment's header for the rules is the report's own opening lines (parties and appeal number)")
pl_b = dd.plan(sc_b, dd.doc_stats(idx, {0, bid}))
check(len(pl_b["groups"]) == 1 and sorted(pl_b["groups"][0]["members"]) == [0, bid] and not pl_b["review"], "the rules call it the same case (same parties, no conflicting case number)")
shutil.rmtree(base, ignore_errors=True)

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILED:")
    for f in FAILURES:
        print("  -", f)
    raise SystemExit(1)
print("ALL PASSED")
