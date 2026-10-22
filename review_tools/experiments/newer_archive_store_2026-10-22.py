"""What did adding the court's newer archive do to the text store? Reads the store (and the old store, if given) only: no network, no spend.

    python review_tools/experiments/newer_archive_store_2026-10-22.py --new corpus.sqlite.new --old corpus.sqlite --out review_results/2026-10-22_newer_archive_store

Checks that no row that was already in the old store changed (same id, same columns, same text length), counts the newer-archive rows by what the build made of them, and lists the ones a person may want
to look at: the second copies inside the archive and the judgments the build could not be sure about.
"""
import argparse
import json
import os
import sqlite3

COLS = "id,doc_key,source,src_id,title,pet,resp,date,date_source,year,bench_size,bench_source,layout,cites,citator,bucket_path,insc,scr_cite,dup_of,maybe_dup_of,body_start,text_len,scan_pages"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--new", required=True)
    ap.add_argument("--old")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    con = sqlite3.connect(f"file:{a.new}?mode=ro", uri=True)
    q = lambda sql, *p: con.execute(sql, p).fetchall()
    res = {"stats": json.loads(q("select v from meta where k='stats'")[0][0])}
    if a.old:
        con.execute("ATTACH DATABASE ? AS old", (f"file:{a.old}?mode=ro",))
        n_old = q("select count(*) from old.docs")[0][0]
        res["old_rows"] = n_old
        res["old_rows_that_differ"] = q(f"select count(*) from (select {COLS} from old.docs except select {COLS} from main.docs where id <= ?)", n_old)[0][0]
        res["old_text_lengths_that_differ"] = q("select count(*) from (select id, length(text) from old.texts except select id, length(text) from main.texts where id <= ?)", n_old)[0][0]
    res["distinct_by_source"] = dict(q("select source, count(*) from docs where dup_of is null group by source"))
    res["distinct_total"] = sum(res["distinct_by_source"].values())
    res["court_rows_by_outcome"] = dict(q("""select case when dup_of like 'b%' then 'copy of a bucket text' when dup_of like 'n%' then 'second copy inside the archive'
                                             when maybe_dup_of is not null then 'judgment, uncertain' else 'judgment' end, count(*) from docs where source='court' group by 1"""))
    res["court_judgments_by_year"] = dict(q("select year, count(*) from docs where source='court' and dup_of is null group by year order by year"))
    res["court_judgments_with_neutral_citation"] = q("select count(*) from docs where source='court' and dup_of is null and insc is not null and insc != ''")[0][0]
    res["court_bench_source"] = dict(q("select coalesce(bench_source,'none'), count(*) from docs where source='court' and dup_of is null group by 1"))
    res["second_copies_inside_the_archive"] = [dict(zip(("doc_key", "dup_of", "date", "title"), r)) for r in q("select doc_key, dup_of, date, title from docs where source='court' and dup_of like 'n%' order by doc_key")]
    res["uncertain_judgments"] = [dict(zip(("doc_key", "maybe_dup_of", "date", "title"), r)) for r in q("select doc_key, maybe_dup_of, date, title from docs where source='court' and dup_of is null and maybe_dup_of is not null order by doc_key")]
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "numbers.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
        fh.write("\n")
    print(json.dumps({k: v for k, v in res.items() if k not in ("second_copies_inside_the_archive", "uncertain_judgments")}, indent=1))


if __name__ == "__main__":
    main()
