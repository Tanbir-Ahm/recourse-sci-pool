"""Moves the statute floor on the 36 fresh questions (not used to choose anything) and on the 47 questions that chose it: expected sections dropped, and statutes that are not expected still handed over. Run: python3 sweep.py"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
fresh = json.load(open(os.path.join(HERE, "scores_fresh.json")))
old = json.load(open(os.path.join(HERE, "..", "2026-10-31_relevance_gate", "scores.json")))
def run(records, floor):
    exp_ret = exp_drop = unexp = unexp_kept = 0
    for r in records:
        exp = {(a, n) for a, ns in (r.get("exp") or {}).items() for n in ns}
        for x in r["rows"]:
            if x["type"] != "statute":
                continue
            kept = x["rr"] is None or x["rr"] >= floor
            if (x["act"], x["sec"]) in exp:
                exp_ret += 1
                exp_drop += (not kept)
            else:
                unexp += 1
                unexp_kept += kept
    return exp_ret, exp_drop, unexp, unexp_kept
tot_exp = sum(len([n for ns in r["exp"].values() for n in ns]) for r in fresh)
print(f"fresh set: {tot_exp} expected sections in all; the search returned {run(fresh, 0)[0]} of them")
print("floor | FRESH: expected dropped / returned | not-expected statutes kept / handed over | OLD (pos only): expected dropped / returned | not-expected kept / handed over")
for fl in (0.45, 0.42, 0.40, 0.38, 0.36, 0.34, 0.30, 0.0):
    a = run(fresh, fl); b = run([r for r in old if r.get("kind") == "pos"], fl)
    print(f" {fl:.2f} |  {a[1]:>2} / {a[0]:<2}  |  {a[3]:>2} / {a[2]:<2}  |  {b[1]:>2} / {b[0]:<2}  |  {b[3]:>2} / {b[2]:<2}")
print("the fresh expected sections the 0.45 floor drops:")
for r in fresh:
    exp = {(a, n) for a, ns in r["exp"].items() for n in ns}
    for x in r["rows"]:
        if x["type"] == "statute" and (x["act"], x["sec"]) in exp and x["rr"] is not None and x["rr"] < 0.45:
            print("  ", x["act"], x["sec"], x["rr"], "|", r["q"][:80])
