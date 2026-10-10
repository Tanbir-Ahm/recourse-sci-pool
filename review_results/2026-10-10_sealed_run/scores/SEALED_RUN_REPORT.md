# Sealed-run report (PRIVATE; LLM-judged: no lawyer has checked any of it)

**Outcome: A floor is missed: nothing is connected; the sealed half is used up, any new final test needs new questions**

Reliability: the two tools agree exactly on 64% of the passages (ok). Coverage complete: True. Chosen arm: **R challenger re-ranker** (the challenger wins under the rules).

## Floors on the chosen arm (ties to the lower mark unless stated)

| Floor | Value | Needed | Met | |
|---|---|---|---|---|
| F1 useful share | 69% | at least 70% | False | weak pass |
| F2 Misleading share | 18% (ties lower), 5% (ties higher) | at most 15% and 10% | False | weak pass |
| F3 named authority in the top 10 | 60% of 10 answerable | at least 60% | True | weak pass |
| F4 direct (Yes) share | 35% | at least 25% | True | weak pass |

## The two re-rankers (top 5 shares, averaged over questions)

| Settlement | A: Yes / useful / Misleading / grade | R: same | questions R better / worse |
|---|---|---|---|
| ChatGPT alone | 40% / 82% / 11% / 2.11 | 44% / 93% / 5% / 2.31 | 2 / 0 |
| Gemini alone | 33% / 65% / 18% / 1.80 | 42% / 69% / 18% / 1.93 | 2 / 1 |
| both, ties to the lower mark | 27% / 65% / 22% / 1.71 | 35% / 69% / 18% / 1.85 | 3 / 1 |
| both, ties to the higher mark | 45% / 82% / 7% / 2.20 | 51% / 93% / 5% / 2.38 | 2 / 0 |

Rules on the marks (1, 2, 3, 5): {'rule1_grade_all_four_settlements': True, 'rule2_misleading_and_useful_margins': True, 'rule3_two_more_questions_better': True, 'rule5_reliability_not_weak': True, 'marks_rules_hold': True}
Rule 4 (named authority in the top 5 and known-stale count, not worse): True; named authority {'A today': {'top5': 6, 'top10': 6, 'answerable': 10}, 'R challenger re-ranker': {'top5': 6, 'top10': 6, 'answerable': 10}}; known-stale passages in the top 5 {'A today': 4, 'R challenger re-ranker': 3}.

## Safety net (D3)

{'keep_the_net': False, 'passages': 33, 'mis_lower': 0.13636363636363635, 'useful_lower': 0.41818181818181815, 'yes_by_every_run': 5}

## Domains

| Domain | relevance (lower / higher ties) | currency | the sealed question alone | eligible |
|---|---|---|---|---|
| A | green / green | no trap (0 of 0) | {'both, ties to the lower mark': ['green'], 'both, ties to the higher mark': ['green']} | False |
| B | green / green | green (0 of 2) | {'both, ties to the lower mark': ['green'], 'both, ties to the higher mark': ['green']} | False |
| C | amber / amber | amber (1 of 2) | {'both, ties to the lower mark': ['green'], 'both, ties to the higher mark': ['green']} | False |
| D | red / red | amber (1 of 2) | {'both, ties to the lower mark': ['red'], 'both, ties to the higher mark': ['red']} | False |
| E | amber / green | no trap (0 of 0) | {'both, ties to the lower mark': ['green'], 'both, ties to the higher mark': ['green']} | False |
| F | red / green | no trap (0 of 0) | {'both, ties to the lower mark': ['red'], 'both, ties to the higher mark': ['green']} | False |
| G | red / green | no trap (0 of 0) | {'both, ties to the lower mark': ['red'], 'both, ties to the higher mark': ['green']} | False |
| H | green / green | no trap (0 of 0) | {'both, ties to the lower mark': ['green'], 'both, ties to the higher mark': ['green']} | False |
| I | green / green | green (0 of 1) | {'both, ties to the lower mark': ['green'], 'both, ties to the higher mark': ['green']} | False |
| J | green / green | red (1 of 1) | {'both, ties to the lower mark': ['green'], 'both, ties to the higher mark': ['green']} | False |

Currency overall (without the register): {'light': 'amber', 'let_through': '3 of 8'}.

Answerable: R03, R05, R07, R10, R13, R16, R18, R23, R25, R27. Index gaps and controls (reported apart): R30.

Never to be written as 'X% accurate'. Mr. Advocate reads every passage marked Misleading by any run and a random 20 of the others before anything leaves the project.
