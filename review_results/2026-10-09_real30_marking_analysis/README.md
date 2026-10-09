# J and S's marks on the tuning half of the 30 questions: analysis of 2026-10-09 (PRIVATE; every number is LLM-judged, nothing is lawyer-checked)

Marks of ChatGPT and Gemini (run by J and S; the file names do not say who ran which) on the 217 passages of the 19 tuning questions: `J_and_S_s_marks.zip` (sha256 `00d7d026d69c8fce22f6096eb9a2bda6f2c2cf95d43e887d692e80512b1878f0`), 50 files, all 50 of the manifest present. The sealed half is untouched. Everything below is reproducible from the files in this folder.

## 1. What was received, what was wrong with it, what was done

| Problem | Evidence | What I did |
|---|---|---|
| 23 of the 25 ChatGPT files are unreadable as received: the chat window's copy button put a backslash before every underscore and square bracket (`"question\_id"`, `\[`, `\]`; 167 escapes in all) | the first reading found "no valid JSON" in 23 files | `review_tools/normalise_replies.py` removes exactly those three escape sequences and nothing else (tests: every mark, number and quote survives; other backslashes are left alone). Originals kept in `replies_as_received/`; fingerprints in `replies_for_the_reader_NORMALISATION.json` |
| `R02_A_ChatGPT.txt` is **the prompt, not a reply** | it opens with "QUESTION ID: R02 (prompt version...)" and ends with the prompt's last line. The first reading even took the prompt's example JSON for two real marks | left out |
| `R06_A_ChatGPT.txt` is **byte-identical to `R06_A_Gemini.txt`** | same sha256 `87792c06...` | one reply saved under two names. It is formatted as Gemini formats (multi-line, no escapes), so I kept it as Gemini's and left the ChatGPT copy out [Likely] |

Consequences: ChatGPT/A covers 195 of the 217 passages (no R02, no R06); **Q6 rests on a single run (Gemini/A)**. **Two chats are still owed: ChatGPT for R02 (order A) and for R06 (order A).** The reader is blind to which person ran which file.

Quotes: reviewers were asked to quote the words that justify each mark. 496 of 550 quotes (90%) are word for word in the passage; ChatGPT 250 of 264 (95%), Gemini 246 of 286 (86%). The rest are paraphrases or altered words, not necessarily inventions (one reviewer's "text is corrupt" remark about R20 is a slip in the Supreme Court's own text, which says "complainant" for "accused").

## 2. How far to trust the marks

- **The two tools agree reasonably:** on the 195 passages both marked in order A they give the same mark 74% of the time (kappa 0.62, "good"); on useful versus not useful 88% (kappa 0.67). Each tool agrees with itself across the two presentation orders (kappa 0.73 for both).
- **No position bias detected:** of the passages marked in both orders, ChatGPT changed its mark on 11 of 60 (6 went up when the passage came earlier, 5 when it came later) and Gemini on 13 of 69 (7 and 6). The changes are noise, not a pull towards the top of the list.
- **The tools differ in temper:** ChatGPT says Yes 37%, Partly 41%, No 9%, Misleading 13%; Gemini says Yes 33%, Partly 39%, No 19%, Misleading 10%. On the common passages ChatGPT marks higher than Gemini 33 times and Gemini higher 17 times. Misleading is the most repeatable mark: where Gemini says it, ChatGPT agrees 83% of the time.
- **They do not judge each passage alone, as told.** They read the other passages in the same file and use what they know: they marked passages Misleading because "a later ruling in another supplied passage" had overruled them (Shafhi Mohammad, the Kanhaiyalal line, Dashrath Rupsingh Rathod). So the relevance marks partly act as a currency check, and a currency check that depends on the new ruling being in the same pack.
- **Limits:** two AI tools, no lawyer; 19 questions; a version's score moves by several points depending on how a disagreement between runs is settled. A gap under about 10 points between versions is not worth acting on.

## 3. What today's search (version A) delivers

"Yes" = directly answers; "Partly" = on the topic, incomplete; Misleading = could give a wrong impression. A passage's mark is the plurality of the runs that marked it; ties are dropped (agreed only), or settled to the lower or to the higher mark. Shares are per question, averaged over the 19 questions (`analysis.json`).

| Of A's top 5 | agreed only | ties to the lower mark | ties to the higher mark |
|---|---|---|---|
| directly answer (Yes) | 40% | 33% | 50% |
| useful (Yes or Partly) | 82% | 76% | 85% |
| misleading | 8% | 12% | 6% |

