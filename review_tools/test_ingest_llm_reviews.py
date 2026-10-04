"""Tests for ingest_llm_reviews.py on SYNTHETIC replies only: nothing here is a real review result.
Uses the saved pool (review_data/pool_all.json) for passage numbers and texts; builds any review sheet it needs itself.
Run: python review_tools/test_ingest_llm_reviews.py   (needs openpyxl)"""
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ingest_llm_reviews as ing
import review_common as rc

POOL = rc.DEFAULT_POOL
pool_all, passages_all = ing.load_pool(POOL)
first = lambda q: dict(q, rows=rc.rows_of(q, False))                  # the first batch of a question
topup = lambda q: dict(q, rows=rc.rows_of(q, True))                   # its top-up batch
pool = [first(q) for q in pool_all]                                   # the original 175 passages
TOTAL = sum(len(q["rows"]) for q in pool)

R = lambda qid, no: ing.MARKS[(no + int(qid[1:])) % 4]               # the synthetic "truth" rule
other = lambda m: ing.MARKS[(ing.MARKS.index(m) + 1) % 4]

FAILS = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{detail}]"))
    if not cond:
        FAILS.append(name)


def entry(r, mark, evidence=None):
    words = r["text"].split()
    return {"no": r["n"], "mark": mark, "evidence": evidence if evidence is not None else " ".join(words[:6]), "reason": "synthetic", "confidence": "high"}


def reply_obj(q, mark_fn, drop=(), fake=()):
    marks = []
    for r in q["rows"]:
        if r["n"] in drop:
            continue
        marks.append(entry(r, mark_fn(q["qid"], r["n"]), "this sentence is not in the passage at all" if r["n"] in fake else None))
    return {"question_id": q["qid"], "marks": marks, "good_answer_present": "Yes", "best_passage_no": 1, "caveats": ""}


