"""Writes the prepared-records files the indexer reads with --extra-dir (sci_index.py, ids from EXTRA_BASE): `index_blocks/<scope>-<NNNN>.ok<n>.miss0.err0.jsonl.gz`, at most 250 records each,
in a fixed order (decision date, then key), so a judgment's id never changes. Files already present are never rewritten (immutable once written); a new run only adds blocks after them.
  sci_newer: the Supreme Court's newer archive judgments that the open bucket does not hold (in_bucket != yes).
  ghc_court: Gauhati High Court files read from the court's own PDFs, reasoned judgments of wanted types.
Usage: python3 -I build_index_blocks.py sci_newer SCI_SHARDS_WORKTREE | ghc_court GHC_WORKTREE"""
import glob, gzip, json, os, sys

BLOCK = 250
scope, root = sys.argv[1:3]

def shards(d):
    for f in sorted(glob.glob(os.path.join(d, "shards", "*.jsonl.gz"))):
        for line in gzip.open(f, "rt", encoding="utf-8"):
            yield json.loads(line)

recs = []
if scope == "sci_newer":
    for r in shards(root):
        if r.get("in_bucket") == "yes": continue
        recs.append((r["decision_date"], r["pdf_url"], {"status": "ok", "text": r["text"], "pages": r["pages"], "path": r["pdf_url"], "title": r.get("case_name"),
            "decision_date": r["decision_date"], "citation": r.get("neutral_citation") or None, "case_id": r.get("diary_no"), "case_number": r.get("case_number"),
            "source_kind": "sci_newer", "url": r["pdf_url"], "court": "Supreme Court of India"}))
elif scope == "ghc_court":
    for r in shards(root):
        if r.get("text_source") != "court" or r.get("excluded_type") or not r.get("reasoned_judgment"): continue
        recs.append((r["decision_date"], r["bucket_key"], {"status": "ok", "text": r["text"], "pages": r["pages"], "path": r["court_url"], "title": r.get("parties"),
            "decision_date": r["decision_date"], "citation": r.get("case_number"), "case_id": r.get("case_number"), "case_number": r.get("case_number"),
            "source_kind": "ghc_court", "url": r["court_url"], "court": "Gauhati High Court"}))
else:
    raise SystemExit("scope must be sci_newer or ghc_court")
recs.sort(key=lambda x: (x[0], x[1]))
out = os.path.join(root, "index_blocks"); os.makedirs(out, exist_ok=True)
have = {f for f in os.listdir(out) if f.startswith(scope + "-")}
if have:
    print("blocks already exist, nothing rewritten:", sorted(have)); sys.exit(0)
for n in range(0, len(recs), BLOCK):
    chunk = [x[2] for x in recs[n:n + BLOCK]]
    name = f"{scope}-{n // BLOCK:04d}.ok{len(chunk)}.miss0.err0.jsonl.gz"
    with gzip.open(os.path.join(out, name), "wt", encoding="utf-8") as fh:
        for c in chunk: fh.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(name)
print(scope, len(recs), "judgments in", (len(recs) + BLOCK - 1) // BLOCK, "blocks")
