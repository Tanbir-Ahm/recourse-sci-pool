"""Tests for sci_index.py (fake Voyage service, real temporary git repos, no network, costs nothing). Run: python test_sci_index.py"""
import glob
import gzip
import json
import os
import re
import shutil
import subprocess
import tempfile
from types import SimpleNamespace

import numpy as np

import sci_index as si

FAILURES = []
BS = 10  # small blocks keep the tests fast

for k, v in (("GIT_AUTHOR_NAME", "t"), ("GIT_AUTHOR_EMAIL", "t@t"), ("GIT_COMMITTER_NAME", "t"), ("GIT_COMMITTER_EMAIL", "t@t")):
    os.environ[k] = v


def check(condition, description):
    print(f"[{'PASS' if condition else 'FAIL'}] {description}")
    if not condition:
        FAILURES.append(description)


# ---------------------------------------------------------------- fake service
class RateLimitError(Exception):
    pass


class AuthenticationError(Exception):
    pass


def bow_vec(text, dim=64):
    v = np.zeros(dim)
    for w in re.findall(r"[a-z0-9]+", text.lower()):
        v[hash(w) % dim] += 1.0
    n = np.linalg.norm(v)
    return (v / n if n else v).tolist()


class FakeClient:
    """fail_after=N: the (N+1)th embed call raises exc. plan={call_no: exception}."""

    def __init__(self, plan=None, fail_after=None, exc=None):
        self.calls, self.plan, self.fail_after, self.exc = 0, plan or {}, fail_after, exc
        self.texts, self.tokens = [], 0

    def embed(self, texts, model=None, input_type=None):
        self.calls += 1
        if self.plan.get(self.calls):
            raise self.plan[self.calls]
        if self.fail_after is not None and self.calls > self.fail_after:
            raise self.exc
        self.texts.append(list(texts))
        tok = sum(len(t) for t in texts) // 4 + 1
        self.tokens += tok
        return SimpleNamespace(embeddings=[bow_vec(t) for t in texts], total_tokens=tok)

    def rerank(self, query, documents, model=None, top_k=None):
        q = set(re.findall(r"[a-z0-9]+", query.lower()))
        sc = [(i, len(q & set(re.findall(r"[a-z0-9]+", d.lower()))) / (len(q) + 1)) for i, d in enumerate(documents)]
        sc.sort(key=lambda x: -x[1])
        return SimpleNamespace(results=[SimpleNamespace(index=i, relevance_score=s) for i, s in sc[:top_k]], total_tokens=10)


# ---------------------------------------------------------------- synthetic judgments
JUNK = "\nhttp://JUDIS.NIC.IN \nSUPREME COURT OF INDIA\nPage 2 of 9 \n"


def crim_text(tag, n=8):
    head = "IN THE SUPREME COURT OF INDIA\nCRIMINAL APPELLATE JURISDICTION\nCRIMINAL APPEAL NO. 7 OF 2012\nA. Appellant Versus State Respondent\nJUDGMENT\n"
    base = f"The accused {tag} was prosecuted for the offence under Section 420 IPC and the prosecution case is that the complainant lodged an FIR about cheating number %d and the trial court convicted him after hearing the evidence of witnesses on record."
    paras = []
    for i in range(1, n + 1):
        body = base % i
        if i == 1:
            body = "The FIR was registered against the accused " + tag + " on a complaint of cheating and the prosecution case is that the money was taken by deceit from the complainant over several months in the year 2008."
        if i == 3:
            body = "Learned counsel for the appellant submitted that the conviction is bad in law because no dishonest intention was proved against the accused " + tag + " at the time of the promise made to the complainant."
        if i == 5:
            body = "The court observed \\023no dishonest intention at inception\\024 and the accused " + tag + " was in no way connected with the offence charged against him by the prosecution witnesses."
        if i == 6:
            body = "We are of the view that the ingredients of the offence of cheating are not made out against the accused " + tag + " because the prosecution failed to prove any deception at the very inception."
        if i == n:
            body = "In the result, the appeal is allowed and the conviction of the accused " + tag + " is set aside and he is acquitted of the charge. No order as to costs."
        paras.append(f"\n{i}. {body}")
        if i == 4:
            paras.append(JUNK + "\f")
    return head + "".join(paras)


