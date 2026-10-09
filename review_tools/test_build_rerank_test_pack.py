"""Tests for review_tools/build_rerank_test_pack.py on an invented pool, invented merged lists and invented passage records (no index, no network, no spend).
Run: python review_tools/test_build_rerank_test_pack.py"""
import copy
import csv
import hashlib
import json
import os
import re
import sys
import tempfile
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_rerank_test_pack as B
import ingest_llm_reviews as ing
import pool_runner as P

FAILS = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{detail}]"))
    if not cond:
        FAILS.append(name)


COMMIT = "c" * 40
N_ARM, M_ARM = P.SAFETY_VERSIONS


def mk_row(qid, n, h, doc, variants, text=None):
    return {"h": h, "doc": doc, "pn": str(n), "page": n, "title": f"Case {doc} v. State", "text": text or f"Paragraph {n} of case {doc} about bail and arrest on the facts, text {h}.", "also": [], "variants": variants, "n": n}


def mk_question(qid, hashes_marked, a10, merged):
    """hashes_marked: the hashes that already have a row (numbered 1..); a10 and merged: lists of hashes."""
    rows = [mk_row(qid, i, h, 100 + i, {"A today": a10.index(h) + 1} if h in a10[:5] else {"S site shown": 3}) for i, h in enumerate(hashes_marked, 1)]
    item = lambda h: {"doc": 100 + int(h[1:]) % 50, "h": h, "also": []}
    return {"qid": qid, "domain": "X", "kind": "legal", "question": f"Is bail available in case {qid}?", "rewrite": None, "half": "dev", "rows": rows,
            "lists": {"A today": [item(h) for h in a10], "E no multiplier": [item(h) for h in a10]}}


def mk_fused(merged, a10):
    return {"fused": [{"pos": i, "h": h, "doc": 100 + int(h[1:]) % 50} for i, h in enumerate(merged, 1)], "A_top10_h": a10, "A_top10_fused_positions": [merged.index(h) + 1 if h in merged else None for h in a10],
            "E_top10_h": a10, "E_top10_fused_positions": [None] * 10}


# question R90: merged top five m1..m5; A's ten a1..a10 with a6..a10 beyond the top five; marked rows: m1 (also a1), a2..a5, a6, and m3
m = [f"m{i}" for i in range(1, 61)]
a_ = [f"a{i}" for i in range(1, 11)]
merged1 = ["m1", "m2", "m3", "a3", "m5"] + [f"m{i}" for i in range(6, 56)]
a10_1 = ["m1", "a2", "a3", "a4", "a5", "a6", "a7", "a8", "a9", "a10"]
marked1 = ["m1", "a2", "a3", "a4", "a5", "a6", "m3"]
q1 = mk_question("R90", marked1, a10_1, merged1)
# question R91: nothing to add except anchors (everything in the merged top five and A's ten is marked)
merged2 = ["b1", "b2", "b3", "b4", "b5"] + [f"x{i}" for i in range(1, 56)]
a10_2 = ["b1", "b2", "b3", "b4", "b5", "b6", "b7", "b8", "b9", "b10"]
q2 = mk_question("R91", a10_2 + [], a10_2, merged2)
for r in q2["rows"]:
    r["variants"].setdefault("A today", 1)
pool = {"run": {"index_commit": COMMIT, "versions": ["A today", "B no repeats", "E no multiplier", "S site shown"], "half": "dev", "spend": {}}, "questions": [q1, q2]}
fused = {"index_commit": COMMIT, "reproduction_problems": [], "spend": {}, "questions": {"R90": mk_fused(merged1, a10_1), "R91": mk_fused(merged2, a10_2)}}


def records_for(q, f):
    out = {}
    for kind in ("core", "extra"):
        for h, doc in B.plan_question(q, f)[kind]:
            out[(h, doc)] = {"h": h, "doc": doc, "pn": "7", "page": 3, "title": f"Case {doc} v. State", "text": f"Passage text of {h} about the offence and the accused person.", "also": []}
    return out


recs = {**records_for(q1, fused["questions"]["R90"]), **records_for(q2, fused["questions"]["R91"])}

# ---- the plan --------------------------------------------------------------------------------------------------------------------------------------
pl = B.plan_question(q1, fused["questions"]["R90"])
check("core = the merged top five that has no row yet", [h for h, _ in pl["core"]] == ["m2", "m5"], pl["core"])
check("extra = A's places 6 to 10 that have no row yet and are not already core", [h for h, _ in pl["extra"]] == ["a7", "a8", "a9", "a10"], pl["extra"])
check("the safety net = the merged top five that A's ten do not show (m3 is already marked but A does not show it), in merged order", pl["net"] == ["m2", "m3", "m5"], pl["net"])
check("two anchors, chosen by a fixed hash from the rows already marked", len(pl["anchors"]) == 2 and {r["h"] for r in pl["anchors"]} <= set(marked1))
q1_other = copy.deepcopy(q1)
for r in q1_other["rows"]:
    r["variants"] = {"E no multiplier": 9}
