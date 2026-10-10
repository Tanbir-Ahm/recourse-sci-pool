#!/usr/bin/env python3
"""Scores the sealed run mechanically, exactly as review_data/ruler/SEALED_RUN_RULES_v1.md says (frozen: sealed_run_rules_v1.freeze). LLM-judged marks only; nothing here is a lawyer's.

TWO STAGES, so that the key is opened only after the marks are in (rules, section 8):

  python review_tools/score_sealed_run.py marks --pool POOL.json --replies DIR --out OUT          # stage 1: marks only; the key is not opened
  python review_tools/score_sealed_run.py key   --pool POOL.json --replies DIR --out OUT --key real30_key_v1.json [--half sealed]     # stage 2: refuses unless stage 1 is complete and unchanged

Stage 1: coverage (every passage marked by both tools, else INCOMPLETE), reliability (the two tools' exact agreement; under 60% = weak), per arm and settlement the top-5 shares (Yes, useful = Yes or Partly,
Misleading, mean grade Misleading 0 / No 1 / Partly 2 / Yes 3, each averaged over questions the way the tuning-half comparators were), the floors F1, F2, F4 for both arms, the marks-based parts (1, 2, 3, 5) of the
choice between the re-rankers, the safety nets' numbers. Four settlements: ChatGPT alone, Gemini alone, both with ties to the lower mark, both with ties to the higher mark.
Stage 2 (opens the key, tuning or sealed ids only): which questions are answerable; the named authority in each arm's top 5 and top 10; known-stale rulings in the top 5; rule 4; the choice of arm (D1); the floors on the
chosen arm including F3 (D2); the safety-net rule (D3); relevance and currency lights per domain (the sealed question alone, and with the tuning half's if --tuning-pool and --tuning-replies are given); domain
eligibility; the outcome row of section 7. Writes OUT/stage1.json, OUT/stage2.json and OUT/SEALED_RUN_REPORT.md. PRIVATE.
"""
import argparse
import collections
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ingest_llm_reviews as ing
import real30_lights as RL
import real30_score as RS
import score_rerank_arms as SR

GRADE = {"Misleading": 0, "No": 1, "Partly": 2, "Yes": 3}
NAMES = {"a": "A today", "r": "R challenger re-ranker", "s": "S site shown", "na": "M safety net", "nr": "M safety net (challenger)"}
BOTH = ("both, ties to the lower mark", "both, ties to the higher mark")
# thresholds of SEALED_RUN_RULES_v1.md (frozen); [Guessing]
F1_USEFUL, F2_MIS_LOWER, F2_MIS_HIGHER, F3_NAMED, F4_YES = 0.70, 0.15, 0.10, 0.60, 0.25
R_MIS_MARGIN, R_USEFUL_MARGIN, R_Q_DELTA, R_Q_MARGIN = 0.02, 0.02, 0.4, 2
WEAK_AGREEMENT = 0.60
NET_MIS, NET_USEFUL, NET_YES_ALL = 0.05, 0.55, 5


def sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def replies_digest(folder):
    h = hashlib.sha256()
    for fn in sorted(os.listdir(folder)):
        h.update(fn.encode())
        h.update(open(os.path.join(folder, fn), "rb").read())
    return h.hexdigest()


def stats(q, version, f):
    """One question, one version, one settlement: shares over the passages it put in its top 5 (everything it showed, for S and M sets) that have a mark. None if it has none."""
    rows = RL.slots(q, version)
    judged = [(r, f((q["qid"], r["n"]))) for r in rows]
    judged = [(r, m) for r, m in judged if m in GRADE]
    if not judged:
        return None
    n = len(judged)
    ranks = sorted(r["variants"][version] for r, m in judged if m == "Yes")
    return {"n": n, "yes": sum(m == "Yes" for _, m in judged) / n, "useful": sum(m in ("Yes", "Partly") for _, m in judged) / n, "mis": sum(m == "Misleading" for _, m in judged) / n,
            "grade": sum(GRADE[m] for _, m in judged) / n, "mis3": any(m == "Misleading" and r["variants"][version] <= 3 for r, m in judged), "first_yes": ranks[0] if ranks else None}


