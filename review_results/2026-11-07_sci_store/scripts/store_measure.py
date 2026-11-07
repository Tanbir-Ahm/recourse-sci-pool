import sys, os, glob, time, json
which, idx, commit, sidedir, names, storepath = sys.argv[1:7]
repo="/home/user/recourse-sci-pool"; sys.path.insert(0,repo); os.chdir(repo)
os.environ.update(SCI_INDEX_COMMIT=commit, SCI_NAMES_TABLE=os.path.join(repo,"names_table",names), SCI_STORE_PATH=storepath)
if which=="lean": os.environ["SCI_STORE"]="on"
def st(k):
    for l in open('/proc/self/status'):
        if l.startswith(k+':'): return int(l.split()[1])/1024
import sci_search_service as S
sides=sorted(glob.glob(os.path.join(repo,"review_data",sidedir,"*/")))
t=time.time(); svc=S.SearchService.load(idx, side_dirs=sides, client=object()); dt=time.time()-t
print(f"{which}: load {dt:.1f}s  RSS after {st('VmRSS'):.0f} MB  peak {st('VmHWM'):.0f} MB  store={svc.info.get('store')}")
print(S.startup_line(svc,'h',1)[:260])
