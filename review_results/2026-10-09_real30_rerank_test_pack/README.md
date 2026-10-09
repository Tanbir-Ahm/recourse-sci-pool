# The re-ranker test pack and the safety net (built 2026-10-09; PRIVATE; only `Second_Batch_Pack.zip` goes to J and S)

## 1. What was built

| File | What it is | Who sees it |
|---|---|---|
| `Second_Batch_Pack.zip` (and the same folder unzipped) | 19 prompt files `R01_TA.txt` ... `R29_TA.txt`, a README for J and S, `manifest.csv`, an empty `replies/` folder. **38 chats** (19 files x ChatGPT and Gemini), 143 passages, 4 to 10 per file | J and S |
| `pool_with_rerank_arms.json` | The tuning pool plus the new rows and two new arms (it names which search found what) | private |
| `build_info.json` | counts, the zip's sha256 (`5fccb603...`), per-question numbers | private |
| `safety_net_reach.py`, `safety_net_reach.json` | which named cases the safety net brings up (section 4) | private |

The zip's own README never says what the pack is for; the folder is called `Second_Batch_Pack`; the prompts say nothing about the search, versions, arms, key or half (checked in the tests and again on the real files).

**What is in the 143 passages (the reviewers cannot tell):** 39 *core* (the merged top 5, i.e. the order the three searches give before the re-ranker, that no version ever showed to a reviewer), 66 *extra* (version A's places 6 to 10 that nobody has marked and that are not core, so that A's whole ten plus the safety net can be scored), 38 *anchors* (two passages per question from the first batch, chosen by a fixed hash and not by their marks, repeated under new numbers to measure whether the same tool marks the same text differently in a second batch). New numbers continue after the first batch's (the top-up rule), in a fixed shuffle. Reply names: `R01_TA_ChatGPT.txt`, `R01_TA_Gemini.txt`.

## 2. What the marks will tell us (`review_tools/score_rerank_arms.py`)

1. **Does the re-ranker help?** A's top 5 against N's top 5 (the search without the re-ranker) on all 19 questions, under four settlements (ChatGPT alone, Gemini alone, both with ties to the lower mark, both with ties to the higher), with a bootstrap interval over questions. Also kept / promoted / demoted passages one by one.
2. **Is the safety net worth showing?** The net M as a set, against A's places 6 to 10, and A's ten plus M.
3. **Is the second batch marked differently?** The anchors: same text, same tool, first batch against second.

Rehearsed end to end on the real extended pool with *synthetic* second-batch replies (to test the plumbing only; the numbers meant nothing and were not kept): 0 passages of any list left unmarked, 143 passages read per tool, the only warnings were the 54 first-batch quote warnings already known. When the replies are back: `normalise_replies.py` on the second batch (add `--drop` only for a file that is the prompt or a duplicate), copy them next to the 50 normalised first-batch replies, then
`python review_tools/score_rerank_arms.py --pool review_results/2026-10-09_real30_rerank_test_pack/pool_with_rerank_arms.json --replies DIR --out DIR2`.

## 3. The safety net (what "make sure those cases come up" became)

**Rule** (`pool_runner.safety_net`, behind `--safety-net`; tests in `test_pool_runner.py`): the list to show is *A's ten, then whatever of the merged top 5 (the cases the three searches agreed on before the re-ranker) A's ten do not show*, in merged order, a copy of the same text counting as shown. At most 15 passages; **every passage of the merged top 5 is in the list, whatever the re-ranker thinks of it and whatever the question**. It costs no extra call (the merged order is what the re-ranker was given) and changes nothing when the flag is off. On the 19 tuning questions the net holds 52 passages (1 to 4 per question) in addition to A's ten.

**Why a net and not a different order:** the evidence says the re-ranker's picks are on balance better (RERANKER_IMPORTANCE.md), but it made the named case's position worse on 4 of the 14 questions, and what the three searches agreed on is stronger than what it digs up from far down (45% against 27% direct answers). A net keeps its picks first and loses nothing the first stage agreed on.

**What it is not:** a quality claim. The 18 net passages the reviewers happened to see rated 22% direct and 67 to 83% useful (cautious and generous settlements); the pack tells us how the other 34 rate, and how A's places 6 to 10 rate beside them. If the net is mostly "background", show it under "also found", not to the answer-writing step.

## 4. Which *named* cases come up (the tuning half; from `safety_net_reach.json`)

The safety net adds **none** of the named cases that A's ten lacked, because they were not in the merged top 5 either. State of the 14 answerable questions: **10 are in A's top 5 already; 4 are not shown by A's ten plus the net**:

| Q | Where the named case is | What would bring it up | Cost / caution |
|---|---|---|---|
| R09 | merged order 14th, A 36th (the re-ranker prefers the older rulings the 2015 Act replaced) | a net of 14 or more, **or** a currency layer that demotes superseded rulings and brings their replacement | a deeper net adds noise; the currency layer needs Mr. Advocate's lists |
| R20 | merged order 15th, A 11th | show A's list to 11 places, or a net of 15 | longer list |
| R22 | not among the 60 candidates (best meaning rank 58); if added, 10th of 68; the rewrite (C) puts it 5th | a candidate pool of 100 instead of 60, or the rewrite arm | about 1.7 times the re-ranking; the rewrite needs a language-model call and 3 times the re-ranking |
| R14 | not among the 60 (best meaning rank 2241); if added, the re-ranker would put it 1st | **nothing generic reaches it** | only a curated link or a better rewrite |
| R15 | Shivangi Bansal (2025) is in the library (side index) but its best meaning rank is 172; if added to the 60 it would be 11th of 68; Rajesh Sharma and Social Action Forum do come up (A ranks 1, 2 and 4) | only a curated link from the cases that do come up | a pin or a lawyer's authority list |
| R06 | the 23 Aug 2024 order is not in the main index; **with the side index it is first or second in every version** | already done (the side index) | whether the final system includes the side indexes is your decision |
| R21 | Arjun Panditrao was filtered out of the main index; **with the side index it is 2nd (A, B, S) or 3rd (E)** | already done (the side index) | the old ruling (Shafhi Mohammad) still ranks first: that is the register's job |

With a net of 15 (and A's ten) the named case would be in the list for 12 of the 14 (R09, R20 join); R22 needs the wider pool or the rewrite; R14 stays out. **Do not read those depths as a finding:** they were found by looking at which cases were missed, so they prove nothing about new questions; the sealed half is the test.

## 5. What I did not do, and why

**I did not pin the named cases of your 30 questions into the search.** Your rule keeps the key out of every search and pack, and a pin built from the key would make the tuning half measure the pin instead of the search and would put the sealed half's answers into the system before the run. If you want named leading cases to come up for a scenario (a good product feature: "leading cases on this issue"), the safe way is a list written by a lawyer from outside the exam (Mr. Advocate's sheet, or Recourse's own doctrine maps), tested on questions that were not used to write it, and added after the sealed run. The mechanism (a data file of scenario to authorities, matched by meaning and section, injected after the re-ranked results) is straightforward to build once you say which source it should come from.

## 6. Decisions for the owner

1. Send `Second_Batch_Pack.zip` (and only that) to J and S.
2. Whether the sealed run carries `--safety-net` (no extra call; about 50 more passages to mark in the sealed half), and whether the product's list is "A's ten plus the net".
3. Whether to widen the net or the pool for the cases in section 4, knowing it cannot be validated on the tuning half.
4. Whether a lawyer-curated "leading cases per scenario" layer is wanted, and from which source.
