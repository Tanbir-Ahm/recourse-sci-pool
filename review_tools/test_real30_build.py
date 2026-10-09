"""Tests for the 30-question builder (review_tools/real30_build.py): the importer reads the owner's workbook to the plan's counts, the link table and the stale-ruling table are consistent,
the built files hold what they should and nothing more, and the committed files are what the builder produces. Run: python review_tools/test_real30_build.py"""
import collections
import copy
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import real30_build as B
import real_questions as RQ

FAILS = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{detail}]"))
    if not cond:
        FAILS.append(name)


# ---- the importer, on the owner's workbook ------------------------------------------------------------------------------------------------------
rows, owner_key = B.read_workbook()
count = lambda f: collections.Counter(f(r) for r in rows)
check("30 questions are read, Q1 to Q30 in order", [r["owner_q"] for r in rows] == [f"Q{i}" for i in range(1, 31)])
check("domains follow the plan (3,3,3,2,3,3,3,3,2,2,3)", [count(lambda r: r["domain"])[d] for d in RQ.DOMAINS] == [3, 3, 3, 2, 3, 3, 3, 3, 2, 2, 3])
check("phrasing: 10 everyday, 11 legal, 9 narrative", dict(count(lambda r: r["kind"])) == {"everyday": 10, "legal": 11, "narrative": 9}, count(lambda r: r["kind"]))
check("section numbers: 9 BNS/BNSS, 7 IPC/CrPC, 14 none", dict(count(lambda r: r["numbering"])) == {"BNS/BNSS": 9, "IPC/CrPC": 7, "none": 14}, count(lambda r: r["numbering"]))
check("13 traps and 24 questions whose best law is from 2017 or later", count(lambda r: r["trap"])["yes"] == 13 and count(lambda r: r["best_law_era"])["2017 or later"] == 24)
check("the controls are a divorce question, a cut-off trap and a statute-table question", [r["control_type"] for r in rows if r["domain"] == "K"] == ["civil/tax/divorce", RQ.CUTOFF_TRAP, "statute table answers it"])
check("no question text keeps the owner's quotation marks", all(not r["question"].startswith('"') and not r["question"].endswith('"') for r in rows))
check("the intake passes the validator with no problems and no warnings", RQ.validate(rows) == ([], []), RQ.validate(rows))
check("the key holds an expected answer, an authority and sources for every question", all(k["expected_answer"] and k["key_authority_text"] and k["source_urls"] for k in owner_key.values()))
check("the trap pairs of the Currency Traps sheet are attached to their questions (13)", sum(1 for k in owner_key.values() if k["trap_pair"]) == 13)
check("the To Verify items are attached to their questions", owner_key["Q15"]["to_verify"] and owner_key["Q5"]["to_verify"] and not owner_key["Q3"]["to_verify"])

# ---- the link table and the stale table ------------------------------------------------------------------------------------------------------------------
links = B.read_links()
sides, _ = RQ.ruler_sides(os.path.join(B.DATA, "ruler_v2.json"))
check("every link names a question of the set and a ruler topic", all(l["id"] in {f"R{i:02d}" for i in range(1, 31)} and l["topic"] in sides and l["basis"] in ("shared case", "doctrine group") and l["note"] for l in links))
try:
    forced = RQ.forced_sides(links, sides)
    ok = True
except ValueError:
    forced, ok = {}, False
check("no question is linked to topics on both sides of the seal", ok)
check("the links force Q10 and Q16 and Q5 to sealed and Q1, Q2, Q11, Q12, Q14, Q15, Q24 to dev", forced == {"R01": "dev", "R02": "dev", "R05": "sealed", "R10": "sealed", "R11": "dev", "R12": "dev", "R14": "dev", "R15": "dev", "R16": "sealed", "R24": "dev"}, forced)
coverage = json.load(open(B.COVERAGE, encoding="utf-8"))
stale = json.load(open(B.STALE, encoding="utf-8"))["rulings"]
labels = {c["label"] for c in coverage if c["role"] == "stale"}
check("the stale table has an entry for each of the 16 older rulings and no other", labels == set(stale) and len(labels) == 16, (labels ^ set(stale)))
check("every older ruling is in the index, as the review found", all(c["where"] == "in_index" for c in coverage if c["role"] == "stale"))
check("every stale entry says what happened, where that comes from, and whether it counts", all(v["kind"] and v["basis"] and v["source"] and isinstance(v["counts_as_stale"], bool) for v in stale.values()))
check("an entry that counts as stale names its expected treatment", all(v.get("expect") in ("adverse", "adverse_in_part") for v in stale.values() if v["counts_as_stale"]))

