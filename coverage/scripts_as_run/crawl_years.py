import gzip, json, glob, re, os
os.chdir("/home/user/recourse-sci-pool-data")
M="January|February|March|April|May|June|July|August|September|October|November|December"
D1=re.compile(rf"\b({M})\s+(\d{{1,2}})\s*,?\s*(20\d\d|19\d\d)\b",re.I)
D2=re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({M})\s*,?\s*(20\d\d|19\d\d)\b",re.I)
D3=re.compile(r"\b(\d{1,2})[./](\d{1,2})[./]((?:19|20)\d\d)\b")
out={}; src={"end-date":0,"head-year":0,"none":0}
for f in sorted(glob.glob("shards/*.jsonl.gz")):
    lo=int(os.path.basename(f)[:6])
    if lo<28000: continue
    for l in gzip.open(f,"rt",encoding="utf-8"):
        r=json.loads(l)
        if r["status"]!="ok": continue
        t=r["text"]; tail=t[-900:]
        ys=[int(m.group(3)) for m in D1.finditer(tail)]+[int(m.group(3)) for m in D2.finditer(tail)]
        if ys: out[r["id"]]=ys[-1]; src["end-date"]+=1; continue
        ys=[int(m.group(3)) for m in D3.finditer(tail)]
        if ys: out[r["id"]]=ys[-1]; src["end-date"]+=1; continue
        ys=[int(y) for y in re.findall(r"\b(20[01]\d)\b",t[:1500])]
        if ys: out[r["id"]]=max(ys); src["head-year"]+=1
        else: src["none"]+=1
json.dump(out,open("/tmp/claude-0/-home-user-recourse-sci-pool/33686f69-1895-5643-b31d-21bed3d4a6ee/scratchpad/crawl_years.json","w"))
print("done",len(out),src)
