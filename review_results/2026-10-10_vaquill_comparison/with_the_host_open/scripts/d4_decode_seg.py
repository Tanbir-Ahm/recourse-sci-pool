"""Decodes the payloads and vectors of one Qdrant segment pulled to scratch (gridstore tracker -> LZ4 block -> JSON)."""
import sys, json, struct, collections
import numpy as np
import lz4.block
D = sys.argv[1] + "/"
tr = open(D + "payload_storage__tracker.dat", "rb").read()
pg = open(D + "payload_storage__page_0.dat", "rb").read()
nvec = len(open(D + "mutable_id_tracker.versions", "rb").read()) // 8
vec = np.frombuffer(open(D + "vector_storage-dense__vectors__chunk_0.mmap", "rb").read(), dtype="<f4").reshape(-1, 1024)[:nvec]
hdr = struct.unpack_from("<II", tr, 0)
print("tracker header", hdr, "| points", nvec)
payloads = []
for i in range(nvec):
    page, blk, ln, _ver = struct.unpack_from("<IIII", tr, 8 + 16 * i)
    if ln == 0: payloads.append(None); continue
    raw = pg[blk * 128: blk * 128 + ln]
    try:
        js = lz4.block.decompress(raw)          # size-prepended block
        payloads.append(json.loads(js))
    except Exception as e:
        payloads.append({"_error": str(e), "_head": raw[:16].hex()})
bad = sum(1 for p in payloads if p is None or "_error" in p)
print("decoded", nvec - bad, "of", nvec, "| errors", bad)
keys = collections.Counter(k for p in payloads if p and "_error" not in p for k in p)
print("payload keys (count):", dict(keys))
ok = [p for p in payloads if p and "_error" not in p]
print("court_type values:", collections.Counter(p.get("court_type") for p in ok))
print("language values:", collections.Counter(p.get("language") or p.get("language_code") for p in ok).most_common(6))
p0 = ok[0]
print("\nexample payload (text truncated):")
print(json.dumps({k: (v[:300] + "..." if isinstance(v, str) and len(v) > 300 else v) for k, v in p0.items()}, indent=1)[:3000])
json.dump(payloads, open(D + "payloads.json", "w"))
np.save(D + "vecs.npy", vec)
