import sys, os, json, glob, hashlib, time
which, idx, commit, sidedir, names, out = sys.argv[1:7]
repo="/home/user/recourse-sci-pool"; sys.path.insert(0,repo); os.chdir(repo)
os.environ["SCI_INDEX_COMMIT"]=commit; os.environ["SCI_NAMES_TABLE"]=os.path.join(repo,"names_table",names)
if which=="old": os.environ["SCI_LOAD_COPY"]="on"
import numpy as np, sci_search_service as S
def st(k):
    for l in open('/proc/self/status'):
        if l.startswith(k+':'): return int(l.split()[1])/1024
sides=sorted(glob.glob(os.path.join(repo,"review_data",sidedir,"*/")))
t=time.time(); svc=S.SearchService.load(idx, side_dirs=sides, client=object()); dt=time.time()-t
rss_after, peak_after = round(st("VmRSS")), round(st("VmHWM"))
M=svc.M; h=hashlib.sha256()
for i in range(0,len(M),20000): h.update(np.ascontiguousarray(M[i:i+20000]).tobytes())
mh=hashlib.sha256(json.dumps(svc.metas, sort_keys=True, default=str).encode()).hexdigest()
info={k:v for k,v in svc.info.items() if k!="load_seconds"}
fts=svc.fts.execute("select count(*) from f_docsize").fetchone()[0]
r={"which":which,"dtype":str(M.dtype),"shape":list(M.shape),"M_sha256":h.hexdigest(),"metas_n":len(svc.metas),"metas_sha256":mh,"info_sha256":hashlib.sha256(json.dumps(info,sort_keys=True,default=str).encode()).hexdigest(),"fts_rows":fts,
   "rss_after_load_mb":rss_after,"peak_during_load_mb":peak_after,"load_s":round(dt,1)}
json.dump(r,open(out,"w")); print(r)
