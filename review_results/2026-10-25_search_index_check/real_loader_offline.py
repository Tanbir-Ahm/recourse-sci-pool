"""Scratch: runs the search service's OWN loader (sci_search_service.SearchService.load) offline on a copy of the index, with a dummy embedding client, and prints the info the live /health would report."""
import sys, os, json, glob, time
repo, idx, commit = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, repo); os.chdir(repo)
os.environ["SCI_INDEX_COMMIT"] = commit
import sci_search_service as S
sides = [] if os.environ.get("NOSIDE") else sorted(glob.glob(os.path.join(repo, "review_data", "side_index", "*/")))
t = time.time()
try:
    svc = S.SearchService.load(idx, side_dirs=sides, client=object())
except Exception as e:
    print("LOAD REFUSED:", type(e).__name__, str(e)[:300]); sys.exit(0)
info = dict(svc.info)
print(json.dumps({k: info[k] for k in info if k not in ("side_indexes",)}, indent=1, default=str))
print("side indexes:", [(s.get("dir"), s.get("documents"), s.get("passages")) for s in info.get("side_indexes", [])])
json.dump(info, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "loader_info_" + commit[:7] + ".json"), "w"), indent=1, default=str)
print("took", round(time.time() - t, 1), "s")