def macro(per_q, key):
    v = [s[key] for s in per_q.values() if s]
    return sum(v) / len(v) if v else None


def arm_table(pool, runs, versions):
    """{settlement: {version: {qid: stats}}}"""
    out = {}
    for name, f in SR.settle_funcs(runs).items():
        out[name] = {v: {q["qid"]: stats(q, v, f) for q in pool} for v in versions}
    return out


def compare_arms(table, a, r):
    """Rules 1 to 3 on the marks, per settlement, over the questions both arms have marks for."""
    res = {}
    for name, per in table.items():
        common = [q for q in per[a] if per[a][q] and per[r].get(q)]
        pa = {q: per[a][q] for q in common}
        pr = {q: per[r][q] for q in common}
        d = {q: pr[q]["grade"] - pa[q]["grade"] for q in common}
        res[name] = {"questions": len(common), "A": {k: macro(pa, k) for k in ("yes", "useful", "mis", "grade")}, "R": {k: macro(pr, k) for k in ("yes", "useful", "mis", "grade")},
                     "R_better": sorted(q for q in common if d[q] >= R_Q_DELTA), "R_worse": sorted(q for q in common if d[q] <= -R_Q_DELTA)}
    return res


def rules_on_marks(cmp, agreement):
    """Rules 1, 2, 3, 5 of section 5 (rule 4 needs the key)."""
    ok1 = all(c["R"]["grade"] is not None and c["R"]["grade"] >= c["A"]["grade"] for c in cmp.values())
    ok2 = all(cmp[s]["R"]["mis"] <= cmp[s]["A"]["mis"] + R_MIS_MARGIN and cmp[s]["R"]["useful"] >= cmp[s]["A"]["useful"] - R_USEFUL_MARGIN for s in BOTH)
    ok3 = all(len(cmp[s]["R_better"]) >= len(cmp[s]["R_worse"]) + R_Q_MARGIN for s in BOTH)
    ok5 = agreement >= WEAK_AGREEMENT
    return {"rule1_grade_all_four_settlements": ok1, "rule2_misleading_and_useful_margins": ok2, "rule3_two_more_questions_better": ok3, "rule5_reliability_not_weak": ok5, "marks_rules_hold": ok1 and ok2 and ok3 and ok5}


def floors(table, version):
    """F1, F2, F4 for one arm (F3 needs the key)."""
    lo, hi = table[BOTH[0]][version], table[BOTH[1]][version]
    f1, f2l, f2h, f4 = macro(lo, "useful"), macro(lo, "mis"), macro(hi, "mis"), macro(lo, "yes")
    val = {"useful": [x["useful"] for x in lo.values() if x], "yes": [x["yes"] for x in lo.values() if x]}
    val_h = [x["mis"] for x in hi.values() if x]
    val_l = [x["mis"] for x in lo.values() if x]
    return {"F1_useful_lower": f1, "F2_mis_lower": f2l, "F2_mis_higher": f2h, "F4_yes_lower": f4,
            "F1": f1 is not None and f1 >= F1_USEFUL, "F2": f2l is not None and f2l <= F2_MIS_LOWER and f2h is not None and f2h <= F2_MIS_HIGHER, "F4": f4 is not None and f4 >= F4_YES,
            "intervals": {"F1_useful_lower": SR.boot(val["useful"]), "F2_mis_lower": SR.boot(val_l), "F2_mis_higher": SR.boot(val_h), "F4_yes_lower": SR.boot(val["yes"])}}


def clear_or_weak(value, interval, floor, upper):
    """A floor met with the interval's near end beyond it is a clear pass; met by the point value only, weak."""
    if interval is None:
        return "no interval"
    return "clear pass" if ((interval[1] <= floor) if upper else (interval[0] >= floor)) else "weak pass"


