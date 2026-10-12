"""Stage D gate of the fix test (review_data/ruler/FIX_TEST_RULES_v1.md, section 3), computed mechanically from a --fix-test D pool. No marks, no spend. PRIVATE (reads the key of questions already used).

    python review_tools/score_fix_stage_d.py --pool review_results/2026-10-12_fix_test_stage_d/pool.json --out review_results/2026-10-12_fix_test_stage_d

Each of C, N1, N2 goes to stage F only if, against B on the same questions: (1) named authority in the top 10 on the answerable tuning questions >= B's count; (2) known-stale passages in the top 5, summed
over the same questions, <= B's; (3) R16: a passage of its key judgment in the top 5 (the known-failure check, for each of C, N1, N2); (4) re-rank tokens per question <= 1.8 x B's (the arms share one call, so 1.0).
Also reported, not gated: how many questions each arm changed in the top 5 and top 10, which Acts fired on which question, and R23 and R03.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fix_arms as FA
import real30_score as RS

KNOWN_FAILURES = ("R16", "R23", "R03")
TOKEN_LIMIT = 1.8


def gate(pool, key, tuning_ids, tokens_by_arm=None):
    """Returns (table, per_question) with everything the gate and the report need."""
    scores = RS.score(pool, key)
    summ = RS.summarise(scores, key, only=set(tuning_ids))
    base = summ[FA.B_VERSION]
    rows, verdict = {}, {}
    for v in FA.FIX_VERSIONS:
        s = summ[v]
        r16 = scores[v].get("R16", {}).get("hits", {}).get("5")
        tok = (tokens_by_arm or {}).get(v, 1.0)
        rows[v] = {"answerable_tuning_questions": s["questions"], "named_authority_top5": s["hit@5"], "named_authority_top10": s["hit@10"], "stale_slots_top5": s["stale_slots"], "stale_questions_top5": s["stale_questions"],
                   "R16_key_in_top5": r16, "R16_first_rank": scores[v].get("R16", {}).get("first_rank"), "R23_first_rank": scores[v].get("R23", {}).get("first_rank"), "R03_first_rank": scores[v].get("R03", {}).get("first_rank"),
                   "rerank_tokens_ratio_to_B": tok}
        if v == FA.B_VERSION:
            continue
        c1, c2, c3, c4 = s["hit@10"] >= base["hit@10"], s["stale_slots"] <= base["stale_slots"], bool(r16), tok <= TOKEN_LIMIT
        verdict[v] = {"1 named authority top 10 >= B": c1, "2 stale slots top 5 <= B": c2, "3 R16 key judgment in top 5": c3, "4 tokens <= 1.8 x B": c4, "goes to stage F": c1 and c2 and c3 and c4}
    return {"rows": rows, "verdict": verdict}, scores


MAX_CHANGED_TOP5 = 8          # rules v2, condition 5: the top 5 may differ from B's on at most this many of the 22 questions


def gate_v2(pool, key, tuning_ids):
    """Rules v2, section 2: the four v1 conditions plus condition 5 (collateral change) for each candidate; section 1.4: per trigger the SMALLER passing size is the finalist.
    Returns ({'rows', 'verdict', 'finalists'}, scores)."""
    scores = RS.score(pool, key)
    summ = RS.summarise(scores, key, only=set(tuning_ids))
    base = summ[FA.B_VERSION]
    ch = churn(pool, FA.V2_VERSIONS)
    rows, verdict = {}, {}
    for v in FA.V2_VERSIONS:
        s = summ[v]
        r16 = scores[v].get("R16", {}).get("hits", {}).get("5")
        rows[v] = {"answerable_tuning_questions": s["questions"], "named_authority_top5": s["hit@5"], "named_authority_top10": s["hit@10"], "stale_slots_top5": s["stale_slots"], "stale_questions_top5": s["stale_questions"],
                   "R16_key_in_top5": r16, "R16_first_rank": scores[v].get("R16", {}).get("first_rank"), "R23_first_rank": scores[v].get("R23", {}).get("first_rank"), "R03_first_rank": scores[v].get("R03", {}).get("first_rank"),
                   "top5_changed": ch.get(v, {}).get("top5_changed", 0), "rerank_tokens_ratio_to_B": 1.0}
        if v == FA.B_VERSION:
            continue
        c = [s["hit@10"] >= base["hit@10"], s["stale_slots"] <= base["stale_slots"], bool(r16), True, rows[v]["top5_changed"] <= MAX_CHANGED_TOP5]
        verdict[v] = {"1 named authority top 10 >= B": c[0], "2 stale slots top 5 <= B": c[1], "3 R16 key judgment in top 5": c[2], "4 tokens <= 1.8 x B": c[3], "5 top 5 changed on <= 8 of 22": c[4], "passes": all(c)}
    finalists = {}
    for tier in ("N1", "N2"):
        passing = [z for z in FA.SIZES_V2 if verdict[FA.v2_name(tier, z)]["passes"]]
        finalists[tier] = FA.v2_name(tier, min(passing)) if passing else None
    return {"rows": rows, "verdict": verdict, "finalists": finalists}, scores


def churn(pool, versions=None):
    """Per arm: number of questions whose top 5 / top 10 (as ordered lists of judgments) differs from B's."""
    out = {v: {"top5_changed": 0, "top10_changed": 0, "questions": 0} for v in (versions or FA.FIX_VERSIONS) if v != FA.B_VERSION}
    for q in pool:
        b = [x["h"] for x in q["lists"][FA.B_VERSION]]
        for v in out:
            a = [x["h"] for x in q["lists"][v]]
            out[v]["questions"] += 1
            out[v]["top5_changed"] += a[:5] != b[:5]
            out[v]["top10_changed"] += a != b
    return out


