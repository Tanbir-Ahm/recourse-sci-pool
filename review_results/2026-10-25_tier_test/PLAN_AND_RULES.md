# Test of the "separate tier" idea: plan and pass/fail rules, written BEFORE any paid call (2026-10-25)

Owner's order (2026-10-25): "test the separate tier idea as you planned; do not leave any steps".

## The idea
Show the Supreme Court judgments and the High Court (Gauhati) judgments as **two labelled lists** instead of one mixed list. This follows the rule `FOLLOW_UPS.md` item 1c records for a less-reviewed pool and the site's own pilot-tier code (`pilot_tier_search.py` in the Recourse repository: its own search, its own stricter similarity bar of 0.50 against 0.40 for the core, at most 3 results, one passage per case, an unmissable label).

## Arms (all use the recipe of `review_tools/pool_runner.py`, class `Engine`: meaning top 100 + keyword top 50 + section phrase, merged to 60 candidates, Voyage rerank-2, weights; the code is imported, not copied)
- **M, mixed (today):** one list over the whole index (418,286 passages).
- **T1, split after mixing:** the same 60 mixed candidates, split by court; the Supreme Court list is the Supreme Court passages among them. No extra call.
- **T2, separate pools:** the recipe run once over the Supreme Court passages only (261,572) and once over the Gauhati passages only (156,714). One extra re-rank call per question.
- **T2b, T2 with the site's bar for the High Court list:** only passages with cosine 0.50 or more, one passage per judgment, at most 3 judgments.
- **Extra, free (cached scores, not part of the plan):** the mixed list with the High Court passages' scores multiplied by 0.8 ("court weight").

## Questions
1. The 12 landmark questions (6 verified landmarks): pass = landmark among the top 5 cases AND its verified paragraph among its own top 3 passages (the index's own test). Already seen before this rule was written (24 Oct): mixed 1 pass, landmark in the top 5 cases for 1; Supreme Court only 2 passes, 4 in the top 5.
2. The 14 answerable questions of the tuning half of the 30 (R01, R02, R04, R08, R09, R11, R12, R14, R17, R19, R20, R22, R24, R26; the key authority per question is in the private key `review_data/ruler/real30_key_v1.json`; only counts go into the results). Measure as `real30_score.py`: rank of the first passage from a key authority (counting passages), hit at 1, 5 and 10. The sealed half is not used. Recorded earlier on index `3c80a26`: A today 5, 10, 10.
3. A check of the harness first: the mixed arm on the old index (`3c80a26`, 236,155 passages) must reproduce the recorded 5, 10, 10 within one question; otherwise stop and fix before anything else.

## What is read by a person (me): relevance of the High Court list
For every question where the High Court list shows something, I read the shown passages and mark each "on point", "related" or "off the subject". This is my reading, not a lawyer's, and is labelled so.

## Pass/fail rules
- **R1 no harm:** the Supreme Court list under T2 has hit@5 on the 14 questions at least equal to the mixed list's, and the landmark in the top 5 cases for at least as many questions.
- **R2 benefit:** the Supreme Court list under T2 beats the mixed list by at least 1 on at least one of: landmark passes, landmark in top 5, key authority hit@5.
- **R3 the High Court list is worth showing:** with the 0.50 bar it shows at least one judgment for at least half of the 26 questions, AND at least half of the shown judgments are "on point" or "related" by my reading.
- **R4 cost:** at most one extra re-rank call per question (T2) or none (T1).
- **Verdict:** PASS = R1, R2, R3 and R4 hold; PARTIAL = R1, R2, R4 hold but not R3 (tier the Supreme Court list, keep the High Court list off or restricted); FAIL = R1 or R2 fails.
- Sample sizes are tiny (12 and 14 questions): a difference of one question is within noise and is reported as such; no significance test is claimed.

## Budget and limits
Cap about $0.30 (rerank-2 $0.05 per million tokens, query embedding $0.12 per million). Questions and keys are not changed after seeing results. No sealed question is used. Nothing is written to the index.
