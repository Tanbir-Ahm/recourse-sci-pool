# Review of Mr. Advocate's regex audit (2026-10-12; PRIVATE; dev check, no Voyage spend)

Input: `review_data/ruler/inputs/2026-10-12_mr_advocate_regex_audit.docx` (13 Acts, question-side and passage-side patterns, supplement for the PC Act and NDPS).
- `test_advocate_regex.py`: compiles his patterns in Python, counts what his and my passage markers match in the index, fires both question-side sets on the 30 used questions and on a 26-case hand-made suite, checks title variants and whether Hitesh Verma is in the index (yes, doc 1000252799, 5 Nov 2020). The first run had a parser bug of mine (it paired each Act with the next Act's patterns); it was found, fixed and rerun before any conclusion; only the second run counts.
- `followup.py`: the PWDVA passage pattern does not compile (an unclosed group) and its repair; precision of the standalone NDPS phrases; case-insensitive acronyms; hyphen and 'the' variants of Act titles; the supplement patterns.
The 30 questions are used up: nothing here shows that the boost works. The hand-made suite was written by me and favours my own anchors; treat it as an illustration of the precision/recall trade-off.
