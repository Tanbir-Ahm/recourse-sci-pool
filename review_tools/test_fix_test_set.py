"""Tests for review_tools/fix_test_set.py on the writer's workbook as received (2026-10-12) and the authorities table made from the index check. Nothing is sealed here: every output goes to a temporary folder.
Run: python review_tools/test_fix_test_set.py"""
import copy
import datetime
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fix_test_set as F

ROOT = F.ROOT
WB = os.path.join(ROOT, "review_data", "ruler", "inputs", "2026-10-12_Fix_Test_New_Questions_N01-N30_as_received.xlsx")
AUTH = os.path.join(ROOT, "review_results", "2026-10-12_new_questions_intake", "authorities_as_received.json")
FAILS = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{detail}]"))
    if not cond:
        FAILS.append(name)


public, key = F.build(WB, json.load(open(AUTH, encoding="utf-8")), ["N04", "N06", "N07", "N13"], "3c80a26e42bea75e5858be6ed44a2649ec701355", today="2026-10-12")
Q = {q["id"]: q for q in public["questions"]}
K = key["questions"]
check("30 questions, ids N01 to N30, reserves not included", [q["id"] for q in public["questions"]] == [f"N{i:02d}" for i in range(1, 31)] and public["provenance"]["unused_reserves"] == ["NR1", "NR2", "NR3"])
check("a built set passes its own check, with and without the key", F.check(public) == [] and F.check(public, key) == [], (F.check(public), F.check(public, key)))
check("the writer's own freeze hash is reproduced from the workbook and matches the declared one", public["provenance"]["writer_hash_matches"] and public["provenance"]["writer_text_sha256"] == "7a6963d1159963f5611c4df2fe4d9840ce7f37423d360e656e3afec83e1c99a3", public["provenance"])
check("the public file holds no key fields and no neighbour regime", all(k not in q for q in public["questions"] for k in F.KEY_FIELDS_IN_PUBLIC + ("neighbour",)))
check("tags read from the workbook: N11 is Hinglish, N13 is a look-alike twin of N07 with a soft overlap, N29 is control K2, N16 carries two Acts", Q["N11"]["language"] == "Hinglish" and Q["N13"]["look_alike"] and Q["N13"]["twin_of"] == "N07" and Q["N13"]["soft_overlap"] and Q["N29"]["control_type"] == "K2" and Q["N16"]["acts"] == ["DPA", "PWDVA"], (Q["N16"]["acts"]))
check("soft overlaps are exactly N04, N06, N07, N13", sorted(i for i, q in Q.items() if q["soft_overlap"]) == ["N04", "N06", "N07", "N13"])
check("controls are answerable: None; every scored question has a key authority in the index", all(K[i]["reachable"] is None for i in ("N28", "N29", "N30")) and all(K[f"N{i:02d}"]["reachable"] is True for i in range(1, 28)))
check("N01, N05 and N15 have no PRIMARY authority in the index but do have key documents", all(not K[i]["primary_key_docs"] and K[i]["key_docs"] for i in ("N01", "N05", "N15")), {i: (K[i]["primary_key_docs"], K[i]["key_docs"]) for i in ("N01", "N05", "N15")})
check("stale documents that count: Tapadia (N08), E. Micheal Raj (N10), Paparambaka (N23), Manharibhai (N24); the others are narrower", {i: [s["doc"] for s in K[i]["stale_docs"] if s["counts_as_stale"]] for i in ("N08", "N10", "N23", "N24")} == {"N08": [17418], "N10": [30812], "N23": [16680], "N24": [39617]}
      and not any(s["counts_as_stale"] for i in ("N16", "N17", "N25", "N27") for s in K[i]["stale_docs"]))
check("N15's older ruling is not in the index, so it contributes no stale document", K["N15"]["stale_docs"] == [] and K["N26"]["stale_docs"] == [])
check("the key keeps the writer's expected answer and the neighbour regime", K["N02"]["expected_answer"].startswith("No, not if") and "Ordinary search" in K["N02"]["neighbour_regime"])
# tampering is detected
p2 = copy.deepcopy(public); p2["questions"][3]["text"] += " x"
check("a changed question text is detected", any("changed since the freeze" in b for b in F.check(p2)))
p3 = copy.deepcopy(public); p3["questions"][3]["acts"] = ["NDPS"]
check("a changed tag is detected too", any("changed since the freeze" in b for b in F.check(p3)))
k2 = copy.deepcopy(key); k2["questions"]["N03"]["key_docs"] = [1]
check("a changed key is detected", any("key has changed" in b for b in F.check(public, k2)))
p4 = copy.deepcopy(public); p4["questions"][0]["primary_authority"] = "x"
check("a key field in the public file is detected", any("key fields" in b for b in F.check(p4)))
p5 = copy.deepcopy(public); p5["questions"][5]["domain"] = "A"
check("a changed domain count is detected", any("domain counts" in b for b in F.check(p5)))
# the hand-out guard
with tempfile.TemporaryDirectory() as t:
    runs = os.path.join(t, "runs.jsonl")
    for kw, frag in ((dict(final=False, label="x"), "final=True"), (dict(final=True, label=" "), "label")):
        try:
            F.select(public, runs_path=runs, **kw); ok = False
        except F.SealedError as e:
            ok = frag in str(e)
        check(f"select refuses without {frag}", ok)
    try:
        F.select(p2, final=True, label="x", runs_path=runs); ok = False
    except F.SealedError as e:
        ok = "changed since the freeze" in str(e)
    check("select refuses questions that have changed since the freeze", ok and not os.path.exists(runs))
    now = datetime.datetime(2026, 11, 1, 9, 0, tzinfo=datetime.timezone.utc)
    got = F.select(public, final=True, label="stage F", runs_path=runs, now=now)
    log = F.read_runs(runs)
    check("the first hand-out returns 30 questions marked final and logs it with both hashes", len(got) == 30 and all(q["half"] == "final" for q in got) and len(log) == 1 and log[0]["ts"] == "2026-11-01T09:00:00Z" and log[0]["freeze_sha256"] == public["freeze"]["sha256"] and log[0]["key_sha256"] == public["freeze"]["key_sha256"] and not log[0]["repeat"])
    try:
        F.select(public, final=True, label="again", runs_path=runs); ok = False
    except F.SealedError as e:
        ok = "already handed out" in str(e)
    check("a second hand-out is refused", ok and len(F.read_runs(runs)) == 1)
    F.select(public, final=True, label="repeat on purpose", runs_path=runs, allow_repeat=True)
    check("allow_repeat works and the repeat is logged as a repeat", len(F.read_runs(runs)) == 2 and F.read_runs(runs)[1]["repeat"])
# build refuses a bad table
bad = json.load(open(AUTH, encoding="utf-8")); bad = [a for a in bad if not (a["qid"] == "N03" and a["role"] == "primary")]
try:
    F.build(WB, bad, [], "abc"); ok = False
except ValueError as e:
    ok = "N03: no primary authority" in str(e)
check("build refuses a table with no primary authority for a scored question", ok)
try:
    F.build(WB, json.load(open(AUTH, encoding="utf-8")), ["N99"], "abc"); ok = False
except ValueError as e:
    ok = "soft-overlap" in str(e)
check("build refuses a soft-overlap id that is not in the set", ok)
print("\nall passed" if not FAILS else f"\n{len(FAILS)} FAILED: {FAILS}")
sys.exit(1 if FAILS else 0)
