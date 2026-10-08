# The plan, for the record: choosing the search for the big index with 30 real questions

**ACCEPTED by the owner on 2026-10-08, in full: the domain table, the sealing default (about 11-12 sealed), the draft traffic-light rule and the duplicate fix (apply it before pooling). Work on the plan proceeds after the weekly register routine and the full register workbook were delivered (also 2026-10-08).** Written 2026-10-08, after commit `25d68cb` on `claude/sharp-euler-unyfv0`. PRIVATE (answer key and sealed questions live here). Nothing in this plan connects anything to the live Recourse site, merges to `main`, opens a pull request or creates a scheduled routine; each of those needs the owner's separate say-so. Every figure the plan produces carries its source label: **LLM-judged** unless a lawyer's sheet is in it.

## 1. Purpose

Decide, before any connection to the live site: (a) which search recipe over the big index to carry forward; (b) in which areas of criminal law the index is good enough to switch on and in which it is not (a readiness map); (c) whether stale law (overruled or doubted cases) is caught, by the register, the checker or neither.

## 2. What exists today (done and pushed)

- **The ruler** (`review_data/ruler/`, commit `d9c1eae`): 16 topics, 32 active questions (24 for tuning, 8 sealed: T08 default bail, T12 NDPS Section 37 bail, T13 informant who also investigated, T16 domestic violence after leaving). 44 key paragraphs, all found in the index. Q06 is superseded by Q06v2 (Section 326, not 325). Freeze hash `48cbb184c9098e25739afd031a4f6ede190c1c246ad255da960c7e0ab89dbbc7`. The guard hands the sealed questions out once, for a final run with a label, and logs it. Its answer key comes from Recourse's hand-verified excerpts (new topics) and this project's own picks (first six): it is **not lawyer-checked, and biased toward famous, settled cases**.
- **The currency pass** (`review_tools/currency_pass.py`, commit `25d68cb`): runs the Overruled Register over saved search results as a second pass kept apart from the relevance marks.
- **The register sweep** now reads back to 2000 (42 new proposals, 232 open, none read). It finds only judgments that use overruling words and found neither Prabha Shankar Dubey nor Krishna Janardhan Bhat.
- The index: **10,509 criminal-law judgments, 236,814 passages**, in `../recourse-sci-index`. The first 12 questions were marked on the older index of about 8,200 judgments.

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

## 4. How they will be searched

- Run here, in the cloud session, over a copy of the index. **Not connected to the live site** (read-only to this project, no link to the big index). Outside calls: Voyage only (embedding, re-ranking).
- **Recipes pooled, none chosen in advance:** A (today: re-ranker x passage-type weights), B (no repeated passages), E (no weights), S (the live site's own method run on the big index, without its hand pins and topic routing; a comparison arm), and a **blind rewrite arm** (a fixed instruction to a model rewrites each everyday or narrative question into legal wording, saved before any search; not written by me with the answer in view). L does not apply (no keys).
- Each recipe's top results are merged and de-duplicated into one pool per question; reviewers do not see which recipe found what.
- Also run: the first 12 questions on the current index (only the new passages need marks), Q06v2, and the 20 new ruler questions. The 20 new ruler questions are scored first by the **automatic key-paragraph test** (is Recourse's key paragraph in the top results?), which needs no human marks; human marks on them come only if time allows. The sealed ruler questions are run only in the final run.
- **Duplicate fix (accepted 2026-10-08): apply it to the index before pooling** (removes 659 passages), so the baseline is measured once.

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
| 1 | Owner | the 30 anonymised questions, the confirmed domain table, the sealing default, the Voyage allowance, the duplicate-fix decision, Mr. Advocate's traps, J's Q09, a 20-label spot-check |
| 2 | Claude | load the questions into a new ruler version, assign the halves by the fixed rule, hash it, commit (before any search) |
| 3 | Claude | pools for the tuning half of the real questions, Q06v2, the old 12 and the 20 new ruler questions (Voyage); the key-paragraph test on the ruler questions; a spend report against the allowance |
| 4 | J, S | marking packs built by Claude, both tools |
| 5 | Claude | scores, sensitivity table, currency pass, first readiness map; a plain-terms report |
| 6 | Owner | decide the recipe(s) to carry forward; any tuning is done on the tuning half only |
| 7 | Claude, J, S | the sealed run, once, logged |
| 8 | Owner, Claude | only then: a separate plan to connect the index to the site (the standing item: cards overlay for every citable case, a "not checked by us" wording, the owner applies the patch himself) |

## 9. Costs and risks

- **Voyage re-ranking:** about 4.5-7.5 million tokens for 30 questions plus the re-runs [guess]; the allowance on the owner's dashboard is not yet read and nothing is run before it is.
- **Reviewer effort:** the largest cost; see section 5.
- **Limits that remain:** AI marks are not lawyer marks; the ruler's answer key is Recourse's pick; 30 questions give crude domain readings and about 12 sealed questions show only large differences; the index lacks some cases (Satender Kumar Antil Jan 2026, Youth Bar Association, Usha Chakraborty; Mohan Lal 2018 is in the index, contrary to what an earlier version of this plan said; Shreya Singhal and the domestic-violence cases are cut by its criminal-law filter; 2026 coverage is partial); the index speaks IPC/CrPC while users now speak BNS/BNSS.

## 10. Open items outside this plan (unchanged)

Weekly register routine not created; trap exam for the register not run; nobody has reviewed a register row; licence question on list 1; authority workbook part 1; Q05 versions C and F need re-running on the corrected rewrite; the register sweep wording is not widened (needs a precision test first).
