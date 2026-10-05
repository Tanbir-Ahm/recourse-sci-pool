"""Builds year_counts.csv: how many Supreme Court judgments each source holds per year, next to Indian Kanoon's own yearly list.

Sources
  indiankanoon  typed from a screenshot of https://indiankanoon.org/browse/supremecourt/ taken 2026-10-05 (1968 to 2026). Not scraped.
  crawl         our crawl of api.sci.gov.in/jonew/judis (36,928 judgments). The decision year is ESTIMATED from the text:
                ids below 28,000 use the date in the old-format header, or the nearest dated neighbour by id; ids from 28,000 use the last
                date near the end of the text (see crawl_years.py). Single years near 2015 to 2017 are noisy; use period totals.
  bucket        the open 'indian-supreme-court-judgments' AWS bucket, one metadata table per year (CC-BY-4.0, Dattam Labs); distinct judgments
                by decision year (second listings of the same judgment removed; an earlier version of this file counted them twice).
  catalogue     Recourse's case_lookup_index.db (Vaquill dataset plus bucket additions), by decision year.

Inputs the crawl column needs (made by the other scripts in scripts_as_run/): crawl_table.json and crawl_years.json. Paths below are
hard-coded to the session where this ran; change them before running. Run: python year_counts.py
"""
import bisect, collections, csv, json, os, re, sqlite3
import pyarrow.parquet as pq

SCRATCH = "/tmp/claude-0/-home-user-recourse-sci-pool/33686f69-1895-5643-b31d-21bed3d4a6ee/scratchpad"
BUCKET_DIR = f"{SCRATCH}/bucket"                      # meta_<year>.parquet, downloaded from the bucket
CATALOGUE = "/home/user/tanbir-ahm/recourse/case_lookup_index.db"
IK = {1968: 393, 1969: 555, 1970: 428, 1971: 666, 1972: 616, 1973: 436, 1974: 456, 1975: 548, 1976: 524, 1977: 367, 1978: 420, 1979: 510, 1980: 469, 1981: 420, 1982: 228, 1983: 398, 1984: 368, 1985: 375, 1986: 472, 1987: 635, 1988: 530, 1989: 578, 1990: 738, 1991: 603, 1992: 774, 1993: 994, 1994: 1214, 1995: 1298, 1996: 2263, 1997: 1647, 1998: 1288, 1999: 1164, 2000: 1566, 2001: 1167, 2002: 1349, 2003: 1378, 2004: 1228, 2005: 950, 2006: 1250, 2007: 1590, 2008: 2835, 2009: 2218, 2010: 1381, 2011: 1271, 2012: 849, 2013: 1077, 2014: 882, 2015: 812, 2016: 745, 2017: 780, 2018: 1057, 2019: 1252, 2020: 688, 2021: 880, 2022: 1277, 2023: 1047, 2024: 1024, 2025: 1421, 2026: 983}

# The per-year tables list 5,181 judgments twice (same file path, date and title, once in the decision year's table and once in
# another year's), so a plain row count overstates the bucket by about 14% (43,333 rows, 38,152 distinct judgments). Count distinct ones.
import pandas as pd
_raw = pd.concat([pd.read_parquet(f"{BUCKET_DIR}/meta_{y}.parquet") for y in range(1950, 2027)], ignore_index=True)
_raw["_t"] = _raw.title.map(lambda s: re.sub(r"[^a-z0-9]+", " ", str(s).lower()).strip())
_distinct = _raw.drop_duplicates(["path", "decision_date", "_t"])
bucket = collections.Counter(int(d[-4:]) for d in _distinct.decision_date)
con = sqlite3.connect(f"file:{CATALOGUE}?mode=ro", uri=True)
catalogue = dict(con.execute("select cast(substr(decision_date,1,4) as int), count(*) from cases where decision_date is not null group by 1").fetchall())

rows = json.load(open(f"{SCRATCH}/crawl_table.json"))
late = {int(k): v for k, v in json.load(open(f"{SCRATCH}/crawl_years.json")).items()}
dated = {r["id"]: int(r["date"].split("/")[2]) for r in rows if r["date"] and re.match(r"\d{1,2}/\d{1,2}/\d{4}$", r["date"]) and r["id"] < 28000}
ids = sorted(dated)


def year_of(i):
    if i >= 28000:
        return late.get(i)
    if i in dated:
        return dated[i]
    k = bisect.bisect_left(ids, i)
    near = [ids[j] for j in (k - 1, k) if 0 <= j < len(ids)]
    return dated[min(near, key=lambda x: abs(x - i))]


crawl = collections.Counter(y for y in (year_of(r["id"]) for r in rows) if y)
with open("year_counts.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["year", "indiankanoon", "crawl_estimated", "bucket", "recourse_catalogue"])
    for y in range(1950, 2027):
        w.writerow([y, IK.get(y, ""), crawl.get(y, 0) if y <= 2017 else (crawl.get(y, 0) or 0), bucket.get(y, 0), catalogue.get(y, 0)])
tot = lambda d, a, b: sum(d.get(y, 0) for y in range(a, b + 1))
print(f"{'period':>10}{'IK':>8}{'crawl':>8}{'bucket':>8}{'catalogue':>10}")
for a, b in ((1968, 1979), (1980, 1989), (1990, 1999), (2000, 2004), (2005, 2009), (2010, 2014), (2015, 2017), (2018, 2025), (2026, 2026)):
    print(f"{a}-{b}:{tot(IK, a, b):>8}{tot(crawl, a, b):>8}{tot(bucket, a, b):>8}{tot(catalogue, a, b):>10}")
