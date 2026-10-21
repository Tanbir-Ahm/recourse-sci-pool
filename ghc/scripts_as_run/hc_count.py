import requests,re,sys,collections
B="https://indian-high-court-judgments.s3.ap-south-1.amazonaws.com"
def count(prefix):
    n=0;size=0;tok=None;ex=None;benches=collections.Counter()
    while True:
        p={"list-type":"2","prefix":prefix,"max-keys":"1000"}
        if tok: p["continuation-token"]=tok
        t=requests.get(B,params=p,timeout=60).text
        keys=re.findall(r"<Key>([^<]*)</Key>",t); szs=re.findall(r"<Size>(\d+)</Size>",t)
        n+=len(keys); size+=sum(map(int,szs))
        for k in keys:
            m=re.search(r"bench=([^/]+)/",k); benches[m.group(1) if m else '?']+=1
        if keys and ex is None: ex=keys[0]
        if "<IsTruncated>true" in t: tok=re.search(r"<NextContinuationToken>([^<]*)<",t).group(1)
        else: break
    return n,size,ex,benches
tot=0;totsz=0;allb=collections.Counter()
for y in range(int(sys.argv[1]),int(sys.argv[2])+1):
    n,s,ex,b=count(f"data/pdf/year={y}/court=18_6/")
    tot+=n;totsz+=s;allb.update(b)
    if n: print(y,n,round(s/1e6,1),"MB",ex if y in (int(sys.argv[1]),) else "")
print("TOTAL",tot,round(totsz/1e9,2),"GB",dict(allb))
