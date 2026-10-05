"""One searchable store (SQLite with full-text search) over every Supreme Court judgment we hold: the crawl (to 4 May 2017) and the open bucket
(after that date, plus older judgments the crawl lacks). Built from the two data branches; rebuild it whenever either changes.

    python -m goodlaw.corpus build --crawl-dir ../recourse-sci-pool-data --bucket-dir ../recourse-sci-bucket-data --out corpus.sqlite

One row per distinct judgment where it can tell. A judgment present in both sources is stored once, from the crawl (the court's own file), and
takes the bucket's exact decision date, neutral citation and law-report citation. Judgments only the bucket holds are stored from the bucket.
Second copies inside the crawl are kept but marked `dup_of` the copy that is read; later steps count only rows with no `dup_of`.

doc_key: `c<id>` for a crawl text (c37060), `b<path>` for a bucket text (b2019_5_569_578).
"""
import argparse
import bisect
import collections
import csv
import glob
import gzip
import json
import os
import re
import sqlite3
import statistics
import sys
from multiprocessing import Pool

from . import cites as C
from . import headers as H

_STOP = set("""versus vs v and ors anr anrs others another the of in for to by through lrs lr dead legal representatives representative thr his her
their its etc ltd limited pvt private co company shri sri smt dr mr mrs ms m s no nos""".split())
RELIABLE = ("header", "tail_place", "bucket")

SCHEMA = """
CREATE TABLE docs (
  id INTEGER PRIMARY KEY, doc_key TEXT UNIQUE NOT NULL, source TEXT NOT NULL, src_id TEXT NOT NULL,
  title TEXT, pet TEXT, resp TEXT, date TEXT, date_source TEXT, year INTEGER,
  bench_size INTEGER, bench_source TEXT, layout TEXT, cites TEXT, citator TEXT,
  bucket_path TEXT, insc TEXT, scr_cite TEXT, dup_of TEXT, maybe_dup_of TEXT, body_start INTEGER, text_len INTEGER, scan_pages INTEGER
);
CREATE TABLE texts (id INTEGER PRIMARY KEY, text TEXT NOT NULL);
CREATE VIRTUAL TABLE fts USING fts5(text, content='', tokenize='unicode61 remove_diacritics 2');
CREATE TABLE meta (k TEXT PRIMARY KEY, v TEXT);
CREATE INDEX docs_year ON docs(year);
CREATE INDEX docs_dup ON docs(dup_of);
"""


def name_key(s):
    """Ordered distinctive words of a party name; two spellings of one name usually give the same key."""
    return " ".join(t for t in re.findall(r"[a-z0-9]+", (s or "").lower()) if t not in _STOP and len(t) > 1)


def norm_text(s):
    return re.findall(r"[a-z0-9]+", s.lower())


def shingles(words, n=5):
    return {" ".join(words[i:i + n]) for i in range(max(len(words) - n + 1, 0))}


# ---------------------------------------------------------------- reading the sources
def _crawl_shard(path):
    out = []
    for line in gzip.open(path, "rt", encoding="utf-8"):
        r = json.loads(line)
        if r.get("status") != "ok":
            continue
        text = r["text"]
        d = H.parse_crawl(text)
        if d["date_source"] == "tail_any":      # checked against bucket dates: only 17% exact, so it is not used
            d["date"], d["date_source"] = None, None
        d.update(id=r["id"], text=text)
        out.append(d)
    return out


def read_crawl(crawl_dir, workers=4):
    files = sorted(glob.glob(os.path.join(crawl_dir, "shards", "*.jsonl.gz")))
    docs = []
    if workers > 1:
        with Pool(workers) as pool:
            for part in pool.imap(_crawl_shard, files):
                docs.extend(part)
    else:
        for f in files:
            docs.extend(_crawl_shard(f))
    docs.sort(key=lambda d: d["id"])
    return docs


def read_bucket(bucket_dir):
    recs = []
    for f in sorted(glob.glob(os.path.join(bucket_dir, "shards", "*.jsonl.gz"))):
        scope = os.path.basename(f).split("-")[0]
        for line in gzip.open(f, "rt", encoding="utf-8"):
            r = json.loads(line)
            if r.get("status") != "ok":
                continue
            r["_scope"] = scope
            recs.append(r)
    return recs


def _iso(ddmmyyyy):
    m = re.match(r"(\d{1,2})-(\d{1,2})-(\d{4})$", ddmmyyyy or "")
    return H.to_iso(m[1], m[2], m[3]) if m else None


