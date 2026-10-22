"""One searchable store (SQLite with full-text search) over every Supreme Court judgment we hold: the crawl (to 4 May 2017), the open bucket
(after that date, plus older judgments the crawl lacks) and the court's newer archive (from 1 May 2017). Built from the three data branches; rebuild it whenever any changes.

    python -m goodlaw.corpus build --crawl-dir ../recourse-sci-pool-data --bucket-dir ../recourse-sci-bucket-data --newer-dir ../recourse-sci-newer-data --out corpus.sqlite

One row per distinct judgment where it can tell. A judgment present in both the crawl and the bucket is stored once, from the crawl (the court's own file), and
takes the bucket's exact decision date, neutral citation and law-report citation. Judgments only the bucket holds are stored from the bucket.
Second copies inside the crawl are kept but marked `dup_of` the copy that is read; later steps count only rows with no `dup_of`.

The court's newer archive (branch `claude/sci-court-newer`; the court's own typeset PDFs, read as raw text) is added after the other rows, so no existing row id moves. All of
it is stored. A text its own `in_bucket` field says the bucket holds is stored as a second copy (`dup_of` the bucket row, found by decision date and the title the archive
recorded, which is cut at 60 characters), so the bucket's text stays the one that is read and counts do not change; the court's copy stays available for comparison. A text the bucket
lacks is stored as a judgment of its own. Several diary numbers can carry one judgment (consolidated matters): identical files, and texts with the same parties, the same decision
date and the same body, are marked `dup_of` the first. A text the archive says the bucket lacks is also compared by its words with the bucket texts dated within 3 days (the archive's marker misses a copy the bucket dates a day earlier or spells differently):
sharing at least half of the shorter text's 8-word runs makes it a second copy of that bucket text; sharing 30% with an agreeing title does too. A text that may duplicate another but is not certain gets `maybe_dup_of` and stays a judgment.

doc_key: `c<id>` for a crawl text (c37060), `b<path>` for a bucket text (b2019_5_569_578), `n<diary no>_<year>_<date>` for a newer-archive text (n39999_2014_2018-05-14).
"""
import argparse
import bisect
import collections
import csv
import datetime
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
CRAWL_LAST_DATE = "2017-05-04"      # the crawl ends here (coverage/COVERAGE_NOTE.md); the newer archive starts on 1 May 2017, so a few days can be in both
DEFAULT_NEWER = "../recourse-sci-newer-data"
# The archive's own `in_bucket` marker compares exact dates and titles, and misses copies the bucket dates a day earlier or spells differently ("MOHANLAL", "KERELA"); measured on the real
# archive (2026-10-22), 266 of its 3,747 "not in the bucket" texts had a bucket text within 3 days sharing at least half their 8-word runs. The bucket's typeset text has glued words and
# misread letters, so the same judgment can share well under half (0.2 to 0.5) when the title also agrees.
TEXT_DAYS = 3
TEXT_SAME, TEXT_SAME_TITLE, TEXT_MAYBE_TITLE = 0.5, 0.3, 0.2
IN_BUCKET = ("yes", "no", "beyond")  # the newer archive's own marker: the bucket holds the judgment / does not / it is newer than the bucket's last date

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


def read_newer(newer_dir):
    """The newer archive's records (one per judgment PDF), in file order. A record with no text, link or date is left out."""
    shards = os.path.join(newer_dir, "shards")
    if not os.path.isdir(shards):
        raise FileNotFoundError(f"no shards folder in {newer_dir}")
    recs = []
    for f in sorted(glob.glob(os.path.join(shards, "*.jsonl.gz"))):
        for line in gzip.open(f, "rt", encoding="utf-8"):
            r = json.loads(line)
            if not (r.get("text") and r.get("pdf_url") and r.get("decision_date")):
                continue
            if r.get("in_bucket") not in IN_BUCKET:
                raise ValueError(f"{r['pdf_url']}: in_bucket is {r.get('in_bucket')!r}, expected one of {IN_BUCKET}")
            recs.append(r)
    return recs


def newer_key(r):
    return "n" + re.sub(r"[^A-Za-z0-9]+", "_", r["diary_no"]).strip("_") + "_" + r["decision_date"]


def _squash(s):
    return re.sub(r"\s+", " ", s or "").strip().lower()


