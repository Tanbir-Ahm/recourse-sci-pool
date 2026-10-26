"""
compare_old_new.py -- the same 12 known-answer questions (landmarks.json: 6 landmark judgments, each asked in a layman's and a lawyer's words) and 9 spot-check questions, run through the search service's REAL recipe
(SearchService.search: meaning + words + section lookups, rank fusion, Voyage rerank) on one index at a time. Needs VOYAGE_API_KEY (never printed); costs well under one dollar.

    python compare_old_new.py <repo> <index_dir> <index_commit> <label> <out.json> [--names <names_table.json.gz>] [--sides <glob>]

What it measures: for each landmark question, the rank (1..10) of the landmark judgment among the 10 passages the service returns, and the court of every returned passage.
What it does NOT measure: whether the verified paragraph is among the top 3 (the older raw-index test did; this is a coarser, case-level question), or the quality of the spot-check results (nobody has marked them).
"""
import glob
import json
import os
import sys
import time

repo, idx, commit, label, out = sys.argv[1:6]
names = sides = None
if "--names" in sys.argv:
    names = sys.argv[sys.argv.index("--names") + 1]
if "--sides" in sys.argv:
    sides = sys.argv[sys.argv.index("--sides") + 1]
sys.path.insert(0, repo)
os.chdir(repo)
os.environ["SCI_INDEX_COMMIT"] = commit
if names:
    os.environ["SCI_NAMES_TABLE"] = os.path.join(repo, names)
import sci_search_service as S

side_dirs = sorted(glob.glob(os.path.join(repo, sides or "review_data/side_index/*/")))
SPOT = [
    "bail in a case under the NDPS Act where the quantity is commercial: what are the twin conditions",
    "can anticipatory bail be granted with conditions and for how long does it last",
    "quashing of an FIR when the parties have settled, the power of the High Court",
    "delay in lodging the FIR and its effect on the prosecution case",
    "when can a dying declaration alone be the basis of a conviction",
    "possession of a firearm without licence under the Arms Act, conviction and sentence",
    "default bail when the chargesheet is not filed within 60 or 90 days",
    "criminal trespass and cheating over a land dispute in Assam",
    "Armed Forces Special Powers Act and the arrest of a civilian",
]
t0 = time.time()
svc = S.SearchService.load(idx, side_dirs=side_dirs)
load_s = round(time.time() - t0, 1)
lm = json.load(open(os.path.join(repo, "landmarks.json"), encoding="utf-8"))["landmarks"]
res = {"label": label, "index_commit": commit, "info": {k: svc.info[k] for k in ("index_commit", "passages", "documents", "as_of", "courts", "as_of_by_court") if k in svc.info}, "load_seconds": load_s, "landmarks": [], "spot": []}


def run(q):
    r = svc.search(q, k=10)
    rows = [{"rank": x["rank"], "doc": x["doc"], "case": x.get("case_name"), "date": x.get("date"), "court": x.get("court"), "para": x.get("paragraph"), "type": x.get("passage_type")} for x in r["results"]]
    return rows


for l in lm:
    for q in l["questions"]:
        rows = run(q["q"])
        docs = [x["doc"] for x in rows]
        rank = (docs.index(l["doc"]) + 1) if l["doc"] in docs else None
        res["landmarks"].append({"landmark": l["name"], "doc": l["doc"], "kind": q["kind"], "doc_rank_in_top10": rank, "n_results": len(rows), "courts_in_top10": sorted({x["court"] for x in rows if x["court"]}),
                                 "n_other_court_in_top10": sum(1 for x in rows if x["court"] and x["court"] != "Supreme Court of India"), "rows": rows})
for q in SPOT:
    rows = run(q)
    res["spot"].append({"q": q, "results": rows, "n_other_court": sum(1 for x in rows if x["court"] and x["court"] != "Supreme Court of India")})
res["usage_today"] = svc.health().get("today")
json.dump(res, open(out, "w", encoding="utf-8"), indent=1, default=str)
ok = [x for x in res["landmarks"] if x["doc_rank_in_top10"]]
print(label, "landmark doc in top 10:", len(ok), "of", len(res["landmarks"]), "| in top 5:", sum(1 for x in ok if x["doc_rank_in_top10"] <= 5), "| in top 3:", sum(1 for x in ok if x["doc_rank_in_top10"] <= 3), "| load", load_s, "s")
