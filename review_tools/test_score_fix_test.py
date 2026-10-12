"""Tests for review_tools/score_fix_test.py on an invented stage F pool, invented replies and an invented key built on the writer's real tags (no network, no spend, nothing sealed).
Marks are designed so that every number can be worked out by hand: see the comments. Run: python review_tools/test_score_fix_test.py"""
import copy
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fix_arms as FA
import fix_test_set as FT
import score_fix_test as S

FAILS = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{detail}]"))
    if not cond:
        FAILS.append(name)


ROOT = FT.ROOT
WB = os.path.join(ROOT, "review_data", "ruler", "inputs", "2026-10-12_Fix_Test_New_Questions_N01-N30_as_received.xlsx")
AUTH = os.path.join(ROOT, "review_results", "2026-10-12_new_questions_intake", "authorities_as_received.json")
B, N1, N2 = FA.B_VERSION, FA.v2_name("N1", 1.25), FA.v2_name("N2", 1.25)
public0, key0 = FT.build(WB, json.load(open(AUTH, encoding="utf-8")), ["N04", "N06", "N07", "N13"], "3c80a26e42bea75e5858be6ed44a2649ec701355", today="2026-10-12")
# marks by row number: row 1 Partly, 2 Yes, 3 Partly, 4 No, 5 Misleading, 6 Yes, 7 to 10 No; rows 11 and 12 differ between the tools (agreement 10/12)
CHAT = {1: "Partly", 2: "Yes", 3: "Partly", 4: "No", 5: "Misleading", 6: "Yes", 7: "No", 8: "No", 9: "No", 10: "No", 11: "No", 12: "No"}
GEM = {**CHAT, 11: "Partly", 12: "Partly"}
NROWS = 12
LA = [q["id"] for q in public0["questions"] if q["look_alike"] and q["domain"] != "K"]
SCORED = [q["id"] for q in public0["questions"] if q["domain"] != "K"]
CONTROLS = [q["id"] for q in public0["questions"] if q["domain"] == "K"]
check("fixture: 27 scored, 3 controls, 17 look-alikes, 4 soft overlaps", len(SCORED) == 27 and len(CONTROLS) == 3 and len(LA) == 17 and sum(q["soft_overlap"] for q in public0["questions"]) == 4)


def lst(rows):
    return [{"doc": 1000 + r, "h": f"h{r}", "also": []} for r in rows]


