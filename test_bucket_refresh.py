"""Tests for bucket_refresh.py (fake bucket listing and metadata, real temporary git repo, no network). Run: python test_bucket_refresh.py"""
import csv
import gzip
import io
import os
import shutil
import subprocess
import tempfile
import urllib.parse
from datetime import datetime, timezone

import pyarrow as pa
import pyarrow.parquet as pq

import bucket_refresh as br

FAILURES = []
for k, v in (("GIT_AUTHOR_NAME", "t"), ("GIT_AUTHOR_EMAIL", "t@t"), ("GIT_COMMITTER_NAME", "t"), ("GIT_COMMITTER_EMAIL", "t@t")):
    os.environ[k] = v


def check(condition, description):
    print(f"[{'PASS' if condition else 'FAIL'}] {description}")
    if not condition:
        FAILURES.append(description)


def sh(*args, cwd=None):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True)


def parquet_bytes(rows):
    cols = ["title", "petitioner", "respondent", "citation", "case_id", "nc_display", "cnr", "judge", "disposal_nature", "available_languages", "decision_date", "path"]
    t = pa.table({c: [r.get(c) for r in rows] for c in cols})
    buf = io.BytesIO()
    pq.write_table(t, buf)
    return buf.getvalue()


# the fake bucket: three years of English files; 2026 has two new ones, 2025 has one new one, all others are known
FILES = {
    "data/pdf/year=2024/english/2024_1_1_10_EN.pdf": 1000,
    "data/pdf/year=2025/english/2025_1_1_10_EN.pdf": 2000,
    "data/pdf/year=2025/english/2025_9_90_99_EN.pdf": 2500,       # new
    "data/pdf/year=2026/english/2026_1_20_29_EN.pdf": 3000,       # new, later date
    "data/pdf/year=2026/english/2026_1_5_14_EN.pdf": 3500,        # new, earlier date
    "data/pdf/year=2026/english/2026_2_77_88_EN.pdf": 4000,       # new, no metadata row
}
META = {
    2025: [dict(title="A versus B", petitioner="A", respondent="B", citation="[2025] 9 S.C.R. 90", case_id="2025 INSC 1100", nc_display="2025INSC1100", cnr="X", judge="J", disposal_nature="Dismissed",
                available_languages="ENG", decision_date="20-12-2025", path="2025_9_90_99")],
    2026: [dict(title="C versus D", petitioner="C", respondent="D", citation="[2026] 1 S.C.R. 20", case_id="2026 INSC 5", nc_display="2026INSC5", cnr="Y", judge="K", disposal_nature="Allowed",
                available_languages="ENG", decision_date="09-01-2026", path="2026_1_20_29"),
           dict(title="E versus F", petitioner="E", respondent="F", citation="[2026] 1 S.C.R. 5", case_id="2026 INSC 3", nc_display="2026INSC3", cnr="Z", judge="L", disposal_nature="Allowed",
                available_languages="ENG", decision_date="05-01-2026", path="2026_1_5_14")],
}
calls = []


def xml(keys, prefixes=(), token=None, truncated=False):
    body = "".join(f"<Contents><Key>{k}</Key><LastModified>2026-06-04T00:00:00.000Z</LastModified><Size>{s}</Size></Contents>" for k, s in keys)
    body += "".join(f"<CommonPrefixes><Prefix>{p}</Prefix></CommonPrefixes>" for p in prefixes)
    if truncated:
        body += f"<IsTruncated>true</IsTruncated><NextContinuationToken>{token}</NextContinuationToken>"
    return f'<?xml version="1.0"?><ListBucketResult>{body}</ListBucketResult>'.encode()


def fake_get(url):
    calls.append(url)
    u = urllib.parse.urlparse(url)
    q = urllib.parse.parse_qs(u.query)
    if "metadata/parquet" in u.path:
        y = int(u.path.split("year=")[1].split("/")[0])
        if y not in META:
            raise RuntimeError("404")
        return parquet_bytes(META[y])
    prefix = q["prefix"][0]
    if prefix == "data/pdf/":
        return xml([], prefixes=["data/pdf/year=2024/", "data/pdf/year=2025/", "data/pdf/year=2026/"])
    items = sorted((k, s) for k, s in FILES.items() if k.startswith(prefix))
    if "continuation-token" not in q and len(items) > 2:       # force a second page for 2026
        return xml(items[:2], token="T1", truncated=True)
    if q.get("continuation-token") == ["T1"]:
        return xml(items[2:])
    return xml(items)


base = tempfile.mkdtemp(prefix="refresh_test_")
data = os.path.join(base, "data")
sh("git", "init", "-b", "claude/sci-bucket", data)
sh("git", "commit", "--allow-empty", "-m", "start", cwd=data)

reg = os.path.join(base, "registry.csv.gz")
with gzip.open(reg, "wt", encoding="utf-8", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["decision_date", "title", "path", "tier"])
    w.writerows([["01-01-2024", "OLD", "2024_1_1_10", "after"], ["01-01-2025", "OLD2", "2025_1_1_10", "after"]])

