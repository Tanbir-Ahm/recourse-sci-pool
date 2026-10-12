"""Round 2 duplicate check of the replacement questions (N02, N12, N15) and, for completeness, of the whole round-2 file:
(1) by question wording: TF-IDF cosine on words and word pairs against the earlier 30 and the ruler's 33 questions;
(2) by expected answer: the same cosine between the new key's 'Expected answer' and the earlier 30's expected answers (wording can differ while the legal point is the same);
(3) by authority: index documents named in the final key that an earlier question or ruler topic also uses.
No external service; private (it reads the key)."""
import collections, json, math, os, re, sys
import openpyxl
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(HERE, "..")); sys.path.insert(0, HERE)
from authorities import A
from adjudication import ADJ
from authorities_round2 import A2_NEW, REPLACED
ADJ2 = {
 "D.K. Basu v. State of West Bengal (1996/97)": ("IN", [14580]),
 "Arnesh Kumar v. State of Bihar (2014)": ("IN", [41736]),
 "Joginder Kumar v. State of U.P. (1994)": ("ABSENT", []),
 "Gian Singh v. State of Punjab (2012)": ("IN", [39579]),
 "Parbatbhai Aahir v. State of Gujarat (2017)": ("IN", [1000250282]),
 "Narinder Singh v. State of Punjab (2014)": ("IN", [41348]),
 "Rajnesh v. Neha (2020)": ("IN", [1000252794]),
 "Shyamlal Devda v. Parimala (2020)": ("IN", [1000252355]),
 "Juveria Abdul Majid Patni v. Atif Iqbal Mansoori (2014)": ("IN", [1000004478]),
 "Mahmood Farooqui v. State (Govt. of NCT of Delhi) (2017)": ("ABSENT", []),
}
STOP = set("a an the and or of to in on for is are was were be been can could would should must may might will shall do does did not that this with from by as at it its who what when how which if any all have has had than then them they their there these those under into about over after before while where whether such just only also more most other some my me i he she his her we our you your us am so no yes now but up out off too very".split())
def toks(t):
    w = [x for x in re.findall(r"[a-z0-9]+", (t or "").lower()) if x not in STOP and len(x) > 1]
    return w + [f"{a}_{b}" for a, b in zip(w, w[1:])]
def cos_factory(docs):
    df = collections.Counter(); T = {k: toks(v) for k, v in docs.items()}
    for t in T.values():
        df.update(set(t))
    N = len(T)
    def vec(t):
        c = collections.Counter(t)
        return {w: (1 + math.log(n)) * math.log(N / df[w]) for w, n in c.items()}
    V = {k: vec(t) for k, t in T.items()}
    def cos(a, b):
        a, b = V[a], V[b]
        num = sum(a[w] * b.get(w, 0) for w in a)
        return num / ((math.sqrt(sum(x * x for x in a.values())) * math.sqrt(sum(x * x for x in b.values()))) or 1)
    return cos
R1 = os.path.join(ROOT, "review_data/ruler/inputs/2026-10-12_Fix_Test_New_Questions_N01-N30_as_received.xlsx")
R2 = os.path.join(ROOT, "review_data/ruler/inputs/2026-10-12_Fix_Test_New_Questions_N01-N30_round2_as_received.xlsx")
def sheet(path, name):
    rows = list(openpyxl.load_workbook(path)[name].iter_rows(values_only=True)); hdr = rows[0]
    return hdr, {r[0]: dict(zip(hdr, r)) for r in rows[1:]}
_, q2 = sheet(R2, "Questions"); _, k2 = sheet(R2, "Key"); _, q1 = sheet(R1, "Questions")
new = {i: r["Question text"] for i, r in q2.items()}
newans = {i: r["Expected answer"] for i, r in k2.items()}
real = json.load(open(os.path.join(ROOT, "review_data/ruler/real30_v1.json"), encoding="utf-8"))
old = {q["id"]: q["text"] for q in real["questions"]}
ruler = json.load(open(os.path.join(ROOT, "review_data/ruler/ruler_v2.json"), encoding="utf-8"))
old.update({f"ruler {q['id']}": q["text"] for q in ruler["questions"]})
key = json.load(open(os.path.join(ROOT, "review_data/ruler/real30_key_v1.json"), encoding="utf-8"))["questions"]
oldans = {f"{i} answer": k.get("expected_answer", "") for i, k in key.items()}
CHANGED = ["N02", "N12", "N15"]
print("1. BY QUESTION WORDING (1.00 = identical; 0.30 and above is read by eye)")
docs = {**{f"new {i}": t for i, t in new.items()}, **old}
cos = cos_factory(docs)
for q in new:
    sims = sorted(((cos(f"new {q}", o), o) for o in old), reverse=True)[:2]
    mark = "  <== read" if sims[0][0] >= 0.30 else ""
    star = " *" if q in CHANGED else "  "
    print(f"  {star}{q:4} best {sims[0][0]:.2f} with {sims[0][1]:<10} next {sims[1][0]:.2f} with {sims[1][1]}{mark}")
print("\n   the replaced round-1 questions against the round-2 ones (should be different):")
for q in CHANGED:
    d = {"a": q1[q]["Question text"], "b": q2[q]["Question text"]}
    c = cos_factory({**d, **old}); print(f"     {q}: round 1 vs round 2 wording similarity {c('a','b'):.2f}")
print("\n2. BY EXPECTED ANSWER (new key's answer against the earlier 30's answers; same scale)")
adocs = {**{f"new {i}": t for i, t in newans.items()}, **oldans}
cosa = cos_factory(adocs)
for q in CHANGED:
    sims = sorted(((cosa(f"new {q}", o), o) for o in oldans), reverse=True)[:3]
    print(f"   {q}: " + "; ".join(f"{o} {s:.2f}" for s, o in sims))
print("   (all new answers, best earlier answer:)")
for q in newans:
    s, o = max((cosa(f"new {q}", o), o) for o in oldans)
    if s >= 0.20 or q in CHANGED:
        print(f"     {q:4} {s:.2f} with {o}")
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
print("\n3. BY AUTHORITY: documents named in the FINAL key (round 1 minus the replaced questions, plus round 2) that an earlier question or ruler topic also uses")
final = [x for x in A if x[0] not in REPLACED] + list(A2_NEW)
n = 0; per = collections.defaultdict(list)
for q, role, label, tk, year, slack in final:
    st, ds = ({**ADJ, **ADJ2})[label]
    for d in ds:
        if d in earlier:
            n += 1; per[q].append((role, label, d, sorted(earlier[d])))
            if q in CHANGED or True:
                print(f"   {q:4} {role:10} {label[:62]:62} doc {d}: {sorted(earlier[d])}")
print(f"   ({n} overlaps)")
json.dump({"changed": CHANGED, "overlaps": per}, open(os.path.join(HERE, "duplicates_round2.json"), "w"), indent=1, default=list)
