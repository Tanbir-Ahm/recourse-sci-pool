# The plan, for the record: choosing the search for the big index with 30 real questions

**ACCEPTED by the owner on 2026-10-08, in full: the domain table, the sealing default (about 11-12 sealed), the draft traffic-light rule and the duplicate fix (apply it before pooling). Work on the plan proceeds after the weekly register routine and the full register workbook were delivered (also 2026-10-08).** Written 2026-10-08, after commit `25d68cb` on `claude/sharp-euler-unyfv0`. PRIVATE (answer key and sealed questions live here). Nothing in this plan connects anything to the live Recourse site, merges to `main`, opens a pull request or creates a scheduled routine; each of those needs the owner's separate say-so. Every figure the plan produces carries its source label: **LLM-judged** unless a lawyer's sheet is in it.

## 1. Purpose

Decide, before any connection to the live site: (a) which search recipe over the big index to carry forward; (b) in which areas of criminal law the index is good enough to switch on and in which it is not (a readiness map); (c) whether stale law (overruled or doubted cases) is caught, by the register, the checker or neither.

## 2. What exists today (done and pushed)

- **The ruler** (`review_data/ruler/`, commit `d9c1eae`): 16 topics, 32 active questions (24 for tuning, 8 sealed: T08 default bail, T12 NDPS Section 37 bail, T13 informant who also investigated, T16 domestic violence after leaving). 44 key paragraphs, all found in the index. Q06 is superseded by Q06v2 (Section 326, not 325). Freeze hash `48cbb184c9098e25739afd031a4f6ede190c1c246ad255da960c7e0ab89dbbc7`. The guard hands the sealed questions out once, for a final run with a label, and logs it. Its answer key comes from Recourse's hand-verified excerpts (new topics) and this project's own picks (first six): it is **not lawyer-checked, and biased toward famous, settled cases**.
- **The currency pass** (`review_tools/currency_pass.py`, commit `25d68cb`): runs the Overruled Register over saved search results as a second pass kept apart from the relevance marks.
- **The register sweep** now reads back to 2000 (42 new proposals, 232 open, none read). It finds only judgments that use overruling words and found neither Prabha Shankar Dubey nor Krishna Janardhan Bhat.
- The index: **10,505 criminal-law judgments, 236,155 passages** after the duplicate fix of 2026-10-08 (was 10,509 and 236,814; index commit `3c80a26`), in `../recourse-sci-index`. The first 12 questions were marked on the older index of about 8,200 judgments.

## 3. The 30 real questions (to be supplied by the owner)

**Domain table (accepted by the owner 2026-10-08):**

| | Domain | Questions | Recourse today | Index mentions (judgments) |
|---|---|---|---|---|
| A | Arrest and custody rights | 3 | in scope, pinned | arrest safeguards 215 |
| B | Bail: regular, anticipatory, default | 3 | in scope, pinned | bail 3,003; anticipatory 530; default 145 |
| C | Cheque bounce (Section 138) | 3 | own flow | 448 |
| D | NDPS | 2 | own flow | 490 |
| E | FIR quashing; civil dispute dressed as crime (cheating, forgery, breach of trust) | 3 | in scope, thin | cheating 1,723; forgery 1,527; quashing 2,739 |
| F | Marriage-related: 498A, dowry, 304B, 306, domestic violence | 3 | partly | 498A 696; 304B 456; 306 503; DV 75 |
| G | Sexual offences and POCSO | 3 | POCSO refused | rape 1,187; POCSO 107 |
| H | Violent crime: murder, hurt, evidence, sentence | 3 | not covered | murder 4,677; hurt 2,146 |
| I | Special-statute arrest and bail: PMLA, UAPA, SC/ST, corruption | 2 | UAPA refused | PMLA 93; UAPA/terror 673; SC/ST 197; PC Act 971 |
| J | After conviction: appeal, suspended sentence, remission, parole | 2 | not covered | remission 441 |
| K | Controls (no good answer): one civil/tax/divorce; one High Court-only or 2026 point; one a statute table answers | 3 | n/a | - |

Counts are judgments that **mention** the topic (a word match), not judgments that are about it. Areas "not covered" or "refused" are outside today's product scope: what to open is the owner's product decision; the questions tell him what the index can support.

