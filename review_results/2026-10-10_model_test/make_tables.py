"""Turns results.json (and results_confirm.json when it exists) into the tables of the README. No network, no spend.
    python3 make_tables.py results.json > TABLES.md
"""
import json
import os
import sys


def cell(r):
    return "-" if r is None else str(r)


def main(path):
    d = json.load(open(path))
    qs, pq, arms = d["questions"], d["per_question"], ("A0", "A1", "A2", "A2b")
    out = []
    out.append(f"Verdict by the pre-registered rule: **{d['verdict']}**  (valid: {d['validity']['all_ok']})\n")
    out.append("### Validity checks\n")
    for k, v in d["validity"].items():
        out.append(f"- {k}: {v}")
    out.append("\n### Final top 10 (the search as it would run): place of the first passage of a key judgment, and whether a key passage is among the 60 candidates\n")
    out.append("| Question | A0 law-2 | A1 4-large | A2 4-lite q. | A2b 4 q. | key passage among the 60 candidates: A0 / A1 / A2 / A2b | recorded in AUTHORITY_HITS (version A) |")
    out.append("|---|---|---|---|---|---|---|")
    rec = {"R01": 1, "R02": 1, "R04": 2, "R08": 2, "R09": None, "R11": 3, "R12": 5, "R14": None, "R17": 1, "R19": 1, "R20": None, "R22": None, "R24": 1, "R26": 4}
    for q in qs:
        c = " / ".join("yes" if pq[q][a]["cand_has_key"] else "no" for a in arms)
        out.append(f"| {q} | {cell(pq[q]['A0']['rank'])} | {cell(pq[q]['A1']['rank'])} | {cell(pq[q]['A2']['rank'])} | {cell(pq[q]['A2b']['rank'])} | {c} | {cell(rec.get(q))} |")
    s = d["summary"]
    out.append("\n| Arm | key in top 1 | in top 5 | in top 10 | key among the 60 candidates | dense-only, in the pool, judgment level: top 1 / 3 / 5 / 10 | mean reciprocal rank |")
    out.append("|---|---|---|---|---|---|---|")
    for a in arms:
        x = s[a]
        dd = x["dense_pool_judgment_hits"]
        out.append(f"| {a} | {x['hit@1']} | {x['hit@5']} | {x['hit@10']} | {x['candidates_with_key']} of {len(qs)} | {dd['top1']} / {dd['top3']} / {dd['top5']} / {dd['top10']} | {x['dense_pool_mrr']} |")
    out.append("\n### Dense-only place of the key judgment among the pool's judgments (the discrimination view; the re-ranker is not involved)\n")
    out.append("| Question | A0 | A1 | A2 | A2b | pool: passages / judgments |")
    out.append("|---|---|---|---|---|---|")
    for q in qs:
        ps = d["pool_sizes"][q]
        out.append(f"| {q} | {cell(pq[q]['A0']['dense_rank'])} | {cell(pq[q]['A1']['dense_rank'])} | {cell(pq[q]['A2']['dense_rank'])} | {cell(pq[q]['A2b']['dense_rank'])} | {ps['pool_passages']} / {ps['pool_docs']} |")
    out.append("\n### Key passages in each arm's first-stage list (100 nearest) and among the 60 candidates\n")
    out.append("| Question | first stage A0 / A1 / A2 / A2b | candidates A0 / A1 / A2 / A2b |")
    out.append("|---|---|---|")
    for q in qs:
        f, c = pq[q]["key_passages_in_first_stage_top100"], pq[q]["key_passages_in_candidates"]
        out.append(f"| {q} | {' / '.join(str(f[a]) for a in arms)} | {' / '.join(str(c[a]) for a in arms)} |")
    out.append("\n### The rule\n")
    for k in ("rule_A1", "rule_A2_same_test"):
        r = d[k]
        out.append(f"- {k}: rescues {r['rescues']}; gain at 5 = {r['gain5']:+d}; gain at 10 = {r['gain10']:+d}; losses {r['losses']}; candidate-mix effects {r['candidate_mix_effects']}; conditions {r['conditions']}; **passed: {r['passed']}**")
    out.append(f"\nSpend (listed, unchecked prices): {d['spend']}  | about ${d['dollars_at_listed_prices']}")
    cp = os.path.join(os.path.dirname(path), "results_confirm.json")
    if os.path.exists(cp):
        c = json.load(open(cp))
        out.append(f"\n### Confirmation step (rescued questions {c['questions']}): stands = {c['confirmation_stands']}; rule on them: {c['rule_A1_on_rescued']}")
    print("\n".join(out))


if __name__ == "__main__":
    main(sys.argv[1])
