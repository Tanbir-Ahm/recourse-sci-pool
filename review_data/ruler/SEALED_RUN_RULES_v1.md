# Sealed-run rules, version 1: DRAFT of 2026-10-10 (PRIVATE; not frozen until the owner accepts it)

**Status.** Draft written at the owner's request ("Yes, draft those sealed-run rules"). Nothing here has been run. Written **without opening the sealed questions or their key**: only the ids (R03, R05, R07, R10, R13, R16, R18, R23, R25, R27, R30), the count (11) and the domain pattern were used. The domain of each sealed question is inferred from the plan's counts and the tuning ids [Likely]: one per domain, R03 A, R05 B, R07 C, R10 D, R13 E, R16 F, R18 G, R23 H, R25 I, R27 J, R30 K. Every number below is a **[Guessing]** threshold taken from the tuning half; it may be changed **only before the sealed questions are handed out**, by a dated amendment at the end of this file. Once the owner accepts, the file is frozen by recording its SHA-256 in `FOLLOW_UPS.md` and in `sealed_run_rules_v1.freeze` (command in section 10). All results carry the label **LLM-judged** (ChatGPT and Gemini, run by J and S); nothing here is lawyer-validated.

## In one page

1. **What the run decides:** (D1) rerank-2 or rerank-3-lite for the recipe; (D2) whether the recipe may go to the next step toward the lawyer panel ("not independently verified"), domain by domain; (D3) whether the safety net stays in the lawyer list; (D4) the final readiness map. **It decides nothing about the layperson mode** (it reads the verified corpus), **nothing about answer writing**, and it never allows the big index into the verified answer path.
2. **One run, once.** One frozen recipe, 11 sealed questions, both re-rankers as arms, the site's own search as a reference arm, every passage of every arm marked **in one shuffled round** by both tools (about 22 chats). No second look.
3. **Defaults if nothing is clear:** the status quo wins. rerank-2 stays unless rerank-3-lite is better in every way listed in section 5. Nothing is connected unless the floors in section 4 hold.
4. **Floors for the next step (chosen arm, all sealed questions pooled, ties to the lower mark):** useful (Yes or Partly) at least 70%; Misleading at most 15% (and at most 10% with ties to the higher mark); directly answering (Yes) at least 25%; the named authority in the top 10 for at least 60% of the answerable sealed questions. Tuning half for comparison: 75%, 13% (6%), 33%, 71%.
5. **Currency is judged by the plan's currency light** at the register's state on the day of the run; today the register holds few of the trap rulings, so a red light is likely and would keep those domains out until the register is extended and tested on new trap questions.
6. **A pass is not "X% accurate"** and is not a lawyer's clearance; Mr. Advocate reads every passage anyone marked Misleading, plus a sample, before any statement outside this project.

## 1. What is frozen

| Item | Value | Why |
|---|---|---|
| Index | `claude/sci-index` commit `3c80a26` (10,503 judgments with passages, 236,155 passages); the pool runner refuses another head | the plan; **no bucket refresh before the run is over** (the 2026-10-12 refresh reminder must be answered "later") |
| Embedding | voyage-law-2 (model test, 2026-10-10: NOT-PASS for voyage-4-large) | settled |
| Retrieval | 100 by meaning + 50 by keyword + up to 30 per "section N", merged by reciprocal rank (K = 60) into 60 candidates | version A as tuned |
| Re-rankers | arm A: `rerank-2`; arm R: `rerank-3-lite`; the same 60 candidates, one call each, no instructions, text cut at 3,500 characters | re-ranker test, 2026-10-10 |
| After the re-ranker | passage-type weights and the 1.10 section boost **unchanged** for both arms (`sci_index.W`); no weights study before the run | a weights study on 19 questions would be tuning on the tuning half; deferred |
| Question text | exactly as written; **no rewrite arm** (versions C and F gave no gain) | tuning marks |
| Safety net | computed as an opt-in tail: the merged top 5 that the arm's ten do not show, ranked by the arm's own score, after place ten, at most 15; the first ten places are never touched | owner's correction, 2026-10-09 |
| Side indexes | **default: included** (the 17 correcting judgments, the two fetched documents) for both arms, as the final system would have them; "nothing else got worse" on the tuning half | **decision for the owner (section 11)** |
| Reference arm S | the Recourse site's own search code run over this index, no pins, no routing | the question "does the new pipeline beat what the site does today"; not part of D1 |
| Register / checker | **off** during search and marking; applied afterwards by `currency_pass.py` on the saved pools, at the register's commit on the day (recorded) | relevance numbers stay clean |
| Code | the commit of `pool_runner.py`, `sci_index.py` and the scorers is recorded in the run label and is not changed after the freeze | |