def build_world(tmp, n1_top5=None, n2_top5=None, key_row=2, drop_replies=0, tweak_set=None):
    """n1_top5 / n2_top5: function qid -> list of 5 row numbers (default: B's rows 1 to 5). key_row: the row whose document is the key authority of every answerable question."""
    public = copy.deepcopy(public0); key = copy.deepcopy(key0)
    for qid, k in key["questions"].items():
        if k["reachable"] is True:
            k["key_docs"] = [1000 + key_row]; k["primary_key_docs"] = [1000 + key_row]
        k["stale_docs"] = []
    public["freeze"]["key_sha256"] = FT.key_digest(key)
    if tweak_set:
        tweak_set(public, key)
    qs = []
    for q in public["questions"]:
        rows_b = list(range(1, 11))
        t1 = (n1_top5(q["id"]) if n1_top5 else [1, 2, 3, 4, 5]); t2 = (n2_top5(q["id"]) if n2_top5 else [1, 2, 3, 4, 5])
        order = lambda top: top + [r for r in range(1, 11) if r not in top]
        lists = {B: lst(rows_b), N1: lst(order(t1)), N2: lst(order(t2))}
        rows = []
        for r in range(1, NROWS + 1):
            rows.append({"n": r, "h": f"h{r}", "doc": 1000 + r, "pn": str(r), "page": r, "title": f"Case {r}", "text": f"{r}. Passage text number {r} for {q['id']} about the question.", "also": [],
                         "variants": {v: l.index(next(x for x in l if x["h"] == f"h{r}")) + 1 for v, l in lists.items() if any(x["h"] == f"h{r}" for x in l[:10])}})
        qs.append({"qid": q["id"], "domain": q["domain"], "kind": q["kind"], "question": q["text"], "rewrite": None, "half": "final", "rows": rows, "lists": lists,
                   "meta": {k: q[k] for k in ("look_alike", "soft_overlap", "control_type", "acts", "acts_named", "trap", "twin_of")}, "spend": {"rerank_tokens": 1, "embed_tokens": 1}})
    run = {"half": "final", "fix_test": {"stage": "F", "finalists": [N1, N2], "question_freeze_sha256": public["freeze"]["sha256"], "code_uncommitted": [], "label": "test"}}
    paths = {k: os.path.join(tmp, k) for k in ("pool.json", "set.json", "key.json")}
    json.dump({"run": run, "questions": qs}, open(paths["pool.json"], "w"))
    json.dump(public, open(paths["set.json"], "w"), sort_keys=True); json.dump(key, open(paths["key.json"], "w"), sort_keys=True)
    rep = os.path.join(tmp, "replies"); os.makedirs(rep, exist_ok=True)
    n = 0
    for q in qs:
        for tool, marks in (("ChatGPT", CHAT), ("Gemini", GEM)):
            if n < len(qs) * 2 - drop_replies:
                open(os.path.join(rep, f"{q['qid']}_A_{tool}.txt"), "w").write(json.dumps({"question_id": q["qid"], "marks": [{"no": r["n"], "mark": marks[r["n"]], "evidence": r["text"][:20], "reason": "x", "confidence": "high"} for r in q["rows"]],
                                                                                           "good_answer_present": "Yes", "best_passage_no": None, "caveats": ""}))
            n += 1
    return paths, rep, public, key


def world(**kw):
    t = tempfile.mkdtemp()
    return (t,) + build_world(t, **kw)


helps = lambda qid: [6, 1, 2, 3, 4] if qid in LA else [1, 2, 3, 4, 5]          # the finalist swaps B's Misleading fifth passage for the Yes sixth one on the look-alike questions
# ---- scenario 1: N1 helps the look-alikes; N2 changes nothing -----------------------------------------------------------------------------------------
t, P, rep, public, key = world(n1_top5=helps)
out = os.path.join(t, "out")
s1 = S.stage_marks(P["pool.json"], rep, P["set.json"], out)
check("stage 1: coverage complete, 27 scored questions, controls apart", s1["coverage_complete"] and s1["scored_questions"] == 27 and s1["controls"] == CONTROLS, (s1["coverage_complete"], s1["scored_questions"]))
check("agreement is 10 of 12 passages = 83.3% and the reliability note is ok", abs(s1["tool_agreement_exact"] - 10 / 12) < 1e-9 and s1["reliability"] == "ok", s1["tool_agreement_exact"])
lo = s1["settlements"][S.BOTH[0]]
# B top 5 = Partly, Yes, Partly, No, Misleading: yes .2, useful .6, mis .2, grade 1.6. N1 on a look-alike = Yes, Partly, Yes, Partly, No: yes .4, useful .8, mis 0, grade 2.2
check("B's shares over the 27 scored questions: Yes 20%, useful 60%, Misleading 20%, grade 1.6", abs(lo[B]["yes"] - .2) < 1e-9 and abs(lo[B]["useful"] - .6) < 1e-9 and abs(lo[B]["mis"] - .2) < 1e-9 and abs(lo[B]["grade"] - 1.6) < 1e-9, lo[B])
exp_yes = (17 * .4 + 10 * .2) / 27
check("N1's shares: 17 look-alikes at Yes 40%, useful 80%, Misleading 0, grade 2.2 and 10 others as B", abs(lo[N1]["yes"] - exp_yes) < 1e-9 and abs(lo[N1]["useful"] - (17 * .8 + 10 * .6) / 27) < 1e-9 and abs(lo[N1]["mis"] - 10 * .2 / 27) < 1e-9 and abs(lo[N1]["grade"] - (17 * 2.2 + 10 * 1.6) / 27) < 1e-9, lo[N1])
check("N2 equals B (its top 5 is B's)", abs(lo[N2]["grade"] - lo[B]["grade"]) < 1e-9)
check("all four settlements give the same numbers here (the tools differ only outside the top 5)", len({round(s1["settlements"][s][N1]["grade"], 9) for s in s1["settlements"]}) == 1)
check("controls are not in the pooled numbers: they are reported apart with their own shares", set(s1["controls_apart"]) == set(CONTROLS) and s1["controls_apart"]["N28"][B]["useful"] == .6, s1["controls_apart"]["N28"][B])
f1 = s1["finalists"][N1]
check("rule 1, 2, 3, 5 and rule 6a hold for N1: better on the 17 look-alikes, worse on none; look-alike Misleading 20% to 0", f1["marks_rules"]["marks_rules_hold"] and f1["marks_rules"]["rule6a_lookalike_misleading_5_points_lower"]
      and f1["compare"][S.BOTH[0]]["R_better"] == sorted(LA) and f1["compare"][S.BOTH[0]]["R_worse"] == [] and abs(f1["lookalike_misleading"]["B"] - .2) < 1e-9 and f1["lookalike_misleading"]["V"] == 0, f1["marks_rules"])
