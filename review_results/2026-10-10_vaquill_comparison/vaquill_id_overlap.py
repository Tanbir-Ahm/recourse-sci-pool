"""Is every Supreme Court judgment in Vaquill's dataset also in the open AWS bucket we hold, and what does the bucket hold that Vaquill lacks?

Inputs (read only):
  --catalogue   Recourse's case_lookup_index.db (read-only checkout). Its rows with source IS NULL were built from Vaquill's Supreme Court parquet
                (one row per case id that has English text, see case_lookup.build_index); rows with source='bucket' were added later by Recourse from the
                bucket's own case list (extend_index_from_bucket.py).
  --bucket-dir  directory of meta_<year>.parquet: the open bucket's per-year metadata tables (1950 to 2026; CC-BY-4.0, Dattam Labs).
Output: --out (JSON). No network, no spend, no judgment text is read. Run with `python3 -P` (not `-I`) from a directory that holds no data files.

Run: python3 -P vaquill_id_overlap.py --catalogue /home/user/tanbir-ahm/recourse/case_lookup_index.db --bucket-dir <scratch>/bucket --out vaquill_id_overlap.json
"""
import argparse
import collections
import glob
import json
import os
import re
import sqlite3

import pyarrow.parquet as pq


def year_of_id(cid):
    m = re.match(r"^(\d{4})_", cid or "")
    return int(m.group(1)) if m else None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--catalogue", required=True)
    ap.add_argument("--bucket-dir", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)

    con = sqlite3.connect(f"file:{a.catalogue}?mode=ro", uri=True)
    vq = {}                                   # case id -> decision date, rows built from Vaquill's parquet
    vq_full = {}                              # case id -> (title, petitioner, decision date, citation, source_url)
    added = {}                                # rows Recourse added from the bucket's own list
    for cid, dd, src, title, pet, cit, url in con.execute("select case_id, decision_date, source, title, petitioner, citation, source_url from cases"):
        if src is None:
            vq[cid] = dd or ""
            vq_full[cid] = (title, pet, dd, cit, url)
        else:
            added[cid] = dd or ""
    con.close()

    bucket = {}                               # normalised neutral-citation id -> decision date (dd-mm-yyyy)
    bucket_full = {}                          # the first bucket row listed under each id
    rows_total = rows_with_id = 0
    for f in sorted(glob.glob(os.path.join(a.bucket_dir, "meta_*.parquet"))):
        for r in pq.read_table(f, columns=["case_id", "title", "petitioner", "decision_date", "citation"]).to_pylist():
            rows_total += 1
            cid = re.sub(r"\s+", "_", (r["case_id"] or "").strip())
            if cid:
                rows_with_id += 1
                bucket.setdefault(cid, r["decision_date"] or "")
                bucket_full.setdefault(cid, r)

    both = set(vq) & set(bucket)
    vq_only = set(vq) - set(bucket)
    bucket_not_vq = set(bucket) - set(vq)
    added_in_bucket_ids = set(added) & set(bucket)

    norm = lambda t: re.sub(r"[^a-z0-9]", "", (t or "").lower())

    def iso(d):
        m = re.match(r"^\s*(\d{1,2})-(\d{1,2})-(\d{4})\s*$", d or "")
        return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else None
    same = collections.Counter()
    for cid in both:
        t, pet, dd, cit, url = vq_full[cid]
        b = bucket_full[cid]
        same["title"] += norm(t) == norm(b["title"])
        same["petitioner"] += norm(pet) == norm(b["petitioner"])
        same["decision_date"] += dd == iso(b["decision_date"])
        same["citation"] += norm(cit) == norm(b["citation"])
    fill = {"rows": len(vq_full),
            "with_law_report_citation": sum(1 for v in vq_full.values() if (v[3] or "").strip()),
            "with_source_url": sum(1 for v in vq_full.values() if (v[4] or "").strip())}

    by_year = lambda ids: dict(sorted(collections.Counter(y for y in map(year_of_id, ids) if y).items()))
    date_year = lambda d: int(d[:4]) if re.match(r"^\d{4}-", d or "") else None
    vq_by_date_year = dict(sorted(collections.Counter(y for y in map(date_year, vq.values()) if y).items()))
    added_by_date_year = dict(sorted(collections.Counter(y for y in map(date_year, added.values()) if y).items()))

    out = {
        "what": "id-level overlap between the case list built from Vaquill's Supreme Court parquet (2026-08 snapshot, read by Recourse) and the open AWS bucket's metadata tables",
        "catalogue_rows_built_from_vaquill": len(vq),
        "catalogue_rows_added_from_bucket_by_recourse": len(added),
        "bucket_metadata_rows": rows_total, "bucket_rows_with_a_neutral_citation_id": rows_with_id, "bucket_distinct_neutral_ids": len(bucket),
        "vaquill_ids_also_in_bucket": len(both), "vaquill_only": len(vq_only), "vaquill_only_examples": sorted(vq_only)[:10],
        "bucket_ids_not_in_vaquill": len(bucket_not_vq),
        "metadata_of_the_shared_ids_identical_to_the_bucket's": {k: round(v / len(both), 4) for k, v in same.items()},
        "vaquill_built_rows_fill_rates_as_read_by_recourse": fill,
        "share_of_bucket_ids_that_vaquill_has": round(len(both) / len(bucket), 4),
        "bucket_ids_not_in_vaquill_by_id_year": by_year(bucket_not_vq),
        "bucket_ids_not_in_vaquill_top_years": collections.Counter(by_year(bucket_not_vq)).most_common(8),
        "recourse_bucket_additions_by_date_year_top": collections.Counter(added_by_date_year).most_common(8),
        "recourse_bucket_additions_that_have_a_neutral_id_in_bucket": len(added_in_bucket_ids),
        "recourse_bucket_additions_keyed_by_law_report_citation_instead": len(added) - len(added_in_bucket_ids),
        "vaquill_rows_by_decision_year": vq_by_date_year,
        "recourse_bucket_additions_by_decision_year": added_by_date_year,
    }
    out["note"] = ("Case ids use one scheme on both sides ('2025_INSC_605'). 'vaquill_only' = 0 means no Supreme Court judgment in the Vaquill-built list is absent from the bucket's list; "
                   "it says nothing about whether the TEXT is the same (see vaquill_text_compare.py).")
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print(json.dumps({k: v for k, v in out.items() if not isinstance(v, dict) and k != "note"}, indent=1))


if __name__ == "__main__":
    main()
