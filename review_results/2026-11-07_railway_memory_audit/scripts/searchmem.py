"""Phase-by-phase memory of the search service's OWN loader on the real newer index (read-only)."""
import sys, os, time, gc, glob, gzip, json, threading
repo, idx, commit = "/home/user/recourse-sci-pool", sys.argv[1], sys.argv[2]
sys.path.insert(0, repo); os.chdir(repo)
os.environ["SCI_INDEX_COMMIT"] = commit
os.environ["SCI_NAMES_TABLE"] = os.path.join(repo, "names_table", "names_table_d8811a9.json.gz") if commit.startswith("d8811a9") else os.path.join(repo, "names_table", "names_table.json.gz")
def st(k):
    for l in open('/proc/self/status'):
        if l.startswith(k+':'): return int(l.split()[1])/1024
peak = {"max": 0}
def watch():
    while True:
        peak["max"] = max(peak["max"], st('VmRSS')); time.sleep(0.05)
threading.Thread(target=watch, daemon=True).start()
import numpy as np
import sci_search_service as S, sci_index as si
print(f"python+numpy+modules baseline: {st('VmRSS'):.0f} MB")
def phase(name, fn):
    gc.collect(); a=st('VmRSS'); t=time.time(); r=fn(); gc.collect(); b=st('VmRSS')
    print(f"{name:52s} +{b-a:7.0f} MB  total {b:7.0f}  watcher-peak {peak['max']:7.0f}  {time.time()-t:5.1f}s", flush=True); return r
sides = sorted(glob.glob(os.path.join(repo, "review_data", "side_index_d8811a9" if commit.startswith("d8811a9") else "side_index", "*/")))
metas, M, _ = phase("1. si._load_index: np.load shards + np.vstack + meta rows", lambda: si._load_index(idx))
print(f"   passages {len(metas):,}  M {M.dtype} {M.shape} = {M.nbytes/1e6:.0f} MB; text chars {sum(len(m['text']) for m in metas)/1e6:.0f} M")
metas = phase("2. _slim (drop 4 fields)", lambda: [S._slim(m) for m in metas])
fts = phase("3. build_fts (in-memory sqlite FTS5, contentless)", lambda: S.build_fts(metas))
tt = phase("4. _title_table + _src_courts (docs.jsonl.gz parsed again)", lambda: (S._title_table([idx]), S._src_courts([idx]+sides)))
def names():
    p = os.environ["SCI_NAMES_TABLE"]
    with gzip.open(p, "rt", encoding="utf-8") as fh: nd = json.load(fh)
    return {r["doc"]: r for r in nd["rows"]}
nm = phase("5. names table", names)
print("   (side indexes: tiny, 2,607 passages; their vstack copies M once more: transient +%.0f MB)" % (M.nbytes/1e6))
print(f"FINAL {st('VmRSS'):.0f} MB   HIGH-WATER (kernel VmHWM) {st('VmHWM'):.0f} MB")
