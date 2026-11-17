"""SYSTEMATIC SAMPLE for the name-reader fix (protocol fixed 2026-11-17 BEFORE any count was run on it): no hand-picking.
From the names table of the index, draw with a fixed seed (random.Random(20261117)) 150 judgments whose FIRST party carries a corporate-form word (ltd, limited, pvt, private, corp, corporation, corpn, co, company, inc, llp: group 'company')
and 150 whose first party carries none and is not a State, the Union or another shared body (group 'plain'). For each, a full-text query is built from the names alone: the first party's words without honorifics and corporate-form words (up to 3),
AND the first two distinctive words of the second party (only the first party's words when the second party is a State, the Union or another shared body). 'text mentions' = judgments of the index whose text matches it, other than the case's own records.
Kept: cases with at least 5 text mentions (a number that does not depend on the reader). Compared with the authority table's count of judgments naming the case.
Metrics: recall = sum(table counts, capped at the text mentions of that case) / sum(text mentions); cases with table >= half the text mentions; cases with a table count of 0.
Run:  python3 sample_eval.py --which new|pinned --table authority_table/<file> --out FILE      Free (no model call)."""
import argparse, json, os, random, re, sys, gzip
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT); os.chdir(ROOT)
ap = argparse.ArgumentParser(); ap.add_argument("--which", default="new"); ap.add_argument("--table", required=True); ap.add_argument("--out", required=True); a = ap.parse_args()
names_file = "names_table/names_table_d8811a9.json.gz" if a.which == "new" else "names_table/names_table.json.gz"
os.environ["SCI_NAMES_TABLE"] = names_file
import authority_search as AS, sci_search_service as ss, authority_graph as G
CORP = {"ltd", "limited", "pvt", "private", "corp", "corporation", "corpn", "co", "company", "inc", "llp"}
HON = set("shri smt sri sh dr mr mrs ms messrs late lt col capt major justice prof kumari km master baby m s".split())
rows = [r for r in json.load(gzip.open(names_file, "rt", encoding="utf-8"))["rows"] if r.get("name") and re.search(r"\sv\.?\s", r["name"], re.I)]
def parts(name):
    p1, p2 = re.split(r"\sv\.?\s", name, maxsplit=1, flags=re.I)
    w = lambda s: re.findall(r"[A-Za-z]{2,}", re.sub(r"\([^)]*\)?", " ", s))
    return w(p1), w(p2)
def query(r):
    w1, w2 = parts(r["name"])
    core1 = [x for x in w1 if x.lower() not in CORP and x.lower() not in HON][:3]
    core2 = [x for x in w2 if x.lower() not in CORP and x.lower() not in HON and x.lower() not in G._GENERIC_WORDS and x.lower() not in ("of", "and", "the", "ors", "anr", "another", "others")][:2]
    if len(core1) < 1 or sum(len(x) for x in core1) < 6 or core1[0].lower() in G._GENERIC_WORDS:
        return None
    q = '"' + " ".join(core1) + '"'
    if core2:
        q += ' AND "' + " ".join(core2) + '"'
    return q
company, plain = [], []
for r in rows:
    w1, _ = parts(r["name"])
    if not w1:
        continue
    (company if any(x.lower() in CORP for x in w1) else plain).append(r)
rng = random.Random(20261117)
rng.shuffle(company); rng.shuffle(plain)
svc = ss.SearchService.load("/home/user/audit_idx/" + ("new" if a.which == "new" else "pinned"), (["review_data/side_index_d8811a9/" + d for d in sorted(os.listdir("review_data/side_index_d8811a9"))] if a.which == "new" else []), client=object())
tab = AS.AuthorityTable.load(a.table, svc.info.get("index_commit"))
held = set(svc.metas[i]["doc"] for i in range(len(svc.metas)))
def evaluate(pool, n):
    out = []
    for r in pool:
        if len(out) >= n * 3:                       # at most n*3 candidates examined per group (cost control); the first n kept in order
            break
        d = r["doc"]
        if d not in held:
            continue
        q = query(r)
        if not q:
            continue
        docs = set()
        try:
            for (rid,) in svc.fts.execute("select rowid from f where f match ?", (q,)):
                docs.add(svc.metas[rid]["doc"])
        except Exception:
            continue
        cl = tab.cluster_of(d); own = set(tab.docs_of(cl)) | {d}
        tm = len(docs - own)
        out.append({"doc": d, "name": r["name"], "query": q, "text_mentions": tm, "table_cited_by": tab.cited_by.get(cl, 0)})
    kept = [o for o in out if o["text_mentions"] >= 5][:n]
    return kept
res = {"company": evaluate(company, 150), "plain": evaluate(plain, 150)}
def summ(L):
    tm = sum(o["text_mentions"] for o in L); tb = sum(min(o["table_cited_by"], o["text_mentions"]) for o in L)
    return {"cases": len(L), "recall_capped": round(tb / tm, 3) if tm else None, "table_ge_half": sum(1 for o in L if o["table_cited_by"] * 2 >= o["text_mentions"]), "table_zero": sum(1 for o in L if o["table_cited_by"] == 0),
            "table_over_text": sum(1 for o in L if o["table_cited_by"] > o["text_mentions"])}
res["summary"] = {k: summ(v) for k, v in res.items() if k in ("company", "plain")}
json.dump(res, open(a.out, "w"), indent=1)
print(json.dumps(res["summary"], indent=1))
