# LLM review results (real replies)

**Source label for everything below: LLM-judged. None of it is lawyer-validated.**

Runs read: 6 (ChatGPT-J/A, ChatGPT-J/B, ChatGPT-SK/A, ChatGPT-SK/TA, Gemini-J/A, Gemini-J/B); passages covered by at least one run: 199 of 199.

## File problems

- `Q09_A_ChatGPT-SK.txt`: passage 2: evidence quote is not in the passage text (possible invented quote)
- `Q12_A_Gemini-J.txt`: passage 2: evidence quote is not in the passage text (possible invented quote)
- `Q12_A_Gemini-J.txt`: passage 3: evidence quote is not in the passage text (possible invented quote)
- `Q12_A_Gemini-J.txt`: passage 4: evidence quote is not in the passage text (possible invented quote)
- `Q12_A_Gemini-J.txt`: passage 6: evidence quote is not in the passage text (possible invented quote)
- `Q12_A_Gemini-J.txt`: passage 8: evidence quote is not in the passage text (possible invented quote)
- `Q12_A_Gemini-J.txt`: passage 11: evidence quote is not in the passage text (possible invented quote)
- `Q12_B_Gemini-J.txt`: passage 2: evidence quote is not in the passage text (possible invented quote)
- `Q12_B_Gemini-J.txt`: passage 3: evidence quote is not in the passage text (possible invented quote)
- `Q12_B_Gemini-J.txt`: passage 4: evidence quote is not in the passage text (possible invented quote)
- `Q12_B_Gemini-J.txt`: passage 6: evidence quote is not in the passage text (possible invented quote)
- `Q12_B_Gemini-J.txt`: passage 8: evidence quote is not in the passage text (possible invented quote)
- `Q12_B_Gemini-J.txt`: passage 11: evidence quote is not in the passage text (possible invented quote)

## Evidence quotes

- 361 of 374 quotes found verbatim in the passage; 13 not found (possible invented quotes); 0 empty.

## Agreement between runs

| Run A | Run B | Comparison | Passages | Agree (4 marks) | Kappa (4 marks) | Agree (useful vs not) | Kappa (useful vs not) |
|---|---|---|---|---|---|---|---|
| ChatGPT-J/A | ChatGPT-J/B | same model, A vs B | 86 | 0.77 | 0.61 | 0.94 | 0.67 |
| ChatGPT-J/A | ChatGPT-SK/A | different models | 16 | 0.81 | 0.65 | 0.88 | 0.43 |
| ChatGPT-J/B | ChatGPT-SK/A | different models | 16 | 0.69 | 0.38 | 0.94 | 0.64 |
| Gemini-J/A | Gemini-J/B | same model, A vs B | 73 | 0.90 | 0.86 | 0.97 | 0.93 |

Rule of thumb: kappa below 0.4 is weak agreement, 0.4 to 0.6 moderate, above 0.6 good. 'Same model, A vs B' measures sensitivity to passage order.

## Consensus marks (plurality of all runs)

Yes: 67 | Partly: 82 | No: 16 | Misleading: 11 | split: 23 | None: 0

Passages marked Misleading by at least one run: 18

## How good is what each search version shows (LLM-judged consensus)

| Version | Questions judged | Top-5 slots | Unjudged slots | Yes share | Yes or Partly | Misleading | Yes (plain questions) | Yes (legal questions) |
|---|---|---|---|---|---|---|---|---|
| A today | 12 | 59 | 9 | 0.45 | 0.82 | 0.09 | 0.50 | 0.39 |
| B no repeats | 12 | 60 | 9 | 0.45 | 0.82 | 0.07 | 0.50 | 0.39 |
| C rewrite | 6 | 29 | 0 | 0.83 | 0.92 | 0.07 | 0.83 | n/a |
| E no multiplier | 12 | 59 | 10 | 0.41 | 0.85 | 0.07 | 0.44 | 0.38 |
| F merged | 6 | 29 | 0 | 0.86 | 0.92 | 0.07 | 0.86 | n/a |
| L landmark key passages | 12 | 20 | 1 | 0.54 | 0.96 | 0.00 | 0.58 | 0.50 |
| M mine top 6 | 12 | 72 | 10 | 0.40 | 0.78 | 0.10 | 0.50 | 0.29 |
| S site shown | 12 | 64 | 7 | 0.36 | 0.90 | 0.02 | 0.53 | 0.19 |

Shares are averaged per question over the passages each version placed in its top 5; versions whose name starts with S or M (the site's own search, my pipeline's top 6) are scored on everything they showed. Only passages that were in the pool can be scored; 'L landmark key passages' is the set of verified paragraphs, not a search version.

## Sensitivity: do the scores depend on how disagreements between runs are handled?

The table above counts a passage only when the runs agree on its mark, so every passage they disagree on drops out. Here the same scores are recomputed four ways. Each cell is 'Yes share / Yes-or-Partly share', averaged per question over the questions marked so far. 'Ties to the lower mark' and 'Ties to the higher mark' keep every disagreement and settle it the unfavourable or favourable way. 'Each run alone' is the lowest to the highest score any single run gives. A version whose passages are only partly marked so far (for example the site's own extra passages before the top-up is marked) is scored on what has been marked. The last column compares each version with the baseline (A today) on the questions both were marked on, counting the treatments (agreed, lower, higher, each run) in which it comes out above, equal or below.

| Version | Questions judged | Agreed only | Ties to the lower mark | Ties to the higher mark | Each run alone | Against the baseline (same questions) |
|---|---|---|---|---|---|---|
| A today | 12 | 0.45 / 0.82 | 0.37 / 0.85 | 0.52 / 0.85 | 0.28 to 0.60 / 0.80 to 0.93 | baseline |
| B no repeats | 12 | 0.45 / 0.82 | 0.37 / 0.85 | 0.52 / 0.85 | 0.28 to 0.60 / 0.76 to 0.93 | above in 0, equal in 8, below in 0 |
| C rewrite | 6 | 0.83 / 0.92 | 0.83 / 0.92 | 0.83 / 0.92 | 0.80 to 0.88 / 0.87 to 1.00 | above in 8, equal in 0, below in 0 |
| E no multiplier | 12 | 0.41 / 0.85 | 0.32 / 0.81 | 0.45 / 0.85 | 0.28 to 0.50 / 0.68 to 0.93 | above in 0, equal in 1, below in 7 |
| F merged | 6 | 0.86 / 0.92 | 0.86 / 0.92 | 0.86 / 0.92 | 0.80 to 0.90 / 0.87 to 1.00 | above in 8, equal in 0, below in 0 |
| L landmark key passages | 12 | 0.54 / 0.96 | 0.50 / 0.96 | 0.54 / 0.96 | 0.40 to 0.75 / 0.90 to 1.00 | above in 6, equal in 1, below in 1 |
| M mine top 6 | 12 | 0.40 / 0.78 | 0.35 / 0.82 | 0.49 / 0.82 | 0.27 to 0.58 / 0.73 to 0.92 | above in 0, equal in 0, below in 8 |
| S site shown | 12 | 0.36 / 0.90 | 0.35 / 0.90 | 0.43 / 0.92 | 0.17 to 0.49 / 0.65 to 1.00 | above in 0, equal in 0, below in 8 |

Read it this way: a difference between versions is worth acting on only if it points the same way in every column and holds over more than a few questions. With 12 questions only big differences show; gaps that appear in one column and vanish in another are noise from the AI reviewer's own unsteadiness.
