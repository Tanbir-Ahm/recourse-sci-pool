"""End to end on the REAL newer index (d8811a9) with the REAL search recipe (Voyage embed + rerank, a tenth of a cent) and SCI_QUOTES=on, for the question that returned Sadhwi Pragyna Singh Thakur
"paragraph 8" in the 2026-10-26 comparison; then the same result through Recourse's feed_block (no answer model). Run: python3 demo_end_to_end.py REPO INDEX_DIR RECOURSE_DIR OUT.json   (OUT is written inside REPO: the script changes directory to it)"""
import contextlib, glob, io, json, os, sys, time

repo, idx, rec, out = sys.argv[1:5]
sys.path.insert(0, repo)
sys.path.insert(0, rec)
os.chdir(repo)
os.environ["SCI_INDEX_COMMIT"] = "d8811a910c73b0159bea7bcf3183ea258120db5b"
os.environ["SCI_NAMES_TABLE"] = os.path.join(repo, "names_table/names_table_d8811a9.json.gz")
os.environ["SCI_QUOTES"] = "on"
import sci_search_service as S

sides = sorted(glob.glob(os.path.join(repo, "review_data/side_index_d8811a9/*/")))
t0 = time.time()
svc = S.SearchService.load(idx, side_dirs=sides)
print("loaded in", round(time.time() - t0, 1), "s; quotes:", svc.info.get("quotes"))
Q = "Armed Forces Special Powers Act and the arrest of a civilian"
r = svc.search(Q, k=10)
res = r["results"]
print("\nresults for:", Q)
for x in res:
    print(f'{x["rank"]:2}. {x["case_name"][:60]:60} para {str(x["paragraph"]):>7}  quote={x.get("quote") and {k: (v if k != "intro" else v[:70] + "...") for k, v in x["quote"].items()}}')

import sci_search_tier as T
os.environ["SCI_SEARCH_MODE"] = "feed"
os.environ["SCI_SEARCH_URL"] = "http://127.0.0.1:9"
T.search = lambda *a, **k: r
T.reset()
with contextlib.redirect_stdout(io.StringIO()):
    block = T.feed_block(Q)
cases = list(T._LOCAL.cases)
print("\nPROMPT BLOCK (Sadhwi part):")
i = block.find("Sadhwi")
print(block[max(0, block.rfind("[WIDER", 0, i)): block.find("[WIDER", i + 10) if block.find("[WIDER", i + 10) > 0 else None][:2600] if i >= 0 else "(Sadhwi not among the fed cases)")
print("\nCASES THE PAGE LISTS:")
for c in cases:
    print({k: (str(v)[:110] if v else v) for k, v in c.items() if k in ("case_name", "paragraph", "passage_note", "passage_kinds")})
json.dump({"question": Q, "results": [{k: v for k, v in x.items() if k != "text"} for x in res], "cases": [{k: c.get(k) for k in ("case_name", "paragraph", "passage_note", "passage_kinds")} for c in cases], "quotes_stats": svc.info.get("quotes")}, open(out, "w"), indent=1, ensure_ascii=False)
