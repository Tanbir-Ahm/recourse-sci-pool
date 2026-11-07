"""In ONE process: the classic in-memory service and the SCI_STORE service on the same real index; everything the service can be asked is compared."""
import sys, os, glob, time, random, zlib, json, re
idx, commit, sidedir, names, storepath = sys.argv[1:6]
repo="/home/user/recourse-sci-pool"; sys.path.insert(0,repo); os.chdir(repo)
os.environ.update(SCI_INDEX_COMMIT=commit, SCI_NAMES_TABLE=os.path.join(repo,"names_table",names), SCI_STORE_PATH=storepath)
import numpy as np, sci_search_service as S
sides=sorted(glob.glob(os.path.join(repo,"review_data",sidedir,"*/")))
os.environ.pop("SCI_STORE",None)
t=time.time(); A=S.SearchService.load(idx, side_dirs=sides, client=object()); print(f"classic loaded {time.time()-t:.0f}s", flush=True)
os.environ["SCI_STORE"]="on"
t=time.time(); B=S.SearchService.load(idx, side_dirs=sides, client=object()); print(f"lean loaded {time.time()-t:.0f}s  store={B.info.get('store')}", flush=True)
n=len(A.metas); res={}
res["same passage count"]= n==len(B.metas)==A.M.shape[0]==B.M.shape[0]
res["vectors identical"]= np.array_equal(A.M,B.M)
bad=0; badtext=0
for i in range(n):
    a=A.metas[i]; b=B.metas[i]
    if {k:v for k,v in a.items() if k!="text"}!=b: bad+=1
    if a["text"]!=B._text(i): badtext+=1
res["rows with different fields (of %d)"%n]=bad
res["rows with different text (of %d)"%n]=badtext
ia={k:v for k,v in A.info.items() if k not in("load_seconds","store")}; ib={k:v for k,v in B.info.items() if k not in("load_seconds","store")}
res["info identical"]= ia==ib
res["header_docs identical"]= A.header_docs==B.header_docs
docs=sorted({m["doc"] for m in A.metas})
res["titles identical for all %d docs"%len(docs)]= all(A.title(d)==B.title(d) for d in docs)
res["court masks identical"]= all(np.array_equal(A.court_mask(c),B.court_mask(c)) for c in ("sc","hc"))
res["rows_by_doc identical"]= A.rows_by_doc()==B.rows_by_doc()
if os.environ.get("SCI_QUOTES")=="on": res["SCI_QUOTES marks identical (%d flagged)"%len(A.quotes)]= A.quotes==B.quotes and len(A.quotes)>0 and A.info.get("quotes")==B.info.get("quotes")
if os.environ.get("SCI_AUTHORITY")=="on": res["SCI_AUTHORITY table loaded in both"]= A.authority is not None and B.authority is not None
# keyword index: raw rowids for 300 queries (ties included)
rng=random.Random(5); kwbad=0; kwn=0
for _ in range(300):
    r=rng.randrange(n); words=[w for w in re.findall(r"[A-Za-z0-9]{4,}", A.metas[r]["text"].lower())][:40]
    toks=rng.sample(words, min(len(words), rng.randint(1,8))) if words else []
    if not toks: continue
    q=" OR ".join(f'"{t}"' for t in toks); kwn+=1
    ra=[x[0] for x in A.fts.execute("select rowid from f where f match ? order by bm25(f) limit 50",(q,))]
    rb=[x[0] for x in B.fts.execute("select rowid from f where f match ? order by bm25(f) limit 50",(q,))]
    if ra!=rb: kwbad+=1
res["keyword queries with a different rowid list (of %d)"%kwn]=kwbad
# retrieve + full search with stand-ins for Voyage
cur={}
class R: pass
class Cl:
    def embed(self, texts, **k):
        r=R(); r.embeddings=[cur["v"].tolist()]; r.total_tokens=1; return r
    def rerank(self, query, docs, model, top_k):
        r=R(); sc=[(zlib.crc32(d.encode("utf-8","surrogatepass"))%1000)/1000.0 + 0.001*len(set(re.findall(r"[a-z]{4,}",d.lower())) & set(re.findall(r"[a-z]{4,}",query.lower()))) for d in docs]
        order=sorted(range(len(docs)), key=lambda i:-sc[i])[:top_k]
        r.results=[type("X",(),{"index":i,"relevance_score":sc[i]})() for i in order]; r.total_tokens=len(docs)*100; return r
A.client=Cl(); B.client=Cl(); A.sleep=B.sleep=lambda s:None
qs=[]
for r in rng.sample(range(n),120):
    v=A.M[r].astype(np.float32); v/=np.linalg.norm(v); qs.append((v," ".join(A.metas[r]["text"].split()[:12])))
for _ in range(30):
    v=np.random.default_rng(rng.randrange(10**6)).normal(size=1024).astype(np.float32); v/=np.linalg.norm(v)
    qs.append((v, rng.choice(["section 438 anticipatory bail custody","section 17 prevention of corruption act proviso","section 482 quash FIR settlement","dowry death section 304B presumption","section 138 negotiable instruments cheque"])))
rb=0; sb=0; m=0
for v,txt in qs:
    cur["v"]=v
    for court in (None,"sc","hc"):
        a=A.retrieve(txt, 60, A.court_mask(court)); b=B.retrieve(txt, 60, B.court_mask(court))
        rb += (a["cand"]!=b["cand"] or a["nums"]!=b["nums"]); m+=1
for v,txt in qs[:60]:
    cur["v"]=v
    for court in (None,"sc","hc"):
        a=A.search(txt, 10, court=court); b=B.search(txt, 10, court=court)
        for d in (a,b):
            for k in ("seconds",): d.pop(k,None)
        sb += (json.dumps(a,sort_keys=True,default=str)!=json.dumps(b,sort_keys=True,default=str))
res["retrieve() candidate lists different (of %d, incl. court filters)"%m]=rb
res["search() full replies different (of 180: rank, score, text, names, links)"]=sb
for k,v in res.items(): print(("OK  " if (v is True or v==0) else "BAD ")+k+": "+str(v))
