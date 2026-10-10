"""Extracts every Supreme Court point of one segment of a Qdrant shard snapshot: decoded payload (text kept) and float32 dense vector.
Args: scripts_dir url member_index.json out_prefix. Writes out_prefix + '_payload.jsonl.gz', '_vecs.npy' (float32, SC points only, same order), '_summary.json'. Read-only on the host."""
import sys, json, struct, gzip, time, collections, io
from concurrent.futures import ThreadPoolExecutor
import numpy as np
sys.path.insert(0, sys.argv[1])
import qd_read as Q
import lz4.block
url, idx_p, out = sys.argv[2], sys.argv[3], sys.argv[4]
raw = json.load(open(idx_p))
mem = {k: Q.Member(url, *v) for k, v in raw.items() if not k.startswith("payload_index/")}
def fetch(m, chunk=16 * 1024 * 1024, workers=8):
    """Whole apparent content of a member, downloaded in parallel blocks."""
    buf = bytearray(m.real)
    spans = [(a, min(a + chunk, m.real)) for a in range(0, m.real, chunk)]
    def one(sp):
        a, b = sp; buf[a:b] = m.read(a, b - a)
    with ThreadPoolExecutor(workers) as ex: list(ex.map(one, spans))
    return bytes(buf)
t0 = time.time()
tracker = fetch(mem["payload_storage/tracker.dat"])
n = struct.unpack_from("<II", tracker, 0)[0]
pages = {}
for k in mem:
    if k.startswith("payload_storage/page_"):
        pages[int(k.split("_")[-1].split(".")[0])] = fetch(mem[k])
print(f"tracker slots {n:,}; payload pages {len(pages)} downloaded in {time.time()-t0:.0f}s", flush=True)
keep, summary = [], collections.Counter()
t1 = time.time()
with gzip.open(out + "_payload.jsonl.gz", "wt", encoding="utf-8") as fh:
    for i in range(n):
        page, blk, ln, _ = struct.unpack_from("<IIII", tracker, 8 + 16 * i)
        if ln == 0: summary["empty slot"] += 1; continue
        try: p = json.loads(lz4.block.decompress(pages[page][blk * 128: blk * 128 + ln]))
        except Exception: summary["undecodable"] += 1; continue
        summary[(p.get("court_type"), p.get("language_code"))] += 1
        if p.get("court_type") == "supreme_court":
            keep.append(i)
            fh.write(json.dumps({"offset": i, **p}) + "\n")
print(f"decoded in {time.time()-t1:.0f}s; points by (court_type, language): {dict(summary)}; SC kept {len(keep):,}", flush=True)
if "vector_storage-dense/matrix.dat" in mem:
    M = np.frombuffer(fetch(mem["vector_storage-dense/matrix.dat"]), dtype="<f4", offset=4).reshape(-1, 1024)
else:                                                                  # appendable segment: chunked mmap files of 8192 vectors each
    parts, k = [], 0
    while f"vector_storage-dense/vectors/chunk_{k}.mmap" in mem:
        parts.append(np.frombuffer(fetch(mem[f"vector_storage-dense/vectors/chunk_{k}.mmap"]), dtype="<f4").reshape(-1, 1024)); k += 1
    M = np.concatenate(parts)
print("matrix rows", M.shape[0], "vs slots", n, flush=True)
np.save(out + "_vecs.npy", M[np.array(keep)].astype(np.float32))
json.dump({"slots": n, "sc_points": len(keep), "by_type_language": {str(k): v for k, v in summary.items()}, "seconds": round(time.time() - t0)}, open(out + "_summary.json", "w"))
print("done", round(time.time() - t0), "s")
