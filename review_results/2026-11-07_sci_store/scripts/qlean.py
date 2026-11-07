import sys, os, glob, time, re, zlib
mode=sys.argv[1]
repo="/home/user/recourse-sci-pool"; sys.path.insert(0,repo); os.chdir(repo)
os.environ.update(SCI_INDEX_COMMIT="d8811a910c73b0159bea7bcf3183ea258120db5b", SCI_NAMES_TABLE=os.path.join(repo,"names_table","names_table_d8811a9.json.gz"), SCI_STORE_PATH="/home/user/audit_idx/store_new.sqlite")
if mode=="lean": os.environ["SCI_STORE"]="on"
import numpy as np, sci_search_service as S
def st(k):
    for l in open('/proc/self/status'):
        if l.startswith(k+':'): return int(l.split()[1])/1024
sides=sorted(glob.glob(os.path.join(repo,"review_data","side_index_d8811a9","*/")))
svc=S.SearchService.load("/home/user/audit_idx/new", side_dirs=sides, client=object())
cur={}
class R: pass
class C:
    def embed(self, texts, **k):
        r=R(); r.embeddings=[cur["v"].tolist()]; r.total_tokens=1; return r
    def rerank(self, query, docs, model, top_k):
        r=R(); sc=[(zlib.crc32(d.encode())%1000)/1000 for d in docs]; o=sorted(range(len(docs)),key=lambda i:-sc[i])[:top_k]
        r.results=[type("X",(),{"index":i,"relevance_score":sc[i]})() for i in o]; r.total_tokens=len(docs)*50; return r
svc.client=C(); svc.sleep=lambda s:None; rng=np.random.default_rng(4)
a=(round(st("VmRSS")),round(st("VmHWM")))
t=time.time()
for i in range(30):
    v=rng.normal(size=1024).astype(np.float32); cur["v"]=v/np.linalg.norm(v); svc.retrieve("bail anticipatory arrest custody section 438", pool=60)
tr=(time.time()-t)/30; t=time.time()
for i in range(20):
    v=rng.normal(size=1024).astype(np.float32); cur["v"]=v/np.linalg.norm(v); svc.search("bail anticipatory arrest custody section 438", 10)
ts=(time.time()-t)/20
print(f"{mode}: after load {a}; after 30 retrieves + 20 searches RSS {st('VmRSS'):.0f} peak {st('VmHWM'):.0f}; retrieve {tr*1000:.0f} ms, whole search (stub rerank) {ts*1000:.0f} ms")