- The **first result** is a direct answer on 10 to 12 of the 19 questions, useful on 15 to 17; at least one direct answer in the top 5 on 13 to 15; **no useful passage at all on none**.
- **Order carries signal:** by position in A's top 5 the share of Yes is 53% at ranks 1 and 2, 21% at 3, 26% at 4, 11% at 5 (19 questions each): the passages that answer directly are mostly put first.
- **Plain-language questions are the weak spot** (ties to the lower mark): everyday questions 23% Yes and 60% useful (6 questions); narrative 47% and 83% (6); legal-wording 29% and 83% (7), but legal-wording questions carry the most Misleading (17%).
- **Six questions have no direct answer in A's top 5** (agreed or conservative; four if ties go the higher way): R06, R09, R11, R14, R15, R20. They are four different problems: R06 the court's order was not in the library (now fixed: it is rank 1 or 2 once added); R09 and R11 the top 5 is filled with the old law that a later ruling or statute replaced (R09 3 Misleading, R11 2 to 4); R14 the story's wording does not match the case (the rewrite finds 5 Yes there); R15 and R20 the law is new or unsettled and nothing directly answers. R22, one of the four "named case missing" questions, is not a failure: its top 5 has 4 Yes from other cases.
- Where the named key authority is in A's top 5 (10 questions) the top 5 averages 46% Yes and 88% useful; where it is not (R09, R14, R20, R22) 20% and 55% (ties to the lower mark). The key-authority test is a fair proxy except for R22 (and for R15, see the Shivangi Bansal note).

## 4. The versions, like with like (`analysis.json`, `paired_against_A_same_questions`)

Difference from A on the same questions, in percentage points of the top-5 share, ties to the lower mark (the two other treatments point the same way unless noted); interval = bootstrap over questions; "drop one" = the range when any single question is left out.

