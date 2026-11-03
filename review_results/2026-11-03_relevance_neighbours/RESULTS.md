# Relevance gate: does "keep the neighbours of a kept section" fix it? (owner's "run D first", 2026-11-03)

**Answer: no, and the measurement shows a larger problem with the floor itself.**

## What was run
* **36 fresh questions** (`questions_fresh.py`), written by Claude (not a lawyer), **committed before any retrieval was run on them** (commit `d8e2196`; file hash `e0f0460646a703c4`). 43 expected sections in all, chosen from the question alone; each number was checked against the title of the library's chunk, not against a retrieval result. None of these questions was seen when the floors were chosen.
* `run.py` ran the library search with the gate off and the Voyage re-ranker on each result (same protocol as 2026-10-31); `scores_fresh.json` holds every passage. It must be run from the Recourse checkout (the retrieval reads its data relative to it).
* `analyze.py` and `sweep.py` count, from those scores (outputs: `analyze_output.txt`, `sweep_output.txt`).

## Findings
1. **On the fresh questions the gate as built (statute floor 0.45) drops 3 of the 36 expected sections the search returned (8%).** On the 47 questions that chose the floor it dropped 0 of 24, as it had to: the floor was tuned on them. The three: BNSS 483 (rerank 0.375; "the prosecution says I broke my bail conditions"), BNSS 175 (0.424; refusal to register an FIR) and BNSS 251 (0.431; framing of charge). Small numbers (3 of 36); the sections and questions are mine.
2. **The neighbour rule gives back 1 of those 3** (BNSS 175, next to BNSS 173 which scored above the floor) with a window of one section, the same with two (plus two sections that were not expected). It cannot help BNSS 483 (no neighbour above the floor in that pool) or BNSS 251 (BNSS 250 was not retrieved).
3. **On the live anticipatory-bail run (owner's log, 2026-11-03) it would have rescued nothing.** The gate's report lists every passage it scored with a `kept` flag; in question 1 all six (BNSS 479, 60, 483, 487, 481 and M. Ravindran) were below the floor, so there was no kept section to be a neighbour of. In question 2 the same (BNSS 142, 492, 483, 143, 480, Vihaan Kumar). **Correction of my earlier message:** I said BNSS 482 "was not on the list, so it is kept". It was not in the gate's pool at all (it reached the answer by another route, not through the library search that the gate reads); every library passage of question 1 was below the floor, so `on` would have emptied the library's share, 483 included. In question 2 the carry-forward would have put 483 back.
4. **Lowering the floor does not fix it either** (`sweep_output.txt`). Fresh questions: floor 0.45 drops 3 expected and hands over 55 of 73 sections that were not expected; 0.42 drops 1 and hands over 62; 0.36 drops 0 and hands over 67 (92%). A floor low enough to keep every expected section removes almost nothing. ("Not expected" is not the same as irrelevant: neighbours are often useful; I did not read all 73.)

## What it means
* The re-ranker score does not separate a section that answers from one that does not well enough for a fixed floor to be safe: in this set it loses about one expected section in twelve on questions it was not tuned on, and at the floor that avoids that it removes next to nothing.
* The neighbour rule is not worth building. **Keep `RELEVANCE_GATE` on `log` (or off).** The clutter the gate was meant to stop is now handled for the lawyers' note by the strict "rests on" list; the sections that were handed over and not used did not reach either anticipatory-bail answer.
* Not tried: a gate that acts only when the library's best section is below a high bar (the circumstantial-evidence case, best 0.407); a different re-ranker model. Neither is measured; both would need a fresh question set.

## Limits
36 questions written by Claude with expected sections chosen by Claude; 43 expected sections of which the search returned 36; the three drops are 3 of 36; no lawyer has read any of it. No hallucination rate has been measured.
