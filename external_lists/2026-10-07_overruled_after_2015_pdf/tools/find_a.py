"""For each PDF-2 row, look for the EARLIER case (A) in the collection by title tokens; print date/bench so the PDF's year can be compared. Read-only."""
import sqlite3, json, re
SP = "/tmp/claude-0/-home-user-recourse-sci-pool/33686f69-1895-5643-b31d-21bed3d4a6ee/scratchpad/"
con = sqlite3.connect(SP + "corpus.sqlite")
rows = json.load(open(SP + "pdf2_in/rows.json"))
STOP = set("v vs versus the and of in re state union india ltd limited pvt private co corporation dead lrs through retd anr ors m s".split())
def toks(s):
    s = re.sub(r"\([^)]*\)", " ", s)
    return [t for t in re.findall(r"[A-Za-z]{4,}", s) if t.lower() not in STOP]
seen = set()
for r in rows:
    for label, name, yr in (("A", r["a"], r["a_year"]), ("B", r["b"], r["b_year"])):
        if (label, name) in seen: continue
        seen.add((label, name))
        parts = re.split(r"\s+v\.?\s+", re.sub(r"\([^)]*\)", " ", name), maxsplit=1)
        p1 = toks(parts[0])[:2]; p2 = toks(parts[1])[:2] if len(parts) > 1 else []
        if not p1: continue
        q = "select doc_key,title,date,bench_size from docs where dup_of is null"
        args = []
        for t in p1 + p2[:1]:
            q += " and upper(title) like ?"; args.append("%" + t.upper() + "%")
        res = con.execute(q + " order by date limit 6", args).fetchall()
        print(f'{label} #{r["no"]:>2} {name} ({yr}) ->', "; ".join(f'{k} {d} b{b}' for k, t, d, b in res) or "NOT FOUND")
