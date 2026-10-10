"""Do Vaquill's High Court counts match the public AWS High Court bucket that Vaquill says its judgments come from?

Vaquill's README (lines 35 to 37, 424 to 428) says the judgment PDFs are on the AWS Open Data Registry ("Indian High Court Judgments", "~17.8M judgments, ~1.25 TiB", Dattam Labs, CC-BY-4.0)
and that it publishes "the layer they lack". The bucket lists its documents in per-year, per-court, per-bench metadata tables (`metadata/parquet/year=YYYY/court=C/bench=B/metadata.parquet`).
This script counts the rows of every table from its parquet footer (ONE small range request per file; no table is downloaded), names the 25 courts from the `court` column of each court's
smallest file, and sets the counts against Vaquill's own per-court, per-year table (`upstream_snapshot/data_coverage_02-judgments-by-year.csv`).

What a row is: one DOCUMENT of a case (the PDF name is `<CNR>_<order number>_<date>.pdf`), so a row may be an interim order, not only a final judgment; the metadata cannot tell the two apart
(`is_final` and `order_type` exist only in recent files and are almost empty; `pdf_exists` reads False on every sampled row, so it is not used). A gap between the bucket and Vaquill is therefore a gap
in DOCUMENTS; whether the missing ones are final judgments, interim orders or extraction failures is not known from metadata.

Network: anonymous GETs to the public bucket only; no spend; no Vaquill host (those answer 403 from this environment). Run time about 4 minutes the first time.
Run: python3 -P hc_aws_vs_vaquill.py --out-dir . [--cache-dir DIR]     (the cache holds the listing and the row counts so a re-run is instant)
"""
import argparse
import collections
import csv
import io
import json
import os
import re
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import pyarrow.parquet as pq

HERE = os.path.dirname(os.path.abspath(__file__))
BUCKET = "https://indian-high-court-judgments.s3.ap-south-1.amazonaws.com/"
VAQUILL_CSV = os.path.join(HERE, "upstream_snapshot", "data_coverage_02-judgments-by-year.csv")
VAQUILL_HELD_CSV = os.path.join(HERE, "upstream_snapshot", "data_coverage_09-held-vs-embedded.csv")

# the `court` value of each court's files -> the column name in Vaquill's table
ALIAS = {"Patna High Court": "Patna", "High Court of Sikkim": "Sikkim", "High Court of Manipur": "Manipur", "High Court of Tripura": "Tripura", "High Court of Meghalaya": "Meghalaya",
         "Gauhati High Court": "Gauhati", "Calcutta High Court": "Calcutta", "High Court of Jammu and Kashmir": "Jammu and Kashmir", "High Court of Jharkhand": "Jharkhand",
         "Orissa High Court": "Orissa", "High Court Of Chhattisgarh": "Chhattisgarh", "High Court of Madhya Pradesh": "Madhya Pradesh", "High Court of Gujarat": "Gujarat",
         "Bombay High Court": "Bombay", "High Court of Andhra Pradesh": "Andhra Pradesh", "High Court of Karnataka": "Karnataka", "High Court of Himachal Pradesh": "Himachal Pradesh",
         "High Court of Kerala": "Kerala", "Madras High Court": "Madras", "High Court  for State of Telangana": "Telangana", "High Court of Punjab and Haryana": "Punjab and Haryana",
         "High Court of Uttarakhand": "Uttarakhand", "High Court of Delhi": "Delhi", "High Court Of Rajasthan": "Rajasthan", "Allahabad High Court": "Allahabad"}


class RangeFile(io.RawIOBase):
    """Read-only seekable file over an HTTPS URL using Range requests; the last 512 KB are cached (enough for a parquet footer)."""

    def __init__(self, url, size, tail=512 * 1024, timeout=60):
        self.url, self.size, self.pos, self.timeout = url, size, 0, timeout
        self.tail_start, self._tail = max(0, size - tail), None

    def _get(self, start, end):
        req = urllib.request.Request(self.url, headers={"Range": f"bytes={start}-{end}"})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return r.read()

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else (self.pos + off if whence == 1 else self.size + off)
        return self.pos

    def read(self, n=-1):
        if n is None or n < 0:
            n = self.size - self.pos
        n = min(n, self.size - self.pos)
        if n <= 0:
            return b""
        a, b = self.pos, self.pos + n - 1
        if a >= self.tail_start:
            if self._tail is None:
                self._tail = self._get(self.tail_start, self.size - 1)
            out = self._tail[a - self.tail_start: b - self.tail_start + 1]
        else:
            out = self._get(a, b)
        self.pos += len(out)
        return out

    def readinto(self, buf):
        d = self.read(len(buf))
        buf[:len(d)] = d
        return len(d)


