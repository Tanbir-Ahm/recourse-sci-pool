"""Walks the top-level tar structure of a Qdrant shard snapshot by range requests (512-byte headers only; no payload is downloaded)."""
import sys, urllib.request, time
URL = sys.argv[1]; SIZE = int(sys.argv[2]); LIMIT = int(sys.argv[3])
UA = {"User-Agent": "recourse-sci-pool-audit/1.0 (read-only research)"}
def get(start, end):
    req = urllib.request.Request(URL, headers=dict(UA, Range=f"bytes={start}-{end}"))
    with urllib.request.urlopen(req, timeout=60) as r: return r.read()
def parse(h):
    name = h[0:100].split(b"\0")[0].decode("utf8", "replace")
    prefix = h[345:500].split(b"\0")[0].decode("utf8", "replace")
    size_f = h[124:136].split(b"\0")[0].strip()
    typ = h[156:157]
    magic = h[257:263]
    if size_f.startswith(b"\x80"):                         # base-256 size
        size = int.from_bytes(size_f.ljust(12, b"\0")[1:12].rstrip(b"\0") or b"\0", "big") if False else int.from_bytes(h[124:136][1:], "big")
    else:
        size = int(size_f or b"0", 8)
    return (prefix + "/" + name if prefix else name), size, typ, magic
off, n = 0, 0
t0 = time.time()
while off < SIZE and n < LIMIT:
    h = get(off, off + 511)
    if h.strip(b"\0") == b"": print("end of archive at", off); break
    name, size, typ, magic = parse(h)
    print(f"{off:>14,}  {size:>16,}  {typ!r}  {magic!r}  {name}")
    off += 512 + ((size + 511) // 512) * 512
    n += 1
print("entries listed:", n, "seconds", round(time.time() - t0, 1))
