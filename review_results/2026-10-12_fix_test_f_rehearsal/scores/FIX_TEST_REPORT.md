# Fix test, stage F: report (PRIVATE; LLM-judged: no lawyer has checked any of it)

**Outcome: B stays: no finalist satisfies rules 1 to 6 of FIX_TEST_RULES_v1.md section 5; a floor is missed by the chosen recipe: nothing is connected, and any new final test needs new questions**

Reliability: the two tools agree exactly on 74% of the passages (ok). Coverage complete: True. Scored questions 27 (domains A to J); controls apart: N28, N29, N30. Chosen recipe: **B baseline (rerank-3-lite)**.

## Top-5 shares, averaged over the scored questions

| Settlement | version | Yes | useful | Misleading | mean grade |
|---|---|---|---|---|---|
| ChatGPT alone | B | 28% | 67% | 8% | 1.87 |
| ChatGPT alone | N1-125 | 27% | 67% | 9% | 1.86 |
| ChatGPT alone | N2-125 | 28% | 68% | 9% | 1.87 |
| Gemini alone | B | 29% | 67% | 10% | 1.86 |
| Gemini alone | N1-125 | 27% | 67% | 10% | 1.85 |
| Gemini alone | N2-125 | 27% | 67% | 10% | 1.85 |
| both, ties to the lower mark | B | 24% | 61% | 11% | 1.74 |
| both, ties to the lower mark | N1-125 | 22% | 62% | 12% | 1.73 |
| both, ties to the lower mark | N2-125 | 22% | 63% | 12% | 1.73 |
| both, ties to the higher mark | B | 33% | 72% | 7% | 1.99 |
| both, ties to the higher mark | N1-125 | 33% | 73% | 7% | 1.99 |
| both, ties to the higher mark | N2-125 | 33% | 73% | 7% | 1.99 |

## Each finalist against B (rules of FIX_TEST_RULES_v1.md section 5)

| Finalist | rule 1 grade | rule 2 margins | rule 3 two more questions better | rule 4 named authority and stale | rule 5 reliability | rule 6 look-alikes | passes |
|---|---|---|---|---|---|---|---|
| N1-125 | False | True | False | True | True | True (marks False, key True) | **False** |
| N2-125 | False | True | False | True | True | True (marks False, key True) | **False** |

Questions where the finalist is better / worse than B by 0.4 or more in the mean grade of the top 5:

- N1-125, both, ties to the lower mark: better on [], worse on ['N07']; top 5 differs from B on 5 questions
- N1-125, both, ties to the higher mark: better on ['N25'], worse on []; top 5 differs from B on 5 questions
- N2-125, both, ties to the lower mark: better on [], worse on ['N07']; top 5 differs from B on 8 questions
- N2-125, both, ties to the higher mark: better on ['N25'], worse on []; top 5 differs from B on 8 questions

Named authority (answerable questions, 24): {'B baseline (rerank-3-lite)': {'top5': 15, 'top10': 17, 'answerable': 24}, 'N1-125 named-Act boost x1.25 (precise)': {'top5': 16, 'top10': 18, 'answerable': 24}, 'N2-125 named-Act boost x1.25 (broad)': {'top5': 16, 'top10': 18, 'answerable': 24}}. Known-stale passages in the top 5: {'B baseline (rerank-3-lite)': 8, 'N1-125 named-Act boost x1.25 (precise)': 8, 'N2-125 named-Act boost x1.25 (broad)': 8}.

## Floors on the chosen recipe

| Floor | Value | Needed | Met | |
|---|---|---|---|---|
| F1 useful share | 61% | at least 70% | False | weak pass |
| F2 Misleading share | 11% (ties lower), 7% (ties higher) | at most 15% and 10% | True | weak pass |
| F3 named authority in the top 10 | 71% of 24 answerable | at least 60% | True | weak pass |
| F4 direct (Yes) share | 24% | at least 25% | False | weak pass |

## Domains (chosen recipe)

| Domain | relevance (lower / higher ties) | currency | eligible |
|---|---|---|---|
| A | red / amber | no trap (0 of 0) | False |
| B | amber / green | green (0 of 2) | False |
| C | amber / amber | amber (1 of 2) | False |
| D | green / green | amber (1 of 2) | False |
| E | red / amber | no trap (0 of 0) | False |
| F | amber / amber | red (1 of 1) | False |
| G | amber / amber | no trap (0 of 0) | False |
| H | red / red | red (1 of 1) | False |
| I | red / red | green (0 of 1) | False |
| J | red / amber | red (1 of 1) | False |

Currency overall (without the register): {'light': 'amber', 'let_through': '5 of 10'}.

## Controls (reported apart; the search should not look confident here)

- N28 (K1): B Yes 20%, useful 60%, Misleading 0%; N1-125 Yes 20%, useful 60%, Misleading 0%; N2-125 Yes 20%, useful 60%, Misleading 0%
- N29 (K3): B Yes 20%, useful 80%, Misleading 0%; N1-125 Yes 20%, useful 80%, Misleading 0%; N2-125 Yes 20%, useful 80%, Misleading 0%
- N30 (K3): B Yes 0%, useful 40%, Misleading 0%; N1-125 Yes 0%, useful 40%, Misleading 0%; N2-125 Yes 0%, useful 40%, Misleading 0%

Floors F1 / F2 / F4 with the three controls pooled in as well (the sealed run's convention; descriptive only): B useful 61%, Misleading 10%/6%, Yes 23%; N1-125 useful 62%, Misleading 11%/6%, Yes 21%; N2-125 useful 63%, Misleading 11%/6%, Yes 21%

## The same without the questions kept as soft overlaps (descriptive only; the decision above uses all scored questions)

Questions left (answerable): 21. Named authority: {'B baseline (rerank-3-lite)': {'top5': 13, 'top10': 15}, 'N1-125 named-Act boost x1.25 (precise)': {'top5': 14, 'top10': 16}, 'N2-125 named-Act boost x1.25 (broad)': {'top5': 14, 'top10': 16}}. Marks rules per finalist: {'N1-125 named-Act boost x1.25 (precise)': {'rule1_grade_all_four_settlements': False, 'rule2_misleading_and_useful_margins': True, 'rule3_two_more_questions_better': False, 'rule5_reliability_not_weak': True, 'marks_rules_hold': False, 'rule6a_lookalike_misleading_5_points_lower': False}, 'N2-125 named-Act boost x1.25 (broad)': {'rule1_grade_all_four_settlements': False, 'rule2_misleading_and_useful_margins': True, 'rule3_two_more_questions_better': False, 'rule5_reliability_not_weak': True, 'marks_rules_hold': False, 'rule6a_lookalike_misleading_5_points_lower': False}}. Floors of the chosen recipe F1/F2/F4: {'F1': False, 'F2': True, 'F4': True}.

Never to be written as 'X% accurate'. Mr. Advocate reads every passage marked Misleading by any run and a random 20 of the others before anything leaves the project.
