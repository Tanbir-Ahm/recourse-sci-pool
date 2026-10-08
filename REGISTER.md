# The Overruled Register

Built 2026-10-07 on the owner's instruction. Code: `goodlaw/register.py` (facts, matching, wording), `register_guard.py` (the three locks), `register_build.py` (from the two outside lists), `register_review.py` (the weekly review), `register_sweep.py` (finds the register does not hold yet), `register_exam.py` (trap-question exam). Data: `goodlaw/data/register/` (`register.json`, `flags.json`, `proposals.json`, `list2_enrich.json`). Tests: `test_goodlaw_register.py`. For the Recourse site: `REGISTER_SITE_PATCH.md`.

**What it is.** A list of decisions that a later court has overruled, reversed or disapproved, kept as facts with their evidence, their trust level and a history. It answers one question: *has the Supreme Court said this decision is overruled?*, for a case named in a question, in a retrieved passage or in a finished answer. **What it is not:** a verdict of the code. The code only looks up and words what a row says. The checker (`goodlaw/report.py`) still only warns.

## What the row IDs mean

| Prefix | Meaning | How many |
|---|---|---|
| `L1-nnnn` | the row number in the 1,688-entry list (list 1, to about 2015): `L1-0006` is row 6 | 1,688 |
| `L2-nnn` | the entry number in the 59-entry post-2015 list (list 2): `L2-004` is entry 4 | 59 |
| `D2-NAME` | "derived from list 2": a decision the same post-2015 judgments overruled but that list 2 leaves out, found by Claude while checking list 2 (for example `D2-KADER`, `D2-PRABHULAL-2017`; the year is added where the same case was overruled more than once). The label is Claude's own naming and was not written down before 2026-10-08 | 18 |
| `RC-nnn`, `RS-nnn` | rows created only when a reviewer accepts a checker flag (`RC`) or a sweep proposal (`RS`) | none yet |
| `F-...`, `P-nnnn` | a checker flag, a sweep proposal (these are not register rows) | 2, 329 |

## What is in it (1,765 rows)

| Source | Rows | Trust | Wording in an answer |
|---|---|---|---|
| List 1: the 1,688-entry "List of Overruled Cases" (ends about 2015) | 1,688 | **verified** - Mr. Advocate, 2026-10-07 | firm: "X was overruled by Y (year)" |
| List 2: the post-2015 list, checked by Claude against the judgments | 58 | **candidate** | hedged: "X is reported as overruled by Y (year) (not yet confirmed by our reviewer)" |
| List 2, row 43 (the later judgment is not in our text) | 1 | **unchecked** | none; goes to the review queue |
| Sibling decisions found in the same judgments (Bhanudas Krishna Gawde, the six India Cement companions, Raj Kumar Karwal, ...) | 18 | **candidate** | hedged |
| A row a person confirms or a flag/proposal a person accepts | 0 so far | **reviewer_confirmed** | firm |
| A candidate a person rejects | 0 so far | **rejected** (kept, never worded) | none |

- **The verification of list 1 is recorded from the owner's statement** on 2026-10-07 (reviewer Mr. Advocate, verification date that day). Claude did not see the verification. List 1 ends about 2015: correct as of then, not complete. **List 2 is not marked verified.** Mr. Advocate is assigned as its reviewer; nothing is verified until a confirmation is recorded in the weekly review.
- **Treatments are the court's words, not one flag:** overruled, overruled_in_part, not_good_law, per_incuriam, not_binding, not_approved, reversed_on_appeal (a High Court decision reversed in the same dispute: 507 rows of list 1, decided by comparing the parties' names, a heuristic), disputed_listing (13 rows where the list itself is inconsistent: each case listed as overruled by the other, or no overruling decision named).
- Every row keeps: both decisions' names, citations and years, the bench and date of the overruling decision (list 2), the court's own words (list 2), the evidence kind, who verified it and when, and an append-only history.
- List 1 carries only facts (names, citations, years, the row number in the list). **Licence: not cleared.** The same list is on www.referencer.in, which reserves its copyright; whether a facts-only register may be used in a product is still a question for the lawyer. If the answer is no, drop the `list1` rows (`source` is on every row) and rebuild.

## How a decision is recognised (never by a bare name)

1. **A reported citation on the row** (SCC, SCR, AIR, JT, SCALE, INSC; High Court AIR). An SCR page without a volume ("1966 SCR 209") matches the same page; two different volumes' page 332 do not match each other.
2. **Both party names, in the row's order, and a year within one of the row's years** (reporter year and decision year differ by one). Dotted initials ("A.D.M.", "K.L."), "U.P." / "Uttar Pradesh" and alternative spellings (stored on the row) are read the same.
3. Both names without a year is a **weak** match: listed for a person, never worded as a fact. A first party alone ("Mohan Lal") is ignored. A name pair made only of common words ("Sekar v. State") is found by citation only.

