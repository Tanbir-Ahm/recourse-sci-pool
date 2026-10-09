#!/usr/bin/env python3
"""Builds a SIDE INDEX ("supplement"): extra passages and vectors for judgments that the main index left out, in a separate folder, so that the main index (and the experiment recorded on its
commit) is not touched. The pool runner can search "main + supplement" as a labelled extra arm (`pool_runner.py --supplement DIR`).

  python review_tools/build_supplement.py --docs review_results/2026-10-09_index_gap_sizing/supplement_docs.json --out ../recourse-sci-supplement            # plan only: reads, cuts, counts, spends nothing
  python review_tools/build_supplement.py --docs ... --out ../recourse-sci-supplement --embed --max-tokens 1200000                                          # embeds with voyage-law-2 and writes

What it does, per listed judgment: finds the saved record (crawl block or bucket shard) by the document id the main index gave it, checks that its text hashes to what the main index recorded for
that id (so it is the very text the main index saw), checks that the main index holds no passages for it (it must be a judgment the index left out), cuts it into passages with the index's own
code (`sci_index.prepare_block`, `make_passages`) with the criminal-law test switched off for these documents only, embeds the passages and writes block files in the index's format. The documents
keep the ids the main index gave them, so the scorers' key (by id) works unchanged on the supplement arm. Nothing is embedded without --embed, and never above --max-tokens.
Writes OUT/index/*.docs.jsonl.gz, *.meta.jsonl.gz, *.vec.npy, OUT/index/MODEL and OUT/SUPPLEMENT.json (what, why, source files, tokens charged).
"""
import argparse
import contextlib
import datetime
import glob
import gzip
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
import sci_index as si                     # noqa: E402

DEFAULT_POOL = os.path.normpath(os.path.join(ROOT, "..", "recourse-sci-pool-data"))
DEFAULT_BUCKET = os.path.normpath(os.path.join(ROOT, "..", "recourse-sci-bucket-data"))
DEFAULT_INDEX = os.path.normpath(os.path.join(ROOT, "..", "recourse-sci-index"))
SUPPLEMENT_START = 5_000_000_000        # a file name only (the block's documents keep their own ids); outside the main index's id space
VERSION = "supplement-1"


class SupplementError(RuntimeError):
    pass


def main_index_rows(index_dir):
    """{doc id: the main index's document row} (hash, skip reason, passages) and the set of documents that have passages there."""
    rows, with_passages = {}, set()
    for f in glob.glob(os.path.join(index_dir, "index", "*.docs.jsonl.gz")):
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    r = json.loads(line)
                    rows[r["doc"]] = r
                    if r.get("passages"):
                        with_passages.add(r["doc"])
    return rows, with_passages


def locate(entry, crawl_blocks, bucket_blocks):
    """The saved record (as prepare_block reads it) of one listed judgment, found by the document id the main index gave it."""
    doc = int(entry["index_doc"])
    if entry["source"] == "bucket":
        start = doc - (doc - si.BUCKET_BASE) % si.BLOCK_SIZE
        info = bucket_blocks.get(start)
        if info is None:
            raise SupplementError(f"{entry['doc_key']}: no bucket shard starts at {start}")
    else:
        starts = [s for s, v in crawl_blocks.items() if s <= doc <= v["end"]]
        if not starts:
            raise SupplementError(f"{entry['doc_key']}: no crawl block holds id {doc}")
        info = crawl_blocks[starts[0]]
    for r in si.read_block(info):
        if r.get("id") == doc:
            return r
    raise SupplementError(f"{entry['doc_key']}: id {doc} is not in {os.path.basename(info['path'])}")


@contextlib.contextmanager
def criminal_test_off():
    """Within the block, `sci_index.is_criminal` answers yes for every document (the density is still measured and recorded). Restored afterwards, whatever happens."""
    original = si.is_criminal

    def always(text):
        return True, original(text)[1]
    si.is_criminal = always
    try:
        yield
    finally:
        si.is_criminal = original


def prepare(entries, rows, with_passages, crawl_blocks, bucket_blocks):
    """(records, problems): the records to cut, after the identity checks. A problem is a reason a listed judgment cannot be added."""
    records, problems = [], []
    for e in entries:
        doc = int(e["index_doc"])
        row = rows.get(doc)
        if row is None:
            problems.append(f"{e['doc_key']}: the main index has no record of document {doc}")
            continue
        if doc in with_passages:
            problems.append(f"{e['doc_key']}: the main index already holds passages of document {doc}; it is not a gap")
            continue
        if row.get("skip") != "not_criminal":
            problems.append(f"{e['doc_key']}: the main index skipped it as {row.get('skip')!r}, not as 'not_criminal'")
            continue
        try:
            rec = locate(e, crawl_blocks, bucket_blocks)
        except SupplementError as err:
            problems.append(str(err))
            continue
        if si.doc_hash(rec["text"]) != row.get("hash"):
            problems.append(f"{e['doc_key']}: the saved text does not hash to the main index's record of document {doc} (a different text or a different preparation)")
            continue
        rec = dict(rec, in_crawl=False)
        records.append(rec)
    return records, problems


