"""Plans a refresh of the open-bucket text: finds judgments added to s3://indian-supreme-court-judgments since the last run and writes a work
list that sci_bucket.py then downloads.

    python bucket_refresh.py plan --data-dir ../recourse-sci-bucket-data

What counts as "already known": every file path in the registry (coverage/bucket_match/registry.csv.gz, which lists every bucket judgment as
of 2026-10-05, downloaded or matched to the crawl) and in every earlier refresh work list under state/worklists/ on the data branch. Anything
else in the bucket's English listing is new. Metadata (title, parties, date, citations) comes from the per-year metadata table of each year
that has new files. A file whose metadata row is missing is still listed, with empty metadata (tier refresh_nometa).

It writes state/worklists/refresh_<YYYYMMDD>.csv.gz on the data branch, commits it, and prints the scope name to pass to
`python sci_bucket.py shift --scope <scope> --worklist <that file>`. Needs `pip install pyarrow`. Downloads no PDF.
"""
import argparse
import csv
import glob
import gzip
import io
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

import sci_bucket

HOST = sci_bucket.HOST
DEFAULT_REGISTRY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "coverage", "bucket_match", "registry.csv.gz")
COLUMNS = ["scope", "decision_date", "path", "key", "size", "title", "petitioner", "respondent", "citation", "case_id", "nc_display", "cnr",
           "judge", "disposal_nature", "available_languages", "tier"]


def http_get(url, retries=3, timeout=120, sleep=time.sleep):
    last = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "recourse-sci-bucket/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:
            last = e
            if attempt < retries:
                sleep(2 ** attempt)
    raise RuntimeError(f"GET {url} failed: {last}")


def list_prefix(prefix, delimiter=None, get=http_get):
    """(list of (key, size), list of common prefixes) for one prefix of the public bucket, following continuation tokens."""
    keys, prefixes, token = [], [], None
    while True:
        q = {"list-type": "2", "prefix": prefix, "max-keys": "1000"}
        if delimiter:
            q["delimiter"] = delimiter
        if token:
            q["continuation-token"] = token
        x = get(HOST + "?" + urllib.parse.urlencode(q)).decode("utf-8")
        keys += [(k, int(sz)) for k, sz in re.findall(r"<Key>([^<]+)</Key>.*?<Size>(\d+)</Size>", x, re.S)]
        prefixes += re.findall(r"<CommonPrefixes><Prefix>([^<]+)</Prefix></CommonPrefixes>", x)
        m = re.search(r"<NextContinuationToken>([^<]+)</NextContinuationToken>", x)
        token = m.group(1) if m else None
        if not token:
            return keys, prefixes


def english_listing(get=http_get):
    """{key: size} for every English PDF in the bucket, whatever years exist now."""
    _, years = list_prefix("data/pdf/", delimiter="/", get=get)
    found = {}
    for y in sorted(years):
        keys, _ = list_prefix(y + "english/", get=get)
        found.update(dict(keys))
    return found


def path_of(key):
    m = re.match(r"^data/pdf/year=(\d{4})/english/(.+)_EN\.pdf$", key)
    return m.group(2) if m else None


def year_of(key):
    m = re.match(r"^data/pdf/year=(\d{4})/", key)
    return m.group(1) if m else None


def known_paths(registry_path, data_dir):
    known = set()
    if registry_path and os.path.exists(registry_path):
        raw = open(registry_path, "rb").read()
        text = gzip.decompress(raw).decode("utf-8") if raw[:2] == b"\x1f\x8b" else raw.decode("utf-8")
        known |= {r["path"] for r in csv.DictReader(text.splitlines())}
    for f in glob.glob(os.path.join(data_dir, "state", "worklists", "*.csv.gz")):
        text = gzip.decompress(open(f, "rb").read()).decode("utf-8")
        known |= {r["path"] for r in csv.DictReader(text.splitlines())}
    return known


def read_parquet_rows(data):
    import pyarrow.parquet as pq

    return pq.read_table(io.BytesIO(data)).to_pylist()


def _s(v):
    return "" if v is None else str(v)


def build_rows(scope, new, get=http_get):
    """new: {key: size}. Returns work-list rows (dicts), sorted by decision date then path."""
    meta = {}
    for y in sorted({year_of(k) for k in new}):
        try:
            for r in read_parquet_rows(get(HOST + f"metadata/parquet/year={y}/metadata.parquet")):
                meta.setdefault(r.get("path"), r)
        except Exception as e:  # a year with no metadata table yet: its files are listed without metadata
            print(f"warning: no metadata table for {y}: {e}", file=sys.stderr)
    rows = []
    for key, size in new.items():
        p = path_of(key)
        m = meta.get(p)
        row = {c: "" for c in COLUMNS}
        row.update(scope=scope, path=p, key=key, size=size, tier="refresh" if m else "refresh_nometa")
        if m:
            for c in COLUMNS:
                if c in m and c not in ("scope", "key", "size", "tier", "path"):
                    row[c] = _s(m[c])
        rows.append(row)

    def sort_key(r):
        try:
            d = datetime.strptime(r["decision_date"], "%d-%m-%Y")
        except ValueError:
            d = datetime(9999, 12, 31)
        return (d, r["path"])

    return sorted(rows, key=sort_key)


def plan(data_dir, registry_path=DEFAULT_REGISTRY, today=None, get=http_get, commit=True):
    today = today or datetime.now(timezone.utc)
    scope = f"refresh_{today:%Y%m%d}"
    rel = os.path.join("state", "worklists", f"{scope}.csv.gz")
    out = os.path.join(data_dir, rel)
    if os.path.exists(out):
        return {"scope": scope, "path": out, "n": None, "note": "this refresh was already planned today; use that work list"}
    listing = english_listing(get)
    known = known_paths(registry_path, data_dir)
    new = {k: s for k, s in listing.items() if path_of(k) and path_of(k) not in known}
    if not new:
        return {"scope": scope, "path": None, "n": 0, "note": f"nothing new: all {len(listing)} English files in the bucket are already known"}
    rows = build_rows(scope, new, get)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLUMNS)
    w.writeheader()
    w.writerows(rows)
    with gzip.open(out, "wt", encoding="utf-8", newline="") as fh:
        fh.write(buf.getvalue())
    if commit:
        for args in (("add", "--", rel), ("commit", "-m", f"work list {scope}: {len(rows)} new judgments")):
            p = subprocess.run(["git", "-C", data_dir, *args], capture_output=True, text=True)
            if p.returncode != 0:
                raise RuntimeError(f"git {args[0]} failed: {(p.stderr or p.stdout).strip()[-200:]}")
    years = sorted({year_of(k) for k in new})
    return {"scope": scope, "path": out, "n": len(rows), "years": years, "note": f"{len(rows)} new judgments in {', '.join(years)}"}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan", help="list what is new in the bucket and write a refresh work list")
    p.add_argument("--data-dir", default="../recourse-sci-bucket-data")
    p.add_argument("--registry", default=DEFAULT_REGISTRY)
    a = ap.parse_args(argv)
    res = plan(a.data_dir, a.registry)
    print(f"PLAN: {res['note']}")
    if res.get("path"):
        print(f"scope: {res['scope']}\nwork list: {res['path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
