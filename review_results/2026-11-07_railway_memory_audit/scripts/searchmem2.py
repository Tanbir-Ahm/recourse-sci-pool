import sys, os, time, gc, glob
repo, idx, commit = "/home/user/recourse-sci-pool", "/home/user/audit_idx/new", "d8811a910c73b0159bea7bcf3183ea258120db5b"
sys.path.insert(0, repo); os.chdir(repo)
os.environ["SCI_INDEX_COMMIT"]=commit; os.environ["SCI_NAMES_TABLE"]=os.path.join(repo,"names_table","names_table_d8811a9.json.gz")
def st(k):
    for l in open('/proc/self/status'):
        if l.startswith(k+':'): return int(l.split()[1])/1024
import numpy as np, sci_search_service as S, authority_search as AS, sci_quotes
sides=sorted(glob.glob(os.path.join(repo,"review_data","side_index_d8811a9","*/")))
svc=S.SearchService.load(idx, side_dirs=sides, client=object())
gc.collect(); print(f"service loaded (no switches): RSS {st('VmRSS'):.0f} MB, VmHWM {st('VmHWM'):.0f}")
a=st('VmRSS'); svc.rows_by_doc(); gc.collect(); print(f"  rows_by_doc():                 +{st('VmRSS')-a:.0f} MB")
a=st('VmRSS'); svc.court_mask("hc"); svc.court_mask("sc"); gc.collect(); print(f"  court masks (hc+sc):           +{st('VmRSS')-a:.0f} MB")
a=st('VmRSS'); tab=AS.AuthorityTable.load(os.path.join(repo,"authority_table","authority_d8811a9.json.gz"), commit); gc.collect(); print(f"  SCI_AUTHORITY table:           +{st('VmRSS')-a:.0f} MB")
a=st('VmRSS'); q,stats=sci_quotes.build(svc.metas); gc.collect(); print(f"  SCI_QUOTES=on build:           +{st('VmRSS')-a:.0f} MB  ({len(q):,} flagged)")
print(f"FINAL RSS {st('VmRSS'):.0f} MB  VmHWM {st('VmHWM'):.0f}")
import ctypes
b=st('VmRSS'); ctypes.CDLL("libc.so.6").malloc_trim(0); gc.collect(); print(f"malloc_trim(0) after load: {b:.0f} -> {st('VmRSS'):.0f} MB (returns {b-st('VmRSS'):.0f} MB)")
