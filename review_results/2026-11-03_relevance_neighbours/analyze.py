"""Reads scores_fresh.json (36 fresh questions) and ../2026-10-31_relevance_gate/scores.json (the 47 questions that chose the floors) and counts, for the gate as built (statute floor 0.45, judgment floor 0.40) and for the rule
'a statute below the floor is kept when a statute of the same Act within K section numbers has a re-rank score at or above the floor' (K = 1, 2):
  - expected sections the search returned, and how many the gate drops (the cost of the gate)
  - how many of those the neighbour rule gives back (its benefit), and how many NOT expected statutes it also keeps (its cost)
Run: python3 analyze.py   (scores_fresh.json comes from: cd /home/user/recourse && python3 <this folder>/run.py -- the retrieval reads its data relative to the Recourse checkout)"""
import json, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
F_ST, F_JU = 0.45, 0.40


def num(s):
    m = re.match(r"\d+", str(s or ""))
    return int(m.group(0)) if m else None


def analyse(records, K_list=(1, 2)):
    res = {"questions": len(records), "returned_expected": 0, "gate_drops_expected": 0, "emptied": 0, "statutes_total": 0, "statutes_gate_keeps": 0, "unexpected_statutes": 0, "unexpected_gate_drops": 0}
    for K in K_list:
        res[f"K{K}_rescues_expected"] = 0
        res[f"K{K}_rescues_unexpected"] = 0
        res[f"K{K}_keeps_total"] = 0
    detail = []
    for r in records:
        exp = {(a, n) for a, ns in (r.get("exp") or {}).items() for n in ns}
        st = [x for x in r["rows"] if x["type"] == "statute"]
        ju = [x for x in r["rows"] if x["type"] != "statute"]
        keep_st = [x for x in st if x["rr"] is None or x["rr"] >= F_ST]
        keep_ju = [x for x in ju if x["rr"] is None or x["rr"] >= F_JU]
        if (st or ju) and not keep_st and not keep_ju:
            res["emptied"] += 1
        res["statutes_total"] += len(st)
        res["statutes_gate_keeps"] += len(keep_st)
        for x in st:
            is_exp = (x["act"], x["sec"]) in exp
            kept = x in keep_st
            if is_exp:
                res["returned_expected"] += 1
                if not kept:
                    res["gate_drops_expected"] += 1
            else:
                res["unexpected_statutes"] += 1
                if not kept:
                    res["unexpected_gate_drops"] += 1
        for K in K_list:
            anchors = [(x["act"], num(x["sec"])) for x in keep_st if num(x["sec"]) is not None]
            keeps = 0
            for x in st:
                if x in keep_st:
                    keeps += 1
                    continue
                n = num(x["sec"])
                rescued = n is not None and any(a == x["act"] and abs(n - m) <= K and m != n for a, m in anchors)
                if rescued:
                    keeps += 1
                    if (x["act"], x["sec"]) in exp:
                        res[f"K{K}_rescues_expected"] += 1
                        detail.append((r["q"][:70], K, f'{x["act"]} {x["sec"]}', x["rr"], "EXPECTED"))
                    else:
                        res[f"K{K}_rescues_unexpected"] += 1
                        detail.append((r["q"][:70], K, f'{x["act"]} {x["sec"]}', x["rr"], "not expected"))
            res[f"K{K}_keeps_total"] += keeps
    return res, detail


fresh = json.load(open(os.path.join(HERE, "scores_fresh.json")))
old = json.load(open(os.path.join(HERE, "..", "2026-10-31_relevance_gate", "scores.json")))
for name, recs in (("FRESH (36 questions, not used to choose anything)", fresh), ("OLD (47 questions that chose the floors; cost side only)", [r for r in old if r.get("kind") == "pos"])):
    res, detail = analyse(recs)
    print("==", name)
    for k, v in res.items():
        print(f"  {k}: {v}")
    if name.startswith("FRESH"):
        print("  rescues (K, section, rerank, status):")
        for d in detail:
            print("   ", d)
# where each fresh expected section stands
print("== FRESH: every expected section: retrieved? rerank?")
for r in fresh:
    exp = {(a, n) for a, ns in r["exp"].items() for n in ns}
    got = {(x["act"], x["sec"]): x["rr"] for x in r["rows"] if x["type"] == "statute"}
    print(("  " if any(k in got for k in exp) else "  MISS "), r["q"][:68], "|", {f"{a} {n}": got.get((a, n), "not retrieved") for a, n in sorted(exp)})
