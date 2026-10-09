"""Tests for review_tools/score_rerank_arms.py on an invented extended pool and invented marks. Run: python review_tools/test_score_rerank_arms.py"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import score_rerank_arms as S
import ingest_llm_reviews as ing

FAILS = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{detail}]"))
    if not cond:
        FAILS.append(name)


A, N, M = S.A_ARM, S.N_ARM, S.M_ARM


def row(n, variants, text=None, **kw):
    return dict({"n": n, "h": f"h{n}", "doc": 100 + n, "pn": str(n), "page": 1, "title": f"Case {n}", "text": text or f"Passage {n} of the judgment says something about bail and the accused.", "also": [], "variants": variants}, **kw)


# R90: first batch n1..n7 (n8 and the anchor n9 belong to the second batch)
rows90 = [row(1, {A: 1, N: 1}), row(2, {A: 2, N: 2}), row(3, {A: 3, N: 3}), row(4, {A: 4}), row(5, {A: 5}), row(6, {A: 6, N: 4}), row(7, {A: 7}),
          row(8, {N: 5, M: 1}, topup=True), row(9, {}, topup=True, anchor_of=1, text="Passage 1 of the judgment says something about bail and the accused.")]
# R91: only first-batch rows; A's top 5 all Yes by both tools, N's top 5 shares three of them
rows91 = [row(i, {A: i, N: (i if i <= 3 else None)} if i <= 3 else {A: i}) for i in range(1, 6)] + [row(6, {N: 4}), row(7, {N: 5})]
for r in rows91:
    r["variants"] = {k: v for k, v in r["variants"].items() if v is not None}
pool = {"run": {}, "questions": [{"qid": "R90", "kind": "legal", "rows": rows90}, {"qid": "R91", "kind": "everyday", "rows": rows91}]}

chat = {"R90": {1: "Yes", 2: "Partly", 3: "No", 4: "Yes", 5: "Partly", 6: "Yes", 7: "No"}, "R91": {1: "Yes", 2: "Yes", 3: "Yes", 4: "Yes", 5: "Yes", 6: "No", 7: "No"}}
gem = {"R90": {1: "Yes", 2: "Yes", 3: "No", 4: "Partly", 5: "No", 6: "No", 7: "No"}, "R91": {1: "Yes", 2: "Yes", 3: "Yes", 4: "Yes", 5: "Yes", 6: "No", 7: "Partly"}}
runs = {("ChatGPT", "A"): {("R90", n): m for n, m in chat["R90"].items()} | {("R91", n): m for n, m in chat["R91"].items()},
        ("Gemini", "A"): {("R90", n): m for n, m in gem["R90"].items()} | {("R91", n): m for n, m in gem["R91"].items()},
        ("ChatGPT", "TA"): {("R90", 8): "Partly", ("R90", 9): "Yes"},
        ("Gemini", "TA"): {("R90", 8): "No", ("R90", 9): "Partly"}}
res = S.score(pool, runs)
g = S.lists_of(pool["questions"][0])
check("the groups of R90: A's top 5, A's 6 to 10, N's top 5, the net, the list shown, and the three swap groups; anchors belong to none",
      g["A top 5"] == [1, 2, 3, 4, 5] and g["A places 6 to 10"] == [6, 7] and g["N top 5"] == [1, 2, 3, 6, 8] and g["M safety net"] == [8] and g["A ten plus M"] == [1, 2, 3, 4, 5, 6, 7, 8]
      and g["kept (in both top 5)"] == [1, 2, 3] and g["promoted (A only)"] == [4, 5] and g["demoted (N only)"] == [6, 8], g)
c = res["settlements"]["ChatGPT alone"]["groups"]
check("ChatGPT alone: A's top 5 averages (40% + 100%) / 2 = 70% direct over the two questions", abs(c["A top 5"]["yes"] - 0.7) < 1e-9 and c["A top 5"]["questions"] == 2, c["A top 5"])
r90a = S.shares([chat["R90"][n] for n in g["A top 5"]])
r90n = S.shares([chat["R90"][n] if n != 8 else "Partly" for n in g["N top 5"]])
check("by hand: A 40/80/0 and N 40/80/0 for ChatGPT on R90", (r90a["yes"], r90a["useful"], r90a["mis"]) == (0.4, 0.8, 0.0) and (r90n["yes"], r90n["useful"], r90n["mis"]) == (0.4, 0.8, 0.0), (r90a, r90n))
# macro over the two questions: R91 A = all Yes (1.0, 1.0), N top 5 = n1,n2,n3,n6,n7 -> Yes Yes Yes No No = 0.6 / 0.6
pg = res["settlements"]["ChatGPT alone"]["A_top5_minus_N_top5"]
check("ChatGPT alone: A minus N averaged over the two questions: direct (0 + 0.4)/2 = +20 points, useful (0 + 0.4)/2 = +20", abs(pg["yes"]["A_minus_N"] - 0.2) < 1e-9 and abs(pg["useful"]["A_minus_N"] - 0.2) < 1e-9 and pg["yes"]["questions"] == 2, pg)
check("the bootstrap interval is over questions and holds the mean", pg["yes"]["ci95_over_questions"][0] <= 0.2 <= pg["yes"]["ci95_over_questions"][1], pg["yes"]["ci95_over_questions"])
gm = res["settlements"]["Gemini alone"]["A_top5_minus_N_top5"]
# Gemini R90: A = Yes Yes No Partly No (0.4 / 0.6); N = n1 Yes, n2 Yes, n3 No, n6 No, n8 No (0.4 / 0.4) -> 0, +0.2 ; R91: A all Yes; N = Y Y Y N Partly -> 0.6 / 0.8 -> +0.4 / +0.2
check("Gemini alone: direct (0 + 0.4)/2 = +20, useful (0.2 + 0.2)/2 = +20", abs(gm["yes"]["A_minus_N"] - 0.2) < 1e-9 and abs(gm["useful"]["A_minus_N"] - 0.2) < 1e-9, gm)
pp = res["settlements"]["ChatGPT alone"]["passages_pooled"]
check("promoted (A only) = R90 n4, n5 and R91 n4, n5; demoted (N only) = R90 n6, n8 and R91 n6, n7: pooled over passages", pp["promoted (A only)"]["passages"] == 4 and pp["demoted (N only)"]["passages"] == 4
      and abs(pp["promoted (A only)"]["yes"] - 0.75) < 1e-9 and abs(pp["demoted (N only)"]["yes"] - 0.25) < 1e-9, pp)
tiers = res["settlements"]["both, ties to the lower mark"]["groups"]
check("tiers exist for the lists to show", {"A top 5", "A places 6 to 10", "M safety net", "A ten plus M", "N top 5"} <= set(tiers), sorted(tiers))
an = res["anchors"]
check("anchors: ChatGPT gave Yes to n1 and Yes to its repeat (same); Gemini gave Yes then Partly (second lower by one grade)", an["ChatGPT"]["pairs"] == 1 and an["ChatGPT"]["same_mark"] == 1.0 and an["Gemini"]["same_mark"] == 0.0 and an["Gemini"]["second_lower"] == 1
      and abs(an["both"]["mean_grade_shift_second_minus_first"] + 0.5) < 1e-9 and an["Gemini"]["same_useful_or_not"] == 1.0, an)
check("coverage: every passage of the lists is marked here, so none is missing", all(v["not_marked_by_any_run"] == 0 for v in res["coverage"].values()), res["coverage"])
runs2 = {k: dict(v) for k, v in runs.items()}
del runs2[("ChatGPT", "TA")][("R90", 8)]
del runs2[("Gemini", "TA")][("R90", 8)]
cov = S.score(pool, runs2)["coverage"]
check("coverage counts a passage no run has marked, and leaves it out of the shares", cov["M safety net"]["not_marked_by_any_run"] == 1 and cov["N top 5"]["not_marked_by_any_run"] == 1 and "M safety net" not in S.score(pool, runs2)["settlements"]["ChatGPT alone"]["groups"])

# through the files: the same marks written as replies and read by the ingest tool
tmp = tempfile.mkdtemp()
pp_ = os.path.join(tmp, "pool.json")
json.dump(pool, open(pp_, "w"))
rep = os.path.join(tmp, "replies")
os.makedirs(rep)
def write(qid, order, tool, nums, marks):
    qrows = {r["n"]: r for r in next(q for q in pool["questions"] if q["qid"] == qid)["rows"]}
    json.dump({"question_id": qid, "marks": [{"no": n, "mark": marks[n], "evidence": qrows[n]["text"][:25], "reason": "x", "confidence": "high"} for n in nums], "good_answer_present": "Yes", "best_passage_no": None, "caveats": ""},
              open(os.path.join(rep, f"{qid}_{order}_{tool}.txt"), "w"))
for tool, d in (("ChatGPT", chat), ("Gemini", gem)):
    write("R90", "A", tool, range(1, 8), d["R90"]); write("R91", "A", tool, range(1, 8), d["R91"])
write("R90", "TA", "ChatGPT", [8, 9], {8: "Partly", 9: "Yes"}); write("R90", "TA", "Gemini", [8, 9], {8: "No", 9: "Partly"})
outd = os.path.join(tmp, "out")
rc = S.main(["--pool", pp_, "--replies", rep, "--out", outd])
saved = json.load(open(os.path.join(outd, "rerank_arms_scores.json")))
check("main reads the replies of both batches against the extended pool and writes the same numbers", rc == 0 and saved["reply_problems"] == 0 and saved["settlements"]["ChatGPT alone"]["A_top5_minus_N_top5"]["yes"]["A_minus_N"] == res["settlements"]["ChatGPT alone"]["A_top5_minus_N_top5"]["yes"]["A_minus_N"]
      and saved["runs"] == {"ChatGPT/A": 14, "ChatGPT/TA": 2, "Gemini/A": 14, "Gemini/TA": 2}, saved["runs"])
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "score_rerank_arms.py"), encoding="utf-8").read()
check("the scorer never reads the private key", "real30_key" not in src and "real30_score" not in src)

print()
print("FAILED: " + ", ".join(FAILS) if FAILS else "all passed")
sys.exit(1 if FAILS else 0)
