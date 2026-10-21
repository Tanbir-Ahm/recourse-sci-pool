"""Audit of the fetching: every link in every month's links_all.txt must have a row in that month's results.csv, every English judgment must be `ok`,
and every `ok` judgment must be in its monthly text shard on the data branch. Prints a summary and lists what is not clean.
Usage: python3 -I audit_fetch.py DATA_WORKTREE"""
import csv, glob, gzip, json, os, re, sys
data = sys.argv[1]
shard_urls = set()
for f in glob.glob(os.path.join(data, "shards", "*.jsonl.gz")):
    for line in gzip.open(f, "rt", encoding="utf-8"): shard_urls.add(json.loads(line)["pdf_url"])
tot = dict(links=0, english=0, ok=0, vernacular=0, no_diary=0, other=0); problems = []; pending = []
for d in sorted(glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), "20[0-9][0-9]-[0-9][0-9]*"))):
    lf, rf = os.path.join(d, "links_all.txt"), os.path.join(d, "results.csv")
    if not os.path.exists(lf): continue
    links = [l.strip() for l in open(lf) if l.strip()]
    if not os.path.exists(rf): pending.append((os.path.basename(d), len(links))); continue
    rows = {r["url"]: r for r in csv.DictReader(open(rf))}
    for u in dict.fromkeys(links):
        tot["links"] += 1; r = rows.get(u)
        if r is None: problems.append((os.path.basename(d), "no result row", u)); continue
        k = r["kind"]
        if k == "english judgment":
            tot["english"] += 1
            if r["status"].startswith("ok"):
                tot["ok"] += 1
                if u not in shard_urls: problems.append((os.path.basename(d), "ok but not in the text shards", u))
            else: problems.append((os.path.basename(d), "not fetched: " + r["status"], u))
        elif k.startswith("vernacular"): tot["vernacular"] += 1
        elif k.startswith("malformed"): tot["no_diary"] += 1
        else: tot["other"] += 1
print("months still pending (no results yet):", len(pending), sum(n for _, n in pending), "links")
print("links with results:", tot["links"], "| English", tot["english"], "of which ok", tot["ok"], "| vernacular skipped", tot["vernacular"], "| no diary number", tot["no_diary"], "| other", tot["other"])
print("problems:", len(problems))
for p in problems[:40]: print("  ", *p)
