# Case file and age card, 2026-11-09: what was measured and what was not

All questions and all expected sections are Claude's (not a lawyer's); the sets were written before the runs (`PREREGISTRATION.md`, `questions_age_card.py`). No model was run (no Anthropic key in the sandbox); retrieval is the real one (Voyage embeddings).

## 1. A follow-up searched on the new message plus the conversation's facts (`run_followups.py`, output `results_followups.json`)

Eight two-turn conversations, each run as staging ran the follow-up (NO: folded with the earlier message, searched on its own words, the rewrite dropped by the number guard) and with the case file (WITH: the facts as a search text, merged with the own-words search).

| conversation | expected sections | NO | WITH |
|---|---|---|---|
| molestation / recording | BNS 77, IT Act 66E | 0 | 1 |
| job cheating with forged letter | BNS 318, 336, 340 | 0 | 2 |
| hurt with an iron rod | BNS 115, 117, 118 | 2 | 2 |
| visa fraud | BNS 318 | 0 | 1 |
| dowry cruelty | BNS 85 | 0 | 1 |
| stalking | BNS 78 | 0 | 1 |
| bail (regression) | BNSS 478, 480 | 2 | 2 |
| arrest (regression) | BNSS 35 | 0 | 1 |
| **total** | 14 | **4** | **11** |

The pre-set rule (never fewer than NO where NO found any; more in total) held. Limits: eight conversations; the expected sections are mine; "present among the sections handed to the model" is not "the answer used it correctly"; the molestation follow-up still lacks IT Act 66E (the Act shelf needs the Act to be detected: that is the unbuilt "other charges" step, not this one). The offline harness cannot show the quality of the written answer.

## 2. The age card's trigger (`run_age_card.py`)

18 positives (cases that mention a sexual offence and give no age) and 23 negatives (definition questions, non-sexual cases, cases whose words already say the victim is a child, adult-context cases), 3 positives and 2 negatives declared hard in advance.

- Card shown for 15 of 18 positives. Missed: "a video of an intimate act was recorded and shared", "secretly filming a woman in a changing room" (declared hard), "forcing himself on a woman" (declared hard).
- Card wrongly shown for 2 of 23 negatives: "Can an FIR for rape be quashed on settlement?" (a general question that names an FIR) and "sexual abuse of a student of class 8" (declared hard: a child by context, no keyword).
- Not tuned afterwards: the word list is left as written; a change needs a new set. Both kinds of error are cheap (a missed card means no question is asked; a false card is one dismissible question).

## 3. Not measured

Whether the answer model writes a follow-up as well as a first answer; whether the delta answer after "Under 18" is short, correct or useful (it is a prompt clause, untried with the model); how many people tap "Under 18" wrongly; the cost of the delta answer (my estimate of Rs 3 to 5 is a guess). No lawyer has read any of it. No hallucination rate has been measured.

## 4. Answer shape, the BNSS First Schedule and the other-charges table (later the same day)

**Answer shape (`ANSWER_SHAPE`, default off).** The lawyers' note takes one heading per ask of the person's message, lifts its length for "detailed" (about 1,800 words) and shortens it for "briefly" (about 300), writes the Bottom line as three short labelled lines, and gets a code-built checklist "You asked for ... answered under heading N / the material does not show it / not found". Measured by code only: the length tier of 20 messages written before the first run is read as expected (20 of 20, `test_answer_shape.py`); the owner's follow-up is read as two asks (its "give me detailed explainations" is a style word); the prompt carries the block only for two or more asks or a length word, only for the lawyers' voice, only with the switch on, with the Hard rules block unchanged. **Not measured: whether the model follows the new instructions, or writes the three-line Bottom line without garbling it.** The checklist matches headings by number AND a shared content word, so a note that numbers its issues in its own way (the 9 Nov Q2 note) is shown as "not found" for the ask it did not take up.

