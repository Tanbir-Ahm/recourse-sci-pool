"""Checks the pre-registered rules of PLAN_AND_RULES.md against the saved results (no network, no cost).
  python3 -I summarise_ratings.py            # run inside this folder
Reads tier_full.json (numbers from tier_test.py) and hc_tier_ratings.csv (my reading of every shown High Court judgment: on point / related / off)."""
import collections, csv, json
f = json.load(open("tier_full.json", encoding="utf-8")); rows = list(csv.DictReader(open("hc_tier_ratings.csv", encoding="utf-8")))
nq, al, at = f["questions"], f["agg_landmarks"], f["agg_tuning"]
c = collections.Counter(r["rating"] for r in rows); good = c["on point"] + c["related"]
print("Supreme Court list, 14 tuning questions (hit at 1 / 5 / 10):", {a: tuple(at[a].values()) for a in at})
print("Supreme Court list, 12 landmark questions (pass / in top 5 cases / in top 10 / not among the candidates):", {a: (al[a]["pass"], al[a]["case_top5"], al[a]["case_top10"], al[a]["not_found"]) for a in al})
r1 = at["T2_SC"]["hit5"] >= at["M"]["hit5"] and al["T2_SC"]["case_top5"] >= al["M"]["case_top5"]
r2 = al["T2_SC"]["pass"] - al["M"]["pass"] >= 1 or al["T2_SC"]["case_top5"] - al["M"]["case_top5"] >= 1 or at["T2_SC"]["hit5"] - at["M"]["hit5"] >= 1
shown_q, shown = f["hc_tier_questions_with_a_result"], f["hc_tier_judgments_shown"]
r3 = shown_q * 2 >= nq and good * 2 >= len(rows)
r4 = f["billed"]["rerank_calls"] <= 3 * nq   # the mixed arm, the Supreme Court pool, the Gauhati pool: one more than the mixed list alone
print(f"HC list: something shown for {shown_q} of {nq} questions; {shown} judgments shown; my reading: on point {c['on point']}, related {c['related']}, off the subject {c['off']} ({100 * good / len(rows):.0f}% on point or related)")
print("R1 no harm:", r1, "| R2 benefit:", r2, "| R3 Gauhati list worth showing:", r3, "| R4 cost:", r4)
print("VERDICT:", "PASS" if r1 and r2 and r3 and r4 else "PARTIAL" if r1 and r2 and r4 else "FAIL")
print("post hoc, not part of the verdict - what a higher similarity bar would do to the Gauhati list:")
for bar in (0.50, 0.52, 0.53, 0.55, 0.60):
    k = [r for r in rows if float(r["cosine"]) >= bar]; kc = collections.Counter(r["rating"] for r in k)
    print(f"  bar {bar:.2f}: {len(k):2d} judgments (on point {kc['on point']}, related {kc['related']}, off {kc['off']}), {len({r['question'] for r in k})} of {nq} questions show something")