def write(folder, qid, order, model, obj, style="plain"):
    s = json.dumps(obj, indent=1)
    if style == "fence":
        s = "Here is my answer:\n```json\n" + s + "\n```\nHope that helps."
    elif style == "prose":
        s = "Sure! " + s + "\nLet me know if you need more."
    elif style == "comments":
        s = s.rstrip("}").rstrip() + ",\n}"                           # trailing comma before the final brace
        s = s.replace('"best_passage_no": 1,', '"best_passage_no": 1, // best one')
    elif style == "truncated":
        s = s[: len(s) // 2]
    with open(os.path.join(folder, f"{qid}_{order}_{model}.txt"), "w", encoding="utf-8") as fh:
        fh.write(s)


def make_sheet(path, marks):
    """A minimal review sheet in the layout the reader expects: sheet 'Review', Q in column A, No. in B, mark in E, plus a banner row."""
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Review"
    ws.append(["Q", "No.", "Judgment", "Passage text", "Your mark", "Comment", "Same text also in", "Ref"])
    ws.append(["Q01", None, "Plain English", "QUESTION: a banner row has no number", None, None, None, None])
    for (qid, no), mk in sorted(marks.items()):
        ws.append([qid, no, "j", "t", mk, None, None, "ref"])
    wb.save(path)


# ---------------------------------------------------------------- the pool itself
check("the pool holds the 175 original passages plus the 24 top-up passages", TOTAL == 175 and len(passages_all) == 199, (TOTAL, len(passages_all)))
check("(question, number) is unique across both batches and top-up numbers continue after the first batch's",
      len(passages_all) == len({(q["qid"], r["n"]) for q in pool_all for r in q["rows"]})
      and all(r["n"] > max(x["n"] for x in rc.rows_of(q, False)) for q in pool_all for r in rc.rows_of(q, True)))

# ---------------------------------------------------------------- parser edge cases
good = {"question_id": "Q01", "marks": [{"no": 1, "mark": "Yes", "evidence": "x", "reason": "y", "confidence": "high"}]}
js = json.dumps(good)
for label, text, want_ok in [("plain", js, True), ("fenced", f"```json\n{js}\n```", True), ("prose around", f"Sure.\n{js}\nDone.", True),
                             ("trailing comma", js.replace("}]}", "},]}"), True), ("truncated", js[:40], False), ("not json", "I cannot do that", False),
                             ("empty", "", False), ("comment line", js.replace('{"question_id"', '// hello\n{"question_id"'), True)]:
    obj, note = ing.parse_reply(text)
    check(f"parse_reply: {label}", (obj is not None) == want_ok, note)
check("norm_mark aliases", ing.norm_mark("partially") == "Partly" and ing.norm_mark(" YES. ") == "Yes" and ing.norm_mark("Maybe") is None)
k, po = ing.cohen_kappa(["a", "b", "a", "b"], ["a", "b", "a", "b"]); check("kappa perfect", abs(k - 1) < 1e-9 and po == 1)
k, po = ing.cohen_kappa(["a", "a", "b", "b"], ["a", "b", "a", "b"]); check("kappa chance-level = 0", abs(k) < 1e-9 and po == 0.5, f"{k} {po}")
check("kappa degenerate -> None", ing.cohen_kappa(["a", "a"], ["a", "a"])[0] is None)
check("reply file names: Q3_A and q03_b are accepted, Qxx_C is not",
      ing.NAME_RE.match("Q3_A_x.txt") and ing.NAME_RE.match("q03_b_x.json") and ing.NAME_RE.match("Q03_TB_x.md") and not ing.NAME_RE.match("Q03_C_x.txt"))

# ---------------------------------------------------------------- scenario 1: two models, clean, known flips, a sheet from a person
tmp = tempfile.mkdtemp(prefix="SYNTHETIC_")
try:
    rep, out = f"{tmp}/replies", f"{tmp}/out"
    os.makedirs(rep)
    flips = {(pool[0]["qid"], pool[0]["rows"][i]["n"]) for i in range(5)} | {(pool[4]["qid"], pool[4]["rows"][i]["n"]) for i in range(2)}      # exactly 7 flipped passages
    flip = lambda qid, no: other(R(qid, no)) if (qid, no) in flips else R(qid, no)
    for q in pool:
        write(rep, q["qid"], "A", "SynM1", reply_obj(q, R), "fence")
        write(rep, q["qid"], "B", "SynM1", reply_obj(q, R), "prose")
        write(rep, q["qid"], "A", "SynM2", reply_obj(q, flip), "comments" if q["qid"] == "Q02" else "plain")
        write(rep, q["qid"], "B", "SynM2", reply_obj(q, R), "plain")
    exp_flips = {(pool[1]["qid"], pool[1]["rows"][i]["n"]) for i in range(3)}
    sheet = f"{tmp}/sheet_SYNTHETIC.xlsx"
    make_sheet(sheet, {(q["qid"], r["n"]): (other(R(q["qid"], r["n"])) if (q["qid"], r["n"]) in exp_flips else R(q["qid"], r["n"])) for q in pool for r in q["rows"]})
    res = ing.main(["--replies", rep, "--out", out, "--human", sheet, "--label", "SYNTHETIC TEST"])        # no --pool: the saved pool is used
    runs, problems, ev, cons, pair = res["runs"], res["problems"], res["ev"], res["cons"], res["pair"]
    check("all four runs found", sorted(runs) == [("SynM1", "A"), ("SynM1", "B"), ("SynM2", "A"), ("SynM2", "B")])
    check("each run has all 175 marks", all(len(v) == TOTAL for v in runs.values()), {k: len(v) for k, v in runs.items()})
    check("evidence: every quote found", ev["found"] == ev["marks"] == 4 * TOTAL and ev["not_found"] == 0, dict(ev))
    pm = {(p["a"], p["b"]): p for p in pair}
    p = pm[("SynM1/A", "SynM1/B")]; check("same model identical -> agree 1.0, kappa 1.0", p["agree4"] == 1.0 and abs(p["kappa4"] - 1) < 1e-9 and p["kind"] == "same model, A vs B")
    p = pm[("SynM1/A", "SynM2/A")]; check("7 flips -> agree (175-7)/175", abs(p["agree4"] - (TOTAL - 7) / TOTAL) < 1e-9 and p["n"] == TOTAL and p["kind"] == "different models", p)
    fp = sorted(flips)[0]
    check("consensus uses plurality, flipped passage share 0.75", cons[fp]["mark"] == R(*fp) and abs(cons[fp]["share"] - 0.75) < 1e-9, cons[fp])
    for vr in res["var_rows"]:                                           # independent recomputation (consensus == R wherever it was judged)
        v = vr["variant"]
        per_q = []
        for q in pool:
            ms = [R(q["qid"], r["n"]) for r in q["rows"] if (v in r["variants"] if v.startswith(("S ", "M ")) else r["variants"].get(v, 99) <= 5)]
            if ms:
                per_q.append(sum(m == "Yes" for m in ms) / len(ms))
        check(f"variant '{v}' Yes share matches an independent loop", abs(vr["yes"] - sum(per_q) / len(per_q)) < 1e-9, (vr["yes"], sum(per_q) / len(per_q)))
    name, label_h, e = res["experts"][0]
    check("a person's sheet: 3 flips -> agree (175-3)/175, labelled human-judged (not expert-checked)", e["n"] == TOTAL and abs(e["agree4"] - (TOTAL - 3) / TOTAL) < 1e-9 and label_h == "human-judged (not a lawyer)", e)
    summ = open(f"{out}/llm_summary.md", encoding="utf-8").read()
    check("summary says LLM-judged and human-judged, and never expert-checked here", "LLM-judged" in summ and "human-judged (not a lawyer)" in summ and "expert-checked" not in summ and "SYNTHETIC TEST" in summ)
    res_e = ing.main(["--replies", rep, "--out", f"{tmp}/out_e", "--expert", sheet])
    check("a lawyer's sheet passed with --expert is labelled expert-checked", res_e["experts"][0][1] == "expert-checked" and "expert-checked" in open(f"{tmp}/out_e/llm_summary.md", encoding="utf-8").read())
    check("csv written with a source column", open(f"{out}/llm_marks.csv", encoding="utf-8").read().count("LLM-judged") == len(passages_all))
    check("'comments' style file (Q02 SynM2 A) parsed", ("SynM2", "A") in runs and any(k[0] == "Q02" for k in runs[("SynM2", "A")]))
    # a file named Q3_A_... is the same as Q03_A_...
    rep_q3 = f"{tmp}/replies_q3"
    os.makedirs(rep_q3)
    q3 = next(q for q in pool if q["qid"] == "Q03")
    with open(f"{rep_q3}/Q3_A_SynM9.txt", "w", encoding="utf-8") as fh:
        json.dump(reply_obj(q3, R), fh)
    res_q3 = ing.main(["--replies", rep_q3, "--out", f"{tmp}/out_q3"])
    check("a file named Q3_A_... is read as Q03", len(res_q3["runs"][("SynM9", "A")]) == len(q3["rows"]) and all(k[0] == "Q03" for k in res_q3["runs"][("SynM9", "A")]))
    # a reply saved as ...Gemini.txt.txt (a hidden extension added twice) belongs to the same tool as ...Gemini.txt
    rep_dbl = f"{tmp}/replies_dbl"
    os.makedirs(rep_dbl)
    for name in ("Q03_A_SynM8.txt", "Q03_B_SynM8.txt.txt", "Q03_TA_SynM8.json.txt"):
        with open(f"{rep_dbl}/{name}", "w", encoding="utf-8") as fh:
            json.dump(reply_obj(q3 if "_TA_" not in name else topup(next(x for x in pool_all if x["qid"] == "Q03")), R), fh)
    res_dbl = ing.main(["--replies", rep_dbl, "--out", f"{tmp}/out_dbl"])
    check("a doubled file extension does not turn one tool into two", sorted({m for m, _ in res_dbl["runs"]}) == ["SynM8"] and sorted(o for _, o in res_dbl["runs"]) == ["A", "B", "TA"], sorted(res_dbl["runs"]))

    # ---------------------------------------------------------------- scenario 2: messy third model
    q3, q5, q7, q9 = pool[2], pool[4], pool[6], pool[8]
    fake_nos = {q3["rows"][0]["n"], q3["rows"][1]["n"], q3["rows"][2]["n"]}
    drop_nos = {q5["rows"][0]["n"], q5["rows"][3]["n"]}
    rep3 = f"{tmp}/replies3"
    os.makedirs(rep3)
    write(rep3, q3["qid"], "A", "SynM3", reply_obj(q3, R, fake=fake_nos))
    write(rep3, q5["qid"], "A", "SynM3", reply_obj(q5, R, drop=drop_nos))
    write(rep3, q7["qid"], "A", "SynM3", reply_obj(q7, R), "truncated")
    bad = reply_obj(q9, R); bad["marks"][0]["mark"] = "Maybe"; bad["marks"][1]["mark"] = "partially"; bad["marks"][2]["mark"] = ""
    write(rep3, q9["qid"], "A", "SynM3", bad)
    write(rep3, "Q11", "A", "SynM3", reply_obj(pool[10], R))
    dup = open(f"{rep3}/Q11_A_SynM3.txt", encoding="utf-8").read()
    with open(f"{rep3}/notes.txt", "w") as fh:
        fh.write("stray file")
    with open(f"{rep3}/Q99_A_SynM3.txt", "w") as fh:
        fh.write(dup)
    wrongq = reply_obj(pool[11], R); wrongq["question_id"] = "Q03"
    write(rep3, "Q12", "A", "SynM3", wrongq)
    res3 = ing.main(["--replies", rep3, "--out", f"{tmp}/out3", "--label", "SYNTHETIC TEST 2"])
    txt = "\n".join(f"{a}: {b}" for a, b in res3["problems"])
    check("invented quotes: exactly 3 detected", res3["ev"]["not_found"] == 3 and sum("invented" in b for _, b in res3["problems"]) == 3, dict(res3["ev"]))
    check("missing passages listed", f"passages not marked: {sorted(drop_nos)}" in txt, txt)
    check("truncated reply reported, run continues", "Q07_A_SynM3.txt: no valid JSON" in txt and not any(k[0] == "Q07" for k in res3["runs"][("SynM3", "A")]))
    check("bad marks reported, 'partially' accepted as Partly", "mark 'Maybe'" in txt and "mark ''" in txt and res3["runs"][("SynM3", "A")][(q9["qid"], q9["rows"][1]["n"])] == "Partly")
    check("stray file and unknown question skipped", "notes.txt: file name does not match" in txt and "Q99_A_SynM3.txt: unknown question" in txt)
    check("mismatched question_id skipped", "reply says question_id=Q03 but file is Q12" in txt and not any(k[0] == "Q12" for k in res3["runs"][("SynM3", "A")]))
    check("passages with no votes are 'unjudged', not crashes", sum(1 for c in res3["cons"].values() if c["mark"] is None) > 0)
    check("variant table still produced with unjudged slots counted", all("unjudged" in r for r in res3["var_rows"]) and any(r["unjudged"] > 0 for r in res3["var_rows"]))

    def judged_questions(v):          # independent count: questions where this version has at least one marked passage
        n = 0
        for q in pool:
            marks = [res3["cons"][(q["qid"], r["n"])]["mark"] for r in q["rows"] if v in r["variants"] and (v.startswith(("S ", "M ")) or r["variants"][v] <= 5)]
            n += any(m not in (None, "split") for m in marks)
        return n
    check("'Questions judged' counts only questions where the version has a marked passage (not every question in the pool)",
          all(vr["questions"] == judged_questions(vr["variant"]) for vr in res3["var_rows"]) and any(vr["questions"] < len(pool) for vr in res3["var_rows"]),
          [(vr["variant"], vr["questions"], judged_questions(vr["variant"])) for vr in res3["var_rows"]])

    # ---------------------------------------------------------------- scenario 3: the top-up batch
    rep4 = f"{tmp}/replies4"
    os.makedirs(rep4)
    for q in pool_all:
        write(rep4, q["qid"], "A", "SynM1", reply_obj(first(q), R), "plain")
        new = topup(q)
        if new["rows"]:
            write(rep4, q["qid"], "TA", "SynM1", reply_obj(new, R), "fence")
            if len(new["rows"]) > 1:
                write(rep4, q["qid"], "TB", "SynM1", reply_obj(dict(new, rows=new["rows"][::-1]), R), "prose")
    res4 = ing.main(["--replies", rep4, "--out", f"{tmp}/out4", "--label", "SYNTHETIC TEST 3"])
    runs4 = res4["runs"]
    check("clean batches raise no problems", res4["problems"] == [] or all("extracted" in b for _, b in res4["problems"]), [b for _, b in res4["problems"]][:3])
    check("main, top-up A and top-up B runs are told apart", sorted(runs4) == [("SynM1", "A"), ("SynM1", "TA"), ("SynM1", "TB")])
    check("each run covers exactly its own batch", len(runs4[("SynM1", "A")]) == 175 and len(runs4[("SynM1", "TA")]) == 24 and len(runs4[("SynM1", "TB")]) == 21)
    check("runs on different batches are never compared with each other", not any(p["a"].endswith("/TA") and p["b"].endswith("/A") for p in res4["pair"]))
    check("every passage of both batches ends with its consensus mark", all(res4["cons"][p]["mark"] == R(*p) for p in passages_all))
    for vr in res4["var_rows"]:
        v = vr["variant"]
        per_q = []
        for q in pool_all:
            ms = [R(q["qid"], r["n"]) for r in q["rows"] if (v in r["variants"] if v.startswith(("S ", "M ")) else r["variants"].get(v, 99) <= 5)]
            if ms:
                per_q.append(sum(m == "Yes" for m in ms) / len(ms))
        check(f"variant '{v}' Yes share matches an independent loop ({'everything it showed' if v.startswith(('S ', 'M ')) else 'top 5'})", abs(vr["yes"] - sum(per_q) / len(per_q)) < 1e-9)
    check("the site's shown set and my top 6 both appear in the scoring table", {"S site shown", "M mine top 6"} <= {vr["variant"] for vr in res4["var_rows"]})
    check("the site's shown set is scored on every passage it showed, not a top 5",
          next(vr for vr in res4["var_rows"] if vr["variant"] == "S site shown")["top5_slots"] == sum(1 for q in pool_all for r in q["rows"] if "S site shown" in r["variants"]))
    # a sheet covering top-up numbers is read too
    sheet_top = f"{tmp}/sheet_top_SYNTHETIC.xlsx"
    make_sheet(sheet_top, {(q["qid"], r["n"]): R(q["qid"], r["n"]) for q in pool_all for r in rc.rows_of(q, True)})
    res_h = ing.main(["--replies", rep4, "--out", f"{tmp}/out_h", "--human", sheet_top])
    check("a top-up sheet is compared on the 24 top-up passages", res_h["experts"][0][2]["n"] == 24 and res_h["experts"][0][2]["agree4"] == 1.0)

    # wrong-batch and missing-passage handling
    rep5 = f"{tmp}/replies5"
    os.makedirs(rep5)
    q9a = next(q for q in pool_all if q["qid"] == "Q09"); new9 = topup(q9a)
    q3a = next(q for q in pool_all if q["qid"] == "Q03")
    write(rep5, "Q09", "TA", "SynM2", reply_obj(dict(new9, rows=new9["rows"][1:]), R))                                  # one new passage left out
    write(rep5, "Q03", "A", "SynM2", reply_obj(dict(q3a, rows=rc.rows_of(q3a, False) + rc.rows_of(q3a, True)), R))      # a main file that also marks top-up numbers
    write(rep5, "Q01", "TA", "SynM2", reply_obj(dict(topup(q3a), qid="Q01"), R))                                       # Q01 has no top-up passages
    res5 = ing.main(["--replies", rep5, "--out", f"{tmp}/out5", "--label", "SYNTHETIC TEST 4"])
    txt5 = "\n".join(f"{a}: {b}" for a, b in res5["problems"])
    check("a top-up reply that leaves out a passage is reported with its number", f"passages not marked: [{new9['rows'][0]['n']}]" in txt5)
    check("a main-batch reply that marks top-up numbers is reported", "is not part of this batch for Q03" in txt5)
    check("a top-up reply for a question without new passages is refused", "Q01 has no top-up passages" in txt5)

    # ---------------------------------------------------------------- the sensitivity table, against numbers worked out by hand
    # One question with four passages (all in A's top 5); version C shows passages 1 and 2 only; a second question that only A covers.
    row = lambda n, **v: {"n": n, "variants": v}
    spool = [dict(qid="Q01", kind="lay", rows=[row(1, **{"A today": 1, "C rewrite": 1}), row(2, **{"A today": 2, "C rewrite": 2}), row(3, **{"A today": 3}), row(4, **{"A today": 4})]),
             dict(qid="Q02", kind="legal", rows=[row(1, **{"A today": 1}), row(2, **{"A today": 2})])]
    spass = {(q["qid"], r["n"]): {} for q in spool for r in q["rows"]}
    sruns = {("M1", "A"): {("Q01", 1): "Yes", ("Q01", 2): "Partly", ("Q01", 3): "Yes", ("Q01", 4): "No", ("Q02", 1): "Yes", ("Q02", 2): "Yes"},
             ("M1", "B"): {("Q01", 1): "Yes", ("Q01", 2): "Yes", ("Q01", 3): "Partly", ("Q01", 4): "No", ("Q02", 1): "No", ("Q02", 2): "Yes"}}
    sens = {r["variant"]: r for r in ing.sensitivity(sruns, spass, spool)}
    a, c = sens["A today"], sens["C rewrite"]
    close = lambda x, y: x is not None and abs(x - y) < 1e-9
    # Q01 for A: agreed -> passages 1 (Yes) and 4 (No) only = 0.5; lower -> Yes, Partly, Partly, No = 0.25; higher -> Yes, Yes, Yes, No = 0.75
    # Q02 for A: agreed -> passage 2 (Yes) only = 1.0; lower -> No, Yes = 0.5; higher -> Yes, Yes = 1.0.   Average over both questions:
    check("agreed-only Yes share for A is the average of 0.5 and 1.0", close(a["cells"]["agreed"]["yes"], 0.75), a["cells"]["agreed"])
    check("'ties to the lower mark' keeps every disagreement and settles it the unfavourable way (0.25 and 0.5)", close(a["cells"]["lower"]["yes"], 0.375), a["cells"]["lower"])
    check("'ties to the higher mark' settles it the favourable way (0.75 and 1.0)", close(a["cells"]["higher"]["yes"], 0.875), a["cells"]["higher"])
    check("each run alone is scored on that run's own marks (run A: 0.5 and 1.0; run B: 0.5 and 0.5)", close(a["cells"]["run M1/A"]["yes"], 0.75) and close(a["cells"]["run M1/B"]["yes"], 0.5), (a["cells"]["run M1/A"], a["cells"]["run M1/B"]))
    check("the range over single runs is reported lowest to highest", close(a["runs_yes"][0], 0.5) and close(a["runs_yes"][1], 0.75), a["runs_yes"])
    check("Yes-or-Partly share under 'agreed' for Q01 and Q02 is computed over the same passages (1 of 2 and 1 of 1)", close(a["cells"]["agreed"]["useful"], 0.75), a["cells"]["agreed"])
    check("a version marked on one question reports one question judged, the baseline two", c["questions"] == 1 and a["questions"] == 2, (c["questions"], a["questions"]))
    # C on Q01 (passages 1 and 2): agreed -> [Yes] = 1.0 vs A on Q01 0.5; lower -> Yes, Partly = 0.5 vs 0.25; higher -> 1.0 vs 0.75;
    # run A -> Yes, Partly = 0.5 vs A's 0.5 (Yes, Partly, Yes, No); run B -> Yes, Yes = 1.0 vs 0.5
    check("against the baseline on the SAME questions: above in 4, equal in 1, below in 0", (c["above"], c["equal"], c["below"]) == (4, 1, 0), (c["above"], c["equal"], c["below"]))
    check("the baseline row says so and is not compared with itself", a["is_baseline"] and (a["above"], a["equal"], a["below"]) == (0, 0, 0))
    one = ing.sensitivity({("M1", "A"): sruns[("M1", "A")]}, spass, spool)
    check("with a single run the 'agreed', 'lower', 'higher' and run columns all coincide", all(close(r["cells"]["agreed"]["yes"], r["cells"]["lower"]["yes"]) and close(r["cells"]["lower"]["yes"], r["cells"]["higher"]["yes"]) for r in one))
    res_s = ing.main(["--replies", rep5, "--out", f"{tmp}/out_s", "--label", "SYNTHETIC TEST 5"])
    check("the summary has the sensitivity section only when there is more than one run",
          "## Sensitivity" not in open(f"{tmp}/out_s/llm_summary.md", encoding="utf-8").read() or len(res_s["runs"]) > 1)
    res_two = ing.main(["--replies", rep4, "--out", f"{tmp}/out_two"])
    check("with several runs the summary gets the sensitivity table and a CSV", "## Sensitivity" in open(f"{tmp}/out_two/llm_summary.md", encoding="utf-8").read() and os.path.exists(f"{tmp}/out_two/llm_sensitivity.csv"))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("\nALL PASSED" if not FAILS else f"\nFAILED: {FAILS}")
sys.exit(1 if FAILS else 0)
