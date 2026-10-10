"""A read-only, seekable file object over an HTTPS URL using Range requests; the last 512 KB are cached (enough for a parquet footer)."""
import io, urllib.request

class RangeFile(io.RawIOBase):
    def __init__(self, url, size, tail=512 * 1024, timeout=60):
        self.url, self.size, self.pos, self.timeout = url, size, 0, timeout
        self.tail_start = max(0, size - tail)
        self._tail = None
        self.requests = 0
    def _get(self, start, end):                         # inclusive range
        req = urllib.request.Request(self.url, headers={"Range": f"bytes={start}-{end}", "User-Agent": "recourse-sci-pool-audit/1.0 (read-only research)"})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            self.requests += 1
            return r.read()
    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.pos
    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else (self.pos + off if whence == 1 else self.size + off)
        return self.pos
    def read(self, n=-1):
        if n is None or n < 0: n = self.size - self.pos
        n = min(n, self.size - self.pos)
        if n <= 0: return b""
        a, b = self.pos, self.pos + n - 1
        if a >= self.tail_start:
            if self._tail is None: self._tail = self._get(self.tail_start, self.size - 1)
            out = self._tail[a - self.tail_start: b - self.tail_start + 1]
        else:
            out = self._get(a, b)
        self.pos += len(out)
        return out
    def readinto(self, buf):
        d = self.read(len(buf)); buf[:len(d)] = d; return len(d)
