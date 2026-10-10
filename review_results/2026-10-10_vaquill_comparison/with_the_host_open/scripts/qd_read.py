"""Minimal reader for entries of a (nested) GNU-tar Qdrant shard snapshot over HTTP range requests, including GNU sparse members."""
import urllib.request
UA = {"User-Agent": "recourse-sci-pool-audit/1.0 (read-only research)"}
def get(url, start, end):
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers=dict(UA, Range=f"bytes={start}-{end}"))
            with urllib.request.urlopen(req, timeout=120) as r: return r.read()
        except Exception as e:
            err = e
    raise err
def octal(b): return int(b.split(b"\0")[0].strip() or b"0", 8)
def walk(url, base, inner_size, want=None):
    """yield (name, header_abs_offset, data_abs_offset, stored_size, real_size, sparse_map) for entries of the segment tar starting at absolute offset `base` (its outer header included)."""
    off = 0
    while off < inner_size:
        hdr_abs = base + 512 + off
        h = get(url, hdr_abs, hdr_abs + 511)
        if h.strip(b"\0") == b"": return
        name = h[0:100].split(b"\0")[0].decode(); typ = h[156:157]
        size = octal(h[124:136])
        sparse, real, ext = [], size, 0
        if typ == b"S":
            real = octal(h[483:494])
            for i in range(4):
                o, n = h[386 + 24 * i: 386 + 24 * i + 12], h[386 + 24 * i + 12: 386 + 24 * i + 24]
                if o.strip(b"\0 "): sparse.append((octal(o), octal(n)))
            more = h[482:483] == b"\x01"
            while more:
                blk = get(url, hdr_abs + 512 + 512 * ext, hdr_abs + 512 + 512 * ext + 511); ext += 1
                for i in range(21):
                    o, n = blk[24 * i: 24 * i + 12], blk[24 * i + 12: 24 * i + 24]
                    if o.strip(b"\0 "): sparse.append((octal(o), octal(n)))
                more = blk[504:505] == b"\x01"
        data_abs = hdr_abs + 512 + 512 * ext
        if want is None or name in want or any(name.endswith(w) for w in want):
            yield name, hdr_abs, data_abs, size, real, sparse
        off += 512 + 512 * ext + ((size + 511) // 512) * 512
def read_member(url, data_abs, stored, real, sparse):
    """Apparent contents of a member (holes filled with zeros). Only for members that fit in memory."""
    raw = get(url, data_abs, data_abs + stored - 1) if stored else b""
    if not sparse: return raw
    out = bytearray(real); pos = 0
    for o, n in sparse:
        out[o:o + n] = raw[pos:pos + n]; pos += n
    return bytes(out)

class Member:
    """Random access to the apparent contents of one (possibly GNU-sparse) tar member by range requests."""
    def __init__(self, url, data_abs, stored, real, sparse):
        self.url, self.data_abs, self.stored, self.real = url, data_abs, stored, real
        self.sparse = sparse or [(0, real)]
        self.starts, pos = [], 0
        for o, n in self.sparse:
            self.starts.append(pos); pos += n
    def read(self, off, n):
        out = bytearray(n)
        for (o, ln), st in zip(self.sparse, self.starts):
            a, b = max(off, o), min(off + n, o + ln)
            if a < b:
                out[a - off:b - off] = get(self.url, self.data_abs + st + (a - o), self.data_abs + st + (b - o) - 1)
        return bytes(out)

def index_segment(url, base, inner_size, names=("payload_storage/", "vector_storage-dense/vectors/", "mutable_id_tracker", "immutable_id_tracker", "id_tracker", "segment.json")):
    """{short name: Member} for the files of one segment tar that matter for sampling."""
    mem = {}
    for name, hdr, data, stored, real, sparse in walk(url, base, inner_size):
        short = name.replace("snapshot/files/", "")
        if any(short.startswith(p) for p in names):
            mem[short] = Member(url, data, stored, real, sparse)
    return mem