def net_numbers(pool, runs, version):
    f_lo = SR.settle_funcs(runs)[BOTH[0]]
    per = {q["qid"]: stats(q, version, f_lo) for q in pool}
    passages = [(q["qid"], r["n"]) for q in pool for r in q["rows"] if version in r["variants"] and not r.get("anchor_of")]
    all_yes = 0
    for p in passages:
        votes = [runs[k][p] for k in runs if p in runs[k]]
        all_yes += bool(votes) and all(v == "Yes" for v in votes)
    return {"passages": len(passages), "mis_lower": macro(per, "mis"), "useful_lower": macro(per, "useful"), "yes_by_every_run": all_yes}


def frozen_rules_hash(freeze_path=os.path.join(HERE, "..", "review_data", "ruler", "sealed_run_rules_v1.freeze")):
    import re
    if not os.path.exists(freeze_path):
        return None
    m = re.search(r"sha256\s+([0-9a-f]{64})", open(freeze_path, encoding="utf-8").read())
    return m.group(1) if m else None


def halves_of(pool_path, half, real_path=os.path.join(HERE, "..", "review_data", "ruler", "real30_v1.json")):
    """Ids of the questions of one half, read from the question file's half labels only (no question text is used)."""
    return {q["id"] for q in json.load(open(real_path))["questions"] if q["half"] == half}


def stage_marks(pool_path, replies, out, names):
    pool, passages = ing.load_pool(pool_path)
    runs, problems, ev = ing.load_replies(replies, passages, pool)
    keys = sorted(passages)
    both_tools = [t for t in ("ChatGPT", "Gemini")]
    marked_by = {p: [t for t in both_tools if any(p in runs[k] for k in runs if k[0] == t)] for p in keys}
    missing = [p for p in keys if len(marked_by[p]) < 2]
    pairs = [(next(runs[k][p] for k in runs if k[0] == "ChatGPT" and p in runs[k]), next(runs[k][p] for k in runs if k[0] == "Gemini" and p in runs[k])) for p in keys if len(marked_by[p]) == 2]
    agreement = (sum(a == b for a, b in pairs) / len(pairs)) if pairs else 0.0
    versions = [v for v in names.values() if any(v in r["variants"] for q in pool for r in q["rows"])]
    table = arm_table(pool, runs, versions)
    res = {"stage": "marks", "pool_sha256": sha(pool_path), "replies_sha256": replies_digest(replies), "names": names, "questions": len(pool), "passages": len(keys), "runs": {f"{m}/{o}": len(r) for (m, o), r in sorted(runs.items())},
           "file_problems": len(problems), "quote_problems": sum(1 for _, m in problems if "quote" in m), "coverage_complete": not missing, "passages_not_marked_by_both_tools": len(missing),
           "tool_agreement_exact": agreement, "reliability": "weak" if agreement < WEAK_AGREEMENT else "ok"}
    res["settlements"] = {s: {v: {"questions": sum(1 for x in per[v].values() if x), "yes": macro(per[v], "yes"), "useful": macro(per[v], "useful"), "mis": macro(per[v], "mis"), "grade": macro(per[v], "grade")} for v in versions} for s, per in table.items()}
    if names["a"] in versions and names["r"] in versions:
        cmp = compare_arms(table, names["a"], names["r"])
        res["R_against_A"] = cmp
        res["marks_rules"] = rules_on_marks(cmp, agreement)
        res["floors"] = {"A": floors(table, names["a"]), "R": floors(table, names["r"])}
    res["nets"] = {k: net_numbers(pool, runs, names[k]) for k in ("na", "nr") if names[k] in versions}
    os.makedirs(out, exist_ok=True)
    json.dump(res, open(os.path.join(out, "stage1.json"), "w"), indent=1)
    return res


