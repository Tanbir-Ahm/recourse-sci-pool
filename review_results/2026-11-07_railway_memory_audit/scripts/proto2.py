import sys, os, time, gc, zlib, sqlite3, json, gzip
repo="/home/user/recourse-sci-pool"; idx="/home/user/audit_idx/new"; out="/home/user/audit_idx/proto"; os.makedirs(out, exist_ok=True)
sys.path.insert(0,repo); os.chdir(repo)
def st(k):
    for l in open('/proc/self/status'):
        if l.startswith(k+':'): return int(l.split()[1])/1024
import numpy as np
import sci_index as si, sci_search_service as S
metas, M, _ = si._load_index(idx)
n=len(metas)
texts=[m["text"] for m in metas]
t=time.time(); enc=[x.encode("utf-8") for x in texts]; blob_len=sum(map(len,enc))
print(f"utf-8 bytes total {blob_len/1e6:.0f} MB")
t=time.time(); comp=[zlib.compress(b,3) for b in enc]; cl=sum(map(len,comp))
print(f"zlib(3) per-passage total {cl/1e6:.0f} MB ({cl/blob_len:.0%}), {time.time()-t:.0f}s to build")
t=time.time()
for i in range(0,n,4600): zlib.decompress(comp[i])
print(f"decompress ~90 passages: {(time.time()-t)*1000:.1f} ms")
# --- on-disk text store + on-disk contentless FTS5 + on-disk keyword
p=os.path.join(out,"lean.sqlite")
if os.path.exists(p): os.remove(p)
c=sqlite3.connect(p)
c.execute("create table t(id integer primary key, z blob)")
c.executemany("insert into t values(?,?)", ((i,comp[i]) for i in range(n)))
c.execute("create virtual table f using fts5(text, content='', tokenize='porter unicode61')")
t=time.time()
c.executemany("insert into f(rowid,text) values(?,?)", ((i,texts[i]) for i in range(n)))
c.commit(); c.close()
print(f"on-disk sqlite (compressed text + contentless FTS5): {os.path.getsize(p)/1e6:.0f} MB, built in {time.time()-t:.0f}s")