# ---- the built files ---------------------------------------------------------------------------------------------------------------------------------
real = RQ.load(B.OUT_Q)
key = json.load(open(B.OUT_KEY, encoding="utf-8"))
check("the committed question file passes its own check, with the ruler cross-check", RQ.check(real, os.path.join(B.DATA, "ruler_v2.json")) == [], RQ.check(real, os.path.join(B.DATA, "ruler_v2.json")))
check("the builder's check passes (key matches, owner's workbook unchanged)", B.check(ruler_path=os.path.join(B.DATA, "ruler_v2.json")) == [], B.check(ruler_path=os.path.join(B.DATA, "ruler_v2.json")))
check("the seal is the 11 questions the link-first rule gives", real["freeze"]["questions"] == ["R03", "R05", "R07", "R10", "R13", "R16", "R18", "R23", "R25", "R27", "R30"], real["freeze"]["questions"])
check("every domain has at least ceil(n/3) sealed", all(sum(1 for q in real["questions"] if q["domain"] == d and q["half"] == "sealed") >= -(-sum(1 for q in real["questions"] if q["domain"] == d) // 3) for d in RQ.DOMAINS))
check("the three questions the index cannot answer are all on the tuning side", all(q["half"] == "dev" for q in real["questions"] if q["id"] in ("R06", "R15", "R21")))
check("the question file records the index head, the owner's file hash and the provenance label", len(real["index_snapshot"]["commit"]) == 40 and real["provenance"]["source_sha256"] == B.sha256_file(B.SOURCE) and "not client messages" in real["provenance"]["label"])
blob = json.dumps(real, ensure_ascii=False)
secret = [k["expected_answer"][:60] for k in key["questions"].values()] + [k["key_authority_text"][:60] for k in key["questions"].values()]
check("no expected answer and no authority text appears in the question file", not any(s in blob for s in secret))
check("the question file holds no case names of the older or newer rulings (no trap notes)", all("trap_note" not in q for q in real["questions"]) and "authorities" not in blob)
unreach = sorted(i for i, k in key["questions"].items() if k["reachable"] is False)
check("the key marks Q6, Q15 and Q21 as unreachable and the controls as not applicable", unreach == ["R06", "R15", "R21"] and all(key["questions"][i]["reachable"] is None for i in ("R28", "R29", "R30")), unreach)
check("the key lists the 16 older rulings across 12 questions (the 13th trap, Q18, is a High Court ruling outside the index)", sum(len(k["stale_docs"]) for k in key["questions"].values()) == 16 and sum(1 for k in key["questions"].values() if k["stale_docs"]) == 12)
check("a key authority's documents are index ids from the index files, never corpus keys", all(isinstance(d, int) for k in key["questions"].values() for d in k["key_docs"]))
check("a stale ruling that does not count (narrower, contested) is kept in the key but flagged", [s["kind"] for s in key["questions"]["R01"]["stale_docs"]] == ["narrower"] * 3 and not any(s["counts_as_stale"] for s in key["questions"]["R01"]["stale_docs"]))

# ---- the blind rewrites -------------------------------------------------------------------------------------------------------------------------------
import hashlib
import re
rw = json.load(open(os.path.join(B.DATA, "real30_rewrites_v1.json"), encoding="utf-8"))
dev_plain = [q for q in real["questions"] if q["half"] == "dev" and q["kind"] != "legal"]
check("the rewrites cover exactly the tuning-half questions that are not in legal wording, and no sealed question", sorted(rw["rewrites"]) == sorted(q["id"] for q in dev_plain) and len(dev_plain) == 12 and not any(q["half"] == "sealed" and q["id"] in rw["rewrites"] for q in real["questions"]))
body = "\n\n".join(f'{q["id"]}: {q["text"]}' for q in dev_plain)
check("the rewrites were made from the questions as built (input hash) with the saved prompt (prompt hash)", rw["input_sha256"] == hashlib.sha256(body.encode()).hexdigest() and rw["prompt_sha256"] == hashlib.sha256(open(os.path.join(B.DATA, "rewrite_prompt_v1.txt"), "rb").read()).hexdigest())
check("no rewrite names a case or runs over the prompt's 60 words, and they were saved unedited", all(len(v.split()) <= 60 and not re.search(r"\bv\.|\bversus\b|\bvs\b", v) for v in rw["rewrites"].values()) and rw["unedited"] is True)
check("the question file does not contain the rewrites", not any(v[:40] in json.dumps(real, ensure_ascii=False) for v in rw["rewrites"].values()))

# ---- reproducibility and refusals --------------------------------------------------------------------------------------------------------------------
fresh, fkey, _, _ = B.build(index_dir=B.DEFAULT_INDEX, today=real["built"])
a, b = copy.deepcopy(fresh), copy.deepcopy(real)
for d in (a, b):
    d.pop("index_snapshot")
check("a fresh build from the committed inputs gives the committed question file (apart from the index head)", a == b)
check("and the committed key", {k: v for k, v in fkey.items() if k != "built"} == {k: v for k, v in key.items() if k != "built"})
check("a second build is refused without --force", B.main(["build"]) == 2)

print()
print("FAILED: " + ", ".join(FAILS) if FAILS else "all passed")
sys.exit(1 if FAILS else 0)
