"""Chunk-level quality indicators for Vaquill's English chunks, and the same indicators for OUR index passages as a baseline."""
import sys, re, collections, statistics, random
import numpy as np
import pyarrow.parquet as pq
sys.path.insert(0, "/home/user/recourse-sci-pool"); sys.path.insert(0, "/home/user/recourse-sci-pool/review_tools")
HDR = re.compile(r"\A(?:Case: [^\n]*\n)?(?:Section: [^\n]*\n)?\n?")
MARGIN = re.compile(r"(?m)^[A-H]$")                     # a lone margin letter on its own line
MARGIN_ANY = re.compile(r"(?m)^[A-Z]$")
RUNHEAD = re.compile(r"(?m)^(?:\d{1,4} )?SUPREME COURT REPORTS.*$|^\[\d{4}\] (?:SUPP\. )?\d+ S\.C\.R\.\s*$|^\[\d{4}\] \d+ S\.C\.R\. \d+\s*$")
TAG = re.compile(r"(?m)^\[[A-Z_]+\]")
TILDE = re.compile(r"~")
PARANO = re.compile(r"(?m)^\s*\d{1,3}\.\s")
SENT_END = re.compile(r"[.?!:;\"'”’)\]]\s*$")
def stats(texts, label):
    n = len(texts)
    out = collections.OrderedDict()
    body = [HDR.sub("", t, count=1) for t in texts]
    out["chunks"] = n
    out["mean chars (full)"] = round(sum(map(len, texts)) / n)
    out["header 'Case:' present"] = f"{sum(t.startswith('Case: ') for t in texts) / n:.1%}"
    out["[TAG] lines per chunk"] = round(sum(len(TAG.findall(t)) for t in body) / n, 2)
    out["chunks with a lone A-H margin letter line"] = f"{sum(bool(MARGIN.search(t)) for t in body) / n:.1%}"
    out["margin-letter lines per 10k chars"] = round(10000 * sum(len(MARGIN.findall(t)) for t in body) / sum(map(len, body)), 2)
    out["running-header lines per 10k chars"] = round(10000 * sum(len(RUNHEAD.findall(t)) for t in body) / sum(map(len, body)), 2)
    out["'~' per 10k chars"] = round(10000 * sum(len(TILDE.findall(t)) for t in body) / sum(map(len, body)), 2)
    out["chunks starting with lowercase letter"] = f"{sum(bool(b[:1].islower()) for b in body) / n:.1%}"
    out["chunks not ending at sentence end"] = f"{sum(not SENT_END.search(b) for b in body) / n:.1%}"
    out["paragraph-number lines per chunk"] = round(sum(len(PARANO.findall(b)) for b in body) / n, 2)
    return out
# Vaquill English chunks (all)
t = pq.read_table(sys.argv[1], columns=["case_id", "chunk_index", "text_original"]).to_pandas()
rnd = random.Random(7)
idx = rnd.sample(range(len(t)), 60000)
vt = [t.text_original.iat[i] for i in idx]
print("Vaquill English chunks (random 60,000 of %d)" % len(t))
for k, v in stats(vt, "vaquill").items(): print(f"  {k}: {v}")
ex = collections.Counter(HDR.search(x).group(0).split("\n")[1] if HDR.search(x) and "\n" in HDR.search(x).group(0) else "" for x in vt[:20000])
print("  'Section:' header values (20k sample):", dict(ex.most_common(8)))
# Ours
import sci_index as si
metas, M, _ = si._load_index("/home/user/recourse-sci-index")
ours = [m["text"] for m in rnd.sample(metas, 60000)]
print("\nOur passages (random 60,000 of %d)" % len(metas))
for k, v in stats(ours, "ours").items(): print(f"  {k}: {v}")
