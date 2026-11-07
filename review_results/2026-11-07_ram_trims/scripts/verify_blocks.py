import sys, os, glob, time, random
idx, commit, sidedir, names = sys.argv[1:5]
repo="/home/user/recourse-sci-pool"; sys.path.insert(0,repo); os.chdir(repo)
os.environ["SCI_INDEX_COMMIT"]=commit; os.environ["SCI_NAMES_TABLE"]=os.path.join(repo,"names_table",names)
import numpy as np, sci_search_service as S
sides=sorted(glob.glob(os.path.join(repo,"review_data",sidedir,"*/")))
svc=S.SearchService.load(idx, side_dirs=sides, client=object())
cur={"v":None}
class R: pass
class FakeClient:
    def embed(self, texts, **k):
        r=R(); r.embeddings=[cur["v"].tolist()]; r.total_tokens=1; return r
svc.client=FakeClient()
rng=np.random.default_rng(11); random.seed(11)
N=len(svc.M); rows=random.sample(range(N),150)
queries=[]
for r in rows:
    v=svc.M[r].astype(np.float32); words=" ".join(svc.metas[r]["text"].split()[:14])
    queries.append(("exact-passage-vector", v/np.linalg.norm(v), words))
    n=v+rng.normal(scale=0.02,size=v.shape).astype(np.float32); queries.append(("noised", n/np.linalg.norm(n), words))
for _ in range(50):
    v=rng.normal(size=1024).astype(np.float32); queries.append(("random", v/np.linalg.norm(v), "bail anticipatory arrest section 438 custody"))
res={}
for blk in ("50000","5000","1000"):
    os.environ["SCI_SIM_BLOCK"]=blk; out=[]; t=time.time()
    for kind,v,txt in queries:
        cur["v"]=v; r_=svc.retrieve(txt, pool=60); out.append((r_["cand"], r_["nums"]))
    res[blk]=(out, time.time()-t)
print("queries:", len(queries), " passages:", N)
base=res["50000"][0]
for blk in ("5000","1000"):
    diff=[i for i,(a,b) in enumerate(zip(base,res[blk][0])) if a!=b]
    kinds={}
    for i in diff: kinds[queries[i][0]]=kinds.get(queries[i][0],0)+1
    print(f"block {blk} vs 50000: candidate lists identical for {len(queries)-len(diff)} of {len(queries)}; differing: {kinds}   time {res[blk][1]:.1f}s (50000: {res['50000'][1]:.1f}s)")
# top-100 semantic order only
os.environ["SCI_SIM_BLOCK"]="50000"; ds=0; tot=0
for kind,v,txt in queries[:100]:
    qv=v
    s1=np.concatenate([svc.M[i:i+50000].astype(np.float32)@qv for i in range(0,N,50000)])
    s2=np.concatenate([svc.M[i:i+5000].astype(np.float32)@qv for i in range(0,N,5000)])
    tot+=1; ds+= (list(np.argsort(-s1)[:100])!=list(np.argsort(-s2)[:100])); 
print(f"top-100 semantic order differs in {ds} of {tot} (max score diff {np.abs(s1-s2).max():.2e} on the last)")
