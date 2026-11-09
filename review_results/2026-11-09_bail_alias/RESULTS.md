# Bail sections for "arrested me" questions: what was measured (2026-11-09)

Owner: "Build the bail sections for 'arrested me' questions". Recourse `fb153ee` + test fix (branch `register-hooks-and-overlay`, NOT on `main`); switch `STATUTE_ALIASES` (default OFF), the same switch as the harbouring and the two older entries. All questions are Claude's, not a lawyer's. Harness: `review_results/2026-11-03_retrieval_misses/run_e2e.py`, config `fixes` (real retrieval, model stubbed out).

## Baseline (no entry): the library search did NOT bring the bail sections
| 30 questions where someone has been arrested or is in custody | baseline | with the entries | rule |
|---|---|---|---|
| BNSS 478 and 480 both reach the prompt | **4** | **30** | >= 27 |
| BNSS 478 alone / 480 alone | 10 / 4 | 30 / 30 | |
| 8 questions where bail was refused: BNSS 483 | **4** | **8** | >= 7 |
| 30 questions where nobody is arrested or in custody: an entry fires | n/a | **1** | <= 2 |
(The baseline rule "build only if the search does not already bring them (fewer than 27 of 30)" was met: 4 of 30.)
The one negative that fired: "How long can a person be kept in custody before being produced before a magistrate?" (a general question that says "kept in custody").

## Earlier question sets (325 questions run through the word groups alone)
20 fire. Read one by one: most are about someone being arrested (correct trigger). Two are clearly NOT about an arrest: "The police took my phone and laptop during their investigation ..." ("police took my phone" is read as an arrest by the group as written) and "Who is responsible for the health and safety of an accused while he is in custody?". Several more mention an arrest but are not about release (the hotel owner whose guest was arrested; the friend whose phone was seized after his arrest): the entry adds the two sections anyway. These are left as written (not tuned on seen questions) and listed as known limits.

## Cost of a fire
BNSS 478 is 1,506 characters, 480 is 4,649 and 483 is 1,623: about 6,200 characters (roughly 1,500 tokens) are added to the prompt of every question that mentions an arrest, about 7,800 when bail was also refused. Money not measured.

## What this does not show
Whether the answer model now discusses bail well, or wrongly pads an answer about something else with bail (no Anthropic key; the owner's staging test is `DEPLOY_STAGING.md` Part 4az). Whether a lawyer would pick 478 and 480 (and 483 only after a refusal) for each of these questions. Anticipatory bail (BNSS 482) is NOT part of this: a person who fears arrest but has not been arrested gets no entry. No hallucination rate has been measured.
