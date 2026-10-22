"""What does the big search index actually hold: how many judgments of each court were looked at, how many were embedded, and is every embedded passage really there? Reads files only: no network,
no key, no spend, nothing changed.

    python review_tools/experiments/index_holdings_2026-10-22.py --index-dir <checkout of claude/sci-index> [--store corpus.sqlite] --out review_results/2026-10-22_index_holdings

Per source (the crawl, the open bucket, the Supreme Court's newer archive, the Gauhati High Court's own files, the Gauhati text from the open bucket) it counts, from the index's document records:
judgments looked at ("recorded"), judgments embedded ("kept": they have passages), and the judgments that were looked at but NOT embedded, with the index's own reason (not criminal law, too short, an
exact copy, held by the crawl). Then it checks that every passage the ledger counts has a vector: rows of each vectors file against rows of its passage file and against the ledger and the document
records, and that every vector is finite. With --store it also counts distinct judgments by the text store's reckoning (a second copy is the judgment it copies). A block's source is read from its id.
"""
import argparse
import collections
import gzip
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)

import sci_index as si  # noqa: E402

EXTRA = 2_000_000_000
SOURCES = ("crawl", "bucket", "ghc_court", "sci_newer", "ghc_bucket")
COURT = {"crawl": "Supreme Court", "bucket": "Supreme Court", "sci_newer": "Supreme Court", "ghc_court": "Gauhati High Court", "ghc_bucket": "Gauhati High Court"}


def source_of(start):
    if start < 1_000_000_000:
        return "crawl"
    if start < EXTRA:
        return "bucket"
    n = (start - EXTRA) // si.BLOCK_SIZE
    return "ghc_court" if n < 1000 else ("sci_newer" if n < 2000 else "ghc_bucket")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--index-dir", required=True)
    ap.add_argument("--store")
    ap.add_argument("--head", help="the index branch commit the checkout is at, recorded in the numbers (the index can change while a run is in progress)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    led = si.ledger(a.index_dir)
    idx = os.path.join(a.index_dir, "index")
    res = {"index_branch_commit": a.head, "counted_at_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).strftime("%Y-%m-%d %H:%M:%S"), "blocks_in_ledger": len(led), "tokens_spent_ever": si.tokens_spent(a.index_dir), "sources": {}, "vectors_check": {}}
    docs = {}
    rows = {s: {"blocks": 0, "tokens": 0, "recorded": 0, "kept": 0, "passages_in_document_records": 0, "noise_dropped": 0, "ledger_passages": 0, "not_embedded": collections.Counter(),
                "vector_rows": 0, "passage_rows": 0, "non_finite_vectors": 0, "blocks_where_rows_differ": []} for s in SOURCES}
    for start, v in sorted(led.items()):
        s = source_of(start)
        r = rows[s]
        r["blocks"] += 1
        r["tokens"] += v["tokens"]
        r["ledger_passages"] += v["passages"]
        for line in gzip.open(os.path.join(idx, v["base"] + ".docs.jsonl.gz"), "rt", encoding="utf-8"):
            d = json.loads(line)
            docs[d["doc"]] = (s, d)
            r["recorded"] += 1
            if "skip" in d:
                r["not_embedded"][d["skip"]] += 1
            else:
                r["kept"] += 1
                r["passages_in_document_records"] += d.get("passages", 0)
                r["noise_dropped"] += d.get("noise", 0)
        vec_path, meta_path = os.path.join(idx, v["base"] + ".vec.npy"), os.path.join(idx, v["base"] + ".meta.jsonl.gz")
        if os.path.exists(vec_path):                      # a block with no passage to embed (every judgment in it was skipped) has no vectors file
            vec = np.load(vec_path, mmap_mode="r")
            n_vec = vec.shape[0]
            for i in range(0, n_vec, 20000):
                r["non_finite_vectors"] += int((~np.isfinite(np.asarray(vec[i:i + 20000], dtype=np.float32)).all(axis=1)).sum())
        else:
            n_vec = 0
        n_meta = sum(1 for _ in gzip.open(meta_path, "rt", encoding="utf-8")) if os.path.exists(meta_path) else 0
        r["vector_rows"] += n_vec
        r["passage_rows"] += n_meta
        if not (n_vec == n_meta == v["passages"]):
            r["blocks_where_rows_differ"].append(start)
    for s in SOURCES:
        r = rows[s]
        r["not_embedded"] = dict(r["not_embedded"])
        r["every_kept_passage_has_a_vector"] = (r["vector_rows"] == r["passage_rows"] == r["ledger_passages"] == r["passages_in_document_records"] and not r["non_finite_vectors"] and not r["blocks_where_rows_differ"])
        r["court"] = COURT[s]
        res["sources"][s] = r
    res["by_court"] = {}
    for court in ("Supreme Court", "Gauhati High Court"):
        ss = [s for s in SOURCES if COURT[s] == court]
        res["by_court"][court] = {"recorded": sum(rows[s]["recorded"] for s in ss), "embedded_judgments": sum(rows[s]["kept"] for s in ss), "passages": sum(rows[s]["ledger_passages"] for s in ss)}
    res["total_passages"] = sum(rows[s]["ledger_passages"] for s in SOURCES)
    res["total_vector_rows"] = sum(rows[s]["vector_rows"] for s in SOURCES)

    if a.store:
        sys.path.insert(0, ROOT)
        from goodlaw import corpus as K
        from goodlaw import passage_input as PI
        corpus = K.Corpus(a.store)
        idocs = PI.IndexDocs([d for _, d in docs.values()])
        who = PI.CorpusIdentity(corpus, idocs)
        distinct, unmapped, copies = collections.defaultdict(set), collections.Counter(), collections.Counter()
        for doc_id, (s, d) in docs.items():
            if "skip" in d or COURT[s] != "Supreme Court":
                continue
            ident = who(doc_id)
            if not ident or not ident.doc_key:
                unmapped[s] += 1
                continue
            distinct[s].add(ident.doc_key)
        allkeys = set().union(*distinct.values()) if distinct else set()
        res["supreme_court_distinct_by_the_store"] = {"embedded_judgments_mapped_to_the_store": {s: len(k) for s, k in distinct.items()}, "distinct_judgments_over_all_sources": len(allkeys),
                                                      "embedded_judgments_the_store_cannot_place": dict(unmapped)}
        res["supreme_court_embedded_judgments_raw"] = sum(rows[s]["kept"] for s in ("crawl", "bucket", "sci_newer"))
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "numbers.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
        fh.write("\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
