"""Measure the wider checker list (FOLLOW_UPS 2cp). Written and committed BEFORE it was run; seeds fixed (28). Reads only; spends nothing.

    python3 measure_checker_list.py RECOURSE_DIR NAMES_TABLE.json.gz OUT.json

Four sets, each run through three configurations:
  OLD   grounding_checks._sc_title_list_has  (the Supreme Court title list, word for word: what production does)
  TOL   checker_list on the title list only  (spelling tolerance, no names file)
  WIDE  checker_list with the names file     (title list + wide index SC and Gauhati HC + library)

 S0  the wide index's Supreme Court names against the title list (OLD vs TOL): of the names OLD misses, how many does tolerance find, and for those how many hits carry the SAME decision date as the
     index judgment (same date = almost certainly the same judgment) against a different date (the same parties in another case, or a wrong match).
 S1  names a model might write for real cases (rule-made variants of 2,000 real names that ARE in the title list): how many each configuration still finds.
 S2  names that are NOT real, three kinds (3,000 each): swapped parties (first party of one real case, second party of another), plausible invented names (a given name and a surname from the corpus, against
     a State or the Union), and one-letter twins (a real name with one unrelated letter changed). How many does each configuration wrongly accept?
 S3  the library's 68 cases.
"""
import collections, gzip, json, os, random, re, statistics, sys, time

rec, names_path, out = sys.argv[1:4]
os.chdir(rec)
sys.path.insert(0, rec)
os.environ["CASE_LOOKUP_INDEX_PATH"] = os.path.join(rec, "case_lookup_index.db")
os.environ["CHECKER_LIST"] = "wide"
import grounding_checks as G
import checker_list as C
import name_match as NM

rng = random.Random(28)
nd = json.load(gzip.open(names_path, "rt", encoding="utf-8"))
SC = "Supreme Court of India"
sc_rows = [r for r in nd["rows"] if r.get("name") and r.get("court") == SC]
VS = re.compile(r"\s+v\.?\s+", re.I)


def split(name):
    p = VS.split(name, maxsplit=1)
    return (p[0].strip(), p[1].strip()) if len(p) == 2 else (None, None)


def old(name):
    return G._sc_title_list_has(name)


# --- TOL: the same index code, built without the names file
C.build(names_path="/nonexistent")
tol_state = {k: C._STATE[k] for k in ("built", "error", "entries", "inv", "p3", "s3", "cache", "info")}
tol_n = len(tol_state["entries"])
C.build()                                                       # WIDE (the names file beside the code)
wide_state = {k: C._STATE[k] for k in tol_state}
wide_n = len(wide_state["entries"])


def use(state):
    C._STATE.update(state)


def tol(name):
    use(tol_state)
    r = C.lookup(name)
    return None if r is None else r.get("found"), r


def wide(name):
    use(wide_state)
    r = C.lookup(name)
    return None if r is None else r.get("found"), r


res = {"sizes": {"title_list_only_entries": tol_n, "wide_entries": wide_n}}

# ---------------- S0
t0 = time.time()
miss = []
n_old = 0
for r in sc_rows:
    o = old(r["name"])
    if o:
        n_old += 1
    else:
        miss.append(r)
s0 = collections.Counter()
hits = []
for r in miss:
    f, info = tol(r["name"])
    if f:
        d1, d2 = r.get("date"), (info or {}).get("date")
        kind = "same date" if d1 and d2 and d1 == d2 else ("same year" if d1 and d2 and d1[:4] == d2[:4] else ("a date is missing" if not d1 or not d2 else "different year"))
        s0[kind] += 1
        hits.append({"index_name": r["name"], "index_date": d1, "list_title": info["title"], "list_date": d2, "kind": kind})
    else:
        s0["not found by tolerance"] += 1
res["S0"] = {"sc_names": len(sc_rows), "found_by_old": n_old, "missed_by_old": len(miss), "tolerance_outcome": dict(s0), "seconds": round(time.time() - t0)}
res["S0_samples"] = {k: [h for h in hits if h["kind"] == k][:15] for k in ("same date", "same year", "different year", "a date is missing")}

