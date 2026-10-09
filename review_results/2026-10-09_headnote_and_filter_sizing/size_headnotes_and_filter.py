"""Two read-only sizings, no search and no spend (PRIVATE: uses the answer key for one table).

1. HEADNOTES. The law-report front matter (catchwords, "Issue for Consideration", "Held") that the index cuts off bucket judgments before cutting passages. What would it cost to embed it
   as extra passages, how long is it, and do the key authorities of the tuning questions that the search missed even have one?
2. THE CRIMINAL-LAW FILTER. The index keeps a judgment only if its opening block says it is criminal or its cue-word density is 10 per 10,000 characters or more. How many judgments sit just below
   the line, and what would they cost to add?

Needs the corpus store (python -m goodlaw.corpus build --crawl-dir ../recourse-sci-pool-data --bucket-dir ../recourse-sci-bucket-data --out corpus.sqlite), the main index folder, the bucket data and
the private key. Run: python size_headnotes_and_filter.py --corpus corpus.sqlite
"""
import argparse
import collections
import glob
import gzip
import json
import os
import random
import sqlite3
import statistics
import sys

ROOT = "/home/user/recourse-sci-pool"
sys.path.insert(0, ROOT)
import sci_index as si                                   # noqa: E402

OUT = os.path.dirname(os.path.abspath(__file__))
INDEX = "/home/user/recourse-sci-index"
BUCKET = "/home/user/recourse-sci-bucket-data"
CHARS_PER_TOKEN, PRICE = 3.87, 0.12 / 1e6


def cost(chars):
    return round(chars / CHARS_PER_TOKEN * PRICE, 3)


def index_docs():
    """{doc id: the main index's document row} for every document the index looked at."""
    rows = {}
    for f in glob.glob(os.path.join(INDEX, "index", "*.docs.jsonl.gz")):
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    r = json.loads(line)
                    rows[r["doc"]] = r
    return rows


def headnotes(rows):
    held = {d: r for d, r in rows.items() if r.get("passages") and isinstance(r.get("src"), dict)}
    blocks = si.bucket_blocks(BUCKET)
    need = collections.defaultdict(set)
    for d in held:
        need[d - (d - si.BUCKET_BASE) % si.BLOCK_SIZE].add(d)
    lens = []
    for start, docs in need.items():
        with gzip.open(blocks[start]["path"], "rt", encoding="utf-8", errors="replace") as fh:
            recs = [json.loads(l) for l in fh if l.strip()]
        for i, r in enumerate(recs):
            if start + i in docs:
                lens.append(len(r["text"][: (r.get("body_start") or 0)]))
    with_hn = [x for x in lens if x > 0]
    caps = {c: sum(min(x, c) for x in lens) for c in (3000, 4000, 6000)}
    key = json.load(open(os.path.join(ROOT, "review_data/ruler/real30_key_v1.json")))["questions"]
    pool = json.load(open(os.path.join(ROOT, "review_results/2026-10-09_real30_pool_dev/authority_hits.json")))["scores"]["A today"]
    tuning = {q["id"] for q in json.load(open(os.path.join(ROOT, "review_data/ruler/real30_v1.json")))["questions"] if q["half"] == "dev"}
    table = []
    for rid in sorted(k for k in key if k in tuning and key[k]["reachable"] is True):
        docs = key[rid]["primary_key_docs"] or key[rid]["key_docs"]
        table.append({"qid": rid, "key_docs": docs, "has_law_report_headnote": all(d >= si.BUCKET_BASE for d in docs), "version_A_first_rank": pool.get(rid, {}).get("first_rank")})
    return {"bucket_judgments_in_main_index": len(lens), "with_front_matter": len(with_hn), "median_chars": statistics.median(with_hn), "mean_chars": round(statistics.mean(with_hn)),
            "p90_chars": sorted(with_hn)[int(len(with_hn) * 0.9)], "total_chars": sum(lens), "total_dollars": cost(sum(lens)),
            "dollars_if_capped_at_chars": {str(c): cost(v) for c, v in caps.items()}, "tuning_key_authorities": table}


def density_bands(corpus):
    con = sqlite3.connect(corpus)
    by = {}
    for k, source, sid, bp, title, year, tl in con.execute("select doc_key, source, src_id, bucket_path, title, year, text_len from docs"):
        by[(source, bp if source == "bucket" else sid)] = (k, title, year, tl)
    rows = []
    for d, r in index_docs().items():
        if r.get("skip") != "not_criminal":
            continue
        m = by.get(("bucket", r["src"]["path"])) if isinstance(r.get("src"), dict) and r["src"].get("path") else by.get(("crawl", str(d)))
        if m:
            rows.append((d, r.get("density") or 0.0, m))
    bands = [(8, 10), (6, 8), (5, 6), (4, 5), (3, 4), (2, 3), (1, 2), (0.0001, 1), (0, 0.0001)]
    out, cum_n, cum_c = [], 0, 0
    for lo, hi in bands:
        sel = [x for x in rows if lo <= x[1] < hi]
        chars = sum(x[2][3] or 0 for x in sel)
        cum_n, cum_c = cum_n + len(sel), cum_c + chars
        out.append({"density_from": lo, "density_below": hi, "judgments": len(sel), "chars": chars, "dollars": cost(chars), "cumulative_judgments": cum_n, "cumulative_dollars": cost(cum_c)})
    rnd = random.Random(7)
    samples = {}
    for name, (lo, hi) in (("6_to_10", (6, 10)), ("3_to_6", (3, 6))):
        sel = [x for x in rows if lo <= x[1] < hi and (x[2][3] or 0) > 8000]
        samples[name] = {"eligible": len(sel), "titles": [{"density": round(x[1], 1), "year": x[2][2], "title": (x[2][1] or "")[:90]} for x in rnd.sample(sel, min(14, len(sel)))]}
    return {"not_criminal_judgments_with_a_corpus_match": len(rows), "bands": out, "samples": samples}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    a = ap.parse_args()
    rows = index_docs()
    res = {"headnotes": headnotes(rows), "filter": density_bands(a.corpus)}
    json.dump(res, open(os.path.join(OUT, "sizing.json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps({"headnotes": {k: v for k, v in res["headnotes"].items() if k != "tuning_key_authorities"}, "bands": res["filter"]["bands"]}, indent=1))


if __name__ == "__main__":
    main()
