"""Prints where the crawl ends: the highest judgment id saved, its opening and closing text, the last dates, and the run of empty ids after it.
Reads the crawl shards (branch claude/sci-pool checked out at /home/user/recourse-sci-pool-data). Run: python last_crawl_id.py"""
import glob, gzip, json, os, re
os.chdir("/home/user/recourse-sci-pool-data")
M = "January|February|March|April|May|June|July|August|September|October|November|December"
DATE = re.compile(rf"\b({M})\s+(\d{{1,2}})\s*,\s*(20\d\d)\b|\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({M})\s*,?\s*(20\d\d)\b", re.I)
ok, top, gaps_after = [], 0, 0
for f in sorted(glob.glob("shards/*.jsonl.gz")):
    for l in gzip.open(f, "rt", encoding="utf-8"):
        r = json.loads(l); top = max(top, r["id"])
        if r["status"] == "ok":
            ok.append(r)
ok.sort(key=lambda r: r["id"])
last = ok[-1]["id"]
for f in sorted(glob.glob("shards/*.jsonl.gz")):
    for l in gzip.open(f, "rt", encoding="utf-8"):
        r = json.loads(l)
        if r["id"] > last and r["status"] == "gap":
            gaps_after += 1
print(f"judgments saved: {len(ok):,} | highest id saved: {last} | highest id scanned: {top} | empty ids after the last judgment: {gaps_after}")
for r in ok[-8:]:
    ds = [m.group(0) for m in DATE.finditer(r["text"][-700:])]
    print(f"id {r['id']} | {r['pages']} pages | {len(r['text']):,} text chars | last date near the end: {ds[-1] if ds else '(none found)'}")
r = ok[-1]
print("\n--- text of the last judgment ---\n" + r["text"])