def civil_text(tag, n=8):
    head = "IN THE SUPREME COURT OF INDIA\nCIVIL APPELLATE JURISDICTION\nCIVIL APPEAL NO. 9 OF 2011\nJUDGMENT\n"
    paras = [f"\n{i}. The assessee {tag} challenged the assessment of sales tax on the turnover for the year and the tribunal held that the rate of tax on the goods is as notified in the schedule number {i} of the statute for the year in question under appeal." for i in range(1, n + 1)]
    return head + "".join(paras)


def prose_text(tag):
    s = [f"The appellant {tag} was found with the stolen goods by the police and the accused was arrested on the spot in the market. " * 1,
         "The prosecution examined many witnesses and the trial court convicted the accused of the offence of theft under the penal code. ",
         "Learned counsel for the appellant submitted that the identification of the accused was doubtful and the recovery was not proved. ",
         "We are of the view that the recovery is reliable and the conviction of the accused needs no interference by this Court at all. ",
         "In the result, the appeal is dismissed. "]
    return "CASE NO.: Appeal (crl.) 12 of 2000 PETITIONER: " + tag + " RESPONDENT: State DATE OF JUDGMENT: 01/01/2000 BENCH: X J. JUDGMENT: The Judgment of the Court was delivered by Y, J. " + " ".join(s * 6)


# ================================================================ A. cleaning / splitting / tagging
print("--- cleaning, splitting, tagging")
cp = si.clean_page("hello\nhttp://JUDIS.NIC.IN \nSUPREME COURT OF INDIA\nPage 12 of 14 \nworld Page 12 JUDGMENT more\n")
check("JUDIS" not in cp and "Page 12" not in cp and "SUPREME COURT OF INDIA" not in cp and "hello" in cp and "world" in cp and "more" in cp, "running page headers are removed but real words stay")
check(si.fix_text("\\023quoted\\024 and \\026 dash") == '"quoted" and - dash', "old-PDF escape codes become real quote marks and dashes")
meta, rest = si.split_old_header("CASE NO.: Appeal (crl.) 12 of 2000 PETITIONER: Ram Singh RESPONDENT: State of U.P. DATE OF JUDGMENT: 04/05/2000 BENCH: A & B JUDGMENT: The Judgment of the Court was delivered by K.T. THOMAS, J. The facts are simple.")
check(meta and meta["pet"] == "Ram Singh" and meta["resp"] == "State of U.P." and meta["date"] == "04/05/2000" and rest.startswith("The facts"), "an old-style header block is lifted out as case data, not left as a passage")

ps, m = si.make_passages(crim_text("Raju"))
check(len(ps) >= 8 and all(p["method"] == "para" for p in ps), "a numbered judgment is split on its real paragraph numbers")
check([p["pn"] for p in ps if p["pn"] != "preamble"][:3] == ["1", "2", "3"], "paragraph numbers are kept so a result can point to the exact paragraph")
alltext = " ".join(p["text"] for p in ps)
check("JUDIS" not in alltext and "Page 2 of 9" not in alltext, "header junk never reaches a passage")
check("\\023" not in alltext and '"no dishonest intention at inception"' in alltext, "escape codes are fixed inside passages")
check(max(p["page"] for p in ps) >= 1, "every passage knows its page")
sec = {p["pn"]: p["section"] for p in ps}
check(sec["3"] == "argument", "a paragraph reporting what a lawyer submitted is tagged argument")
check(sec["6"] == "reasoning", "'we are of the view' marks the court's own reasoning")
check(sec[str(8)] == "order", "the closing 'appeal is allowed' paragraph is tagged order")
check(sec["1"] == "facts", "an early 'FIR was registered' paragraph is tagged facts")