check("anchors do not depend on the marks or on which version showed a passage", [r["h"] for r in B.pick_anchors(q1["rows"], "R90")] == [r["h"] for r in B.pick_anchors(q1_other["rows"], "R90")])
check("a question with nothing new still gets its anchors", B.plan_question(q2, fused["questions"]["R91"])["core"] == [] and len(B.plan_question(q2, fused["questions"]["R91"])["anchors"]) == 2)

# ---- the build -------------------------------------------------------------------------------------------------------------------------------------
tmp = tempfile.mkdtemp()
pool_p, fused_p = os.path.join(tmp, "pool.json"), os.path.join(tmp, "fused.json")
json.dump(pool, open(pool_p, "w"))
json.dump(fused, open(fused_p, "w"))
before = hashlib.sha256(open(pool_p, "rb").read()).hexdigest()
out = os.path.join(tmp, "out")
info = B.build(pool_p, fused_p, out, records=recs)
check("the original pool file is untouched", hashlib.sha256(open(pool_p, "rb").read()).hexdigest() == before)
check("one prompt file per question with new passages, two chats each", info["prompt_files"] == 2 and info["chats"] == 4, info)
ext = json.load(open(os.path.join(out, "pool_with_rerank_arms.json")))
eq1 = next(q for q in ext["questions"] if q["qid"] == "R90")
new1 = [r for r in eq1["rows"] if r.get("topup")]
check("R90: 2 core + 4 extra + 2 anchors = 8 new rows; the 7 old rows are kept as they were (same numbers, same text)", len(new1) == 8 and len(eq1["rows"]) == 15 and [r["n"] for r in eq1["rows"][:7]] == list(range(1, 8)) and
      [r["text"] for r in eq1["rows"][:7]] == [r["text"] for r in q1["rows"]], (len(new1), len(eq1["rows"])))
check("new numbers continue after the old ones, each once", sorted(r["n"] for r in new1) == list(range(8, 16)))
check("the new rows are not in number order of kind: the shuffle hides which are core, extra or anchors", [r["kind"] for r in sorted(new1, key=lambda r: r["n"])] != ["core"] * 2 + ["extra"] * 4 + ["anchor"] * 2)
anch = [r for r in new1 if r["kind"] == "anchor"]
check("anchors repeat an old passage's text under a new number, point at the old number and belong to no version", all(r["variants"] == {} and r["text"] == next(o for o in eq1["rows"] if o["n"] == r["anchor_of"])["text"] for r in anch))
check("the merged-order arm N marks the merged top ten wherever those rows are, with their merged position", {r["h"]: r["variants"][N_ARM] for r in eq1["rows"] if N_ARM in r["variants"] and not r.get("anchor_of")} ==
      {h: i for i, h in enumerate(merged1[:10], 1) if h in {r["h"] for r in eq1["rows"]}})
check("the safety-net arm M is exactly the merged top five that A's ten do not show", {r["h"] for r in eq1["rows"] if M_ARM in r["variants"]} == {"m2", "m3", "m5"})
check("the lists for the scorer carry both arms", [it["h"] for it in eq1["lists"][M_ARM]] == ["m2", "m3", "m5"] and len(eq1["lists"][N_ARM]) == 10)
check("the run record lists the new arms and says what was added", set(P.SAFETY_VERSIONS) <= set(ext["run"]["versions"]) and ext["run"]["extended_by"]["anchors_per_question"] == 2)

