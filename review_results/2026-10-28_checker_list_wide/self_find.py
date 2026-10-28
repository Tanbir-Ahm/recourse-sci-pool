"""Does every named judgment of the wide index find ITSELF in the wide list? (a check of the matcher, not of coverage: the names are in the list by construction.)
    python3 self_find.py RECOURSE_DIR NAMES_TABLE.json.gz OUT.json"""
import collections, gzip, json, os, sys
rec, names_path, out = sys.argv[1:4]
os.chdir(rec); sys.path.insert(0, rec)
os.environ["CHECKER_LIST"] = "wide"
import checker_list as C
C.build()
rows = [r for r in json.load(gzip.open(names_path, "rt", encoding="utf-8"))["rows"] if r.get("name")]
res, miss = collections.Counter(), []
for r in rows:
    x = C.lookup(r["name"])
    if x is None:
        res["cannot read the name"] += 1; miss.append([r["name"], r["court"], "cannot read"])
    elif x["found"]:
        res["found"] += 1
    else:
        res["not found"] += 1; miss.append([r["name"], r["court"], "not found"])
json.dump({"named_rows": len(rows), "result": dict(res), "by_court": dict(collections.Counter(m[1] for m in miss)), "misses": miss}, open(out, "w"), ensure_ascii=False, indent=1)
print(len(rows), dict(res))
