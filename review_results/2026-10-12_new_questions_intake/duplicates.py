"""Duplicate check of the new questions against the earlier 30 and the ruler's 33 questions: (1) by meaning, approximated by word overlap (TF-IDF cosine on words and word pairs; no external service);
(2) by authority: index documents named in the new key that are also key or older-ruling documents of an earlier question or a ruler topic. Private."""
import collections, json, math, os, re, sys
import openpyxl
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
from authorities import A
from adjudication import ADJ
STOP = set("a an the and or of to in on for is are was were be been can could would should must may might will shall do does did not that this with from by as at it its who what when how which if any all have has had than then them they their there these those under into about over after before while where whether such just only also more most other some my me i he she his her we our you your us am so no yes now but up out off too very".split())
def toks(t):
    w = [x for x in re.findall(r"[a-z0-9]+", t.lower()) if x not in STOP and len(x) > 1]
    return w + [f"{a}_{b}" for a, b in zip(w, w[1:])]
wb = openpyxl.load_workbook(os.path.join(ROOT, "review_data/ruler/inputs/2026-10-12_Fix_Test_New_Questions_N01-N30_as_received.xlsx"))
rows = list(wb["Questions"].iter_rows(values_only=True)); hdr = rows[0]
new = {r[0]: r[2] for r in rows[1:]}
real = json.load(open(os.path.join(ROOT, "review_data/ruler/real30_v1.json"), encoding="utf-8"))
old = {q["id"]: q["text"] for q in real["questions"]}
ruler = json.load(open(os.path.join(ROOT, "review_data/ruler/ruler_v2.json"), encoding="utf-8"))
old.update({f"ruler {q['id']}": q["text"] for q in ruler["questions"]})
docs = {**new, **old}
df = collections.Counter()
T = {k: toks(v) for k, v in docs.items()}
for k, t in T.items():
    df.update(set(t))
N = len(T)
def vec(t):
    c = collections.Counter(t)
    return {w: (1 + math.log(n)) * math.log(N / df[w]) for w, n in c.items()}
V = {k: vec(t) for k, t in T.items()}
def cos(a, b):
    num = sum(a[w] * b.get(w, 0) for w in a)
    return num / ((math.sqrt(sum(x * x for x in a.values())) * math.sqrt(sum(x * x for x in b.values()))) or 1)
print("1. BY MEANING (word overlap; 1.00 = identical; 0.30 and above is read by eye)")
flag = []
for q in new:
    sims = sorted(((cos(V[q], V[o]), o) for o in old), reverse=True)[:2]
    mark = "  <== read" if sims[0][0] >= 0.30 else ""
    print(f"   {q:4} best {sims[0][0]:.2f} with {sims[0][1]:<10} next {sims[1][0]:.2f} with {sims[1][1]}{mark}")
    if sims[0][0] >= 0.30:
        flag.append((q, sims[0]))
        print("        NEW:", new[q][:200]); print("        OLD:", old[sims[0][1]][:200])
# authority overlap
key = json.load(open(os.path.join(ROOT, "review_data/ruler/real30_key_v1.json"), encoding="utf-8"))["questions"]
earlier = collections.defaultdict(set)
for qid, k in key.items():
    for d in k.get("key_docs", []):
        earlier[d].add(f"{qid} key")
    for s in k.get("stale_docs", []):
        earlier[s["doc"]].add(f"{qid} older ruling")
for t in ruler["topics"]:
    for e in t.get("expected", []):
        earlier[e["doc"]].add(f"ruler {t['id']} expected")
    for e in t.get("also_acceptable", []):
        d = e["doc"] if isinstance(e, dict) else e
        earlier[d].add(f"ruler {t['id']} also acceptable")
print("\n2. BY AUTHORITY: documents named in the new key that an earlier question or ruler topic also uses")
n = 0
for q, role, label, toks_, year, slack in A:
    st, ds = ADJ[label]
    for d in ds:
        if d in earlier:
            n += 1
            print(f"   {q:4} {role:10} {label[:60]:60} doc {d}: {sorted(earlier[d])}")
print(f"   ({n} overlaps)")
