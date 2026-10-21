import requests,re,sys,collections
B="https://indian-high-court-judgments.s3.ap-south-1.amazonaws.com"
def sizes(prefix):
    out=[];tok=None
    while True:
        p={"list-type":"2","prefix":prefix,"max-keys":"1000"}
        if tok: p["continuation-token"]=tok
        t=requests.get(B,params=p,timeout=60).text
        out+=list(zip(re.findall(r"<Key>([^<]*)</Key>",t),map(int,re.findall(r"<Size>(\d+)</Size>",t))))
        if "<IsTruncated>true" in t: tok=re.search(r"<NextContinuationToken>([^<]*)<",t).group(1)
        else: return out
for y in sys.argv[1:]:
    s=sizes(f"data/pdf/year={y}/court=18_6/")
    z=sorted(x[1] for x in s)
    th=[10_000,30_000,100_000,300_000]
    print(y,len(s),'median KB',round(z[len(z)//2]/1000,1),'| >=',{t//1000:sum(v>=t for v in z) for t in th},'| biggest',round(z[-1]/1e6,2),'MB')
    if y==sys.argv[1]:
        big=sorted(s,key=lambda x:-x[1])
        open('/tmp/claude-0/hc_big.txt','w').write('\n'.join(f"{k}\t{v}" for k,v in big[:40]))
