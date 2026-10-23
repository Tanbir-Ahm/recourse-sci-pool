"""NO-SPEND plan for embedding the post-2017 Guwahati documents (shards_post2017). Prepares each document with the indexer's own code (sci_index.prepare_block: criminal-law test, duplicate test
against everything already in the index, passage building, token estimate) after a light cleaning (cause-title block cut, 'Page No.#' markers and the closing 'Comparing Assistant' line removed).
Nothing is sent anywhere, no key is read, no index file is changed.
Usage: python3 -I plan_embedding_post2017.py CODE_DIR INDEX_DIR_READONLY DATA_WORKTREE OUT.json"""
import collections, glob, gzip, json, os, re, sys
code, index_dir, data, out_path = sys.argv[1:5]
sys.path.insert(0, code)
import sci_index as si
PRICE = 0.12; CEILING = 85_000_000
PAGE = re.compile(r"(?im)^[ \t]*Page No\.#?\s*\d+\s*/\s*\d+[ \t]*$")
TAIL = re.compile(r"(?im)^[ \t]*Comparing Assistant[ \t]*$")
def clean(o):
    t = o["text"][o["body_start"]:]
    t = PAGE.sub("", t); t = TAIL.sub("", t)
    return re.sub(r"\n{3,}", "\n\n", t)
docs = []
for f in sorted(glob.glob(os.path.join(data, "shards_post2017", "*.jsonl.gz"))):
    for l in gzip.open(f, "rt", encoding="utf-8"):
        o = json.loads(l)
        if "error" not in o: docs.append(o)
seen = si.load_seen(index_dir); spent = si.tokens_spent(index_dir)
rep = {"spent_tokens": spent, "ceiling": CEILING, "price_per_million": PRICE, "documents_stored": len(docs), "sets": {}}
def run(name, sel):
    s = dict(seen); recs = []
    for i, o in enumerate(sel):
        t = clean(o)
        recs.append({"id": 3_000_000_000 + i, "status": "ok", "text": t, "raw_text": t, "pages": o["pages"], "_y": o["decision_date"][:4], "_cl": o["court_listed"]})
    st = collections.Counter(); py = collections.defaultdict(collections.Counter); tokens = 0
    for i in range(0, len(recs), 250):
        blk = si.prepare_block(recs[i:i + 250], s); b = blk["stats"]; tokens += b["est_tokens"]; st["kept"] += b["docs_kept"]; st["passages"] += b["passages"]
        for k, v in b["skipped"].items(): st[k] += v
        yrs = {r["id"]: r["_y"] for r in recs[i:i + 250]}
        for d in blk["docs"]:
            y = yrs[d["doc"]]; py[y]["kept" if "skip" not in d else d["skip"]] += 1
    row = dict(st); row["input"] = len(recs); row["est_tokens"] = tokens; row["est_dollars"] = round(tokens / 1e6 * PRICE, 2)
    row["per_year"] = {y: dict(c) for y, c in sorted(py.items())}
    rep["sets"][name] = row; print(name, {k: v for k, v in row.items() if k != "per_year"}, flush=True)
    return tokens
t1 = run("P1_documents_with_a_judgment_signal", [o for o in docs if o["reasoned_signal"]])
t2 = run("P2_court_listed_only", [o for o in docs if o["court_listed"]])
t3 = run("P3_no_signal_documents_for_information", [o for o in docs if not o["reasoned_signal"]])
rep["total_if_P1"] = {"est_tokens": t1, "est_dollars": round(t1 / 1e6 * PRICE, 2), "spent_plus_plan": spent + t1, "fits_under_ceiling": spent + t1 <= CEILING, "needed_ceiling_with_6pct_margin": int((spent + t1 * 1.06))}
print("P1 total:", rep["total_if_P1"], "spent so far", spent)
json.dump(rep, open(out_path, "w"), indent=1)
