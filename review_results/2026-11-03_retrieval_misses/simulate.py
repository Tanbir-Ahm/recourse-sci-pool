"""Offline policy simulation on the stored diagnostics (diag_*.json) + the end-to-end base sets (e2e_shelf_*.json).
Policy 'widen(P, E, f)': add to what already reaches the model up to E statute chunks from the top P by cosine, taking those with the highest re-ranker score that are >= f.
Policy 'gap(g, cap)': the old rule with a different gap and cap (cosine only).
"""
import json, sys
from analyze_e2e import got_set, norm_act
def load(name, qmod):
    d = json.load(open(f"diag_{qmod}.json")); e = json.load(open(f"e2e_shelf_{qmod}.json"))
    return list(zip(d, e))
def key(r): return (norm_act(r["act"]), r["sec"].upper())
def evaluate(sets, policy):
    tot = hit = extras = 0; nq = 0; per = []
    for qmod in sets:
        for d, e in load(*qmod):
            base = got_set(e)
            add = policy(d, base)
            allset = base | add
            exp = [(a, n) for a, v in d["exp"].items() for n in v]
            h = sum(1 for x in exp if x in allset)
            tot += len(exp); hit += h; extras += len(add - base); nq += 1
            per.append((d["q"], [x for x in exp if x not in allset], len(add - base)))
    return hit, tot, extras / nq, per
def widen(P, E, f, cosfloor=0.0):
    def pol(d, base):
        pool = [r for r in d["stat"][:P] if r.get("rr") is not None and r["cos"] >= cosfloor and key(r) not in base]
        pool.sort(key=lambda r: -r["rr"])
        return {key(r) for r in pool[:E] if r["rr"] >= f}
    return pol
def gapcap(g, cap, floor=0.34):
    def pol(d, base):
        top = d["stat"][0]["cos"]
        rows = [r for r in d["stat"] if r["cos"] >= floor and top - r["cos"] <= g][:cap]
        return {key(r) for r in rows}
    return pol
SETS = [("questions", "questions"), ("questions_fresh", "questions_fresh")]
SETS = [("questions",), ("questions_fresh",)]
SETS = [("questions", "questions"), ("questions_fresh", "questions_fresh")]
if __name__ == "__main__":
    # load() signature takes (name, qmod); both are the same string here
    sets = [("questions", "questions"), ("questions_fresh", "questions_fresh")]
    sets = [(a, b) for a, b in sets]
    base = evaluate(sets, lambda d, b: set())
    print("today      : %d of %d expected reach the model; extras/question 0.00" % (base[0], base[1]))
    for g, cap in [(0.08, 5), (0.12, 7), (0.15, 8), (0.20, 10)]:
        r = evaluate(sets, gapcap(g, cap)); print("gap %.2f cap %2d : %d of %d; extras/question %.2f" % (g, cap, r[0], r[1], r[2]))
    for P in (8, 10, 15, 20, 30):
        for E in (2, 3, 4):
            for f in (0.40, 0.50, 0.60):
                r = evaluate(sets, widen(P, E, f)); print("widen P=%2d E=%d f=%.2f : %d of %d; extras/question %.2f" % (P, E, f, r[0], r[1], r[2]))
