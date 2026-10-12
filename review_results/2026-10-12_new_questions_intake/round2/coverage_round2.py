"""Round 2: is each authority named for the replacement questions in the index (10,503 judgments + 19 side-index judgments)? Same method as ../coverage.py (title with date, opening text, records the index left out).
Names only; no embedding, no search of any question, no spend. PRIVATE."""
import glob, gzip, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "review_tools")); sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
import pool_runner as PR, sci_index as si
from authorities_round2 import A2_NEW

def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())

def year_of(title):
    ys = [int(y) for y in re.findall(r"(?<!\d)(?:0?[1-9]|[12]\d|3[01])[-/.](?:0?[1-9]|1[0-2])[-/.]((?:19|20)\d\d)(?!\d)", title or "")]
    if not ys:
        ys = [int(y) for y in re.findall(r"(?<!\d)((?:19|20)\d\d)(?!\d)", title or "")]
    return ys[0] if ys else None

head = PR.index_head(PR.DEFAULT_INDEX)
metas, M, _ = si._load_index(PR.DEFAULT_INDEX)
extra_titles = {}
for d in PR.FINAL_SIDE_INDEXES:
    metas, M, info, extra = PR.load_supplement(os.path.join(ROOT, d), metas, M, head)
    extra_titles.update(extra)
title = PR.titles([PR.DEFAULT_INDEX] + [os.path.join(ROOT, d) for d in PR.FINAL_SIDE_INDEXES], metas, extra_titles or None)
docs = sorted({m["doc"] for m in metas})
tab = {d: (title(d) or "") for d in docs}
tabn = {d: norm(t) for d, t in tab.items()}
taby = {d: year_of(t) for d, t in tab.items()}
first = {}
for m in metas:
    first.setdefault(m["doc"], m["text"])
firstn = {d: norm(t[:900]) for d, t in first.items()}
allrec = {}
for f in glob.glob(os.path.join(PR.DEFAULT_INDEX, "index", "*.docs.jsonl.gz")):
    with gzip.open(f, "rt", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("passages", 0) > 0:
                continue
            nm, dt = None, None
            if r.get("case"):
                nm, dt = f"{r['case'].get('pet','')} {r['case'].get('resp','')}", r["case"].get("date")
            elif isinstance(r.get("src"), dict):
                nm, dt = r["src"].get("title"), r["src"].get("date")
            if nm:
                allrec[r["doc"]] = (norm(nm), year_of(dt or ""), r.get("skip"), (nm or "")[:100], dt)
print("index head", head, "| judgments", len(docs), "| passages", len(metas))
rows = []
for q, role, label, toks, year, slack in A2_NEW:
    by_title = [d for d in docs if all(t in tabn[d] for t in toks) and taby[d] is not None and abs(taby[d] - year) <= slack + 1]
    by_head = [d for d in docs if d not in by_title and all(t in firstn[d] for t in toks)]
    filt = [(d, v[2], v[3], v[4]) for d, v in allrec.items() if all(t in v[0] for t in toks) and v[1] is not None and abs(v[1] - year) <= slack + 1]
    rows.append({"q": q, "role": role, "label": label, "tokens": toks, "year": year,
                 "by_title": [(d, tab[d][:110].replace("\n", " ")) for d in by_title[:6]],
                 "by_head": [(d, re.sub(r"\s+", " ", first[d][:220])) for d in by_head[:6]], "n_head": len(by_head),
                 "filtered_in_collection": filt[:3]})
json.dump({"index_head": head, "rows": rows}, open(os.path.join(HERE, "coverage_round2.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
for r in rows:
    print(f"{r['q']:4} {r['role']:10} {r['label'][:80]}")
    for d, t in r["by_title"]:
        print(f"       TITLE {d}: {t}")
    for d, t in r["by_head"]:
        print(f"       HEAD  {d}: {t[:200]}")
    for x in r["filtered_in_collection"]:
        print(f"       LEFT-OUT {x}")
