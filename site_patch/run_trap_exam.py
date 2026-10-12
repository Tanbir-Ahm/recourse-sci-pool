"""Runs the trap exam (default: the 28-question criminal-domain one, register_exam/criminal/; --exam original for the 50-question one) through the Recourse assistant with the register's locks OFF and ON, and writes the files the scorer reads.
THIS CALLS THE REAL ANTHROPIC MODEL (and Voyage for retrieval): it costs credit and needs the Recourse keys in the environment. Run it on your own computer, in a Recourse checkout that has the patch applied
(site_patch/recourse_721e063.patch) and the bundle exported (overruled_register/). Nothing is written into the Recourse checkout except what the assistant itself writes; the answer-cache database is pointed at a temporary file.

    python site_patch/run_trap_exam.py --recourse ../recourse --out-dir exam_run_1 [--limit 5] [--arms off,on]

Writes, in --out-dir:
    answers_off.jsonl         the model's answer with REGISTER_HOOKS=off (what the live site says today)
    answers_on_model.jsonl    the model's answer with locks (a) and (b) on, WITHOUT the notes added afterwards
    answers_on_shown.jsonl    what the page would show with all three locks: that answer plus the register/card notes and the 'not checked' sentence
    raw.jsonl                 per question and arm: state, answer, notes, seconds
    reading_sheet.md          20 answers for a lawyer (every one the guard had to correct, then others, fixed seed), with the key
Then score each of the three answer files:  python sci_goodlaw.py register-exam score --answers FILE
Honest reading of a result: a question the assistant refuses or answers from its own library (state other than single_match) says nothing about the register; the run prints how many that is.
"""
import argparse
import json
import os
import random
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def load_questions(path):
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def shown_text(result):
    """The answer plus what the page adds under it (the register notes and the 'not checked' sentence)."""
    parts = [result.get("response_text") or ""]
    parts += list(result.get("register_notes") or [])
    if result.get("register_not_checked"):
        parts.append(result["register_not_checked"])
    return "\n\n".join(p for p in parts if p)


def run(recourse, questions, arms, out_dir, sleep=0.0, answer_fn=None, log=print):
    """Runs every question through each arm (interleaved: off then on for the same question). answer_fn is for tests; by default chat_assistant.answer_question from the Recourse checkout."""
    os.makedirs(out_dir, exist_ok=True)
    os.environ.setdefault("ANSWER_CACHE_DB_PATH", os.path.join(tempfile.mkdtemp(prefix="trap_exam_cache_"), "answer_cache.db"))
    if answer_fn is None:
        sys.path.insert(0, os.path.abspath(recourse))
        os.chdir(os.path.abspath(recourse))
        import chat_assistant
        answer_fn = chat_assistant.answer_question
    raw = []
    prev = os.environ.get("REGISTER_HOOKS")
    try:
        for q in questions:
            for arm in arms:
                os.environ["REGISTER_HOOKS"] = "off" if arm == "off" else "on"
                t0 = time.time()
                try:
                    res = answer_fn(q["question"])
                    err = None
                except Exception as exc:  # one failed question must not lose the run
                    res, err = {"state": "error"}, f"{type(exc).__name__}: {exc}"
                raw.append({"id": q["id"], "arm": arm, "state": res.get("state"), "error": err, "seconds": round(time.time() - t0, 1),
                            "answer": res.get("response_text") or "", "register_notes": res.get("register_notes") or [], "register_not_checked": res.get("register_not_checked"),
                            "shown": shown_text(res)})
                log(f'{q["id"]} {arm}: {res.get("state")} ({raw[-1]["seconds"]}s){" ERROR " + err if err else ""}')
                if sleep:
                    time.sleep(sleep)
    finally:
        if prev is None:
            os.environ.pop("REGISTER_HOOKS", None)
        else:
            os.environ["REGISTER_HOOKS"] = prev
    return raw


def write_outputs(raw, out_dir):
    def dump(name, arm, field):
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as f:
            for r in raw:
                if r["arm"] == arm:
                    f.write(json.dumps({"id": r["id"], "answer": r[field]}, ensure_ascii=False) + "\n")
    dump("answers_off.jsonl", "off", "answer")
    dump("answers_on_model.jsonl", "on", "answer")
    dump("answers_on_shown.jsonl", "on", "shown")
    with open(os.path.join(out_dir, "raw.jsonl"), "w", encoding="utf-8") as f:
        for r in raw:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def state_summary(raw):
    out = {}
    for r in raw:
        out.setdefault(r["arm"], {}).setdefault(r["state"], 0)
        out[r["arm"]][r["state"]] += 1
    return out