## 2. The marking round (one round, no confound)

- **Pool per question:** the union of A's top 10, R's top 10, S's shown list and the safety net(s); about 18 to 22 passages; shuffled with a fixed seed; the prompt says nothing about arms, re-rankers or the half. Roughly 220 passages in 11 files.
- **Both tools on every file, order A only** (the tuning round found no order effect: kappa 0.70 and 0.73 across orders). 22 chats. No anchors and no repeats are needed because the arms are compared inside the same round (the two-round confound that weakened the tuning-half comparison cannot occur).
- Same prompt text and rules as before; replies normalised by `normalise_replies.py` (backslashes only); a reply is accepted only if it is a reply, not a prompt, and not a duplicate of the other tool's file; **coverage must be 100%** (every passage marked by both tools) before any score is read.
- **Reliability flag:** if the two tools agree on fewer than 60% of the sealed passages (tuning: 70.5% and 75.5%), the result is reported as **weak** and Mr. Advocate's check becomes a condition of any use.

## 3. Measures (computed by one scorer, written and tested before the freeze, rehearsed on the tuning data)

Four settlements everywhere: ChatGPT alone, Gemini alone, both with ties to the lower mark, both with ties to the higher mark (plus "agreed only" in the summary table). Grades for averages: Misleading 0, No 1, Partly 2, Yes 3. Per arm and per question, on the top 5: share Yes, share useful (Yes or Partly), share Misleading, mean grade, whether a Misleading sits in the top 3, the place of the first Yes. **Automatic, no marks:** the named authority in the top 1, 5 and 10 for the answerable questions (answerable and index-gap questions are known only when the key is opened, section 8); known-stale rulings in the top 5; the ruler's frozen half (T08, T12, T13, T16) by the key-paragraph test only, labelled "well-known settled topics, Recourse's picks". Intervals: bootstrap over questions, 5,000 resamples, seed fixed in the scorer.

## 4. The floors (D2): may the recipe go on toward the lawyer panel?

Applied to the **chosen arm** (section 5), all sealed questions that have a mark, pooled; answerable questions for F3. The index-gap questions and controls are reported apart as in the tuning half.

| | Floor | Tuning half, version A (for comparison) |
|---|---|---|
| F1 useful (Yes or Partly) share of the top 5, ties to the lower mark | at least 70% | 75% (ties higher 87%) |
| F2 Misleading share of the top 5 | at most 15% (ties lower) **and** at most 10% (ties higher) | 13% and 6% |
| F3 named authority in the top 10, answerable questions | at least 60% | 10 of 14 = 71% |
| F4 directly answering (Yes) share, ties to the lower mark | at least 25% | 33% (ties higher 51%) |

All four must hold. A floor met with the lower end of its interval above it is called a **clear pass**; met by the point value only, a **weak pass**; the report says which. I expect that even if the true quality equalled the tuning half, noise on 11 questions would make at least one floor fail by chance in roughly **35 to 45%** of repeats [Guessing]; the floors are therefore minimums for an unverified panel, not a prediction.

**Currency (the plan's currency light, unchanged definition).** For the sealed trap questions: green = no known-stale ruling in the top 5; red = one in the top 5 of more than half; amber otherwise; computed without the register and, separately, with the register's demotion and the "not checked by us" wording of the standing item. **Domain eligibility for the next step = relevance light green or amber, currency light not red, floors F1 to F4 met overall, and the domain's own sealed question not red on its own.** Lights per domain use all questions of the domain (tuning marks of the chosen arm and the sealed marks); the tuning marks of arm R are complete for its top 5. Because the register held only a minority of the trap rulings when the file was reviewed (4 of the 13 trap questions' stale rulings, whole set), expect red currency lights; an extension of the register and a new test on new trap questions (not these) is what turns them.

## 5. Choosing the re-ranker (D1): the status quo wins ties

R replaces A **only if all of the following hold**, on the sealed questions with marks:

1. In **all four settlements**, R's pooled top-5 mean grade is at least A's.
2. In both "both" settlements, R's Misleading share is at most A's + 2 points, and R's useful share is at least A's - 2 points.
3. In both "both" settlements, counting questions where the mean grade of the top 5 differs by at least 0.4 (two one-step changes), **R is better on at least two more questions than it is worse.**
4. Automatic: the named authority in the top 5 for R is at least A's count; known-stale passages in the top 5 summed over questions: R at most A.
5. R's reliability note (section 2) is not "weak".