def stage_key(pool_path, replies, out, key_path, names, half, tuning=None, register_flags=None):
    s1p = os.path.join(out, "stage1.json")
    if not os.path.exists(s1p):
        raise SystemExit("refused: stage 1 (marks) has not been run; the key is opened only after the marks are scored")
    s1 = json.load(open(s1p))
    if s1["pool_sha256"] != sha(pool_path) or s1["replies_sha256"] != replies_digest(replies):
        raise SystemExit("refused: the pool or the replies have changed since stage 1; run stage 1 again and keep both outputs")
    if not s1["coverage_complete"]:
        raise SystemExit(f"refused: {s1['passages_not_marked_by_both_tools']} passages are not marked by both tools; the result would be INCOMPLETE, not scored")
    pool, passages = ing.load_pool(pool_path)
    runs, _, _ = ing.load_replies(replies, passages, pool)
    with open(pool_path, encoding="utf-8") as fh:
        doc = json.load(fh)
    run_rec = doc.get("run", {}) if isinstance(doc, dict) else {}
    if half == "sealed":
        frozen = frozen_rules_hash()
        got = (run_rec.get("final_recipe") or {}).get("rules_sha256")
        if frozen is None or got != frozen:
            raise SystemExit("refused: this pool was not made by the guarded sealed run (its run record has no final recipe under the frozen rules)")
    else:
        sealed_ids = halves_of(pool_path, "sealed")
        if any(q["qid"] in sealed_ids for q in pool):
            raise SystemExit("refused: --half dev, but the pool holds a sealed question")
    key = json.load(open(key_path))
    kq = {q["qid"]: key["questions"][q["qid"]] for q in pool}                       # only the questions of this pool are read out of the key
    del key
    a_name, r_name = names["a"], names["r"]
    versions = [a_name, r_name]
    answerable = [q["qid"] for q in pool if kq[q["qid"]]["reachable"] is True and q["domain"] != "K"]
    gaps_controls = [q["qid"] for q in pool if q["qid"] not in answerable]

    def named(q, v):
        items = q["lists"].get(v) or []
        wanted = set(kq[q["qid"]]["key_docs"])
        return RS.first_rank(items, wanted)
    nm = {v: {q["qid"]: named(q, v) for q in pool if q["qid"] in answerable} for v in versions}
    hits = lambda v, k: sum(1 for r in nm[v].values() if r is not None and r <= k)

    def stale_in_top5(q, v):
        stale = {x["doc"] for x in kq[q["qid"]]["stale_docs"] if x["counts_as_stale"]}
        items = (q["lists"].get(v) or [])[:5]
        return [it for it in items if ({it["doc"], *it.get("also", [])} & stale)]
    stale_counts = {v: sum(len(stale_in_top5(q, v)) for q in pool) for v in versions}
    rule4 = hits(r_name, 5) >= hits(a_name, 5) and stale_counts[r_name] <= stale_counts[a_name]
    r_wins = s1["marks_rules"]["marks_rules_hold"] and rule4
    chosen_key = "r" if r_wins else "a"
    chosen = names[chosen_key]
    fl = s1["floors"]["R" if r_wins else "A"]
    f3_vals = [1.0 if (nm[chosen][q] is not None and nm[chosen][q] <= 10) else 0.0 for q in answerable]
    f3 = (sum(f3_vals) / len(f3_vals)) if f3_vals else None
    floor_ok = bool(fl["F1"] and fl["F2"] and fl["F4"] and f3 is not None and f3 >= F3_NAMED)
    interval = fl["intervals"]
    kinds = {"F1": clear_or_weak(fl["F1_useful_lower"], interval["F1_useful_lower"], F1_USEFUL, False),
             "F2": "clear pass" if clear_or_weak(fl["F2_mis_lower"], interval["F2_mis_lower"], F2_MIS_LOWER, True) == "clear pass" and clear_or_weak(fl["F2_mis_higher"], interval["F2_mis_higher"], F2_MIS_HIGHER, True) == "clear pass" else "weak pass",
             "F3": clear_or_weak(f3, SR.boot(f3_vals) if f3_vals else None, F3_NAMED, False), "F4": clear_or_weak(fl["F4_yes_lower"], interval["F4_yes_lower"], F4_YES, False)}
    # D3: the chosen arm's safety net
    net = s1["nets"].get("nr" if r_wins else "na")
    d3 = None if net is None else {"keep_the_net": bool(net["mis_lower"] is not None and net["mis_lower"] <= NET_MIS and net["useful_lower"] >= NET_USEFUL and net["yes_by_every_run"] >= NET_YES_ALL), **net}
    # lights
    f_lo, f_hi = SR.settle_funcs(runs)[BOTH[0]], SR.settle_funcs(runs)[BOTH[1]]
    by_domain = collections.defaultdict(lambda: {"rel": {BOTH[0]: [], BOTH[1]: []}, "cur": [], "sealed_rel": {BOTH[0]: [], BOTH[1]: []}, "sealed_cur": []})
    for q in pool:
        k = kq[q["qid"]]
        if k["reachable"] is True and q["domain"] != "K":
            for sname, f in ((BOTH[0], f_lo), (BOTH[1], f_hi)):
                rel = RL.question_relevance(q, chosen, lambda qid, n, f=f: f((qid, n)))
                if rel:
                    by_domain[q["domain"]]["rel"][sname].append(rel)
                    by_domain[q["domain"]]["sealed_rel"][sname].append(RL.relevance_light([rel])[0])
        stale = {x["doc"] for x in k["stale_docs"] if x["counts_as_stale"]}
        if stale and q["domain"] != "K":
            let = bool(stale_in_top5(q, chosen))
            if register_flags is not None:
                flagged = set(register_flags.get(q["qid"], []))
                let_reg = any(it["h"] not in flagged for it in stale_in_top5(q, chosen))
            else:
                let_reg = None
            by_domain[q["domain"]]["cur"].append(let)
            by_domain[q["domain"]]["sealed_cur"].append((q["qid"], let, let_reg))
    tun_note = None
    if tuning:
        tun_note = add_tuning(by_domain, tuning, chosen_key, names)
    domains = {}
    all_cur = [x for d in by_domain.values() for x in d["cur"]]
    cur_overall = RL.currency_light(all_cur)
    for d, parts in sorted(by_domain.items()):
        rel = {s: RL.relevance_light(parts["rel"][s]) for s in BOTH}
        cur = RL.currency_light(parts["cur"])
        guard_ok = all(c != "red" for colours in parts["sealed_rel"].values() for c in colours)          # with one sealed question per domain: that question alone is not red
        eligible = floor_ok and all(rel[s][0] in ("green", "amber") for s in BOTH) and cur[0] != "red" and guard_ok
        domains[d] = {"relevance": {s: rel[s][0] for s in BOTH}, "currency": cur[0], "currency_let_through": f"{cur[1]} of {cur[2]}", "sealed_question_alone_relevance": parts["sealed_rel"], "eligible": bool(eligible)}
    if not floor_ok:
        outcome = "A floor is missed: nothing is connected; the sealed half is used up, any new final test needs new questions"
    elif not any(v["eligible"] for v in domains.values()):
        outcome = "Floors met, no domain eligible: retrieval is fit, currency is not; extend the register and test on new trap questions"
    else:
        outcome = "Floors met, at least one domain eligible: the recipe may go to shadow mode in the eligible domains only"
    res = {"stage": "key", "half": half, "key_opened_after_marks": True, "answerable": answerable, "gaps_or_controls": gaps_controls, "named_authority": {v: {"top5": hits(v, 5), "top10": hits(v, 10), "answerable": len(answerable)} for v in versions},
           "stale_in_top5": stale_counts, "rule4_authority_and_stale_not_worse": rule4, "marks_rules": s1["marks_rules"], "R_replaces_A": r_wins, "chosen_arm": chosen, "floors_chosen_arm": {"F1": fl["F1"], "F2": fl["F2"], "F3": bool(f3 is not None and f3 >= F3_NAMED), "F4": fl["F4"],
           "F3_named_authority_top10": f3, "values": {k: fl[k] for k in ("F1_useful_lower", "F2_mis_lower", "F2_mis_higher", "F4_yes_lower")}, "clear_or_weak": kinds}, "floors_met": floor_ok, "safety_net_D3": d3,
           "currency_overall": {"light": cur_overall[0], "let_through": f"{cur_overall[1]} of {cur_overall[2]}"}, "domains": domains, "tuning_added": tun_note, "reliability": s1["reliability"], "outcome": outcome}
    json.dump(res, open(os.path.join(out, "stage2.json"), "w"), indent=1, default=list)
    json.dump({"key_file_sha256": sha(key_path), "questions_read": sorted(kq), "after_stage1_pool_sha256": s1["pool_sha256"]}, open(os.path.join(out, "key_opened.json"), "w"), indent=1)
    write_report(out, s1, res, names)
    return res