Measured on the real register: 1,655 of 1,765 rows are recognised strongly (1,615 by name and year, 40 by citation only); 68 weakly and 42 not at all - those 110 carry the flag `needs_citation_or_year` and come up in the weekly review (the list gives them no citation or year). Scanning the title and year of every judgment in the collection (45,186) gives 477 strong hits on 459 rows and no collision (the nine low-similarity ones are the same cases under another spelling). The 76 library cases give 2 hits, **Mohan Lal and Mhetre**, the two the checker also flags; both are candidate rows. The 103 Vaquill judgments give 1 weak hit (Sunita Devi v. State of Bihar, 2024, against the 2005 Sunita Devi of list 2): a different case, and it was not worded.

## Chains

When the overruling decision B is itself the overruled decision of another row, the wording says so ("B was itself later overruled by C; the current position should be checked"). 85 rows have a chain, 83 of them in list 1: for example K.L. Verma (overruled by Adri Dharan Das, which Sushila Aggarwal 2020 overruled), State of U.P. v. Synthetics (1980) and Ram Lal Narang, H.R.S. Murthy, the Delhi High Court's Naz Foundation, and N.N. Global. A chain row stays as listed and goes to the weekly review ("does the recorded status still stand?"); nothing is carried forward silently.

## The three locks (`register_guard.py`)

| Lock | When | Function | Effect |
|---|---|---|---|
| a | before the model writes | `retrieval_flags(reg, chunks)` | a retrieved passage whose own case is a firm row is demoted and badged; a candidate row only badged; a case merely named in the text is noted |
| b | while it writes | `prompt_facts(reg, texts)` | lines for the prompt: "REGISTER FACT: X was overruled by Y (year). Do not state its holding as current law..." (a candidate gives "REGISTER NOTE (not yet confirmed)") |
| c | after it wrote | `guard_answer(reg, answer)` | scans the finished answer, including cases the model recalled from memory; for every register case that appears without a word of overruling next to it, returns a standard note and a badge flag; weak matches are listed for review. It needs no cooperation from the model |

A word of overruling counts as the answer saying it only when it belongs to the mention: after it in the same sentence, at the start of a next sentence that refers back ("It was later overruled"), or directly before it ("In overruling X"). "X was overruled by Y" acknowledges X, not Y; a neighbouring case's overruling does not count. The Recourse site is read-only for this project, so nothing here is connected to it: the patch for its owner is `REGISTER_SITE_PATCH.md`, and `python sci_goodlaw.py register-export-site --out DIR` writes the dependency-free bundle (three modules and a 789 KB slim register).

## The weekly review (every 7 days)

`python sci_goodlaw.py register-review-queue --out review_queue.csv` writes the week's sheet; the reviewer fills `decision` (and the extra columns the sheet asks for); `python sci_goodlaw.py register-review --sheet review_queue.csv --reviewer "Mr. Advocate"` records it. An item left undecided, or marked `keep`, returns seven days later. The sheet holds, most important first: **flags** (the checker's ADVERSE_SIGNAL / QUESTIONED cards, kept in `flags.json`), **candidate** and **unchecked** rows, **chain** rows, the sweep's **proposals** (at most 20 a week), **listing** rows (list 1's own inconsistencies) and **match** rows (at most 20 a week); the sheet is capped at 60 items, flags never cut.

Rules that do not bend: the checker's flags and the sweep's proposals enter the register only when a person confirms them; a flag the checker stops raising stays open until a person clears it; nothing is deleted (a rejected row stays, marked rejected); a verified row is never rejected in the sheet (use `change`); `register-build` refuses to overwrite a register a person has reviewed. The owner gave the cadence (7 days) but did not say who reviews flags: Mr. Advocate is assumed.

Today's flags: Mohan Lal v. State of Punjab (2018) and Siddharam Satlingappa Mhetre v. State of Maharashtra (2011), both open, both already candidate rows (overruled by Mukesh Singh 2020; overruled in part by Sushila Aggarwal 2020).

