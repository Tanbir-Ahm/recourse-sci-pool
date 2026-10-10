#!/usr/bin/env python3
"""Scores a challenger re-ranker on the reviewers' marks: are the passages it brings into the top 5 at least as good as the ones it pushes out? LLM-judged marks only (never lawyer-checked).

  python review_tools/score_challenger_arm.py --pool .../pool_with_rerank_arms.json --replies DIR --out DIR

DIR holds the normalised replies of ALL batches (first batch R01_A_ChatGPT.txt ..., second batch R01_TA_ChatGPT.txt ...). The pool is the extended pool written by `build_rerank_test_pack.py --challenger`: its rows
carry the arms B (today's re-ranker, top 5) and R (the challenger, top 5). Compared: R against B. If the pool has no B arm, the recorded version A ("A today") is used instead and the output says so.

Groups per question: kept (in both top 5), entering (R only), leaving (B only). Under four settlements of the marks (ChatGPT alone, Gemini alone, both with ties to the lower mark, both with ties to the higher mark):
  * the passages entering against the passages leaving, pooled over questions (counts and shares of Yes / useful (Yes or Partly) / Misleading);
  * per question, the top 5 of R minus the top 5 of B in the share of Yes / useful / Misleading, averaged over questions with a bootstrap interval over questions;
  * coverage: passages of either top 5 that no run has marked.

THE RULE (written before any mark exists; it concerns the two "both" settlements, which must agree):
  PROCEED to the next step (a sealed run on the challenger) only if every passage of both top 5s is marked, and in BOTH "both" settlements
     useful(entering) >= useful(leaving) - 1   and   misleading(entering) <= misleading(leaving) + 1   (counts of passages),
  and, outside this tool, no known-stale ruling enters the top 5 (checked against the key's stale list). With about 20 passages on each side one passage is 5 points, so the rule means "not worse by more than one
  passage", it is not a proof of improvement. Otherwise DO NOT PROCEED; if marks are missing, INCOMPLETE. Nothing is read from the key. Writes OUT/challenger_scores.json.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ingest_llm_reviews as ing
import score_rerank_arms as S

R_ARM = "R challenger re-ranker top 5"
B_ARM = "B today's re-ranker top 5 (baseline for R)"
A_ARM = S.A_ARM


def groups_of(q, base_arm):
    rows = [r for r in q["rows"] if not r.get("anchor_of")]
    top5 = lambda arm: {r["n"] for r in rows if r["variants"].get(arm) is not None and r["variants"][arm] <= 5}
    b, r_ = top5(base_arm), top5(R_ARM)
    return {"baseline top 5": sorted(b), "R top 5": sorted(r_), "kept (in both)": sorted(b & r_), "entering (R only)": sorted(r_ - b), "leaving (baseline only)": sorted(b - r_)}


def counts(marks):
    j = [m for m in marks if m is not None]
    return {"marked": len(j), "yes": sum(m == "Yes" for m in j), "useful": sum(m in ("Yes", "Partly") for m in j), "misleading": sum(m == "Misleading" for m in j)}


def score(pool, runs):
    qs = pool["questions"] if isinstance(pool, dict) else pool
    base_arm = B_ARM if any(B_ARM in r["variants"] for q in qs for r in q["rows"]) else A_ARM
    groups = {q["qid"]: groups_of(q, base_arm) for q in qs}
    out = {"questions": len(qs), "baseline": base_arm, "settlements": {}, "coverage": {}}
    for name, f in S.settle_funcs(runs).items():
        ent = counts([f((q["qid"], n)) for q in qs for n in groups[q["qid"]]["entering (R only)"]])
        lea = counts([f((q["qid"], n)) for q in qs for n in groups[q["qid"]]["leaving (baseline only)"]])
        ent["passages"] = sum(len(groups[q["qid"]]["entering (R only)"]) for q in qs)
        lea["passages"] = sum(len(groups[q["qid"]]["leaving (baseline only)"]) for q in qs)
        paired = {}
        common = [q["qid"] for q in qs if S.shares([f((q["qid"], n)) for n in groups[q["qid"]]["baseline top 5"]]) and S.shares([f((q["qid"], n)) for n in groups[q["qid"]]["R top 5"]])]
        for key in ("yes", "useful", "mis"):
            d = [S.shares([f((i, n)) for n in groups[i]["R top 5"]])[key] - S.shares([f((i, n)) for n in groups[i]["baseline top 5"]])[key] for i in common]
            paired[key] = {"R_minus_baseline": (sum(d) / len(d)) if d else None, "ci95_over_questions": S.boot(d), "questions": len(d), "R_better": sum(x > 1e-9 for x in d), "same": sum(abs(x) <= 1e-9 for x in d), "R_worse": sum(x < -1e-9 for x in d)}
        out["settlements"][name] = {"entering": ent, "leaving": lea, "R_top5_minus_baseline_top5": paired}
    marked = {p for r in runs.values() for p in r}
    for g in ("baseline top 5", "R top 5", "entering (R only)", "leaving (baseline only)"):
        tot = sum(len(groups[q["qid"]][g]) for q in qs)
        out["coverage"][g] = {"passages": tot, "not_marked_by_any_run": sum(1 for q in qs for n in groups[q["qid"]][g] if (q["qid"], n) not in marked)}
    out["per_question"] = {q["qid"]: {k: v for k, v in groups[q["qid"]].items() if k in ("entering (R only)", "leaving (baseline only)")} for q in qs}
    both = [out["settlements"][k] for k in ("both, ties to the lower mark", "both, ties to the higher mark")]
    complete = all(v["not_marked_by_any_run"] == 0 for k, v in out["coverage"].items()) and all(s["entering"]["marked"] == s["entering"]["passages"] and s["leaving"]["marked"] == s["leaving"]["passages"] for s in both)
    ok = all(s["entering"]["useful"] >= s["leaving"]["useful"] - 1 and s["entering"]["misleading"] <= s["leaving"]["misleading"] + 1 for s in both)
    out["rule"] = {"verdict": "INCOMPLETE" if not complete else ("PROCEED" if ok else "DO NOT PROCEED"), "complete": complete,
                   "both_settlements": [{"entering": s["entering"], "leaving": s["leaving"]} for s in both],
                   "note": "the stale-ruling check on the entering passages is separate and must also be clean"}
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
    with open(os.path.join(a.out, "challenger_scores.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
    for name, d in res["settlements"].items():
        e, l = d["entering"], d["leaving"]
        print(f"{name:30s} entering {e['passages']} (marked {e['marked']}): yes {e['yes']}, useful {e['useful']}, misleading {e['misleading']} | leaving {l['passages']} (marked {l['marked']}): yes {l['yes']}, useful {l['useful']}, misleading {l['misleading']}")
    print("coverage:", {k: v["not_marked_by_any_run"] for k, v in res["coverage"].items()})
    print("RULE:", res["rule"]["verdict"], "(the stale-ruling check is separate)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
