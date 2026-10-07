"""Rough completeness check for the 'overruled after 2015' list: scan post-2015 judgments of 3+ judges for operative-sounding 'overruled' sentences naming a case. Read-only."""
import sys, re, json, sqlite3
sys.path.insert(0, "/home/user/recourse-sci-pool")
from goodlaw import corpus as K, textutil as X
SP = "/tmp/claude-0/-home-user-recourse-sci-pool/33686f69-1895-5643-b31d-21bed3d4a6ee/scratchpad/"
C = K.Corpus(SP + "corpus.sqlite")
con = C.con
LISTED = set("""b2017_10_569_999 c44452 b2017_13_1009_1052 b2018_7_1191_1231 b2018_7_379_746 b2018_11_765_950 b2019_15_795_864 b2019_4_928_944 b2019_15_936_989 b2019_11_74_134 b2020_2_1_131 b2020_7_180_282 b2020_9_245_302 b2020_10_135_237 b2020_11_1001_1180 b2021_12_311_364 b2021_3_193_254 b2020_3_1_328 b2023_1_919_924 b2023_8_496_580 b2019_17_1013_1047 b2024_11_1647_2038 b2024_8_1321_1672 b2024_7_1549_1846 b2024_10_1931_2182 b2024_2_946_988 b2024_11_541_640 b2023_9_285_492 b2025_2_1331_1395""".split())
OP = re.compile(r"(?:\b(?:is|are|stands?|stood|hereby|accordingly|therefore|also|specifically|expressly|must be|needs to be)\b[^.;]{0,90}\boverrul(?:ed|ing)\b|\bwe\s+(?:\w+\s+){0,3}overrule\b|\bis\s+not\s+good\s+law\b|\bnot\s+lay\s+down\s+(?:the\s+)?(?:correct|good)\s+law\b|\bstand\s+overruled\b)", re.I)
NEG = re.compile(r"objection|contention|plea|submission|prayer|application|learned|counsel|urged|argued|\bwould\b|\bif\b|\bmay be overruled|needs? to be overruled by|referred|reference", re.I)
CITE = re.compile(r"\bv\.?\s+\w|\bvs\.?\s+\w|\bsupra\b|\(supra\)|SCC", re.I)
rows = con.execute("select doc_key,title,date,bench_size,year from docs where dup_of is null and year>=2016 and bench_size>=3 order by date").fetchall()
print("candidate judgments (2016+, 3+ judges):", len(rows))
out = []
for k, title, date, bs, yr in rows:
    if k in LISTED: continue
    d = C.get(k); t = X.flatten(d["text"]); st = int(d.get("body_start") or 0)
    body = t[st:] if st else t[len(t)//8:]
    hits = []
    for s in re.split(r"(?<=[.;])\s+", body):
        if OP.search(s) and CITE.search(s) and not NEG.search(s) and len(s) < 600:
            hits.append(re.sub(r"\s+", " ", s))
    if hits:
        out.append((k, title, date, bs, hits))
print("judgments not in the list with at least one operative-sounding sentence:", len(out))
json.dump(out, open(SP + "pdf2_in/completeness_hits.json", "w"), ensure_ascii=False, indent=0)
for k, title, date, bs, hits in out[:60]:
    print(f"- {k} {date} b{bs} {title[:70]} | {len(hits)} | {hits[0][:260]}")