Commands: `register-flags` (take the checker's cards into the ledger after each `cards` run), `register-sweep --corpus corpus.sqlite` (about a minute and a half since the default window was widened on 2026-10-08 from 2016 to 2000: finds later judgments of three or more judges that say an earlier decision is overruled, from the law report's own tags and from the court's sentences; proposals only), `register-check "Name v Name" --year Y --cite C` (what the register says about one case), `register-scan --file answer.txt` (the guard on a finished answer).

## The weekly routine (created 2026-10-08)

A scheduled cloud session runs `REGISTER_ROUTINE_RUNBOOK.md` every Thursday morning (India time): it writes `register_review/DATE/` (the week's sheet as CSV and Excel, and a short `SUMMARY.md`) on the branch `claude/sharp-euler-unyfv0`. It is read-only on the register. The sweep is not part of it (it needs the 1.8 GB corpus store).

**The loop:** (1) Thursday: the sheet appears. (2) Mr. Advocate fills the yellow columns of `Review_Sheet_DATE.xlsx` (decision, and new_treatment / scope / overruling_case / overruling_year / overruled_cites / overruled_year / note where the decision asks for it). (3) The owner sends the filled file to a Claude session. (4) The session records it: `python sci_goodlaw.py register-review --sheet FILE.xlsx --reviewer "Mr. Advocate"`, runs the tests and commits. Items left blank or kept return seven days later. The first sheet (2026-10-08) holds 60 of a backlog of 504 items: about 9 weeks at 60 a week.

**Run log:** every run adds a line to `register_review/RUN_LOG.md`, so a week without a line means the routine did not run, and every run has something to commit and push.
**How it is wired:** on 2026-10-08 the owner also created a stand-alone routine in the Claude app ("Register weekly review sheet", Thursday 9:35 India time, repository attached, Default environment; its first manual test ran end to end except the push). Its first test pushed successfully (16:24 UTC, 2026-10-08), so the session-bound routine (trigger `trig_01RvfxUFMQWUN9bFGKsmgUBc`) was DISABLED the same evening; it had been Thursday 08:49 India time, first scheduled run 2026-10-15) sends the run instruction into the working session `session_01YEUNXbYb9LDbJLc2ziqL3n`, which has this repository checked out. A fresh-session routine could not be created with Claude's tools (a routine made that way gets no repository); if you want one that does not depend on the working session, create it in the Claude app with this repository attached and paste the prompt from `REGISTER_ROUTINE_RUNBOOK.md` step 0 onward.
**How to stop it:** in the Claude app open Routines (scheduled tasks), find "Register weekly review sheet" and pause or delete it; or ask a Claude session to run `update_trigger` with enabled false. If the working session is archived, the weekly sheet stops.

**Full workbook for checking:** `python sci_goodlaw.py register-export-xlsx --out FILE.xlsx` writes every row (1,765), every finding, the post-2015 sheets, the sweep proposals, the review backlog, the checker's cards and the known cases (the 2026-10-08 copy is `register_review/2026-10-08/Overruled_Register_Full_Review.xlsx`). The summary's formulas are computed by Excel when the file is opened.

## Tests and the trap-question exam

`python test_goodlaw_register.py`: unit tests (matching, wording, chains, the guard, the review decisions, the sweep's parsing, the build) and gates on the real register (every recognisable row is found by its own name and year; the 76 library cases hit only the two known flags; a bare name is nothing; a wrong year is weak; the bundle works on its own). All pass.

`register_exam/questions.jsonl` has 50 trap questions (36 from list 1 spread over the decades, 10 from list 2, 4 chain rows) and `key.json` its key. **It has not been run: it needs the live assistant.** Run the assistant on each question with the locks off and with them on, store `{"id","answer"}` per line, and score each file with `python sci_goodlaw.py register-exam score --answers FILE`. The scorer counts answers that acknowledge the overruling, answers the guard would have caught, answers that name the case in a form the register cannot recognise (a gap: the run fails) and answers that do not cite the case. Pass mark: no unrecognised mention, and a lawyer reads 20 answers.

## Limits (read before relying on it)

- List 1 stops about 2015 and was compiled by an unknown author; list 2 is incomplete (a sweep of the 1,514 judgments of three or more judges since 2016 found 127 further case-by-case proposals from the law reports' own tags and 63 from the courts' sentences, unreviewed and not yet read by anyone: `proposals.json`). **The sweep was widened to 2000 on 2026-10-08** (3,406 judgments of three or more judges): 42 further proposals (41 from sentences, 1 from a tag), 232 open in all, none read by anyone. **Its recall on two known cases is nil:** it finds neither Prabha Shankar Dubey (rejected by the Jadeja Constitution Bench in 2010) nor Krishna Janardhan Bhat (Rangappa, 2010: its observations 'may not be correct'), because those courts did not write 'overruled' or 'not good law' (Jadeja: the view 'is neither borne out from the language of sub-section (1) of Section 50 nor ... in consonance with ... Baldev Singh'). The sweep sees explicit overruling wording only. A court that disapproves in other words is invisible to it, so a lawyer's list of such cases (the currency-trap questions) is the only way in; widening the wording needs a precision test on a labelled sample first, or it floods the weekly sheet.
- 110 list-1 rows cannot be recognised without a citation or year (the list gives none); they are weak or invisible to the guard until the reviewer supplies them.
- The register only knows decisions overruled by a later Supreme Court decision. It does not know a statute that overrides a decision, a High Court decision overruled by a High Court, or a decision merely distinguished or doubted.
- A citation names a reported page; AIR pages hold more than one report, so a wrong citation in an answer could point at another row. The guard prints the mention it matched.
- The acknowledgement test is a heuristic on wording; it does not read the answer's meaning. A case described without naming it ("the 2018 informant-investigator ruling") is invisible to it.
- 507 rows are marked `reversed_on_appeal` by comparing the parties' names (Jaccard 0.5): a heuristic, not read row by row.