def link_newer(newer, bucket_recs):
    """{newer key: (kind, bucket path)}, kind 'dup' (a certain copy of that bucket text) or 'maybe'. A record the archive marks `yes` is a copy when exactly one bucket text of
    that decision date starts with the title the archive recorded (cut at 60 characters); with several it is 'maybe' (the first by path); with none it is left alone. A record
    marked `no` or `beyond` is 'maybe' only when a bucket text of the same date has the same two party names (the archive's marker may be wrong)."""
    by_date, by_names = collections.defaultdict(list), collections.defaultdict(list)
    for b in bucket_recs:
        d = _iso(b.get("decision_date"))
        by_date[d].append(b)
        kp, kr = name_key(b.get("petitioner")), name_key(b.get("respondent"))
        if kp and kr:
            by_names[(d, kp, kr)].append(b["path"])
    out = {}
    for r in newer:
        key = newer_key(r)
        if r["in_bucket"] == "yes":
            title = _squash(r.get("bucket_title"))
            paths = sorted({b["path"] for b in by_date.get(r["decision_date"], []) if title and _squash(b.get("title")).startswith(title)})
            if len(paths) == 1:
                out[key] = ("dup", paths[0])
            elif paths:
                out[key] = ("maybe", paths[0])
        else:
            kp, kr = name_key(r.get("petitioner")), name_key(r.get("respondent"))
            paths = sorted(set(by_names.get((r["decision_date"], kp, kr), []))) if kp and kr else []
            if paths:
                out[key] = ("maybe", paths[0])
    return out


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


def _runs(text, n=8, limit=20000):
    """The set of 8-word runs (hashed) of the first `limit` characters of a text."""
    w = norm_text(text[:limit])
    return {hash(" ".join(w[i:i + n])) for i in range(max(len(w) - n + 1, 0))}


def _title_words(title):
    return {w for w in name_key(title).split() if len(w) > 1}


def _titles_agree(a, b):
    wa, wb = _title_words(a), _title_words(b)
    return bool(wa and wb) and len(wa & wb) / len(wa | wb) >= 0.6


def match_by_text(added, bucket_recs, keys):
    """For each newer-archive judgment not yet known to be a copy: the bucket texts within TEXT_DAYS days of its date whose text shares enough 8-word runs (the share of the SHORTER text's runs).
    A share of TEXT_SAME, or of TEXT_SAME_TITLE with an agreeing title, makes it a copy (`dup_of`, `bucket_path`); TEXT_MAYBE_TITLE with an agreeing title makes it a `maybe_dup_of`. The best
    candidate by (kind, share) is used. Returns how many became copies and how many became maybes."""
    by_date = collections.defaultdict(list)
    for b in bucket_recs:
        if f"b{b['path']}" in keys:
            by_date[_iso(b.get("decision_date"))].append(b)
    cache = {}
    copies = maybes = 0
    for a in added:
        if a["dup_of"] is not None or not a["date"]:
            continue
        ra = _runs(a["text"])
        if not ra:
            continue
        day, best = datetime.date.fromisoformat(a["date"]), None
        for g in range(-TEXT_DAYS, TEXT_DAYS + 1):
            for b in by_date.get((day + datetime.timedelta(days=g)).isoformat(), []):
                if b["path"] not in cache:
                    cache[b["path"]] = _runs(b["text"])
                rb = cache[b["path"]]
                if not rb:
                    continue
                share = len(ra & rb) / min(len(ra), len(rb))
                agree = _titles_agree(a["title"], b.get("title"))
                kind = 2 if (share >= TEXT_SAME or (share >= TEXT_SAME_TITLE and agree)) else (1 if share >= TEXT_MAYBE_TITLE and agree else 0)
                if kind and (best is None or (kind, share) > best[:2]):
                    best = (kind, share, b["path"])
        if best and best[0] == 2:
            a["dup_of"], a["bucket_path"], a["maybe_dup_of"] = f"b{best[2]}", best[2], None
            copies += 1
        elif best:
            a["maybe_dup_of"] = a["maybe_dup_of"] or f"b{best[2]}"
            maybes += 1
    return copies, maybes


def court_bench(text):
    """(size, source) for a newer-archive text: the signature lines' count, always a lower bound ('signatures'), or (None, None). The court's own PDF has no law-report line, and the
    pattern that reads one (`H.bench_size`) mistakes phrases such as "one of us (Aftab Alam" for a judge list and would call that a complete bench, so it is not used here."""
    n = H.bench_from_signatures(text)
    return (n, "signatures") if n and n <= H.MAX_BENCH else (None, None)


