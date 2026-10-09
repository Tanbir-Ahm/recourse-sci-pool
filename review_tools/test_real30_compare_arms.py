"""Tests for review_tools/real30_compare_arms.py on two invented pools and an invented key. Run: python review_tools/test_real30_compare_arms.py"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import real30_compare_arms as C

FAILS = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{detail}]"))
    if not cond:
        FAILS.append(name)


def it(doc, h=None, also=()):
    return {"doc": doc, "also": list(also), "h": h or f"h{doc}"}


def row(n, doc, h=None):
    return {"n": n, "h": h or f"h{doc}", "doc": doc, "pn": "1", "page": 1, "title": f"Case {doc}", "text": "x", "also": [], "variants": {}}


key = {"questions": {
    "R01": {"reachable": True, "key_docs": [10], "stale_docs": [{"doc": 20, "label": "Old v. State (2000)", "kind": "overruled", "counts_as_stale": True}], "authorities": [{"label": "New v. State", "role": "key"}]},
    "R02": {"reachable": True, "key_docs": [11], "stale_docs": [], "authorities": [{"label": "Other v. State", "role": "key"}]},
    "R21": {"reachable": False, "key_docs": [], "stale_docs": [{"doc": 20, "label": "Old v. State (2000)", "kind": "overruled", "counts_as_stale": True}], "authorities": [{"label": "Gap v. State", "role": "key"}]},
    "R28": {"reachable": None, "key_docs": [], "stale_docs": [], "authorities": []},
}}
base = {"run": {"index_commit": "3c80a26" + "0" * 33, "spend": {"rerank_tokens": 1000}}, "questions": [
    {"qid": "R01", "rows": [row(1, 10), row(2, 31), row(3, 20)], "lists": {"A today": [it(31), it(10), it(20)], "S site shown": [it(31), it(10)]}},
    {"qid": "R02", "rows": [row(1, 40), row(2, 11)], "lists": {"A today": [it(40), it(11)], "S site shown": [it(40)]}},
    {"qid": "R21", "rows": [row(1, 20), row(2, 41)], "lists": {"A today": [it(20), it(41)], "S site shown": [it(20)]}},
    {"qid": "R28", "rows": [row(1, 70)], "lists": {"A today": [it(70)], "S site shown": [it(70)]}}]}
arm = {"run": {"index_commit": "3c80a26" + "0" * 33, "spend": {"rerank_tokens": 1100}, "side_index": {"documents": 2, "passages": 5}}, "questions": [
    {"qid": "R01", "rows": [row(1, 10), row(2, 31), row(3, 20), row(4, 32)], "lists": {"A today": [it(31), it(32), it(10), it(20)], "S site shown": [it(31), it(10)]}},     # key authority 2 -> 3, one new main passage
    {"qid": "R02", "rows": [row(1, 40), row(2, 11)], "lists": {"A today": [it(40), it(11)], "S site shown": [it(40)]}},                                                          # unchanged
    {"qid": "R21", "rows": [row(1, 20), row(2, 90, "side90"), row(3, 91, "side91")], "lists": {"A today": [it(20), it(90, "side90"), it(91, "side91")], "S site shown": [it(90, "side90"), it(20)]}},
    {"qid": "R28", "rows": [row(1, 70)], "lists": {"A today": [it(70)], "S site shown": [it(70)]}}]}
overlay = {"questions": {"R21": {"key_docs": [90], "label": "Gap v. State (side index)"}}}
side_docs, titles = {90, 91}, {90: "GAP v. STATE", 91: "OTHER SIDE v. STATE"}
res = C.compare(base, arm, key, overlay, side_docs, titles)

check("only questions in both pools are compared", res["questions"] == ["R01", "R02", "R21", "R28"] and res["versions"] == ["A today", "S site shown"], res["versions"])
rb, ra = res["rates_base"]["A today"], res["rates_arm_same_key"]["A today"]
check("with the original key both pools count the same answerable questions and the index-gap question is left out", rb["questions"] == ra["questions"] == 2 and rb["hit@5"] == ra["hit@5"] == 2, (rb, ra))
check("with the overlay the arm counts the index-gap question and finds its key authority", res["rates_arm_with_overlay"]["A today"]["questions"] == 3 and res["rates_arm_with_overlay"]["A today"]["hit@5"] == 3, res["rates_arm_with_overlay"]["A today"])
moved = {(m["qid"], m["version"]): m for m in res["moved"]}
check("a key authority that moved on an answerable question is listed with both ranks", moved[("R01", "A today")]["base"] == 2 and moved[("R01", "A today")]["arm"] == 3)
check("a key authority found only through the side index is listed as such", moved[("R21", "A today")]["base"] is None and moved[("R21", "A today")]["arm"] == 2 and "side index" in moved[("R21", "A today")]["note"]
      and moved[("R21", "S site shown")]["arm"] == 1)
check("a question whose rank did not change is not listed", not [m for m in res["moved"] if m["qid"] in ("R02", "R28")], res["moved"])
surf = {(s["qid"], s["version"]): s for s in res["surfaced"]}
check("side-index judgments in the results are listed with rank and title", [h["doc"] for h in surf[("R21", "A today")]["hits"]] == [90, 91] and surf[("R21", "A today")]["hits"][0]["rank"] == 2 and surf[("R21", "A today")]["hits"][0]["title"] == "GAP v. STATE"
      and ("R01", "A today") not in surf)
check("passages the base pool did not show are counted, and those from the side index separately", {u["qid"]: (u["new_rows"], u["from_side_index"]) for u in res["unseen"]} == {"R01": (1, 0), "R21": (2, 2)}, res["unseen"])
check("stale rulings in the top 5 are counted over all the compared questions in both pools (the index-gap question's old ruling too)", res["stale_slots_top5"] == {"A today": {"base": 2, "arm": 2}, "S site shown": {"base": 1, "arm": 1}}, res["stale_slots_top5"])
rep = C.report(res, base["run"], arm["run"], key)
check("the report says it is private and mark-free, names the side index and lists what moved", "PRIVATE" in rep and "no reviewer mark" in rep and "side index of 2 judgments" in rep and "R21" in rep and "Passages of the arm" in rep)
tmp = tempfile.mkdtemp()
paths = {n: os.path.join(tmp, n) for n in ("base.json", "arm.json", "key.json", "ov.json", "man.json")}
for n, obj in (("base.json", base), ("arm.json", arm), ("key.json", key), ("ov.json", overlay), ("man.json", {"documents_detail": [{"doc": 90, "title": "GAP v. STATE"}, {"doc": 91, "title": "OTHER SIDE v. STATE"}]})):
    json.dump(obj, open(paths[n], "w"))
rc = C.main(["--base", paths["base.json"], "--arm", paths["arm.json"], "--key", paths["key.json"], "--overlay", paths["ov.json"], "--side-manifest", paths["man.json"], "--out", os.path.join(tmp, "out")])
check("main writes the report and the json", rc == 0 and os.path.exists(os.path.join(tmp, "out", "ARM_COMPARISON.md")) and os.path.exists(os.path.join(tmp, "out", "arm_comparison.json")))

print()
print("FAILED: " + ", ".join(FAILS) if FAILS else "all passed")
sys.exit(1 if FAILS else 0)
