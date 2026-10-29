# Why the search missed a landmark judgment that is in the index, and the authority-aware ranking that is the general fix (2026-10-29)

Owner's request, 2026-10-29: the answer to "Can a person be convicted on circumstantial evidence alone? What must the prosecution prove?" left out *Sharad Birdhichand Sarda v. State of Maharashtra* although the index holds it. "Same issue may arise with another question where the response might end up missing another landmark case ... FIX this problem for good." Plain-terms version: `RESULTS_IN_PLAIN_TERMS.md`. Labels: [Certain] = measured or read in a file; [Likely] = inference; [Guessing] = judgment.

## 1. What happened, for that one question (newer index d8811a9: 420,893 passages, 19,255 judgments)
The staging answer was fed eight wider-search cases and not Sarda. Reproduced with the real service code and the real Voyage models, the same list as the owner's staging log came back (`trace_one_question.py`; the plain list is the "off" list below).

- **Sarda is in the index: 197 passages.** [Certain]
- **None of them reached the re-ranker.** The search first collects 60 candidate passages (the 100 closest in meaning, 50 by keywords and the "section N" matches, merged), then a re-ranking model orders only those 60. By meaning Sarda's best passages stand at places **488, 563, 1,436, 1,437 and 1,475** of 420,893; none is among the 100 taken, and no keyword or section hit picked one up. So the question was never one of ranking Sarda too low: it was **not a candidate**. [Certain]
- **Why Sarda's passages are not the closest in meaning.** The ten passages that did win are short plain restatements (median 788 characters; the median passage of the index is 1,384). A landmark's long passage mixes quotations, history and several points; a short later passage that restates the rule in one tidy sentence sits closer to a short question. There are hundreds of such restatements. [Certain for the lengths, Likely for the reason]
- **And ranking would not have saved it.** Among the 60 candidates the re-ranker's scores run from 0.922 (first) to 0.871 (10th) to 0.836 (30th): the first thirty places lie within 0.09 of each other, so small differences decide who is in the first ten. Earlier (the 104-question set below) 22 landmarks had been retrieved and then ranked out for exactly this reason. [Certain]
- **The one thing the search ignores: the court's own pointers.** 446 judgments of the collection refer to Sarda by name, and 22 of the 59 judgments that this very search retrieved for the question do. The search uses no such signal. [Certain]

## 2. How general (104 questions, written by Claude, not by a lawyer; committed before any search, `ef286cb`)
52 questions per half ("dev" for the design, "frozen" for one final run). Each has expected landmark judgments found by NAME in the names table before any search. Plain search (recipe B) on the newer index, run before any change: a landmark among the first 10 for **55 of 104**; **22 retrieved among the 60 and ranked out; 27 never among the 60** (`baseline_recipe_B_newer_index.json`). So the owner's case is the common case, not a rare one. [Certain, with the limit that the questions and the expected landmarks are Claude's]

## 3. The fix: authority-aware ranking (`SCI_AUTHORITY`, default off; service code `authority_search.py`, `sci_search_service.py`; offline table builder `authority_graph.py`)
1. **Offline: who names whom.** `authority_graph.py build` reads the text of every passage of an index and records, for each judgment, which other judgments it refers to by name ("X v. Y", year, and bare names under strict context rules; duplicate records of one case are clustered). Output: `authority_table/authority_<index commit>.json.gz` (146 KB; 5,827 judgments named, 10,514 that name others, on the newer index). The service refuses to start with the switch on if the table is missing or made for another index commit.
2. **Query time: take the court's own pointers.** From the 60 candidates, count which judgments the retrieved judgments name. A judgment named by at least 3 and at least 8 percent of the retrieved judgments (at most 10 such) is a pointer: its best 3 passages by meaning are added to the passages the re-ranker reads (one re-ranker call, as before).
3. **A small boost.** The re-ranker's score is multiplied by `1 + 0.1 x (how many judgments of the whole collection name it, log scale, 100 = full) + 0.6 x (the share of the retrieved judgments that name it, full at half)`. At most x1.7: a passage the re-ranker finds only half relevant (0.5) stays below one it finds a good fit (0.9). A judgment takes at most one place in the list returned (the website keeps one passage of each judgment, so more only crowded the others out).
4. **The facts travel with the result:** `authority: {named_by_collection, named_by_retrieved, retrieved, pointer, raw_score}`. Recourse's `authority_notes.py` turns them into a line for the answer model and one sentence for the page ("Named by other judgments: 22 of the 59 ..., about 446 in the whole collection (an automatic count of mentions of its name; a judgment can be named because it was followed, distinguished or criticised, so this does not say that the case is still good law)").
5. **With the switch off nothing changes**: same ranking, no extra field, same prompt block byte for byte (hashes in Recourse `test_authority_notes.py`).

