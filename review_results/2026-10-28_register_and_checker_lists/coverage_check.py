"""Is every judgment the corpus holds in the list the invented-case checker looks up?

The checker (Recourse grounding_checks.check_cases) lets a case name in an answer pass when the case's distinctive party name appears in the material given to the model for that answer;
otherwise it asks grounding_checks.sc_list_has(name), which looks the name up in case_lookup_index.db (the Supreme Court title list: 38,026 titles, 1950 to 12 Dec 2025) and says True only when a title
has the same first party and a similar second party. This script runs that very function over (a) every judgment of the wide index d8811a9 (names table), (b) the library's judgments.
Run: python3 coverage_check.py RECOURSE_DIR NAMES_TABLE.json.gz OUT.json     (reads only; spends nothing)"""
import collections, glob, gzip, json, os, sys, time

rec, names_path, out = sys.argv[1:4]
os.chdir(rec)
sys.path.insert(0, rec)
os.environ["CASE_LOOKUP_INDEX_PATH"] = os.path.join(rec, "case_lookup_index.db")
import sqlite3
import grounding_checks as G

# the list, by decision date, to tell "the list lacks it" from "the name match missed it"
db = sqlite3.connect("file:" + os.path.join(rec, "case_lookup_index.db") + "?mode=ro", uri=True)
by_date = collections.defaultdict(list)
for cid, title, pet, res, dt, cit in db.execute("select case_id,title,petitioner,respondent,decision_date,citation from cases"):
    by_date[dt].append((cid, title, cit))
LIST_END = db.execute("select max(decision_date) from cases").fetchone()[0]

nd = json.load(gzip.open(names_path, "rt", encoding="utf-8"))
res_rows = []
t0 = time.time()
for r in nd["rows"]:
    name, date, court = r.get("name"), r.get("date"), r.get("court")
    row = {"doc": r["doc"], "name": name, "date": date, "court": court, "citations": json.dumps(r.get("citations") or {}), "link_kind": r.get("link_kind")}
    if not name:
        row["status"] = "no name in the names table"
    elif court != "Supreme Court of India":
        row["status"] = "not a Supreme Court judgment (the list is Supreme Court only)"
        row["checker_says"] = G.sc_list_has(name)
    else:
        ok = G.sc_list_has(name)
        row["checker_says"] = ok
        if ok:
            row["status"] = "found by the checker"
        elif date and date > LIST_END:
            row["status"] = "NOT in the list: decided after the list ends (" + LIST_END + ")"
        else:
            same_day = by_date.get(date) or []
            p1 = set(G._tokens(G._parties(name)[0]))
            near = [t for t in same_day if p1 and p1 & set(G._tokens(G._parties(t[1])[0]))]
            if near:
                row["status"] = "in the list under another spelling; the checker's name match misses it"
                row["list_title"] = near[0][1]
            else:
                row["status"] = "NOT in the list (decided before it ends)"
    res_rows.append(row)
    if len(res_rows) % 2000 == 0:
        print(len(res_rows), round(time.time() - t0), "s", flush=True)

lib = []
for f in sorted(glob.glob(os.path.join(rec, "chunks", "*_chunks.json"))):
    ch = json.load(open(f, encoding="utf-8"))
    if not ch or "case_name" not in ch[0]:
        continue
    nm = ch[0]["case_name"]
    lib.append({"file": os.path.basename(f), "name": nm, "citation": ch[0].get("citation"), "checker_says": G.sc_list_has(nm)})
json.dump({"list_end": LIST_END, "list_size": sum(len(v) for v in by_date.values()), "wide": res_rows, "library": lib}, open(out, "w"), ensure_ascii=False)
c = collections.Counter(r["status"] for r in res_rows)
for k, v in c.most_common():
    print(f"{v:6}  {k}")
print("library:", collections.Counter(x["checker_says"] for x in lib), "of", len(lib))