def add_tuning(by_domain, tuning, chosen_key, names):
    """Adds the tuning half's questions to the domain lights for the chosen arm (the pool and replies of the tuning marks; arm names may differ there)."""
    pool_t, passages_t = ing.load_pool(tuning["pool"])
    runs_t, _, _ = ing.load_replies(tuning["replies"], passages_t, pool_t)
    key_t = json.load(open(tuning["key"]))
    version = tuning["a"] if chosen_key == "a" else tuning["r"]
    f_lo, f_hi = SR.settle_funcs(runs_t)[BOTH[0]], SR.settle_funcs(runs_t)[BOTH[1]]
    added = 0
    for q in pool_t:
        k = key_t["questions"][q["qid"]]
        if not any(version in r["variants"] for r in q["rows"]):
            continue
        if k["reachable"] is True and q["domain"] != "K":
            for sname, f in ((BOTH[0], f_lo), (BOTH[1], f_hi)):
                rel = RL.question_relevance(q, version, lambda qid, n, f=f: f((qid, n)))
                if rel:
                    by_domain[q["domain"]]["rel"][sname].append(rel)
        stale = {x["doc"] for x in k["stale_docs"] if x["counts_as_stale"]}
        if stale and q["domain"] != "K" and q["lists"].get(version) is not None:
            by_domain[q["domain"]]["cur"].append(any(({it["doc"], *it.get("also", [])} & stale) for it in q["lists"][version][:5]))
        added += 1
    return {"tuning_questions_added": added, "version": version}


