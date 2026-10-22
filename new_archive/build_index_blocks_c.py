"""Set C: writes the prepared-records files for the open bucket's Guwahati text (scope `ghc_bucket`, read by sci_index.py with --extra-dir; ids from EXTRA_BASE + 2000 * 250), after the
word rejoin of `rejoin_guwahati.py`. Same file format and rules as build_index_blocks.py: at most 250 records per file, fixed order (decision date, then bucket key), files already
present are never rewritten. Records: the bucket's reasoned judgments of wanted types (text_source not 'court', not excluded_type, reasoned_judgment), the same selection as plan_embedding.py set C.
Usage: python3 -I build_index_blocks_c.py GHC_WORKTREE SCI_NEWER_WORKTREE   (the second one only supplies clean text for the rejoin's lexicon)"""
import glob, gzip, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rejoin_guwahati as rj

BLOCK = 250
root, sci = sys.argv[1:3]
lex = rj.build_lexicon([sci, root])
recs = []
for f in sorted(glob.glob(os.path.join(root, "shards", "*.jsonl.gz"))):
    for line in gzip.open(f, "rt", encoding="utf-8"):
        r = json.loads(line)
        if r.get("text_source") == "court" or r.get("excluded_type") or not r.get("reasoned_judgment"):
            continue
        recs.append((r["decision_date"], r["bucket_key"], {"status": "ok", "text": rj.rejoin(r["text"], lex), "pages": r["pages"], "path": r["bucket_url"], "title": r.get("parties"),
            "decision_date": r["decision_date"], "citation": r.get("case_number"), "case_id": r.get("case_number"), "case_number": r.get("case_number"),
            "source_kind": "ghc_bucket", "url": r["bucket_url"], "court": "Gauhati High Court"}))
recs.sort(key=lambda x: (x[0], x[1]))
out = os.path.join(root, "index_blocks"); os.makedirs(out, exist_ok=True)
have = {f for f in os.listdir(out) if f.startswith("ghc_bucket-")}
if have:
    print("blocks already exist, nothing rewritten:", sorted(have)); sys.exit(0)
for n in range(0, len(recs), BLOCK):
    chunk = [x[2] for x in recs[n:n + BLOCK]]
    name = f"ghc_bucket-{n // BLOCK:04d}.ok{len(chunk)}.miss0.err0.jsonl.gz"
    with gzip.open(os.path.join(out, name), "wt", encoding="utf-8") as fh:
        for c in chunk: fh.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(name)
print("ghc_bucket", len(recs), "judgments in", (len(recs) + BLOCK - 1) // BLOCK, "blocks")
