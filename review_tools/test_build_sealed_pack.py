"""Tests for review_tools/build_sealed_pack.py on an invented pool (no network, no spend). Run: python review_tools/test_build_sealed_pack.py"""
import csv
import json
import os
import re
import sys
import tempfile
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_sealed_pack as B
import ingest_llm_reviews as ing

FAILS = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{detail}]"))
    if not cond:
        FAILS.append(name)


def mk_q(qid, n, question="Can bail be refused on the facts of the case under the old version of the section?"):
    rows = [{"n": i, "h": f"{qid}h{i}", "doc": 100 + i, "pn": str(i), "page": i, "title": f"Case {i} v. State", "text": f"{i}. The court considered the accused's liberty and the rival extra argument number {i}.", "also": [],
             "variants": {"A today": i, "R challenger re-ranker": n - i + 1}} for i in range(1, n + 1)]
    return {"qid": qid, "domain": "B", "kind": "legal", "question": question, "rewrite": None, "half": "sealed", "rows": rows, "lists": {"A today": []}}


run = {"half": "sealed", "final_recipe": {"label": "x | rules abc | code def", "code_uncommitted": []}, "versions": ["A today", "R challenger re-ranker"]}
tmp = tempfile.mkdtemp()
pool_p = os.path.join(tmp, "pool.json")
json.dump({"run": run, "questions": [mk_q("R03", 12), mk_q("R05", 9), mk_q("R07", 15)]}, open(pool_p, "w"))
out = os.path.join(tmp, "out")
info = B.build(pool_p, out)
folder = os.path.join(out, B.PACK_NAME)
prompts = sorted(os.listdir(os.path.join(folder, "prompts")))
check("one prompt file per question, order A only, named like R03_A.txt", prompts == ["R03_A.txt", "R05_A.txt", "R07_A.txt"], prompts)
check("two chats per file, 36 passages in all", info["chats"] == 6 and info["passages"] == 36 and info["questions"] == 3, info)
txt = open(os.path.join(folder, "prompts", "R05_A.txt"), encoding="utf-8").read()
check("every passage number 1 to 9 is in the prompt once, in number order (order A)", [int(x) for x in re.findall(r"--- PASSAGE (\d+) ---", txt)] == list(range(1, 10)))
check("the prompt asks for the usual single JSON object for that question", "QUESTION ID: R05" in txt and "END OF PASSAGES. Now reply with the single JSON object for R05" in txt)
check("nothing in our own wording (the README, the prompt framing) names an arm, a re-ranker, the half or the key", not B.framing_leaks(open(os.path.join(folder, "README.txt"), encoding="utf-8").read()) and not B.framing_leaks(re.sub(r"(?s)QUESTION:.*?={78}\n.*?(?=={78}\nEND)", "", txt)))
check("a court-text word such as 'extra' or a question that says 'version' does not trip the check", "extra argument" in txt and "version" in txt)
man = list(csv.reader(open(os.path.join(folder, "manifest.csv"), encoding="utf-8")))
check("the manifest names the reply files for both tools", len(man) == 7 and {r[5] for r in man[1:]} == {f"{q}_A_{t}.txt" for q in ("R03", "R05", "R07") for t in ("ChatGPT", "Gemini")})
readme = open(os.path.join(folder, "README.txt"), encoding="utf-8").read()
check("the README tells them to check the saved file is a reply and that the two tools' files differ", "not the prompt you pasted" in readme and "different replies" in readme and "6 chats in all" in readme)
with zipfile.ZipFile(os.path.join(out, B.PACK_NAME + ".zip")) as z:
    names = z.namelist()
check("the zip holds the prompts, README, manifest and an empty replies folder under one top folder, and no pool", all(n.startswith(B.PACK_NAME + "/") for n in names) and not any("pool" in n for n in names) and f"{B.PACK_NAME}/README.txt" in names)
# the replies come back and are read against the same pool
rep = os.path.join(tmp, "replies")
os.makedirs(rep)
pool_l, passages = ing.load_pool(pool_p)
for q in pool_l:
    for tool, marks in (("ChatGPT", ["Yes", "Partly"]), ("Gemini", ["Partly", "No"])):
        open(os.path.join(rep, f"{q['qid']}_A_{tool}.txt"), "w").write(json.dumps({"question_id": q["qid"], "marks": [{"no": r["n"], "mark": marks[r["n"] % 2], "evidence": r["text"][:25], "reason": "x", "confidence": "high"} for r in q["rows"]],
                                                                                   "good_answer_present": "Yes", "best_passage_no": None, "caveats": ""}))
runs, problems, ev = ing.load_replies(rep, passages, pool_l)
check("the replies are read against the pool as order-A runs without a problem, every passage marked by both tools", not problems and set(runs) == {("ChatGPT", "A"), ("Gemini", "A")} and len(runs[("ChatGPT", "A")]) == 36, (problems[:2], sorted(runs)))
# refusals
def refused(pool_doc, **kw):
    pp = os.path.join(tmp, "p2.json")
    json.dump(pool_doc, open(pp, "w"))
    try:
        B.build(pp, os.path.join(tmp, "o2"), **kw)
        return None
    except SystemExit as e:
        return str(e)
