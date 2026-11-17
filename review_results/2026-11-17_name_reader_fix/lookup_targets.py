import gzip, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import importlib; TARGETS = importlib.import_module(os.environ.get("TARGETS_MODULE", "targets_v1")).TARGETS
out = {}
for tag, f in (("new", "names_table/names_table_d8811a9.json.gz"), ("pinned", "names_table/names_table.json.gz")):
    rows = json.load(gzip.open(os.path.join(ROOT, f), "rt", encoding="utf-8"))["rows"]
    for label, p1, p2, yr, q in TARGETS:
        hits = []
        for r in rows:
            n = (r.get("name") or "").lower()
            if re.search(p1, n) and re.search(p2, n.split(" v", 1)[-1] if " v" in n else n):
                y = r.get("year") or (int(r["date"][:4]) if r.get("date") else None)
                hits.append((r["doc"], r["name"], y))
        ok = [h for h in hits if h[2] and abs(h[2] - yr) <= 2] or hits
        out.setdefault(label, {})[tag] = ok[:6]
for label, d in out.items():
    print(label[:62].ljust(64), "new:", [(h[0], h[2]) for h in d["new"]][:3], "| pinned:", [(h[0], h[2]) for h in d["pinned"]][:3])
json.dump(out, open(os.path.join(HERE, ""+os.environ.get("TARGETS_MODULE","targets_v1")+"_lookup.json"), "w"), indent=1)