The settings (prior 0.1, consensus 0.6, minimum share 8%, minimum 3, 10 pointers, 3 passages each, one place per judgment) were chosen on the dev half only and committed (`5299029`) before the frozen half was run. Nothing was changed after seeing the frozen results.

## 4. Results (hit = at least one expected landmark among the first 8 judgments; the website feeds the model at most 8; the same case held under two document numbers counts once)
Both columns come from the same run of the real service code (`evaluate.py`, files `evaluation_final_*.json`, with the sha256 of the code and data that ran).

| Index | Half | Plain search | With the step | Gained / lost |
|---|---|---|---|---|
| Newer (staging's, 19,255 judgments) | dev (52) | 29 (55.8%) | 45 (86.5%) | 16 / 0 |
| | **frozen (52), run once** | **23 (44.2%)** | **39 (75.0%), 95% interval 62 to 85** | **16 / 0** |
| | all (104) | 52 (50.0%) | 84 (80.8%) | |
| Production's pinned (10,522 judgments) | dev (52) | 35 (67.3%) | 46 (88.5%) | 11 / 0 |
| | **frozen (52), run once** | **27 (51.9%)** | **41 (78.8%), 95% interval 66 to 88** | **15 / 1** |
| | all (104) | 62 (59.6%) | 87 (83.7%) | |

- The honest figure is the frozen one: **about 75 to 79 percent against about 44 to 52 percent**, on questions Claude wrote (frozen newer index: sign test on 16 gained, 0 lost, p = 0.00003). The dev figure (86 to 89 percent) is higher because the settings were chosen on it.
- Lay questions (frozen, newer): 12 of 25 -> 17 of 25; lawyer questions: 11 of 27 -> 22 of 27. [Certain]
- Not every question has a landmark that the pool points to. See section 6.
- **The step's cost:** one embedding call and one re-ranker call per question, as before; the re-ranker reads about 13 to 18 more passages (on the owner's question 10,390 -> 12,312 tokens, +18%). [Certain] Search time was not measured.
- The first frozen run on the newer index stopped on a Voyage server error before any result existed; it was re-run unchanged with a retry wrapper in the test harness (the service is untouched; the production-index run used the harness before the wrapper was added, which is why the `evaluate.py` sha256 differs between the two result files). The same plain search run twice moved 7 of 104 questions' outcome (5 down, 2 up counting duplicate records): **differences of two or three questions are noise.**

### The owner's question, with the step on (staging index; `owner_q_*` runs)
| | Plain search (what the owner saw) | With the step |
|---|---|---|
| Judgments fed to the answer model | 8, none of them Sarda | 8: **Sarda (1984)** first, **Hanumant (1952)** second, *M. G. Agarwal* (1962) fourth; five of the previous eight stay, three (Herman Tirky, Hongro Ngotan, Majendran Langeswaran) go out |
| Sarda: named by | | 22 of the 59 retrieved judgments, 446 of the collection |

