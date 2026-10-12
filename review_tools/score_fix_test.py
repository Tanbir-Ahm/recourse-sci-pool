#!/usr/bin/env python3
"""Scores the fix test's stage F mechanically, exactly as review_data/ruler/FIX_TEST_RULES_v1.md (sections 5 and 6) and FIX_TEST_RULES_v2.md say (frozen: fix_test_rules_v1.freeze, fix_test_rules_v2.freeze),
with the interpretations written in FIX_TEST_RUNBOOK.md before the search. LLM-judged marks only; nothing here is a lawyer's.

TWO STAGES, so that the key is opened only after the marks are in (rules v1 section 4: "the key is opened only after the marks are scored, once"):

  python review_tools/score_fix_test.py marks --pool POOL.json --replies DIR --set fix_test_f_v1.json --out OUT
  python review_tools/score_fix_test.py key   --pool POOL.json --replies DIR --set fix_test_f_v1.json --key fix_test_f_key_v1.json --out OUT      # refuses unless stage 1 is complete and unchanged

Stage 1 (marks only, the key is not opened): coverage (every passage marked by both tools, else INCOMPLETE), reliability (exact agreement of the two tools; under 60% = weak), per version and settlement the top-5 shares
(Yes, useful = Yes or Partly, Misleading, mean grade Misleading 0 / No 1 / Partly 2 / Yes 3) averaged over the scored questions (domains A to J: 27 in the plan, 26 after N12 was dropped before sealing; the three controls are reported apart), each finalist against B on rules 1, 2, 3, 5
and the marks part of rule 6 (look-alike questions), the floors F1, F2, F4 for B and each finalist, the same again without the questions the owner kept as soft overlaps (descriptive, never the decision).
Four settlements: ChatGPT alone, Gemini alone, both with ties to the lower mark, both with ties to the higher mark.
Stage 2 (opens the key, only after stage 1 and only the pool's questions): answerable questions; named authority in each version's top 5 and top 10; known-stale rulings in the top 5; rule 4; the key part of rule 6; the choice (the
passing finalist with the highest mean grade, else B stays); the floors F1 to F4 on the chosen recipe with clear or weak pass; lights per domain; controls apart; the outcome of SEALED_RUN_RULES_v1.md section 7.
Writes OUT/stage1.json, OUT/stage2.json, OUT/key_opened.json and OUT/FIX_TEST_REPORT.md. PRIVATE. Never write the result as "X% accurate".
"""
import argparse
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fix_arms as FA
import fix_test_set as FT
import ingest_llm_reviews as ing
import real30_lights as RL
import real30_score as RS
import score_rerank_arms as SR
import score_sealed_run as SS

BOTH = SS.BOTH
LOOKALIKE_MIS_MARGIN = 0.05            # rules v1 section 5, rule 6: the look-alike Misleading share at least 5 points lower than B's
TIE_ORDER = ("N1", "N2")               # interpretation: an exact tie between two passing finalists goes to the precise trigger (runbook)


def sha(path):
    return SS.sha(path)


def load_checked(pool_path, set_path):
    """The pool and the sealed question file it was made from: the pool must be a stage F pool of exactly those questions."""
    doc = json.load(open(pool_path, encoding="utf-8"))
    run = doc["run"]
    ft = run.get("fix_test") or {}
    public = FT.load(set_path)
    if ft.get("stage") != "F" or not ft.get("finalists"):
        raise SystemExit("refused: this is not the stage F pool of the fix test")
    if ft.get("code_uncommitted"):
        raise SystemExit("refused: the pool was made from uncommitted code")
    if FT.freeze_digest(public) != public["freeze"]["sha256"]:
        raise SystemExit("refused: the question file has changed since its freeze")
    if ft.get("question_freeze_sha256") != public["freeze"]["sha256"]:
        raise SystemExit("refused: the pool was not made from this question file")
    qids = [q["qid"] for q in doc["questions"]]
    if qids != [q["id"] for q in public["questions"]]:
        raise SystemExit(f"refused: the pool holds {len(qids)} questions, the sealed file {len(public['questions'])}, or they differ")
    return doc, run, ft, public


def per_version_tables(pool, runs, versions):
    return SS.arm_table(pool, runs, versions)


def changed_questions(pool, b, v):
    """Questions whose top 5 under v differs from B's (as ordered lists of passage hashes)."""
    out = []
    for q in pool:
        lb, lv = [x["h"] for x in (q["lists"].get(b) or [])[:5]], [x["h"] for x in (q["lists"].get(v) or [])[:5]]
        if lb != lv:
            out.append(q["qid"])
    return out