**Inside the 30:** at least 5 everyday, 5 legal-wording and 5 long messy narrative questions; at least 5 using BNS/BNSS section numbers, 5 using IPC/CrPC numbers, the rest none (the index speaks IPC/CrPC and its section search ignores which code a number belongs to); at least 3 currency traps from Mr. Advocate (the first ruling a search finds was later overtaken); at least 8 where the best law is from 2017 on; 3-4 Hinglish questions exactly as written if real users write that way.

**Format and privacy.** One file; each question as the client said it; tagged everyday / legal / narrative; "trap" where known; no answers, no case names; **anonymised** (no names, places, case numbers): questions go to Voyage (embedding, re-ranking), to ChatGPT/Gemini (marking, by J and S) and into the private repository. Anonymised real questions from Recourse's own WhatsApp logs would be better than imagined ones if that database keeps the text (not known).

**Sealing (default unless the owner says otherwise).** About 11-12 of the 30 are sealed by the fixed rule used for the ruler: inside each domain, order that domain's questions by SHA-256 of `seed|question id` and seal the first (one of three; one of two). Written down and hashed before any search. Sealed questions are neither searched nor marked until the final run.

**Update 2026-10-09: the owner's file arrived** (`review_data/ruler/inputs/2026-10-09_owner_30_questions.xlsx`; review in `review_results/2026-10-09_real30_file_review/REVIEW.md`). It is a constructed set that follows this section's counts exactly, with an answer key (expected answer, key authority, sources) in the same file, not 30 real questions. Findings that change this plan, all awaiting the owner's decisions: (1) ten of the 30 repeat ruler topics, so sealing needs a link-first step (a question that shares a case or a doctrine group with a ruler topic takes that topic's side); (2) Q6, Q15 and Q21 cannot be answered from the index (their key authorities are filtered out or absent) and are scored separately as index gaps; (3) 13 of 27 are currency traps, so the traffic-light rule needs a second, separate currency light; (4) Q29 is not a clean control; (5) no Hinglish yet. The answer columns never go to Voyage, ChatGPT/Gemini, J or S. Nothing is built, sealed or searched yet.

## 4. How they will be searched