# ---- the prompts ------------------------------------------------------------------------------------------------------------------------------------
folder = os.path.join(out, "Second_Batch_Pack")
prompts = sorted(os.listdir(os.path.join(folder, "prompts")))
check("prompt files are named like R90_TA.txt and there is no reversed file", prompts == ["R90_TA.txt", "R91_TA.txt"], prompts)
txt = open(os.path.join(folder, "prompts", "R90_TA.txt"), encoding="utf-8").read()
nums_in = sorted(int(x) for x in re.findall(r"--- PASSAGE (\d+) ---", txt))
check("the prompt holds exactly the new passages, numbered on from the first batch", nums_in == list(range(8, 16)) and "Passage numbers to cover: 8, 9, 10, 11, 12, 13, 14, 15" in txt, nums_in)
check("the prompt names the question and the batch, and the closing line is the usual one", "QUESTION ID: R90" in txt and "top-up batch" in txt and "END OF PASSAGES. Now reply with the single JSON object for R90" in txt)
leaks = ["merged", "re-rank", "rerank", "safety", "A today", "variant", "N merged", "M safety", "anchor", "core", "extra", "sealed", "tuning", "key", "fused", "half", "half:", "version "]
found = [w for w in leaks if re.search(r"\b" + re.escape(w), re.sub(r"(?s)RULES.*?REQUIRED JSON SHAPE", "", txt), re.I)]
check("nothing about the search, the versions, the arms, the key or the half in a prompt", not found, found)
check("an old passage's number does not appear as a passage in the prompt", not any(f"--- PASSAGE {n} ---" in txt for n in range(1, 8)))
readme = open(os.path.join(folder, "README.txt"), encoding="utf-8").read()
check("the README names the file pattern, both tools, the checks on saved files and the number of chats", "R90_TA_ChatGPT.txt" in readme and "R90_TA_Gemini.txt" in readme and "4 chats in all" in readme and "not the prompt you pasted" in readme and "not one saved twice" in readme)
man = list(csv.reader(open(os.path.join(folder, "manifest.csv"), encoding="utf-8")))
check("the manifest has a row per file per tool, in the usual columns", man[0][:3] == ["prompt file", "question", "batch"] and len(man) == 5 and {r[5] for r in man[1:]} == {"R90_TA_ChatGPT.txt", "R90_TA_Gemini.txt", "R91_TA_ChatGPT.txt", "R91_TA_Gemini.txt"})
with zipfile.ZipFile(os.path.join(out, "Second_Batch_Pack.zip")) as z:
    names = z.namelist()
check("the zip holds the prompts, the README, the manifest and an empty replies folder, under one top folder", all(n.startswith("Second_Batch_Pack/") for n in names) and "Second_Batch_Pack/README.txt" in names and "Second_Batch_Pack/prompts/R90_TA.txt" in names)
check("the extended pool, which names the arms, is not inside the pack, and nothing in the pack says what it is for", not any("pool_with_rerank_arms" in n for n in names) and not re.search(r"re-?rank|safety|merged", readme + "".join(names), re.I), names[:3])

# ---- the replies come back: the ingest tool reads them against the extended pool ------------------------------------------------------------------
rep_dir = os.path.join(tmp, "replies")
os.makedirs(rep_dir)
def reply(q, marks):
    return json.dumps({"question_id": q["qid"], "marks": [{"no": r["n"], "mark": marks[i % len(marks)], "evidence": r["text"][:20], "reason": "x", "confidence": "high"} for i, r in enumerate(sorted([r for r in q["rows"] if r.get("topup")], key=lambda r: r["n"]))],
                       "good_answer_present": "Yes", "best_passage_no": None, "caveats": ""})
open(os.path.join(rep_dir, "R90_TA_ChatGPT.txt"), "w").write(reply(eq1, ["Yes", "Partly"]))
open(os.path.join(rep_dir, "R90_TA_Gemini.txt"), "w").write(reply(eq1, ["Partly", "No"]))
pool_l, passages = ing.load_pool(os.path.join(out, "pool_with_rerank_arms.json"))
runs, problems, ev = ing.load_replies(rep_dir, passages, pool_l)
check("the top-up replies are read against the extended pool without a problem, as TA runs", not problems and set(runs) == {("ChatGPT", "TA"), ("Gemini", "TA")} and len(runs[("ChatGPT", "TA")]) == 8, (problems, sorted(runs)))
cons, pair, var_rows = ing.analyse(runs, passages, pool_l)
names_scored = {r["variant"] for r in var_rows}
check("the two new arms are scored by the usual tool (N by its top five, M as a set)", {N_ARM, M_ARM} <= names_scored, sorted(names_scored))

# ---- guards -----------------------------------------------------------------------------------------------------------------------------------------
bad_f = dict(fused, index_commit="d" * 40)
json.dump(bad_f, open(os.path.join(tmp, "bad.json"), "w"))
try:
    B.build(pool_p, os.path.join(tmp, "bad.json"), os.path.join(tmp, "o2"), records=recs)
    raised = None
except SystemExit as e:
    raised = str(e)
check("refused: merged lists made on another index than the pool", raised and "index" in raised, raised)
bad_f2 = dict(fused, reproduction_problems=[["R90", 2]])
json.dump(bad_f2, open(os.path.join(tmp, "bad2.json"), "w"))
try:
    B.build(pool_p, os.path.join(tmp, "bad2.json"), os.path.join(tmp, "o3"), records=recs)
    raised = None
except SystemExit as e:
    raised = str(e)
check("refused: merged lists that do not reproduce the pool", raised and "reproduce" in raised, raised)
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "build_rerank_test_pack.py"), encoding="utf-8").read()
check("the builder never reads the private key", "real30_key" not in src.replace("the key", "") and "real30_score" not in src)

print()
print("FAILED: " + ", ".join(FAILS) if FAILS else "all passed")
sys.exit(1 if FAILS else 0)