Through Recourse's real feed code the prompt block now holds Sarda's best passage (1,385 characters, the passage that discusses Horry's case and Hanumant's rule: "no person can be convicted on pure moral conviction"), Hanumant's passage, the line "Named by other judgments ... NOT a statement that the case is good law" under each and one instruction sentence. **The passage fed is the one the re-ranker scored best (0.80), not the passage that lists the five conditions;** the second-best Sarda passage begins the list "(1) the circumstances ... fully established" and is cut mid-way. (The two prompt blocks, plain and with the step, exactly as Recourse's `feed_block` builds them from the service's replies, are `owner_question_feed_block_off.txt` and `owner_question_feed_block_on.txt`; the raw replies are `owner_question_service_results.json`.) So this fix puts the landmark in front of the model; whether the model then gives the five conditions depends on the passage and on the model, and was not tried (no model key here). The verbatim five-conditions anchor (`LANDMARKS=on`, FOLLOW_UPS 2cq) stays the exact-words route for this one topic.

### An independent check (the six verified landmarks of `landmarks.json`, two questions each = 12; written for earlier work)
Landmark in the first 10 judgments: plain search **3 of 12**, with the step **7 of 12** (newer index). The five that stay out: Md. Ibrahim (2 questions; the table finds its name 0 times), Nanda Gopalan (2; 2 times), Noor Aga for the lay question (no retrieved judgment names it). Whether the project's own verified paragraph is the passage returned: 3 of the 7 yes, 4 no (the re-ranker chose another paragraph of the same judgment); giving the step 10 or 20 passages of the pointer to choose from instead of 3 did not improve that (it lost one of the three matches), so 3 stays. [Certain, 12 questions only]

### Do ordinary questions get worse? (control: 70 questions not written for this test; `control_unrelated.py`)
| | Newer index | Production's index |
|---|---|---|
| Mean re-ranker score of the first 8 judgments, plain / with the step | 0.697 / 0.675 | 0.686 / 0.657 |
| ... over the same number of judgments from each list | 0.697 / 0.687 | 0.686 / 0.677 |
| Judgments brought in: how many, their mean score | 148, 0.602 | 178, 0.592 |
| Judgments pushed out: how many, their mean score | 86, 0.657 | 89, 0.627 |
| Of the 8, how many the two lists share (mean); questions with the same 8 | 5.9; 7 of 70 | 5.5; 2 of 70 |
| Questions whose score fell by 0.05 or more / rose by 0.05 or more | 3 / 0 | 3 / 0 |
On ordinary questions the step changes about two or three of the eight judgments and the ones it brings in score a little lower with the re-ranker (about 0.05) than the ones they replace: it trades some closeness of wording for authority. Whether that is better for the reader was not measured and cannot be by a score. [Certain for the numbers, Guessing for what they mean]

## 5. A risk the step adds, measured: heavily named judgments include overruled ones
A judgment is named most when it is important, and also when a later judgment overrules it (the overruling judgment names it). Over the 104 questions the step brought **317 judgments** into some list that plain search did not have; **10 of them are on the Overruled Register** (Adri Dharan Das, Siddharam Mhetre, Salauddin Abdulsamad Shaikh, Nirmal Jeet Kaur, Raj Deo Sharma, Shafhi Mohammad, Tomaso Bruno, Arnit Das, Sowmithri Vishnu, Jayendra Saraswathi). **The number of questions whose first 8 judgments hold a register-listed judgment rose from 5 of 104 to 13 of 104** (appearances 5 -> 17). [Certain]
What stands in the way on the website: the register's existing machinery. A listed judgment keeps its REGISTER FACT line, goes last, and the judgment that corrected it is added; the new code never presents a register-listed or card-flagged judgment as "read this first" (a test). What stands in no one's way: **an overruled judgment that is not on the register**. The register lists 1,688 + 59 rows and cards cover part of the rest; the step cannot know the others. This is the main thing for a lawyer to look for in staging answers.