def _read_csv_gz(path):
    return list(csv.DictReader(gzip.open(path, "rt", encoding="utf-8")))


def bucket_cites(rec):
    keys = []
    for field in ("citation", "case_id", "nc_display"):
        for k in C.cite_keys(rec.get(field) or ""):
            if k not in keys:
                keys.append(k)
    return keys


# ---------------------------------------------------------------- linking crawl and bucket
def link_maps(registry_path, none_resolution_path, bucket_recs):
    """({crawl id: bucket info}, set of bucket paths to leave out because the crawl already holds them, {bucket path: best crawl id for 'uncertain'})."""
    by_path = {r["path"]: r for r in bucket_recs}
    info_by_path = {}
    links = {}
    for row in _read_csv_gz(registry_path):
        if row["tier"] in ("T1", "T2", "T3") and row["crawl_ids"]:
            ids = [int(x) for x in row["crawl_ids"].split(";")]
            info = {"bucket_path": row["path"], "date": _iso(row["decision_date"]), "title": row["title"], "citation": row["citation"],
                    "case_id": row["case_id"]}
            for i in ids:
                links.setdefault(i, info)
    skip, maybe = set(), {}
    if none_resolution_path and os.path.exists(none_resolution_path):
        for row in _read_csv_gz(none_resolution_path):
            path = row["path"]
            if row["in_crawl"] == "yes" and row["best_crawl_id"]:
                skip.add(path)
                rec = by_path.get(path, {})
                links.setdefault(int(float(row["best_crawl_id"])), {"bucket_path": path, "date": _iso(row["decision_date"]), "title": row["title"],
                                                                    "citation": rec.get("citation", ""), "case_id": rec.get("case_id", "")})
            elif row["in_crawl"] == "uncertain" and row["best_crawl_id"]:
                maybe[path] = int(float(row["best_crawl_id"]))
    return links, skip, maybe


# ---------------------------------------------------------------- dates for crawl texts without their own
def neighbour_years(docs):
    """{doc id: estimated year} for crawl docs with no reliable date: the median year of the 7 nearest crawl ids that have one (98% exact on
    23,298 docs whose true year is known from the bucket)."""
    rel = sorted((d["id"], int(d["date"][:4])) for d in docs if d.get("date") and d.get("date_source") in RELIABLE)
    ids = [i for i, _ in rel]
    years = [y for _, y in rel]
    out = {}
    for d in docs:
        if d.get("date") and d.get("date_source") in RELIABLE:
            continue
        j = bisect.bisect_left(ids, d["id"])
        lo, hi, cand = j - 1, j, []
        while len(cand) < 7 and (lo >= 0 or hi < len(ids)):
            dl = d["id"] - ids[lo] if lo >= 0 else 10**9
            dh = ids[hi] - d["id"] if hi < len(ids) else 10**9
            if dl <= dh:
                cand.append(years[lo])
                lo -= 1
            else:
                cand.append(years[hi])
                hi += 1
        if cand:
            out[d["id"]] = int(statistics.median(cand))
    return out


# ---------------------------------------------------------------- second copies inside the crawl
def find_duplicates(rows, threshold=0.5):
    """rows: list of dicts with key, pet, resp, year, text_len, text. Returns {duplicate key: canonical key}. Groups are rows with the same
    party-name keys and year; within a group two rows are copies when the 5-word shingles of their first 6,000 body characters overlap by
    at least `threshold` (Jaccard). The longest text is kept."""
    groups = collections.defaultdict(list)
    for r in rows:
        if r["pet"] and r["resp"] and r["year"]:
            kp, kr = name_key(r["pet"]), name_key(r["resp"])
            if kp and kr:
                groups[(kp, kr, r["year"])].append(r)
    parent = {}

    def find(x):
        while parent.get(x, x) != x:
            parent[x] = parent.get(parent[x], parent[x])
            x = parent[x]
        return x

    for g in groups.values():
        if len(g) < 2:
            continue
        sh = {}
        for r in g:
            body = r["text"][r.get("body_start") or 0:][:6000]
            sh[r["key"]] = shingles(norm_text(body))
        for i in range(len(g)):
            for j in range(i + 1, len(g)):
                a, b = sh[g[i]["key"]], sh[g[j]["key"]]
                if a and b and len(a & b) / len(a | b) >= threshold:
                    ra, rb = find(g[i]["key"]), find(g[j]["key"])
                    if ra != rb:
                        parent[rb] = ra
    clusters = collections.defaultdict(list)
    for g in groups.values():
        for r in g:
            clusters[find(r["key"])].append(r)
    dup = {}
    for members in clusters.values():
        if len(members) > 1:
            keep = sorted(members, key=lambda r: (-r["text_len"], r["key"]))[0]["key"]
            for r in members:
                if r["key"] != keep:
                    dup[r["key"]] = keep
    return dup