Otherwise A stays. If A fails the floors and R meets them, R is chosen only if it also satisfies 1 to 5; if both fail, neither goes on. I expect R to win under these terms with probability about **20 to 25%** [Guessing]: 11 questions cannot show a small gain, and the rule asks for a visible one. Cost is not a tie-breaker in the rule (rerank-3-lite is listed at $0.02 per million tokens against $0.05, unchecked).

## 6. The safety net (D3)

Kept in the lawyer list only if, pooled over the sealed questions, ties to the lower mark: its Misleading share is at most 5% (tuning 2 to 3%), its useful share at least 55% (tuning 56 to 71%), and at least 5 of its passages were marked Yes by every run that marked them (tuning 9 of 52). Otherwise the list is the ten alone. Never in the top 5.

## 7. Outcomes, agreed in advance

| Result | Meaning | Next step |
|---|---|---|
| Floors met, at least one domain eligible | the recipe may go to **shadow mode** (agreed in principle: background job, nothing shown to users, redacted or hashed questions, own Voyage key), then to the "not independently verified" panel in the eligible domains only (arrest and bail first), with register warnings and the "not checked by us" wording | the register patch applied by the owner (staging first), the trap exam run, Mr. Advocate's check; **never** the verified answer path |
| Floors met, no domain eligible (lights red) | retrieval is fit, currency is not | extend the register and test on new trap questions; no connection |
| A floor missed | the tuning-half results do not carry over | nothing is connected; the sealed half is used up, so any new final test needs **new questions** (written by someone who has not seen the sealed ones); the reasons are written up |
| Mixed (clear floor misses in one domain only) | only that domain is excluded | as above for the rest |

## 8. Order of events and hygiene

1. Owner accepts or amends; the file is frozen and hashed (section 10).
2. Build, test and review (no sealed data): the second re-ranker arm in `pool_runner.py` with its tests (today the model is a constant), the sealed pack builder, the scorer implementing sections 3 to 6, a **rehearsal of the scorer on the tuning data** (to see the floors on known numbers and to prove the code), the run label and the code commit recorded.
3. Preconditions checked and written down: index head `3c80a26`; Voyage balance still above the $5 live-site reserve after the run's cost (about 0.5 million re-rank tokens, a few cents, cap 2 million); side-index decision made; refresh postponed.
4. **The sealed pool is built once**: `pool_runner.py --half sealed --final --label "..."` (the guard hands the questions out once and logs it; `allow_repeat` is not used); the ruler's frozen half has its own guard (`--source ruler --half sealed --final --label "..."`) and is run in the same session for the key-paragraph test only. A technical failure before any mark exists may be repeated, logged as such; after a mark exists nothing is re-run and nothing is changed.
5. The pack goes to J and S; replies come back; coverage 100%.
6. **The key is opened only now**, after the marks are ingested and the key-free scores are written; then the key-dependent scoring runs once (answerable or gap, named authority, stale list, lights) and every number is reported whatever it is.
7. Report in plain terms: all four settlements, intervals, the label, the weak-pass or clear-pass wording; no "X% accurate".
8. Mr. Advocate reads every sealed passage marked Misleading by any run and a random 20 of the others before anything leaves the project.

## 9. What the run cannot show

Answer writing (the model that words an answer has never been measured); the register's correctness (the trap exam); anything a lawyer would grade; real users' questions (the set is re-told from reported cases, a best case); High Court or 2026 law (the index is Supreme Court, partial for 2026); whether the next snapshot behaves the same (later snapshots get a cheap automatic regression check on the tuning half, not another sealed run). Eleven questions, one per domain, give a pooled reading and one-question domain readings; they cannot show a difference of a few points.

## 10. Freezing, amending, and what the owner must decide

Freeze (after acceptance): `sha256sum review_data/ruler/SEALED_RUN_RULES_v1.md > review_data/ruler/sealed_run_rules_v1.freeze`, commit, and record the hash in `FOLLOW_UPS.md`. Amendments: appended below with a date and the reason, before the sealed questions are handed out, never after; an amendment after the hand-out is void.

**Decisions for the owner (defaults in brackets):**
1. Accept or change the floors and thresholds in sections 4 to 6 (all [Guessing]).
2. Side indexes in the sealed run? [yes]
3. Reference arm S? [yes]
4. Safety-net tail as an arm of the run? [yes; about 50 more passages]
5. Timing: after the register patch is applied and Mr. Advocate has reviewed the 16 older rulings, or sooner? [after, if it is a matter of weeks; the currency light is only meaningful with the register in a known state]
6. Answer the 2026-10-12 refresh reminder with "after the sealed run"? [yes]

## Amendments
(none)
