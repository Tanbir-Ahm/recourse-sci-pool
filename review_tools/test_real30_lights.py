"""Tests for review_tools/real30_lights.py on an invented pool, key and marks. Run: python review_tools/test_real30_lights.py"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import real30_lights as L

FAILS = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{detail}]"))
    if not cond:
        FAILS.append(name)


def row(n, doc, **variants):
    return {"n": n, "doc": doc, "also": [], "variants": variants, "text": f"passage {n}"}


def q(qid, domain, rows, lists):
    return {"qid": qid, "domain": domain, "kind": "legal", "rows": rows, "lists": lists}


def items(*docs):
    return [{"doc": d, "also": [], "h": f"h{d}"} for d in docs]


key = {"questions": {
    "R01": {"reachable": True, "key_docs": [10], "stale_docs": [{"doc": 20, "label": "Old (2000)", "kind": "overruled", "counts_as_stale": True}]},
    "R02": {"reachable": True, "key_docs": [11], "stale_docs": [{"doc": 21, "label": "Narrow (2001)", "kind": "narrower", "counts_as_stale": False}]},
    "R03": {"reachable": True, "key_docs": [12], "stale_docs": []},
    "R06": {"reachable": False, "key_docs": [], "stale_docs": []},
    "R28": {"reachable": None, "key_docs": [], "stale_docs": []}}}
V = "A today"
# domain A: R01 (a trap) has five passages, four useful; the old ruling (doc 20) is in the top 5.  R02 has five, all useful.
pool = [
    q("R01", "A", [row(i, 100 + i, **{V: i}) for i in range(1, 6)], {V: items(100, 20, 102, 103, 104, 105)}),
    q("R02", "A", [row(i, 200 + i, **{V: i}) for i in range(1, 6)], {V: items(201, 202, 203, 204, 205)}),
    q("R03", "B", [row(i, 300 + i, **{V: i}) for i in range(1, 6)], {V: items(301, 302, 303, 304, 305)}),
    q("R06", "C", [row(i, 400 + i, **{V: i}) for i in range(1, 6)], {V: items(401, 402, 403, 404, 405)}),
    q("R28", "K", [row(i, 500 + i, **{V: i}) for i in range(1, 6)], {V: items(501, 502, 503, 504, 505)}),
]
marks = {("R01", 1): "Yes", ("R01", 2): "Partly", ("R01", 3): "Yes", ("R01", 4): "Partly", ("R01", 5): "No",
         **{("R02", i): "Yes" for i in range(1, 6)},
         ("R03", 1): "Yes", ("R03", 2): "Misleading", ("R03", 3): "Yes", ("R03", 4): "Yes", ("R03", 5): "Yes",
         **{("R06", i): "No" for i in range(1, 6)}, **{("R28", i): "No" for i in range(1, 6)}}
mark_of = lambda qid, n: marks.get((qid, n))
res = L.lights(pool, key, mark_of)[V]
check("domain A: shares 0.8 and 1.0 average 0.9, no Misleading in the top 3: relevance green", res["A"]["relevance"][0] == "green" and abs(res["A"]["relevance"][1] - 0.9) < 1e-9 and res["A"]["relevance"][2] == 0, res["A"])
check("domain A: the one trap question lets its old ruling into the top 5: currency red (1 of 1)", res["A"]["currency"] == ("red", 1, 1), res["A"]["currency"])
check("a Misleading passage at rank 2 stops a domain being green even with a high share (R03: 4 of 5 useful)", res["B"]["relevance"][0] == "red" and res["B"]["relevance"][2] == 1, res["B"]["relevance"])
check("a domain with no trap question says so", res["B"]["currency"][0] == "no trap")
check("a narrower older ruling does not count as a trap question", "currency" in res["A"] and res["A"]["currency"][2] == 1)
check("the index gap and the control are left out of the lights", "C" not in res and "K" not in res, list(res))
check("thresholds: 0.8 is green, just under is amber, under 0.6 is red", L.relevance_light([(0.8, False, 5)])[0] == "green" and L.relevance_light([(0.79, False, 5)])[0] == "amber" and L.relevance_light([(0.59, False, 5)])[0] == "red")
check("red also when a Misleading sits in the top 3 on more than half the questions, amber when on half or fewer", L.relevance_light([(0.9, True, 5), (0.9, True, 5), (0.9, False, 5)])[0] == "red" and L.relevance_light([(0.9, True, 5), (0.9, False, 5)])[0] == "amber")
check("currency: none is green, half is amber, more than half is red", L.currency_light([False, False])[0] == "green" and L.currency_light([True, False])[0] == "amber" and L.currency_light([True, True, False])[0] == "red")
check("a question with nothing marked is not scored", L.question_relevance(pool[0], V, lambda qid, n: None) is None and L.relevance_light([])[0] == "no data")
check("an S version is scored on everything it showed", len(L.slots(q("R09", "A", [row(i, 900 + i, **{"S site shown": i}) for i in range(1, 8)], {}), "S site shown")) == 7)
check("a normal version is scored on its top 5 only", len(L.slots(q("R09", "A", [row(i, 900 + i, **{V: i}) for i in range(1, 8)], {}), V)) == 5)

# treatments from two runs that disagree on one passage
runs = {("ChatGPT", "A"): {(qq["qid"], r["n"]): marks[(qq["qid"], r["n"])] for qq in pool for r in qq["rows"]}, ("Gemini", "A"): {}}
runs[("Gemini", "A")] = dict(runs[("ChatGPT", "A")])
runs[("Gemini", "A")][("R01", 1)] = "No"
passages = {(qq["qid"], r["n"]): r for qq in pool for r in qq["rows"]}
tr = L.treatments(runs, passages)
check("four ways of settling disagreement, plus each run alone", set(tr) == {"agreed only", "ties to the lower mark", "ties to the higher mark", "run ChatGPT/A", "run Gemini/A"}, set(tr))
check("agreed only drops the split passage, lower takes No, higher takes Yes", tr["agreed only"]("R01", 1) is None and tr["ties to the lower mark"]("R01", 1) == "No" and tr["ties to the higher mark"]("R01", 1) == "Yes")
allres = {name: L.lights(pool, key, fn) for name, fn in tr.items()}
check("under 'lower' R01's share falls to 0.6 (Yes becomes No) and the domain average to 0.8: still green; under agreed it is 0.75 and 1.0", abs(allres["ties to the lower mark"][V]["A"]["relevance"][1] - 0.8) < 1e-9 and allres["ties to the lower mark"][V]["A"]["relevance"][0] == "green", allres["ties to the lower mark"][V]["A"])
rep = L.report(allres, {"A": "Arrest", "B": "Bail"})
check("the report names both lights and the draft status", "relevance / currency" in rep and "first reading, not proof" in rep and "Arrest" in rep, rep[:300])

print()
print("FAILED: " + ", ".join(FAILS) if FAILS else "all passed")
sys.exit(1 if FAILS else 0)
