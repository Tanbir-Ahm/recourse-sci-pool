"""NO-SPEND plan: what would it cost to embed (a) the Supreme Court judgments of the newer archive that the open bucket does not hold, (b) the Guwahati High Court files read from the
court's own PDFs, (c) the Guwahati text from the open bucket (reasoned judgments)? It prepares each judgment exactly as the indexer does (sci_index.prepare_block: criminal-law test,
duplicate test, passage building, token estimate) and adds up. Nothing is sent to any service, no key is read, no index file is changed.
Usage: python3 -I plan_embedding.py CODE_DIR INDEX_DIR_READONLY SCI_SHARDS_DIR GHC_SHARDS_DIR OUT.json"""
import collections, glob, gzip, json, os, re, sys
code, index_dir, sci_dir, ghc_dir, out_path = sys.argv[1:6]
sys.path.insert(0, code)
import sci_index as si

PRICE_PER_M = 0.12            # voyage-law-2, listed price in dollars per million tokens (the owner's notes; not read from the service)
CEILING = 72_000_000

def read_shards(d):
    for f in sorted(glob.glob(os.path.join(d, "shards", "*.jsonl.gz"))):
        for line in gzip.open(f, "rt", encoding="utf-8"):
            yield json.loads(line)

def unwrap_fixed(text):
    """The bucket's Guwahati PDFs are typed in a fixed width (80, 79 or 72 characters) and a line break can fall inside a word. Per document: take the commonest length of the
    lines and join the lines of that length (or one less) to the next line without a separator. Text with no such width is left alone."""
    out = []
    for pg in text.split("\f"):
        lines = pg.split("\n")
        lens = collections.Counter(len(x) for x in lines[:-1] if len(x) >= 60)
        w = lens.most_common(1)[0][0] if lens else 0
        if not w or lens[w] < 5:
            out.append(pg); continue
        buf, res = "", []
        for ln in lines:
            if len(ln) in (w, w - 1) and len(ln) >= 60: buf += ln
            else: res.append(buf + ln); buf = ""
        if buf: res.append(buf)
        out.append("\n".join(res))
    return "\f".join(out)

index_seen = si.load_seen(index_dir)
spent = si.tokens_spent(index_dir)
seen = dict(index_seen)
report = {"spent_tokens": spent, "ceiling": CEILING, "price_per_million": PRICE_PER_M, "sets": {}}

def run(name, recs, extra=None):
    docs = list(recs)
    stats = collections.Counter(); per_year = collections.defaultdict(collections.Counter); tokens = 0
    for i in range(0, len(docs), 250):
        blk = si.prepare_block(docs[i:i + 250], seen)
        s = blk["stats"]
        tokens += s["est_tokens"]; stats["kept"] += s["docs_kept"]; stats["passages"] += s["passages"]
        for k, v in s["skipped"].items(): stats[k] += v
        yrs = {d["id"]: d.get("_year") for d in docs[i:i + 250]}
        for d in blk["docs"]:
            y = yrs.get(d["doc"], "?")
            per_year[y]["kept" if "skip" not in d else d["skip"]] += 1
            if "skip" not in d: per_year[y]["passages"] += d.get("passages", 0)
    row = dict(stats); row["input"] = len(docs); row["est_tokens"] = tokens; row["est_dollars"] = round(tokens / 1e6 * PRICE_PER_M, 2)
    row["per_year"] = {y: dict(c) for y, c in sorted(per_year.items())}
    if extra: row.update(extra)
    report["sets"][name] = row
    print(name, {k: v for k, v in row.items() if k != "per_year"})

# (a) Supreme Court, newer archive, not held by the open bucket
a = []; held = 0
for r in read_shards(sci_dir):
    if r.get("in_bucket") == "yes": held += 1; continue
    a.append({"id": len(a) + 1, "status": "ok", "text": r["text"], "raw_text": r["text"], "pages": r["pages"], "_year": r["decision_date"][:4]})
run("A_supreme_court_not_in_bucket", a, {"held_by_bucket_not_planned": held})

# (b) Guwahati court files (reasoned, wanted types)
b = []; c = []; nonreasoned = 0
for r in read_shards(ghc_dir):
    if r.get("excluded_type") or not r.get("reasoned_judgment"):
        nonreasoned += 1; continue
    rec = {"status": "ok", "pages": r["pages"], "_year": r["decision_date"][:4]}
    if r.get("text_source") == "court":
        rec.update(id=100000 + len(b), text=r["text"], raw_text=r["text"]); b.append(rec)
    else:
        t = unwrap_fixed(r["text"]); rec.update(id=200000 + len(c), text=t, raw_text=t); c.append(rec)
run("B_guwahati_court_files", b)
run("C_guwahati_bucket_text_joined", c, {"not_reasoned_or_excluded_left_out": nonreasoned})

tot_tokens = sum(s["est_tokens"] for s in report["sets"].values()); tot_kept = sum(s["kept"] for s in report["sets"].values())
report["total"] = {"kept": tot_kept, "est_tokens": tot_tokens, "est_dollars": round(tot_tokens / 1e6 * PRICE_PER_M, 2), "spent_plus_plan": spent + tot_tokens,
                   "fits_under_ceiling": spent + tot_tokens <= CEILING}
print("TOTAL", report["total"], "spent so far", spent)
json.dump(report, open(out_path, "w"), indent=1)
