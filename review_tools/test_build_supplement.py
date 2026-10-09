"""Tests for review_tools/build_supplement.py on a tiny invented collection (a crawl block, a bucket shard and a main index folder written to a temporary directory), with a fake embedding
service. Costs nothing. Run: python review_tools/test_build_supplement.py"""
import gzip
import json
import os
import re
import shutil
import sys
import tempfile
from types import SimpleNamespace

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..")))
import build_supplement as B             # noqa: E402
import sci_index as si                   # noqa: E402

FAILS = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{detail}]"))
    if not cond:
        FAILS.append(name)


def civil(tag, n=12):
    head = "IN THE SUPREME COURT OF INDIA\nCIVIL APPELLATE JURISDICTION\nCIVIL APPEAL NO. 9 OF 2011\nJUDGMENT\n"
    return head + "".join(f"\n{i}. The assessee {tag} challenged the assessment of sales tax on the turnover for the year, and the tribunal held that the rate of tax on the goods is as notified in the schedule number {i} of the statute for the year in question under appeal, which the revenue disputes in this court." for i in range(1, n + 1))


def criminal(tag, n=12):
    head = "IN THE SUPREME COURT OF INDIA\nCRIMINAL APPELLATE JURISDICTION\nCRIMINAL APPEAL NO. 7 OF 2012\nJUDGMENT\n"
    return head + "".join(f"\n{i}. The accused {tag} was prosecuted for the offence and the prosecution case is that the complainant lodged an FIR about cheating number {i}, and the trial court convicted him after the evidence of the witnesses on record." for i in range(1, n + 1))


class FakeClient:
    def __init__(self):
        self.calls, self.texts = 0, []

    def embed(self, texts, model=None, input_type=None):
        self.calls += 1
        self.texts += list(texts)
        tok = sum(len(t) for t in texts) // 4 + 1
        rng = np.random.default_rng(len(self.texts))
        return SimpleNamespace(embeddings=rng.normal(size=(len(texts), 16)).tolist(), total_tokens=tok)


def write_gz(path, rows):
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")


def doc_row(doc, text, skip=None, passages=None):
    r = {"doc": doc, "hash": si.doc_hash(text), "v": si.PREP_VERSION}
    if skip:
        r["skip"] = skip
    if passages:
        r["passages"] = passages
    return r