def plan(entries, index_dir, pool_dir, bucket_dir):
    rows, with_passages = main_index_rows(index_dir)
    crawl_blocks = si.pool_blocks(pool_dir)
    bucket_blocks = si.bucket_blocks(bucket_dir)
    records, problems = prepare(entries, rows, with_passages, crawl_blocks, bucket_blocks)
    with criminal_test_off():
        prepared = si.prepare_block(records, {})
    return prepared, problems


def build(entries, out_dir, index_dir, pool_dir, bucket_dir, client=None, max_tokens=None, embed=False, docs_path=None, log=print):
    """Plans, and when `embed` is set embeds and writes. Returns a dict with the plan figures (and the manifest when written). Refuses on any identity problem."""
    prepared, problems = plan(entries, index_dir, pool_dir, bucket_dir)
    if problems:
        raise SupplementError("; ".join(problems))
    stats = prepared["stats"]
    per_doc = {d["doc"]: d.get("passages", 0) for d in prepared["docs"]}
    log(f"{len(prepared['docs'])} judgments, {stats['passages']:,} passages, about {stats['est_tokens']:,} tokens (about ${stats['est_tokens'] * 0.12 / 1e6:.3f} at $0.12 per million)")
    result = {"docs": len(prepared["docs"]), "passages": stats["passages"], "est_tokens": stats["est_tokens"], "per_doc": per_doc, "written": False}
    if not embed:
        return result
    if max_tokens is None:
        raise SupplementError("--max-tokens is required with --embed")
    if stats["est_tokens"] > max_tokens:
        raise SupplementError(f"the estimate of {stats['est_tokens']:,} tokens is over --max-tokens {max_tokens:,}")
    if os.path.isdir(os.path.join(out_dir, "index")) and glob.glob(os.path.join(out_dir, "index", "*.meta.jsonl.gz")):
        raise SupplementError(f"{out_dir} already holds a supplement; remove it first (nothing was embedded)")
    texts = [p["text"] for p in prepared["passages"]]
    vectors, used = si.embed_texts(client, texts, budget_tokens=max_tokens)
    base = si.write_block_files(out_dir, SUPPLEMENT_START, si.BLOCK_SIZE, prepared["docs"], prepared["passages"], vectors, used)
    with open(os.path.join(out_dir, "index", "MODEL"), "w", encoding="utf-8") as fh:
        fh.write(si.MODEL + "\n")
    head = si._git(index_dir, "rev-parse", "HEAD").stdout.strip() if os.path.isdir(index_dir) else None
    manifest = {"version": VERSION, "built": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "model": si.MODEL,
                "main_index_commit": head, "block_file": base, "documents": len(prepared["docs"]), "passages": stats["passages"], "tokens_charged": used,
                "dollars_estimate": round(used * 0.12 / 1e6, 4), "docs_list": os.path.relpath(docs_path, ROOT) if docs_path else None,
                "docs_list_sha256": hashlib.sha256(open(docs_path, "rb").read()).hexdigest() if docs_path else None,
                "why": "judgments the Overruled Register links to a ruling the main index holds, but that the main index left out as 'not criminal law' (cue-word density below 10 per 10,000 characters); "
                       "added here, outside the main index, so that the correcting ruling can be found next to the ruling it corrects",
                "documents_detail": [{"doc": d["doc"], "doc_key": next(e["doc_key"] for e in entries if int(e["index_doc"]) == d["doc"]), "title": next(e["title"] for e in entries if int(e["index_doc"]) == d["doc"]),
                                      "passages": d.get("passages", 0), "density": d.get("density")} for d in prepared["docs"]]}
    with open(os.path.join(out_dir, "SUPPLEMENT.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    result.update(written=True, tokens_charged=used, manifest=manifest)
    log(f"written {base}; tokens charged {used:,} (about ${used * 0.12 / 1e6:.3f})")
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--docs", required=True, help="the list of judgments (supplement_docs.json)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--index-dir", default=DEFAULT_INDEX)
    ap.add_argument("--pool-dir", default=DEFAULT_POOL)
    ap.add_argument("--bucket-dir", default=DEFAULT_BUCKET)
    ap.add_argument("--embed", action="store_true", help="embed and write (spends); without it only the plan is printed")
    ap.add_argument("--max-tokens", type=int, help="refuse to embed more than this many tokens (required with --embed)")
    a = ap.parse_args(argv)
    with open(a.docs, encoding="utf-8") as fh:
        entries = json.load(fh)["docs"]
    try:
        build(entries, a.out, a.index_dir, a.pool_dir, a.bucket_dir, client=si.make_client() if a.embed else None, max_tokens=a.max_tokens, embed=a.embed, docs_path=a.docs)
    except (SupplementError, si.EmbedStop) as e:
        print("refused:", e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