# listing pages are followed and years discovered from the bucket itself
listing = br.english_listing(fake_get)
check(len(listing) == 6 and listing["data/pdf/year=2026/english/2026_2_77_88_EN.pdf"] == 4000, "the listing follows continuation tokens and finds every year folder the bucket has")
check(br.path_of("data/pdf/year=2026/english/2026_1_20_29_EN.pdf") == "2026_1_20_29" and br.path_of("data/pdf/year=2026/regional/x.pdf") is None, "path_of reads English files only")

today = datetime(2026, 10, 12, 9, 0, tzinfo=timezone.utc)
res = br.plan(data, reg, today=today, get=fake_get)
check(res["scope"] == "refresh_20261012" and res["n"] == 4 and res["years"] == ["2025", "2026"], "the plan finds the four files not in the registry")
out = os.path.join(data, "state", "worklists", "refresh_20261012.csv.gz")
rows = list(csv.DictReader(gzip.decompress(open(out, "rb").read()).decode("utf-8").splitlines()))
check([r["path"] for r in rows[:3]] == ["2025_9_90_99", "2026_1_5_14", "2026_1_20_29"], "rows with metadata are sorted by decision date (December 2025 before January 2026)")
check(rows[-1]["path"] == "2026_2_77_88" and rows[-1]["tier"] == "refresh_nometa" and rows[-1]["title"] == "", "a file with no metadata row is listed last, with empty metadata and its own tier")
by = {r["path"]: r for r in rows}
check(by["2025_9_90_99"]["decision_date"] == "20-12-2025" and by["2025_9_90_99"]["case_id"] == "2025 INSC 1100" and by["2025_9_90_99"]["tier"] == "refresh", "metadata is attached from the year's metadata table")
check(by["2026_1_20_29"]["key"] == "data/pdf/year=2026/english/2026_1_20_29_EN.pdf" and by["2026_1_20_29"]["size"] == "3000" and by["2026_1_20_29"]["scope"] == "refresh_20261012", "key, size and scope are filled")
check(sh("git", "status", "--porcelain", cwd=data).stdout.strip() == "" and "work list refresh_20261012" in sh("git", "log", "-1", "--format=%s", cwd=data).stdout, "the work list is committed on the data branch")
check(not any("english" in c and ".pdf" in c and "list-type" not in c for c in calls), "no PDF is downloaded while planning")

# the work list works with the downloader
import sci_bucket
rows_back, sha = sci_bucket.load_worklist(out, "refresh_20261012")
check(len(rows_back) == 4 and len(sha) == 64, "sci_bucket.py reads the refresh work list")

# running again the same day reuses it; the next planning run sees these four as known
res2 = br.plan(data, reg, today=today, get=fake_get)
check(res2["n"] is None and "already planned" in res2["note"], "planning twice on one day reuses the first work list")
res3 = br.plan(data, reg, today=datetime(2026, 11, 12, tzinfo=timezone.utc), get=fake_get)
check(res3["n"] == 0 and "nothing new" in res3["note"], "a later run with no additions says nothing is new (earlier refresh lists count as known)")

# a new file appears later
FILES["data/pdf/year=2026/english/2026_3_1_9_EN.pdf"] = 100
META[2026].append(dict(title="G versus H", petitioner="G", respondent="H", citation="", case_id="2026 INSC 99", nc_display="", cnr="", judge="", disposal_nature="", available_languages="",
                       decision_date="15-02-2026", path="2026_3_1_9"))
res4 = br.plan(data, reg, today=datetime(2026, 12, 1, tzinfo=timezone.utc), get=fake_get)
check(res4["n"] == 1 and res4["scope"] == "refresh_20261201", "a later addition gives a new work list with only the new file")

# a metadata table that does not exist yet does not stop the plan
FILES["data/pdf/year=2027/english/2027_1_1_9_EN.pdf"] = 50
_orig = fake_get


def fake_get2(url):
    u = urllib.parse.urlparse(url)
    q = urllib.parse.parse_qs(u.query)
    if q.get("prefix") == ["data/pdf/"]:
        return xml([], prefixes=["data/pdf/year=2024/", "data/pdf/year=2025/", "data/pdf/year=2026/", "data/pdf/year=2027/"])
    return _orig(url)


res5 = br.plan(data, reg, today=datetime(2027, 1, 5, tzinfo=timezone.utc), get=fake_get2)
rows5 = list(csv.DictReader(gzip.decompress(open(res5["path"], "rb").read()).decode("utf-8").splitlines()))
check(res5["n"] == 1 and rows5[0]["tier"] == "refresh_nometa" and rows5[0]["path"] == "2027_1_1_9", "a new year with no metadata table yet is still listed")

shutil.rmtree(base, ignore_errors=True)
print()
if FAILURES:
    print(f"{len(FAILURES)} FAILED")
    for f in FAILURES:
        print(" -", f)
    raise SystemExit(1)
print("ALL PASSED")