def lookalike_mis(table, version, ids):
    per = {q: table[BOTH[0]][version][q] for q in ids if table[BOTH[0]][version].get(q)}
    return SS.macro(per, "mis"), len(per)


def marks_rules(pool_scored, runs, b, v, agreement, la_ids):
    """Rules 1, 2, 3, 5 and the marks part of rule 6 for finalist v against B over `pool_scored`."""
    tab = SS.arm_table(pool_scored, runs, [b, v])
    cmp = SS.compare_arms(tab, b, v)
    base = SS.rules_on_marks(cmp, agreement)
    mis_b, n_b = lookalike_mis(tab, b, la_ids)
    mis_v, n_v = lookalike_mis(tab, v, la_ids)
    rule6a = mis_b is not None and mis_v is not None and (mis_b - mis_v) >= LOOKALIKE_MIS_MARGIN - 1e-12
    return {"table": tab, "compare": cmp, "rules": dict(base, **{"rule6a_lookalike_misleading_5_points_lower": rule6a}), "lookalike_mis": {"B": mis_b, "V": mis_v, "questions": min(n_b, n_v)}}


def stage_marks(pool_path, replies, set_path, out):
    doc, run, ft, public = load_checked(pool_path, set_path)
    pool, passages = ing.load_pool(pool_path)
    runs, problems, ev = ing.load_replies(replies, passages, pool)
    keys = sorted(passages)
    marked_by = {p: [t for t in ("ChatGPT", "Gemini") if any(p in runs[k] for k in runs if k[0] == t)] for p in keys}
    missing = [p for p in keys if len(marked_by[p]) < 2]
    pairs = [(next(runs[k][p] for k in runs if k[0] == "ChatGPT" and p in runs[k]), next(runs[k][p] for k in runs if k[0] == "Gemini" and p in runs[k])) for p in keys if len(marked_by[p]) == 2]
    agreement = (sum(a == b for a, b in pairs) / len(pairs)) if pairs else 0.0
    b = FA.B_VERSION
    finalists = ft["finalists"]
    versions = [b] + finalists
    scored = [q for q in pool if q["domain"] != "K"]
    controls = [q for q in pool if q["domain"] == "K"]
    la_ids = [q["qid"] for q in scored if (q.get("meta") or {}).get("look_alike")]
    soft = {q["qid"] for q in scored if (q.get("meta") or {}).get("soft_overlap")}
    res = {"stage": "marks", "pool_sha256": sha(pool_path), "replies_sha256": SS.replies_digest(replies), "set_freeze_sha256": public["freeze"]["sha256"], "versions": versions, "questions": len(pool), "scored_questions": len(scored),
           "controls": [q["qid"] for q in controls], "look_alike_questions": la_ids, "soft_overlap_questions": sorted(soft), "passages": len(keys), "runs": {f"{m}/{o}": len(r) for (m, o), r in sorted(runs.items())},
           "file_problems": len(problems), "coverage_complete": not missing, "passages_not_marked_by_both_tools": len(missing), "tool_agreement_exact": agreement, "reliability": "weak" if agreement < SS.WEAK_AGREEMENT else "ok"}
    tab = SS.arm_table(scored, runs, versions)
    res["settlements"] = {s: {v: {"questions": sum(1 for x in per[v].values() if x), "yes": SS.macro(per[v], "yes"), "useful": SS.macro(per[v], "useful"), "mis": SS.macro(per[v], "mis"), "grade": SS.macro(per[v], "grade")} for v in versions} for s, per in tab.items()}
    res["floors"] = {v: SS.floors(tab, v) for v in versions}
    res["finalists"] = {}
    soft_pool = [q for q in scored if q["qid"] not in soft]
    for v in finalists:
        mr = marks_rules(scored, runs, b, v, agreement, la_ids)
        sens = marks_rules(soft_pool, runs, b, v, agreement, [i for i in la_ids if i not in soft])
        res["finalists"][v] = {"compare": mr["compare"], "marks_rules": mr["rules"], "lookalike_misleading": mr["lookalike_mis"], "changed_top5_questions": changed_questions(scored, b, v),
                               "without_soft_overlaps": {"questions": len(soft_pool), "compare": sens["compare"], "marks_rules": sens["rules"], "lookalike_misleading": sens["lookalike_mis"],
                                                         "floors": SS.floors(SS.arm_table(soft_pool, runs, versions), v)}}
    res["without_soft_overlaps_floors_B"] = SS.floors(SS.arm_table(soft_pool, runs, versions), b)
    # for comparison with the sealed run, which pooled its one control with the other questions: the floors with the controls included (descriptive only)
    tab_all = SS.arm_table(pool, runs, versions)
    res["floors_including_controls"] = {v: {k: SS.floors(tab_all, v)[k] for k in ("F1_useful_lower", "F2_mis_lower", "F2_mis_higher", "F4_yes_lower", "F1", "F2", "F4")} for v in versions}
    # controls apart: what each version put in the top 5 of the questions that have no answer
    f_lo = SR.settle_funcs(runs)[BOTH[0]]
    res["controls_apart"] = {q["qid"]: {v: SS.stats(q, v, f_lo) for v in versions} for q in controls}
    os.makedirs(out, exist_ok=True)
    json.dump(res, open(os.path.join(out, "stage1.json"), "w"), indent=1, default=list)
    return res


