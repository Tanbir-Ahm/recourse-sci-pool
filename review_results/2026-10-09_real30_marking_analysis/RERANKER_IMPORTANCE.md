# How important is the re-ranker? (2026-10-09; PRIVATE; every mark is an AI mark, no lawyer; the 19 tuning questions)

> **Update 2026-10-10:** the pack this note asked for was marked (J and S, 38 chats). Measured: the re-ranker adds 8 to 17 points of direct answers and 10 to 15 points of useful passages to the top 5, with a few more Misleading ones; see `../2026-10-10_second_batch_marking/README.md`. The guess below is superseded.


Tags: [Certain] = counted from the saved runs and marks, [Likely] = strong inference, [Guessing] = filling a gap. Numbers come from `rerank_vs_marks.json` (`python rerank_vs_marks.py`, no network, no spend), `../2026-10-09_real30_pool_dev/rerank_effect/` and `analysis.json`.

## Verdict

**Important as a sorter, not decisive for accuracy.** The re-ranker decides most of what the user sees and, on the evidence we have, it makes the list somewhat better, probably by roughly 6 to 14 points of direct answers and 2 to 6 points of useful passages [Guessing, see section 3]. It cannot add a passage the three searches did not find, it knows nothing about whether a ruling is still good law, and the biggest weaknesses of the search (old law, library gaps, wording that does not match) are untouched by it. It costs about a tenth of a cent per question. **Keep it; do not expect it to fix the problems that matter most.**

## 1. What it is