def pct(x):
    return "-" if x is None else f"{100 * x:.0f}%"


def write_report(out, s1, s2, names):
    L = ["# Sealed-run report (PRIVATE; LLM-judged: no lawyer has checked any of it)", "", f"**Outcome: {s2['outcome']}**", "",
         f"Reliability: the two tools agree exactly on {pct(s1['tool_agreement_exact'])} of the passages ({s1['reliability']}). Coverage complete: {s1['coverage_complete']}. Chosen arm: **{s2['chosen_arm']}**" + (" (the challenger wins under the rules)" if s2["R_replaces_A"] else " (the status quo stays)") + ".", "",
         "## Floors on the chosen arm (ties to the lower mark unless stated)", "", "| Floor | Value | Needed | Met | |", "|---|---|---|---|---|"]
    v = s2["floors_chosen_arm"]
    L += [f"| F1 useful share | {pct(v['values']['F1_useful_lower'])} | at least {pct(F1_USEFUL)} | {v['F1']} | {v['clear_or_weak']['F1']} |",
          f"| F2 Misleading share | {pct(v['values']['F2_mis_lower'])} (ties lower), {pct(v['values']['F2_mis_higher'])} (ties higher) | at most {pct(F2_MIS_LOWER)} and {pct(F2_MIS_HIGHER)} | {v['F2']} | {v['clear_or_weak']['F2']} |",
          f"| F3 named authority in the top 10 | {pct(v['F3_named_authority_top10'])} of {len(s2['answerable'])} answerable | at least {pct(F3_NAMED)} | {v['F3']} | {v['clear_or_weak']['F3']} |",
          f"| F4 direct (Yes) share | {pct(v['values']['F4_yes_lower'])} | at least {pct(F4_YES)} | {v['F4']} | {v['clear_or_weak']['F4']} |", "",
          "## The two re-rankers (top 5 shares, averaged over questions)", "", "| Settlement | A: Yes / useful / Misleading / grade | R: same | questions R better / worse |", "|---|---|---|---|"]
    for s, c in s1["R_against_A"].items():
        L.append(f"| {s} | {pct(c['A']['yes'])} / {pct(c['A']['useful'])} / {pct(c['A']['mis'])} / {c['A']['grade']:.2f} | {pct(c['R']['yes'])} / {pct(c['R']['useful'])} / {pct(c['R']['mis'])} / {c['R']['grade']:.2f} | {len(c['R_better'])} / {len(c['R_worse'])} |")
    L += ["", f"Rules on the marks (1, 2, 3, 5): {s1['marks_rules']}", f"Rule 4 (named authority in the top 5 and known-stale count, not worse): {s2['rule4_authority_and_stale_not_worse']}; named authority {s2['named_authority']}; known-stale passages in the top 5 {s2['stale_in_top5']}.", "",
          "## Safety net (D3)", "", str(s2["safety_net_D3"]), "", "## Domains", "", "| Domain | relevance (lower / higher ties) | currency | the sealed question alone | eligible |", "|---|---|---|---|---|"]
    for d, x in s2["domains"].items():
        L.append(f"| {d} | {x['relevance'][BOTH[0]]} / {x['relevance'][BOTH[1]]} | {x['currency']} ({x['currency_let_through']}) | {x['sealed_question_alone_relevance']} | {x['eligible']} |")
    L += ["", f"Currency overall (without the register): {s2['currency_overall']}.", "", "Answerable: " + ", ".join(s2["answerable"]) + ". Index gaps and controls (reported apart): " + ", ".join(s2["gaps_or_controls"]) + ".", "",
          "Never to be written as 'X% accurate'. Mr. Advocate reads every passage marked Misleading by any run and a random 20 of the others before anything leaves the project."]
    open(os.path.join(out, "SEALED_RUN_REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stage", choices=["marks", "key"])
    ap.add_argument("--pool", required=True)
    ap.add_argument("--replies", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--key", default=os.path.join(HERE, "..", "review_data", "ruler", "real30_key_v1.json"))
    ap.add_argument("--half", choices=["dev", "sealed"], default="sealed")
    ap.add_argument("--arm-a", default=NAMES["a"])
    ap.add_argument("--arm-r", default=NAMES["r"])
    ap.add_argument("--arm-s", default=NAMES["s"])
    ap.add_argument("--net-a", default=NAMES["na"])
    ap.add_argument("--net-r", default=NAMES["nr"])
    ap.add_argument("--tuning-pool")
    ap.add_argument("--tuning-replies")
    ap.add_argument("--tuning-arm-a", default="A today")
    ap.add_argument("--tuning-arm-r", default="R challenger re-ranker top 5")
    ap.add_argument("--register-flags", help="JSON {qid: [passage hashes the register flags]}; without it the register arm is not computed")
    a = ap.parse_args(argv)
    names = {"a": a.arm_a, "r": a.arm_r, "s": a.arm_s, "na": a.net_a, "nr": a.net_r}
    if a.stage == "marks":
        s1 = stage_marks(a.pool, a.replies, a.out, names)
        print(f"stage 1 written; coverage complete {s1['coverage_complete']}; reliability {s1['reliability']} (agreement {s1['tool_agreement_exact']:.1%}); marks rules {s1.get('marks_rules')}")
        return 0 if s1["coverage_complete"] else 2
    tuning = {"pool": a.tuning_pool, "replies": a.tuning_replies, "key": a.key, "a": a.tuning_arm_a, "r": a.tuning_arm_r} if a.tuning_pool and a.tuning_replies else None
    flags = json.load(open(a.register_flags)) if a.register_flags else None
    s2 = stage_key(a.pool, a.replies, a.out, a.key, names, a.half, tuning, flags)
    print(s2["outcome"], "| chosen arm:", s2["chosen_arm"], "| floors met:", s2["floors_met"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