tmp = tempfile.mkdtemp()
try:
    pool, bucket, index, out = (os.path.join(tmp, d) for d in ("pool", "bucket", "index_repo", "supp"))
    for d in (os.path.join(pool, "shards"), os.path.join(bucket, "shards"), os.path.join(index, "index")):
        os.makedirs(d)
    # crawl block 0..249: id 3 civil (to add), id 4 criminal (already in the main index), id 5 civil (to add, but its text will not match the index record), id 6 civil (skipped for another reason)
    crawl = {3: civil("Alpha"), 4: criminal("Beta"), 5: civil("Gamma"), 6: civil("Delta")}
    recs = [{"id": i, "status": "ok", "text": crawl[i], "pages": 5} for i in sorted(crawl)]
    write_gz(os.path.join(pool, "shards", "000000-000249.ok4.gap0.err0.jsonl.gz"), recs)
    # bucket shard 'after-0000': record 0 is a civil judgment with a headnote to be cut, record 1 a criminal one
    b0 = {"scope": "after", "decision_date": "05-05-2017", "path": "2017_3_1_9", "title": "OMEGA versus STATE", "citation": "[2017] 3 S.C.R. 1", "case_id": "x", "status": "ok", "pages": 3,
          "text": "A\nSUPREME COURT REPORTS [2017] 3 S.C.R.\n" + civil("Omega"), "body_start": 0}
    b1 = dict(b0, path="2017_3_10_19", title="SIGMA versus STATE", text=criminal("Sigma"))
    write_gz(os.path.join(bucket, "shards", "after-0000.ok2.miss0.err0.jsonl.gz"), [b0, b1])
    bucket_start = si.BUCKET_BASE + si.bucket_ordinal("after", 0) * si.BLOCK_SIZE
    bucket_text0 = si.bucket_pages(b0)[0]
    rows = [doc_row(3, crawl[3], skip="not_criminal"), doc_row(4, crawl[4], passages=12), doc_row(5, "a different text entirely " * 100, skip="not_criminal"), doc_row(6, crawl[6], skip="short"),
            doc_row(bucket_start + 0, bucket_text0, skip="not_criminal"), doc_row(bucket_start + 1, si.bucket_pages(b1)[0], passages=12)]
    write_gz(os.path.join(index, "index", "000000-000249.docs6.pass0.tok0.docs.jsonl.gz"), rows)

    def entry(key, source, doc, title):
        return {"doc_key": key, "source": source, "src_id": str(doc), "bucket_path": None, "index_doc": doc, "title": title, "year": 2000, "text_len": 1000, "register_rows": []}

    good = [entry("c3", "crawl", 3, "ALPHA v. STATE"), entry("bX", "bucket", bucket_start + 0, "OMEGA v. STATE")]

    # the plan
    prepared, problems = B.plan(good, index, pool, bucket)
    check("a listed judgment the main index left out is read, cut into passages and planned, whatever its subject", not problems and len(prepared["docs"]) == 2 and prepared["stats"]["passages"] >= 20, (problems, prepared["stats"]))
    check("the documents keep the ids the main index gave them", sorted(d["doc"] for d in prepared["docs"]) == sorted([3, bucket_start + 0]))
    check("the passages come out as the index would cut them (same fields, same numbering from 1)", all({"doc", "i", "pn", "page", "section", "h", "text"} <= set(p) for p in prepared["passages"])
          and [p["i"] for p in prepared["passages"] if p["doc"] == 3][:3] == [0, 1, 2])
    check("the criminal-law test is restored after the plan (a civil text is still skipped by the index's own rule)", si.is_criminal(civil("Zed"))[0] is False and si.is_criminal(criminal("Zed"))[0] is True)
    # without the switch the same text is skipped, which is why the switch exists
    plain = si.prepare_block([dict(r, in_crawl=False) for r in (B.locate(good[0], si.pool_blocks(pool), si.bucket_blocks(bucket)),)], {})
    check("the same civil judgment is skipped by the ordinary index code", plain["stats"]["passages"] == 0 and plain["docs"][0]["skip"] == "not_criminal")

    # problems that stop the build
    for name, e, frag in (("one the main index already holds", entry("c4", "crawl", 4, "BETA"), "already holds passages"),
                          ("one whose text is not the text the main index saw", entry("c5", "crawl", 5, "GAMMA"), "does not hash"),
                          ("one the main index skipped for another reason", entry("c6", "crawl", 6, "DELTA"), "not as 'not_criminal'"),
                          ("one the main index has never heard of", entry("c9", "crawl", 9, "NOBODY"), "no record of document 9")):
        _, probs = B.plan([e], index, pool, bucket)
        check(f"refused: {name}", len(probs) == 1 and frag in probs[0], probs)
    try:
        B.build(good + [entry("c4", "crawl", 4, "BETA")], out, index, pool, bucket, client=FakeClient(), max_tokens=10 ** 9, embed=True)
        refused = False
    except B.SupplementError:
        refused = True
    check("a build with any problem listed embeds nothing and writes nothing", refused and not os.path.exists(out))

    # plan only
    fake = FakeClient()
    res = B.build(good, out, index, pool, bucket, client=fake, embed=False, log=lambda *_: None)
    check("without --embed nothing is spent and nothing is written", fake.calls == 0 and not os.path.exists(out) and res["written"] is False and res["passages"] > 0)
    try:
        B.build(good, out, index, pool, bucket, client=fake, embed=True, max_tokens=None, log=lambda *_: None)
        needs_cap = False
    except B.SupplementError:
        needs_cap = True
    check("--embed needs a token cap", needs_cap and fake.calls == 0)
    try:
        B.build(good, out, index, pool, bucket, client=fake, embed=True, max_tokens=10, log=lambda *_: None)
        over = False
    except B.SupplementError:
        over = True
    check("an estimate over the cap is refused before any call", over and fake.calls == 0)

    # the build
    res = B.build(good, out, index, pool, bucket, client=fake, embed=True, max_tokens=10 ** 9, docs_path=None, log=lambda *_: None)
    check("with --embed the passages are embedded once each and the files are written", res["written"] and fake.calls >= 1 and len(fake.texts) == res["passages"] and res["tokens_charged"] > 0)
    led = si.ledger(out)
    check("the written folder reads as an index (ledger, passages and vectors line up)", len(led) == 1 and list(led.values())[0]["passages"] == res["passages"])
    metas, M, docs_with = si._load_index(out)
    check("the index loader reads it: one vector per passage, documents as listed", len(metas) == M.shape[0] == res["passages"] and docs_with == {3, bucket_start + 0})
    check("it records the model that made its vectors", open(os.path.join(out, "index", "MODEL"), encoding="utf-8").read().strip() == si.MODEL)
    man = json.load(open(os.path.join(out, "SUPPLEMENT.json"), encoding="utf-8"))
    check("the manifest says what was added, why, and what it cost", man["documents"] == 2 and man["passages"] == res["passages"] and man["tokens_charged"] == res["tokens_charged"] and "not criminal law" in man["why"]
          and {d["doc_key"] for d in man["documents_detail"]} == {"c3", "bX"})
    try:
        B.build(good, out, index, pool, bucket, client=fake, embed=True, max_tokens=10 ** 9, log=lambda *_: None)
        again = False
    except B.SupplementError as e:
        again = "already holds a supplement" in str(e)
    check("a second build into the same folder is refused (nothing is paid for twice)", again)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print()
print("FAILED: " + ", ".join(FAILS) if FAILS else "all passed")
sys.exit(1 if FAILS else 0)
