# Retrieval misses: how often a relevant section never reaches the answer model, and three fixes (2026-11-03)

Owner, after the plain-terms answer on whether relevant BNS / BNSS / BSA sections are sometimes not shown: **"Yes, measure the misses and fix the common ones."**
Recourse branch `register-hooks-and-overlay` `5a0a88d` plus a small follow-up commit (labels only); NOT on Recourse `main`; every fix is behind a switch that is OFF by default; nothing is deployed; nothing has been tried with the answer model (no Anthropic key in the sandbox).

## In plain terms

* **Yes, relevant sections are sometimes not shown, and it is not rare.** Measured on questions I wrote (not a lawyer), with the answer model taken out and everything else real: for the BNS and BNSS about **1 expected section in 8 to 1 in 4 never reached the model** (12% on the 65 development questions, 27% on 48 new narrative questions, 13% on 35 more). For the law of evidence (the Bharatiya Sakshya Adhiniyam) the position was far worse: **when the question did not name the Act, 17 of 18 expected sections never arrived**; the site finds that Act only by its name.
* **What I built (all three default OFF; nothing changes on any site until you set them):**
  1. `STATUTE_WIDEN` — a section that is close but cut by the "within 0.08 of the best, at most five" rule is added back if a second, more careful scorer (Voyage re-ranker) rates it 0.55 or higher; at most two extra sections; on average 0.5 extra sections per question on the new questions, 1.1 to 1.4 on the short development questions.
  2. `STATUTE_ALIASES` — two sections whose wording shares nothing with how people ask: BNSS 528 ("quash an FIR"; the section is titled "Saving of inherent powers of the High Court") and BNSS 359 ("settle the case"; compounding). Only these two, because only these two were measured misses.
  3. `EVIDENCE_DETECT` — the evidence Act is recognised from its own topics (admissible, confession, dying declaration, burden of proof, hearsay, hostile witness, electronic record with a cue, secondary evidence and so on), without the Act being named. It works only when `ACT_DETECT` is `wide` or `ai`.
* **What it does for the numbers** (expected sections reaching the model, today → all three on): development sets 64/73 → 72/73; the 48 narrative questions 34/62 → 51/62; 16 fresh evidence questions 0/22 → 12/22; **35 questions never used to choose anything 34/39 → 35/39** (the library already did well there; widening recovered 1 of 5 misses). 
* **What it does not do:** it does not make a delivered section the right one; it does not find sections whose wording is far from the question (apart from the two aliases); on the fresh evidence questions the word pass named the Act for 10 of 16 and 6 were still missed; and even when the Act is found, the section picked by meaning is sometimes a neighbour (WhatsApp and CCTV evidence got BSA 62 and 90 but not 63). Every figure is on questions I wrote; the settings were partly chosen on the same questions that are scored, as marked below. **No hallucination rate has been measured.**

## Method (so it can be repeated)