def reading_sheet(raw, key, results_off, results_on, out_path, n=20, seed=11):
    """20 answers for a lawyer: every on-arm answer the guard had to correct or could not recognise first, then answers that name the case, then the rest (fixed seed)."""
    by = {(r["id"], r["arm"]): r for r in raw}
    ids = sorted(key)
    first = [i for i in ids if results_on.get(i) in ("guard_note", "unmatched") or results_off.get(i) in ("guard_note", "unmatched")]
    second = [i for i in ids if i not in first and "not_cited" not in (results_off.get(i), results_on.get(i)) and results_off.get(i) and (i, "on") in by]
    rest = [i for i in ids if i not in first and i not in second]
    rnd = random.Random(seed)
    rnd.shuffle(second)
    rnd.shuffle(rest)
    pick = (first + second + rest)[:n]
    lines = ["# Trap exam: 20 answers for the reading lawyer", "",
             "For each: was the old decision stated as current authority anywhere, and did the page (right column) say it was overruled? Mark OK / PROBLEM and note why.", ""]
    for i in pick:
        k = key[i]
        lines += [f"## {i}: {k['case']}", f"Key (private): overruled by {k['overruling']} ({k['kind']}, {k['trust']}). Scorer: off={results_off.get(i)}, on={results_on.get(i)}", "",
                  f"**Question:** {by.get((i, 'off'), by.get((i, 'on'), {})).get('question', '')}", "",
                  "### Without the locks", by.get((i, "off"), {}).get("answer", "(not run)") or "(no answer text)", "",
                  "### With the locks, as the page would show it", by.get((i, "on"), {}).get("shown", "(not run)") or "(no answer text)", "",
                  "Reader's mark: ____   Note: ____", ""]
    open(out_path, "w", encoding="utf-8").write("\n".join(lines))
    return pick


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--recourse", required=True, help="a Recourse checkout with the patch applied and overruled_register/ exported")
    ap.add_argument("--exam", choices=("criminal", "original"), default="criminal",
                    help="criminal (28 questions about register cases that are in the criminal-law index: the one that can test the live site) or original (50 questions, mostly tax/service/property that the site will refuse)")
    ap.add_argument("--questions", help="override the question file")
    ap.add_argument("--key", help="override the key file")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--arms", default="off,on")
    ap.add_argument("--limit", type=int, default=0, help="only the first N questions (try 3 first)")
    ap.add_argument("--sleep", type=float, default=0.0)
    a = ap.parse_args(argv)
    base = os.path.join(ROOT, "register_exam", "criminal") if a.exam == "criminal" else os.path.join(ROOT, "register_exam")
    a.questions = a.questions or os.path.join(base, "questions.jsonl")
    a.key = a.key or os.path.join(base, "key.json")
    qs = load_questions(a.questions)
    if a.limit:
        qs = qs[: a.limit]
    arms = [x.strip() for x in a.arms.split(",") if x.strip()]
    out_dir = os.path.abspath(a.out_dir)
    key_path = os.path.abspath(a.key)
    raw = run(a.recourse, qs, arms, out_dir, a.sleep)
    qtext = {q["id"]: q["question"] for q in qs}
    for r in raw:
        r["question"] = qtext[r["id"]]
    write_outputs(raw, out_dir)
    print("states:", json.dumps(state_summary(raw)))
    sys.path.insert(0, ROOT)
    from goodlaw import register as R, register_exam as EX
    reg = R.Register.load()
    key = {k: v for k, v in json.load(open(key_path, encoding="utf-8")).items() if k in qtext}
    res = {}
    for name in ("answers_off", "answers_on_model", "answers_on_shown"):
        p = os.path.join(out_dir, name + ".jsonl")
        if os.path.getsize(p):
            table, per = EX.score(reg, EX.read_answers(p), key)
            res[name] = per
            print(name, json.dumps(table))
    if "answers_off" in res and "answers_on_shown" in res:
        reading_sheet(raw, key, res["answers_off"], res["answers_on_shown"], os.path.join(out_dir, "reading_sheet.md"))
        print("reading sheet:", os.path.join(out_dir, "reading_sheet.md"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
