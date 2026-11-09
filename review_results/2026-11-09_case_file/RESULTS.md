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
