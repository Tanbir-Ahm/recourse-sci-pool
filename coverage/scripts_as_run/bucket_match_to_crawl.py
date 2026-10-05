import gzip, json, re, os, glob, collections, statistics
import pymupdf as fitz
S="/tmp/claude-0/-home-user-recourse-sci-pool/33686f69-1895-5643-b31d-21bed3d4a6ee/scratchpad"
W=lambda s: re.findall(r"[a-z0-9]+", s.lower())
def shingles(ws,n=8): return {hash(" ".join(ws[i:i+n])) for i in range(max(len(ws)-n+1,0))}
bucket={}
for f in sorted(glob.glob("pdfs/201[0-7]_*.pdf")):
    doc=fitz.open(f)
    if not all(p.get_images() for p in list(doc)[:3]): continue          # scanned-regime PDFs only
    txt="".join(p.get_text() for p in doc); bucket[f]=txt
print("scanned-regime bucket PDFs from 2012-2017 available:",len(bucket))
bsh={f:shingles(W(t)) for f,t in bucket.items()}
allb=set().union(*bsh.values())
hits=collections.defaultdict(lambda: collections.Counter())
for l in gzip.open(f"{S}/heads.jsonl.gz","rt",encoding="utf-8"):
    r=json.loads(l); sh=shingles(W(r["head"]))
    x=sh & allb
    if len(x)>=8:
        for f,b in bsh.items():
            c=len(x & b)
            if c>=8: hits[f][r["id"]]=c
match={f:c.most_common(1)[0] for f,c in hits.items()}
print("bucket PDFs that also exist in the crawl:",len(match),"->",{os.path.basename(f)[:14]:v for f,v in match.items()})
json.dump({f:v for f,v in match.items()},open("matches.json","w"))
