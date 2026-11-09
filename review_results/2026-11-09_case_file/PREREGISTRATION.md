# Case file: does searching a follow-up on the new message PLUS the conversation's facts bring the sections the follow-up needs?

Written 2026-11-09 BEFORE the first run. Questions and expected sections are Claude's (not a lawyer's): a ceiling, not a measure of the law.

Method: `run_followups.py` runs the engine's real retrieval (`_answer_question_core`, answer model stubbed, Voyage embeddings real, `ACT_SHELF` on, `ACT_DETECT=wide`, `STATUTE_WIDEN` on, `CHAT_MODE=on` with a stand-in rewrite that the number guard drops, as on staging 2026-11-09) on
8 two-turn conversations, twice: (NO) as staging ran, the follow-up folded with the earlier message and searched on its own words; (WITH) the same with the case file's facts as a search text (merged with the own-words search).
Recorded: whether at least one expected section is among the sections handed over, and how many expected sections are.

Pre-set rules: the case file is kept if WITH holds at least as many expected sections as NO in every conversation in which NO found any, and finds more in total. If it loses a section somewhere, that is reported and the merge rule is looked at, not the questions changed.
The two last conversations (bail, arrest) are regression checks: their expected sections are the ordinary ones and must not be lost.