pp, pm = si.make_passages(prose_text("Mohan"))
check(pm and pm["pet"] == "Mohan" and all(p["method"] == "sentences" and p["pn"] is None for p in pp), "unnumbered prose is cut by sentences, with the page as its location")
check(all(len(p["text"]) <= 2700 for p in pp) and all(p["text"].rstrip()[-1] in ".?!;\"'" for p in pp), "sentence windows are bounded and do not stop mid-sentence")
check("PETITIONER" not in " ".join(p["text"] for p in pp), "the old header block is not embedded as text")

stat = [{"pn": "9", "page": 1, "method": "para", "text": "Section 415 reads as under: Whoever, by deceiving any person, fraudulently or dishonestly induces the person so deceived to deliver any property shall be punished with imprisonment which may extend to three years or with fine."}]
check(si.tag_doc(stat)[0]["section"] == "statute_text", "a paragraph that merely prints a statute is tagged statute_text")
quoted = [{"pn": "9", "page": 1, "method": "para", "text": "In State of Haryana v. Bhajan Lal AIR 1992 SC 604 and Ram v. State (2005) 3 SCC 260 this Court held that the power must be used sparingly and only in the rarest of cases by the courts."}]
check(si.tag_doc(quoted)[0]["prec"] == 1, "a paragraph quoting earlier cases is flagged as quoted precedent")
junk = [{"pn": "9", "page": 1, "method": "para", "text": "1234 5678 9012 3456 7890 1234 5678 9012 3456 7890 1234 5678 9012 3456 7890 1234"}, {"pn": "10", "page": 1, "method": "para", "text": "Leave granted."}]
tg = si.tag_doc(junk)
check(tg[0]["noise"] == 1 and tg[1]["noise"] == 1, "number-only and very short fragments are flagged as noise (never embedded)")
hdr = [{"pn": "preamble", "page": 1, "method": "para", "text": "IN THE SUPREME COURT OF INDIA CRIMINAL APPELLATE JURISDICTION CRIMINAL APPEAL NO. 5 OF 2010 A versus State of X with a few more words of the caption here"}]
check(si.tag_doc(hdr)[0]["section"] == "header", "a leftover caption block is tagged header")

# ================================================================ B. criminal-law filter
print("--- criminal-law filter")
check(si.is_criminal(crim_text("A"))[0], "a judgment with a criminal header is kept")
check(not si.is_criminal(civil_text("B"))[0], "a tax/civil judgment is left out")
nohdr = "S.B. Sinha, J. Appellant was prosecuted for an offence under the NDPS Act. The accused was convicted; the prosecution examined the complainant and the FIR was lodged; bail was refused and the conviction was upheld. " * 12
check(si.is_criminal(nohdr)[0], "a criminal judgment with no header is still caught by its wording")
check(si.is_criminal("Page 1 IN THE SUPREME COURT OF INDIA CRIMINAL APPELLATE JURISDICTION " + "x " * 10)[0], "the header test alone is enough")

# ================================================================ C. prepare_block
print("--- block preparation")
recs = [
    {"id": 20, "status": "ok", "pages": 3, "text": crim_text("One")},
    {"id": 21, "status": "ok", "pages": 3, "text": civil_text("Two")},
    {"id": 22, "status": "ok", "pages": 3, "text": crim_text("One")},   # identical copy of 20
    {"id": 23, "status": "gap"},
    {"id": 24, "status": "ok", "pages": 1, "text": "tiny order"},
    {"id": 25, "status": "ok", "pages": 3, "text": prose_text("Three")},
]
seen = {}
blk = si.prepare_block(recs, seen)
why = {d["doc"]: d.get("skip") for d in blk["docs"]}
check(why[20] is None and why[25] is None, "criminal judgments are kept")
check(why[21] == "not_criminal", "a civil judgment is recorded as skipped (not embedded)")
check(why[22] == "duplicate", "an identical copy is skipped, so it is never paid for twice")
check(why[24] == "short", "a tiny order is skipped")
check(23 not in why, "an empty ID is ignored")
check(blk["stats"]["passages"] == len(blk["passages"]) and blk["stats"]["est_tokens"] > 0, "the block reports how many passages and about how many tokens it will cost")
check(all(not p.get("noise") for p in blk["passages"]) and all(p["h"] for p in blk["passages"]), "only non-noise passages are queued, each with a content hash")
blk2 = si.prepare_block([{"id": 5, "status": "ok", "pages": 3, "text": crim_text("One")}], seen)
check(blk2["docs"][0]["skip"] == "duplicate" and blk2["docs"][0]["of"] == 20, "a copy found in a later block is still recognised as a duplicate")

