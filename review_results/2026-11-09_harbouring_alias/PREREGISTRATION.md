# Harbouring alias: pre-registration (written 2026-11-09, BEFORE any retrieval was run on these questions and BEFORE any alias code exists)

**Trigger (measured miss).** The owner's 2026-11-08 staging answer (a person who gave a lift to an absconding prime accused and was arrested). The offline harness (`review_results/2026-11-03_retrieval_misses/run_e2e.py`, config `fixes`) reproduces the material the answer had and BNS 249 (harbouring an offender) is not in it. That one question is the SEEN case; it is reported separately and is not counted.

**The rule being followed** (`statute_aliases.py` docstring, FOLLOW_UPS 2de): a new alias needs a miss that was measured, word groups written before the question set is looked at, a negative list, and a test; no tuning on the set that measures it.

**Entries (the exact regular expressions are in `groups_as_written.py`, committed before the run):**
* `bns_249_harbour` -> BNS 249 (harbouring an offender; knows or has reason to believe; intention of screening; at most 5 years).
* `bns_253_harbour_escaped_or_ordered` -> BNS 253 (harbouring a person who escaped from lawful custody or whose apprehension a public servant ordered).
* `bns_254_harbour_robbers` -> BNS 254 (harbouring robbers or dacoits; up to 7 years).
The alias hands over the library's own text of the section, no commentary, marked retrieval `alias` (the existing mechanism). It says nothing about whether the person is guilty: it only puts the section in front of the answer model.

**Question sets (all written by Claude, not a lawyer; fixed here):** 24 positives for 249, 8 for 253, 4 for 254 (`questions_harbour.py`, kind `pos249`, `pos253`, `pos254`), and 40 negatives (kind `neg`): questions that mention arrest, absconding, hiding, giving a lift, shelter, "harbouring" in another sense, or a fugitive, but are NOT about helping a wanted person; the alias must not fire on them. Also: every question of the earlier question modules in `review_results/2026-11-03_retrieval_misses/` and `2026-10-31_relevance_gate/` is run through the word groups alone (no retrieval) to count unintended fires.

**What is measured.** Positives: the expected section is among the material that reaches the answer model (baseline = today's code with the same switches; after = with the entries). Negatives: an entry fires (count; each fire read by eye). Legacy sets: fires counted and read.

**Success rule fixed in advance.** Positives: 249 reaches the prompt for at least 22 of 24 after the change; 253 at least 6 of 8; 254 at least 3 of 4. Negatives: at most 2 of 40 fire. Legacy sets: every fire is read; any fire on a question that is not about helping a wanted person counts as a false fire. If a rule fails I report it and do NOT edit the word groups on these questions; a further change needs a NEW question set.

**What this cannot show.** Whether the answer model uses the section well (no Anthropic key in the sandbox; the owner's staging test is the test); whether a lawyer agrees the section is the right one for each question (only Claude chose the expected sections); whether real users phrase it this way. No hallucination rate has been measured.
