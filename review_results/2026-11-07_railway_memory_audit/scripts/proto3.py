import sys, os, time, gc, sqlite3, glob, zlib, random
repo="/home/user/recourse-sci-pool"; idx="/home/user/audit_idx/new"; db="/home/user/audit_idx/proto/lean.sqlite"
sys.path.insert(0,repo); os.chdir(repo)
def st(k):
    for l in open('/proc/self/status'):
        if l.startswith(k+':'): return int(l.split()[1])/1024
def line(tag): print(f"{tag:58s} RSS {st('VmRSS'):6.0f}  anon {st('RssAnon'):6.0f}  file {st('RssFile'):6.0f}  peak {st('VmHWM'):6.0f}", flush=True)
import numpy as np, sci_index as si
mode=sys.argv[1]   # "ram" = float16 matrix in RAM without the vstack copy ; "mmap" = per-shard mmap
line("baseline")
led=si.ledger(idx); d=si._idx_dir(idx); shards=[led[s] for s in sorted(led) if led[s]["passages"]]
if mode=="ram":
    n=sum(s["passages"] for s in shards); M=np.empty((n,1024),dtype=np.float16); o=0
    for s in shards:
        a=np.load(os.path.join(d,s["base"]+".vec.npy")); M[o:o+len(a)]=a; o+=len(a); del a
    chunks=[M]
else:
    chunks=[np.load(os.path.join(d,s["base"]+".vec.npy"), mmap_mode="r") for s in shards]; n=sum(len(c) for c in chunks)
line(f"vectors loaded ({mode}), {n:,} x 1024 float16")
# on-disk text + keyword index, small page cache
c=sqlite3.connect("file:"+db+"?mode=ro", uri=True, check_same_thread=False); c.execute("pragma cache_size=-32768"); c.execute("pragma mmap_size=0")
line("sqlite opened read-only (32 MB page cache)")
q=np.random.default_rng(0).normal(size=1024).astype(np.float32); q/=np.linalg.norm(q)
def sims(step):
    out=[]
    for ch in chunks:
        for i in range(0,len(ch),step): out.append(ch[i:i+step].astype(np.float32) @ q)
    return np.concatenate(out)
t=time.time(); s=sims(50000); t1=time.time()-t; line(f"after 1 query, 50,000-row blocks ({t1:.2f}s)")
t=time.time(); s2=sims(5000); t2=time.time()-t; print(f"   5,000-row blocks: {t2:.2f}s; identical scores: {np.array_equal(s,s2)}")
line("after block test")
t=time.time()
for w in ["bail anticipatory","section 438 custody","circumstantial evidence conviction","disproportionate assets arrest"]:
    r=c.execute("select rowid from f where f match ? order by bm25(f) limit 50",(" OR ".join(w.split()),)).fetchall()
t3=(time.time()-t)/4
ids=random.sample(range(n),90); t=time.time()
txt=[zlib.decompress(c.execute("select z from t where id=?",(i,)).fetchone()[0]) for i in ids]; t4=time.time()-t
print(f"   FTS query from disk: {t3*1000:.0f} ms avg; fetch+decompress 90 texts: {t4*1000:.0f} ms")
line("after FTS + text fetches")