check("refused: a pool that is not a sealed run's final recipe", "not the final recipe" in (refused({"run": {"half": "dev"}, "questions": [mk_q("R01", 5)]}) or ""))
check("refused: a pool made from uncommitted code", "uncommitted" in (refused({"run": {"half": "sealed", "final_recipe": {"code_uncommitted": ["a.py"]}}, "questions": [mk_q("R03", 5)]}) or ""))
gap = mk_q("R03", 5)
gap["rows"][2]["n"] = 7
check("refused: numbering with a gap", "not 1 to 5" in (refused({"run": run, "questions": [gap]}) or ""))
empty = mk_q("R03", 5)
empty["rows"][1]["text"] = "  "
check("refused: an empty passage text", "empty passage" in (refused({"run": run, "questions": [empty]}) or ""))
check("refused: a question with no passages", "no passages" in (refused({"run": run, "questions": [dict(mk_q("R03", 5), rows=[])]}) or ""))
info_r = B.build(pool_p, os.path.join(tmp, "rehearsal_out"), rehearsal=True) if False else None
dev_pool = {"run": {"half": "dev"}, "questions": [mk_q("R01", 6)]}
pp = os.path.join(tmp, "dev.json")
json.dump(dev_pool, open(pp, "w"))
ir = B.build(pp, os.path.join(tmp, "reh"), rehearsal=True)
check("a rehearsal on a tuning pool is allowed, is named Rehearsal_Pack and says so in its record", ir["rehearsal"] and os.path.isdir(os.path.join(tmp, "reh", B.REHEARSAL_NAME)) and not os.path.isdir(os.path.join(tmp, "reh", B.PACK_NAME)))
# the fix test's stage F pool (pool_runner.py --fix-test F): pack named Fourth_Batch_Pack, N-ids, replies read by the same reader
fx_run = {"half": "final", "fix_test": {"stage": "F", "finalists": ["N1-125 named-Act boost x1.25 (precise)"], "label": "stage F | rules abc | code def", "code_uncommitted": []}, "versions": ["B baseline (rerank-3-lite)"]}
def mk_n(qid, n):
    q = mk_q(qid, n)
    for r in q["rows"]:
        r["variants"] = {"B baseline (rerank-3-lite)": r["n"], "N1-125 named-Act boost x1.25 (precise)": n - r["n"] + 1}
    return dict(q, half="final")
fp = os.path.join(tmp, "fix_pool.json")
json.dump({"run": fx_run, "questions": [mk_n("N01", 11), mk_n("N02", 8)]}, open(fp, "w"))
fi = B.build(fp, os.path.join(tmp, "fixout"), fixtest=True)
fprompts = sorted(os.listdir(os.path.join(tmp, "fixout", B.FIXTEST_NAME, "prompts")))
check("the stage F pack is named Fourth_Batch_Pack, one prompt per question, 2 chats each", fprompts == ["N01_A.txt", "N02_A.txt"] and fi["chats"] == 4 and os.path.exists(os.path.join(tmp, "fixout", B.FIXTEST_NAME + ".zip")) and not os.path.isdir(os.path.join(tmp, "fixout", B.PACK_NAME)), (fprompts, fi))
check("its record carries the run label", fi["run_label"] == "stage F | rules abc | code def", fi["run_label"])
ftxt = open(os.path.join(tmp, "fixout", B.FIXTEST_NAME, "prompts", "N01_A.txt"), encoding="utf-8").read()
check("nothing in the stage F prompt or README names an arm, a finalist or the boost", not B.framing_leaks(open(os.path.join(tmp, "fixout", B.FIXTEST_NAME, "README.txt"), encoding="utf-8").read()) and "named-Act" not in ftxt and "N1-125" not in ftxt and "baseline" not in re.sub(r"(?s)QUESTION:.*", "", ftxt))
frep = os.path.join(tmp, "freplies"); os.makedirs(frep)
fpool_l, fpass = ing.load_pool(fp)
for q in fpool_l:
    for tool in ("ChatGPT", "Gemini"):
        open(os.path.join(frep, f"{q['qid']}_A_{tool}.txt"), "w").write(json.dumps({"question_id": q["qid"], "marks": [{"no": r["n"], "mark": "Partly", "evidence": r["text"][:25], "reason": "x", "confidence": "high"} for r in q["rows"]], "good_answer_present": "Yes", "best_passage_no": None, "caveats": ""}))
fruns, fprob, _ = ing.load_replies(frep, fpass, fpool_l)
check("replies named N01_A_ChatGPT.txt are read against the stage F pool", not fprob and len(fruns[("ChatGPT", "A")]) == 19, (fprob[:2]))
check("refused: a stage D2 pool offered as the stage F pool", "not the stage F pool" in (refused({"run": {"half": "dev", "fix_test": {"stage": "D2"}}, "questions": [mk_n("N01", 5)]}, fixtest=True) or ""))
check("refused: a stage F pool made from uncommitted code", "uncommitted" in (refused({"run": {"fix_test": dict(fx_run["fix_test"], code_uncommitted=["a.py"])}, "questions": [mk_n("N01", 5)]}, fixtest=True) or ""))
check("refused: a final-recipe pool of the sealed run is not accepted as a stage F pool", "not the stage F pool" in (refused({"run": run, "questions": [mk_q("R03", 5)]}, fixtest=True) or ""))
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "build_sealed_pack.py"), encoding="utf-8").read()
check("the builder never reads the private key", "real30_key" not in src and "real30_score" not in src)
print()
print("FAILED: " + ", ".join(FAILS) if FAILS else "all passed")
sys.exit(1 if FAILS else 0)
