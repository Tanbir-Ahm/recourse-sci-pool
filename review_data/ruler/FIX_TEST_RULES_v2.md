# Fix-test rules, version 2 (written and frozen 2026-10-12, BEFORE any code for it and BEFORE the new question file was read; PRIVATE until the run is over)

**Status.** v1 (`FIX_TEST_RULES_v1.md`, frozen, hash in `fix_test_rules_v1.freeze`) stays in force **except where this file says otherwise**; v1 itself is not edited. Written at the owner's decision "B" of 2026-10-12, after Stage D of v1 failed all three arms (`review_results/2026-10-12_fix_test_stage_d/STAGE_D_GATE.md`). All results are LLM-judged (ChatGPT and Gemini, run by J and S) unless a lawyer's sheet is added; nothing is lawyer-validated. Every number below marked [Guessing] is a judgment, not a measured value.

## 1. What changes from v1
1. **Arm C is dropped.** It changed the top 5 on 5 of 22 questions and raised nothing (v1 Stage D).
2. **The 1.10 boost sizes of N1 and N2 are dropped as arms.** On R16 they lifted Kamatchi (the key judgment) from outside the top 10 to place 7, not into the top 5; they changed nothing else that was measured. Their v1 results stay on record.
3. **New candidate arms: the same named-Act boost (Machine Spec v2, judgment-level labels, 3 or more distinct marked passages, exactly as v1 section 1) at two larger sizes:**

| Candidate | Trigger | Boost |
|---|---|---|
| N1-125 | N1 (precise anchors) | x1.25 |
| N1-150 | N1 | x1.50 |
| N2-125 | N2 (precise or plain-language anchors, with the exclusion guards) | x1.25 |
| N2-150 | N2 | x1.50 |

   The boost multiplies the final score (re-ranker x passage-type weight x section boost) once per passage, as in v1. Nothing else changes: same 60 candidates, same rerank-3-lite, same weights, same Machine Spec v2 (pinned by hash in `fix_test_rules_v2.freeze`). No size above 1.50 is tried: above it a boost starts to outweigh the re-ranker's own judgment for any passage of a labelled judgment [Guessing]. No size between 1.10 and 1.25 is tried.
4. **Selection of the size, per trigger (pre-registered, mechanical):** for N1 and for N2 separately, the **smaller** of the two sizes that passes all five conditions of section 2 is that trigger's finalist (N1* and N2*). If neither size passes, that trigger is dropped. So at most **two** arms (N1*, N2*) can go to Stage F; this is deliberate (few arms, less chance of picking a winner by luck).

## 2. Stage D (v2): the gate
Same 22 questions as v1 Stage D (the 19 tuning questions and R16, R23, R03 as a check, not a test); one retrieval and one re-rank call per question; B and the four candidates are built from the same scores in the same run (B is recomputed in this run, not taken from the v1 run). A candidate passes only if **all five** hold against B on the same questions:
1. Named authority in the top 10 on the answerable tuning questions at least B's count.
2. Known-stale passages in the top 5, summed, at most B's.
3. R16: a passage of the key judgment (Kamatchi) in the top 5. **Disclosure:** the sizes above were chosen after seeing that 1.10 brings Kamatchi to place 7, so passing this condition is **not independent evidence** that the boost works; it only shows the boost is large enough to do the one thing it was built for. The evidence is the marked Stage F.
4. Re-rank tokens per question at most 1.8 x B's (the arms share one call, so this holds by construction).
5. **New: collateral change.** The top 5 differs from B's on at most **8 of the 22** questions [Guessing: v1 N2 at 1.10 changed 5]. A boost that rewrites more than a third of the old top 5s is not a small fix.
The result table is committed before any new question is searched. A candidate that fails is dropped, not retuned.

## 3. If neither trigger has a finalist
B stays. **No marking round is run for arms.** Whether to spend a marking round on a floors-only test of B alone on the new questions is a separate decision for the owner (recommended against in the 2026-10-12 discussion: it measures the same recipe a second time).

## 4. Stage F (v2) when there is at least one finalist
As v1 section 4, with the arms B and the finalists only (one or two). v1 section 5 (choice rules 1 to 6, status quo wins ties, combinations not tested) and section 6 (floors F1 to F4 unchanged) apply unchanged to each finalist in place of V. If both finalists pass, the one with the higher mean grade (both judges, ties to the lower mark) is adopted; on a tie the cheaper. The new question set, its rules (`question_rules/New_Test_Questions_Rules_and_Guidelines.docx`), key sealing, hand-out guard, single search, one marking round (about 60 chats; fewer chats if only one finalist), two-stage scoring and Mr. Advocate's reading of every Misleading passage plus a random 20 are as in v1 sections 2 and 8.

## 5. Order of events and hygiene (v2)
1. Freeze this file (hash in `fix_test_rules_v2.freeze`, together with v1's and the Machine Spec's hashes). **The new question file has not been read by Claude at the time of this freeze.** It is read only after this freeze and only for the format, count, duplicate, index-coverage and trigger-versus-tag checks of the question rules; **nothing in the arms, sizes or conditions above may change after the file is read.**
2. Code the sizes behind an off-by-default option (`--fix-test D2`), with tests; commit; the run records the commit.
3. Run Stage D (v2) once; commit the table.
4. Only then: question checks, Mr. Advocate's key review, sealing, preflight, Stage F search (once).
5. The writer of the new questions has seen no earlier results or keys (the owner is asked to confirm).

## 6. What this does not show
Same limits as v1 section 7. In addition: a larger boost may help the look-alike questions and hurt the others, or the reverse; with about 27 scored questions only a difference of roughly 8 to 10 points can be seen; the choice of 1.25 and 1.50 is a judgment [Guessing], and the other sizes between and beyond are untested.

## Amendments
(none)