check("N1's top 5 differs from B's on exactly the 17 look-alikes", f1["changed_top5_questions"] == sorted(LA))
f2 = s1["finalists"][N2]
check("N2 fails rule 3 and rule 6a (nothing changed)", not f2["marks_rules"]["rule3_two_more_questions_better"] and not f2["marks_rules"]["rule6a_lookalike_misleading_5_points_lower"] and f2["changed_top5_questions"] == [])
check("the same is computed without the soft overlaps (23 questions) and is only descriptive", f1["without_soft_overlaps"]["questions"] == 23 and f1["without_soft_overlaps"]["marks_rules"]["marks_rules_hold"])
ic = s1["floors_including_controls"]
check("with the controls pooled in (descriptive), B's useful share is still 60% because the controls got the same marks", abs(ic[B]["F1_useful_lower"] - .6) < 1e-9 and set(ic) == {B, N1, N2})
check("floors on the marks: B misses F1 and F4, N1 meets F1, F2 and F4", not s1["floors"][B]["F1"] and not s1["floors"][B]["F4"] and s1["floors"][N1]["F1"] and s1["floors"][N1]["F2"] and s1["floors"][N1]["F4"], {k: s1["floors"][N1][k] for k in ("F1", "F2", "F4")})
s2 = S.stage_key(P["pool.json"], rep, P["set.json"], P["key.json"], out)
check("stage 2: 27 answerable, named authority in the top 5 for all (key document is B's second passage), no stale", len(s2["answerable"]) == 27 and s2["named_authority"][B]["top5"] == 27 and s2["named_authority"][N1]["top10"] == 27 and s2["stale_in_top5"][B] == 0, s2["named_authority"])
v1 = s2["verdicts"][N1]
check("N1 passes rules 1 to 6 and is adopted; N2 does not", v1["passes"] and not s2["verdicts"][N2]["passes"] and s2["adopted"] == N1 and s2["chosen_recipe"] == N1, s2["verdicts"])
check("the floors on the chosen recipe: all four met (F3 100%)", s2["floors_met"] and s2["floors_chosen"]["F3"] and s2["floors_chosen"]["F3_named_authority_top10"] == 1.0)
check("the outcome says N1 replaces B and the recipe may go to shadow mode in the eligible domains only", "replaces B" in s2["outcome"] and "shadow mode" in s2["outcome"] and any(d["eligible"] for d in s2["domains"].values()), s2["outcome"])
check("the key is opened once: a record names the questions read and the pool hash from stage 1", json.load(open(os.path.join(out, "key_opened.json")))["after_stage1_pool_sha256"] == s1["pool_sha256"])
check("the report is written, says LLM-judged and never 'accurate'", "LLM-judged" in open(os.path.join(out, "FIX_TEST_REPORT.md"), encoding="utf-8").read() and "X% accurate" in open(os.path.join(out, "FIX_TEST_REPORT.md"), encoding="utf-8").read())
check("without the soft overlaps the decision data are reported separately", s2["without_soft_overlaps"]["questions_left"] == 23 and "N1" in json.dumps(s2["without_soft_overlaps"]["marks_rules"]))
shutil.rmtree(t)
# ---- scenario 2: N1 improves the marks but loses the named authority from the top 5 (rule 4) -------------------------------------------------------------
t, P, rep, public, key = world(n1_top5=helps, key_row=5)
out = os.path.join(t, "out"); S.stage_marks(P["pool.json"], rep, P["set.json"], out)
s2 = S.stage_key(P["pool.json"], rep, P["set.json"], P["key.json"], out)
check("rule 4 stops N1: the key document (B's fifth passage) leaves its top 5 on the look-alikes; B stays", not s2["verdicts"][N1]["rule4_named_authority_and_stale_not_worse"] and not s2["verdicts"][N1]["passes"] and s2["adopted"] is None and s2["chosen_recipe"] == B, s2["verdicts"][N1])
check("B misses F1 and F4: the outcome says so", not s2["floors_met"] and "B stays" in s2["outcome"] and "a floor is missed" in s2["outcome"], s2["outcome"])
shutil.rmtree(t)
# ---- scenario 3: both finalists identical and passing: the tie goes to the precise trigger ------------------------------------------------------------
t, P, rep, public, key = world(n1_top5=helps, n2_top5=helps)
out = os.path.join(t, "out"); S.stage_marks(P["pool.json"], rep, P["set.json"], out)
s2 = S.stage_key(P["pool.json"], rep, P["set.json"], P["key.json"], out)
check("two passing finalists with equal grades: the one with the precise trigger (N1) is adopted", s2["passing"] == [N1, N2] and s2["adopted"] == N1, (s2["passing"], s2["adopted"]))
shutil.rmtree(t)
# ---- scenario 4: a finalist that is worse on the marks fails rule 1 -------------------------------------------------------------------------------------------
worse = lambda qid: [5, 1, 2, 3, 4] if qid in LA else [1, 2, 3, 4, 5]               # the Misleading passage moves to first place: same shares, so only the order changes
t, P, rep, public, key = world(n1_top5=lambda q: [5, 4, 3, 2, 1] if q in LA else [1, 2, 3, 4, 5])
out = os.path.join(t, "out"); s1 = S.stage_marks(P["pool.json"], rep, P["set.json"], out)
check("a reordering with the same five passages changes no share and no mean grade, so no rule is satisfied by it either (rule 3 and 6 fail)", not s1["finalists"][N1]["marks_rules"]["rule3_two_more_questions_better"] and s1["finalists"][N1]["changed_top5_questions"] == sorted(LA))
shutil.rmtree(t)
# ---- scenario 5: the Misleading passage is a look-alike's first place: rule 6b by the key alone (more look-alikes with the key authority in the top 5) --------
t, P, rep, public, key = world(n1_top5=lambda q: [1, 3, 4, 5, 2] if q in LA else [1, 2, 3, 4, 5], key_row=2)
out = os.path.join(t, "out"); S.stage_marks(P["pool.json"], rep, P["set.json"], out)
s2 = S.stage_key(P["pool.json"], rep, P["set.json"], P["key.json"], out)
check("rule 6b needs MORE look-alikes with the key authority in the top 5 than B has: equal counts do not count", not s2["verdicts"][N1]["rule6b_key_authority_top5_on_more_lookalikes"] and s2["verdicts"][N1]["named_top5_lookalikes"] == {"B": 17, "V": 17}, s2["verdicts"][N1]["named_top5_lookalikes"])
shutil.rmtree(t)
# ---- guards ---------------------------------------------------------------------------------------------------------------------------------------------------
t, P, rep, public, key = world(n1_top5=helps, drop_replies=2)
out = os.path.join(t, "out"); s1 = S.stage_marks(P["pool.json"], rep, P["set.json"], out)
check("stage 1 reports INCOMPLETE when two reply files are missing", not s1["coverage_complete"] and s1["passages_not_marked_by_both_tools"] > 0)
try:
    S.stage_key(P["pool.json"], rep, P["set.json"], P["key.json"], out); ok = False
