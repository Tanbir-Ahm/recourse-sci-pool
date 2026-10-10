"""Tests for review_tools/score_challenger_arm.py on an invented pool and invented marks (no network, no spend). Run: python review_tools/test_score_challenger_arm.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import score_challenger_arm as C

FAILS = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{detail}]"))
    if not cond:
        FAILS.append(name)


def mk_q(qid, with_baseline=True):
    rows = []
    for n in range(1, 9):
        v = {}
        if n <= 5:
            v[C.B_ARM if with_baseline else C.A_ARM] = n
        if n in (1, 2, 3, 6, 7):
            v[C.R_ARM] = (1, 2, 3, 6, 7).index(n) + 1
        rows.append({"n": n, "h": f"{qid}h{n}", "doc": n, "variants": v})
    rows.append({"n": 9, "h": f"{qid}h1", "doc": 1, "variants": {}, "anchor_of": 1})           # an anchor belongs to no arm and is left out
    return {"qid": qid, "rows": rows}


pool = [mk_q("R90"), mk_q("R91")]
g = C.groups_of(pool[0], C.B_ARM)
check("groups: kept, entering and leaving are set differences of the two top 5s; anchors are ignored", g["kept (in both)"] == [1, 2, 3] and g["entering (R only)"] == [6, 7] and g["leaving (baseline only)"] == [4, 5], g)


def runs_with(marks):
    """marks: {n: mark} applied to both questions and both tools."""
    one = {(q, n): m for q in ("R90", "R91") for n, m in marks.items()}
    return {("ChatGPT", "TA"): dict(one), ("Gemini", "TA"): dict(one)}


base = {1: "Yes", 2: "Yes", 3: "Partly", 4: "Partly", 5: "No"}
ok = C.score(pool, runs_with({**base, 6: "Yes", 7: "Partly"}))
check("a challenger whose entering passages are as good as the leaving ones: PROCEED", ok["rule"]["verdict"] == "PROCEED" and ok["settlements"]["ChatGPT alone"]["entering"]["useful"] == 4 and ok["settlements"]["ChatGPT alone"]["leaving"]["useful"] == 2, ok["rule"])
bad = C.score(pool, runs_with({**base, 6: "Misleading", 7: "Misleading"}))
check("entering passages that mislead (4 against 0 leaving, more than one apart): DO NOT PROCEED", bad["rule"]["verdict"] == "DO NOT PROCEED", bad["rule"])
weak = C.score(pool, runs_with({**base, 6: "No", 7: "No"}))
check("entering passages that are all useless (0 useful against 2 leaving useful, pooled): DO NOT PROCEED", weak["rule"]["verdict"] == "DO NOT PROCEED", weak["rule"])
edge = C.score(pool, runs_with({**base, 6: "Yes", 7: "No"}))
check("entering as useful as leaving (2 useful against 2, pooled) with one No among them: PROCEED", edge["rule"]["verdict"] == "PROCEED" and edge["settlements"]["Gemini alone"]["entering"]["useful"] == 2, edge["rule"])
inc = C.score(pool, runs_with({**base, 6: "Yes"}))
check("a passage nobody marked: INCOMPLETE, never a verdict", inc["rule"]["verdict"] == "INCOMPLETE" and inc["coverage"]["entering (R only)"]["not_marked_by_any_run"] == 2, inc["coverage"])
pq = ok["per_question"]["R90"]
check("per-question lists name the entering and leaving rows", pq["entering (R only)"] == [6, 7] and pq["leaving (baseline only)"] == [4, 5])
only_a = C.score([mk_q("R90", False), mk_q("R91", False)], runs_with({**base, 6: "Yes", 7: "Partly"}))
check("without a baseline arm the recorded version A is used, and the output says so", only_a["baseline"] == C.A_ARM and only_a["rule"]["verdict"] == "PROCEED")
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "score_challenger_arm.py"), encoding="utf-8").read()
check("the scorer never reads the private key", "real30_key" not in src.replace("Nothing is read from the key", "") and "open(" not in src.split("def main")[0])
print()
print("FAILED: " + ", ".join(FAILS) if FAILS else "all passed")
sys.exit(1 if FAILS else 0)
