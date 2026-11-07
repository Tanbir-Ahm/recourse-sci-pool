"""Reads the four Word files of the Supreme Court's archive list (SC_judgments_list_part1of4.docx ... part4of4.docx, made by the crawl report: every judgment the court's archive holds, with its archive id, an automatic type,
page count, the first 140 characters of the judgment and the address of the court's own PDF) and writes names_table/archive_list_<date>.json.gz: {"schema", "source", "rows": [[id, type, opening lines], ...]}.

    python names_table/archive_list_from_docx.py FILE1.docx FILE2.docx FILE3.docx FILE4.docx [--out names_table/archive_list_2026-11-07.json.gz]

Every row's address must be https://api.sci.gov.in/jonew/judis/<id>.pdf (checked here; the table of the Recourse site rebuilds the address from the id). Nothing here is verified or shown to users: 'Type' and the opening lines are read automatically and are rough.
"""
import argparse
import gzip
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def read(files):
    import docx
    rows, seen = [], set()
    for f in files:
        d = docx.Document(f)
        for r in d.tables[0].rows[1:]:
            c = [x.text for x in r.cells]
            i = int(c[0])
            if c[5] != f"https://api.sci.gov.in/jonew/judis/{i}.pdf":
                raise ValueError(f"{f}: id {i} has an unexpected address {c[5]!r}")
            if i in seen:
                raise ValueError(f"{f}: id {i} appears twice")
            seen.add(i)
            rows.append([i, c[1], c[4]])
    rows.sort()
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--out", default=os.path.join(HERE, "archive_list_2026-11-07.json.gz"))
    a = ap.parse_args(argv)
    rows = read(a.files)
    doc = {"schema": "archive-list-1", "built": time.strftime("%Y-%m-%d", time.gmtime()), "source": "the owner's four Word files SC_judgments_list_part1of4..4of4 (the crawl report of the Supreme Court archive)",
           "judgments": len(rows), "first_id": rows[0][0], "last_id": rows[-1][0], "rows": rows}
    with gzip.open(a.out, "wt", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, separators=(",", ":"))
    print(f"{len(rows)} judgments (ids {rows[0][0]} to {rows[-1][0]}) -> {a.out} ({os.path.getsize(a.out) / 1e6:.2f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
