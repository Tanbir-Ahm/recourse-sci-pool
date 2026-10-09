#!/usr/bin/env python3
"""Scores the re-ranker test: does the re-ranker's top 5 beat the merged order's top 5 on the reviewers' marks, and are the safety-net passages worth showing? LLM-judged marks only.

  python review_tools/score_rerank_arms.py --pool review_results/2026-10-09_real30_rerank_test_pack/pool_with_rerank_arms.json --replies DIR --out DIR

DIR holds the normalised replies of BOTH batches: the first batch (R01_A_ChatGPT.txt ...) and the second (R01_TA_ChatGPT.txt, R01_TA_Gemini.txt ...). The pool is the extended pool written by
build_rerank_test_pack.py (or a pool from `pool_runner.py --safety-net`): its rows carry the arms "A today", "N merged order (no re-ranker)" and "M safety net".

What it reports (each under four settlements of the marks: ChatGPT alone, Gemini alone, both with ties to the lower mark, both with ties to the higher mark; passages marked by one run only count that run):
  1. A's top 5 against N's top 5 (the search without the re-ranker), per question, averaged over questions, with a bootstrap interval over questions: this is the re-ranker's effect on the marks.
  2. The same split passage by passage: kept (in both top 5), promoted (A only), demoted (N only).
  3. The tiers of the list to show: A's top 5, A's places 6 to 10, the safety net M, and A's ten plus M.
  4. The anchors: passages marked in the first batch and repeated in the second; how often the same tool gives the same mark, and the average shift (a batch effect).
  5. Coverage: passages of these lists that no run has marked (they are left out of the shares, and counted here).
Nothing is read from the key. Writes OUT/rerank_arms_scores.json.
"""
import argparse
import collections
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ingest_llm_reviews as ing

A_ARM, N_ARM, M_ARM = "A today", "N merged order (no re-ranker)", "M safety net"
GRADE = {"Misleading": 0, "No": 1, "Partly": 2, "Yes": 3}


def settle_funcs(runs):
    """{name: f(passage key) -> mark or None}."""
    keys = sorted(runs)

    def votes(p):
        return [runs[k][p] for k in keys if p in runs[k]]

    def tool(t):
        def f(p):                                   # the tool's order-A run for a first-batch passage, its second-batch run for a new one
            for order in ("A", "TA"):
                m = runs.get((t, order), {}).get(p)
                if m:
                    return m
            return None
        return f

    def cons(pick):
        def f(p):
            v = votes(p)
            return ing._resolve(v, pick) if v else None
        return f
    return {"ChatGPT alone": tool("ChatGPT"), "Gemini alone": tool("Gemini"), "both, ties to the lower mark": cons(min), "both, ties to the higher mark": cons(max)}


def shares(marks):
    j = [m for m in marks if m is not None]
    if not j:
        return None
    n = len(j)
    return {"n": n, "yes": sum(m == "Yes" for m in j) / n, "useful": sum(m in ("Yes", "Partly") for m in j) / n, "mis": sum(m == "Misleading" for m in j) / n}


def lists_of(q):
    """Row numbers per group for one question."""
    rows = [r for r in q["rows"] if not r.get("anchor_of")]
    rank = lambda r, v: r["variants"].get(v)
    g = {"A top 5": [r["n"] for r in rows if rank(r, A_ARM) is not None and rank(r, A_ARM) <= 5],
         "A places 6 to 10": [r["n"] for r in rows if rank(r, A_ARM) is not None and 6 <= rank(r, A_ARM) <= 10],
         "N top 5": [r["n"] for r in rows if rank(r, N_ARM) is not None and rank(r, N_ARM) <= 5],
         "M safety net": [r["n"] for r in rows if rank(r, M_ARM) is not None]}
    g["A ten plus M"] = sorted(set(g["A top 5"]) | set(g["A places 6 to 10"]) | set(g["M safety net"]))
    g["kept (in both top 5)"] = sorted(set(g["A top 5"]) & set(g["N top 5"]))
    g["promoted (A only)"] = sorted(set(g["A top 5"]) - set(g["N top 5"]))
    g["demoted (N only)"] = sorted(set(g["N top 5"]) - set(g["A top 5"]))
    return g


def boot(diffs, n=5000, seed=20261010):
    if not diffs:
        return None
    r = random.Random(seed)
    ms = sorted(sum(diffs[r.randrange(len(diffs))] for _ in diffs) / len(diffs) for _ in range(n))
    return [round(ms[int(0.025 * n)], 4), round(ms[int(0.975 * n)], 4)]


