# Owner's staging re-test of the section-17 fixes (2026-10-20, `staging-site`, Recourse 72be728 with PASSAGE_NOTES=on)

Files: `answers_q1_q4_as_pasted.txt` (the four answers, as pasted), `staging_logs.log` (Railway log of the same session).

## What the logs and pages show (Certain)
- Section 17 first in every turn: `named` in turns 1, 3, 4, `implied` in turn 2. BNS 17 is not in the material. No 17A in its place.
- `SECTION_NOTE ... s.17: official` in all four turns; the grey box with the whole official text is under every answer.
- All four answers set out the first and the second proviso.
- Turn 1: `SCI_FEED_FILTER` dropped Radhy Shyam (section 17 of another law). No label inside a case name.
- Voice notices reached the page and the model used one in Q4 ("one judge's view, not the Court's holding"). No `PASSAGE_NOTE_FLAG` line in any turn.
- Cost Rs 3.41 / 3.82 / 3.87 / 3.66 per turn.

## What it shows that is wrong or missing
1. Section 13 never reached the model (ACT_SHELF matches: 17, 17A, 19, 20; 17A, 19, 20, 23; 17A, 19, 20, 23; 20, 19, 17A, 18A). The second proviso of section 17 points at "clause (b) of sub-section (1) of section 13", and in the shelf's own text section 13(1)(b) with its Explanation 1 is the disproportionate-assets offence. So for the owner's scenario the second proviso is the decisive point (an order of an officer not below Superintendent of Police). The four answers state the proviso but never say it is the disproportionate-assets clause, and Q1 opens "Yes ... can usually be registered and investigated without the approval required under Section 17". Cause: no code follows a cross-reference from a named section to the section it cites.
2. Q1: the model put "approval to file the case" in quotation marks (the owner's own idea, not a quotation); the quote check flagged it (nearest 0.85, "the previous approval a in the case of a"). A harmless false alarm that tells the reader "unverified".
3. Q2 and Q3/Q4 go beyond the wider-search passages: Sudhakar Reddy is said to mean that a later-false report "does not undo" the FIR (the passage says the scope of a preliminary inquiry is not to verify absolute truthfulness); the Shri Ram Singh claim "authorised to investigate ... except clause (e)" is not in the ~600 characters the page shows (the model gets up to 900; not checked which).
4. Q4 states "irregularities ... don't automatically void proceedings unless failure of justice is shown" and "a chargesheet ... can be challenged on that footing" with no passage behind them; Q2 said, correctly, that the material shows no ruling on the consequence of a missing section 17 order.
5. Voice labels: Surya Sankaram Karri para (Q3) is labelled "a party's submission" but reads as the investigating officer's evidence plus the Special Judge's holding; Santosh Karnani para 33 (Q4) is labelled a party's submission, not checked against the judgment. Neither was cited in an answer.
6. Fit: Thommandru Hannah Vijayalakshmi (no preliminary enquiry needed before an FIR) is used in Q1 for a question about section 17. Belongs to `SUPPORT_AND_FIT_PLAN.md` (deferred).

No lawyer has read these answers. One conversation of four questions on one topic is not a measure.