# ================================================================ D. batching
print("--- batching")
texts = ["x" * 2000] * 1000
bs = si.batch_texts(texts, max_tokens=100000, max_items=500)
flat = [i for b in bs for i in b]
check(flat == list(range(1000)), "every passage is sent exactly once, in order")
check(all(len(b) <= 500 for b in bs) and all(sum(len(texts[i]) for i in b) / 3.87 <= 100000 for b in bs), "no batch exceeds the item cap or the token cap")

# ================================================================ E. embedding behaviours
print("--- embedding behaviours")
sleeps = []
slp = lambda s: sleeps.append(s)
c = FakeClient()
vec, used = si.embed_texts(c, ["alpha beta", "gamma delta", "alpha gamma"], sleep=slp, pause=2.0)
check(vec.shape == (3, 64) and vec.dtype == np.float16 and used == c.tokens, "vectors come back in order, as small numbers, with the real token count")
check(2.0 in sleeps, "it pauses between batches")

sleeps.clear()
c = FakeClient(plan={1: ConnectionError("blip")})
vec, used = si.embed_texts(c, ["alpha beta"], sleep=slp, pause=0)
check(vec.shape[0] == 1 and c.calls == 2 and 10 in sleeps, "a network blip is retried after a wait")
sleeps.clear()
c = FakeClient(plan={1: RateLimitError("slow down")})
vec, used = si.embed_texts(c, ["alpha beta"], sleep=slp, pause=0)
check(vec.shape[0] == 1 and 65 in sleeps, "a rate limit waits 65 seconds then continues")

c = FakeClient(plan={1: AuthenticationError("bad key")})
try:
    si.embed_texts(c, ["alpha"], sleep=slp, pause=0)
    check(False, "a refused key stops")
except si.EmbedStop as e:
    check("refused" in e.reason and c.calls == 1, "a refused key/request stops at once without retrying")
c = FakeClient(plan={1: RateLimitError("You have exceeded your free token allowance; add a payment method")})
try:
    si.embed_texts(c, ["alpha"], sleep=slp, pause=0)
    check(False, "allowance used up stops")
except si.EmbedStop as e:
    check(c.calls == 1 and "allowance" in e.reason.lower(), "an 'allowance used up / add payment' message stops at once instead of waiting")
c = FakeClient(fail_after=0, exc=ConnectionError("down"))
try:
    si.embed_texts(c, ["alpha"], sleep=slp, pause=0)
    check(False, "repeated failure stops")
except si.EmbedStop as e:
    check(c.calls == 5 and "5 failed attempts" in e.reason, "five failures in a row stop it (never loops forever)")

c = FakeClient()
try:
    si.embed_texts(c, ["word " * 400] * 4, sleep=slp, pause=0, budget_tokens=10)
    check(False, "ceiling stops")
except si.EmbedStop as e:
    check("ceiling" in e.reason and c.calls == 0 and e.used == 0, "a batch that would pass the ceiling is never sent")
c = FakeClient(fail_after=1, exc=AuthenticationError("denied"))
try:
    si.embed_texts(c, ["w" * 3000] * 200, sleep=slp, pause=0, max_items=100)
    check(False, "mid-way stop")
except si.EmbedStop as e:
    check(e.used > 0, "tokens already spent before a stop are reported (they count against the allowance)")

