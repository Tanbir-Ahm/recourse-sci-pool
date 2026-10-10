# J and S's second-batch marks (pack v2, 38 chats), analysed 2026-10-10. AI marks only (ChatGPT and Gemini, run by J and S); no lawyer has checked any of it

Received: `Second_Batch_J_and_S_as_received.zip` (sha256 `2b5e86f4...fa06`), 38 files, all named as asked, none a prompt echo, none duplicated, every passage marked by both tools. 140 markdown backslashes were removed in 20 files by `normalise_replies.py` (marks and words untouched; originals in `replies_as_received/`). Ingest against the v2 extended pool: **364 of 364 passages in the pool now have at least one mark.** 15 of the 294 second-batch quotes (5%) are not word for word in the passage (first batch: about 5% for ChatGPT, 14% for Gemini). Scripts: `review_tools/score_rerank_arms.py`, `review_tools/score_challenger_arm.py` (rule written before the marks), `analyse_second_batch.py`, `analyse_second_batch_extra.py` (exploratory). Outputs: `ingest/`, `rerank_arms/`, `challenger/`, `analysis.json`, `extra_analysis.json`.

## 1. The pre-registered rule: PROCEED (for rerank-3-lite), with a flaw in my rule that matters

Passages entering the top 5 under rerank-3-lite (19) against those leaving (19), counts:

| Settlement | entering: Yes / useful / Misleading | leaving: Yes / useful / Misleading |
|---|---|---|
| ChatGPT alone | 8 / 17 / 2 | 5 / 14 / 4 |
| Gemini alone | 8 / 16 / 1 | 4 / 13 / 4 |
| both, ties to the lower mark | 8 / 15 / 2 | 3 / 13 / 4 |
| both, ties to the higher mark | 8 / 18 / 1 | 7 / 15 / 2 |

The rule (useful no more than one fewer, Misleading no more than one more, in both "both" settlements; every passage marked; no known-stale ruling enters) is met with room to spare. Stale check against the key's list: none enters (`../2026-10-10_reranker_test/results/stale_check.json`).

**The flaw (mine):** I did not foresee that the leaving passages were all marked in the first round and 14 of the 19 entering ones only in the second. The 76 repeated "anchor" passages show the second round is a little more generous on identical text (same mark 72%; second round higher on 12, lower on 9; mean +0.13 of a grade, ChatGPT +0.18, Gemini +0.08). Mean grade (Misleading 0, No 1, Partly 2, Yes 3), entering minus leaving: **+0.47 (ties lower), +0.26 (ties higher)**; bootstrap over questions [0.00, 0.86] and [-0.18, 0.67]. Taking the whole anchor shift off the 14 second-round passages leaves about +0.37 and +0.16, the same sign. The only like-for-like piece, the 5 entering passages marked in the first round: 2 Yes, 4 or 5 useful, 0 Misleading (too few to say more). **So: not worse, probably slightly better, not shown to be better.** The question-level comparison is weak because only 19 of 70 top-5 slots differ: per question (14 questions) rerank-3-lite minus today's: direct +1.4 to +7.1 points, useful +2.9 to +4.3, Misleading -1.4 to -4.3, intervals mostly spanning zero (`challenger/challenger_scores.json`).

What changed, question by question (`analysis.json`, `B_every_passage`): better on R11 (Binda, Misleading in all four runs, replaced by Tofan Singh paragraphs, Partly in three of four runs), R14 (a paragraph of Raj Reddy Kallem, Yes by both, comes in; two weak ones leave, one Misleading in two of four runs and one mostly No), R17 (three Yes in, a mixed set out), R24 (Tarsem Lal para 8, Yes by both, for para 23/2, Partly), R22 (a Misleading death-sentence passage out); level on R04, R19, R26, R08; worse on R12 (one ChatGPT-Misleading in, a Partly out), R20 (Partly in, a Yes or Partly out), and R09 gets a new old-law passage in (Times Business Solution v. Databyte, para 3: Misleading by both tools, "states the earlier rule under Dashrath Rupsingh Rathod without the later statute") while another old-law one leaves. That one is **not on the key's stale list**: the list is a floor, not a clearance.

**Not marked, and it matters:** the key paragraphs of R20 (Pramod Suryabhan Pawar, the case the re-ranker test "rescued") are in no pool row, so no reviewer has judged them. Under rerank-3-lite they sit 8th (outside the top 5); under rerank-3 and rerank-2.5 2nd. R09 and R14 key paragraphs are also unmarked.

