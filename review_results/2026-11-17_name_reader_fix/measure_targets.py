"""For each held-out target (targets_v1.py): how many OTHER judgments of the index name it in their text (full-text search, the independent measure) against how many the authority table counts as naming it.
Free (no model call). Run from anywhere:  python3 measure_targets.py --which new|pinned --table PATH --out FILE
A target is kept only if the names table holds it with a year within 3 of the expected one (or no year); the rule was fixed before any count was run."""
import argparse, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT); sys.path.insert(0, HERE); os.chdir(ROOT)
ap = argparse.ArgumentParser(); ap.add_argument("--which", default="new"); ap.add_argument("--table", required=True); ap.add_argument("--out", required=True); a = ap.parse_args()
os.environ["SCI_NAMES_TABLE"] = "names_table/names_table_d8811a9.json.gz" if a.which == "new" else "names_table/names_table.json.gz"
import authority_search as AS, sci_search_service as ss
import importlib; TARGETS = importlib.import_module(os.environ.get("TARGETS_MODULE", "targets_v1")).TARGETS
look = json.load(open(os.path.join(HERE, ""+os.environ.get("TARGETS_MODULE","targets_v1")+"_lookup.json")))
sides = ["review_data/side_index_d8811a9/" + d for d in sorted(os.listdir("review_data/side_index_d8811a9"))] if a.which == "new" else []
svc = ss.SearchService.load("/home/user/audit_idx/" + ("new" if a.which == "new" else "pinned"), sides, client=object())
tab = AS.AuthorityTable.load(a.table, svc.info.get("index_commit"))
out = {}
for label, p1, p2, yr, qs in TARGETS:
    hits = look.get(label, {}).get(a.which) or []
    hits = [h for h in hits if h[2] is None or abs(h[2] - yr) <= 3]
    if len(hits) != 1:
        out[label] = {"dropped": "not held, or more than one record within 3 years" if not hits else f"{len(hits)} records"}
        continue
    d = hits[0][0]
    docs = set()
    for q in qs:
        for (rid,) in svc.fts.execute("select rowid from f where f match ?", (q,)):
            docs.add(svc.metas[rid]["doc"])
    cl = tab.cluster_of(d); own = set(tab.docs_of(cl)) | {d}
    out[label] = {"doc": d, "text_mentions": len(docs - own), "table_cited_by": tab.cited_by.get(cl, 0), "group": "company" if any(w in label for w in ("Ltd", "Private", "Corporation", "Pvt", "Co ")) or label.split(" v.")[0].endswith(("Ltd", "Corporation")) else "control"}
json.dump(out, open(a.out, "w"), indent=1)
kept = {k: v for k, v in out.items() if "doc" in v}
print(f"{len(kept)} targets kept, {len(out) - len(kept)} dropped")
for k, v in kept.items():
    print(f"{v['group']:8} {k[:58]:58} text mentions {v['text_mentions']:5}  table counts {v['table_cited_by']:5}")
