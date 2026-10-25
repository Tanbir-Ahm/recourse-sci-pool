"""Scratch: counts what a copy of the big judgment index holds, straight from its files. usage: python count_index.py <index folder> <label>"""
import sys, glob, gzip, json, collections, os, re
import numpy as np
d, label = sys.argv[1], sys.argv[2]
shards = sorted(glob.glob(d + "/*.docs.jsonl.gz"))
recs = {}                      # doc id -> record (docs file)
dup_docs = 0
skip = collections.Counter()
passages = 0
docs_with_passages = set()
vec_rows = 0
bad_shards = []
for f in shards:
    base = f[:-len(".docs.jsonl.gz")]
    with gzip.open(f, "rt", encoding="utf-8") as fh:
        for l in fh:
            if not l.strip():
                continue
            r = json.loads(l)
            k = str(r["doc"])
            if k in recs:
                dup_docs += 1
            recs[k] = r
            if r.get("skip"):
                skip[r["skip"]] += 1
    n = 0
    if os.path.exists(base + ".meta.jsonl.gz"):
        with gzip.open(base + ".meta.jsonl.gz", "rt", encoding="utf-8") as fh:
            for l in fh:
                if l.strip():
                    m = json.loads(l)
                    n += 1
                    docs_with_passages.add(str(m["doc"]))
    passages += n
    rows_v = np.load(base + ".vec.npy", mmap_mode="r").shape[0] if os.path.exists(base + ".vec.npy") else 0
    vec_rows += rows_v
    if rows_v != n:
        bad_shards.append((os.path.basename(base), n, rows_v))
print(f"=== {label}")
print("shards:", len(shards))
print("document records (all, distinct ids):", len(recs), "| duplicate ids across shards:", dup_docs)
print("records with a skip reason:", sum(skip.values()), dict(skip))
print("records WITHOUT passages in meta files:", len(set(recs) - docs_with_passages), "| passages' docs not in docs files:", len(docs_with_passages - set(recs)))
print("DOCUMENTS WITH AT LEAST ONE PASSAGE (= searchable judgments):", len(docs_with_passages))
print("passages (meta rows):", passages, "| vectors:", vec_rows, "| shards where meta rows != vector rows:", bad_shards[:5])
by_src = collections.Counter()
for k in docs_with_passages:
    r = recs.get(k, {})
    s = r.get("src")
    by_src["bucket" if isinstance(s, dict) and s.get("source") == "bucket" else "crawl"] += 1
print("searchable docs by origin:", dict(by_src))
json.dump({"label": label, "searchable": sorted(docs_with_passages), "skip": dict(skip), "records": len(recs), "passages": passages}, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), f"counts_{label}.json"), "w"))
