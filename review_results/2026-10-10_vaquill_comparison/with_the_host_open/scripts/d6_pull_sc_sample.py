"""From the last segment of shard 0 (~110k points, mostly Supreme Court), pulls a sample of SC points: decoded payload + float32 dense vector (matrix.dat, 4-byte header)."""
import sys, json, struct, os, random, collections
import numpy as np
sys.path.insert(0, sys.argv[1])
import qd_read as Q
import lz4.block
URL = "https://oss-data-in.vaquill.ai/qdrant/legal_corpus_v2/shard-0/legal_corpus_v2-shard-0-2026-08-22-12-38-53.snapshot"
out = sys.argv[2]; N = int(sys.argv[3]); os.makedirs(out, exist_ok=True)
raw = json.load(open(sys.argv[4]))
mem = {k: Q.Member(URL, *v) for k, v in raw.items() if not k.startswith("payload_index/")}
pst = mem["payload_storage/tracker.dat"]
nslots = struct.unpack("<II", pst.read(0, 8))[0]
mat = mem["vector_storage-dense/matrix.dat"]
print("points", nslots, "| matrix.dat bytes", mat.real, "=> (bytes-4)/4096 =", (mat.real - 4) / 4096)
rnd = random.Random(5)
cand = sorted(rnd.sample(range(nslots), N))
rows = []
for i in cand:
    page, blk, ln, _ = struct.unpack("<IIII", pst.read(8 + 16 * i, 16))
    if ln == 0: continue
    pg = mem.get(f"payload_storage/page_{page}.dat")
    try: p = json.loads(lz4.block.decompress(pg.read(blk * 128, ln)))
    except Exception: continue
    rows.append((i, p))
print("sampled", len(rows), dict(collections.Counter(p.get("court_type") for _, p in rows)))
sc = [(i, p) for i, p in rows if p.get("court_type") == "supreme_court"]
vecs = np.stack([np.frombuffer(mat.read(4 + i * 4096, 4096), dtype="<f4") for i, _ in sc])
print("vector norms (min/median/max):", float(np.linalg.norm(vecs, axis=1).min()), float(np.median(np.linalg.norm(vecs, axis=1))), float(np.linalg.norm(vecs, axis=1).max()))
np.save(out + "/sc_vecs.npy", vecs)
json.dump([{"offset": i, **p} for i, p in sc], open(out + "/sc_payloads.json", "w"))
print("saved", len(sc), "SC points")
print("payload keys over the SC sample:", dict(collections.Counter(k for _, q in sc for k in q)))
p = sc[0][1]
print(json.dumps({k: (v[:260] + "..." if isinstance(v, str) and len(v) > 260 else v) for k, v in p.items()}, indent=1)[:2600])