def named_rank(q, v, kq):
    items = q["lists"].get(v) or []
    return RS.first_rank(items, set(kq[q["qid"]]["key_docs"]))


def stage_key(pool_path, replies, set_path, key_path, out):
    s1p = os.path.join(out, "stage1.json")
    if not os.path.exists(s1p):
        raise SystemExit("refused: stage 1 (marks) has not been run; the key is opened only after the marks are scored")
    s1 = json.load(open(s1p))
    if s1["pool_sha256"] != sha(pool_path) or s1["replies_sha256"] != SS.replies_digest(replies):
        raise SystemExit("refused: the pool or the replies have changed since stage 1; run stage 1 again and keep both outputs")
    if not s1["coverage_complete"]:
        raise SystemExit(f"refused: {s1['passages_not_marked_by_both_tools']} passages are not marked by both tools; the result would be INCOMPLETE, not scored")
    doc, run, ft, public = load_checked(pool_path, set_path)
    key_all = json.load(open(key_path, encoding="utf-8"))
    if FT.key_digest(key_all) != public["freeze"]["key_sha256"]:
        raise SystemExit("refused: the key has changed since the freeze (its hash differs from the one in the sealed question file)")
    pool, passages = ing.load_pool(pool_path)
    runs, _, _ = ing.load_replies(replies, passages, pool)
    kq = {q["qid"]: key_all["questions"][q["qid"]] for q in pool}               # only the questions of this pool are read out of the key
    del key_all
    b, finalists = FA.B_VERSION, ft["finalists"]
    versions = [b] + finalists
    scored = [q for q in pool if q["domain"] != "K"]
    controls = [q for q in pool if q["domain"] == "K"]
    answerable = [q["qid"] for q in scored if kq[q["qid"]]["reachable"] is True]
    gaps = [q["qid"] for q in scored if kq[q["qid"]]["reachable"] is not True]
    la_ids = [q["qid"] for q in scored if (q.get("meta") or {}).get("look_alike")]
    la_answerable = [i for i in la_ids if i in answerable]
    nm = {v: {q["qid"]: named_rank(q, v, kq) for q in scored if q["qid"] in answerable} for v in versions}
    hits = lambda v, k, ids=None: sum(1 for i, r in nm[v].items() if (ids is None or i in ids) and r is not None and r <= k)

    def stale_in_top5(q, v):
        stale = {x["doc"] for x in kq[q["qid"]]["stale_docs"] if x["counts_as_stale"]}
        return [it for it in (q["lists"].get(v) or [])[:5] if ({it["doc"], *it.get("also", [])} & stale)]
    stale_counts = {v: sum(len(stale_in_top5(q, v)) for q in scored) for v in versions}
    verdicts = {}
    for v in finalists:
        mr = s1["finalists"][v]["marks_rules"]
        rule4 = hits(v, 5) >= hits(b, 5) and stale_counts[v] <= stale_counts[b]
        rule6b = hits(v, 5, la_answerable) > hits(b, 5, la_answerable)
        rule6 = bool(mr["rule6a_lookalike_misleading_5_points_lower"] or rule6b)
        verdicts[v] = {"rule1": mr["rule1_grade_all_four_settlements"], "rule2": mr["rule2_misleading_and_useful_margins"], "rule3": mr["rule3_two_more_questions_better"], "rule4_named_authority_and_stale_not_worse": rule4,
                       "rule5": mr["rule5_reliability_not_weak"], "rule6_helps_the_look_alikes": rule6, "rule6a_marks": mr["rule6a_lookalike_misleading_5_points_lower"], "rule6b_key_authority_top5_on_more_lookalikes": rule6b,
                       "named_top5_lookalikes": {"B": hits(b, 5, la_answerable), "V": hits(v, 5, la_answerable)}, "passes": bool(mr["marks_rules_hold"] and rule4 and rule6)}
    passing = [v for v in finalists if verdicts[v]["passes"]]
    grade = lambda v: s1["settlements"][BOTH[0]][v]["grade"]
    adopted = None
    if passing:
        top = max(grade(v) for v in passing)
        best = [v for v in passing if abs(grade(v) - top) < 1e-12]
        best.sort(key=lambda v: (len(s1["finalists"][v]["changed_top5_questions"]), next((i for i, t in enumerate(TIE_ORDER) if v.startswith(t)), 9)))
        adopted = best[0]
    chosen = adopted or b
    fl = s1["floors"][chosen]
    f3_vals = [1.0 if (nm[chosen][i] is not None and nm[chosen][i] <= 10) else 0.0 for i in answerable]
    f3 = (sum(f3_vals) / len(f3_vals)) if f3_vals else None
    floor_ok = bool(fl["F1"] and fl["F2"] and fl["F4"] and f3 is not None and f3 >= SS.F3_NAMED)
    iv = fl["intervals"]
    kinds = {"F1": SS.clear_or_weak(fl["F1_useful_lower"], iv["F1_useful_lower"], SS.F1_USEFUL, False),
             "F2": "clear pass" if SS.clear_or_weak(fl["F2_mis_lower"], iv["F2_mis_lower"], SS.F2_MIS_LOWER, True) == "clear pass" and SS.clear_or_weak(fl["F2_mis_higher"], iv["F2_mis_higher"], SS.F2_MIS_HIGHER, True) == "clear pass" else "weak pass",
             "F3": SS.clear_or_weak(f3, SR.boot(f3_vals) if f3_vals else None, SS.F3_NAMED, False), "F4": SS.clear_or_weak(fl["F4_yes_lower"], iv["F4_yes_lower"], SS.F4_YES, False)}
    # lights per domain for the chosen recipe (scored questions only)
    f_lo, f_hi = SR.settle_funcs(runs)[BOTH[0]], SR.settle_funcs(runs)[BOTH[1]]
    by_domain = collections.defaultdict(lambda: {"rel": {BOTH[0]: [], BOTH[1]: []}, "cur": []})
    for q in scored:
        k = kq[q["qid"]]
        if k["reachable"] is True:
            for sname, f in ((BOTH[0], f_lo), (BOTH[1], f_hi)):
                rel = RL.question_relevance(q, chosen, lambda qid, n, f=f: f((qid, n)))
                if rel:
                    by_domain[q["domain"]]["rel"][sname].append(rel)
        if any(x["counts_as_stale"] for x in k["stale_docs"]):
            by_domain[q["domain"]]["cur"].append(bool(stale_in_top5(q, chosen)))
    domains = {}
    for d, parts in sorted(by_domain.items()):
        rel = {s: RL.relevance_light(parts["rel"][s]) for s in BOTH}
        cur = RL.currency_light(parts["cur"])
        eligible = floor_ok and all(rel[s][0] in ("green", "amber") for s in BOTH) and cur[0] != "red"
        domains[d] = {"relevance": {s: rel[s][0] for s in BOTH}, "currency": cur[0], "currency_let_through": f"{cur[1]} of {cur[2]}", "eligible": bool(eligible)}
    all_cur = [x for d in by_domain.values() for x in d["cur"]]
    cur_overall = RL.currency_light(all_cur)
    # controls apart, with the key's control type
    controls_apart = {}
    for q in controls:
        controls_apart[q["qid"]] = {"control_type": (q.get("meta") or {}).get("control_type"), "shares_top5_lower_mark": {v: SS.stats(q, v, f_lo) for v in versions},
                                    "stale_in_top5": {v: len(stale_in_top5(q, v)) for v in versions}}
    if adopted is None:
        outcome = "B stays: no finalist satisfies rules 1 to 6 of FIX_TEST_RULES_v1.md section 5"
    else:
        outcome = f"{adopted} replaces B under rules 1 to 6"
    if not floor_ok:
        outcome += "; a floor is missed by the chosen recipe: nothing is connected, and any new final test needs new questions"
    elif not any(x["eligible"] for x in domains.values()):
        outcome += "; floors met but no domain eligible (retrieval is fit, currency is not): extend the register and test on new trap questions; no connection"
    else:
        outcome += "; floors met and at least one domain eligible: the recipe may go to shadow mode in the eligible domains only (never the verified answer path)"
    # descriptive: the same decision without the soft-overlap questions (never the decision itself)
    soft = set(s1["soft_overlap_questions"])
    without = {"questions_left": len([i for i in answerable if i not in soft]),
               "named_authority": {v: {"top5": hits(v, 5, {i for i in answerable if i not in soft}), "top10": hits(v, 10, {i for i in answerable if i not in soft})} for v in versions},
               "marks_rules": {v: s1["finalists"][v]["without_soft_overlaps"]["marks_rules"] for v in finalists},
               "floors_chosen": {k: s1["finalists"][chosen]["without_soft_overlaps"]["floors"][k] for k in ("F1", "F2", "F4")} if adopted else {k: s1["without_soft_overlaps_floors_B"][k] for k in ("F1", "F2", "F4")}}
    res = {"stage": "key", "key_opened_after_marks": True, "answerable": answerable, "gaps": gaps, "controls": [q["qid"] for q in controls], "named_authority": {v: {"top5": hits(v, 5), "top10": hits(v, 10), "answerable": len(answerable)} for v in versions},
           "stale_in_top5": stale_counts, "verdicts": verdicts, "passing": passing, "adopted": adopted, "chosen_recipe": chosen, "floors_chosen": {"F1": fl["F1"], "F2": fl["F2"], "F3": bool(f3 is not None and f3 >= SS.F3_NAMED), "F4": fl["F4"],
           "F3_named_authority_top10": f3, "values": {k: fl[k] for k in ("F1_useful_lower", "F2_mis_lower", "F2_mis_higher", "F4_yes_lower")}, "clear_or_weak": kinds}, "floors_met": floor_ok, "domains": domains,
           "currency_overall": {"light": cur_overall[0], "let_through": f"{cur_overall[1]} of {cur_overall[2]}"}, "controls_apart": controls_apart, "without_soft_overlaps": without, "reliability": s1["reliability"], "outcome": outcome}
    json.dump(res, open(os.path.join(out, "stage2.json"), "w"), indent=1, default=list)
    json.dump({"key_file_sha256": sha(key_path), "questions_read": sorted(kq), "after_stage1_pool_sha256": s1["pool_sha256"]}, open(os.path.join(out, "key_opened.json"), "w"), indent=1)
    write_report(out, s1, res)
    return res