# ---------------- S1: variants of names that are in the title list (found by OLD)
found_rows = [r for r in sc_rows if old(r["name"])]
base = rng.sample(found_rows, min(2000, len(found_rows)))
ABBR = [("Uttar Pradesh", "U.P."), ("Madhya Pradesh", "M.P."), ("Andhra Pradesh", "A.P."), ("Government", "Govt."), ("Limited", "Ltd."), ("Company", "Co.")]


def variant(name, k):
    a, b = split(name)
    if a is None:
        return None
    if k == 0:                                                   # drop "& Ors" / "and Another"
        b2 = re.sub(r"\s*(?:&|and)\s+(?:Ors|Anr|Others|Another)\.?\s*$", "", b, flags=re.I)
        a2 = re.sub(r"\s*(?:&|and)\s+(?:Ors|Anr|Others|Another)\.?\s*$", "", a, flags=re.I)
        return f"{a2} v. {b2}" if (a2, b2) != (a, b) else None
    if k == 1:                                                   # abbreviate or expand a state / word
        for long, short in ABBR:
            for x, y in ((long, short), (short, long)):
                if x in b:
                    return f"{a} v. {b.replace(x, y)}"
                if x in a:
                    return f"{a.replace(x, y)} v. {b}"
        return None
    if k == 2:                                                   # honorific added
        return f"Shri {a} v. {b}" if not a.lower().startswith(("shri", "state", "union", "the")) else None
    if k == 3:                                                   # parties the other way round
        return f"{b} v. {a}"
    if k == 4:                                                   # a scanner slip: one letter deleted from a long word of the first party
        words = [w for w in a.split() if len(w) >= 7 and w.isalpha()]
        if not words:
            return None
        w = rng.choice(words)
        i = rng.randrange(1, len(w) - 1)
        return f"{a.replace(w, w[:i] + w[i + 1:], 1)} v. {b}"
    return None


KINDS = ["drop & Ors", "abbreviate/expand", "honorific added", "parties reversed", "one letter lost (scanner slip)"]
s1 = {}
for k, label in enumerate(KINDS):
    cnt = collections.Counter()
    ex = []
    for r in base:
        v = variant(r["name"], k)
        if not v:
            continue
        cnt["n"] += 1
        o, (t, _), (w, _) = old(v), tol(v), wide(v)
        cnt["old"] += bool(o)
        cnt["tol"] += bool(t)
        cnt["wide"] += bool(w)
        if not t and len(ex) < 6:
            ex.append({"real": r["name"], "variant": v})
    s1[label] = {"n": cnt["n"], "old_found": cnt["old"], "tol_found": cnt["tol"], "wide_found": cnt["wide"], "tol_misses_examples": ex}
res["S1"] = s1

# ---------------- S2: names that are not real
def normkey(name):
    a, b = split(name)
    if a is None:
        return None
    pa, pb = NM.parse_name(name)
    return (tuple(sorted({s[2] for s in pa if not s[3]})), tuple(sorted({s[2] for s in pb if not s[3]})))


real_keys = set()
for st in (tol_state, wide_state):
    pass
real_exact = {normkey(r["name"]) for r in sc_rows}
pool = [split(r["name"]) for r in sc_rows if split(r["name"])[0]]
STATES = ["Bihar", "Punjab", "Kerala", "Gujarat", "Rajasthan", "Haryana", "Karnataka", "Maharashtra", "Odisha", "West Bengal", "Tamil Nadu", "Uttar Pradesh", "Madhya Pradesh", "Assam", "Delhi"]
givens = collections.Counter()
surn = collections.Counter()
for a, _b in pool:
    ws = [w for w in re.findall(r"[A-Za-z]{3,}", a) if w.lower() not in ("state", "union", "the", "shri", "smt", "india", "limited", "company", "bank", "and", "others")]
    if len(ws) >= 2:
        givens[ws[0].title()] += 1
        surn[ws[-1].title()] += 1