| Version | Questions | Yes | Useful | Misleading | Reading |
|---|---|---|---|---|---|
| B no repeats | 19 | +1 | +1 | -1 | the same as A in practice: it differs on one or two questions only |
| E no multiplier (no passage-type weights, no section boost) | 19 | -6 (drop one: -3 to -7) | -4 | +5 (interval +1 to +11) | **worse than A in all 7 treatments and with any one question left out**; the weights help, mostly by pushing down passages that record a lawyer's argument |
| S site shown (the live site's own search) | 19 | -9 (interval -19 to +1; -14 with ties higher, interval -22 to -7) | **-10 to -11 in all three treatments (interval about -22 to 0)** | -4 | **clearly weaker**, above all on everyday questions (Yes 10% against 23%; useful 39% against 60%); equal on legal-wording questions (Yes 33% against 29%; useful 81% against 83%); its first result is a direct answer on 5 of 19 questions against A's 10 |
| C rewrite | 12 | +5 (interval -12 to +25) | +3 | +3 | no reliable gain: **it is one question**: without R14 the Yes gain is -4 to +3 points depending on the treatment |
| F merged | 12 | +12 (interval -2 to +30) | 0 | +7 | the same: without R14 it is +2 to +4 points, and Misleading rises 4 to 9 points because the rewrite also pulls in the old Kanhaiyalal line (R11) and the Family Welfare Committee directions (R15) |

The authority-hit test (no marks) had also found no gain from the rewrite in reaching the named case. **Neither the marks nor that test show a general benefit from rewriting; the marks show one dramatic rescue (R14: A 0 Yes, C and F 5 Yes of 5) and some added risk of old law.** A rewrite costs a language-model call and three times the re-ranking of A.

## 5. The two lights per domain, tuning half, version A (`lights/LIGHTS.md`, every treatment)

Thresholds fixed before any mark was seen. A domain here is one to three questions: a first reading, not a verdict.

| Domain | Questions used | Relevance (7 treatments) | Currency (listed stale rulings only) |
|---|---|---|---|
| A Arrest and custody | R01, R02 | green in all 7 | no trap in this half |
| B Bail | R04 | green in all 7 | green (R04: Salauddin not in the top 5) |
| C Cheque bounce | R08, R09 | unstable: amber 2, red 2, green 1 | **red** (R09: Dashrath, the 2014 rule the 2015 Act replaced, is in the top 5) |
| D NDPS | R11 | amber (6 of 7) | green on the list; **but** two passages of the Kanhaiyalal line are flagged Misleading in A's top 5 (see 6) |
| E FIR quashing, civil disputes | R12, R14 | mixed: green 3, amber 4 | no trap in this half |
| F Marriage-related | R17 (R15 is an index-gap question and is left out) | green in all 7 (one question) | **red** (R15: Rajesh Sharma, modified in 2018, ranks 1 and 2) |
| G Sexual offences | R19, R20 | mixed: green 3, amber 2 | no trap in this half |
| H Violent crime, evidence | R22 (R21 is an index-gap question) | red in all 5, **from one question**: 4 of its 5 passages are Yes, but one in the top 3 is Misleading | **red** (R21: Shafhi Mohammad, overruled, ranks 1) |
| I Special-statute arrest and bail | R24 | green | no trap in this half |
| J After conviction | R26 | green | no trap in this half |

Currency is red in 3 of the 5 domains that have a trap question in this half. The controls (K) are discussed in section 8.

## 6. Old law is the main danger, and the list of known stale rulings under-counts it

- Of the 30 passages any reviewer called Misleading, **19 (63%) were flagged for law that a later ruling or statute replaced**, 5 for recording a lawyer's submission rather than the court's holding, 6 for other reasons (my reading of their stated reasons). Where most of the runs said Misleading (16 passages), 12 are about replaced law.
- All 4 passages of listed stale rulings in A's top 5 were marked not useful (0 Yes or Partly; 2 Misleading, 2 No). So when a famous overruling sits in the same file, the reviewers see it.
- **The Kanhaiyalal line.** In R11 the Misleading passages are not only Kanhaiyalal (2008): they include Ram Singh v. Central Bureau of Narcotics (1992), Surinder Kumar Khanna v. Intelligence Officer, Directorate of Revenue Intelligence (2018) and a 2023 passage of Balwinder Singh (Binda) v. Narcotics Control Bureau that recounts the old rule (all four runs flagged each of them). Tofan Singh (2020) overruled the rule these cases applied, but only Kanhaiyalal and Karwal are on a list. **A currency check that flags only the overruled case itself misses the cases that relied on it.** The checker's mention finder already records which later judgments "followed" a case, so "relies on a ruling that was overruled" is a feasible warning.
- In 4 of the 19 questions A's top 5 carries replaced law (R09, R11, R15, R21).

## 7. The re-ranker and the marks

- The re-ranker is used by A, B, E, C and F (74 calls, 1,812,788 tokens; not by S); its effect on where the named authority lands is in `../2026-10-09_real30_pool_dev/HOW_THE_SEARCH_WORKS_STEP_BY_STEP.md`.
- **The marks cannot yet say whether it helps usefulness.** Of the 90 passages in the merged top 5 of 18 questions (the order before the re-ranker), **35 were never shown by any version and so were never marked**. The 60 passages the re-ranker pulled into A's top 5 from beyond the merged top 5 were 28% Yes, 77% useful and 15% Misleading; the 30 that were already in the merged top 5 were 47% Yes, 83% useful, 7% Misleading. That is not a verdict on the re-ranker (we do not know how the 60 it pushed out would have been marked), only a warning that what it adds from far down the list is weaker than what the three searches already agreed on.
- **A clean test is cheap:** mark the 35 passages (18 small prompts, one per question, in both tools = 36 chats, no money) and score the merged top 5 as a version "without the re-ranker".

## 8. The two controls did not behave as controls

R28 (divorce by mutual consent, the 6-month wait) and R29 (section 38 BNSS) were meant to have no good answer in a criminal-law library. A's top 5 is 2 Yes and 3 Partly for R28 and 1 Yes and 4 Partly for R29. For R28 it is pre-2018 Supreme Court material (A.B. Bhaskara Rao 2011, Harpreet Singh Popli 2009, Inderjit Singh Grewal 2011: criminal-labelled cases that discuss the waiting period) while the two later controlling rulings (Amardeep Singh, 2017; Shilpa Sailesh, 2023) are outside the library because the criminal-law filter dropped them. For R29 a 2025 ruling (Mihir Rajesh Shah, para 36) does say that section 38 BNSS gives the right to meet an advocate. So the search gives **no "nothing found" signal** for an out-of-scope question, and the controls are not clean ones; Mr. Advocate has been asked for cleaner controls (sheet E).

## 9. What follows, and what is waiting

1. Keep A as the baseline: B is the same, E is worse, S (the live site's own retrieval) is clearly worse on everyday questions. If the big index is connected to the site, connect it through A's pipeline (re-ranker included), not through the site's search; A costs about a tenth of a cent of re-ranking per question (one call of about 18,000 to 26,000 tokens).
2. The rewrite deserves a second look only as a rescue for questions where A finds nothing (R14), not as a default; it needs more everyday questions than 6 to judge. The sealed half has 4 everyday questions.
3. Build the currency warning in two steps: the lists Mr. Advocate is asked for (modified and replaced-by-statute rulings: Rajesh Sharma, Dashrath), then "relies on an overruled ruling" using the mention finder.
4. Owed by J and S: ChatGPT chats for R02 (order A) and R06 (order A), plus the optional 36 chats for the 35 unmarked merged-top-5 passages.
5. Decisions for the owner: whether the sealed run includes the side indexes; which versions the sealed run carries (my suggestion: A, F and S only, which makes a smaller pool to mark than the six versions of this round, about 217 passages for 19 questions); everything above is on the tuning half and on AI marks only.

Files: `replies_as_received/`, `replies_for_the_reader/`, `replies_for_the_reader_NORMALISATION.json`, `ingest/` (the reader's summary, marks CSV, sensitivity CSV), `lights/` (`LIGHTS.md`, `lights.json`), `analyse_marks.py`, `analysis.json`, `RESULTS_IN_PLAIN_TERMS.md`.
