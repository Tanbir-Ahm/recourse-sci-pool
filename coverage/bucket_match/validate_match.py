"""Checks the metadata-only matching against the actual texts. Samples bucket judgments from each tier, downloads those PDFs
(a few hundred, ~0.4 MB each), extracts text, and looks for the same judgment in the crawl by shared 8-word runs
(same rule as bucket_match_to_crawl.py: >= 8 shared runs between the crawled text's first 3,500 characters and the bucket text).
Compares the text-based answer with the tier's answer."""
import collections, concurrent.futures as cf, gzip, json, random, re, sys, urllib.request
import pandas as pd
import pymupdf as fitz

S = "/tmp/claude-0/-home-user-recourse-sci-pool/33686f69-1895-5643-b31d-21bed3d4a6ee/scratchpad"
HOST = "https://indian-supreme-court-judgments.s3.ap-south-1.amazonaws.com/"
reg = pd.read_csv("registry.csv", dtype={"crawl_ids": str}).fillna({"crawl_ids": ""})
random.seed(7)
plan = {"T1": 40, "T2": 20, "T3": 50, "T3x": 40, "none": 70}
pick = []
for tier, n in plan.items():
    sub = reg[(reg.tier == tier) & reg.key.notna()]
    pick += [(tier, i) for i in random.sample(list(sub.index), min(n, len(sub)))]
W = lambda s: re.findall(r"[a-z0-9]+", s.lower())
sh = lambda ws, n=8: {hash(" ".join(ws[i:i + n])) for i in range(max(len(ws) - n + 1, 0))}
cr = collections.defaultdict(set)      # shingle -> crawl ids
for l in gzip.open(f"{S}/heads.jsonl.gz", "rt", encoding="utf-8"):
    r = json.loads(l)
    for h in sh(W(r["head"])):
        cr[h].add(r["id"])
print("crawl shingles", len(cr), file=sys.stderr)


def fetch(item):
    tier, i = item
    k = reg.loc[i, "key"]
    try:
        data = urllib.request.urlopen(HOST + urllib.parse.quote(k), timeout=120).read()
        doc = fitz.open(stream=data, filetype="pdf")
        txt = "".join(p.get_text() for p in doc)
        return tier, i, txt
    except Exception as e:
        return tier, i, None


import urllib.parse
rows = []
with cf.ThreadPoolExecutor(8) as ex:
    for tier, i, txt in ex.map(fetch, pick):
        if txt is None:
            rows.append(dict(tier=tier, i=i, ok=False)); continue
        b = sh(W(txt))
        hit = collections.Counter()
        for h in b:
            for cid in cr.get(h, ()):
                hit[cid] += 1
        true_ids = {cid for cid, c in hit.items() if c >= 8}
        claimed = {int(x) for x in str(reg.loc[i, "crawl_ids"]).split(";") if x}
        rows.append(dict(tier=tier, i=i, ok=True, year=int(str(reg.loc[i, "decision_date"])[-4:]), claimed=sorted(claimed), true=sorted(true_ids), title=reg.loc[i, "title"][:70]))
json.dump(rows, open("validation.json", "w"))
for tier in plan:
    rs = [r for r in rows if r["tier"] == tier and r["ok"]]
    if tier == "none":
        found = sum(1 for r in rs if r["true"])
        print(f"{tier}: sampled {len(rs)}; text finds a crawl copy for {found} (false 'none')")
    else:
        agree = sum(1 for r in rs if set(r["claimed"]) & set(r["true"]))
        anytrue = sum(1 for r in rs if r["true"])
        print(f"{tier}: sampled {len(rs)}; claimed id confirmed by text {agree}; text finds some crawl copy {anytrue}; text finds none {len(rs)-anytrue}")