## 6. What the step does not do (the 13 questions still missed in the frozen half, newer index)
Looked at afterwards, for the limits, not for tuning:
- **7: the landmark is named by a few of the retrieved judgments but below the threshold** (for example Arnesh Kumar by 3 where 4 are needed; Bhajan Lal by 1 or 2 although 48 judgments of the collection name it).
- **6 involve a landmark whose name the table finds 0 times** (Md. Ibrahim, Surinder Kumar v. Union Territory, Chandigarh, Tuka Ram). A loose text search of the same index finds them named in real judgments: "Tukaram / Tuka Ram v. State of Maharashtra" in 13 judgments, "Md. / Mohd. Ibrahim v. State of Bihar" in 18, "Surinder Kumar v. Union Territory / U.T. ..." in 11 (`name_variants_check.py`; 418,286 passages read). The later judgments write the name differently ("Tukaram", "Mohd.", "U.T."), and the name matcher of `authority_graph.py` does not yet join those variants. [Certain for the counts]
- **1: the pointer was found but the landmark's passages were outranked** (Dalip Singh); **1: no retrieved judgment names the landmark** (Arjun Panditrao Khotkar).
These are a name-matching and threshold problem with known directions. Any change to them changes the table and must be measured on questions written after this run, not on the dev or frozen halves, which are now used. NOT done.

Other limits, said plainly:
1. **The questions and their expected landmarks are Claude's.** No lawyer has chosen them or read any result. A different author would pick different landmarks and different wording.
2. **Nothing was tried with the answer model** (no key here): whether the answer states the rule from the pointer passage and respects the line under it is for the owner's staging test (`DEPLOY_STAGING.md` Part 4ae).
3. **"Named by" is a count of mentions of a name in text**, approximate in both directions; it is not a count of approving citations and says nothing about whether the case is good law.
4. **The tables belong to one index.** When the index changes, rebuild the table (`python authority_graph.py build ...`) or the service will not start with the switch on. A judgment too new to be named by anyone (2026 judgments) gets no authority; they compete as before.
5. Hindi or mixed-language questions, other High Courts, and judgments whose text is mostly scanned pages were not tried.
6. No hallucination rate has been measured. Do not call the search or the answers accurate or safe.

## 7. Tests
Research: `test_authority_graph.py` 29 checks, `test_sci_search_service.py` 45 (including the step on a small invented index: the landmark that fits worse is fetched and ranks first, the facts, one embedding and one re-rank call, off = no extra field, the boost cap, one place per judgment). Recourse (branch, `56e0cf1`): `test_authority_notes.py` 45 checks; the free suite `run_tests.py` 118 run, 118 passed on the final run (a first full run had 117 of 118: `test_site_e2e.py`, an unsynchronised read of the Streamlit page, failed, and it failed the same way on the unmodified code while the machine was busy).

## 8. Files
Research (branch `claude/sharp-euler-unyfv0`): `authority_graph.py`, `authority_search.py`, `sci_search_service.py`, `authority_table/authority_d8811a9.json.gz` (newer index), `authority_table/authority_3c80a26.json.gz` (production's pinned index), `test_authority_graph.py`, `test_sci_search_service.py`; this folder: `build_question_set.py`, `landmark_questions_v1.json` (the 104 questions, committed first), `baseline_recipe_B_newer_index.json`, `evaluate.py`, `evaluation_dev_*.json` (design runs, counted by document number), `evaluation_final_newer_index.json`, `evaluation_final_old_index.json` (the numbers above), `control_unrelated.py` and its two result files, `trace_one_question.py`. Recourse (branch `register-hooks-and-overlay`): `authority_notes.py`, `sci_search_tier.py`, `test_authority_notes.py`.
Re-run: `python3 evaluate.py --index-dir <index> --names <names table> --table <authority table> [--side <dir> ...] --half all --out <file>` with `SCI_INDEX_COMMIT` set to the index's commit.
