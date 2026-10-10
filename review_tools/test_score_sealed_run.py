"""Tests for review_tools/score_sealed_run.py on an invented pool, invented replies and an invented key (no network, no spend). Run: python review_tools/test_score_sealed_run.py"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import score_sealed_run as S

FAILS = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{detail}]"))
    if not cond:
        FAILS.append(name)


A, R, SS, NA, NR = S.NAMES["a"], S.NAMES["r"], S.NAMES["s"], S.NAMES["na"], S.NAMES["nr"]
DOMAINS = {"R03": "A", "R05": "B", "R07": "C", "R10": "D", "R13": "E", "R16": "F"}
tmp = tempfile.mkdtemp()


def mk_pool(r_better=True):
    """Six questions, ten rows each: rows 1-5 are A's top 5, rows 4-8 are R's top 5 (so 3 and 6-8 differ), row 9 is in the net of A, row 10 in the site's list."""
    qs = []
    for qid, dom in DOMAINS.items():
        rows = []
        for n in range(1, 11):
            v = {}
            if n <= 5:
                v[A] = n
            if 4 <= n <= 8:
                v[R] = n - 3
            if n == 9:
                v[NA] = 1
                v[NR] = 1
            if n == 10:
                v[SS] = 1
            rows.append({"n": n, "h": f"{qid}h{n}", "doc": 1000 + n, "pn": str(n), "page": n, "title": f"Case {n} v. State", "text": f"{n}. Passage {n} of {qid}.", "also": [], "variants": v})
        lists = {A: [{"doc": 1000 + n, "h": f"{qid}h{n}", "also": []} for n in range(1, 11)], R: [{"doc": 1000 + n, "h": f"{qid}h{n}", "also": []} for n in range(4, 14)], SS: [{"doc": 1010, "h": f"{qid}h10", "also": []}]}
        qs.append({"qid": qid, "domain": dom, "kind": "legal", "question": f"Question {qid}?", "rows": rows, "lists": lists})
    return qs


def write_pool(qs, final=True):
    p = os.path.join(tmp, "pool.json")
    json.dump({"run": {"half": "sealed", "final_recipe": {"rules_sha256": "f" * 64, "code_uncommitted": []}} if final else {"half": "dev"}, "questions": qs}, open(p, "w"))
    return p


def write_replies(qs, marks_by_row, gemini_same=True, skip=None):
    d = tempfile.mkdtemp(dir=tmp)
    for q in qs:
        for tool in ("ChatGPT", "Gemini"):
            if skip and (q["qid"], tool) == skip:
                continue
            ms = []
            for r in q["rows"]:
                m = marks_by_row[r["n"]]
                if tool == "Gemini" and not gemini_same:
                    m = {"Yes": "Partly", "Partly": "No", "No": "No", "Misleading": "Misleading"}[m]
                ms.append({"no": r["n"], "mark": m, "evidence": r["text"][:20], "reason": "x", "confidence": "high"})
            open(os.path.join(d, f"{q['qid']}_A_{tool}.txt"), "w").write(json.dumps({"question_id": q["qid"], "marks": ms, "good_answer_present": "Yes", "best_passage_no": None, "caveats": ""}))
    return d


def write_key(qs, stale_row=None, stale_qids=("R03", "R05"), answerable=True, key_row=5):
    p = os.path.join(tmp, "key.json")
    kq = {}
    for q in qs:
        stale = [{"doc": 1000 + stale_row, "label": "old ruling", "kind": "overruled", "counts_as_stale": True}] if stale_row and q["qid"] in stale_qids else []
        kq[q["qid"]] = {"reachable": answerable, "key_docs": [1000 + key_row], "stale_docs": stale}
    kq["R99"] = {"reachable": True, "key_docs": [1], "stale_docs": []}                 # an entry of a question that is not in the pool: must never be used
    json.dump({"questions": kq}, open(p, "w"))
    return p