Three searches (by meaning, by keywords, by section number) each bring back passages; they are merged into **60 candidates**. The re-ranker (Voyage `rerank-2`) then reads the question together with each of the 60 and re-orders them; a few weights are applied (court's reasoning 1.0, argument 0.85, ... header 0.3; +10% if the passage names the section asked about); the top 10 are kept. Versions A, B, E, C, F use it; the live site's own search (S) does not. See `../2026-10-09_real30_pool_dev/HOW_THE_SEARCH_WORKS_STEP_BY_STEP.md`.

## 2. It decides most of what the user sees [Certain]

- Of the 95 passages in version A's top 5 (19 questions), **64 (67%) were not in the top 5 of the merged list**, **52 (55%) were not even in its top 10**, and one came from position 58 of 60. Median merged position of an A top-5 passage: 13. (The earlier count in the step-by-step note, 60 of 90, left out R15, whose rerun did not reproduce that day; it reproduces now.)
- A's **first result** was also first before the re-ranker in only **3 of 19** questions; in 9 (those 3 included) it was in the merged top 5; in **10 of 19 it came from beyond it**.
- Version E (re-ranker alone, no weights) reshuffles just as much (63 of 95 outside the merged top 5), so the reshuffling is the re-ranker's doing, not the weights'.
- 17 of the 31 passages that the reviewers rated "directly answers" (cautious setting) in A's top 5 had come from beyond the merged top 5: **more than half of A's direct answers reach the screen through the re-ranker**.

## 3. Does what it picks work better? Mixed evidence, leaning positive

**(a) Finding the named case (the one test that needs no marks).** On the 14 answerable questions the named key authority is in the top 5 for **8 of 14 before the re-ranker, 9 with the re-ranker alone (E), 10 with the weights as well (A)**; in first place 3, 4, 5. By question, A against the merged order: **better on 6** (R04, R08, R17, R19, R24, R26; R08 went from 10th to 2nd), **worse on 4** (R09 from 14th to out of the top 10, R11 1st to 3rd, R12 3rd to 5th, R20 15th to out), same on 2 (R01, R02); not found by either on 2 (R14, R22). [Certain] A modest net gain, and the four losses are real.

**(b) The first result.** The 10 first results that came from beyond the merged top 5 were rated useful **9 of 10** times and direct 5 of 10 (generous setting: useful 10 of 10, direct 7 of 10); the 9 that were already in the merged top 5 were useful 6 of 9 and direct 5 of 9 (generous: useful 7 of 9, direct 6 of 9). Small numbers, but the re-ranker's own picks for first place were not worse. [Certain as counts; Likely as a reading]

**(c) Passages it pulled in against passages it pushed out.** Of the 95 passages in the merged top 5, 31 stayed in A's top 5, 12 fell to places 6 to 10 and 52 fell out of A's top 10. Of the 64 it pulled in: **27% rated direct, 73% useful, 14% misleading** (cautious setting; generous 44/86/8). Of the 25 it pushed out **that the reviewers did see**: **16% direct, 64% useful, 12% misleading** (generous 24/80/8). So what it pulled in was better than what it pushed out. [Certain as counts] **Caveat:** 39 of the 95 merged-top-5 passages were never shown to the reviewers by any version, so they have no mark; the 25 marked ones are the pushed-out passages that some version still liked enough to show, which probably flatters the pushed-out group. If anything this favours the re-ranker.

**(d) A warning.** The 31 passages that were in the merged top 5 and stayed there rate **45% direct, 77% useful, 10% misleading**; the 64 that were pulled in from further down rate **27%, 73%, 14%**. By how far down they came from (cautious): from merged places 6 to 10, 17% direct but 83% useful and none misleading (12 passages); from 11 to 20, 27% direct, 53% useful, 20% misleading (15); from 21 to 60, 30%, 78%, 16% (37). **What the three searches agreed on is stronger than what the re-ranker digs up from far down**; the re-ranker is not infallible, and its far reaches are noisier. The same pattern holds for each tool alone (ChatGPT 58% direct kept against 39% promoted; Gemini 48% against 34%). [Certain as counts]

**(e) Net effect on the marks: not proven, bounded, and my best guess.** Because 39 passages have no mark, the "search without the re-ranker" cannot be scored exactly (not one question has a fully marked merged top 5). If the 39 were all No the merged top 5 would score 19% direct against A's 33% (cautious setting); if all Yes, 60%. **If the never-shown passages are no better than the shown-but-pushed-out ones** (an assumption, and probably cautious, because nobody liked them enough to show them), the search without the re-ranker would score **27% direct / 69% useful against A's 33% / 75%** (cautious), **37% / 84% against 51% / 87%** (generous); ChatGPT's marks 35% / 80% against 45% / 84%; Gemini's 30% / 74% against 39% / 76%. That is a gain of about **6 to 14 points of direct answers and 2 to 6 points of useful passages** [Guessing], inside the noise of a 19-question test (a gap under about 10 points should not be acted on) and near the size of the effect of the weights (section 5).

## 4. What it cannot do [Certain]

1. **It cannot add candidates.** It only re-orders the 60 the three searches found. In **2 of the 14** answerable questions (R14, R22) the named authority is not among the 60 at all, and in 3 questions (R06, R15, R21) it is not in the library. No re-ranker could rescue those five.
2. **It is not a currency check.** It reads relevance, not whether a ruling still stands. In R09 it moved the case that reflects the 2015 Act (Bridgestone) from 14th to 36th and preferred the older rulings that the Act replaced. In 4 of 19 questions A's top 5 holds replaced law (9 of 95 slots); the re-ranker neither causes nor cures that.
3. **It does not touch the causes of the six questions with no direct answer:** a missing document (R06), old law (R09, R11), wording that does not match the case (R14), new or unsettled law (R15, R20).

## 5. Next to the other parts of the recipe

- **The weights** (a few multipliers, free): the key authority in the top 5 goes 9 to 10 from E (re-ranker alone) to A, as it goes 8 to 9 from the merged order to E; on the marks E is worse than A in all 7 ways of counting, by about 6 points of direct answers and 5 more misleading passages (cautious setting). So **the weights matter about as much as the re-ranker** on the evidence we have. [Likely]
- **The site's own search (S, no re-ranker, no keyword or section search, no weights):** about 9 to 11 points fewer useful passages than A and a direct first result on 5 of 19 questions against 10. That supports the whole of A's pipeline, but S differs from A in several ways at once, so it cannot be put down to the re-ranker alone. [Likely]
- **The rewrite** helps one question (R14); the re-ranker helps or hurts many, by a little.
- **Where the biggest levers are:** old law (a currency layer) and library coverage. The re-ranker is second-tier. [Likely]

## 6. Cost [Certain]

74 calls, 1,812,788 tokens in the whole tuning run, about **$0.09**; one call per question for A of about 18,000 to 26,000 tokens, **about a tenth of a cent** (roughly $9 to $13 per 10,000 questions at the listed $0.05 per million tokens; the owner's dashboard balance of $9.54 matched my running estimate of all spend so far to within about two cents, which supports the listed price). It adds one outside call per question and one more thing that can fail or change price; neither has been measured.

## 7. What is unknown, and the test that settles it

- The re-ranker's effect on **usefulness** is not measured; only the named-authority test is clean. The decisive test is to have **the 39 never-shown merged-top-5 passages marked** (all 19 questions have some): 19 short prompts, in ChatGPT and Gemini, 38 chats, no money. **The pack is built** (`../2026-10-09_real30_rerank_test_pack/`, `Second_Batch_Pack.zip`; it also holds A's unmarked places 6 to 10 and two anchors per question) and the scorer is ready (`review_tools/score_rerank_arms.py`); it gives a real "without the re-ranker" top 5 to score against A, with the same two tools. A safety net (`--safety-net`) now keeps the merged top 5 in the list shown whatever the re-ranker thinks.
- Its effect on the **answers** (the answer-writing step) has not been measured at all.
- It is **not exactly repeatable**: re-running version A on the same 19 questions (2026-10-09, `rerank_effect/a_scores.json`) gave the same ten in the same order for 9, a neighbouring pair swapped in 10, and a different top-5 set in 4 (R04, R12, R15, R20: a 5th/6th swap; for R15 the retrieval itself changed). Places 5 and 6 are close to a coin toss for any pair of near-tied passages; this is service noise on top of the 19-question noise.
- Whether `rerank-2` is better than another re-ranker, or than a re-ranker run only on the top 20, has not been tried.

## 8. What I would do

1. **Keep it in the final system** (cheap, and it moves the named authority up on balance).
2. **Do not credit it with accuracy it cannot give:** fix old law with the register and the "relies on an overruled ruling" warning, and fix library gaps with the side indexes, before spending effort on re-ranker variants.
3. If the owner wants the question settled with marks, run the 38-chat test above before the sealed run, not after.

## Appendix: the named authority, before and after (14 answerable questions; position in the list, "-" = not in it)

| Q | merged order (no re-ranker) | re-ranker alone (E) | re-ranker + weights (A) | change |
|---|---|---|---|---|
| R01 | 1 | 1 | 1 | same |
| R02 | 1 | 1 | 1 | same |
| R04 | 3 | 3 | 2 | better |
| R08 | 10 | 5 | 2 | better |
| R09 | 14 | - | - | worse |
| R11 | 1 | 4 | 3 | worse |
| R12 | 3 | 10 | 5 | worse |
| R14 | - | - | - | not among the 60 candidates |
| R17 | 2 | 2 | 1 | better |
| R19 | 2 | 1 | 1 | better |
| R20 | 15 | - | - | worse |
| R22 | - | - | - | not among the 60 candidates |
| R24 | 2 | 1 | 1 | better |
| R26 | 6 | 3 | 4 | better |

Files: `rerank_vs_marks.py`, `rerank_vs_marks.json`; `../2026-10-09_real30_pool_dev/rerank_effect/save_fused_lists.py` and `fused_lists.json` (the 60 merged candidates per question, saved by re-running the search up to the re-ranker: no re-ranker call, 1,155 embedding tokens, about $0.0001).
