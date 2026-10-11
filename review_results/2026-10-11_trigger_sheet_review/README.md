# Review of the owner's trigger workbook (2026-10-11; PRIVATE; no Voyage spend except well under one cent for the phrase embeddings)

- `trigger_audit.py` (output `trigger_audit.json`): how common each Act's strong passage marker is in the index; what the workbook's original phrases fire on for the 30 used questions with a fuzzy matcher.
- `machine_spec_test.py`: literal anchors for 13 Acts on the 30 used questions; label coverage; semantic routing (rejected).
- `build_appended_workbook.py`: writes `review_data/ruler/inputs/2026-10-11_trigger_workbook_with_claude_appends.xlsx` (original five sheets unchanged, three sheets appended).
The 30 questions are used up: these are dev checks, not evidence that the boost works. Legal content (section numbers, case details, links) is NOT verified by me; Mr. Advocate to confirm.
