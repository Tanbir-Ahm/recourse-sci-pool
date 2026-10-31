# Relevance gate (`RELEVANCE_GATE`), item 1 of the owner's list of 2026-10-31

**Problem (owner's critique of a staging answer):** point 4 of the answer was BNSS section 249 (the prosecutor's opening statement in a sessions trial), which has nothing to do with the question. It was filler, and arguably misleading.

**Cause (measured):** the library search keeps a section if its cosine similarity to the question clears 0.34 (statutes) or 0.40 (judgments). Cosine is not an absolute measure of relevance: irrelevant sections often score 0.42 to 0.44. So up to five sections are always handed over, however far they are from the question.

**Fix (Recourse `relevance_gate.py`, switch `RELEVANCE_GATE=off|log|on`, default off):** after the cosine step, the kept passages are scored by the Voyage re-ranker (`rerank`) and those below a floor are dropped (statute 0.45, judgment 0.40). `log` only writes a `RELEVANCE_GATE` line; `on` removes them. A section that the person named by number (exact hit) is never removed. It fails open: if the re-ranker returns nothing, nothing is removed. If `on` removes everything, the question goes to the wider search alone (`RELEVANCE_GATE_WIDER_ONLY`) instead of ending in a refusal. Two prompt sentences (v3 Adviser and lawyer note): cite a section only if it answers the question; a section is not relevant because it was supplied.

## What I measured (47 questions written by Claude, not a lawyer; `questions.py`, `run.py`, `scores.json` here)
29 positive questions with expected sections (30 expected sections in all) and 18 negative questions (evidence-law and civil questions where the library has no section that answers).
* Floors were chosen on these same 47 questions. **There is no held-out half.** Treat the figures below as a description of this set, not as a forecast.
* Expected sections that the library search returned at all: **24 of 30**. All 24 survive the gate (24 of 24). The other 6 were never retrieved; the gate cannot help with those (BNS 115, BNSS 482, 187, 528, 359 among them): a side finding, library retrieval misses them for these questions.
* On the positive questions the gate removes 16 of 114 returned passages; of the 49 statute passages that were not an expected section it removes 12 (the rest stay: a "not expected" section is often a neighbour that is truly relevant, e.g. BNS 305/306/307 beside 303 for theft).
* On the 18 negative questions, 9 of 12 that had an answer-state before lose every passage under the floors, so `on` would send them to the wider search alone; **"Is a confession made to a police officer admissible?" keeps all 5 (BNSS sections on confessions score above the floor)**, and a few keep 1 or 2. 6 were already `no_match`.

## What it cannot do
* It does not make a left-over section correct; a section above 0.45 may still be a neighbour that does not fit.
* The floor is a re-ranker score, not a legal test. Different questions will need a different floor; the variables `RELEVANCE_STATUTE_FLOOR` and `RELEVANCE_JUDGMENT_FLOOR` exist for the owner to move them.
* When `on` empties the library, the answer rests on the wider search (feed mode) or ends "Not enough to go on yet". In-scope questions on general evidence law (hostile witness, hearsay, res gestae) already ended as `no_match` before; whether they should be answered from the wider search alone is the owner's decision.
* Cost: one extra re-rank call per question (a few passages; cents).
* Not tried with the answer model; no lawyer has read any output. No hallucination rate has been measured.

## Tests
`test_relevance_gate.py` 19 checks (off/log/on, emptied, exact section kept, re-ranker failure, floors from the environment, wiring through `find_relevant_sections`, prompt sentences present); `test_hybrid_search.py`, `test_answer_style_v3.py`, `test_sci_search_tier.py`, `test_authority_notes.py` pass; the full free suite passes except `test_site_e2e.py` ("after accepting: who is signed in, 10 of 10 left"), which fails identically with the gate stashed away (pre-existing, environment).
