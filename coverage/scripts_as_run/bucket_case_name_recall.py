import gzip, json, re, os, glob, statistics
import pymupdf as fitz
D="/home/user/recourse-sci-pool-data"
VS=re.compile(r"\b([A-Z][A-Za-z.\-']{2,}(?:\s+[A-Za-z.\-']{2,}){0,3})\s+(?:v\.?|vs\.?|versus)\s+([A-Z][A-Za-z.\-']{2,}(?:\s+[A-Za-z.\-']{2,}){0,3})")
sq=lambda s: re.sub(r"[^a-z0-9]","",s.lower())
match=json.load(open("matches.json"))
def crawl_text(i):
    f=glob.glob(f"{D}/shards/{i//250*250:06d}-*.jsonl.gz")[0]
    for l in gzip.open(f,"rt",encoding="utf-8"):
        r=json.loads(l)
        if r["id"]==i: return r["text"]
tot_c=hit_c=tot_b=hit_b=0; per=[]
for f,(cid,ov) in match.items():
    if ov<200: continue
    bt="".join(p.get_text() for p in fitz.open(f)); ct=crawl_text(cid)
    flat=lambda t: re.sub(r"\s+"," ",t)
    cnames={(m.group(1),m.group(2)) for m in VS.finditer(flat(ct))}; bnames={(m.group(1),m.group(2)) for m in VS.finditer(flat(bt))}
    bsq,csq=sq(bt),sq(ct)
    # a citation counts as found if the OTHER source contains the same two party-name starts, squeezed, in order and adjacent
    pat=lambda a,b: re.compile(re.escape(sq(a)[-10:])+r"(?:v|vs|versus)"+re.escape(sq(b)[:10]))
    found_c=sum(1 for a,b in cnames if pat(a,b).search(bsq))
    found_b=sum(1 for a,b in bnames if pat(a,b).search(csq))
    tot_c+=len(cnames); hit_c+=found_c; tot_b+=len(bnames); hit_b+=found_b
    if len(cnames)>=5: per.append(found_c/len(cnames))
print(f"case-name citations 'X v. Y' spotted in the crawl text: {tot_c}; of these also present in the bucket text: {hit_c} ({100*hit_c/tot_c:.0f}%)")
print(f"case-name citations spotted in the bucket text: {tot_b}; of these also present in the crawl text: {hit_b} ({100*hit_b/tot_b:.0f}%)")
print("per judgment (those with 5+ citations), share of crawl-spotted citations found in the bucket text: median",round(statistics.median(per),2),"| range",round(min(per),2),"to",round(max(per),2),f"| n={len(per)}")