def add_newer(rows, newer_dir, bucket_recs, log=print):
    """Appends the newer archive's texts to `rows` (after every existing row, so no id moves), sets their dup_of / maybe_dup_of, and returns the counts for the stats."""
    newer = read_newer(newer_dir)
    log(f"  {len(newer)} newer-archive texts")
    existing = {r["key"] for r in rows}
    links = link_newer(newer, bucket_recs)
    added = []
    for r in newer:
        key = newer_key(r)
        if key in existing:
            raise ValueError(f"two newer-archive records share the key {key}")
        existing.add(key)
        text = r["text"]
        size, bsrc = court_bench(text)
        kind, bpath = links.get(key, (None, None))
        bkey = f"b{bpath}" if bpath else None
        added.append(dict(key=key, source="court", src_id=r["pdf_url"], title=r.get("case_name") or None, pet=r.get("petitioner") or None, resp=r.get("respondent") or None,
                          date=r["decision_date"], date_source="court", year=int(r["decision_date"][:4]), bench_size=size, bench_source=bsrc, layout="court",
                          cites=C.cite_keys(r.get("neutral_citation") or ""), citator=[], bucket_path=bpath if kind == "dup" else None, insc=r.get("neutral_citation") or None,
                          scr_cite=None, dup_of=bkey if kind == "dup" else None, maybe_dup_of=bkey if kind == "maybe" else None, body_start=None, text_len=len(text),
                          scan_pages=None, text=text, _sha=r.get("sha256"), _in_bucket=r["in_bucket"]))
    keys = {x["key"] for x in rows}
    for a in added:                                  # a link to a bucket text that is not in the store (the crawl holds it) cannot be a dup_of
        for field in ("dup_of", "maybe_dup_of"):
            if a[field] and a[field] not in keys:
                if field == "dup_of":
                    a["bucket_path"] = None
                a[field] = None
    text_copies, text_maybes = match_by_text(added, bucket_recs, keys)     # copies the archive's own marker missed (a day's difference, a different spelling)
    by_sha = collections.defaultdict(list)           # one file served under several diary numbers
    for a in added:
        if a["_sha"]:
            by_sha[a["_sha"]].append(a)
    for group in by_sha.values():
        if len(group) > 1:
            group.sort(key=lambda a: (a["dup_of"] is None, a["key"]))
            first = group[0]
            for a in group[1:]:
                if a["dup_of"] is None:
                    a["dup_of"] = first["dup_of"] or first["key"]
    own = [dict(key=a["key"], pet=a["pet"], resp=a["resp"], year=a["date"], text=a["text"], text_len=a["text_len"], body_start=0) for a in added if a["dup_of"] is None]
    by_key = {a["key"]: a for a in added}
    for k, v in find_duplicates(own).items():       # the same parties, the same decision date and the same body
        by_key[k]["dup_of"] = v
    crawl_by = collections.defaultdict(list)         # the few days both the crawl and the newer archive cover
    for x in rows:
        if x["source"] == "crawl" and x["date"] and x["date"] <= CRAWL_LAST_DATE and x["pet"] and x["resp"] and not x["dup_of"]:
            crawl_by[(x["date"], name_key(x["pet"]), name_key(x["resp"]))].append(x["key"])
    for a in added:
        if a["dup_of"] is None and a["maybe_dup_of"] is None and a["date"] <= CRAWL_LAST_DATE and a["pet"] and a["resp"]:
            hit = crawl_by.get((a["date"], name_key(a["pet"]), name_key(a["resp"])))
            if hit:
                a["maybe_dup_of"] = sorted(hit)[0]
    rows.extend(added)
    stats = {"court": len(added), "court_copies_of_bucket": sum(1 for a in added if (a["dup_of"] or "").startswith("b")), "court_copies_found_by_text": text_copies,
             "court_second_copies_inside": sum(1 for a in added if (a["dup_of"] or "").startswith("n")),
             "court_judgments": sum(1 for a in added if a["dup_of"] is None), "court_uncertain": sum(1 for a in added if a["dup_of"] is None and a["maybe_dup_of"])}
    log(f"  newer archive: {stats}")
    return stats


# ---------------------------------------------------------------- the build
def build(crawl_dir, bucket_dir, registry_path, none_resolution_path, out_path, workers=4, log=print, newer_dir=None):
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
    newer_stats = add_newer(rows, newer_dir, bucket, log) if newer_dir else {}

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
             "bucket_skipped_because_crawl_holds_them": len(skip), **newer_stats}
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
            if kind == "scr" and series in ("", "s"):
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

    def phrase_df(self, phrase):
        """How many texts contain the exact phrase (full-text index)."""
        words = re.findall(r"[A-Za-z0-9]+", phrase)
        if not words:
            return 0
        return self.con.execute("SELECT COUNT(*) FROM fts WHERE fts MATCH ?", ('"' + " ".join(words) + '"',)).fetchone()[0]

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
    b.add_argument("--newer-dir", default=None, help=f"the newer archive's data branch (default {DEFAULT_NEWER} if it exists; none otherwise)")
    b.add_argument("--out", default="corpus.sqlite")
    b.add_argument("--workers", type=int, default=4)
    i = sub.add_parser("index-cites", help="add the table of reported citations found in each text")
    i.add_argument("--db", default="corpus.sqlite")
    i.add_argument("--workers", type=int, default=4)
    a = ap.parse_args(argv)
    if a.cmd == "index-cites":
        index_cites(a.db, a.workers)
        return 0
    newer = a.newer_dir or (DEFAULT_NEWER if os.path.isdir(DEFAULT_NEWER) else None)
    if newer is None:
        print(f"note: no newer archive at {DEFAULT_NEWER}; building from the crawl and the bucket only")
    build(a.crawl_dir, a.bucket_dir, a.registry, a.none_resolution, a.out, a.workers, newer_dir=newer)
    return 0


if __name__ == "__main__":
    sys.exit(main())
