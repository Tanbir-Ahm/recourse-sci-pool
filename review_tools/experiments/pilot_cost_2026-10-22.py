"""What does one pilot question cost? Computed from the stored spend of real search runs; reads files only: no network, no spend.

    python review_tools/experiments/pilot_cost_2026-10-22.py --out review_results/2026-10-22_pilot_cost

The pilot's search is recipe B of stage F: one query embedding, one retrieval, one re-rank call (rerank-3-lite) over 60 candidates, passage-type weights, the top 10. The stage F run did exactly that once per question
for its 29 questions, so its recorded tokens divided by 29 are the best estimate of a pilot question. Prices are the listed ones in the repository's own notes (third-party price lists, not Voyage's pages): voyage-law-2 $0.12 per
million tokens; re-ranking $0.02 (rerank-3-lite) or $0.05 (rerank-2) per million. Totals only.
"""
import argparse
import json
import os

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
F = os.path.join(ROOT, "review_results", "2026-10-12_fix_test_f", "spend.json")
PRICE_EMBED, PRICE_RERANK = 0.12, {"rerank-3-lite": 0.02, "rerank-2": 0.05}
RESERVE, BALANCE = 5.0, 9.39                      # dollars: the owner's reserve for the live site (2026-10-10) and the balance noted on 2026-10-10 (FOLLOW_UPS.md); the dashboard is the check


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    sp = json.load(open(F, encoding="utf-8"))["run"]["spend"]
    q = sp["rerank_calls"]
    per = {"questions": q, "rerank_tokens_per_question": round(sp["rerank_tokens"] / q), "embed_tokens_per_question": round(sp["embed_tokens"] / q, 1),
           "recorded_rerank_calls_equal_questions": sp["rerank_calls"] == sp["embed_calls"] == q}
    cost = {m: round(per["rerank_tokens_per_question"] * p / 1e6 + per["embed_tokens_per_question"] * PRICE_EMBED / 1e6, 6) for m, p in PRICE_RERANK.items()}
    spendable = round(BALANCE - RESERVE, 2)
    scen = {}
    for name, users, per_day, days in (("placeholder caps, every cap hit every day (100 questions a day)", None, 100, 28), ("5 lawyers, 5 questions each a day", 5, 5, 28), ("5 lawyers, 2 questions each a day", 5, 2, 28)):
        n = (users or 1) * per_day * days if users else per_day * days
        scen[name] = {"questions": n, **{f"dollars_{m}": round(n * c, 2) for m, c in cost.items()}}
    res = {"basis": "stage F run (29 questions, one embedding and one re-rank call each, rerank-3-lite)", "per_question": per, "dollars_per_question": cost, "balance_noted": BALANCE, "reserve": RESERVE, "spendable_above_reserve": spendable,
           "scenarios_28_days": scen, "prices_per_million": {"voyage-law-2": PRICE_EMBED, **{k: v for k, v in PRICE_RERANK.items()}}, "price_status": "listed prices from third-party price lists, not Voyage's pages; the dashboard is the check"}
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "numbers.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
        fh.write("\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
