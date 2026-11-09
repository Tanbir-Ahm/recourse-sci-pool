# Bail sections for "arrested me" questions: pre-registration (2026-11-09, written BEFORE any run and before any code)

**Owner's go:** "Build the bail sections for 'arrested me' questions" (step 1 of the plan after the 8 Nov answer, which printed BNSS 47(2), the right to be told of bail, and said nothing about bail).

**What the hypothesis is.** When a person says they, or someone they name, HAS BEEN arrested or IS in custody, the answer should have the bail sections in front of it: BNSS 478 (bail in a bailable offence: a right), BNSS 480 (bail in a non-bailable offence: discretionary), and, when bail has already been refused, BNSS 483 (the High Court's and Sessions Court's power). The library search may already bring them; that is measured first, as with the harbouring alias.

**Rule being followed** (`statute_aliases.py`): a new alias needs a measured miss, word groups written before the question set is run, a negative list and a test; no tuning on the set that measures it.

**Entries (exact regular expressions in `groups_as_written.py`, committed before the run):** `bnss_478_bail_bailable` and `bnss_480_bail_nonbailable` (same trigger: a person was arrested / detained / is in custody, in jail, in a lock-up, remanded), `bnss_483_bail_higher_court` (bail refused / rejected / denied / dismissed, or bail with High Court / Sessions Court).

**Question sets** (`questions_bail.py`, written by Claude, not a lawyer): 30 positives where someone has been arrested (kind `pos_arrest`, expected BNSS 478 AND 480), 8 where bail was refused (`pos_483`, expected BNSS 483), 30 negatives where nobody has been arrested or is in custody now (`neg`): general arrest law, notices, anticipatory bail, FIR questions, bail in the abstract. Also all 202 earlier questions and the harbouring sets are run through the word groups alone to count unintended fires.

**Success rule fixed in advance.** Build only if the baseline needs it: if the library search already brings BOTH 478 and 480 for at least 27 of the 30 arrest positives, the entries for 478/480 are NOT built (reported as unnecessary). After the change: both sections for at least 27 of 30; 483 for at least 7 of 8; at most 2 of 30 negatives fire an entry; fires on the earlier question sets that are about someone being arrested are not false fires, every other fire is read and counted as false. Failure is reported, not tuned away on these questions.

**What this cannot show.** Whether the answer model uses the sections well (no Anthropic key in the sandbox); whether a lawyer agrees these are the right sections for each question; the cost: two more sections in the prompt of every arrest question (measured as characters added, not as money). No hallucination rate has been measured.