except SystemExit as e:
    ok = "not marked by both tools" in str(e)
check("stage 2 refuses an incomplete stage 1 (the key stays closed)", ok and not os.path.exists(os.path.join(out, "stage2.json")))
shutil.rmtree(t)
t, P, rep, public, key = world(n1_top5=helps)
out = os.path.join(t, "out")
try:
    S.stage_key(P["pool.json"], rep, P["set.json"], P["key.json"], out); ok = False
except SystemExit as e:
    ok = "stage 1" in str(e)
check("stage 2 refuses when stage 1 has not been run", ok)
S.stage_marks(P["pool.json"], rep, P["set.json"], out)
open(os.path.join(rep, "N01_A_Gemini.txt"), "a").write(" ")
try:
    S.stage_key(P["pool.json"], rep, P["set.json"], P["key.json"], out); ok = False
except SystemExit as e:
    ok = "changed since stage 1" in str(e)
check("stage 2 refuses when the replies changed after stage 1", ok)
open(os.path.join(rep, "N01_A_Gemini.txt"), "w").write(open(os.path.join(rep, "N01_A_ChatGPT.txt")).read().replace("Misleading", "Misleading"))
shutil.rmtree(t)
t, P, rep, public, key = world(n1_top5=helps)
out = os.path.join(t, "out"); S.stage_marks(P["pool.json"], rep, P["set.json"], out)
k2 = json.load(open(P["key.json"])); k2["questions"]["N03"]["key_docs"] = [1]; json.dump(k2, open(P["key.json"], "w"))
try:
    S.stage_key(P["pool.json"], rep, P["set.json"], P["key.json"], out); ok = False