def report(table, ch, pool, run):
    L = ["# Fix test, stage D: the mechanical gate (PRIVATE)", "",
         f"Run {run.get('when', '')}; index `{run.get('index_commit', '')[:7]}`; rules `{run['fix_test']['rules_sha256'][:12]}`; code `{run['fix_test']['code_commit'][:10]}`; {len(pool)} questions (19 tuning + R16, R23, R03 as a check, not a test).",
         "Source label: the named key authority found in the index by name; no reviewer mark; nothing here says a passage answers a question. Not lawyer-checked.", "",
         "## The four conditions (rules section 3)", "",
         "| Arm | answerable tuning questions | named authority top 5 | top 10 | stale slots top 5 (questions) | R16 key judgment in top 5 (rank) | R23 rank | R03 rank | tokens vs B |", "|---|---|---|---|---|---|---|---|---|"]
    for v, r in table["rows"].items():
        L.append(f"| {v} | {r['answerable_tuning_questions']} | {r['named_authority_top5']} | {r['named_authority_top10']} | {r['stale_slots_top5']} ({r['stale_questions_top5']}) | {'yes' if r['R16_key_in_top5'] else 'no'} (#{r['R16_first_rank']}) | #{r['R23_first_rank']} | #{r['R03_first_rank']} | {r['rerank_tokens_ratio_to_B']:.2f} |")
    L += ["", "## Verdict (all four must hold; an arm that fails is dropped, not retuned)", "", "| Arm | 1 authority top 10 >= B | 2 stale <= B | 3 R16 | 4 tokens | goes to stage F |", "|---|---|---|---|---|---|"]
    for v, x in table["verdict"].items():
        yn = lambda b: "yes" if b else "NO"
        L.append(f"| {v} | {yn(x['1 named authority top 10 >= B'])} | {yn(x['2 stale slots top 5 <= B'])} | {yn(x['3 R16 key judgment in top 5'])} | {yn(x['4 tokens <= 1.8 x B'])} | **{yn(x['goes to stage F'])}** |")
    L += ["", "## How much each arm changed (not gated)", "", "| Arm | questions | top 5 differs from B | top 10 differs from B |", "|---|---|---|---|"]
    for v, c in ch.items():
        L.append(f"| {v} | {c['questions']} | {c['top5_changed']} | {c['top10_changed']} |")
    L += ["", "## Which Acts fired (question side)", "", "| Question | N1 | N2 |", "|---|---|---|"]
    for q in pool:
        f = q.get("acts_fired", {})
        if f.get("N1") or f.get("N2"):
            L.append(f"| {q['qid']} | {', '.join(f.get('N1', [])) or '-'} | {', '.join(f.get('N2', [])) or '-'} |")
    return "\n".join(L) + "\n"


