"""sci_checker_names.py -- the names file for the invented-case check (2026-10-28, FOLLOW_UPS 2cp).

Recourse's checker (grounding_checks.check_cases -> checker_list.py, switch CHECKER_LIST=wide) looks a case name up in the Supreme Court title list (case_lookup_index.db, 38,026 titles to 12 Dec 2025) and,
with this file, also in every judgment the wide search index holds (Supreme Court and Gauhati High Court) and every judgment of the reviewed library. This script writes that file from the names table of the
index (names_table/names_table_<commit>.json.gz, built by names_table/build_names_table.py) and the library's chunk files. It holds names, courts and dates only: no judgment text, no links.

    python3 sci_checker_names.py export NAMES_TABLE.json.gz RECOURSE_DIR [--out FILE]   writes RECOURSE_DIR/checker_names.json.gz
    python3 sci_checker_names.py verify FILE NAMES_TABLE.json.gz RECOURSE_DIR              re-reads the file and compares it with its two sources (exit 1 on a difference)

Rebuild after any change of the index (the names table is built per index commit; the file records which one). Reads only; spends nothing. A judgment with no name in the names table (108 of 19,255 on
2026-10-26) cannot be looked up by name and is left out; the count is recorded in the file.
"""
import argparse
import glob
import gzip
import json
import os
import sys
import time

SCHEMA = "checker-names-1"
LIBRARY_COURT = "Reviewed library (court not recorded here)"


def _library_names(recourse_dir):
    out, seen = [], set()
    for f in sorted(glob.glob(os.path.join(recourse_dir, "chunks", "*_chunks.json"))):
        try:
            ch = json.load(open(f, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if not ch or not isinstance(ch[0], dict) or "case_name" not in ch[0]:
            continue
        nm = str(ch[0]["case_name"]).strip()
        if nm and nm.lower() not in seen:
            seen.add(nm.lower())
            out.append(nm)
    return out


def build(names_table_path, recourse_dir):
    nd = json.load(gzip.open(names_table_path, "rt", encoding="utf-8"))
    courts, sources = [], ["wide index", "library"]
    cidx = lambda c: courts.index(c) if c in courts else (courts.append(c) or len(courts) - 1)      # noqa: E731
    rows, seen, unnamed = [], set(), 0
    for r in nd["rows"]:
        name = (r.get("name") or "").strip()
        if not name:
            unnamed += 1
            continue
        key = (name.lower(), r.get("date"), r.get("court"))
        if key in seen:
            continue
        seen.add(key)
        rows.append([name, cidx(r.get("court")) if r.get("court") else None, r.get("date"), 0])
    n_wide = len(rows)
    have = {x[0].lower() for x in rows}
    for nm in _library_names(recourse_dir):
        if nm.lower() not in have:
            rows.append([nm, cidx(LIBRARY_COURT), None, 1])
    return {"schema": SCHEMA, "built": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "index_commit": nd.get("index_commit"), "names_table_schema": nd.get("schema"),
            "documents": nd.get("documents"), "named": nd.get("named"), "unnamed_left_out": unnamed, "wide_rows": n_wide, "library_rows": len(rows) - n_wide,
            "courts": courts, "sources": sources, "rows": rows}


def export(names_table_path, recourse_dir, out=None):
    data = build(names_table_path, recourse_dir)
    out = out or os.path.join(recourse_dir, "checker_names.json.gz")
    with gzip.open(out, "wt", encoding="utf-8", compresslevel=9) as fh:
        json.dump(data, fh, ensure_ascii=False, separators=(",", ":"))
    return out, data


def verify(path, names_table_path, recourse_dir):
    """[] when the file holds exactly what its two sources give now; else a list of differences."""
    problems = []
    f = json.load(gzip.open(path, "rt", encoding="utf-8"))
    want = build(names_table_path, recourse_dir)
    if f.get("schema") != SCHEMA:
        problems.append("schema " + str(f.get("schema")))
    if f.get("index_commit") != want["index_commit"]:
        problems.append(f"index commit {f.get('index_commit')} != {want['index_commit']}")
    got = sorted(((r[0], f["courts"][r[1]] if r[1] is not None else None, r[2], f["sources"][r[3]]) for r in f["rows"]), key=str)
    exp = sorted(((r[0], want["courts"][r[1]] if r[1] is not None else None, r[2], want["sources"][r[3]]) for r in want["rows"]), key=str)
    if got != exp:
        problems.append(f"rows differ: file {len(got)} against sources {len(exp)}")
    if len({(r[0].lower(), r[2]) for r in f["rows"]}) != len(f["rows"]):
        problems.append("duplicate name+date rows")
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export")
    e.add_argument("names_table")
    e.add_argument("recourse_dir")
    e.add_argument("--out")
    v = sub.add_parser("verify")
    v.add_argument("file")
    v.add_argument("names_table")
    v.add_argument("recourse_dir")
    a = ap.parse_args(argv)
    if a.cmd == "export":
        out, d = export(a.names_table, a.recourse_dir, a.out)
        print(f"wrote {out}: {d['wide_rows']} wide-index names, {d['library_rows']} library names, {d['unnamed_left_out']} unnamed left out, index commit {str(d['index_commit'])[:7]}, {os.path.getsize(out)} bytes")
        return 0
    problems = verify(a.file, a.names_table, a.recourse_dir)
    print("OK: the file holds exactly what its sources give" if not problems else "DIFFERENCES: " + "; ".join(problems))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
