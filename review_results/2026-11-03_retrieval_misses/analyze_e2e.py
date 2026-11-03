"""
Reads e2e_<config>_<set>.json files and prints: expected sections reaching the model (per section, per question), by Act and by kind; and (with --detail) every miss.
Usage: python3 analyze_e2e.py <file.json> [<file.json> ...] [--detail]
"""
import json, sys
from collections import defaultdict

def norm_act(a):
    a = (a or "").upper()
    if a.startswith("BSA"):
        return "BSA"
    return a

def got_set(row):
    s = set()
    for g in row["got"]:
        if g.get("type") == "statute" or g.get("sec"):
            if g.get("case"):
                continue
            s.add((norm_act(g.get("act")), str(g.get("sec")).upper()))
    return s

def analyse(path, detail=False, quiet=False):
    rows = json.load(open(path))
    tot = hit = 0
    q_all = q_any = 0
    by_act = defaultdict(lambda: [0, 0])
    by_kind = defaultdict(lambda: [0, 0])
    misses = []
    errs = 0
    for r in rows:
        if r.get("error"):
            errs += 1
            continue
        g = got_set(r)
        exp = [(a, n) for a, v in r["exp"].items() for n in v]
        h = [e for e in exp if e in g]
        tot += len(exp); hit += len(h)
        for e in exp:
            by_act[e[0]][1] += 1
            by_kind[r["kind"] or "-"][1] += 1
            if e in g:
                by_act[e[0]][0] += 1
                by_kind[r["kind"] or "-"][0] += 1
        q_any += 1 if h else 0
        q_all += 1 if len(h) == len(exp) else 0
        if len(h) < len(exp):
            misses.append((r, [e for e in exp if e not in g], g))
    if not quiet:
        print(f"== {path.split('/')[-1]}: {len(rows)} questions, {errs} errors")
        print(f"   expected sections reaching the model: {hit} of {tot} ({100*hit/max(tot,1):.0f}%)   questions with at least one: {q_any}   with all: {q_all}")
        print("   by Act:  " + "   ".join(f"{a} {x}/{y}" for a, (x, y) in sorted(by_act.items())))
        print("   by kind: " + "   ".join(f"{a} {x}/{y}" for a, (x, y) in sorted(by_kind.items())))
        if detail:
            for r, miss, g in misses:
                print("   MISS", miss, "|", r["q"][:100])
                print("        got:", sorted(f"{a} {n}" for a, n in g)[:12])
    return hit, tot, misses

if __name__ == "__main__":
    detail = "--detail" in sys.argv
    for p in [a for a in sys.argv[1:] if not a.startswith("--")]:
        analyse(p, detail)