def report_v2(table, ch, pool, run):
    L = ["# Fix test (rules v2), stage D2: the mechanical gate (PRIVATE)", "",
         f"Run {run.get('when', '')}; index `{run.get('index_commit', '')[:7]}`; rules v2 `{run['fix_test']['rules_sha256'][:12]}`; code `{run['fix_test']['code_commit'][:10]}`; {len(pool)} questions (19 tuning + R16, R23, R03 as a check, not a test).",
         "Source label: the named key authority found in the index by name; no reviewer mark; nothing here says a passage answers a question. Not lawyer-checked. The R16 condition is NOT independent evidence (rules v2, section 2, condition 3).", "",
         "| Arm | answerable tuning questions | named authority top 5 | top 10 | stale slots top 5 | R16 key judgment in top 5 (rank) | R23 rank | R03 rank | top 5 differs from B on |", "|---|---|---|---|---|---|---|---|---|"]
    for v, r in table["rows"].items():
        L.append(f"| {v} | {r['answerable_tuning_questions']} | {r['named_authority_top5']} | {r['named_authority_top10']} | {r['stale_slots_top5']} ({r['stale_questions_top5']}) | {'yes' if r['R16_key_in_top5'] else 'no'} (#{r['R16_first_rank']}) | #{r['R23_first_rank']} | #{r['R03_first_rank']} | {r['top5_changed']} of {len(pool)} |")
    yn = lambda b: "yes" if b else "NO"
    L += ["", "## Verdict (all five must hold)", "", "| Arm | 1 authority top 10 >= B | 2 stale <= B | 3 R16 | 4 tokens | 5 top 5 changed on <= 8 | passes |", "|---|---|---|---|---|---|---|"]
    for v, x in table["verdict"].items():
        L.append(f"| {v} | {yn(x['1 named authority top 10 >= B'])} | {yn(x['2 stale slots top 5 <= B'])} | {yn(x['3 R16 key judgment in top 5'])} | {yn(x['4 tokens <= 1.8 x B'])} | {yn(x['5 top 5 changed on <= 8 of 22'])} | **{yn(x['passes'])}** |")
    L += ["", "## Finalists (rules v2, section 1.4: per trigger the smaller passing size)", ""]
    for tier, f in table["finalists"].items():
        L.append(f"- {tier}: {f or 'none (dropped)'}")
    if not any(table["finalists"].values()):
        L += ["", "**No finalist: B stays; no marking round is run for arms (rules v2, section 3).**"]
    L += ["", "## Which Acts fired (question side)", "", "| Question | N1 | N2 |", "|---|---|---|"]
    for q in pool:
        f = q.get("acts_fired", {})
        if f.get("N1") or f.get("N2"):
            L.append(f"| {q['qid']} | {', '.join(f.get('N1', [])) or '-'} | {', '.join(f.get('N2', [])) or '-'} |")
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pool", required=True)
    ap.add_argument("--key", default=RS.DEFAULT_KEY)
    ap.add_argument("--out", required=True)
    ap.add_argument("--rules", choices=["v1", "v2"], default="v1", help="v1: arms B, C, N1, N2 at 1.10; v2: B and N1/N2 at 1.25 and 1.50")
    a = ap.parse_args(argv)
    doc = json.load(open(a.pool, encoding="utf-8"))
    key = json.load(open(a.key, encoding="utf-8"))
    pool = doc["questions"]
    tuning = [q["qid"] for q in pool if q["qid"] not in KNOWN_FAILURES]
    os.makedirs(a.out, exist_ok=True)
    if a.rules == "v2":
        table, scores = gate_v2(pool, key, tuning)
        ch = churn(pool, FA.V2_VERSIONS)
        json.dump({"table": table, "churn": ch, "scores": scores}, open(os.path.join(a.out, "stage_d2_gate.json"), "w", encoding="utf-8"), indent=1)
        open(os.path.join(a.out, "STAGE_D2_GATE.md"), "w", encoding="utf-8").write(report_v2(table, ch, pool, doc["run"]))
        print(open(os.path.join(a.out, "STAGE_D2_GATE.md"), encoding="utf-8").read())
        return 0
    table, scores = gate(pool, key, tuning)
    ch = churn(pool)
    json.dump({"table": table, "churn": ch, "scores": scores}, open(os.path.join(a.out, "stage_d_gate.json"), "w", encoding="utf-8"), indent=1)
    open(os.path.join(a.out, "STAGE_D_GATE.md"), "w", encoding="utf-8").write(report(table, ch, pool, doc["run"]))
    print(open(os.path.join(a.out, "STAGE_D_GATE.md"), encoding="utf-8").read())
    return 0


if __name__ == "__main__":
    sys.exit(main())
