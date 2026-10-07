# Plan: using the overruled-cases list and the checker on the live Recourse website (stored 2026-10-07 at the owner's request)

**Source label: a plan, not built. Nothing here is connected to the live site. The Recourse repository is read-only for this project; every site-side change below is a patch for its owner.**

## Starting facts (as the owner stated them)

- The 1,688-entry "List of Overruled Cases" PDF (`inbox/520254941-List-of-Overruled-Cases.pdf`) was **verified as fully correct by a lawyer** (the owner's statement; name and date of the verification are still to be recorded by the owner). It ends around 2015, so "correct" means correct as of about 2015, not complete.
- With the list verified, the checker's 29% (42 of 146 tuning pairs, rules only) is a **real catch rate on verified overrulings**: the checker misses about 7 in 10. So the list/register is the **primary safeguard** and the checker is the **secondary net**.
- None of the site's 76 library cases and none of its 103 Vaquill judgments is on the list (as overruled), so on today's site data the register would flag nothing; its value is for older authorities pulled from the big index, recalled by the model from memory, or pasted by users.
- The live app (`recourse_app.py`, Railway) already shows currency caveats from a hand-curated map (`citation_currency.py`, 14 entries: 10 GOOD_LAW, 4 SUPERSEDED_BY_STATUTE). Its rule: code never decides good law; only curated, human-verified records may say OVERRULED.

## Part 1. How overruled cases get cited as overruled in future answers

1. **Overruled Register** built from the verified list, 1,688 rows (492 Supreme Court overruled by Supreme Court; 1,196 High Court or tribunal decisions overruled by the Supreme Court, which the checker could never check). Each row: both citations and years, "overruled by", compiled-as-of date (about 2015), verifier name and date (to be filled by the owner, never invented).
2. **Three locks in every answer.** (a) Before the model writes: overruled cases are never offered as authority; their passages are demoted and badged; the overruling case is retrieved instead. (b) While it writes: the prompt carries a fixed fact, "A was overruled by B (year); never state A's holding as current law; mention A only as overruled by B". (c) After it writes: plain code scans the final answer for any register case, including ones the model recalled from memory; if one appears without "overruled", it adds a standard clause and a badge. Lock (c) matters most.
3. **Match on citation, year and full party names, never a bare name.** "Mohan Lal" appears in 8 list rows and none is the 2018 Mohan Lal v State of Punjab.
4. **Wording:** "X (overruled by Y, 2004)", or "... in part", with an "as of" date. If the overruling case was itself later overruled or overcome (Naz Foundation to Koushal to Navtej Johar; Dashrath Rupsingh Rathod and the 2015 NI Act amendment), the answer says so and the row goes to the lawyer for re-reading.
5. **Trap-question exam:** about 50 questions built from register rows where the classic answer comes from the overruled case; run the assistant with and without the locks; pass = zero answers that state an overruled rule as current law; a lawyer reads a sample of 20 answers.
6. **For the lawyer:** one short question on about 27 ambiguous rows (6 pairs listed as overruled by each other = 12 rows, 14 pairs with overruling-before-overruled dates, row 75 with an empty cell); and whether a facts-only register built from the list may be used in a product (the website that publishes the same list, referencer.in, reserves its copyright).

## Part 2. Tracking each judgment in future

- **Judgment ledger:** one row per judgment: names, citations, court, date, bench; status; who or what set it (register, lawyer, checker) and when; evidence (the court's own sentence); next review date; append-only history. Statuses: overruled (register), overruled in part (lawyer-confirmed), flagged (unreviewed), cleared by a human on a date, nothing found (weak), not checkable.
- **Who is tracked, how often:** everything the site can cite (46 core, 16 pilot, 103 Vaquill, anything the index returns, register-linked cases): full check monthly. All ~10,500 indexed criminal-law judgments: light monthly scan. All ~46,000: quarterly or when named.
- **Monthly watch** (a cloud routine on the data branch, triggered by the planned monthly refresh): add new judgments; scan each for adverse sentences naming any tracked case; an explicit "overrules X" becomes a proposed register row needing the lawyer's confirmation; weaker signals become flags; cases whose overruling case was itself attacked are re-checked; a change report goes to the review queue. A whole-collection sweep for adverse-cue sentences costs about 29 minutes on one core.
- Every status shows its "as of" date; the collection's gaps (about 20% of 1990-2009 and a quarter of 2018-2025 missing) are stated.

## Part 3. The checker's other adverse findings (not on the list)

They are **warnings, never facts**. The checker never says "overruled" in its own voice; only the register or a human confirmation can.

| Checker result | What the answer does | What happens next |
|---|---|---|
| Strong flag (e.g. Mhetre; Mohan Lal's reach) | Must carry a clause: "later judgments appear to overrule this in whole or part", with quote and year; ranked lower | Human review within a set number of days; confirmed, it moves to the register ("overruled"); cleared, it is logged with a date; never auto-cleared |
| Questioned | One neutral clause, quote on click; no demotion | Monthly review queue |
| Nothing found | No currency claim, never "good law"; coverage note only | Weak evidence: low review priority |
| Cannot check / too few later judgments | "Not checked by us" | Indian Kanoon spot check only for thin cases, keeping at least Rs 200 reserved |

Raise the catch rate before relying on flags: the second reader (a model reading passages) on flagged items and weak-cue sentences; wording for courteous disapproval ("may not be correct", "to that extent": the gap that hides Krishna Janardhan Bhat); measure once on the untouched odd half of the list (162 pairs), now a verified exam.

## Order and gates

| When | What | Gate |
|---|---|---|
| Week 1 | Lawyer answers the ~27-row question and the facts-only question | Verification name and date recorded |
| Weeks 1-2 | Register file, lookup code, tests; run against all the site's pools | Every known overruled case in the register is found |
| Weeks 2-4 | Answer-guard patch for the Recourse owner; trap-question exam | Zero trap failures; lawyer reads 20 answers |
| Weeks 3-6 | Ledger, monthly routine, review queue | A real monthly change report |
| Weeks 4-8 | Sweep, second reader, new wording; one run on the odd half | Catch rate measured against verified overrulings |

## Decisions still needed from the owner

1. Who is the lawyer reviewer, and the verification date to record?
2. Go to build the register and tests? (Site-side changes are patches for the Recourse owner.)
3. Who reviews flags, and within how many days?

## Added later the same day

A second PDF, "Judgments Overruled After 2015 - Research List" (6 pages, 59 entries, an AI-style research compilation with its own corrective note, cut-off 7 October 2026), was supplied by the owner for checking. It is **not** treated as verified. My check against the judgments in our collection (`external_lists/2026-10-07_overruled_after_2015_pdf/`): 41 confirmed as stated, 11 confirmed but incomplete, 4 with a label stronger than the court's words, 2 wrong in a material detail, 1 not checkable. It is incomplete (60 further candidate judgments found, unchecked), cuts chains (the 2023 N.N. Global ruling was itself overruled in December 2023), and mixes decision and reporter years. **Effect on this plan:** a register row must carry the court's own words, the treatment type (overruled / in part / not good law / per incuriam / not binding), bench size and split, decision date and every later step that touched the overruling case; rows from this list enter only as candidates until a lawyer confirms them.

## Status 2026-10-07 (evening): the register is built

The owner answered the decisions: reviewer Mr. Advocate, verification date 2026-10-07 (recorded for list 1), build the register and tests including the post-2015 list, flags reviewed every 7 days, the re-read idea later. Built: `REGISTER.md` (the register, its trust tiers, the three locks as code, the weekly review, the trap exam), `REGISTER_SITE_PATCH.md` (the patch for the Recourse owner, not applied), `register-export-site` (the bundle). **Still not connected to the live site; the trap exam is not run; no row has been reviewed yet.** The plan's gates: week 1-2 (register, lookup, tests, run against the site's pools) done; weeks 2-4 (answer-guard patch, trap exam, lawyer reads 20 answers) patch written, exam built and not run; weeks 3-6 (ledger, monthly routine, review queue) ledger and queue built, no routine scheduled; weeks 4-8 (sweep, second reader, new wording, odd half) sweep built, the rest not started.

## Owner's instruction, 2026-10-07 (to bring back when the site is connected)

The owner will apply `REGISTER_SITE_PATCH.md` to Recourse himself. When the index, the checker and the search phases are connected to the main site, Claude is to **export the checker's cards as a small overlay for the site, extended to every case the site can cite**, and add a fixed "not checked by us" wording for any case with neither a register row nor a card. Full spec and prerequisites: `FOLLOW_UPS.md` item 0.
