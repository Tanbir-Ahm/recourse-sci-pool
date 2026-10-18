# Quote check: meaning-critical words (2026-10-18)

What this folder shows: the quote check (`grounding_checks.py` in Recourse) used to accept a quotation that was only a 95% letter match of the material, so a single decisive word (not, may/shall, and/or, a number) could change in a long quotation without a flag. The check now also requires those words to agree. This folder holds the test that measured it.

- `quote_fix_study.py`: takes random 22 to 48 word spans of real library text (Recourse `chunks/*.json`), changes each in one way, puts it in quotation marks and runs the old and the new check. Usage (from the Recourse checkout): `python -I quote_fix_study.py grounding_checks_before.py <seed> <n>`.
- `grounding_checks_before.py`: the check as it was before the change (Recourse `f068f98`/`1ce4de4`).
- `results_seed11_n700.txt`, `results_seed23_n500.txt`: the output, two independent random samples.

Pooled over both samples ("old accepted" = quotes the old check let through):

| edit | tried | old check flagged | new check flagged |
|---|---|---|---|
| a decisive word deleted | 1,150 | 143 (12%) | 1,137 (99%) |
| a decisive word swapped (may/shall, and/or, not/now, any/no ...) | 1,033 | 72 (7%) | 1,026 (99%) |
| a number changed | 579 | 30 (5%) | 570 (98%) |
| harmless edits (a dropped article or preposition, two dropped, a small word added, hyphen to space, an ordinary word with an extra s) | about 4,100 accepted by the old check | | 1 newly flagged (0.02%) |

Not caught (19 of about 1,610 decisive edits in the first sample): 5 are in quotations cut by a [bracket] or "..." into pieces under five words, which the check does not test; 14 contain quotation marks of their own (for example "OMs"), which end the quotation early. These are limits of how quotations are found, not of the new rule.

These are AI-made edits of real text, not real model mistakes, so the percentages say how well the rule sees such edits, not how often answers contain them. Nobody has measured the second figure.