# ================================================================ F. ledger integrity
print("--- ledger")
d = tempfile.mkdtemp(prefix="idxL_")
os.makedirs(os.path.join(d, "index"))
base = si.write_block_files(d, 20, BS, docs=[{"doc": 20, "hash": "h"}], passages=[{"doc": 20, "i": 0, "text": "t", "h": "a"}] * 3, vectors=np.zeros((3, 4), dtype=np.float16), tokens=123)
check(os.path.exists(os.path.join(d, "index", base + ".vec.npy")), "a finished block writes three files")
check(si.ledger(d).get(20, {}).get("tokens") == 123 and si.ledger(d)[20]["passages"] == 3, "the ledger reads docs/passages/tokens from the file name")
os.remove(os.path.join(d, "index", base + ".vec.npy"))
check(20 not in si.ledger(d), "a block whose number file is missing does not count as done")
np.save(os.path.join(d, "index", base + ".vec.npy"), np.zeros((2, 4), dtype=np.float16))
check(20 not in si.ledger(d), "a block whose number file has the wrong row count does not count as done")
shutil.rmtree(d, ignore_errors=True)

# ================================================================ G. whole shift, with real git
print("--- whole shift (real temporary git repos)")


def git(cwd, *a):
    return subprocess.run(["git", "-C", cwd, *a], capture_output=True, text=True, encoding="utf-8", errors="replace")