# ---------------------------------------------------------------- the build
def build(crawl_dir, bucket_dir, registry_path, none_resolution_path, out_path, workers=4, log=print):
    if os.path.exists(out_path):
        os.remove(out_path)
    log("reading the crawl...")
    crawl = read_crawl(crawl_dir, workers)
    log(f"  {len(crawl)} crawled texts")
    bucket = read_bucket(bucket_dir)
    log(f"  {len(bucket)} bucket texts")
    links, skip, maybe = link_maps(registry_path, none_resolution_path, bucket)
    est = neighbour_years(crawl)

    rows = []
    for d in crawl:
        link = links.get(d["id"])
        date, dsrc = d["date"], d["date_source"]
        if link and link.get("date"):
            date, dsrc = link["date"], "bucket"
        year = int(date[:4]) if date else est.get(d["id"])
        if not date and year:
            dsrc = "neighbours"
        title = (f"{d['pet']} v. {d['resp']}" if d["pet"] and d["resp"] else None) or (link or {}).get("title")
        cites = []
        for k in C.cite_keys(" ".join(d["cite_air"] + d["cite_scr"] + d["cite_scc"])) + (C.cite_keys((link or {}).get("citation", "") + " " + (link or {}).get("case_id", "")) if link else []):
            if k not in cites:
                cites.append(k)
        rows.append(dict(key=f"c{d['id']}", source="crawl", src_id=str(d["id"]), title=title, pet=d["pet"], resp=d["resp"], date=date, date_source=dsrc, year=year,
                         bench_size=d["bench_size"], bench_source=d["bench_source"], layout=d["layout"], cites=cites, citator=d["citator"],
                         bucket_path=(link or {}).get("bucket_path"), insc=(link or {}).get("case_id") or None, scr_cite=(link or {}).get("citation") or None,
                         dup_of=None, maybe_dup_of=None, body_start=d["body_start"], text_len=len(d["text"]), scan_pages=None, text=d["text"]))
    for r in bucket:
        if r.get("path") in skip:
            continue
        date = _iso(r.get("decision_date"))
        size, bsrc = H.bench_size(r["text"], "report")
        rows.append(dict(key=f"b{r['path']}", source="bucket", src_id=r["path"], title=r.get("title"), pet=r.get("petitioner"), resp=r.get("respondent"),
                         date=date, date_source="bucket" if date else None, year=int(date[:4]) if date else None, bench_size=size, bench_source=bsrc,
                         layout="report", cites=bucket_cites(r), citator=[], bucket_path=r["path"], insc=r.get("case_id") or None, scr_cite=r.get("citation") or None,
                         dup_of=None, maybe_dup_of=(f"c{maybe[r['path']]}" if r["path"] in maybe else None), body_start=r.get("body_start"),
                         text_len=len(r["text"]), scan_pages=r.get("scan_pages"), text=r["text"]))
    log(f"  {len(rows)} stored texts; looking for second copies inside the crawl...")
    dups = find_duplicates([r for r in rows if r["source"] == "crawl"])
    for r in rows:
        r["dup_of"] = dups.get(r["key"])
    log(f"  {len(dups)} crawl texts are second copies of another")

    con = sqlite3.connect(out_path)
    con.executescript(SCHEMA)
    for n, r in enumerate(rows, 1):
        con.execute("INSERT INTO docs(id,doc_key,source,src_id,title,pet,resp,date,date_source,year,bench_size,bench_source,layout,cites,citator,bucket_path,insc,scr_cite,dup_of,maybe_dup_of,body_start,text_len,scan_pages) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (n, r["key"], r["source"], r["src_id"], r["title"], r["pet"], r["resp"], r["date"], r["date_source"], r["year"], r["bench_size"], r["bench_source"], r["layout"],
                     json.dumps(r["cites"]), json.dumps(r["citator"]), r["bucket_path"], r["insc"], r["scr_cite"], r["dup_of"], r["maybe_dup_of"], r["body_start"], r["text_len"], r["scan_pages"]))
        con.execute("INSERT INTO texts(id,text) VALUES (?,?)", (n, r["text"]))
        con.execute("INSERT INTO fts(rowid,text) VALUES (?,?)", (n, r["text"]))
        if n % 5000 == 0:
            log(f"  stored {n}")
    stats = {"docs": len(rows), "crawl": sum(r["source"] == "crawl" for r in rows), "bucket": sum(r["source"] == "bucket" for r in rows),
             "crawl_second_copies": len(dups), "crawl_with_bucket_link": sum(1 for r in rows if r["source"] == "crawl" and r["bucket_path"]),
             "bucket_skipped_because_crawl_holds_them": len(skip)}
    con.execute("INSERT INTO meta VALUES ('stats', ?)", (json.dumps(stats),))
    con.commit()
    con.close()
    log(f"done: {stats}")
    return stats



