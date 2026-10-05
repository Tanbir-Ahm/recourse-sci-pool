"""Decides, from the texts, which of the bucket's "none" judgments (dated up to 4 May 2017, not matched to the crawl by names) the crawl really holds.

For every saved bucket record of scope "none" it counts how many 8-word runs the bucket text shares with the opening (first 3,500
characters) of each crawled text. A real copy shares roughly 135 to 470 runs; a different judgment shares under 35 (checked on a sample,
see MATCH_REPORT.md), so 50 or more shared runs counts as "the crawl holds it". Runs found in more than 20 crawled openings are court
boilerplate and are ignored.

Usage: python resolve_none.py BUCKET_DATA_DIR CRAWL_DATA_DIR OUT.csv.gz
  BUCKET_DATA_DIR  checkout of branch claude/sci-bucket (shards/none-*.jsonl.gz)
  CRAWL_DATA_DIR   checkout of branch claude/sci-pool (shards/*.jsonl.gz)
Writes one row per bucket judgment: path, title, decision_date, key, status, best crawl id, shared runs, and "in_crawl" (yes / no / unreadable).
"""
import collections, csv, glob, gzip, json, re, sys
from array import array
import numpy as np

HEAD_CHARS, MIN_SHARED, MAX_DOCS_PER_RUN = 3500, 50, 20
W = lambda s: re.findall(r"[a-z0-9]+", s.lower())


def runs(text, n=8):
    ws = W(text)
    return {hash(" ".join(ws[i:i + n])) for i in range(max(len(ws) - n + 1, 0))}


def build_index(crawl_dir):
    hs, ids = array("q"), array("i")
    for f in sorted(glob.glob(f"{crawl_dir}/shards/*.jsonl.gz")):
        for line in gzip.open(f, "rt", encoding="utf-8"):
            r = json.loads(line)
            if r.get("status") != "ok":
                continue
            h = runs(r["text"][:HEAD_CHARS])
            hs.extend(h)
            ids.extend([r["id"]] * len(h))
    H = np.frombuffer(hs, dtype=np.int64)
    I = np.frombuffer(ids, dtype=np.int32)
    order = np.argsort(H, kind="stable")
    return H[order], I[order]


def best_match(index, text):
    """(best crawl id, number of shared runs) or (None, 0)."""
    H, I = index
    b = np.array(sorted(runs(text)), dtype=np.int64)
    if not len(b):
        return None, 0
    lo, hi = np.searchsorted(H, b, "left"), np.searchsorted(H, b, "right")
    keep = (hi > lo) & (hi - lo <= MAX_DOCS_PER_RUN)
    found = [I[a:z] for a, z in zip(lo[keep], hi[keep])]
    if not found:
        return None, 0
    c = collections.Counter(np.concatenate(found).tolist())
    cid, n = c.most_common(1)[0]
    return cid, n


def main(bucket_dir, crawl_dir, out_path):
    index = build_index(crawl_dir)
    print("crawl runs indexed:", len(index[0]), file=sys.stderr)
    rows, tally = [], collections.Counter()
    for f in sorted(glob.glob(f"{bucket_dir}/shards/none-*.jsonl.gz")):
        for line in gzip.open(f, "rt", encoding="utf-8"):
            r = json.loads(line)
            row = dict(path=r.get("path"), title=r.get("title"), decision_date=r.get("decision_date"), key=r.get("key"), status=r["status"],
                       best_crawl_id="", shared_runs=0, in_crawl="unreadable", pages=r.get("pages", ""), text_chars=r.get("text_chars", ""))
            if r["status"] == "ok":
                cid, n = best_match(index, r["text"])
                row.update(best_crawl_id=cid if cid is not None else "", shared_runs=n, in_crawl="yes" if n >= MIN_SHARED else "no")
            tally[row["in_crawl"]] += 1
            rows.append(row)
    with gzip.open(out_path, "wt", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(dict(tally), "of", len(rows))


if __name__ == "__main__":
    main(*sys.argv[1:4])
