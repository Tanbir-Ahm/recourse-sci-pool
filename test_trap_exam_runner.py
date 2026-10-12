"""Tests for site_patch/run_trap_exam.py with a stand-in assistant (no model, no network, no cost). Run: python test_trap_exam_runner.py"""
import json, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "site_patch"))
import run_trap_exam as T
from goodlaw import register as R, register_exam as EX, overlay as OV

F = []
def check(c, m):
    print(f"[{'PASS' if c else 'FAIL'}] {m}")
    if not c: F.append(m)

reg = R.Register.load()
qs, key = EX.build_exam(reg)
qs = qs[:6]
key = {k: v for k, v in key.items() if k in {q["id"] for q in qs}}
names = {q["id"]: key[q["id"]]["case"] for q in qs}
seen_env = []

def fake(question):
    qid = next(q["id"] for q in qs if q["question"] == question)
    seen_env.append(os.environ.get("REGISTER_HOOKS"))
    if qid == "Q01":
        return {"state": "single_match", "response_text": f"Yes, {names[qid]} is good law and holds X."}   # states the overruled case as authority
    if qid == "Q02":
        return {"state": "no_match"}
    if qid == "Q03":
        raise RuntimeError("model down")
    return {"state": "single_match", "response_text": "I cannot find that case in my sources."}

with tempfile.TemporaryDirectory() as d:
    raw = T.run(".", qs, ["off", "on"], d, answer_fn=fake, log=lambda *_: None)
    check(len(raw) == 12 and [r["arm"] for r in raw[:2]] == ["off", "on"], "every question runs in both arms, off then on")
    check(seen_env[:2] == ["off", "on"], "the switch is set per arm")
    check(any(r["error"] and r["state"] == "error" for r in raw) and sum(1 for r in raw if r["id"] == "Q04") == 2, "one failing question is recorded and the run goes on")
    for r, q in zip(raw, [q for q in qs for _ in (0, 1)]):
        r["question"] = q["question"]
    # the 'on' arm: pretend the page added a note for Q01
    for r in raw:
        if r["id"] == "Q01" and r["arm"] == "on":
            r["register_notes"] = [f"{names['Q01']}: was overruled by {key['Q01']['overruling']}."]
            r["shown"] = T.shown_text({"response_text": r["answer"], "register_notes": r["register_notes"]})
    T.write_outputs(raw, d)
    for n in ("answers_off", "answers_on_model", "answers_on_shown", "raw"):
        check(os.path.exists(os.path.join(d, n + ".jsonl")), n + ".jsonl written")
    t_off, per_off = EX.score(reg, EX.read_answers(os.path.join(d, "answers_off.jsonl")), key)
    t_shown, per_on = EX.score(reg, EX.read_answers(os.path.join(d, "answers_on_shown.jsonl")), key)
    t_model, per_model = EX.score(reg, EX.read_answers(os.path.join(d, "answers_on_model.jsonl")), key)
    check(per_off["Q01"] == "guard_note" and per_model["Q01"] == "guard_note", "stating the overruled case as authority is caught by the guard in the model-only files")
    check(per_on["Q01"] == "acknowledged", "with the page's note added it counts as acknowledged")
    check(T.state_summary(raw)["off"].get("no_match") == 1 and T.state_summary(raw)["off"].get("error") == 1, "the states are counted so a run of refusals is visible")
    pick = T.reading_sheet(raw, key, per_off, per_on, os.path.join(d, "s.md"), n=20)
    check(pick[0] == "Q01" and len(pick) == len(set(pick)) == 6, "the reading sheet puts the answer the guard had to correct first and lists each question once")
    txt = open(os.path.join(d, "s.md"), encoding="utf-8").read()
    check("Without the locks" in txt and "as the page would show it" in txt and "Reader's mark" in txt, "the sheet has both versions and a place for the mark")
# the criminal-domain exam: a model that states every case as authority is caught on every question; one that says it was overruled is acknowledged
ck = json.load(open(os.path.join(HERE, "register_exam", "criminal", "key.json"), encoding="utf-8"))
cq = T.load_questions(os.path.join(HERE, "register_exam", "criminal", "questions.jsonl"))
naive = {i: f"{k['case']} is good law and the Supreme Court held X." for i, k in ck.items()}
t_naive, p_naive = EX.score(reg, naive, ck)
check(set(p_naive.values()) == {"guard_note"}, f"a naive answer on all {len(ck)} criminal-exam questions is caught by the guard ({t_naive})")
aware = {i: f"{k['case']} was overruled by {k['overruling']}." for i, k in ck.items()}
check(set(EX.score(reg, aware, ck)[1].values()) == {"acknowledged"}, "an answer that says it was overruled is acknowledged on every question")
check(len(cq) == len(ck) == 28 and len({k["row_id"] for k in ck.values()}) == 14, "28 questions from 14 register rows")
print("\nALL PASSED" if not F else f"\n{len(F)} FAILED")
sys.exit(1 if F else 0)
