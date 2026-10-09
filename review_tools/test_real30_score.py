"""Tests for review_tools/real30_score.py on an invented pool and key. Run: python review_tools/test_real30_score.py"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import real30_score as S

FAILS = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{detail}]"))
    if not cond:
        FAILS.append(name)


def it(doc, also=()):
    return {"doc": doc, "also": list(also), "h": f"h{doc}"}


key = {"questions": {
    "R01": {"reachable": True, "key_docs": [10], "stale_docs": [{"doc": 20, "label": "Old v. State (2000)", "kind": "overruled", "counts_as_stale": True}, {"doc": 21, "label": "Narrow v. State (2001)", "kind": "narrower", "counts_as_stale": False}],
            "authorities": [{"label": "New v. State (2020)", "role": "key"}]},
    "R02": {"reachable": True, "key_docs": [11, 12], "stale_docs": [], "authorities": [{"label": "Other v. State (2021)", "role": "key"}]},
    "R06": {"reachable": False, "key_docs": [], "stale_docs": [{"doc": 20, "label": "Old v. State (2000)", "kind": "overruled", "counts_as_stale": True}], "authorities": [{"label": "Missing v. State (2024)", "role": "key"}]},
    "R28": {"reachable": None, "key_docs": [], "stale_docs": [], "authorities": []},
}}
pool = [
    {"qid": "R01", "domain": "A", "lists": {"A today": [it(30), it(31), it(20), it(32), it(33), it(10)], "B no repeats": [it(10), it(21), it(31)], "S site shown": [it(31), it(32), it(10)]}},
    {"qid": "R02", "domain": "B", "lists": {"A today": [it(40), it(50, also=[12])], "B no repeats": [it(41), it(42)], "S site shown": [it(43)]}},
    {"qid": "R06", "domain": "C", "lists": {"A today": [it(20), it(60)], "B no repeats": [it(61)], "S site shown": [it(62)]}},
    {"qid": "R28", "domain": "K", "lists": {"A today": [it(70)], "B no repeats": [it(71)], "S site shown": [it(72)]}},
]
sc = S.score(pool, key)
a, b, s = sc["A today"], sc["B no repeats"], sc["S site shown"]
check("the rank of the first key authority counts passages, best first", a["R01"]["first_rank"] == 6 and b["R01"]["first_rank"] == 1 and s["R01"]["first_rank"] == 3, (a["R01"], b["R01"], s["R01"]))
check("hits are cumulative: top 1, top 5, top 10", b["R01"]["hits"] == {"1": True, "5": True, "10": True} and a["R01"]["hits"] == {"1": False, "5": False, "10": True}, (a["R01"]["hits"], b["R01"]["hits"]))
check("a key authority that appears only as an identical-text copy counts", a["R02"]["first_rank"] == 2, a["R02"])
check("no key authority in the list gives no rank and no hit", b["R02"]["first_rank"] is None and not any(b["R02"]["hits"].values()))
check("a stale ruling in the top 5 is listed with its rank and whether it counts", a["R01"]["stale"] == [{"rank": 3, "doc": 20, "label": "Old v. State (2000)", "kind": "overruled", "counts_as_stale": True}], a["R01"]["stale"])
check("a narrower ruling is listed but does not count", b["R01"]["stale"][0]["counts_as_stale"] is False and b["R01"]["stale"][0]["kind"] == "narrower")
check("a version starting with S is scored on everything it showed", s["R01"]["shown"] == 3 and s["R01"]["hits"]["5"] is True)
check("a stale ruling below rank 5 is not listed for a normal version", all(x["rank"] <= 5 for x in a["R01"]["stale"]))
sm = S.summarise(sc, key)
check("the rates leave out the index gap and the control", sm["A today"]["questions"] == 2 and sm["B no repeats"]["questions"] == 2, sm["A today"])
check("the rates add up", (sm["B no repeats"]["hit@1"], sm["B no repeats"]["hit@5"], sm["A today"]["hit@5"], sm["A today"]["hit@10"]) == (1, 1, 1, 2), sm)
check("stale slots are counted only over the reachable questions and only the ones that count", sm["A today"]["stale_slots"] == 1 and sm["A today"]["stale_questions"] == 1 and sm["B no repeats"]["stale_slots"] == 0 and sm["B no repeats"]["narrower_slots"] == 1, sm)
check("an old ruling in the top 5 of an index-gap question is counted apart, not in the rates", sm["A today"]["gap_stale_slots"] == 1 and sm["A today"]["gap_stale_questions"] == 1 and sm["B no repeats"]["gap_stale_slots"] == 0, sm["A today"])
only = S.summarise(sc, key, only={"R01"})
check("the rates can be limited to a set of questions", only["A today"]["questions"] == 1 and only["A today"]["gap_stale_slots"] == 0 and only["B no repeats"]["hit@1"] == 1, only["A today"])
rep = S.report(pool, key, sc, sm, {"when": "now", "index_commit": "3c80a26abc", "spend": {"rerank_tokens": 1234}})
check("the report says it is private, names the index gap and the control apart, and lists the older ruling", "PRIVATE" in rep and "Never send to reviewers" in rep and "R06" in rep.split("Scored apart")[1] and "R28" in rep.split("Scored apart")[1] and "Old v. State (2000)" in rep, rep[-600:])
# an overlay: key documents that only a side index holds
ov = {"questions": {"R06": {"key_docs": [60], "label": "Missing v. State (2024), side index only"}}}
k2 = S.with_overlay(key, ov)
check("an overlay makes an index-gap question answerable for one pool and leaves the key as it was", k2["questions"]["R06"]["reachable"] is True and k2["questions"]["R06"]["key_docs"] == [60]
      and key["questions"]["R06"]["reachable"] is False and key["questions"]["R06"]["key_docs"] == [] and len(key["questions"]["R06"]["authorities"]) == 1 and len(k2["questions"]["R06"]["authorities"]) == 2)
sm2 = S.summarise(S.score(pool, k2), k2)
check("scored with the overlay the question counts in the rates, and its older ruling counts as stale, no longer as an index-gap stale",
      sm2["A today"]["questions"] == 3 and sm2["A today"]["hit@5"] == 2 and sm2["A today"]["stale_slots"] == 2 and sm2["A today"]["gap_stale_slots"] == 0 and sm2["B no repeats"]["questions"] == 3, sm2["A today"])

tmp = tempfile.mkdtemp()
pp, kp = os.path.join(tmp, "pool.json"), os.path.join(tmp, "key.json")
json.dump({"questions": pool, "run": {"when": "now", "index_commit": "x" * 40, "spend": {"rerank_tokens": 1}}}, open(pp, "w"))
json.dump(key, open(kp, "w"))
check("main writes the json and the report", S.main(["--pool", pp, "--key", kp, "--out", os.path.join(tmp, "out")]) == 0 and os.path.exists(os.path.join(tmp, "out", "AUTHORITY_HITS.md")) and os.path.exists(os.path.join(tmp, "out", "authority_hits.json")))
op = os.path.join(tmp, "overlay.json")
json.dump(ov, open(op, "w"))
S.main(["--pool", pp, "--key", kp, "--overlay", op, "--out", os.path.join(tmp, "out2")])
check("main with --overlay scores the pool with the extra key documents", json.load(open(os.path.join(tmp, "out2", "authority_hits.json")))["summary"]["A today"]["questions"] == 3
      and json.load(open(os.path.join(tmp, "out", "authority_hits.json")))["summary"]["A today"]["questions"] == 2)

print()
print("FAILED: " + ", ".join(FAILS) if FAILS else "all passed")
sys.exit(1 if FAILS else 0)
