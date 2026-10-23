# PDF / Word export and the search page: what was built, what was measured, what is not proven

Date: 2026-10-23. Owner's go: "1. I want two modules. One, a public with a problem and lawyers who want research and drafting. 2. Yes, I want a PDF / word export and the search page".
Code: Recourse branch `register-hooks-and-overlay` (NOT on `main`, nothing deployed) and the owner's private repository `Tanbir-Ahm/recourse-web`.
**Drafting (the lawyers' drafting module) is NOT approved and NOT started; ask before starting it.**

## 1. What was built

| Part | Where | State |
|---|---|---|
| PDF and Word export of one answer or a whole conversation, carrying every box and warning of the page, proved complete by reading the file back | `answer_export.py`, `GET /api/chats/{id}/export?format=pdf|docx[&message=id]` (Recourse `3cfc962`, already on the remote branch) | built, tested |
| Search page engine | `search_service.py` (Recourse `79605c6`, `822293b`, `29cba26`) | built, tested, **local only until pushed** |
| Search route | `POST /api/search` (`454a84d`): one unit of the plan's daily `search` allowance per search, `search_wider` for the separate wider request; migration 0002; plan limits (provisional) | built, tested |
| Stemmer | `search_stem.py` (no new dependency) | built, tested |
| Two modules, the search page, download buttons | `recourse-web` `b8ab7f4`, `f95ef10`, `87b3892`, `ad0551a` | built, tested with a stub engine |

How a search is read (`parse_query`): the query is classified first and only the parts that fit run: a **citation** ("(2014) 8 SCC 273", "2014 INSC 463") finds cases by that citation only; a **bare number** ("17") gives that section of every Act held; **sections** ("IPC 420", "BNSS 187", "sections 103 and 105 of the BNS", "section 17 PC Act"; an old IPC/CrPC number goes through the table of corresponding sections to the BNS/BNSS section and says so); an **Act** alone gives its card (held or not held; an Act Recourse does not hold gets its official link and never a lookalike section of another Act); **words** give sections (below), cases whose name holds the words (the library's 68 and the Supreme Court title index of 38,026 rows), and paragraphs of library judgments. Every case carries the Overruled Register / checker sentence or the fixed "Not checked by us." The wider search (Supreme Court passages) is a separate request, labelled "not independently verified". No model is called; nothing the engine returns is written by a model.

## 2. Round 2 of the section search (words): what it is, and what was measured

Round 1 matched the words typed against Recourse's chunk text with a small list of word endings and a plain BM25. Round 2 (this session) changed three things:

1. **A Porter stemmer** (`search_stem.py`), so that "punishment" finds "punished", "bribing" finds "bribe", "abetting" finds "abetment".
2. **One index for all sections** (918 library sections of the BNS, BNSS, IT Act, NI Act and 385 sections of the nine Acts on the shelf), instead of two separate searches that were then interleaved. BNSS section 531 is indexed without the Schedules that Recourse's chunk runs together with it (98,051 characters; the Schedules would match nearly every query): 1,840 characters are indexed.
3. **Meaning across all the Acts on the shelf**: round 1 searched the shelf by meaning only when the person named the Act. Now each shelf Act offers its best three sections whose cosine to the query is at least 0.50 (a floor chosen from the tuning set's cosines, then checked for sensitivity below), fused by rank with the words and with the library's own meaning list (cosine at least 0.34, the best 40).

Also fixed on the way: the cache of the shelf's index was keyed by the memory address of a dictionary that is rebuilt for every search (it worked by luck of address reuse); a failed read of the library is no longer kept in the cache.

A fourth idea was tried and **removed**: a second word list over only the opening of each section (title and the first 350 characters), on the reasoning that a section says what it is about at the start. On the tuning set the engine without it was better (45/48 against 43/48 at rank 5, MRR 0.831 against 0.779), at every length tried (150 to 800 characters) it was no better than without. It is not in the code.

### 2.1 The stemmer was checked against two independent implementations

`search_stem.stem` was compared with NLTK's `PorterStemmer` in its original-algorithm mode (and with the snowball `porter` stemmer) over **85,325 distinct words**: every word of Recourse's own texts and judgments, other English text on the machine, and 60,000 random root + suffix + suffix products that exercise every rule. **No difference for any word of three or more letters.** The only differences are words of one or two letters ("is", "as", "us"), which the reference implementations cut and this one deliberately leaves alone (as Porter's own C code does). Those libraries are not a dependency of the project; the comparison was run once from a scratch folder, and the repository's `test_search_stem.py` (61 checks) holds Porter's published examples and the legal words instead.

### 2.2 The numbers

Two sets of questions, both written by Claude, each with the sections expected for each question:

* **Tuning set**: 48 questions (`search_gold_questions.json`, frozen at commit `601b31d` before any retrieval was run on them). It WAS looked at while designing round 2 (the misses of round 1 shaped the design; the lead list and the floors were decided on it).
* **Held-out set**: 35 different questions (`search_gold_heldout.json`, frozen at commit `549a377` before round 2 was written). Round 2 was run on it **once**, after the engine was final (`search_gold_results_heldout.json`; the runner refuses to overwrite that file, and every result file records the engine's commit and the SHA-256 of `search_service.py` and `search_stem.py`; the held-out result is stamped `29cba26`. One later commit, `a2bf305`, changed only the time the query-embedding call may take, 15 seconds to 8, and nothing in the ranking). Round 1 was then run on the same questions for the comparison only (`..._BEFORE_round2.json`); nothing was changed after seeing the held-out result.

"hit@5" = an expected section is among the first five sections returned. "Words" = meaning search off; "with meaning" = the real voyage-law-2 query vector (about Rs 0.0001 per search).

| | Round 1 words | Round 2 words | Round 1 with meaning | Round 2 with meaning |
|---|---|---|---|---|
| **Held-out (35), hit@5** | 25 (71%) | **31 (89%)** | 29 (83%) | **32 (91%)** |
| Held-out (35), hit@10 | 26 (74%) | 32 (91%) | 31 (89%) | 34 (97%) |
| Tuning (48), hit@5 | 32 (67%) | 38 (79%) | 38 (79%) | 45 (94%) |
| Tuning (48), hit@10 | 34 (71%) | 41 (85%) | 43 (90%) | 46 (96%) |

The gain holds on questions not used in the design (with meaning: +3 questions at rank 5 and +3 at rank 10 of 35; words only: +6 at rank 5). It is smaller on the held-out set than on the tuning set (with meaning, +7 of 48 at rank 5), which is the usual pattern when a design is shaped on one set; **the held-out figures are the ones to quote.**

What each part contributes (tuning set only; with meaning unless said):

| Variant | hit@5 | hit@10 | MRR |
|---|---|---|---|
| the engine as built | 45/48 | 46/48 | 0.831 |
| without meaning across the shelf Acts | 42/48 | 45/48 | 0.746 |
| words only | 38/48 | 41/48 | 0.650 |
| no stemmer (whole words only), with meaning | 43/48 | 45/48 | 0.725 |
| no stemmer, words only | 30/48 | 32/48 | 0.513 |

Sensitivity (tuning set; one setting changed at a time, the rest as built): the shelf floor 0.40 / 0.45 / 0.50 / 0.55 / 0.60 gives 45 / 45 / 45 / 44 / 44 of 48 at rank 5 (MRR 0.810 / 0.814 / 0.831 / 0.807 / 0.781); the cap per Act 1 / 2 / 3 / 5 gives 44 / 45 / 45 / 45; the library meaning list 20 / 40 / 80 and the fusion constant 10 / 30 / 60 / 100 change nothing (45 each). So the result does not hinge on a lucky setting; the floor 0.50 sits in the flat part.

### 2.3 What the numbers do not say

* **The questions and the expected sections are Claude's, not a lawyer's.** A label can be wrong: for "compensation to the victim of a crime" the expected section is BNSS 395 and the engine returns BNSS 396 (the victim compensation scheme) first, which may well be the better answer; the label was not changed after the freeze.
* **The sets are small** (48 and 35). One question is 2 to 3 points; a difference of one or two questions is noise.
* **hit@k says whether an expected section appears, not whether the rest of the list is useful.** There is no measure of precision, and none for the case search or the citation search (those are covered by the 334 deterministic checks of `test_search_service.py` and by reading, not by a rate).
* **The held-out questions were written by the author of the engine**, before the change, but they are still one person's idea of what a lawyer types. Real queries are not stored or logged by design, so the page cannot measure its own use; a lawyer's list of ten real searches would be worth more than another 35 of ours.
* Nothing here is a statement about the answers of the chat: no hallucination rate has been measured for the answer-writing step.

### 2.4 What still fails, and why (so that nobody is surprised)

* **BNS and BNSS sections have no heading in Recourse's stored text.** "Attempt to commit murder" (BNS 109 "Attempt to murder"), "right of private defence of the body" (BNS 35), "summons to appear in court" (BNSS 63, "Form of summons") are found only when the words happen to be in the section's own text or by meaning. This is the main thing missing for finding a section by its subject, and it is the **deferred BNS/BNSS repair** (FOLLOW_UPS 2ah item 5; the owner's "keep it for later", 2026-10-17): the repair would also be the natural place to take the headings from India Code. Not started.
* **An Act described but not named**: "bail under the unlawful activities law" does not reach the UAPA (the Directory knows the Act by its name and a few fixed phrases; the search page does not use the word pass of `ACT_DETECT`).
* **Terms of art that the statute never uses** ("anticipatory bail" for BNSS 482, "FIR" for BNSS 173, "instant triple talaq" for the Muslim Women Act): found by meaning or not at all.
* **Stemming is blind to meaning**: "bribe" and "bribery" are two stems; "bail" and "bailable" are two stems; "cognizable" and "cognisable" are two stems; "person" and "personal" are one. The cards say "Holds your words, or their usual forms" for that reason.
* **Near-duplicates compete**: around "arrest without warrant" BNSS 47, 55, 57 and 45 are all about arrest and rank above BNSS 35.

## 3. Checks that were run

| Check | Result |
|---|---|
| `test_search_stem.py` | 61 checks pass |
| `test_search_service.py` | 336 checks pass (offline; no Voyage call; the commit message of `29cba26` says 335 for the file as it was then, which had 334) |
| `test_api_search.py` | 56 checks pass |
| Full free suite of Recourse (`run_tests.py`, run on commit `29cba26`, the engine's last change) | 110 files run, 110 passed, 0 failed (includes `test_answer_export`, `test_api_export` and the other API tests) |
| `recourse-web`: `tsc --noEmit`, 73 vitest tests | clean, pass |
| `recourse-web`: 36 Playwright tests (33 desktop, 3 phone width; production build; the real API; a real throwaway PostgreSQL; a stand-in for Google's keys; a STUB answer engine; the real search engine with `ACT_SHELF=on`, `SEARCH_MEANING=off`; a stand-in wider-search service; the downloaded PDF and Word files read back) | 36 passed on the round-2 engine |
| Reflow of section text on the page (display only: the line breaks of the source's page width go, every word stays) | word-preserving over every stored BNS, BNSS, IT and NI section |

## 4. Not proven

* **Never run on Railway or against the real Google**, and never with a real model answer in the new screens.
* **No lawyer has read a search result.** The Acts' text on the shelf is `machine_checked`, not read by a person; the BNS/BNSS text is Recourse's own copy (99% identical to India Code on 2026-10-17; known losses in BNSS 183, 401, 480, 359 and the Schedules joined to section 531, shown beside the sections they affect).
* **No screen-reader or keyboard-only walk**; the automated accessibility checks (axe) pass on the three pages tested.
* The real `sci-search` service on Railway has not been called by the wider search (a stand-in was).
* The plan limits for `search` (free 100 a day) and `search_wider` (free 10 a day; anonymous 0) are provisional placeholders (decision D7).
* Legal text of the notices is placeholder (gate G1); accounts stay closed except on staging.
* **What a lawyer types leaves Recourse's servers** when the search by meaning is on (Voyage AI embeds the query; the wider search also calls `sci-search`). Recourse stores and logs the query nowhere (the tests check the database, the logs and the browser's storage), but the notice that a lawyer drafts (A4) must say that the words go to an outside provider. Both search boxes carry a line telling the reader not to type a client's name or any identifying detail. `SEARCH_MEANING=off` removes the transfer at the price of the meaning search (words only: 38/48 at rank 5 on the tuning set, against 45/48).
