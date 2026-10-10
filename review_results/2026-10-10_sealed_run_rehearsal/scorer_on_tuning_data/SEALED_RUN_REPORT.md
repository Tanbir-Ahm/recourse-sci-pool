# Sealed-run report (PRIVATE; LLM-judged: no lawyer has checked any of it)

**Outcome: Floors met, at least one domain eligible: the recipe may go to shadow mode in the eligible domains only**

Reliability: the two tools agree exactly on 73% of the passages (ok). Coverage complete: True. Chosen arm: **A today** (the status quo stays).

## Floors on the chosen arm (ties to the lower mark unless stated)

| Floor | Value | Needed | Met | |
|---|---|---|---|---|
| F1 useful share | 75% | at least 70% | True | weak pass |
| F2 Misleading share | 13% (ties lower), 6% (ties higher) | at most 15% and 10% | True | weak pass |
| F3 named authority in the top 10 | 71% of 14 answerable | at least 60% | True | weak pass |
| F4 direct (Yes) share | 33% | at least 25% | True | weak pass |

## The two re-rankers (top 5 shares, averaged over questions)

| Settlement | A: Yes / useful / Misleading / grade | R: same | questions R better / worse |
|---|---|---|---|
| ChatGPT alone | 50% / 87% / 11% / 2.26 | 56% / 91% / 9% / 2.39 | 2 / 0 |
| Gemini alone | 43% / 80% / 13% / 2.10 | 50% / 84% / 9% / 2.26 | 2 / 0 |
| both, ties to the lower mark | 39% / 79% / 14% / 2.03 | 47% / 81% / 11% / 2.17 | 2 / 0 |
| both, ties to the higher mark | 54% / 90% / 7% / 2.37 | 59% / 94% / 6% / 2.47 | 2 / 0 |

Rules on the marks (1, 2, 3, 5): {'rule1_grade_all_four_settlements': True, 'rule2_misleading_and_useful_margins': True, 'rule3_two_more_questions_better': True, 'rule5_reliability_not_weak': True, 'marks_rules_hold': True}
Rule 4 (named authority in the top 5 and known-stale count, not worse): False; named authority {'A today': {'top5': 10, 'top10': 10, 'answerable': 14}, 'R challenger re-ranker top 5': {'top5': 9, 'top10': 9, 'answerable': 14}}; known-stale passages in the top 5 {'A today': 4, 'R challenger re-ranker top 5': 1}.

## Safety net (D3)

{'keep_the_net': True, 'passages': 52, 'mis_lower': 0.030701754385964907, 'useful_lower': 0.5614035087719299, 'yes_by_every_run': 9}

## Domains

| Domain | relevance (lower / higher ties) | currency | the sealed question alone | eligible |
|---|---|---|---|---|
| A | green / green | no trap (0 of 0) | {'both, ties to the lower mark': ['green', 'green'], 'both, ties to the higher mark': ['green', 'green']} | True |
| B | green / green | green (0 of 1) | {'both, ties to the lower mark': ['green'], 'both, ties to the higher mark': ['green']} | True |
| C | red / green | red (1 of 1) | {'both, ties to the lower mark': ['red', 'red'], 'both, ties to the higher mark': ['green', 'green']} | False |
| D | amber / amber | green (0 of 1) | {'both, ties to the lower mark': ['amber'], 'both, ties to the higher mark': ['amber']} | True |
| E | amber / green | no trap (0 of 0) | {'both, ties to the lower mark': ['green', 'red'], 'both, ties to the higher mark': ['green', 'green']} | False |
| F | green / green | red (1 of 1) | {'both, ties to the lower mark': ['green'], 'both, ties to the higher mark': ['green']} | False |
| G | amber / green | no trap (0 of 0) | {'both, ties to the lower mark': ['green', 'red'], 'both, ties to the higher mark': ['green', 'green']} | False |
| H | red / red | red (1 of 1) | {'both, ties to the lower mark': ['red'], 'both, ties to the higher mark': ['red']} | False |
| I | green / green | no trap (0 of 0) | {'both, ties to the lower mark': ['green'], 'both, ties to the higher mark': ['green']} | True |
| J | green / green | no trap (0 of 0) | {'both, ties to the lower mark': ['green'], 'both, ties to the higher mark': ['green']} | True |

Currency overall (without the register): {'light': 'red', 'let_through': '3 of 5'}.

Answerable: R01, R02, R04, R08, R09, R11, R12, R14, R17, R19, R20, R22, R24, R26. Index gaps and controls (reported apart): R06, R15, R21, R28, R29.

Never to be written as 'X% accurate'. Mr. Advocate reads every passage marked Misleading by any run and a random 20 of the others before anything leaves the project.