gv, gw = zip(*givens.most_common(1500))
sv, sw = zip(*surn.most_common(1500))


def s2_run(names):
    cnt = collections.Counter()
    ex = []
    for nm in names:
        o, (t, ti), (w, wi) = old(nm), tol(nm), wide(nm)
        cnt["n"] += 1
        cnt["old"] += bool(o)
        cnt["tol"] += bool(t)
        cnt["wide"] += bool(w)
        if w and not o:
            cnt["wide_new_hits"] += 1
            if len(ex) < 40:
                ex.append({"invented": nm, "accepted_as": wi["title"], "list": wi["list"], "date": wi["date"]})
    return cnt, ex


swapped = []
while len(swapped) < 3000:
    (a, _), (_, b) = rng.choice(pool), rng.choice(pool)
    nm = f"{a} v. {b}"
    if normkey(nm) not in real_exact and a.lower() != b.lower():
        swapped.append(nm)
plausible = []
while len(plausible) < 3000:
    first = f"{rng.choices(gv, gw)[0]} {rng.choices(sv, sw)[0]}"
    resp = rng.choice(["State of " + rng.choice(STATES), "Union of India", "State of " + rng.choice(STATES)])
    nm = f"{first} v. {resp}"
    if normkey(nm) not in real_exact:
        plausible.append(nm)
LETTERS = "abcdefghijklmnopqrstuvwxyz"
twins = []
guard = 0
while len(twins) < 3000 and guard < 200000:
    guard += 1
    a, b = rng.choice(pool)
    ws = [w for w in re.findall(r"[A-Za-z]+", a) if len(w) >= 5 and w.lower() not in ("state", "union", "india", "limited", "company", "government")]
    if not ws:
        continue
    w = max(ws, key=len)
    i = rng.randrange(1, len(w) - 1)
    c = rng.choice([x for x in LETTERS if x != w[i].lower() and frozenset((x, w[i].lower())) not in NM._LOOK])
    nm = f"{a.replace(w, w[:i] + c + w[i + 1:], 1)} v. {b}"
    if normkey(nm) not in real_exact:
        twins.append(nm)
for label, names in (("swapped parties", swapped), ("plausible invented names", plausible), ("one unrelated letter changed", twins)):
    cnt, ex = s2_run(names)
    res.setdefault("S2", {})[label] = {"n": cnt["n"], "old_accepts": cnt["old"], "tol_accepts": cnt["tol"], "wide_accepts": cnt["wide"], "accepted_by_wide_but_not_old": cnt["wide_new_hits"], "examples_wide_new": ex}

# ---------------- S3 library
import glob
lib = []
for f in sorted(glob.glob(os.path.join(rec, "chunks", "*_chunks.json"))):
    ch = json.load(open(f, encoding="utf-8"))
    if ch and "case_name" in ch[0]:
        lib.append(ch[0]["case_name"])
lib_old = [old(n) for n in lib]
lib_tol = [tol(n)[0] for n in lib]
res["S3"] = {"library_cases": len(lib), "old_found": sum(bool(x) for x in lib_old), "tol_found_title_list_only": sum(bool(x) for x in lib_tol),
             "tol_still_missing": [n for n, x in zip(lib, lib_tol) if not x]}

# ---------------- speed
use(wide_state)
sample = [r["name"] for r in rng.sample(sc_rows, 1500)] + swapped[:500]
ts = []
for nm in sample:
    t = time.perf_counter()
    C.lookup(nm)
    ts.append((time.perf_counter() - t) * 1000)
res["speed_ms"] = {"n": len(ts), "mean": round(statistics.mean(ts), 2), "p95": round(sorted(ts)[int(len(ts) * .95)], 2), "max": round(max(ts), 1)}
json.dump(res, open(out, "w"), ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in res.items() if not k.endswith("samples")}, ensure_ascii=False, indent=1)[:6000])
