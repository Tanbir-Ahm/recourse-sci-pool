"""Vaquill's Supreme Court judgments per period next to what our sources hold.

Columns (judgments per period; every source counted by decision year):
  IK        Indian Kanoon's own yearly list (1968 to 2026), typed from a screenshot on 2026-10-05, NOT scraped        -> coverage/year_counts.csv
  crawl     our crawl of api.sci.gov.in/jonew/judis (36,928 judgments, ends 4 May 2017); decision year ESTIMATED    -> coverage/year_counts.csv
  bucket    the open AWS bucket 'indian-supreme-court-judgments' (CC-BY-4.0, Dattam Labs), distinct judgments       -> coverage/year_counts.csv
  vq_table  Vaquill's own published table (data/coverage/02-judgments-by-year.csv, README 'Courts'), fetched 2026-10-10 -> upstream_snapshot/vaquill_sc_by_year.json
  vq_rows   the rows of Vaquill's parquet as read by Recourse (case ids with English text), by decision year         -> vaquill_id_overlap.json
Inputs are files in this repository; no network. Run from the repository root:
  python3 review_results/2026-10-10_vaquill_comparison/vaquill_vs_ours.py
Writes vaquill_vs_ours.json next to this file and prints a markdown table.
"""
import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))

PERIODS = [("1950-67", 1950, 1967), ("1968-79", 1968, 1979), ("1980-89", 1980, 1989), ("1990-99", 1990, 1999), ("2000-04", 2000, 2004), ("2005-09", 2005, 2009),
           ("2010-14", 2010, 2014), ("2015-17", 2015, 2017), ("2018-23", 2018, 2023), ("2024-25", 2024, 2025), ("2026", 2026, 2026)]


def load():
    yc = {}
    with open(os.path.join(ROOT, "coverage", "year_counts.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            yc[int(r["year"])] = {k: (int(v) if v not in ("", None) else None) for k, v in r.items() if k != "year"}
    vq_table = {int(k): v for k, v in json.load(open(os.path.join(HERE, "upstream_snapshot", "vaquill_sc_by_year.json"))).items()}
    ov = json.load(open(os.path.join(HERE, "vaquill_id_overlap.json")))
    vq_rows = {int(k): v for k, v in ov["vaquill_rows_by_decision_year"].items()}
    return yc, vq_table, vq_rows


def add(vals):
    got = [v for v in vals if v is not None]
    return sum(got) if got else None


def main():
    yc, vq_table, vq_rows = load()
    series = lambda col: {y: yc[y][col] for y in yc}
    cols = {"IK": series("indiankanoon"), "crawl": series("crawl_estimated"), "bucket": series("bucket"), "vq_table": {y: vq_table.get(y) for y in range(1950, 2027)},
            "vq_rows": {y: vq_rows.get(y, 0) for y in range(1950, 2027)}}
    out = {"periods": {}, "years_where_vaquill_holds_under_70_percent_of_the_bucket": {}, "totals": {}}
    for name, lo, hi in PERIODS:
        row = {c: add(cols[c].get(y) for y in range(lo, hi + 1)) for c in cols}
        out["periods"][name] = row
    for c in cols:
        out["totals"][f"{c} 1950-2025"] = add(cols[c].get(y) for y in range(1950, 2026))
        out["totals"][f"{c} 1968-2025"] = add(cols[c].get(y) for y in range(1968, 2026))
    for y in range(1950, 2027):
        b, v = cols["bucket"][y], cols["vq_rows"][y]
        if b and v < 0.7 * b:
            out["years_where_vaquill_holds_under_70_percent_of_the_bucket"][y] = {"bucket": b, "vq_rows": v, "vq_table": cols["vq_table"][y], "IK": cols["IK"][y]}
    out["differences_between_vaquill_table_and_vaquill_rows"] = {
        "years_differing_by_more_than_50": {y: cols["vq_rows"][y] - cols["vq_table"][y] for y in range(1950, 2026) if abs(cols["vq_rows"][y] - cols["vq_table"][y]) > 50},
        "sum_of_positive_differences": sum(d for d in (cols["vq_rows"][y] - cols["vq_table"][y] for y in range(1950, 2026)) if d > 0),
        "sum_of_negative_differences": sum(d for d in (cols["vq_rows"][y] - cols["vq_table"][y] for y in range(1950, 2026)) if d < 0),
        "note": "Vaquill's published yearly table and the rows of its parquet (as read by Recourse) differ year by year; cause not known (the table says 'measured July 2026', the parquet is the v2026.08.1 snapshot)."}
    json.dump(out, open(os.path.join(HERE, "vaquill_vs_ours.json"), "w"), indent=1)

    pc = lambda a, b: "-" if not a or not b else f"{100 * a / b:.0f}%"
    n = lambda x: "-" if x is None else f"{x:,}"
    print("| Period | IK | our crawl (est.) | open bucket | Vaquill (own table) | Vaquill rows read by Recourse | Vaquill table as share of bucket |")
    print("|---|---|---|---|---|---|---|")
    for name, row in out["periods"].items():
        print(f"| {name} | {n(row['IK'])} | {n(row['crawl'])} | {n(row['bucket'])} | {n(row['vq_table'])} | {n(row['vq_rows'])} | {pc(row['vq_table'], row['bucket'])} |")
    t = out["totals"]
    print(f"| 1950-2025 | {n(t['IK 1950-2025'])} (IK starts 1968) | {n(t['crawl 1950-2025'])} | {n(t['bucket 1950-2025'])} | {n(t['vq_table 1950-2025'])} | {n(t['vq_rows 1950-2025'])} | {pc(t['vq_table 1950-2025'], t['bucket 1950-2025'])} |")
    print(f"| 1968-2025 | {n(t['IK 1968-2025'])} | {n(t['crawl 1968-2025'])} | {n(t['bucket 1968-2025'])} | {n(t['vq_table 1968-2025'])} | {n(t['vq_rows 1968-2025'])} | {pc(t['vq_table 1968-2025'], t['bucket 1968-2025'])} |")
    print("years where Vaquill's parquet rows are under 70% of the bucket:", json.dumps(out["years_where_vaquill_holds_under_70_percent_of_the_bucket"]))
    print("table vs rows:", json.dumps(out["differences_between_vaquill_table_and_vaquill_rows"]))


if __name__ == "__main__":
    main()