# ---------------------------------------------------------------- which reported citations each text contains
_CITE_DB = None


def _own_pages(source, src_id):
    """(year, volume, first page, last page) of the law-report pages a bucket text itself occupies, from its file name 2019_5_569_578; the
    running headers on those pages ("[2019] 5 S.C.R. 570") are not citations of other judgments."""
    if source != "bucket":
        return None
    m = re.match(r"^(?:S_)?(\d{4})_(\d+)_(\d+)_(\d+)$", src_id)
    return (m[1], m[2], int(m[3]), int(m[4])) if m else None


def _cite_chunk(args):
    global _CITE_DB
    path, lo, hi = args
    if _CITE_DB is None:
        _CITE_DB = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    out = []
    for row_id, text, source, src_id in _CITE_DB.execute(
            "SELECT t.id, t.text, d.source, d.src_id FROM texts t JOIN docs d ON d.id = t.id WHERE t.id >= ? AND t.id < ?", (lo, hi)):
        own = _own_pages(source, src_id)
        counts = collections.Counter()
        for key, _, _ in C.find_cites(text):
            if own and key.startswith("scr:"):
                _, year, vol, page = key.split(":")
                if year == own[0] and vol == own[1] and own[2] <= int(page) <= own[3]:
                    continue
            counts[key] += 1
        out.append((row_id, counts))
    return out


def cites_path(path):
    return path + ".cites"


def index_cites(path, workers=4, chunk=400, log=print):
    """Writes <path>.cites with table doc_cites(doc_id, key, n): every reported citation key found in each text, with how many times. It is a
    separate file so the workers can read the corpus while the index is written. Run after build."""
    out = cites_path(path)
    if os.path.exists(out):
        os.remove(out)
    con = sqlite3.connect(out)
    con.execute("CREATE TABLE doc_cites (doc_id INTEGER NOT NULL, key TEXT NOT NULL, n INTEGER NOT NULL)")
    src = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    top = src.execute("SELECT MAX(id) FROM texts").fetchone()[0]
    src.close()
    jobs = [(path, lo, lo + chunk) for lo in range(1, top + 1, chunk)]
    total = 0
    with Pool(workers) as pool:
        for done, part in enumerate(pool.imap(_cite_chunk, jobs), 1):
            for row_id, counts in part:
                con.executemany("INSERT INTO doc_cites VALUES (?,?,?)", [(row_id, k, n) for k, n in counts.items()])
                total += len(counts)
            if done % 20 == 0:
                con.commit()
                log(f"  cite index: {done}/{len(jobs)} chunks")
    con.execute("CREATE INDEX doc_cites_key ON doc_cites(key)")
    con.execute("CREATE INDEX doc_cites_doc ON doc_cites(doc_id)")
    con.commit()
    con.close()
    log(f"cite index done: {total} (text, citation) pairs")
    return total


