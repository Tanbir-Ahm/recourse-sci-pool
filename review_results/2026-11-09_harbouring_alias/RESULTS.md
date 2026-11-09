# Harbouring alias (BNS 249, 253, 254): what was measured (2026-11-09)

Owner: "Build step 1, the harbouring alias, measured first. And lawyer mode was used." Recourse `8d27089` (branch `register-hooks-and-overlay`, NOT on `main`); switch `STATUTE_ALIASES` (default OFF). All questions are Claude's, not a lawyer's. The harness is `review_results/2026-11-03_retrieval_misses/run_e2e.py` (config `fixes`: real retrieval, model stubbed out): it records which sections and judgments would reach the answer model.

## The finding that changes the picture
Before any alias, the library search already brought the section for **20 of 24** harbouring questions (249), **8 of 8** (253) and **4 of 4** (254). The owner's answer missed BNS 249 because his question described the help as "a lift" and never used a word such as harbour, hide or shelter. So the real gap is the phrasing without those words, not harbouring in general.

## Set 1 (pre-registered before any run; `questions_harbour.py`, `PREREGISTRATION.md`)
| | no alias | v1 (as pre-registered) | v2 (informed by set 1's misses) |
|---|---|---|---|
| BNS 249 reaches the prompt (24 questions) | 20 | **21** (rule: 22 -> FAILED) | 24 (not a fair test) |
| BNS 253 (8) | 8 | 8 | 8 |
| BNS 254 (4) | 4 | 4 | 4 |
| negatives where an alias fires (40) | n/a | 0 | 0 |
| the owner's own question (seen) | 249 absent | **249 present** | present |
The three set-1 questions v1 still missed: "I drove an absconding accused to the bus stand", "had been staying at my guest house", "took the prime accused to another town" (the driver) -- plus one more fixed by v1 (a room let to a wanted man, via the word "harbouring").

## Set 2 (NEW, written after v1's result and before v2 was run; `questions_harbour_v2.py`, `PREREGISTRATION_V2.md`)
| BNS 249 reaches the prompt (16 transport / stay / rent questions) | no alias | v1 | **v2** (rule >= 12) |
|---|---|---|---|
| | 7 | 8 | **14** |
Negatives (30): v1 0 fires; **v2 3 fires** (rule <= 3, reached exactly): the police taking an absconder to the station after years; accompanying a wanted cousin to court to surrender; taking him to the police station to surrender. All three were declared as traps in advance; they are false fires (the section is handed over for a question that is not about harbouring).
v2's two misses: "dropped an absconding accused at his sister's house", "carried the wanted man across the border".
The 202 questions of the earlier question sets (not about harbouring): **0 fires**. Unit tests: 42 checks (`test_harbour_alias.py`), Recourse suite 138 of 138.

## Known limits of the groups as written (not tuned; a change needs a NEW measured set)
A person named with his/her/their, "the wanted man", "the absconding accused" and "dropped him at" are not read as the object; the alias fires on police transporting an absconder and on accompanying a wanted person to surrender; knowledge ("knows or has reason to believe") is a matter for the answer, the alias only puts the section in front of the model.

## What this does not show
Whether the answer model now frames the owner's question as harbouring rather than abetment (BNS 45 still reaches the prompt); whether a lawyer agrees these are the right sections; real users' phrasing. The owner's staging test is `DEPLOY_STAGING.md` Part 4ay. Lawyer mode was used for the 8 Nov answer, so "For the client" and the absence of steps are by design, not a bug. No hallucination rate has been measured.