## 2. How much does the re-ranker matter? Now measured (19 questions, first and second batch together)

Version A (rerank-2 x weights) top 5 against the merged order before the re-ranker (N) top 5, four settlements:

| | A top 5: direct / useful / Misleading | N top 5 | A minus N: direct | useful | Misleading |
|---|---|---|---|---|---|
| ChatGPT | 45 / 84 / 11 % | 31 / 74 / 8 % | +14.7 [3.2, 26.3] | +10.5 [2.1, 20.0] | +2.1 [-5.3, 9.5] |
| Gemini | 39 / 76 / 11 | 27 / 62 / 5 | +11.6 [2.1, 22.1] | +13.7 [2.1, 24.2] | +5.3 [-2.1, 12.6] |
| both, lower | 33 / 75 / 13 | 24 / 60 / 8 | +8.4 [-3.2, 18.9] | +14.7 [2.1, 26.3] | +4.2 [-4.2, 12.6] |
| both, higher | 51 / 87 / 6 | 34 / 76 / 5 | +16.8 [8.4, 26.3] | +11.6 [3.2, 20.0] | +1.1 [-5.3, 7.4] |

Passages the re-ranker promotes (64): 27 to 44% direct, 73 to 86% useful, 8 to 14% Misleading; passages it pushes out (64): 14 to 19% direct, 52 to 69% useful, 5 to 8% Misleading. The earlier guess in `RERANKER_IMPORTANCE.md` (direct +6 to +14, useful +2 to +6) was too low on useful. **The re-ranker earns its place; its cost is a few more Misleading passages (old law is promoted along with the good).** It is worse than the merged order on 4 of 19 questions (R08, R09, R17, R20); R09 is the clearest (direct 0% against 60%, Misleading 60% against 20%).

## 3. The safety net and the places 6 to 10

Places 6 to 10 of version A: 12 to 22% direct, 65 to 79% useful, 5 to 14% Misleading (about half the top 5's direct rate). The 52 net passages: 18 to 20% direct, 56 to 71% useful, 2 to 3% Misleading; **9 of them were marked Yes by every run** (R09: 3, R17: 2, R04, R21, R24 and R28: 1 each). The three R09 ones scored 0.79 to 0.80 under rerank-2 (about 15th by score alone) and were pushed to 28th to 31st by the 0.75 weight on passages labelled statute text. So the net is cheap insurance with little harm and a small yield (about one direct answer in two questions); it does not fix R09.

## 4. The reviewers

Second batch, 147 passages each: ChatGPT Yes 34, Partly 74, No 26, Misleading 13; Gemini Yes 29, Partly 67, No 43, Misleading 8. Same mark on 75.5% (kappa 0.63; first batch order A 70.5%, 0.57); same useful-or-not on 84%; ChatGPT the more generous on 26 passages, Gemini on 10. Largest disagreement: R06 (ChatGPT 7 Partly, Gemini 8 No). Neither tool gave a single Yes to the new passages of R06, R15, R20 or R26.

What "Misleading" meant (reviewers' reasons, read by keyword, rough): first batch 70 marks (34 passages): old or replaced law 33, a party's argument taken for the court's holding 16, rejected or distinguished rule 8, other 13; second batch 21 marks (14 passages): old or replaced law 7, argument 2, rejected or distinguished 3, other 9. **About half of what the reviewers call Misleading is old or replaced law, which no re-ranker removes.**

## 5. Other re-rankers (partial: only passages that were marked)

Entering vs leaving, ties lower: rerank-3 (17 of 21 entering marked) Yes 9, useful 14, Misleading 3 against Yes 3, useful 13, Misleading 6; rerank-2.5 (17 of 21) Yes 8, useful 13, Misleading 3 against Yes 3, useful 15, Misleading 4; rerank-3-lite (19 of 19) Yes 8, useful 15, Misleading 2 against Yes 3, useful 13, Misleading 4. No sign that one of the three is worse than the others on the marks; 4 passages each for rerank-3 and rerank-2.5 are unmarked.

## 6. Limits

AI marks only; 19 passages a side; a cross-round comparison (section 1); the three newer models were chosen after seeing the named-case result (some selection); the AI reviewers and Voyage's models may share tastes; no lawyer; tuning half only; the keyword reading of the reasons is crude.

## 7. What follows

Nothing is switched. See `RESULTS_IN_PLAIN_TERMS.md` for the reading and the recommended next step (the sealed run with both re-rankers as arms, marked in one round).
