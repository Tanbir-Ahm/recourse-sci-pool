"""Counts what the post-2017 Guwahati fetch has stored. Usage: python3 -I summarise.py WORKLIST.csv.gz DATA_WORKTREE [OUT.md]"""
import csv, glob, gzip, json, os, sys, collections
work, data = sys.argv[1], sys.argv[2]; out = sys.argv[3] if len(sys.argv) > 3 else None
rows = list(csv.DictReader(gzip.open(work, "rt", encoding="utf-8")))
want = collections.Counter(r["year"] for r in rows)
st = collections.defaultdict(collections.Counter)
for f in sorted(glob.glob(os.path.join(data, "shards_post2017", "*.jsonl.gz"))):
    for l in gzip.open(f, "rt", encoding="utf-8"):
        o = json.loads(l); y = o["decision_date"][:4]
        if "error" in o: st[y]["errors"] += 1; continue
        c = st[y]; c["stored"] += 1; c["court_listed"] += o["court_listed"]; c["heading"] += o["signal_heading_judgment"]; c["long_body"] += o["signal_long_body"]
        c["any_signal"] += o["reasoned_signal"]; c["scan_like"] += o["scan_like"]; c["neutral_citation"] += bool(o["neutral_citation"]); c["chars"] += o["chars"]
L = ["| Year | In worklist | Stored | Errors | Court-listed | JUDGMENT heading | Body 5,000+ chars | Any signal | Scan-like |", "|---|---|---|---|---|---|---|---|---|"]
T = collections.Counter()
for y in sorted(want):
    c = st[y]; L.append(f"| {y} | {want[y]} | {c['stored']} | {c['errors']} | {c['court_listed']} | {c['heading']} | {c['long_body']} | {c['any_signal']} | {c['scan_like']} |")
    T["want"] += want[y]
    for k in ("stored", "errors", "court_listed", "heading", "long_body", "any_signal", "scan_like", "chars"): T[k] += c[k]
L.append(f"| **All** | {T['want']} | {T['stored']} | {T['errors']} | {T['court_listed']} | {T['heading']} | {T['long_body']} | {T['any_signal']} | {T['scan_like']} |")
txt = "\n".join(L) + f"\n\nText stored: {T['chars']:,} characters (about {T['chars']/3.87/1e6:.1f}M tokens if all of it were embedded; only the judgments would be)."
print(txt)
if out: open(out, "w", encoding="utf-8").write("# Guwahati post-2017 criminal-type documents: what is stored\n\n" + txt + "\n")
