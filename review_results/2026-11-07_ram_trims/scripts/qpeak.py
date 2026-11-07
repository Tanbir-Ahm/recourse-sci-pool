import sys, os, glob, time
blk=sys.argv[1]
repo="/home/user/recourse-sci-pool"; sys.path.insert(0,repo); os.chdir(repo)
os.environ.update(SCI_INDEX_COMMIT="d8811a910c73b0159bea7bcf3183ea258120db5b", SCI_NAMES_TABLE=os.path.join(repo,"names_table","names_table_d8811a9.json.gz"), SCI_SIM_BLOCK=blk)
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
svc.client=C(); rng=np.random.default_rng(2)
after_load=(round(st("VmRSS")), round(st("VmHWM")))
t=time.time()
for i in range(30):
    v=rng.normal(size=1024).astype(np.float32); cur["v"]=v/np.linalg.norm(v); svc.retrieve("bail anticipatory arrest custody", pool=60)
print(f"block {blk}: after load RSS/peak {after_load}; after 30 searches RSS {st('VmRSS'):.0f} peak {st('VmHWM'):.0f}; {(time.time()-t)/30:.2f}s per retrieve")