# marks: A's passages 1-3 are good; 4-5 mediocre; R's new ones 6-8 good (the challenger wins) or bad
good = {1: "Yes", 2: "Yes", 3: "Partly", 4: "Partly", 5: "Partly", 6: "Yes", 7: "Yes", 8: "Partly", 9: "Partly", 10: "No"}
bad = {**good, 6: "No", 7: "Misleading", 8: "No"}
qs = mk_pool()
pool_p = write_pool(qs)
rep_good = write_replies(qs, good)
out = os.path.join(tmp, "o1")
s1 = S.stage_marks(pool_p, rep_good, out, S.NAMES)
check("stage 1: coverage complete, tools agree fully, reliability ok", s1["coverage_complete"] and s1["tool_agreement_exact"] == 1.0 and s1["reliability"] == "ok")
check("stage 1 numbers: arm A top 5 = Yes 40%, useful 100%, Misleading 0% (rows 1-5)", abs(s1["settlements"]["ChatGPT alone"][A]["yes"] - 0.4) < 1e-9 and s1["settlements"]["ChatGPT alone"][A]["useful"] == 1.0 and s1["settlements"]["ChatGPT alone"][A]["mis"] == 0)
check("stage 1 numbers: arm R top 5 = rows 4-8 = Yes 40%, useful 100%", abs(s1["settlements"]["ChatGPT alone"][R]["yes"] - 0.4) < 1e-9 and s1["settlements"]["ChatGPT alone"][R]["useful"] == 1.0)
check("the net and the site are scored as whole sets", s1["settlements"]["ChatGPT alone"][NA]["questions"] == 6 and s1["nets"]["na"]["passages"] == 6)
check("floors on both arms are computed, F1 and F4 hold, F2 holds", s1["floors"]["A"]["F1"] and s1["floors"]["A"]["F2"] and s1["floors"]["A"]["F4"])
# R equal to A on the marks (grade 2.4 against 2.4): rule 1 holds (not lower) but rule 3 needs two more questions better -> the status quo
check("a challenger that is only level does not win rule 3 (two more questions better are needed)", s1["marks_rules"]["rule1_grade_all_four_settlements"] and not s1["marks_rules"]["rule3_two_more_questions_better"] and not s1["marks_rules"]["marks_rules_hold"], s1["marks_rules"])
# a better challenger: R's rows 6-8 all Yes, A's rows 4-5 weak
better = {**good, 1: "No", 2: "No", 3: "No", 6: "Yes", 7: "Yes", 8: "Yes"}              # A alone holds rows 1-3, R alone rows 6-8
rep_b = write_replies(qs, better)
s1b = S.stage_marks(pool_p, rep_b, os.path.join(tmp, "o2"), S.NAMES)
check("a clearly better challenger passes rules 1, 2, 3 and 5 on the marks", s1b["marks_rules"]["marks_rules_hold"], s1b["marks_rules"])
rep_w = write_replies(qs, bad)
s1w = S.stage_marks(pool_p, rep_w, os.path.join(tmp, "o3"), S.NAMES)
check("a worse challenger fails rule 1 or 2", not s1w["marks_rules"]["marks_rules_hold"] and (not s1w["marks_rules"]["rule1_grade_all_four_settlements"] or not s1w["marks_rules"]["rule2_misleading_and_useful_margins"]))
# incomplete and weak
rep_inc = write_replies(qs, good, skip=("R07", "Gemini"))
s1i = S.stage_marks(pool_p, rep_inc, os.path.join(tmp, "o4"), S.NAMES)
check("a missing reply file makes the result INCOMPLETE: coverage false, ten passages short", not s1i["coverage_complete"] and s1i["passages_not_marked_by_both_tools"] == 10, s1i["passages_not_marked_by_both_tools"])
rep_weak = write_replies(qs, good, gemini_same=False)
s1k = S.stage_marks(pool_p, rep_weak, os.path.join(tmp, "o5"), S.NAMES)
check("tools that agree on under 60% are flagged weak", s1k["reliability"] == "weak" and s1k["tool_agreement_exact"] < 0.6, s1k["tool_agreement_exact"])

# stage 2 ---------------------------------------------------------------------------------------------------------------------------------------------------
S.frozen_rules_hash = lambda *a, **k: "f" * 64
key_p = write_key(qs)                                    # the named authority is doc 1005: place 5 in A, place 2 in R; no stale ruling
try:
    S.stage_key(pool_p, rep_good, os.path.join(tmp, "never_run"), key_p, S.NAMES, "sealed")
    refused = None
except SystemExit as e:
    refused = str(e)