**BNSS First Schedule, Part I (`schedules/bnss_schedule_I.json`, `build_bnss_schedule1.py`).** Read from the Gazette PDF the library already held (`raw_pdfs/bnss_2023_gazette.pdf`, pages 158 to 188), by the position of each word on the page (the table has no ruling lines). 438 rows, 287 distinct sections, every section a section of the library's BNS, no empty cell, rows in the Schedule's order, 0 rows whose cognizable and bailable columns hold different numbers of entries. Rows I read against the page text: BNS 64(1) rape (cognizable, non-bailable, Court of Session), 70(1) gang rape (same), 77 voyeurism (first conviction bailable, second non-bailable), 115(2) hurt (non-cognizable, bailable), 117(2), 238, 318(4), 336(3), 351(2). **One source, extracted by a program, not read by a person (`machine_extracted`); not checked against a second source (India Code was not tried: one of its hosts did not answer from the sandbox and the notes record an expired certificate since 2 Nov).** A section with several entries keeps all of them in order and the summary field is filled only where every entry agrees. Offences under other laws are not in Part I; Part II (three rows by punishment) is kept; the IT Act's own section 77B governs its offences. `OFFENCE_CLASS` (default off) hands the rows of the BNS offences among an answer's sections to the answer model as material.

**Other-charges table (`CHARGE_MAP`, default off; needs `CASE_FILE`; lawyers' conversations).** Ten patterns written by me from the BNS text (not read by a lawyer) plus a search by meaning that may add at most three BNS offences (a section with a Schedule row, so BNSS 358/234/244 can never stand in for a charge). Three sets of fact texts, each written before it was run (`questions_charge_map*.py`, `run_charge_map_set2.py`):
- set 1 (14 positives, 12 negatives), first run: 10 of 14 positives had every expected section, 1 of 12 negatives wrongly produced a candidate; the misses were word-list gaps ("intimate", "assault", "stood guard") and two declared-hard items;
- the word lists were then widened and an evidence-deleted pattern was given a crime-context word, using sets 1 and 2 (so those two sets are no longer fair): set 1 12 of 14 and 0 of 12, set 2 (written before the widening; first run 7 of 12 and 1 of 8) 12 of 12 and 0 of 8;
- **set 3, new and written before the widened lists were run on it: 8 of 10 positives complete, 0 of 8 negatives wrongly firing.** Its two misses: "sent it to a group chat" (no sharing word "sent") and "others assaulted her sexually" (not "rape" in the words).
All questions are Claude's. The table says it is not complete and has not been read by a lawyer. The model is asked to say, for each section, what it requires, which facts may match, what the prosecution would still have to show, the classification from the Schedule's line and the defence's points; **nothing of that was tried with the model**.

## 5. BNS 45 (abetment) added as its own candidate (owner's question after comparing with another tool's answer: "what about BNS 3(5), abetment (BNS 45)", then "also criminal conspiracy (BNS 61)")
What was already there: the pattern "a person present at a rape" handed over BNS 70 (gang rape), BNS 3 (the whole section; sub-section (5) is the common-intention rule, formerly IPC 34), BNS 61 (criminal conspiracy) and BNS 49 (the punishment of abetment). What was missing: abetment is DEFINED in BNS 45 (instigation, conspiracy, intentional aid) and the table named 45 only inside 49's reason text, so the definition itself never reached the model. Fix: BNS 45 is now its own candidate before 49 (`charge_map.PATTERNS["present_at_rape"]`); it has no Schedule row (it is a definition; the punishment is in 49), so none is invented. BNS 3(5) and 61 needed no change. The three sections resolve from the library (BNS 3: 4,744 characters, 45: 1,155, 49: 1,033, 61: 1,120).
Measured: `test_charge_map.py` 27 checks pass (two counts changed from 8 to 9 candidates, deliberately); the three question sets give the same numbers as before (set 1: 12 of 14 and 0 of 12; set 2: 12 of 12 and 0 of 8; set 3: 8 of 10 and 0 of 8), because none of their expected lists named 45; full suite 147 of 147. Limits: the pattern fires only when the facts say rape AND presence/helping; the same sections are NOT offered for other fact patterns (for example a conspiracy in a cheating case gets BNS 61, but abetment is not offered there); BNS 3(5) is "common intention", not "common object" (the unlawful-assembly concept in BNS 189 is different, and another tool's answer ran the two together). Nothing was tried with the answer model; no lawyer has read the table.
