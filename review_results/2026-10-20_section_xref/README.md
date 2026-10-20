# SECTION_XREF: a named section brings the sections of its own Act that it cites (2026-10-20)

Owner's go: "build 1 and 2 together, with tests using section 17 pointing to section 13 and the CrPC reference skipped". Recourse branch `register-hooks-and-overlay`, commit `fdf24e8` (NOT on `main`). Switch `SECTION_XREF` (default OFF; acts only with `ACT_SHELF` on).

| File | What it is |
|---|---|
| `replay_xref_off.txt`, `replay_xref_on.txt` | The owner's four section-17 questions replayed through the engine's section handling (`../2026-10-19_section_17_staging_fixes/replay_fix1.py`, real Voyage question vector, no answer model). Off: section 13 reaches the model in turn 3 only (by meaning, and that turn's text is an earlier question of the owner's). On: section 13 is handed over in all four turns (`cited` in turns 1, 2, 4). |
| `stress_xref_all_sections.py`, `..._output.txt` | Every one of the 370 askable sections of the seven searched-by-meaning Acts asked about by number, stored question vector, switch on: 0 violations of the invariants (a cited section is a real, non-omitted section of the same Act, word for word the shelf's text; at most two; none twice; none added by a fan-out section). |

## What it does
1. `act_shelf.cited_sections` reads the asked section's OWN text for "section N" references. Skipped: a reference followed at once by another enactment's name ("section 8 of the Code of Criminal Procedure, 1973", "of that Code", "of the [Code]", "sections 262 to 265 ... of the said Code", "section 153A (45 of 1860)", "of the Act"), an amending note's "s. 5" or "(3 of 2013), s. 5", anything inside India Code's "[Note: ...]" paragraph, a self-reference, a number the Act does not have, an omitted section. A section that cites MORE than two others (section 19 of the PC Act with its four; rule-making powers) is followed for none: all or none.
2. `_add_cited`: at most two cited sections, none over 4,000 characters, handed over as retrieval `cited`; one is not added twice if it was named or came by meaning.
3. The prompt gets one more bullet inside "The section the person asked about" (not the Hard rules): section 17 refers to section 13, which is in the material; say in one sentence, from that text only, what the cited section covers; do not go beyond it. The section's block in the material carries "(Cited by section 17 of the same Act, the section the person asked about.)".
4. The grey box under the answer carries the cited section's whole official text, word for word, under one sentence that says nothing about what it means. Written by code; the model is not involved.
5. Logs: `ACT_SHELF` gets `cited`/`cite_skipped`; `SECTION_NOTE` gets "+cites 13".

## Evidence and limits
- `test_section_xref.py`: 90 checks; clean-checkout suite 89 of 89 (`run_tests.py`).
- Across the nine Acts 396 sections: 104 cite one or two sections of their own Act, 13 are skipped as fan-out. A read of 45 accepted and 45 skipped references found the false ties that are now fixed (a "section 2 of the Persons with Disabilities ... Act, 1995" in JJ s.85, "sections 262 to 265 of the said Code", an Act named later in the same sentence); the sample is not exhaustive and the rule is a pattern, not a parser.
- It follows only citations written as "section N". "The offence of criminal misconduct" without a number is not followed.
- Whether the model, given section 13, writes that the second proviso concerns disproportionate assets is NOT known (no model key in the sandbox): the staging test (`DEPLOY_STAGING.md` Part 4q, step 0) shows it. The grey box shows the words of section 13(1)(b) and Explanation 1 whatever the model writes.
- Not wired to WhatsApp (the box); the cited sections do reach the WhatsApp prompt when the switch is on.
