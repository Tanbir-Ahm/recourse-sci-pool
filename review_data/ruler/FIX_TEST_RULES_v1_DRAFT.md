# Fix-test rules, version 1: DRAFT of 2026-10-10 (PRIVATE; not frozen until the owner accepts it)

**Status.** Written at the owner's request ("draft the pre-registered test") after the sealed run missed two floors and the diagnosis (`review_results/2026-10-10_wrong_regime_diagnosis/`) found different causes in different questions. **No fix has been coded, no variant has been run, no new question exists.** Every threshold is a **[Guessing]** and may be changed only by a dated amendment at the end of this file **before** the dev run (section 3). Once the owner accepts, the file is frozen by recording its SHA-256 in `FOLLOW_UPS.md` and `fix_test_rules_v1.freeze` (command in section 9). All results are LLM-judged (ChatGPT and Gemini, run by J and S) unless a lawyer's sheet is added; nothing is lawyer-validated.

## In one page
1. **What it decides:** whether any of three small changes (C, N1, N2; the wider pool W was dropped before the freeze, see the disclosure at the end) to the search recipe, alone, is better than today's recipe (rerank-3-lite, 60 candidates), and, in the same run, whether the chosen recipe meets the connection floors F1 to F4 of `SEALED_RUN_RULES_v1.md` on questions nobody has tuned on. It decides nothing about the layperson mode, answer writing, or the verified answer path.
2. **Why new questions:** the sealed 11 and the tuning 19 have been looked at; R16, R23 and R03 are the reason the changes exist. They may be used to check that a change does what it was built for (section 3), never as evidence that it works.
3. **Two stages.** Stage D (development, free of marks): a mechanical gate on the 19 tuning questions plus the three known failures. Stage F (final): one run, one marking round, on at least 24 NEW questions, all arms in one shuffled list, once.
4. **Status quo wins ties.** A change is adopted only if it passes rules 1 to 6 of section 5. Otherwise the recipe stays as it is.
5. **A pass is not "X% accurate"** and is not a lawyer's clearance. Mr. Advocate reads every passage anyone marked Misleading plus a random 20 before anything leaves the project.

