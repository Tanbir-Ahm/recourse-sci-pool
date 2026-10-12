# Fix test, stage F: report (PRIVATE; LLM-judged: no lawyer has checked any of it)

**Outcome: B stays: no finalist satisfies rules 1 to 6 of FIX_TEST_RULES_v1.md section 5; floors met and at least one domain eligible: the recipe may go to shadow mode in the eligible domains only (never the verified answer path)**

Reliability: the two tools agree exactly on 64% of the passages (ok). Coverage complete: True. Scored questions 26 (domains A to J); controls apart: N28, N29, N30. Chosen recipe: **B baseline (rerank-3-lite)**.

## Top-5 shares, averaged over the scored questions

| Settlement | version | Yes | useful | Misleading | mean grade |
|---|---|---|---|---|---|
| ChatGPT alone | B | 55% | 91% | 6% | 2.40 |
| ChatGPT alone | N1-125 | 49% | 92% | 6% | 2.35 |
| ChatGPT alone | N2-125 | 50% | 92% | 6% | 2.36 |
| Gemini alone | B | 42% | 81% | 12% | 2.12 |
| Gemini alone | N1-125 | 39% | 79% | 12% | 2.06 |
| Gemini alone | N2-125 | 40% | 80% | 12% | 2.08 |
| both, ties to the lower mark | B | 40% | 79% | 14% | 2.05 |
| both, ties to the lower mark | N1-125 | 37% | 78% | 15% | 2.00 |
| both, ties to the lower mark | N2-125 | 38% | 78% | 15% | 2.02 |
| both, ties to the higher mark | B | 58% | 92% | 4% | 2.46 |
| both, ties to the higher mark | N1-125 | 52% | 93% | 4% | 2.41 |
| both, ties to the higher mark | N2-125 | 52% | 94% | 4% | 2.42 |

## Each finalist against B (rules of FIX_TEST_RULES_v1.md section 5)

| Finalist | rule 1 grade | rule 2 margins | rule 3 two more questions better | rule 4 named authority and stale | rule 5 reliability | rule 6 look-alikes | passes |
|---|---|---|---|---|---|---|---|
| N1-125 | False | True | False | False | True | False (marks False, key False) | **False** |
| N2-125 | False | True | False | False | True | False (marks False, key False) | **False** |

Questions where the finalist is better / worse than B by 0.4 or more in the mean grade of the top 5:

- N1-125, both, ties to the lower mark: better on [], worse on ['N04', 'N25']; top 5 differs from B on 7 questions
- N1-125, both, ties to the higher mark: better on [], worse on []; top 5 differs from B on 7 questions
- N2-125, both, ties to the lower mark: better on [], worse on ['N04', 'N25']; top 5 differs from B on 9 questions
- N2-125, both, ties to the higher mark: better on [], worse on []; top 5 differs from B on 9 questions

Named authority (answerable questions, 26): {'B baseline (rerank-3-lite)': {'top5': 20, 'top10': 21, 'answerable': 26}, 'N1-125 named-Act boost x1.25 (precise)': {'top5': 19, 'top10': 21, 'answerable': 26}, 'N2-125 named-Act boost x1.25 (broad)': {'top5': 19, 'top10': 21, 'answerable': 26}}. Known-stale passages in the top 5: {'B baseline (rerank-3-lite)': 1, 'N1-125 named-Act boost x1.25 (precise)': 1, 'N2-125 named-Act boost x1.25 (broad)': 1}.

## Floors on the chosen recipe

| Floor | Value | Needed | Met | |
|---|---|---|---|---|
| F1 useful share | 79% | at least 70% | True | clear pass |
| F2 Misleading share | 14% (ties lower), 4% (ties higher) | at most 15% and 10% | True | weak pass |
| F3 named authority in the top 10 | 81% of 26 answerable | at least 60% | True | clear pass |
| F4 direct (Yes) share | 40% | at least 25% | True | clear pass |

## Domains (chosen recipe)

| Domain | relevance (lower / higher ties) | currency | eligible |
|---|---|---|---|
| A | green / green | no trap (0 of 0) | True |
| B | green / green | no trap (0 of 0) | True |
| C | amber / amber | green (0 of 1) | True |
| D | red / green | red (1 of 1) | False |
| E | green / green | no trap (0 of 0) | True |
| F | red / amber | no trap (0 of 0) | False |
| G | red / amber | no trap (0 of 0) | False |
| H | green / green | green (0 of 1) | True |
| I | amber / green | green (0 of 1) | True |
| J | red / amber | no trap (0 of 0) | False |

Currency overall (without the register): {'light': 'amber', 'let_through': '1 of 4'}.

## Controls (reported apart; the search should not look confident here)

- N28 (K1): B Yes 0%, useful 20%, Misleading 40%; N1-125 Yes 0%, useful 20%, Misleading 40%; N2-125 Yes 0%, useful 20%, Misleading 40%
- N29 (K2): B Yes 40%, useful 60%, Misleading 20%; N1-125 Yes 40%, useful 60%, Misleading 20%; N2-125 Yes 40%, useful 60%, Misleading 20%
- N30 (K3): B Yes 0%, useful 0%, Misleading 0%; N1-125 Yes 0%, useful 0%, Misleading 0%; N2-125 Yes 0%, useful 0%, Misleading 0%

Floors F1 / F2 / F4 with the three controls pooled in as well (the sealed run's convention; descriptive only): B useful 74%, Misleading 14%/3%, Yes 37%; N1-125 useful 72%, Misleading 15%/3%, Yes 34%; N2-125 useful 73%, Misleading 15%/3%, Yes 35%

## The same without the questions kept as soft overlaps (descriptive only; the decision above uses all scored questions)

Questions left (answerable): 21. Named authority: {'B baseline (rerank-3-lite)': {'top5': 17, 'top10': 17}, 'N1-125 named-Act boost x1.25 (precise)': {'top5': 16, 'top10': 17}, 'N2-125 named-Act boost x1.25 (broad)': {'top5': 16, 'top10': 17}}. Marks rules per finalist: {'N1-125 named-Act boost x1.25 (precise)': {'rule1_grade_all_four_settlements': False, 'rule2_misleading_and_useful_margins': True, 'rule3_two_more_questions_better': False, 'rule5_reliability_not_weak': True, 'marks_rules_hold': False, 'rule6a_lookalike_misleading_5_points_lower': False}, 'N2-125 named-Act boost x1.25 (broad)': {'rule1_grade_all_four_settlements': False, 'rule2_misleading_and_useful_margins': True, 'rule3_two_more_questions_better': False, 'rule5_reliability_not_weak': True, 'marks_rules_hold': False, 'rule6a_lookalike_misleading_5_points_lower': False}}. Floors of the chosen recipe F1/F2/F4: {'F1': True, 'F2': False, 'F4': True}.

Never to be written as 'X% accurate'. Mr. Advocate reads every passage marked Misleading by any run and a random 20 of the others before anything leaves the project.
