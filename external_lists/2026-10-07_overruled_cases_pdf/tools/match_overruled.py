"""Match the PDF's rows to the collection by printed citations. Read-only. python3 -I."""
import json, re, sqlite3, collections
SP = "/tmp/claude-0/-home-user-recourse-sci-pool/33686f69-1895-5643-b31d-21bed3d4a6ee/scratchpad/"
rows = json.load(open(SP + "ovr/rows.json"))
c = sqlite3.connect("file:" + SP + "corpus.sqlite?mode=ro", uri=True)

idx = collections.defaultdict(set)
meta = {}
for did, key, title, date, year, cites, dup in c.execute("select id,doc_key,title,date,year,cites,dup_of from docs"):
    meta[did] = (key, title, date, year, dup)
    try:
        for k in json.loads(cites or "[]"):
            if k.startswith(("air:", "scc:", "scr:")):
                idx[k].add(did)
    except Exception:
        pass

AIR = re.compile(r'AIR\s*(\d{4})\s*SC\s*(\d+)')
SCC = re.compile(r'\((\d{4})\)\s*(\d+)\s*SCC\s*(\d+)')
SCR = re.compile(r'\((\d{4})\)\s*(\d+)\s*SCR\s*(\d+)')
def keys(s):
    ks = []
    ks += [f"air:{y}:{p}" for y, p in AIR.findall(s)]
    ks += [f"scc:{y}:{v}:{p}" for y, v, p in SCC.findall(s)]
    ks += [f"scr:{y}:{v}:{p}" for y, v, p in SCR.findall(s)]
    return ks

def match(s):
    hits = collections.Counter()
    for k in keys(s):
        for d in idx.get(k, ()):
            hits[d] += 1
    if not hits:
        return None, "none", keys(s)
    best = hits.most_common()
    if len(best) > 1 and best[0][1] == best[1][1]:
        return [d for d, _ in best], "ambiguous", keys(s)
    return best[0][0], "ok", keys(s)

out = []
for r in rows:
    # the left side: only citations printed in the left cell; the right side likewise
    ld, ls, lk = match(r["left"]); rd, rs, rk = match(r["right"])
    out.append({"no": r["no"], "left_doc": ld, "left_status": ls, "left_keys": lk, "right_doc": rd, "right_status": rs, "right_keys": rk})
json.dump(out, open(SP + "ovr/matched.json", "w"))
C = collections.Counter
print("left: ", C(o["left_status"] for o in out))
print("right:", C(o["right_status"] for o in out))
print("both matched (single doc each):", sum(1 for o in out if o["left_status"] == "ok" and o["right_status"] == "ok"))
print("left has an SC key in the printed cites:", sum(1 for o in out if o["left_keys"]))
print("left has SC key but no doc in collection:", sum(1 for o in out if o["left_keys"] and o["left_status"] == "none"))
