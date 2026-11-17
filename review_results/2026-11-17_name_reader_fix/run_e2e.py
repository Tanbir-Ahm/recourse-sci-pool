"""End-to-end check of the name-reader fix on the held-out questions (endtoend_questions_v1.json, written and committed before any run): the REAL search service code with real Voyage embedding and re-rank (about 0.15 cent a question and setting).
Three settings on the same index: the authority step OFF; ON with the OLD table (the one staging runs); ON with the NEW table (made by the fixed reader). A hit = an expected judgment (counted by case) among the first 8 distinct judgments (what the site feeds) / 10.
    python3 run_e2e.py --which new|pinned --old-table PATH --new-table PATH --out FILE
Run ONCE per index with the settings fixed (the service's defaults); nothing is tuned on these questions."""
import argparse, hashlib, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "review_results", "2026-10-29_landmark_miss")); os.chdir(ROOT)
ap = argparse.ArgumentParser(); ap.add_argument("--which", default="new"); ap.add_argument("--old-table", required=True); ap.add_argument("--new-table", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--questions", default=os.path.join(HERE, "endtoend_questions_v1.json")); a = ap.parse_args()
os.environ["SCI_NAMES_TABLE"] = "names_table/names_table_d8811a9.json.gz" if a.which == "new" else "names_table/names_table.json.gz"
import evaluate as EV, authority_search as AS, sci_search_service as ss
sides = ["review_data/side_index_d8811a9/" + d for d in sorted(os.listdir("review_data/side_index_d8811a9"))] if a.which == "new" else []
svc = ss.SearchService.load("/home/user/audit_idx/" + ("new" if a.which == "new" else "pinned"), sides)
qs = json.load(open(a.questions, encoding="utf-8"))
have = {m["doc"] for m in svc.metas}
qs = [dict(q, expected=[d for d in q["expected"] if d in have]) for q in qs]
qs = [q for q in qs if q["expected"]]
old = AS.AuthorityTable.load(a.old_table, svc.info.get("index_commit")); new = AS.AuthorityTable.load(a.new_table, svc.info.get("index_commit"))
same = new.cluster_of                                   # one common notion of 'the same case' for all three settings (the new table's clusters)
off = EV.run(svc, qs, same_case=same)
on_old = EV.run(svc, qs, old, same_case=same)
on_new = EV.run(svc, qs, new, same_case=same)
def summ(rows):
    out = {}
    for g in ("company", "control", None):
        R = [r for r in rows if g is None or r["group"] == g]
        out[g or "all"] = {"n": len(R), "hit8": sum(r["hit8"] for r in R), "hit10": sum(r["hit10"] for r in R)}
    return out
res = {"index_commit": svc.info.get("index_commit"), "questions": len(qs), "off": summ(off), "on_old_table": summ(on_old), "on_new_table": summ(on_new),
       "sha256": {"authority_graph.py": hashlib.sha256(open(os.path.join(ROOT, "authority_graph.py"), "rb").read()).hexdigest(), "old_table": hashlib.sha256(open(a.old_table, "rb").read()).hexdigest(), "new_table": hashlib.sha256(open(a.new_table, "rb").read()).hexdigest()},
       "rows": {"off": off, "on_old": on_old, "on_new": on_new}}
json.dump(res, open(a.out, "w"), indent=1)
print(json.dumps({k: res[k] for k in ("index_commit", "questions", "off", "on_old_table", "on_new_table")}, indent=1))