def write_pool_shard(pool, start, records):
    os.makedirs(os.path.join(pool, "shards"), exist_ok=True)
    ok = sum(1 for r in records if r["status"] == "ok")
    gap = sum(1 for r in records if r["status"] == "gap")
    name = f"{start:06d}-{start + BS - 1:06d}.ok{ok}.gap{gap}.err0.jsonl.gz"
    with gzip.open(os.path.join(pool, "shards", name), "wt", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")


def new_env(prefix):
    base = tempfile.mkdtemp(prefix=prefix)
    remote = os.path.join(base, "remote.git")
    subprocess.run(["git", "init", "--bare", "-b", "main", remote], capture_output=True)
    code = os.path.join(base, "code")
    subprocess.run(["git", "clone", remote, code], capture_output=True)
    with open(os.path.join(code, "README"), "w") as fh:
        fh.write("code\n")
    git(code, "add", "."); git(code, "commit", "-m", "code"); git(code, "push", "origin", "HEAD:main")
    idx = os.path.join(base, "idx")
    pool = os.path.join(base, "pool")
    return base, remote, code, idx, pool


def run_shift(code, idx, pool, client, **kw):
    kw.setdefault("minutes", 50)
    return si.shift(pool, idx, client=client, block_size=BS, sleep=lambda s: None, pause=0, out=lambda *_: None, **kw)


base, remote, code, idx, pool = new_env("idxA_")
msg = si.init_index_branch(code, idx)
check(os.path.isdir(idx) and not os.path.exists(os.path.join(idx, "README")), "the index branch starts empty (no code files mixed in)")
check(git(code, "ls-remote", "--heads", "origin", "claude/sci-index").stdout.strip() != "", "the new index branch exists on the remote")
write_pool_shard(pool, 20, [{"id": 20, "status": "ok", "pages": 3, "text": crim_text("One")}, {"id": 21, "status": "ok", "pages": 3, "text": civil_text("TaxMarker")},
                            {"id": 22, "status": "ok", "pages": 3, "text": crim_text("One")}, {"id": 25, "status": "ok", "pages": 3, "text": prose_text("Three")}])
write_pool_shard(pool, 10, [{"id": 12, "status": "ok", "pages": 3, "text": crim_text("Four")}, {"id": 13, "status": "gap"}])
write_pool_shard(pool, 0, [{"id": 3, "status": "gap"}])
c = FakeClient()
r = run_shift(code, idx, pool, c)
check(r["blocks_done"] == 2 and r["stop_reason"].startswith("completed"), "the two blocks with real judgments are processed; the all-empty block is left alone (it is not counted, committed or sent)")
log = git(idx, "log", "--format=%s").stdout.splitlines()
check([l for l in log if l.startswith("index block")] == ["index block 000010-000019", "index block 000020-000029"], "blocks are done newest-first, one commit each")
sent = " ".join(t for batch in c.texts for t in batch)
check("TaxMarker" not in sent, "the civil judgment was never sent to the service")
check(sent.count("accused One") > 0 and sum(1 for b in c.texts for t in b if "accused One was prosecuted" in t) == 3, "the duplicate judgment was embedded only once")
check(git(code, "ls-remote", "--heads", "origin", "claude/sci-index").stdout.split()[0] == git(idx, "rev-parse", "HEAD").stdout.strip(), "everything is pushed")
led = si.ledger(idx)
check(sum(v["passages"] for v in led.values()) == sum(len(b) for b in c.texts), "saved passages equal passages sent (nothing lost, nothing paid for twice)")
check(si.tokens_spent(idx) == c.tokens, "the token total on file equals what the service charged")
c2 = FakeClient()
r2 = run_shift(code, idx, pool, c2)
check(r2["blocks_done"] == 0 and c2.calls == 0 and r2["stop_reason"].startswith("nothing left"), "running again does nothing and spends nothing (resume)")
write_pool_shard(pool, 30, [{"id": 31, "status": "ok", "pages": 3, "text": crim_text("Five")}])
c3 = FakeClient()
r3 = run_shift(code, idx, pool, c3)
check(r3["blocks_done"] == 1 and c3.calls >= 1, "a block the crawl adds later is picked up on the next run")
st = si.status_summary(pool, idx, ceiling=1_000_000)
check(st["blocks_done"] == 3 and st["blocks_pending"] == 0 and st["tokens_spent"] == si.tokens_spent(idx) and st["ceiling_left"] == 1_000_000 - st["tokens_spent"], "status reports blocks, tokens and what is left under the ceiling")
open(os.path.join(idx, "STOP"), "w").close()
write_pool_shard(pool, 40, [{"id": 41, "status": "ok", "pages": 3, "text": crim_text("Six")}])
c4 = FakeClient()
r4 = run_shift(code, idx, pool, c4)
check("STOP" in r4["stop_reason"] and c4.calls == 0, "a STOP file halts it before anything is sent")
os.remove(os.path.join(idx, "STOP"))
write_pool_shard(pool, 50, [{"id": 51, "status": "ok", "pages": 3, "text": crim_text("Seven")}])
r4b = run_shift(code, idx, pool, FakeClient(), max_blocks=1)
check(r4b["blocks_done"] == 1 and "max-blocks" in r4b["stop_reason"], "--max-blocks lets us run exactly one block as a trial")
shutil.rmtree(base, ignore_errors=True)

# the trial must reach a REAL block even when the newest blocks are empty
base, remote, code, idx, pool = new_env("idxT_")
si.init_index_branch(code, idx)
write_pool_shard(pool, 60, [{"id": 61, "status": "gap"}])
write_pool_shard(pool, 50, [{"id": 51, "status": "gap"}])
write_pool_shard(pool, 40, [{"id": 41, "status": "ok", "pages": 3, "text": crim_text("Real")}])
ct = FakeClient()
rt = run_shift(code, idx, pool, ct, max_blocks=1)
check(rt["blocks_done"] == 1 and rt["docs_embedded"] == 1 and ct.calls >= 1, "a one-block trial skips empty blocks and embeds the first block that has real judgments")
check(si.status_summary(pool, idx)["blocks_pending"] == 0, "empty blocks are not reported as pending work")
shutil.rmtree(base, ignore_errors=True)

# refusal in the middle of a block: that block is discarded, earlier ones stay
base, remote, code, idx, pool = new_env("idxB_")
si.init_index_branch(code, idx)
write_pool_shard(pool, 20, [{"id": 20 + i, "status": "ok", "pages": 3, "text": crim_text("Name" + str(i), n=9)} for i in range(4)])
write_pool_shard(pool, 10, [{"id": 10 + i, "status": "ok", "pages": 3, "text": crim_text("Other" + str(i), n=9)} for i in range(4)])
probe = FakeClient()
run_shift(code, idx, pool, probe, max_blocks=1, batch_items=6)
calls_for_one_block = probe.calls
shutil.rmtree(base, ignore_errors=True)
base, remote, code, idx, pool = new_env("idxC_")
si.init_index_branch(code, idx)
write_pool_shard(pool, 20, [{"id": 20 + i, "status": "ok", "pages": 3, "text": crim_text("Name" + str(i), n=9)} for i in range(4)])
write_pool_shard(pool, 10, [{"id": 10 + i, "status": "ok", "pages": 3, "text": crim_text("Other" + str(i), n=9)} for i in range(4)])
cf = FakeClient(fail_after=calls_for_one_block + 1, exc=AuthenticationError("service refused"))
r5 = run_shift(code, idx, pool, cf, batch_items=6)
check(r5["blocks_done"] == 1 and "stopped inside block" in r5["stop_reason"] and "discarded" in r5["stop_reason"], "a refusal mid-block keeps the finished block and discards the unfinished one")
check(sorted(si.ledger(idx)) == [20], "only the complete block is in the ledger")
check(not glob.glob(os.path.join(idx, "index", "000010*")), "no half-written files are left behind")
check(r5["wasted_tokens"] > 0 and si.tokens_spent(idx) == cf.tokens, "tokens spent on the discarded block are still counted against the allowance")
shutil.rmtree(base, ignore_errors=True)

# ceiling: stops BEFORE a block it cannot afford
base, remote, code, idx, pool = new_env("idxD_")
si.init_index_branch(code, idx)
write_pool_shard(pool, 20, [{"id": 20 + i, "status": "ok", "pages": 3, "text": crim_text("Name" + str(i), n=9)} for i in range(4)])
write_pool_shard(pool, 10, [{"id": 10 + i, "status": "ok", "pages": 3, "text": crim_text("Other" + str(i), n=9)} for i in range(4)])
probe_tokens = 0
cc = FakeClient()
r6 = run_shift(code, idx, pool, cc, ceiling=3000)
check("ceiling" in r6["stop_reason"] and r6["blocks_done"] <= 1 and si.tokens_spent(idx) <= 3000, "it stops at the token ceiling and never spends past it")
shutil.rmtree(base, ignore_errors=True)

# time budget
base, remote, code, idx, pool = new_env("idxE_")
si.init_index_branch(code, idx)
for s in (30, 20, 10):
    write_pool_shard(pool, s, [{"id": s + 1, "status": "ok", "pages": 3, "text": crim_text("T" + str(s))}])
tick = {"t": 0.0}
def clk():
    tick["t"] += 700.0
    return tick["t"]
r7 = run_shift(code, idx, pool, FakeClient(), minutes=40, clock=clk)
check("time budget" in r7["stop_reason"] and 0 <= r7["blocks_done"] < 3, "it stops cleanly when the time box is used up")
shutil.rmtree(base, ignore_errors=True)

# push failure is reported, not hidden
base, remote, code, idx, pool = new_env("idxF_")
si.init_index_branch(code, idx)
write_pool_shard(pool, 20, [{"id": 21, "status": "ok", "pages": 3, "text": crim_text("T")}])
shutil.rmtree(remote, ignore_errors=True)
r8 = run_shift(code, idx, pool, FakeClient())
check("push failed" in r8["stop_reason"] or "could not update" in r8["stop_reason"], "a push/sync problem is reported in the stop reason")
shutil.rmtree(base, ignore_errors=True)

# ================================================================ H. init, active-check
print("--- init and active-check")
base, remote, code, idx, pool = new_env("idxG_")
si.init_index_branch(code, idx)
idx2 = os.path.join(base, "idx2")
si.init_index_branch(code, idx2) if False else None
now = 10**10
git(idx, "commit", "--allow-empty", "-m", "index block 000020-000029")
git(idx, "push", "origin", "HEAD")
ts = int(git(idx, "log", "-1", "--format=%ct").stdout.strip())
git(code, "fetch", "origin")
check(si.active_check(code, now=ts + 60).startswith("ACTIVE"), "a very recent 'index block' commit means another session is running")
check(si.active_check(code, now=ts + 3600).startswith("IDLE"), "an old commit means nobody is running")
git(idx, "commit", "--allow-empty", "-m", "shift log"); git(idx, "push", "origin", "HEAD"); git(code, "fetch", "origin")
check(si.active_check(code, now=int(git(idx, "log", "-1", "--format=%ct").stdout.strip()) + 60).startswith("IDLE"), "a finished session (shift log) counts as idle")
shutil.rmtree(base, ignore_errors=True)

# second attach to an already-existing branch (a later cloud session)
base, remote, code, idx, pool = new_env("idxH_")
si.init_index_branch(code, idx)
write_pool_shard(pool, 20, [{"id": 21, "status": "ok", "pages": 3, "text": crim_text("T")}])
run_shift(code, idx, pool, FakeClient())
git(code, "worktree", "remove", "--force", idx)
git(code, "branch", "-D", "claude/sci-index")
si.init_index_branch(code, idx)
check(len(si.ledger(idx)) == 1, "a later session re-attaches the existing index branch with its saved blocks")
shutil.rmtree(base, ignore_errors=True)

# ================================================================ I. evaluation helpers + end to end
print("--- evaluation")
check(si.section_numbers("Does Section 139 of the Act and sections 35 and 54 apply to a 498A case?") >= {"139", "35", "54", "498A"}, "section numbers are picked out of a question")
check(si.has_section("as provided in Section 139 of the Negotiable Instruments Act", {"139"}) and not si.has_section("page 139 of the report", {"139"}), "a section number only counts when it is cited as a section")
pin = si.shingles("the presumption under section 139 of the negotiable instruments act includes the existence of a legally enforceable debt which is rebuttable")
check(si.is_pinned("note that the presumption under section 139 of the negotiable instruments act includes the existence of a legally enforceable debt which is rebuttable by the accused", [pin]), "a passage containing the verified holding counts as the pinned paragraph")
check(not si.is_pinned("completely different words about land revenue and tenancy matters in the village", [pin]), "an unrelated passage does not")

base, remote, code, idx, pool = new_env("idxI_")
si.init_index_branch(code, idx)
holding = "The presumption under Section 139 of the Negotiable Instruments Act includes the existence of a legally enforceable debt and the accused can rebut the presumption by raising a probable defence on the preponderance of probabilities."
j = crim_text("Rangappa").replace("The accused Rangappa was prosecuted for the offence under Section 420 IPC and the prosecution case is that the complainant lodged an FIR about cheating number 2", holding + " The cheque was dishonoured and the complainant sent notice")
write_pool_shard(pool, 30, [{"id": 31, "status": "ok", "pages": 3, "text": j}, {"id": 32, "status": "ok", "pages": 3, "text": crim_text("Filler")}])
run_shift(code, idx, pool, FakeClient())
lm = {"landmarks": [
    {"name": "Present case", "doc": 31, "pinned": [{"label": "2", "text": holding}], "questions": [{"kind": "legal", "q": "Does the presumption under Section 139 of the Negotiable Instruments Act include the existence of a legally enforceable debt and how can the accused rebut it?"}]},
    {"name": "Missing case", "doc": 9999, "pinned": [{"label": "1", "text": "nothing"}], "questions": [{"kind": "lay", "q": "something else"}]}]}
lmp = os.path.join(base, "lm.json")
json.dump(lm, open(lmp, "w"))
res = si.run_eval(idx, FakeClient(), landmarks_path=lmp, out=lambda *_: None)
rows = {r["name"]: r for r in res["results"]}
check(rows["Missing case"]["status"] == "not_embedded_yet" and rows["Present case"]["status"] == "tested", "a landmark not yet embedded is reported as such, not counted as a miss")
check(rows["Present case"]["doc_rank"] is not None and rows["Present case"]["doc_rank"] <= 5 and rows["Present case"]["pinned_in_top3"], "the planted verified paragraph is found by the evaluation")
check(res["summary"]["tested"] == 1 and res["summary"]["full_success"] == 1, "the summary counts only tested questions")
shutil.rmtree(base, ignore_errors=True)

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILED:")
    for f in FAILURES:
        print("  -", f)
    raise SystemExit(1)
print("ALL PASSED")