def pct(x):
    return "-" if x is None else f"{100 * x:.0f}%"


def write_report(out, s1, s2):
    b = FA.B_VERSION
    short = lambda v: v.split(" ")[0] if v != b else "B"
    L = ["# Fix test, stage F: report (PRIVATE; LLM-judged: no lawyer has checked any of it)", "", f"**Outcome: {s2['outcome']}**", "",
         f"Reliability: the two tools agree exactly on {pct(s1['tool_agreement_exact'])} of the passages ({s1['reliability']}). Coverage complete: {s1['coverage_complete']}. Scored questions {s1['scored_questions']} (domains A to J); controls apart: {', '.join(s1['controls'])}. "
         f"Chosen recipe: **{s2['chosen_recipe']}**.", "", "## Top-5 shares, averaged over the scored questions", "", "| Settlement | version | Yes | useful | Misleading | mean grade |", "|---|---|---|---|---|---|"]
    for s, per in s1["settlements"].items():
        for v, x in per.items():
            L.append(f"| {s} | {short(v)} | {pct(x['yes'])} | {pct(x['useful'])} | {pct(x['mis'])} | {x['grade']:.2f} |")
    L += ["", "## Each finalist against B (rules of FIX_TEST_RULES_v1.md section 5)", "", "| Finalist | rule 1 grade | rule 2 margins | rule 3 two more questions better | rule 4 named authority and stale | rule 5 reliability | rule 6 look-alikes | passes |", "|---|---|---|---|---|---|---|---|"]
    for v, x in s2["verdicts"].items():
        L.append(f"| {short(v)} | {x['rule1']} | {x['rule2']} | {x['rule3']} | {x['rule4_named_authority_and_stale_not_worse']} | {x['rule5']} | {x['rule6_helps_the_look_alikes']} (marks {x['rule6a_marks']}, key {x['rule6b_key_authority_top5_on_more_lookalikes']}) | **{x['passes']}** |")
    L += ["", "Questions where the finalist is better / worse than B by 0.4 or more in the mean grade of the top 5:", ""]
    for v, x in s1["finalists"].items():
        for s in BOTH:
            c = x["compare"][s]
            L.append(f"- {short(v)}, {s}: better on {c['R_better']}, worse on {c['R_worse']}; top 5 differs from B on {len(x['changed_top5_questions'])} questions")
    L += ["", f"Named authority (answerable questions, {len(s2['answerable'])}): {s2['named_authority']}. Known-stale passages in the top 5: {s2['stale_in_top5']}.", "", "## Floors on the chosen recipe", "", "| Floor | Value | Needed | Met | |", "|---|---|---|---|---|"]
    v = s2["floors_chosen"]
    L += [f"| F1 useful share | {pct(v['values']['F1_useful_lower'])} | at least {pct(SS.F1_USEFUL)} | {v['F1']} | {v['clear_or_weak']['F1']} |",
          f"| F2 Misleading share | {pct(v['values']['F2_mis_lower'])} (ties lower), {pct(v['values']['F2_mis_higher'])} (ties higher) | at most {pct(SS.F2_MIS_LOWER)} and {pct(SS.F2_MIS_HIGHER)} | {v['F2']} | {v['clear_or_weak']['F2']} |",
          f"| F3 named authority in the top 10 | {pct(v['F3_named_authority_top10'])} of {len(s2['answerable'])} answerable | at least {pct(SS.F3_NAMED)} | {v['F3']} | {v['clear_or_weak']['F3']} |",
          f"| F4 direct (Yes) share | {pct(v['values']['F4_yes_lower'])} | at least {pct(SS.F4_YES)} | {v['F4']} | {v['clear_or_weak']['F4']} |", "",
          "## Domains (chosen recipe)", "", "| Domain | relevance (lower / higher ties) | currency | eligible |", "|---|---|---|---|"]
    for d, x in s2["domains"].items():
        L.append(f"| {d} | {x['relevance'][BOTH[0]]} / {x['relevance'][BOTH[1]]} | {x['currency']} ({x['currency_let_through']}) | {x['eligible']} |")
    L += ["", f"Currency overall (without the register): {s2['currency_overall']}.", "", "## Controls (reported apart; the search should not look confident here)", ""]
    for q, x in s2["controls_apart"].items():
        L.append(f"- {q} ({x['control_type']}): " + "; ".join(f"{short(v)} Yes {pct(s['yes']) if s else '-'}, useful {pct(s['useful']) if s else '-'}, Misleading {pct(s['mis']) if s else '-'}" for v, s in x["shares_top5_lower_mark"].items()))
    L += ["", "Floors F1 / F2 / F4 with the three controls pooled in as well (the sealed run's convention; descriptive only): " + "; ".join(f"{short(v)} useful {pct(x['F1_useful_lower'])}, Misleading {pct(x['F2_mis_lower'])}/{pct(x['F2_mis_higher'])}, Yes {pct(x['F4_yes_lower'])}" for v, x in s1["floors_including_controls"].items())]
    w = s2["without_soft_overlaps"]
    L += ["", "## The same without the questions kept as soft overlaps (descriptive only; the decision above uses all scored questions)", "",
          f"Questions left (answerable): {w['questions_left']}. Named authority: {w['named_authority']}. Marks rules per finalist: {w['marks_rules']}. Floors of the chosen recipe F1/F2/F4: {w['floors_chosen']}.", "",
          "Never to be written as 'X% accurate'. Mr. Advocate reads every passage marked Misleading by any run and a random 20 of the others before anything leaves the project."]
    open(os.path.join(out, "FIX_TEST_REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stage", choices=["marks", "key"])
    ap.add_argument("--pool", required=True)
    ap.add_argument("--replies", required=True)
    ap.add_argument("--set", default=FT.DEFAULT_SET)
    ap.add_argument("--key", default=FT.DEFAULT_KEY)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.stage == "marks":
        s1 = stage_marks(a.pool, a.replies, a.set, a.out)
        print(f"stage 1 written; coverage complete {s1['coverage_complete']}; reliability {s1['reliability']} (agreement {s1['tool_agreement_exact']:.1%})")
        return 0 if s1["coverage_complete"] else 2
    s2 = stage_key(a.pool, a.replies, a.set, a.key, a.out)
    print(s2["outcome"], "| chosen:", s2["chosen_recipe"], "| floors met:", s2["floors_met"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