def retry(fn, tries=6):
    for i in range(tries):
        try:
            return fn()
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(1 + 2 * i)


def list_keys():
    keys, token = [], None
    while True:
        q = {"list-type": "2", "prefix": "metadata/parquet/", "max-keys": "1000"}
        if token:
            q["continuation-token"] = token
        x = retry(lambda: urllib.request.urlopen(BUCKET + "?" + urllib.parse.urlencode(q), timeout=60).read().decode())
        for block in re.findall(r"<Contents>(.*?)</Contents>", x, flags=re.S):
            keys.append((re.search(r"<Key>([^<]+)</Key>", block).group(1), int(re.search(r"<Size>(\d+)</Size>", block).group(1))))
        m = re.search(r"<NextContinuationToken>([^<]+)</NextContinuationToken>", x)
        if not m:
            return keys
        token = m.group(1)


def url_of(key):
    return BUCKET + urllib.parse.quote(key, safe="/")


def footer_rows(item):
    key, size = item
    return key, size, retry(lambda: pq.ParquetFile(RangeFile(url_of(key), size)).metadata.num_rows)


def court_name(files):
    size, key = sorted(files)[0]                                  # the court's smallest file
    pf = retry(lambda: pq.ParquetFile(RangeFile(url_of(key), size)))
    vals = retry(lambda: pf.read_row_group(0, columns=["court"]).to_pydict()["court"])
    return collections.Counter(vals).most_common(1)[0][0]


def vaquill_table(path):
    lines = open(path, encoding="utf-8").read().splitlines()
    hdr = next(i for i, l in enumerate(lines) if l.startswith("Year,"))
    out = collections.defaultdict(dict)
    for r in csv.DictReader(lines[hdr:]):
        if not r["Year"].strip().isdigit():
            continue
        for col, v in r.items():
            if col in ("Year", "All courts", "Supreme Court of India") or not (v or "").strip():
                continue
            out[col][int(r["Year"])] = int(v.replace(",", ""))
    return out


