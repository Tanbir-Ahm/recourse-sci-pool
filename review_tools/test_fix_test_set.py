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
WB2 = os.path.join(ROOT, "review_data", "ruler", "inputs", "2026-10-12_Fix_Test_New_Questions_N01-N30_round2_as_received.xlsx")
AUTH2 = os.path.join(ROOT, "review_results", "2026-10-12_new_questions_intake", "round2", "authorities_final_proposed.json")
REHEARSAL = os.path.join(ROOT, "review_results", "2026-10-12_fix_test_f_rehearsal", "rehearsal_set.json")
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
# the round-2 file with N12 dropped before sealing (owner, 2026-10-12)
SOFT2 = ["N02", "N04", "N06", "N07", "N13"]
CONFIRMED = "642613ddc8618e1a15e1337f682179184c780de6a5c6d07189b6b41e09de424c"
auth2 = json.load(open(AUTH2, encoding="utf-8"))
pub2, key2 = F.build(WB2, auth2, SOFT2, "3c80a26e42bea75e5858be6ed44a2649ec701355", today="2026-10-12", drop=["N12"], confirmed_hash=CONFIRMED, confirmed_by="owner, 2026-10-12")
Q2, K2 = {q["id"]: q for q in pub2["questions"]}, pub2["questions"]
ids2 = [f"N{i:02d}" for i in range(1, 31) if i != 12]
check("dropped N12: 29 questions N01 to N30 without N12, 26 scored + 3 controls, the drop is recorded", [q["id"] for q in pub2["questions"]] == ids2 and pub2["provenance"]["dropped"] == ["N12"]
      and sum(1 for q in pub2["questions"] if q["domain"] != "K") == 26 and sum(1 for q in pub2["questions"] if q["domain"] == "K") == 3)
check("the dropped question's key row is not in the sealed key", sorted(key2["questions"]) == sorted(ids2) and "N12" not in key2["questions"])
check("the set passes its own check, with and without the key", F.check(pub2) == [] and F.check(pub2, key2) == [], (F.check(pub2), F.check(pub2, key2)))
check("the writer's hash is computed over all 33 rows as received (N12 included) and equals the one the owner confirmed", pub2["provenance"]["writer_text_sha256"] == CONFIRMED and pub2["provenance"]["writer_confirmed_sha256"] == CONFIRMED and pub2["provenance"]["writer_hash_matches"], pub2["provenance"])
check("the old hash still in the declaration is kept as declared, and is not what matches", pub2["provenance"]["writer_declared_sha256"] == "7a6963d1159963f5611c4df2fe4d9840ce7f37423d360e656e3afec83e1c99a3" and pub2["provenance"]["writer_confirmed_by"] == "owner, 2026-10-12")
check("without a confirmed hash the stale declared hash is reported as not matching", not F.build(WB2, auth2, SOFT2, "abc", drop=["N12"])[0]["provenance"]["writer_hash_matches"])
check("soft overlaps are exactly N02, N04, N06, N07, N13", sorted(i for i, q in Q2.items() if q["soft_overlap"]) == SOFT2)
check("replacements read from the round-2 file: N02 has no Act and is a look-alike, N15 is PWDVA and the twin of N17", Q2["N02"]["acts"] == [] and Q2["N02"]["look_alike"] and Q2["N15"]["acts"] == ["PWDVA"] and Q2["N15"]["twin_of"] == "N17")
check("the replacements have a primary authority in the index: D.K. Basu (N02) and Rajnesh v. Neha (N15)", K2 and pub2 and key2["questions"]["N02"]["primary_key_docs"] == [14580] and key2["questions"]["N15"]["primary_key_docs"] == [1000252794], (key2["questions"]["N02"]["primary_key_docs"], key2["questions"]["N15"]["primary_key_docs"]))
check("N19 now has both Yuvaprakash and Rishipal Singh Solanki as primary documents, and the 'note' on an entry does not reach the sealed key", key2["questions"]["N19"]["primary_key_docs"] == [1000253442, 1000255124] and "note" not in json.dumps(key2["questions"]["N15"]["authorities"]))
check("the four measurable currency traps still count as stale (N08, N10, N23, N24)", {i: [s["doc"] for s in key2["questions"][i]["stale_docs"] if s["counts_as_stale"]] for i in ("N08", "N10", "N23", "N24")} == {"N08": [17418], "N10": [30812], "N23": [16680], "N24": [39617]})
check("N15 no longer carries a trap whose older ruling is outside the index", key2["questions"]["N15"]["stale_docs"] == [])
# tampering with the drop is detected
p6 = copy.deepcopy(pub2); p6["provenance"]["dropped"] = []
check("removing the drop record from the public file is detected (the ids no longer fit and the freeze hash differs)", any("ids are not N01 to N30" in b for b in F.check(p6)) and any("changed since the freeze" in b for b in F.check(p6)), F.check(p6))
p7 = copy.deepcopy(pub2); p7["provenance"]["dropped"] = ["N12", "N13"]
check("adding a second drop record to hide a missing question is detected", any("changed since the freeze" in b for b in F.check(p7)) or any("ids are not" in b for b in F.check(p7)), F.check(p7))
p8 = copy.deepcopy(pub2); p8["questions"] = [q for q in p8["questions"] if q["id"] != "N28"]
check("a missing control is detected even though its id could be 'dropped'", any("ids are not" in b for b in F.check(p8)) or any("domain counts" in b for b in F.check(p8)), F.check(p8))
# build refuses unsafe drops
for drop, frag in ((["N28"], "U1"), (["N01", "N02", "N03", "N04", "N05", "N06", "N07"], "23 usable"), (["N99"], "U1")):
    try:
        F.build(WB2, auth2, [], "abc", drop=drop); ok = False
    except ValueError as e:
        ok = frag in str(e)
    check(f"build refuses drop {drop} ({frag})", ok)
try:
    F.build(WB2, json.load(open(AUTH, encoding="utf-8")), [], "abc", drop=["N12"]); ok = False
except ValueError as e:
    ok = "dropped questions ['N12']" in str(e) or "no primary" in str(e)
check("build refuses an authorities table that still names the dropped question (or lacks the replacements)", ok)
try:
    F.build(WB2, auth2, ["N12"], "abc", drop=["N12"]); ok = False
except ValueError as e:
    ok = "soft-overlap" in str(e)
check("build refuses a soft overlap on a dropped question", ok)
try:
    F.build(WB2, auth2, [], "abc"); ok = False
except ValueError as e:
    ok = "N12: no primary authority" in str(e)
check("keeping N12 without authorities for it is refused (nothing is silently dropped or kept)", ok)
# the hand-out of a set with a drop
with tempfile.TemporaryDirectory() as t:
    runs = os.path.join(t, "runs.jsonl")
    got = F.select(pub2, final=True, label="stage F", runs_path=runs, now=datetime.datetime(2026, 11, 1, 9, 0, tzinfo=datetime.timezone.utc))
    check("the hand-out returns the 29 questions (no N12) and logs exactly those ids", [q["id"] for q in got] == ids2 and F.read_runs(runs)[0]["qids"] == ids2)
# a set with nothing dropped keeps the freeze hash it always had
if os.path.exists(REHEARSAL):
    reh = F.load(REHEARSAL)
    check("a set built before the drop option existed still has its freeze hash (nothing dropped changes nothing)", F.freeze_digest(reh) == reh["freeze"]["sha256"] and not (reh.get("provenance") or {}).get("dropped"))
print("\nall passed" if not FAILS else f"\n{len(FAILS)} FAILED: {FAILS}")
sys.exit(1 if FAILS else 0)
