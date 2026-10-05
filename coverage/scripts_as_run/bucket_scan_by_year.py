import pyarrow.parquet as pq, requests, re, os, random, gzip, json, collections, statistics
import pymupdf as fitz
S="/tmp/claude-0/-home-user-recourse-sci-pool/33686f69-1895-5643-b31d-21bed3d4a6ee/scratchpad"
B="https://indian-supreme-court-judgments.s3.ap-south-1.amazonaws.com/%s"
M="https://indian-supreme-court-judgments.s3.ap-south-1.amazonaws.com/metadata/parquet/year=%d/metadata.parquet"
tok=lambda s: re.findall(r"[a-z]{3,}", s.lower())
voc=collections.Counter(); held=[]
for l in gzip.open(f"{S}/heads.jsonl.gz","rt",encoding="utf-8"):
    r=json.loads(l)
    if r["id"]%2==0: voc.update(tok(r["head"]))
    elif len(held)<400: held.append(r["head"])
V={w for w,c in voc.items() if c>=30}
oov=lambda t:(lambda ts: sum(w not in V for w in ts)/max(len(ts),1))(tok(t))
base=statistics.median(oov(h) for h in held)
print(f"baseline: held-out crawl text, first 3,500 characters: OOV {base:.3f}\n")
random.seed(9)
def fetch_meta(y):
    p=f"meta_{y}.parquet"
    if not os.path.exists(p): open(p,'wb').write(requests.get(M%y,timeout=60).content)
    return pq.read_table(p).to_pylist()
print(f"{'year':>5}{'PDFs':>5}{'pages':>6}{'scan pages':>11}{'scanned PDFs':>13}{'OOV (first 3.5k chars) median':>31}")
res={}
for y in (2012,2014,2016,2017,2018,2020,2022,2024):
    rows=[r for r in fetch_meta(y) if r.get('path')]
    smp=random.sample(rows,8); st=[]
    for r in smp:
        fn=f"pdfs/{y}_{r['path']}.pdf"
        if not os.path.exists(fn):
            try:
                resp=requests.get(B%f"data/pdf/year={y}/english/{r['path']}_EN.pdf",timeout=90)
                if resp.status_code!=200: continue
                open(fn,'wb').write(resp.content)
            except Exception: continue
        doc=fitz.open(fn); txt="".join(p.get_text() for p in doc)
        imgp=sum(1 for p in doc if p.get_images())
        st.append((len(doc),imgp,oov(re.sub(r"\s+"," ",txt)[:3500])))
    if st:
        res[y]=st
        print(f"{y:>5}{len(st):>5}{sum(s[0] for s in st):>6}{sum(s[1] for s in st):>11}{sum(1 for s in st if s[1]>=0.5*s[0]):>13}{statistics.median(s[2] for s in st):>31.3f}")
# what does a scanned page's text layer look like?
for fn in sorted(os.listdir("pdfs")):
    if fn.startswith("2017_"):
        doc=fitz.open("pdfs/"+fn)
        if sum(1 for p in doc if p.get_images())>=len(doc)*0.5:
            p=doc[1]; print("\nscanned 2017 PDF",fn,"| fonts on page 2:",[f[3] for f in p.get_fonts()][:3],"| images:",len(p.get_images()))
            print(re.sub(r"[ \t]+"," ",p.get_text())[:700]); break
