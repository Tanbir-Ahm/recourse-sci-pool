"""Second matching pass: citation keys (as before) plus party names + year for judgments the keys cannot reach. python3 -I."""
import json, re, sqlite3, collections
SP = "/tmp/claude-0/-home-user-recourse-sci-pool/33686f69-1895-5643-b31d-21bed3d4a6ee/scratchpad/"
rows = json.load(open(SP + "ovr/rows.json")); m1 = json.load(open(SP + "ovr/matched.json"))
c = sqlite3.connect("file:" + SP + "corpus.sqlite?mode=ro", uri=True)
docs = {}
byyear = collections.defaultdict(list)
for did, key, title, pet, resp, date, year, dup in c.execute("select id,doc_key,title,pet,resp,date,year,dup_of from docs"):
    docs[did] = dict(key=key, title=title, pet=pet, resp=resp, date=date, year=year, dup=dup)
    byyear[year].append(did)

STOP = set("vs v the and others another of in re state union india uoi ors anr co ltd limited private pvt p u.p. etc by through its m/s mr smt shri sri dr dead lrs lr thr rep represented secretary government govt dept department commissioner collector officer".split())
def toks(s):
    s = re.sub(r'\(.*?\)', ' ', s.lower())
    s = re.sub(r'[^a-z ]', ' ', s)
    return {t for t in s.split() if t not in STOP and len(t) > 1}

CITE_START = re.compile(r',\s*(?:AIR|\(\d{4}\)|\[\d{4}\]|\d{4}\b)|\bAIR\s*\d{4}|\(\d{4}\)\s*\d')
def name_part(s):
    mm = CITE_START.search(s)
    return s[:mm.start()] if mm else s

def side_year(s):
    mm = re.search(r'AIR\s*(\d{4})\s*SC', s)
    if mm: return int(mm.group(1))
    mm = re.search(r'\((\d{4})\)\s*\d+\s*(?:SCC|JT|SCALE|SCR)', s)
    if mm: return int(mm.group(1))
    mm = re.search(r'\((\d{4})\)', s)
    return int(mm.group(1)) if mm else None

def sides(name):
    parts = re.split(r'\s+Vs\.?\s+|\s+v\.?\s+', name, maxsplit=1, flags=re.I)
    return (toks(parts[0]), toks(parts[1])) if len(parts) == 2 else (toks(name), set())

def name_match(cell):
    nm = name_part(cell)
    y = side_year(cell)
    if y is None: return None, "noyear"
    a, b = sides(nm)
    if not (a or b): return None, "noname"
    cands = []
    for yy in (y - 1, y, y + 1):
        for did in byyear.get(yy, []):
            d = docs[did]
            pa = toks(d["pet"] or (d["title"] or "").split(" v. ")[0]); pb = toks(d["resp"] or "")
            # compare as unordered sets of tokens from both sides, and require each side to overlap
            A = a | b; B = pa | pb
            if not A or not B: continue
            jac = len(A & B) / len(A | B)
            # side-wise overlap also (either orientation)
            def ov(x, y_):
                return len(x & y_) / max(1, len(x | y_)) if x and y_ else 0.0
            side = max(min(ov(a, pa), ov(b, pb)) if (b and pb) else ov(a, pa), min(ov(a, pb), ov(b, pa)) if (b and pb) else ov(a, pb))
            score = 0.5 * jac + 0.5 * side
            cands.append((score, did))
    if not cands: return None, "nocand"
    cands.sort(reverse=True)
    best = cands[0]
    second = cands[1][0] if len(cands) > 1 else 0
    if best[0] >= 0.6 and best[0] - second >= 0.1:
        return best[1], "name"
    if best[0] >= 0.6:
        return [d for s, d in cands if s >= best[0] - 0.1], "name-ambiguous"
    return None, "name-none(%.2f)" % best[0]

out = []
for r, x in zip(rows, m1):
    rec = dict(x)
    for side in ("left", "right"):
        if x[side + "_status"] == "ok":
            rec[side + "_how"] = "cite"; continue
        cell = r[side]
        is_sc = bool(x[side + "_keys"]) or bool(re.search(r'\bSCC\b|\bSCR\b|\bJT\b|\bSCALE\b|\bAIRSCW\b|\bSupreme\b', cell))
        if side == "left" and not is_sc:
            rec[side + "_how"] = "not-sc"; continue
        if side == "right" and not is_sc:
            rec[side + "_how"] = "not-sc"; continue
        d, how = name_match(cell)
        rec[side + "_doc2"] = d; rec[side + "_how"] = how
        if how == "name":
            rec[side + "_doc"] = d; rec[side + "_status"] = "ok-name"
    out.append(rec)
json.dump(out, open(SP + "ovr/matched2.json", "w"))
C = collections.Counter
for side in ("left", "right"):
    print(side, C(o[side + "_how"].split("(")[0] for o in out))
print("both matched:", sum(1 for o in out if o["left_status"].startswith("ok") and o["right_status"].startswith("ok")))
