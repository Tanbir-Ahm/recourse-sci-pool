"""Lists the entries inside ONE segment tar of a Qdrant shard snapshot (nested tar), using header-only range requests."""
import sys, urllib.request, time
URL = sys.argv[1]; BASE = int(sys.argv[2]); INNER_SIZE = int(sys.argv[3]); LIMIT = int(sys.argv[4])
UA = {"User-Agent": "recourse-sci-pool-audit/1.0 (read-only research)"}
def get(start, end):
    req = urllib.request.Request(URL, headers=dict(UA, Range=f"bytes={start}-{end}"))
    with urllib.request.urlopen(req, timeout=60) as r: return r.read()
def parse(h):
    name = h[0:100].split(b"\0")[0].decode("utf8", "replace")
    prefix = h[345:500].split(b"\0")[0].decode("utf8", "replace")
    raw = h[124:136]
    size = int.from_bytes(raw[1:], "big") if raw[0] & 0x80 else int(raw.split(b"\0")[0].strip() or b"0", 8)
    return (prefix + "/" + name if prefix else name), size, h[156:157]
off, n = 0, 0
while off < INNER_SIZE and n < LIMIT:
    h = get(BASE + 512 + off, BASE + 512 + off + 511)           # +512: skip the OUTER header of the segment entry
    if h.strip(b"\0") == b"": print("end"); break
    name, size, typ = parse(h)
    ext = 0
    if typ == b"S" and h[482:483] == b"\x01":                       # GNU sparse: extension blocks follow the header
        while True:
            blk = get(BASE + 512 + off + 512 + 512 * ext, BASE + 512 + off + 512 + 512 * ext + 511)
            ext += 1
            if blk[504:505] != b"\x01": break
    realsize = int(h[483:494].split(b"\0")[0].strip() or b"0", 8) if typ == b"S" else size
    print(f"{off:>14,} {size:>16,} {realsize:>16,} {typ!r} ext={ext} {name}")
    off += 512 + 512 * ext + ((size + 511) // 512) * 512
    n += 1
print("entries:", n)