# ---------------------------------------------------------------- reading the store
class Corpus:
    def __init__(self, path):
        self.con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        self.con.row_factory = sqlite3.Row
        self.has_cite_index = os.path.exists(cites_path(path))
        if self.has_cite_index:
            self.con.execute("ATTACH DATABASE ? AS cx", (f"file:{cites_path(path)}?mode=ro",))

    @staticmethod
    def _doc(r):
        d = dict(r)
        d["cites"] = json.loads(d["cites"] or "[]")
        d["citator"] = json.loads(d["citator"] or "[]")
        return d

    def stats(self):
        return json.loads(self.con.execute("SELECT v FROM meta WHERE k='stats'").fetchone()[0])

    def get(self, doc_key, with_text=True):
        r = self.con.execute("SELECT * FROM docs WHERE doc_key=?", (doc_key,)).fetchone()
        if not r:
            return None
        d = self._doc(r)
        if with_text:
            d["text"] = self.con.execute("SELECT text FROM texts WHERE id=?", (d["id"],)).fetchone()[0]
        return d

    def text_of(self, row_id):
        return self.con.execute("SELECT text FROM texts WHERE id=?", (row_id,)).fetchone()[0]

    def search(self, fts_query, limit=None, canonical_only=True):
        """Docs (without text) whose text matches an FTS5 query, e.g. '"sri mohan" AND rangappa' or 'NEAR(rangappa mohan, 6)'."""
        sql = "SELECT d.* FROM fts JOIN docs d ON d.id = fts.rowid WHERE fts MATCH ?"
        if canonical_only:
            sql += " AND d.dup_of IS NULL"
        sql += " ORDER BY d.date IS NULL, d.date, d.id"
        if limit:
            sql += f" LIMIT {int(limit)}"
        return [self._doc(r) for r in self.con.execute(sql, (fts_query,))]

    def find_title(self, query, limit=20):
        """Docs whose title contains every word of the query (case-insensitive), most-cited-looking first is not attempted: ordered by date."""
        words = re.findall(r"[A-Za-z0-9]+", query)
        if not words:
            return []
        sql = "SELECT * FROM docs WHERE dup_of IS NULL AND " + " AND ".join("lower(title) LIKE ?" for _ in words) + " ORDER BY date IS NULL, date LIMIT ?"
        return [self._doc(r) for r in self.con.execute(sql, [f"%{w.lower()}%" for w in words] + [limit])]

    def by_cite(self, key):
        return [self._doc(r) for r in self.con.execute("SELECT * FROM docs WHERE dup_of IS NULL AND cites LIKE ?", (f'%"{key}"%',))]

    def docs_citing(self, keys, canonical_only=True):
        """Docs whose text contains any of the citation keys (a volume-less SCR key also matches the same page with any volume)."""
        if not self.has_cite_index:
            raise RuntimeError("no citation index: run `python -m goodlaw.corpus index-cites --db <corpus>` first")
        ks = set()
        for k in keys:
            ks |= C.key_variants(k)
            kind, year, series, page = C.parse_key(k)
            if kind == "scr" and not series:
                like = f"scr:{year}:%:{page}"
                ks |= {r[0] for r in self.con.execute("SELECT DISTINCT key FROM cx.doc_cites WHERE key LIKE ?", (like,))}
        if not ks:
            return []
        marks = ",".join("?" * len(ks))
        sql = (f"SELECT d.*, c.n AS n_in_text, c.key AS matched_key FROM cx.doc_cites c JOIN docs d ON d.id = c.doc_id WHERE c.key IN ({marks})"
               + (" AND d.dup_of IS NULL" if canonical_only else "") + " ORDER BY d.date IS NULL, d.date, d.id")
        out = []
        for r in self.con.execute(sql, list(ks)):
            d = self._doc(r)
            out.append(d)
        return out

    def doc_frequency(self, term):
        """How many texts contain the word (from the full-text index vocabulary)."""
        if not getattr(self, "_vocab", False):
            self.con.execute("CREATE VIRTUAL TABLE IF NOT EXISTS temp.fts_vocab USING fts5vocab(main, fts, 'row')")
            self._vocab = True
        r = self.con.execute("SELECT doc FROM temp.fts_vocab WHERE term = ?", (term.lower(),)).fetchone()
        return r[0] if r else 0

    def iter_docs(self, where="dup_of IS NULL", params=()):
        for r in self.con.execute(f"SELECT * FROM docs WHERE {where} ORDER BY id", params):
            yield self._doc(r)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--crawl-dir", default="../recourse-sci-pool-data")
    b.add_argument("--bucket-dir", default="../recourse-sci-bucket-data")
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    b.add_argument("--registry", default=os.path.join(here, "coverage", "bucket_match", "registry.csv.gz"))
    b.add_argument("--none-resolution", default=os.path.join(here, "coverage", "bucket_match", "none_resolution.csv.gz"))
    b.add_argument("--out", default="corpus.sqlite")
    b.add_argument("--workers", type=int, default=4)
    i = sub.add_parser("index-cites", help="add the table of reported citations found in each text")
    i.add_argument("--db", default="corpus.sqlite")
    i.add_argument("--workers", type=int, default=4)
    a = ap.parse_args(argv)
    if a.cmd == "index-cites":
        index_cites(a.db, a.workers)
        return 0
    build(a.crawl_dir, a.bucket_dir, a.registry, a.none_resolution, a.out, a.workers)
    return 0


if __name__ == "__main__":
    sys.exit(main())
