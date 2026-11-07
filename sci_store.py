"""
sci_store.py -- the passage text and the keyword index on disk instead of in memory (switch SCI_STORE; FOLLOW_UPS 2dr, built 2026-11-07).

Why. The search service (sci_search_service.py) held three things in memory for every passage of the index: the vectors, the passage text as Python strings inside one dictionary per passage, and a keyword index
(SQLite FTS5) built in memory at every start. On the newer index (420,893 passages) the text and the dictionaries were about 840 MB and the keyword index about 360 MB, and building the keyword index took 16 seconds
of every start. A question needs the text of only the 60 to 90 passages it re-ranks and the ten it returns.

What this module does. SCI_STORE=on: the service writes ONE file (sci_store.sqlite, next to the index; SCI_STORE_PATH names another) holding
  * t(id, z)  the text of passage id (its row number in the service), compressed with zlib, UTF-8,
  * f         the keyword index, the same contentless FTS5 table the service always built (same tokenizer 'porter unicode61', same rowids), now on disk,
  * info      a fingerprint: the number of passages and a SHA-256 over the text of every passage in order.
and keeps in memory only six small fields per passage (doc, i, pn, page, section, h) in columns (LeanMetas). The text is read from the file when needed (re-rank, weight, the returned passages).
The file is built on the first start with the switch on (the data being read anyway), written to a temporary name, read back and compared with what was read, and only then renamed into place.
On every later start the fingerprint of the text just read from the index is compared with the file's: a changed index gives a different fingerprint and the file is rebuilt, so the file can never serve the text of another index.

What it does not do. It does not change which passages are found or how they are ranked: the keyword index is the same SQLite table with the same rows and the same text, the text is returned byte for byte, and the vectors are not touched.
Any problem with the file (cannot be written, the rows lack a field) falls back to the in-memory path with a line in the log; a refusal about the index itself (wrong model, wrong commit, width) is raised as before.
Way back: unset SCI_STORE (or anything but on).
"""
import hashlib
import os
import re
import sqlite3
import sys
import threading
import time
import zlib

FORMAT = 1
FIELDS = ("doc", "i", "pn", "page", "section", "h")
FILENAME = "sci_store.sqlite"
BATCH = 5000
ZLEVEL = 6


class StoreError(Exception):
    """The store cannot be used (the caller keeps the in-memory path)."""


def enabled():
    return (os.environ.get("SCI_STORE") or "").strip().strip("\"'").lower() in ("1", "on", "true", "yes")


def store_path(index_dir):
    return (os.environ.get("SCI_STORE_PATH") or "").strip().strip("\"'") or os.path.join(index_dir, FILENAME)


def _enc(text):
    return text.encode("utf-8", "surrogatepass")


def _dec(blob):
    return zlib.decompress(blob).decode("utf-8", "surrogatepass")


def read_info(path):
    """The fingerprint rows of an existing store as a dict, or None when the file is missing, unreadable or of another format."""
    if not os.path.exists(path):
        return None
    try:
        conn = sqlite3.connect("file:" + path + "?mode=ro", uri=True)
        try:
            d = dict(conn.execute("select k, v from info"))
        finally:
            conn.close()
        if int(d.get("format", 0)) != FORMAT:
            return None
        return {"digest": d["digest"], "passages": int(d["passages"]), "total_chars": int(d["total_chars"]), "built": d.get("built")}
    except Exception:  # noqa: BLE001
        return None