def vaquill_held(path):
    """Vaquill's own 'held vs embedded' table: court -> extracted texts it holds in its R2 store (measured 2026-08-14, its COVERAGE.md lines 155 to 175)."""
    out = {}
    for r in csv.DictReader(open(path, encoding="utf-8")):
        if r["Court"] and r["Court"] != "Total":
            out[re.sub(r" High Court$", "", r["Court"])] = int(r["Extracted texts in R2"])
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--cache-dir")
    a = ap.parse_args(argv)
    cache = (lambda n: os.path.join(a.cache_dir, n)) if a.cache_dir else (lambda n: None)
    if a.cache_dir:
        os.makedirs(a.cache_dir, exist_ok=True)

    if cache("hc_keys.json") and os.path.exists(cache("hc_keys.json")):
        keys = [tuple(x) for x in json.load(open(cache("hc_keys.json")))]
    else:
        keys = list_keys()
        if cache("hc_keys.json"):
            json.dump(keys, open(cache("hc_keys.json"), "w"))
    if cache("hc_rows.json") and os.path.exists(cache("hc_rows.json")):
        rows = [tuple(x) for x in json.load(open(cache("hc_rows.json")))]
    else:
        with ThreadPoolExecutor(12) as ex:
            rows = list(ex.map(footer_rows, keys))
        if cache("hc_rows.json"):
            json.dump(rows, open(cache("hc_rows.json"), "w"))

    by_code, aws = collections.defaultdict(list), collections.defaultdict(collections.Counter)
    for key, size, n in rows:
        m = re.search(r"year=(\d+)/court=([^/]+)/", key)
        by_code[m.group(2)].append((size, key))
        aws[m.group(2)][int(m.group(1))] += n
    if cache("hc_names.json") and os.path.exists(cache("hc_names.json")):
        names = json.load(open(cache("hc_names.json")))
    else:
        names = {c: court_name(f) for c, f in by_code.items()}
        if cache("hc_names.json"):
            json.dump(names, open(cache("hc_names.json"), "w"))
    vq = vaquill_table(VAQUILL_CSV)
    held = vaquill_held(VAQUILL_HELD_CSV)

    table, gaps = [], []
    for code, nm in names.items():
        vname = ALIAS[nm]
        a_all, a_to25 = sum(aws[code].values()), sum(v for y, v in aws[code].items() if y <= 2025)
        v_all = sum(vq[vname].values())
        table.append({"court": vname, "aws_code": code, "aws_rows": a_all, "aws_rows_through_2025": a_to25, "vaquill": v_all, "vaquill_share_of_aws_through_2025": round(v_all / a_to25, 4),
                      "aws_first_year": min(aws[code]), "vaquill_first_year": min(vq[vname]),
                      "vaquill_extracted_texts_held": held[vname], "vaquill_held_share_of_aws_through_2025": round(held[vname] / a_to25, 4)})
        for y, n in aws[code].items():
            if y <= 2025:
                gaps.append({"court": vname, "year": y, "aws_rows": n, "vaquill": vq[vname].get(y, 0), "gap": n - vq[vname].get(y, 0)})
        for y, v in vq[vname].items():
            if y not in aws[code]:
                gaps.append({"court": vname, "year": y, "aws_rows": 0, "vaquill": v, "gap": -v})
    table.sort(key=lambda r: -r["aws_rows"])
    gaps.sort(key=lambda g: -g["gap"])
    pos = sum(g["gap"] for g in gaps if g["gap"] > 0)
    tot_aws, tot_aws25, tot_v = (sum(r[k] for r in table) for k in ("aws_rows", "aws_rows_through_2025", "vaquill"))
    out = {
        "what": "row counts of the public AWS High Court metadata tables (footers only) against Vaquill's own per-court, per-year table (README 'Courts', data/coverage/02-judgments-by-year.csv)",
        "aws": {"metadata_files": len(keys), "rows_all_years": tot_aws, "rows_2026": tot_aws - tot_aws25, "rows_through_2025": tot_aws25, "courts": len(table)},
        "vaquill_high_court_total": tot_v, "vaquill_share_of_aws_rows_through_2025": round(tot_v / tot_aws25, 4),
        "vaquill_extracted_texts_held_total": sum(held.values()), "vaquill_held_share_of_aws_rows_through_2025": round(sum(held.values()) / tot_aws25, 4),
        "vaquill_readme_says_aws_holds": "~17.8M judgments, ~1.25 TiB (README lines 424 to 428)", "vaquill_share_of_that_17_8M": round(tot_v / 17_800_000, 4),
        "by_court": table,
        "court_years_with_a_gap": sum(1 for g in gaps if g["gap"] > 0), "sum_of_gaps": pos, "share_of_the_gaps_in_the_25_largest_court_years": round(sum(g["gap"] for g in gaps[:25]) / pos, 4),
        "largest_gaps": gaps[:30],
        "court_years_where_vaquill_exceeds_the_bucket": [g for g in gaps if g["gap"] < 0],
        "caution": "A row is a document of a case (an order or a judgment). Vaquill may have left out interim orders on purpose; the metadata cannot say. The comparison shows where Vaquill holds fewer documents than the bucket it cites, not that those are all judgments.",
    }
    with open(os.path.join(a.out_dir, "hc_aws_vs_vaquill.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print(f"AWS rows {tot_aws:,} (through 2025: {tot_aws25:,}); Vaquill {tot_v:,} = {100 * tot_v / tot_aws25:.0f}% of the bucket's rows through 2025, {100 * tot_v / 17_800_000:.0f}% of the 17.8M its README cites")
    for r in table:
        print(f"{r['court']:20s} AWS {r['aws_rows_through_2025']:>10,}  Vaquill published {r['vaquill']:>10,} ({100 * r['vaquill_share_of_aws_through_2025']:3.0f}%)  Vaquill held texts {r['vaquill_extracted_texts_held']:>10,} ({100 * r['vaquill_held_share_of_aws_through_2025']:3.0f}%)")
    print("largest gaps:", [(g["court"], g["year"], g["aws_rows"], g["vaquill"]) for g in gaps[:8]])


if __name__ == "__main__":
    main()