def score(pool, runs):
    qs = pool["questions"] if isinstance(pool, dict) else pool
    f_all = settle_funcs(runs)
    out = {"questions": len(qs), "settlements": {}, "anchors": {}, "coverage": {}}
    groups = {q["qid"]: lists_of(q) for q in qs}
    for name, f in f_all.items():
        per_group = {}
        for gname in next(iter(groups.values())):
            per_q = {}
            for q in qs:
                s = shares([f((q["qid"], n)) for n in groups[q["qid"]][gname]])
                if s:
                    per_q[q["qid"]] = s
            if per_q:
                per_group[gname] = {"questions": len(per_q), **{k: sum(v[k] for v in per_q.values()) / len(per_q) for k in ("yes", "useful", "mis")}}
        # pooled over passages for the split groups
        pooled = {}
        for gname in ("kept (in both top 5)", "promoted (A only)", "demoted (N only)"):
            marks = [f((q["qid"], n)) for q in qs for n in groups[q["qid"]][gname]]
            s = shares(marks)
            pooled[gname] = dict(s or {}, passages=len(marks))
        paired = {}
        common = [q["qid"] for q in qs if shares([f((q["qid"], n)) for n in groups[q["qid"]]["A top 5"]]) and shares([f((q["qid"], n)) for n in groups[q["qid"]]["N top 5"]])]
        for key in ("yes", "useful", "mis"):
            d = [shares([f((qid, n)) for n in groups[qid]["A top 5"]])[key] - shares([f((qid, n)) for n in groups[qid]["N top 5"]])[key] for qid in common]
            paired[key] = {"A_minus_N": (sum(d) / len(d)) if d else None, "ci95_over_questions": boot(d), "questions": len(d), "A_better": sum(x > 1e-9 for x in d), "same": sum(abs(x) <= 1e-9 for x in d), "A_worse": sum(x < -1e-9 for x in d)}
        out["settlements"][name] = {"groups": per_group, "passages_pooled": pooled, "A_top5_minus_N_top5": paired}
    # anchors: same tool, same text, first batch against second
    anc = []
    for q in qs:
        for r in q["rows"]:
            if r.get("anchor_of"):
                for tool in ("ChatGPT", "Gemini"):
                    a1, a2 = runs.get((tool, "A"), {}).get((q["qid"], r["anchor_of"])), runs.get((tool, "TA"), {}).get((q["qid"], r["n"]))
                    if a1 and a2:
                        anc.append((tool, a1, a2))
    for tool in ("ChatGPT", "Gemini", "both"):
        sel = [x for x in anc if tool == "both" or x[0] == tool]
        if sel:
            out["anchors"][tool] = {"pairs": len(sel), "same_mark": sum(a == b for _, a, b in sel) / len(sel), "same_useful_or_not": sum((a in ("Yes", "Partly")) == (b in ("Yes", "Partly")) for _, a, b in sel) / len(sel),
                                    "mean_grade_shift_second_minus_first": sum(GRADE[b] - GRADE[a] for _, a, b in sel) / len(sel), "second_higher": sum(GRADE[b] > GRADE[a] for _, a, b in sel), "second_lower": sum(GRADE[b] < GRADE[a] for _, a, b in sel)}
    # coverage: passages of the lists that no run has marked
    marked = {p for r in runs.values() for p in r}
    for gname in next(iter(groups.values())):
        tot = sum(len(groups[q["qid"]][gname]) for q in qs)
        miss = sum(1 for q in qs for n in groups[q["qid"]][gname] if (q["qid"], n) not in marked)
        out["coverage"][gname] = {"passages": tot, "not_marked_by_any_run": miss}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pool", required=True)
    ap.add_argument("--replies", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    pool_list, passages = ing.load_pool(a.pool)
    runs, problems, ev = ing.load_replies(a.replies, passages, pool_list)
    for fn, msg in problems:
        print(f"  {fn}: {msg}")
    res = score(pool_list, runs)
    res["runs"] = {f"{m}/{o}": len(r) for (m, o), r in sorted(runs.items())}
    res["reply_problems"] = len(problems)
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "rerank_arms_scores.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
    pc = lambda x: "-" if x is None else f"{100 * x:.0f}%"
    for name, d in res["settlements"].items():
        p = d["A_top5_minus_N_top5"]
        print(f"{name:30s} A top 5 minus N top 5: direct {100 * p['yes']['A_minus_N']:+.1f} points {p['yes']['ci95_over_questions']}, useful {100 * p['useful']['A_minus_N']:+.1f} {p['useful']['ci95_over_questions']}, "
              f"misleading {100 * p['mis']['A_minus_N']:+.1f} {p['mis']['ci95_over_questions']} on {p['yes']['questions']} questions" if p["yes"]["A_minus_N"] is not None else f"{name}: nothing to compare yet")
    print("coverage:", {k: v["not_marked_by_any_run"] for k, v in res["coverage"].items()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
