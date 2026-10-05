"""Second validation step, saved as run on 2026-10-05 (it was run inline). Re-reads the sampled bucket PDFs (caching their text), and for each
counts how many 8-word runs it shares with every crawled text's opening; the best match's count separates real matches (about 135 to 470
shared runs) from non-matches (under 35). Writes validation_counts.json."""
import json, collections, gzip, re, sys, urllib.request, urllib.parse, concurrent.futures as cf, os
import pandas as pd, pymupdf as fitz
S="/tmp/claude-0/-home-user-recourse-sci-pool/33686f69-1895-5643-b31d-21bed3d4a6ee/scratchpad"
HOST="https://indian-supreme-court-judgments.s3.ap-south-1.amazonaws.com/"
reg=pd.read_csv("registry.csv",dtype={"crawl_ids":str}).fillna({"crawl_ids":""})
rows=json.load(open("validation.json"))
table={r["id"]:r for r in json.load(open(f"{S}/crawl_table.json"))}
def get(r):
    i=r["i"]; p=f"texts/{i}.txt"
    if os.path.exists(p): return open(p).read()
    data=urllib.request.urlopen(HOST+urllib.parse.quote(reg.loc[i,"key"]),timeout=120).read()
    t="".join(pg.get_text() for pg in fitz.open(stream=data,filetype="pdf")); open(p,"w").write(t); return t
W=lambda s: re.findall(r"[a-z0-9]+", s.lower())
sh=lambda ws,n=8: {hash(" ".join(ws[i:i+n])) for i in range(max(len(ws)-n+1,0))}
heads={}; hs={}
for l in gzip.open(f"{S}/heads.jsonl.gz","rt",encoding="utf-8"):
    r=json.loads(l); heads[r["id"]]=r["head"]; hs[r["id"]]=sh(W(r["head"]))
cr=collections.defaultdict(set)
for cid,s in hs.items():
    for h in s: cr[h].add(cid)
ok=[r for r in rows if r["ok"]]
with cf.ThreadPoolExecutor(8) as ex: texts=list(ex.map(get,ok))
out=[]
for r,t in zip(ok,texts):
    b=sh(W(t)); hit=collections.Counter()
    for h in b:
        for cid in cr.get(h,()): hit[cid]+=1
    top=hit.most_common(3)
    best=top[0] if top else (None,0)
    frac=best[1]/max(len(hs[best[0]]),1) if best[0] else 0
    out.append(dict(tier=r["tier"],i=r["i"],best=best[0],n=best[1],frac=round(frac,2),second=top[1][1] if len(top)>1 else 0))
json.dump(out,open("validation_counts.json","w"))
