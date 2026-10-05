"""Decides, from the texts, which of the bucket's "none" judgments (dated up to 4 May 2017, not matched to the crawl by names) the crawl really holds.

For every saved bucket record of scope "none" it counts how many 8-word runs the bucket text shares with the opening (first 3,500
characters) of each crawled text, and divides by the number of runs in that crawled opening (`frac`). Runs found in more than 20
crawled openings are court boilerplate and are ignored.

The cut-offs were set on the full run, not on the earlier sample: a raw count of 50 shared runs let in different judgments that quote the
same passages (their party names and dates differ). By `frac`, matches whose crawl text carries the same decision date: 0.00 to 0.2 about 3%
(not the same judgment), 0.2 to 0.3 about 48% (uncertain), 0.3 and above about 80 to 91% (the rest differ only by a mistyped date or name).
So: frac >= 0.3 is "yes", 0.2 to 0.3 is "uncertain", under 0.2 is "no".

Usage: python resolve_none.py BUCKET_DATA_DIR CRAWL_DATA_DIR OUT.csv.gz
  BUCKET_DATA_DIR  checkout of branch claude/sci-bucket (shards/none-*.jsonl.gz)
  CRAWL_DATA_DIR   checkout of branch claude/sci-pool (shards/*.jsonl.gz)
Writes one row per bucket judgment: path, title, decision_date, key, status, best crawl id, shared runs, frac, and "in_crawl" (yes / uncertain / no / unreadable).
"""
import collections, csv, glob, gzip, json, re, sys
from array import array
import numpy as np

HEAD_CHARS, YES_FRAC, MAYBE_FRAC, MAX_DOCS_PER_RUN = 3500, 0.3, 0.2, 20
W = lambda s: re.findall(r"[a-z0-9]+", s.lower())


def runs(text, n=8):
    ws = W(text)
    return {hash(" ".join(ws[i:i + n])) for i in range(max(len(ws) - n + 1, 0))}


def build_index(crawl_dir):
    hs, ids, nruns = array("q"), array("i"), {}
    for f in sorted(glob.glob(f"{crawl_dir}/shards/*.jsonl.gz")):
        for line in gzip.open(f, "rt", encoding="utf-8"):
            r = json.loads(line)
            if r.get("status") != "ok":
                continue
            h = runs(r["text"][:HEAD_CHARS])
            nruns[r["id"]] = max(len(h), 1)
            hs.extend(h)
            ids.extend([r["id"]] * len(h))
    H = np.frombuffer(hs, dtype=np.int64)
    I = np.frombuffer(ids, dtype=np.int32)
    order = np.argsort(H, kind="stable")
    return H[order], I[order], nruns


def best_match(index, text):
    """(best crawl id, number of shared runs, shared runs / runs in that crawled opening) or (None, 0, 0.0)."""
    H, I, nruns = index
    b = np.array(sorted(runs(text)), dtype=np.int64)
    if not len(b):
        return None, 0, 0.0
    lo, hi = np.searchsorted(H, b, "left"), np.searchsorted(H, b, "right")
    keep = (hi > lo) & (hi - lo <= MAX_DOCS_PER_RUN)
    found = [I[a:z] for a, z in zip(lo[keep], hi[keep])]
    if not found:
        return None, 0, 0.0
    c = collections.Counter(np.concatenate(found).tolist())
    cid, n = c.most_common(1)[0]
    return cid, n, round(n / nruns[cid], 3)


def main(bucket_dir, crawl_dir, out_path):
    index = build_index(crawl_dir)
    print("crawl runs indexed:", len(index[0]), file=sys.stderr)
    rows, tally = [], collections.Counter()
    for f in sorted(glob.glob(f"{bucket_dir}/shards/none-*.jsonl.gz")):
        for line in gzip.open(f, "rt", encoding="utf-8"):
            r = json.loads(line)
            row = dict(path=r.get("path"), title=r.get("title"), decision_date=r.get("decision_date"), key=r.get("key"), status=r["status"],
                       best_crawl_id="", shared_runs=0, frac=0.0, in_crawl="unreadable", pages=r.get("pages", ""), text_chars=r.get("text_chars", ""))
            if r["status"] == "ok":
                cid, n, frac = best_match(index, r["text"])
                row.update(best_crawl_id=cid if cid is not None else "", shared_runs=n, frac=frac,
                           in_crawl="yes" if frac >= YES_FRAC else "uncertain" if frac >= MAYBE_FRAC else "no")
            tally[row["in_crawl"]] += 1
            rows.append(row)
    with gzip.open(out_path, "wt", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(dict(tally), "of", len(rows))


if __name__ == "__main__":
    main(*sys.argv[1:4])