* **Harness:** `run_e2e.py` runs Recourse's real `chat_assistant._answer_question_core` (scope check stubbed to "in scope", the answer model stubbed out, the wider search off). So retrieval (Voyage embeddings), the curated overrides, the explicit-section lookup, the offence-keyword anchors, the Act Directory + Act shelf (`ACT_SHELF=on`, `ACT_DETECT=wide`) and the library caps are all real; what is recorded is the list of material the prompt would carry. The Haiku pass of `ACT_DETECT=ai` is NOT run (no key): the owner's staging has it, so for questions that the word pass misses the real staging figure may be better than mine.
* **Question sets** (all written by Claude; the expected sections are chosen from the question alone and checked against the first line of the library's chunk, or the heading in `bsa_2023.json`; nothing was chosen from a retrieval result):
  | set | questions | expected sections | use |
  |---|---|---|---|
  | dev 1 (`../2026-10-31_relevance_gate/questions.py`) | 29 | 30 (BNS, BNSS) | development |
  | dev 2 (`../2026-11-03_relevance_neighbours/questions_fresh.py`) | 36 | 43 | development |
  | frozen (`questions_frozen.py`, committed `3f06bf8` before any retrieval) | 48 | 62 (BNS 20, BNSS 21, BSA 21) | baseline measured first; **then used to choose the widening floor (0.60 → 0.55), so it is a development set for that one number**; the BSA word pass was written before its result was seen |
  | evidence 2 (`questions_evidence2.py`, committed `9716fc6` before it was run) | 16 (+ 8 negatives) | 22 (BSA) | unseen for the word pass |
  | set 3 (`questions_set3.py`, committed `50a673b` before it was run) | 35 | 39 (BNS 20, BNSS 19) | unseen for the widening floor and the aliases |
  | negatives (`questions_negative.py` 14, evidence 2 `NEG2` 8) | 22 | — | the word pass must stay quiet |
* **Diagnostics:** `diagnose.py` (cosine rank and re-ranker score of every statute section for every question), `simulate.py` (offline policies), `summary.py` → `summary_output.txt`, `misses_after_fixes.txt`. Retrieval scripts must be run from `/home/user/recourse`.

## Results

`summary_output.txt` (generated):

| set | today | all three on |
|---|---|---|
| dev 1 (29 q) | 28/30 93% | 30/30 100% |
| dev 2 (36 q) | 36/43 84% | 42/43 98% |
| frozen (48 q) | 34/62 55% | 51/62 82% (BNS 15→18 of 20; BNSS 15→16 of 21; BSA 4→17 of 21) |
| evidence 2 (16 q) | 0/22 0% | 12/22 55% |
| set 3 (35 q) | 34/39 87% | 35/39 90% |

* **The BSA gap was the biggest by far.** On the frozen set, evidence questions that named the Act: 4 of 4 sections arrived; evidence questions that did not: 1 of 18 (that one was BNS 80, from the dowry-death flow). `EVIDENCE_COMPANIONS=on` changed nothing (it covers circumstantial evidence only). With the word pass: 14 of 18.
* **Two kinds of miss for the BNS / BNSS:** *near misses* (the section was 3rd to 7th by similarity and cut by the 0.08 gap or the cap of five: on the 65 development questions 6 of 9 misses; on the frozen set 9 of 11 were within the first 15) and *far misses* (the question's words share nothing with the section: BNSS 528 ranked 83rd and 119th, BNSS 359 38th). Widening can only help the first kind; the aliases are a hand patch for the second kind.
* **Widening (`STATUTE_WIDEN`), pool 10, at most 2, floor 0.55:** development sets alone, every floor from 0.50 to 0.60 recovered the same 5 of 9 misses; on the frozen narrative questions the cross-encoder scores lower, 0.60 recovered 2 of 11, 0.55 recovered 4, 0.50 no more; so 0.55. **Unseen (set 3): 1 of 5 misses recovered** (BNS 221). Average extra sections per question: 0.49 on set 3, 0.56 on the frozen set, 1.1 and 1.4 on the two development sets (short questions get more). Pooled over dev + frozen (98 questions with a BNS/BNSS section): 94/114 → 103/114 offline.
* **Aliases:** BNSS 528 and 359 arrive for the 3 development questions that missed them, and for none of the other 161 questions. They were written *because* of those misses, so this shows only that they fire; the frozen and set-3 questions contain no question about quashing or compounding. Unit tests cover 13 phrasings that should fire and 14 that should not (compound wall, squash court, "cancel the bail", …). The existing judgment wiring already gave Bhajan Lal for FIR quashing; BNSS 528 itself did not arrive before.
* **Evidence word pass:** names the Act for 12 of 12 frozen evidence questions (written by the same author as the patterns, so optimistic) and **10 of 16 fresh ones** (the realistic figure). Missed: admission by a party (BSA 16/25), judicial notice (51/52), a blind or deaf witness (124/125), a lawyer's duty of confidence (132/134), an entry in an account book (28), and the weapon recovered after the accused pointed it out (23). False alarms: **1 of 154 non-evidence questions** ("Can a magistrate record a confession from the accused during the investigation, and how?" — arguably an evidence question too, and BNSS 183 is the right section for it).
* **Remaining misses with everything on** (`misses_after_fixes.txt`): mostly the *other* acceptable section when one of two was delivered (BNSS 289 beside 290, 413 beside 415, 446 beside 447, 106/94 beside 105/185/49); BNS 109 (attempt to murder; the search gives 110, attempt to commit culpable homicide, and 130), BNS 61 / 105 / 45 / 270 on set 3; BSA sections picked by meaning after the Act was found (BSA 63 for electronic records, 157/148 for a hostile witness). One label I now doubt: BNSS 63 in dev 2 is "Form of summons"; the question was about *service* and the sections 64 to 70 that arrive are the service sections, so that "miss" is probably a wrong label of mine.

## What these fixes can do wrong (for the owner's staging test)

* **More material, not necessarily better answers.** Widening adds up to two sections per question that a scorer thinks relevant; a neighbour in the same chapter can pass (BNS 192, 193, 195 beside 191). The risk is the filler problem of 2026-10-31 in a milder form. `STATUTE_WIDEN=log` first: it writes a `STATUTE_WIDEN` line with what it would add and changes nothing.
* **The evidence word pass changes what the page says**: a detected Act brings the Act notice ("looks like it is about the Bharatiya Sakshya Adhiniyam") and the shelf's meaning search picks up to five sections of it. For a long Act whose text reached the answer the notice is the shorter one.
* **Nothing here reads or checks the Act texts**: the BSA text is `machine_checked`, nobody has read it. The aliases and the word-pass patterns are my wording, not a lawyer's.
* **Cost:** one extra re-rank call per question (a few thousand tokens; [Likely] a few paise, not measured: the `COST_QUESTION` line of the staging test will show it); the word pass is free; the aliases are free.
* **Not tried with the answer model.** Whether the extra sections improve or worsen the answers is exactly what only the staging test (and a lawyer's reading) can show.

## Not done (and why)

* The shelf's own section choice by meaning (BSA 63 and 157 missed after the Act was found); a re-ranker pass there would be the same idea as widening, but it needs its own held-out set.
* More evidence patterns for the 6 fresh misses: I would be tuning on a set that is then no longer unseen; better to see what `ACT_DETECT=ai` does on staging first.
* A general lay-to-legal dictionary: only two entries were measured misses.
* The BNS/BNSS text repair (deferred by the owner; not touched).
