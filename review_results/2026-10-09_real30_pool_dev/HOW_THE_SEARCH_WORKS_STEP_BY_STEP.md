# How the search finds passages, step by step, and where the re-ranker comes in (answered 2026-10-09; PRIVATE)

**One line:** three searches (by meaning, by keywords, by section number) each find candidates; the three lists are merged into 60 candidates; **a re-ranker then reads the question together with each of the 60 and re-orders them**; small weights are applied; the top 10 are kept. Yes: meaning + keyword + section + re-ranker. This is true of versions A, B, E, C and F. Version S (the live site's own search code) is different and has **no re-ranker**.

## 1. The steps, with the code that does each (`review_tools/pool_runner.py`, class `Engine`)

| Step | What it is, in plain words | Numbers | Where |
|---|---|---|---|
| 1. Meaning search | The question is turned into a "fingerprint of meaning" (voyage-law-2). Every one of the 236,155 passages has such a fingerprint. The 100 passages whose fingerprint is nearest are taken. Finds a passage that says the same thing in different words. | 100 | `retrieve`, lines 106 to 132 |
| 2. Keyword search | An ordinary word search (SQLite full-text, ranked by BM25) on the question's first 12 distinct words of 4 or more letters that are not common words. Finds a passage that uses the same words. | 50 | `retrieve` |
| 3. Section search | If the question contains a section number ("section 479", "498A"), search for the exact phrase "section 479". Does nothing when the question names no section. | up to 30 per number | `retrieve`, `si.section_numbers` |
| 4. Merge | Reciprocal rank fusion: a passage near the top of several lists scores most. The best 60 are the **candidates**. | 60 | `retrieve` |
| 5. **Re-ranker** | Voyage `rerank-2` reads the question and **each candidate together** and gives each a score. This is a different kind of reading from step 1: step 1 compares two separate fingerprints; the re-ranker reads the pair. The site's own code describes it as a cross-encoder "which reads the query and each document TOGETHER" (`semantic_retrieval.py`, `rerank`). It is paid for, per token read. | 60 passages (each cut at 3,500 characters) | `rerank`, line 134 |
| 6. Weights | The score is multiplied by a weight for the kind of passage: court's reasoning 1.0, argument 0.85, facts 0.8, statute text 0.75, order 0.6, header 0.3. Version A also multiplies by 1.10 if the passage names the section the question mentions. | | `weight`, line 142 |
| 7. Top results | The best 10 are kept; the top 5 of each version go to the reviewers (all of S's). | 10 / 5 | `lists_for`, line 149 |

## 2. Which version uses what

| Version | Meaning | Keyword | Section | Re-ranker | Weights | Note |
|---|---|---|---|---|---|---|
| A today | yes | yes | yes | **yes** | yes + section boost | the main recipe |
| B no repeats | yes | yes | yes | **yes** | yes + boost | skips passages whose text is identical to one already taken |
| E no multiplier | yes | yes | yes | **yes** | no | re-ranker alone, to see what the weights add |
| C rewrite | yes | yes | yes | **yes** | yes + boost | the same pipeline run on a blind rewording of the question (12 questions) |
| F merged | yes | yes | yes | **yes** | yes + boost | the candidates of A and C together, scored by the better of the two readings (12 questions) |
| S site shown | yes (top 50, cosine at least 0.40) | only as a backfill (at most 2) | its exact-section lookup is **off** | **no** | no | the Recourse site's own code, `semantic_retrieval.find_relevant_sections`; it does not call `rerank` (checked in the code: `rerank` is defined in the same file but called only from other parts of the site, such as the related-judgments lane in `related_judgments.py`) |

## 3. Evidence that the re-ranker was used

- **The bill.** `spend.json`: **74 re-rank calls, 1,812,788 re-rank tokens** (model `rerank-2`), 50 question embeddings (model `voyage-law-2`), about $0.09. The count follows from the design: 19 questions x 2 (A and E share one call, B has its own) plus 12 rewritten questions x 3 (one for C, two for F) = 74.
- **The record.** `pool.json`, `run.models`: `{"embed": "voyage-law-2", "rerank": "rerank-2"}`.
- **The code.** `lists_for` calls `self.rerank(...)` before anything is kept; the miss diagnosis (`miss_diagnosis/`) shows the re-ranker's own scores (for example Bridgestone, R09, rank 36 of 60).

## 4. What the re-ranker changes (measured, `rerank_effect/`, 18 of the 19 questions; the search was rerun up to the point just before the re-ranker, no re-ranker calls, $0.0001)

- **It decides most of what you see.** Of the 90 passages that ended in version A's top 5, **60 (two in three) were not in the top 5 of the merged list**, 50 were not even in its top 10, and one came from position 58 of 60. On average only 1.7 of the 5 are the same before and after.
- **It helps more often than it hurts, but it does hurt.** The named key authority is in the top 5 for **8 of 14** answerable questions before the re-ranker, **9** after the re-ranker alone (version E), **10** after the re-ranker and the weights (version A); first place: 3, 4, 5. In the top 10 it is 10 of 14 in all three, the same questions.
  - *Helped, R08 (everyday: "20% interim compensation on the very first date. Is that compulsory?"):* the named case (Rakesh Ranjan Shrivastava, 2024) was 10th in the merged list, 5th after the re-ranker, **2nd** with the weights.
  - *Hurt, R09 (legal: which court has jurisdiction when the payee presents the cheque in Delhi):* the named case (Bridgestone, 2015) was 14th in the merged list and **36th** after the re-ranker: it preferred the older rulings that the 2015 Act replaced.
  - Also worse: R11 (1st to 3rd in A, 4th in E), R12 (3rd to 5th in A, 10th in E).
- **What this does not show.** Whether the passages the re-ranker puts first *answer the question* is only known from the reviewers' marks, which are not in yet. "Named key authority in the top 5" is one test, and the key authority is one authority per question.
- (Re-run on 2026-10-09 for the marks analysis, with Q15 now reproducing: 64 of 95 outside the merged top 5, 52 of 95 outside its top 10, deepest position 58; see `review_results/2026-10-09_real30_marking_analysis/RERANKER_IMPORTANCE.md`.)
- Q15 was left out of these figures: its retrieval did not reproduce exactly on the rerun (6 of the recorded top-10 passages were not among the recomputed candidates; the question embedding and the keyword ranking can differ a little between calls). The other 18 reproduced exactly.

## 4b. The safety net (added 2026-10-09, opt-in with `--safety-net`; not used in the run above)

Because the re-ranker decides most of what is shown and made the named case's position worse on 4 of 14 questions, the recipe can also keep what the three searches agreed on: the list to show is **A's ten, untouched (so the top 5 always follows the rules already set), then whatever of the merged top 5 A's ten do not show**, placed after place ten and ranked by the same query-based score as A (a copy of the same text counts as shown), at most 15 passages. It costs no extra call. Without it, those passages are simply ranked by the question like every other candidate and land at a median place of 28 of 60. It brings up nothing that was not in the merged top 5 (so it does not rescue a case that is not among the 60 candidates). See `review_results/2026-10-09_real30_rerank_test_pack/README.md`.

## 5. What was NOT used

- **The Overruled Register** was not used in any search (see `HOW_IT_SEARCHED_AND_THE_REGISTER.md`).
- **No language model wrote any answer or chose any passage.** The only language-model text in the search is the blind rewording used by versions C and F, saved before the search. The reviewers' marks (ChatGPT, Gemini) come afterwards and judge, they do not search.

## 6. Finding documents to add to the library is a different job and used no re-ranker

When I looked for a judgment in the collection (sizing the gaps; checking whether Kartar Singh, Shivangi Bansal and the others are there) I used plain name and citation matching and a word search over the collection's text (SQLite), not the meaning search and not the re-ranker; Voyage was not called. When I fetched the two documents (Q6, Q15) I used the links directly: no search at all. Voyage was used only afterwards, to embed the new passages (a fraction of a cent) and then to search them like any other.
