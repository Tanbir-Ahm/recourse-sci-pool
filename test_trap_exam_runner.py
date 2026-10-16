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
    check(pick[0] == "Q01" and len(pick) == len(set(pick)) == 4 and "Q02" not in pick and "Q03" not in pick, "the reading sheet puts the answer the guard had to correct first, lists each question once, and leaves out the two questions with no answer text (refused, failed)")
    txt = open(os.path.join(d, "s.md"), encoding="utf-8").read()
    check("Without the locks" in txt and "as the page would show it" in txt and "Reader's mark" in txt, "the sheet has both versions and a place for the mark")
    check(txt.startswith("# Trap exam: 4 answers for the reading lawyer") and txt.count("Reader's mark") == 4 and "(no answer text)" not in txt, "the sheet says how many answers it holds and has no empty entry")
    check("## Not shown: no answer text in either arm" in txt and "Q02 (no_match)" in txt and "Q03 (error)" in txt, "the questions left out are listed at the end with their state")
# the exam calls the assistant the way the website does (the four inline domains), so NDPS is no longer shown as a refusal
calls = []
def _aq(question, inline_domains=frozenset(), audience=None, channel=None):
    calls.append(set(inline_domains))
    return {"state": "single_match", "response_text": "x"}
T.site_answer_fn(_aq)("a question")
check(calls == [{"cheque_bounce", "freeze", "domestic_violence", "ndps"}] and T.SITE_INLINE_DOMAINS == frozenset(calls[0]), "the default call passes the same four inline domains as recourse_app.py and whatsapp_bot.py")
src_site = open(os.path.join(HERE, "..", "recourse", "recourse_app.py"), encoding="utf-8").read() if os.path.exists(os.path.join(HERE, "..", "recourse", "recourse_app.py")) else ""
check(not src_site or 'inline_domains={"cheque_bounce", "freeze", "domestic_violence", "ndps"}' in src_site, "(when a sibling Recourse checkout exists) the page still passes exactly these four")
check(T.site_answer_fn(_aq, ()) is _aq, "with no inline domains the assistant is called as before (runs made before 2026-10-16)")
# the criminal-domain exam: a model that states every case as authority is caught on every question; one that says it was overruled is acknowledged
ck = json.load(open(os.path.join(HERE, "register_exam", "criminal", "key.json"), encoding="utf-8"))
cq = T.load_questions(os.path.join(HERE, "register_exam", "criminal", "questions.jsonl"))
naive = {i: f"{k['case']} is good law and the Supreme Court held X." for i, k in ck.items()}
t_naive, p_naive = EX.score(reg, naive, ck)
check(set(p_naive.values()) == {"guard_note"}, f"a naive answer on all {len(ck)} criminal-exam questions is caught by the guard ({t_naive})")
aware = {i: f"{k['case']} was overruled by {k['overruling']}." for i, k in ck.items()}
check(set(EX.score(reg, aware, ck)[1].values()) == {"acknowledged"}, "an answer that says it was overruled is acknowledged on every question")
check(len(cq) == len(ck) == 28 and len({k["row_id"] for k in ck.values()}) == 14, "28 questions from 14 register rows")
# the situation-form exam
sk = json.load(open(os.path.join(HERE, "register_exam", "situation", "key.json"), encoding="utf-8"))
sq = {q["id"]: q["question"] for q in T.load_questions(os.path.join(HERE, "register_exam", "situation", "questions.jsonl"))}
check(len(sq) == len(sk) == 24 and len({k["row_id"] for k in sk.values()}) == 12, f"situation exam: 24 questions from 12 register rows ({len(sq)})")
named = [i for i, k in sk.items() if k["variant"] == "named"]
check(all(R.party_sigs(sk[i]["case"])[0][0] in sq[i].lower() for i in named) and all(R.party_sigs(sk[i]["case"])[0][0] not in sq[i].lower() for i in sk if sk[i]["variant"] == "unnamed"), "the named version contains the case name, the unnamed one does not")
naive_s = {i: f"{k['case']} is good law and settles this." for i, k in sk.items()}
check(set(EX.score(reg, naive_s, sk)[1].values()) == {"guard_note"}, "a naive answer is caught by the guard on every situation question")
check(all(len(q.split()) < 70 and "good law" not in q for q in sq.values()), "the situation questions are plain facts, not 'is it good law' research")
print("\nALL PASSED" if not F else f"\n{len(F)} FAILED")
sys.exit(1 if F else 0)