class Collector:
    """Receives every full passage row as the index is read (the `keep` argument of sci_index._load_index): returns the small dictionary the service needs, hashes the text, remembers the opening lines of a
    document with no case record (the 'header' table the service used to build from the full rows), and, when `build_to` is a path, writes the text and the keyword index to that file as it goes."""

    def __init__(self, build_to=None):
        self.count = 0
        self.total_chars = 0
        self.incomplete = None            # a reason, when a row cannot be handled
        self.header = {}
        self._h = hashlib.sha256()
        self._build_to = build_to
        self._conn = None
        self._batch = []
        if build_to:
            self._tmp = build_to + ".building"
            try:
                if os.path.exists(self._tmp):
                    os.remove(self._tmp)
                os.makedirs(os.path.dirname(os.path.abspath(build_to)), exist_ok=True)
                self._conn = sqlite3.connect(self._tmp)
                c = self._conn
                c.execute("pragma journal_mode=off")
                c.execute("pragma synchronous=off")
                c.execute("create table t(id integer primary key, z blob not null)")
                c.execute("create virtual table f using fts5(text, content='', tokenize='porter unicode61')")
            except (OSError, sqlite3.Error) as e:
                raise StoreError(f"cannot create {self._tmp}: {e}") from e

    def keep(self, m):
        text = m.get("text")
        if not isinstance(text, str) or any(k not in m for k in FIELDS):
            self.incomplete = self.incomplete or f"row {self.count} lacks a field or its text is not a string"
            text = text if isinstance(text, str) else ""
        enc = _enc(text)
        self._h.update(len(enc).to_bytes(8, "big"))
        self._h.update(enc)
        if self._conn is not None:
            self._batch.append((self.count, zlib.compress(enc, ZLEVEL), text))
            if len(self._batch) >= BATCH:
                self._flush()
        self.total_chars += len(text)
        if m.get("doc") not in self.header and (m.get("section") == "header" or str(m.get("pn")).startswith("preamble")):
            self.header[m.get("doc")] = re.sub(r"\s+", " ", text)[:260]       # as sci_search_service used to compute it from the full rows
        self.count += 1
        return {k: m[k] for k in FIELDS if k in m}

    def _flush(self):
        try:
            self._conn.executemany("insert into t(id, z) values(?,?)", ((i, z) for i, z, _ in self._batch))
            self._conn.executemany("insert into f(rowid, text) values(?,?)", ((i, t) for i, _, t in self._batch))
        except sqlite3.Error as e:
            raise StoreError(f"cannot write {self._tmp}: {e}") from e
        self._batch = []

    def digest(self):
        return self._h.copy().hexdigest()

    def abort(self):
        if self._conn is not None:
            try:
                self._conn.close()
            except sqlite3.Error:
                pass
            self._conn = None
            try:
                os.remove(self._tmp)
            except OSError:
                pass

    def finish(self):
        """Complete the file, read it back against what was read from the index, and move it into place. Returns its size in bytes."""
        if self._conn is None:
            raise StoreError("nothing to finish")
        try:
            if self._batch:
                self._flush()
            c = self._conn
            digest = self.digest()
            c.execute("create table info(k text primary key, v text)")
            c.executemany("insert into info values(?,?)", [("format", str(FORMAT)), ("digest", digest), ("passages", str(self.count)), ("total_chars", str(self.total_chars)),
                                                          ("built", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))])
            c.commit()
            # read-back: every row decompresses to the text that was read, in order (so a short write or a bad disk is caught before the file is used)
            h2, n2 = hashlib.sha256(), 0
            for _id, z in c.execute("select id, z from t order by id"):
                if _id != n2:
                    raise StoreError(f"{self._tmp}: row {n2} is missing")
                enc = zlib.decompress(z)
                h2.update(len(enc).to_bytes(8, "big"))
                h2.update(enc)
                n2 += 1
            if n2 != self.count or h2.hexdigest() != digest:
                raise StoreError(f"{self._tmp} does not read back as what was written")
            nf = c.execute("select count(*) from f_docsize").fetchone()[0]
            if nf != self.count:
                raise StoreError(f"{self._tmp}: the keyword index holds {nf} rows, not {self.count}")
            c.close()
            self._conn = None
            os.replace(self._tmp, self._build_to)
            return os.path.getsize(self._build_to)
        except (OSError, sqlite3.Error, zlib.error) as e:
            self.abort()
            raise StoreError(f"cannot complete {self._build_to}: {e}") from e
        except StoreError:
            self.abort()
            raise


class LeanMetas:
    """The service's `metas` without the text: a sequence of small dictionaries rebuilt from six columns (doc, i, pn, page, section, h), and `text(i)` read from the store when it is needed."""

    def __init__(self, rows, path, total_chars):
        self._doc = [r["doc"] for r in rows]
        self._i = [r["i"] for r in rows]
        self._pn = [sys.intern(r["pn"]) if isinstance(r["pn"], str) else r["pn"] for r in rows]
        self._page = [r["page"] for r in rows]
        self._section = [sys.intern(r["section"]) if isinstance(r["section"], str) else r["section"] for r in rows]
        self._h = [r["h"] for r in rows]
        self.total_chars = total_chars
        self.path = path
        self._lock = threading.Lock()
        self._conn = open_ro(path)

    def __len__(self):
        return len(self._doc)

    def __getitem__(self, k):
        if isinstance(k, slice):
            return [self[j] for j in range(*k.indices(len(self)))]
        if k < 0:
            k += len(self)
        return {"doc": self._doc[k], "i": self._i[k], "pn": self._pn[k], "page": self._page[k], "section": self._section[k], "h": self._h[k]}

    def __iter__(self):
        for k in range(len(self._doc)):
            yield self[k]

    def text(self, k):
        with self._lock:
            row = self._conn.execute("select z from t where id=?", (int(k),)).fetchone()
        if row is None:
            raise KeyError(k)
        return _dec(row[0])

    def rows_with_text(self):
        """Every passage as {doc, i, pn, text} in order (sci_quotes.build reads the whole index once, one judgment at a time)."""
        with self._lock:
            conn = sqlite3.connect("file:" + self.path + "?mode=ro", uri=True)
        try:
            for k, (_id, z) in enumerate(conn.execute("select id, z from t order by id")):
                yield {"doc": self._doc[k], "i": self._i[k], "pn": self._pn[k], "text": _dec(z)}
        finally:
            conn.close()


def open_ro(path):
    """The store, read-only, with a small page cache and no memory mapping (the operating system's file cache is not part of the process)."""
    try:
        conn = sqlite3.connect("file:" + path + "?mode=ro", uri=True, check_same_thread=False)
        conn.execute("pragma cache_size=-32768")
        conn.execute("pragma mmap_size=0")
        return conn
    except sqlite3.Error as e:
        raise StoreError(f"cannot open {path}: {e}") from e
