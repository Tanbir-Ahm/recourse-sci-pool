"""Writes the prepared-records files for the post-2017 Guwahati documents that carry a judgment signal (set P1, owner approved 2026-10-24): `index_blocks/ghc_post2017-NNNN.ok<n>.miss0.err0.jsonl.gz`,
at most 250 records each, in a fixed order (decision date, then bucket key) so a judgment's id never changes. Text = the part after the cause-title block ('BEFORE ... HON'BLE' line on), with the
'Page No.#' markers and the closing 'Comparing Assistant' line removed (the same cleaning as the no-spend plan). Existing block files are never rewritten.
Usage: python3 -I build_index_blocks_p1.py DATA_WORKTREE"""
import glob, gzip, json, os, re, sys
root = sys.argv[1]
PAGE = re.compile(r"(?im)^[ \t]*Page No\.#?\s*\d+\s*/\s*\d+[ \t]*$"); TAIL = re.compile(r"(?im)^[ \t]*Comparing Assistant[ \t]*$")
recs = []
for f in sorted(glob.glob(os.path.join(root, "shards_post2017", "*.jsonl.gz"))):
    for l in gzip.open(f, "rt", encoding="utf-8"):
        o = json.loads(l)
        if "error" in o or not o["reasoned_signal"]: continue
        t = re.sub(r"\n{3,}", "\n\n", TAIL.sub("", PAGE.sub("", o["text"][o["body_start"]:])))
        sig = [k for k, v in (("court_listed", o["court_listed"]), ("heading_judgment", o["signal_heading_judgment"]), ("long_body", o["signal_long_body"])) if v]
        recs.append((o["decision_date"], o["bucket_key"], {"status": "ok", "text": t, "pages": o["pages"], "path": o["bucket_key"], "title": o["parties"], "decision_date": o["decision_date"],
            "citation": o["case_number"], "case_id": o["case_number"], "case_number": o["case_number"], "source_kind": "ghc_post2017", "url": o["court_url"] or o["bucket_url"],
            "court": "Gauhati High Court", "neutral_citation": o["neutral_citation"] or None, "court_listed": o["court_listed"], "bucket_url": o["bucket_url"], "signals": sig}))
recs.sort(key=lambda x: (x[0], x[1]))
out = os.path.join(root, "index_blocks"); os.makedirs(out, exist_ok=True)
if any(f.startswith("ghc_post2017-") for f in os.listdir(out)): print("blocks already exist, nothing rewritten"); sys.exit(0)
for n in range(0, len(recs), 250):
    chunk = [x[2] for x in recs[n:n + 250]]
    name = f"ghc_post2017-{n // 250:04d}.ok{len(chunk)}.miss0.err0.jsonl.gz"
    with gzip.open(os.path.join(out, name), "wt", encoding="utf-8") as fh:
        for c in chunk: fh.write(json.dumps(c, ensure_ascii=False) + "\n")
print("ghc_post2017:", len(recs), "judgments in", (len(recs) + 249) // 250, "blocks")