check("the key is refused before stage 1 has run", refused and "stage 1" in refused, refused)
s2 = S.stage_key(pool_p, rep_b, os.path.join(tmp, "o2"), key_p, S.NAMES, "sealed")
check("stage 2: the better challenger wins when the named authority and the stale count are not worse", s2["R_replaces_A"] and s2["chosen_arm"] == R and s2["rule4_authority_and_stale_not_worse"], (s2["chosen_arm"], s2["named_authority"]))
check("stage 2: six answerable questions, the named authority is in both arms' top 5", s2["named_authority"][A]["top5"] == 6 and s2["named_authority"][R]["top5"] == 6 and len(s2["answerable"]) == 6)
check("stage 2: only the pool's questions are read out of the key (R99 never appears)", "R99" not in json.dumps(s2) and json.load(open(os.path.join(tmp, "o2", "key_opened.json")))["questions_read"] == sorted(DOMAINS))
check("stage 2: floors hold on the chosen arm and each is labelled clear or weak", s2["floors_met"] and set(s2["floors_chosen_arm"]["clear_or_weak"]) == {"F1", "F2", "F3", "F4"} and s2["floors_chosen_arm"]["F3_named_authority_top10"] == 1.0)
check("stage 2: a domain is eligible when the floors hold, relevance is not red, currency is not red and its own sealed question is not red", all(d["eligible"] for d in s2["domains"].values()) and len(s2["domains"]) == 6 and "eligible" in s2["outcome"], s2["outcome"])
check("stage 2 writes the report in plain words and the key-opened record", os.path.exists(os.path.join(tmp, "o2", "SEALED_RUN_REPORT.md")) and "Never to be written as 'X% accurate'" in open(os.path.join(tmp, "o2", "SEALED_RUN_REPORT.md")).read())
# rule 4: the challenger brings a stale ruling into the top 5 that A does not have
key_stale = write_key(qs, stale_row=7, stale_qids=("R03", "R05"))
s2s = S.stage_key(pool_p, rep_b, os.path.join(tmp, "o2"), key_stale, S.NAMES, "sealed")
check("rule 4: more known-stale passages in R's top 5 than in A's keeps the status quo although the marks favour R", not s2s["R_replaces_A"] and s2s["chosen_arm"] == A and s2s["stale_in_top5"][R] == 2 and s2s["stale_in_top5"][A] == 0, s2s["stale_in_top5"])
check("currency light: two trap questions of six domains, one let through each in R, none in A (A chosen): green", s2s["currency_overall"]["light"] == "green", s2s["currency_overall"])
# currency red: a stale ruling in A's top 5 for every question
key_red = write_key(qs, stale_row=2, stale_qids=tuple(DOMAINS))
s2r = S.stage_key(pool_p, rep_good, os.path.join(tmp, "o1"), key_red, S.NAMES, "sealed")
check("currency red everywhere: floors can hold and still no domain is eligible", s2r["floors_met"] and not any(d["eligible"] for d in s2r["domains"].values()) and "no domain eligible" in s2r["outcome"], s2r["outcome"])
# a missed floor: every passage poor
poor = {n: "No" for n in range(1, 11)}
rep_p = write_replies(qs, poor)
S.stage_marks(pool_p, rep_p, os.path.join(tmp, "o6"), S.NAMES)
s2p = S.stage_key(pool_p, rep_p, os.path.join(tmp, "o6"), key_p, S.NAMES, "sealed")
check("a missed floor is reported as such: nothing connected, new questions needed", not s2p["floors_met"] and "floor is missed" in s2p["outcome"], s2p["outcome"])
# integrity refusals
open(os.path.join(rep_b, "R03_A_ChatGPT.txt"), "a").write(" ")
try:
    S.stage_key(pool_p, rep_b, os.path.join(tmp, "o2"), key_p, S.NAMES, "sealed")
    ref2 = None
except SystemExit as e:
    ref2 = str(e)
check("stage 2 refuses when a reply file changed after stage 1", ref2 and "changed since stage 1" in ref2, ref2)
try:
    S.stage_key(pool_p, rep_inc, os.path.join(tmp, "o4"), key_p, S.NAMES, "sealed")
    ref3 = None
except SystemExit as e:
    ref3 = str(e)
check("stage 2 refuses an incomplete round", ref3 and "not marked by both tools" in ref3, ref3)
pool_nr = write_pool(qs, final=False)
S.stage_marks(pool_nr, rep_good, os.path.join(tmp, "o7"), S.NAMES)
try:
    S.stage_key(pool_nr, rep_good, os.path.join(tmp, "o7"), key_p, S.NAMES, "sealed")
    ref4 = None
except SystemExit as e:
    ref4 = str(e)
check("a sealed scoring refuses a pool the guarded runner did not make", ref4 and "guarded sealed run" in ref4, ref4)
S.halves_of = lambda *a, **k: {"R03"}
try:
    S.stage_key(pool_nr, rep_good, os.path.join(tmp, "o7"), key_p, S.NAMES, "dev")
    ref5 = None
except SystemExit as e:
    ref5 = str(e)
check("--half dev refuses a pool that holds a sealed question", ref5 and "sealed question" in ref5, ref5)
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "score_sealed_run.py"), encoding="utf-8").read()
check("stage 1 has no key argument and never opens the key", "key_path" not in src.split("def stage_marks")[1].split("def stage_key")[0])
print()
print("FAILED: " + ", ".join(FAILS) if FAILS else "all passed")
sys.exit(1 if FAILS else 0)