- Run here, in the cloud session, over a copy of the index. **Not connected to the live site** (read-only to this project, no link to the big index). Outside calls: Voyage only (embedding, re-ranking).
- **Recipes pooled, none chosen in advance:** A (today: re-ranker x passage-type weights), B (no repeated passages), E (no weights), S (the live site's own method run on the big index, without its hand pins and topic routing; a comparison arm), and a **blind rewrite arm** (a fixed instruction to a model rewrites each everyday or narrative question into legal wording, saved before any search; not written by me with the answer in view). L does not apply (no keys).
- Each recipe's top results are merged and de-duplicated into one pool per question; reviewers do not see which recipe found what.
- Also run: the first 12 questions on the current index (only the new passages need marks), Q06v2, and the 20 new ruler questions. The 20 new ruler questions are scored first by the **automatic key-paragraph test** (is Recourse's key paragraph in the top results?), which needs no human marks; human marks on them come only if time allows. The sealed ruler questions are run only in the final run.
- **Duplicate fix (accepted 2026-10-08): applied on 2026-10-08 before any pooling** (4 judgments, 659 passages removed; `index_fixes/2026-10-08/README.md`). Its EVAL step (a few cents of Voyage) waits for the allowance.

## 5. How they will be marked

AI tools (ChatGPT and Gemini, run by J and S) mark each passage Yes / Partly / No / Misleading, seeing only the question and the passage. Both tools on every question (the first round never had that), the A order for all and the reversed order for about a third (order check). Marking priority: the 30 real questions and Q06v2 (31 packs x 2 tools = 62 chats, plus about 10 reversed-order chats), then top-ups for the old 12 (about 12 smaller chats): **about 85 chats in all [estimate]**, spread over J and S. Marking the 20 new ruler questions as well would add about 55 more; I recommend not doing that unless the key-paragraph test looks wrong. A lawyer reads the Misleading and borderline calls and spot-checks about 20 labels. Until then every figure is LLM-judged. J's Q09 (Gemini, orders A and B; optionally Q03) is still missing and Q09 rests on one reader.

## 6. Currency checks (the register is NOT on while marking)

1. Search and marking with the register off, so relevance numbers stay clean.
2. `currency_pass.py` over the saved pools: per recipe, passages from register cases and from known-stale cases, and what the demotion lock would change (the "search + register" arm).
3. Mr. Advocate's trap questions test whether the register holds the trap rulings; a gap goes to his weekly sheet as a proposal, never as a row.
4. The checker (warnings only) is run on the judgments that reach a top 5, a few hundred, offline. Not yet tried at that scale; its recall on known overruled pairs was 26%.
5. Known limits: the register knows only explicit Supreme Court overrulings; the sweep sees only overruling words; "doubted", "distinguished" and statute changes are invisible. On the first pool the register held 6 of 10 known-stale cases, flagged none of the stale passages and falsely flagged none of 13 settled cases.

## 7. How the results are read

- A recipe is preferred only if it points the same way in every treatment (agreed marks only, ties to the lower mark, ties to the higher mark, each run alone) **and** on the sealed half.
- The rewrite arm is carried forward only if the blind rewrite keeps most of the gain the hand rewrite showed.
- **Readiness map:** a traffic light per domain. Rule (accepted by the owner 2026-10-08 as the draft; thresholds are [Guessing] and may be adjusted only before any mark is seen): green = Yes-or-Partly at least 80% of the top 5, no Misleading in the top 3, no stale-case passage in the top 5; red = under 60% or a Misleading in the top 3 on most questions; amber otherwise. Two or three questions per domain is a first reading, not proof. The map is final only after the sealed run.
- Tuning (for instance the "who is speaking" passage labels) uses the tuning half only, and nothing seen on a sealed topic may motivate a rule.
- Results on the 32 ruler questions are labelled "well-known settled topics, Recourse's picks" and are not compared with the live site, which was tuned on those topics.

## 8. Order of work

| Step | Who | Needs |
|---|---|---|
| 1 | Owner | (the Excel form `review_data/ruler/real_questions_template.xlsx` is ready) the 30 anonymised questions, the confirmed domain table, the sealing default, the Voyage allowance, the duplicate-fix decision, Mr. Advocate's traps, J's Q09, a 20-label spot-check |
| 2 | Claude | `python review_tools/real_questions.py build --intake FILLED.xlsx` (checks the form, names any shortfall against the plan, ids R01 to R30 in row order, seals by the fixed rule, writes `real30_v1.json` with the freeze hash; tested by `test_real_questions.py`), commit before any search |
| 3 | Claude | pools for the tuning half of the real questions, Q06v2, the old 12 and the 20 new ruler questions (Voyage); the key-paragraph test on the ruler questions; a spend report against the allowance |
| 4 | J, S | marking packs built by Claude, both tools |
| 5 | Claude | scores, sensitivity table, currency pass, first readiness map; a plain-terms report |
| 6 | Owner | decide the recipe(s) to carry forward; any tuning is done on the tuning half only |
| 7 | Claude, J, S | the sealed run, once, logged |
| 8 | Owner, Claude | only then: a separate plan to connect the index to the site (the standing item: cards overlay for every citable case, a "not checked by us" wording, the owner applies the patch himself) |

## 9. Costs and risks

- **Voyage re-ranking:** about 4.5-7.5 million tokens for 30 questions plus the re-runs [guess]; the balance was read on 2026-10-09 ($9.88, shared with the live site); the cap and the estimate are in section 11.
- **Reviewer effort:** the largest cost; see section 5.
- **Limits that remain:** AI marks are not lawyer marks; the ruler's answer key is Recourse's pick; 30 questions give crude domain readings and about 12 sealed questions show only large differences; the index lacks some cases (Satender Kumar Antil Jan 2026, Youth Bar Association, Usha Chakraborty; Mohan Lal 2018 is in the index, contrary to what an earlier version of this plan said; Shreya Singhal and the domestic-violence cases are cut by its criminal-law filter; 2026 coverage is partial); the index speaks IPC/CrPC while users now speak BNS/BNSS.

## 10. Open items outside this plan (unchanged)

Weekly register routine not created; trap exam for the register not run; nobody has reviewed a register row; licence question on list 1; authority workbook part 1; Q05 versions C and F need re-running on the corrected rewrite; the register sweep wording is not widened (needs a precision test first).

## 11. Decisions of 2026-10-09 (owner: "Yes, go ahead with all the defaults"), and what was built

**The set.** The 30 questions are the owner's file (kept at `review_data/ruler/inputs/2026-10-09_owner_30_questions.xlsx`). Built by `review_tools/real30_build.py` into `review_data/ruler/real30_v1.json` (questions only; ids R01 to R30 = the owner's Q1 to Q30) and `real30_key_v1.json` (the private key: expected answers, authorities, trap pairs, sources; never read by a search or a pack builder). Label: "re-told from reported cases and government sources (owner's statement); not client messages; per-question source not recorded". Every figure from the set is a best case.

**Link-first sealing** (`real30_links_v1.json`, written before the seal): a question that shares a case or a doctrine group with a ruler topic takes that topic's side; the rest are sealed by the hash rule inside each domain. **Sealed (11): R03, R05, R07, R10, R13, R16, R18, R23, R25, R27, R30.** Tuning (19): the rest. Freeze hash of the sealed content `8aa158ba889369b2c7b87872335d0abe261eedf4174a9f99df3154f82643381c`; split hash (sides, links, rule) `6e42f467c5ce6e69dacf6e631dcf4f58e428fbb5f1b75810b68c31c6be32e9e0`; both written before any search. Ten questions are linked (R01, R02, R05, R10, R11, R12, R14, R15, R16, R24); the borderline ones left free are recorded in the links file (R07, R13, R19 against the compounding group). The sealed questions are handed out once by `real_questions.select`.

**Q6, Q15, Q21 are scored apart** as index gaps (their key authority is filtered out of the index or absent); they stay on the tuning side and are marked like the others. **Q29 is a cut-off trap**, not a control: the clean "High Court only or 2026" control is still missing and is asked of Mr. Advocate (the builder prints it as a GAP).

**Two lights per domain** (replacing the single light of section 7; thresholds are [Guessing] and may be adjusted only before any mark is seen):
- *Relevance light*, from search alone: green = Yes-or-Partly at least 80% of the top 5 and no Misleading in the top 3 on most questions; red = under 60% or a Misleading in the top 3 on most; amber otherwise. Questions whose key authority is unreachable are left out and counted as index gaps.
- *Currency light*: for the domain's trap questions, green = no passage from a known-stale ruling (one that counts as stale in `real30_stale_status_v1.json`) in the top 5; red = one in the top 5 of most trap questions; amber otherwise; reported without the register and, separately, with the register's demotion. A narrower or contested older ruling is listed but does not count.
Two questions or three per domain is a first reading; both lights are final only after the sealed run.

**Index held at commit `3c80a26`** (10,503 judgments with passages, 236,155 passages; the 10,505 counted earlier included two judgments with no usable passage). The pool runner refuses another head. The 2026-10-12 refresh decision waits until the run is over.

**Voyage.** Balance read from the owner's dashboard on 2026-10-09: **$9.88**, auto-recharge off; the account is shared with the live site. Re-ranking `rerank-2` is listed at about $0.05 per million tokens (third-party price lists, not Voyage's own page; the first real call's billed tokens will be checked against it) and query embeddings with `voyage-law-2` at $0.12 per million. The estimate for the whole run (tuning half, then the sealed half) is about 10 to 12 million re-rank tokens, about $0.50 to $0.60. **Cap set by Claude: 15 million re-rank tokens (about $0.75) for the tuning half and 30 million (about $1.50) for the whole experiment**; the runner stops at the cap and says so. Anything beyond is asked of the owner. At least $8 stays for the live site.

**What was run on 2026-10-09 (after the seal, the rewrites and the runner were committed).** The tuning half of the 30 (19 questions) and the ruler's tuning half (24 questions) were pooled over index `3c80a26`: about $0.13 of the $9.88 balance and 2.63 million of the 30 million re-rank-token cap. First look, with no reviewer mark: the key authority named in the owner's file is in the top 5 of version A for 10 of the 14 answerable questions (E 9, S 6); the blind rewrite gives no gain (like with like on 9 questions: A 7, C 6, F 6); on the two questions the index cannot answer an old ruling is in every version's top 5. The marking pack (19 questions, 50 chats) is with the owner for J and S. Details: `review_results/2026-10-09_real30_pool_dev/README.md`, `review_results/2026-10-09_ruler_pool_dev/README.md`.

**Added later on 2026-10-09 ("the way forward"): a side index for library gaps.** The measurement round stays on the main index alone. A separate side index (`review_data/side_index/2026-10-09_correcting_judgments/`, 17 judgments the register links to rulings the index holds; built by `review_tools/build_supplement.py`; $0.098) was searched as an extra arm on the tuning half (`review_results/2026-10-09_real30_pool_dev_plus_side_index/`; $0.091): Q21's correcting ruling (Arjun Panditrao) is found at rank 2 and nothing else got worse. Q6 and Q15 need two documents the working environment cannot fetch (network policy). If the owner wants the final system to include the side index, the sealed run (once only) must use it; this is to be decided before that run, together with the marks for the arm's 5 new passages. Sizing and its correction: `review_results/2026-10-09_index_gap_sizing/README.md`.

**Sizings of 2026-10-09 (read-only).** Headnotes as extra passages: $0.20 to $0.53 for the 2,247 law-report judgments in the index, but three of the four answerable misses have pre-2017 key authorities without a headnote, so the idea is parked until the marks show where the real weaknesses are. The criminal-law filter (density 10 per 10,000 characters) leaves out 559 judgments at density 6 to 10 (about $0.55) and 1,244 at 3 or more (about $1.23), and dropped 1 of the 35 key authorities; a lower line is a proposal for the new snapshot (`review_results/2026-10-09_headnote_and_filter_sizing/README.md`). The workbook for Mr. Advocate is `review_results/2026-10-09_mr_advocate_sheet/`.

**Q6 and Q15 fetched (2026-10-09, network opened by the owner).** Q6's key order (23 Aug 2024) was fetched from the court's site and verified; in the library it is found at rank 1 or 2 by every version. Q15's key judgment (Shivangi Bansal, 2025) was fetched from the owner's Indian Kanoon link and read: a consent settlement with a one-sentence direction about the High Court's Family Welfare Committee guidelines; the search does not bring it up (rank 6 in the rewrite version only) because it is far from the question by meaning, so Q15 should be read as a currency question, not a library gap. The search method, with the re-ranker's measured effect: `review_results/2026-10-09_real30_pool_dev/HOW_THE_SEARCH_WORKS_STEP_BY_STEP.md`.


**Marks of J and S on the tuning half, analysed 2026-10-09 (AI marks only; `review_results/2026-10-09_real30_marking_analysis/`).** Files repaired without changing a mark (`review_tools/normalise_replies.py`); the two missing ChatGPT chats (R02 and R06, order A) arrived the same day and were added, so every passage is marked by both tools. Today's recipe (A): top 5 = 40% direct answers, 80% useful, 8% misleading (ranges over how ties are settled: 33 to 51, 75 to 87, 6 to 13); the rating with intervals, each tool alone and the reasons is `ACCURACY_RATING.md` there. Against A on the same questions: B equal; E worse (Yes -6, Misleading +5); S clearly weaker (useful -10 to -11); C and F gain +5 and +12 points of Yes only through R14 and pull in more old law. The two lights were computed for the tuning half (`lights/LIGHTS.md`): relevance green in 5 of 10 domains, mixed or amber in 4, red in 1 from a single question; currency red in 3 of the 5 domains with a trap question in this half. The main danger is old law (19 of 34 Misleading passages), not finding passages; the stale list under-counts it. Nothing was changed in the sealed half, the key, the seal or the index (still `3c80a26`).

**Re-ranker test pack and safety net (2026-10-09).** Because the marks cannot say whether the re-ranker helps (39 of the 95 merged-top-5 passages were never shown to a reviewer), a second batch was built (`review_results/2026-10-09_real30_rerank_test_pack/`: 143 passages, 19 prompts, 38 chats; 39 never-shown merged-top-5 passages, 66 of A's places 6 to 10, 38 repeated anchors) with a scorer ready (`review_tools/score_rerank_arms.py`). The recipe gained an opt-in **safety net** (`pool_runner.py --safety-net`, no extra call): the list to show is A's ten, untouched (the top 5 always follows the rules already set), followed by the merged top 5 that A's ten do not show, placed after place ten and ranked by A's own query-based score, at most 15 (the owner's correction of the same day: nothing is forced into the top 5, the extra passages are ranked by the question). It does not bring up the named cases A's ten lack (they were not in the merged top 5); named cases of the 30 questions were not pinned into the search (the key stays out of every search). If the sealed run is to carry the arms, say so before it; it adds about 50 passages to mark.