## 1. What is tested (exact definitions; coded and unit-tested before any paid call)
| Arm | Change from the baseline B (rerank-3-lite on 60 candidates, weights and 1.10 section boost as now) |
|---|---|
| **B** | nothing (today's final recipe) |
| **C** | **cap of 2 per judgment in the top 5**: fill places 1 to 5 in score order, skipping a passage when two passages of its judgment already hold places; skipped passages follow in score order from place 6; places 6 to 10 otherwise unchanged |
| **N1** | **named-Act boost, factor 1.10, judgment-level label**: if the question fires an Act of the Machine Spec (workbook sheet 'Machine Spec (draft)', 13 Acts, literal anchors), every passage of every judgment that carries that Act's strong marker in **3 or more** passages has its final score multiplied by 1.10 (once per passage; the section boost is unchanged). General codes (BNS/IPC, BNSS/CrPC, BSA/IEA) never boost |
| **N2** | the same with factor **1.25** |

The Machine Spec is fixed before any final question is searched and cannot be extended afterwards. It was written from the owner's trigger workbook (`review_data/ruler/inputs/2026-10-11_trigger_workbook_with_claude_appends.xlsx`: five original sheets untouched, three appended: 'Claude Review', 'Index Reality Check', 'Machine Spec (draft)'), not from any result of this test. Mr. Advocate reviews it before the freeze. A change that fails stage D is dropped, not retuned; a new magnitude needs an amendment before stage D starts.

## 2. Data
- **Stage D:** the 19 tuning questions (R01, R02, R04, R06, R08, R09, R11, R12, R14, R15, R17, R19 to R22, R24, R26, R28, R29; the sealed 11 are not among them) and, labelled "known failures, a check not a test", R16, R23, R03.
- **Stage F:** **at least 24 new questions** (30 preferred), same workbook format as the owner's 30, written **by someone who has not seen the sealed or tuning questions** (Mr. Advocate preferred; not Claude), with the key (expected answer, key authorities, older rulings) written and sealed with a freeze hash **before any search**, the same way `real30_v1.json` was. Required mix: the domains A to K spread as before; **at least 8 look-alike questions** (a question whose obvious neighbour is a different Act or section: for example a question under one special Act whose wording also fits ordinary criminal procedure), of which at least 3 do **not** name the Act in the question's own words; at least 2 index-gap or control questions, reported apart.

## 3. Stage D: the mechanical gate (no marks; cost under about $1)
Each of C, N1, N2 is run on the stage D questions. It goes to stage F only if **all** hold, against B on the same questions:
1. the named authority in the top 10 on the answerable tuning questions is **at least B's count**;
2. known-stale passages in the top 5, summed, **at most B's**;
3. on the three known failures it does what it was built for: **each of C, N1 and N2** must bring a passage of the key judgment of R16 into the top 5 (R23 is not a target of any arm: see the disclosure);
4. re-rank tokens per question **at most 1.8 times** B's.
The result table is committed before stage F questions are searched. A change that passes stage D has shown only that it does not obviously break the old questions.

## 4. Stage F: the run
One pool per question: the union of the top 10 of B and the top 5 of each arm that passed stage D, shuffled with a fixed seed; the prompt says nothing about arms; both tools on every file, order A; coverage must be 100% before any score is read; replies kept as received, cleaned by `normalise_replies.py` only; reliability flag as in the sealed rules (agreement under 60% = weak). The key is opened only after the marks are scored, once.

## 5. Choosing a change (the status quo wins ties)
An arm V replaces B only if all of the following hold, on the Stage F questions with marks (rules 1 to 5 are rules 1 to 5 of the sealed rules, V in place of R and B in place of A):
1. In all four settlements V's mean top-5 grade is at least B's.
2. In both "both" settlements V's Misleading share is at most B's + 2 points and V's useful share at least B's - 2 points.
3. In both "both" settlements V is better on at least two more questions than it is worse (a question differs when the mean grade of the top 5 differs by 0.4 or more).
4. Automatic: named authority in the top 5 at least B's count; known-stale passages in the top 5 at most B's.
5. The reliability note is not "weak".
6. **It helps what it was built for:** on the look-alike questions, V's Misleading share (both, ties to the lower mark) is at least 5 points lower than B's, **or** V has the key authority in the top 5 on more look-alike questions than B.
If more than one arm passes, the one with the highest mean grade (both, ties to the lower mark) is adopted; on a tie, the cheaper in re-rank tokens. **Combinations are not tested in this run**; a combination needs its own run on new questions. If none passes, B stays.

## 6. Floors and outcomes
The chosen recipe (V or B) is held to the **unchanged floors** F1 to F4 of `SEALED_RUN_RULES_v1.md` section 4 (useful at least 70% with ties to the lower mark; Misleading at most 15% and at most 10% with ties to the higher mark; named authority in the top 10 for at least 60% of the answerable questions; direct answers at least 25%), clear or weak pass as there, and to the outcome table of section 7 of those rules. Meeting the floors still leads only to shadow mode in the eligible domains and never to the verified answer path. I expect, at 24 questions and with the two judges agreeing on about 64%, that a recipe as good as the tuning half would still miss at least one floor in roughly **30 to 40%** of runs [Guessing]; a miss would again mean new questions.

## 7. What the test cannot show
Whether a change helps questions unlike the new ones; whether two changes together help; anything a lawyer would grade; answer writing; real users. Twenty-four questions cannot show a difference smaller than about 8 to 10 points; the rules ask for **no loss** plus a gain on the look-alikes, not for a large gain.

## 8. Order of events and hygiene
1. Owner accepts or amends; Mr. Advocate reviews the Machine Spec and the 'Claude Review' sheet of the workbook; the file is frozen and hashed.
2. Code the three arms in `pool_runner.py` (a `--variant` option, off by default, output unchanged without it), with tests; commit; record the commit in every run label.
3. Stage D; commit its table. Arms that fail are dropped.
4. In parallel, the question writer prepares the new questions; they are sealed with a freeze hash and a hand-out guard (the same machinery as the 30) **before** any search. The writer sees none of the results of stages D or F.
5. Preflight (rules hash, clean pushed checkout, index head, freeze hash, no hand-out logged, Voyage balance above the $5 reserve; cost about $0.30).
6. Stage F search once; pack built; J and S mark (about 50 chats for 24 questions); stage 1 on marks only; stage 2 opens the key once; report in plain words. Nothing is re-run and nothing is changed after a mark exists; a technical failure before any mark may be repeated and logged.
7. The index stays frozen at `3c80a26` until the run is over.

## 9. Freezing, amending, and what the owner must decide
Freeze: `sha256sum review_data/ruler/FIX_TEST_RULES_v1_DRAFT.md > review_data/ruler/fix_test_rules_v1.freeze` (renamed to `FIX_TEST_RULES_v1.md` at the same time), commit, record the hash in `FOLLOW_UPS.md`. Amendments are appended below with a date and reason, before stage D; never after stage F's questions are searched.

**Decisions for the owner (defaults in brackets):**
1. The arms: C, N1, N2 (W dropped on the evidence in the disclosure). [accepted by the owner on 2026-10-10 for C, N1, N2; W's removal awaits the owner's confirmation]
2. Who writes the new questions, and by when? [owner: "brand new questions would be provided"; at least 24, in the columns of the owner's 30-question workbook]
3. Is another marking round of about 50 chats acceptable to J and S? [yes, confirmed 2026-10-10]
4. Stage D spend under about $1? [yes, approved 2026-10-10]
5. Mr. Advocate reviews the Machine Spec (workbook, 13 Acts) before the freeze? [yes, confirmed 2026-10-10; the freeze waits for his review; the first 9-row Appendix A is withdrawn]

## Appendix A: withdrawn
The first draft table (9 Acts, with markers such as 'cheque', 'prevention of money', 'contraband', 'protection of women') is withdrawn: the owner's trigger workbook shows those markers misfire, and the index check confirms the general-code families cannot discriminate. The Machine Spec in the workbook replaces it. For stage F the new-question workbook gets one more column, 'Act(s) the question concerns (if any)', so trigger precision and recall can be measured before any search.

## Disclosure: a look at the data before the freeze (2026-10-10), and why W is gone
Before this file was frozen the owner asked whether the wider pool W was wise. A descriptive look (`review_results/2026-10-10_wide_pool_look/`, `wide_pool_look.py`, about $0.05, the 19 tuning and 11 sealed questions, all already used) ran W and three alternatives (Wd: pool of 100 with places 61 to 100 discounted by 0.90; L: 60 plus 15 best-by-meaning; J: "case first", 60 plus the 3 best passages of each of the 10 judgments with the highest summed meaning-list score over the top 300). Checks: the re-ranker's scores did not depend on the size of the call (difference 0.0000), the baseline B reproduced the sealed run's saved top 5 on 11 of 11 questions. Findings, which are the only use made of the look:
- **No arm raised the named authority** on the 24 answerable questions (top 5: 15 for B and for every arm; top 10: B 17, W 16, Wd 17, L 17, J 17) and none rescued R23 or R16.
- W changed the top 5 on 13 of 30 questions (18 passages, all from fused places 61 to 100, none of them marked); L 10, J 11, Wd 3.
- **R23 is not a pool-size problem:** the key judgment's passage at meaning rank 46 (fused place 88, inside a pool of 100) ends 24th; the passage that the re-ranker likes (3rd) is at meaning rank 248, outside every list. An earlier statement that a pool of 100 would put it 2nd or 3rd was wrong.
- The earlier remark that deeper lists "add noise" came from the safety-net depth in the re-ranker test pack, not from the candidate pool; for the pool the look shows churn without a gain, not harm.
Decision (proposed to the owner): drop W; do not add Wd, L or J. R23's kind of miss (the right passage deep in the meaning list) is left as a known limitation. These were chosen after a look at dev data, so they are tested only on the new questions.

### Second look, 2026-10-11 (the owner's trigger workbook)
`review_results/2026-10-11_trigger_sheet_review/`. Findings used: the workbook's separation of question triggers from passage markers is adopted; its false-positive audit is right about the first draft table; the three general codes mark 12 to 14% (BNS/IPC, BNSS/CrPC) and 2.7% (BSA) of all passages and are excluded from boosting; six families have under 100 marked passages in this index and are parked; a passage-level marker marks only 19 to 40% of an on-topic judgment's passages (operative paragraphs say 'the Act'), so the label is placed at the judgment level (3 or more marked passages), a design choice made from this audit and not tested on results; the workbook's long phrases do not match real questions, so literal anchors are used (they fire on 11 of the 30 used questions, none looked wrong), and semantic routing was tried and rejected (nearest-Act cosines 0.2 to 0.5 for every question). These were looked at on already-used questions.

## Amendments
(none)
