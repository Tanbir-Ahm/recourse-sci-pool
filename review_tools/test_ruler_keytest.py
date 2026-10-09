"""Tests for review_tools/ruler_keytest.py and for running the ruler's questions through the pool runner's adapter. Run: python review_tools/test_ruler_keytest.py"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pool_runner as P
import ruler as RU
import ruler_keytest as K

FAILS = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{detail}]"))
    if not cond:
        FAILS.append(name)


RULER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "review_data", "ruler", "ruler_v2.json")
R = RU.load(RULER)
keys = K.key_hashes(R)
dev = P.ruler_questions(RULER, "dev")
check("the ruler's tuning half is 24 questions, 12 everyday and 12 legal, and no frozen question", len(dev) == 24 and sum(q["kind"] == "everyday" for q in dev) == 12 and all(q["half"] == "dev" for q in dev), len(dev))
check("each carries its topic's area as its domain and has at least one key-paragraph hash", all(q["domain"] and keys[q["id"]] for q in dev))
check("the superseded Q06 is not run; Q06v2 is", "Q06" not in {q["id"] for q in dev} and "Q06v2" in {q["id"] for q in dev})
try:
    P.ruler_questions(RULER, "sealed")
    ok = False
except Exception as e:                                  # noqa: BLE001
    ok = type(e).__name__ == "FrozenHalfError"
check("the frozen half is refused without --final (the ruler's own guard)", ok)

q1 = dev[0]["id"]
h = sorted(keys[q1])[0]
it = lambda hh: {"doc": 1, "also": [], "h": hh}
pool = [{"qid": q1, "domain": "arrest_bail", "kind": "everyday", "lists": {"A today": [it("x"), it("y"), it(h)] + [it("z")] * 5, "B no repeats": [it("x")] * 10, "S site shown": [it(h)]}},
        {"qid": dev[1]["id"], "domain": "arrest_bail", "kind": "legal", "lists": {"A today": [it(sorted(keys[dev[1]["id"]])[0])] + [it("x")] * 9, "B no repeats": [it("x")] * 10, "S site shown": [it("x")]}}]
sc = K.score(pool, keys)
check("the rank counts passages and the hits are cumulative", sc["A today"][q1]["first_rank"] == 3 and sc["A today"][q1]["hits"] == {"1": False, "3": True, "5": True, "10": True}, sc["A today"][q1])
check("no key passage means no rank and no hit", sc["B no repeats"][q1]["first_rank"] is None and not any(sc["B no repeats"][q1]["hits"].values()))
check("an S version is scored on what it showed", sc["S site shown"][q1]["first_rank"] == 1 and sc["S site shown"][q1]["shown"] == 1)
sm = K.summarise(sc, pool)
check("the summary counts hits overall and by everyday and legal", sm["A today"]["top1"] == 1 and sm["A today"]["top3"] == 2 and sm["A today"]["top1_legal"] == 1 and sm["A today"]["top3_everyday"] == 1 and sm["B no repeats"]["top10"] == 0, sm["A today"])
rep = K.report(pool, sc, sm, {"when": "now", "index_commit": "3c80a26abc", "spend": {"rerank_tokens": 5}})
check("the report says it is a key-paragraph match with no reviewer mark and warns against comparing with the live site", "no reviewer mark" in rep and "live site" in rep and "PRIVATE" in rep)
tmp = tempfile.mkdtemp()
pp = os.path.join(tmp, "pool.json")
json.dump({"run": {"when": "now", "index_commit": "x" * 40, "spend": {"rerank_tokens": 1}}, "questions": pool}, open(pp, "w"))
check("main writes the json and the report", K.main(["--pool", pp, "--out", os.path.join(tmp, "o")]) == 0 and os.path.exists(os.path.join(tmp, "o", "KEY_TEST.md")))

print()
print("FAILED: " + ", ".join(FAILS) if FAILS else "all passed")
sys.exit(1 if FAILS else 0)