except SystemExit as e:
    ok = "key has changed" in str(e)
check("stage 2 refuses a key whose hash differs from the one sealed in the question file", ok)
shutil.rmtree(t)
t, P, rep, public, key = world(n1_top5=helps)
pool = json.load(open(P["pool.json"])); pool["run"]["fix_test"]["question_freeze_sha256"] = "0" * 64; json.dump(pool, open(P["pool.json"], "w"))
try:
    S.stage_marks(P["pool.json"], rep, P["set.json"], os.path.join(t, "o")); ok = False
except SystemExit as e:
    ok = "not made from this question file" in str(e)
check("a pool made from another question file is refused", ok)
pool = json.load(open(P["pool.json"])); pool["run"]["fix_test"] = {"stage": "D2"}; json.dump(pool, open(P["pool.json"], "w"))
try:
    S.stage_marks(P["pool.json"], rep, P["set.json"], os.path.join(t, "o")); ok = False
except SystemExit as e:
    ok = "not the stage F pool" in str(e)
check("a stage D2 pool is refused", ok)
shutil.rmtree(t)
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "score_fix_test.py"), encoding="utf-8").read()
check("stage 1 never opens the key file", src.split("def stage_key")[0].count("key_path") == 0 and "json.load(open(key_path" not in src.split("def stage_key")[0])
print("\nall passed" if not FAILS else f"\n{len(FAILS)} FAILED: {FAILS}")
sys.exit(1 if FAILS else 0)
