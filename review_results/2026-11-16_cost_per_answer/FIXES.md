# Cost-saving fixes for lawyer answers, 2026-11-16 (owner: "Build the cost-saving fixes for lawyer answers")

## Where a lawyer's answer spends money (from the cost note in RESULTS.md)
1. The answer call itself: about 3,000 to 20,000 input tokens plus about 5,000 output tokens (one October data point; thinking is billed as output). About Rs 6 to 10.
2. A second full answer when a check fails (`answer_recheck`): the same again. FOLLOW_UPS 2x: Rs 6.41 + Rs 6.52; 2026-11-09: Rs 22.17 for an answer that was then withheld.
Stored logs show three lawyer retries by reason: `unsupported_case_generalisation` (the proximity fix of 2x already removed its main false trigger) and `cognizable_bailable_omission` twice. The retry rate is unknown.

## BUILT: `RETRY_BY_CODE` (Recourse branch, default OFF, lawyers' note only)
- `on`: when the only thing the checks found is a FACT THE ANSWER LEFT OUT, the answer is kept and the fact is added as a note written by code: (a) a section's cognizable / bailable status that the answer stated for the other field only (the table's value, as for the existing classification note); (b) a companion section that reached the material (today the BNSS 164 / 166 pair) and was not discussed.
- `soft`: also for a case the answer credits with more than its excerpt shows: a "check the excerpt" note instead of a second answer. This trades a rewrite for a warning; the owner's choice.
- Never skipped: a wrong status, a section or Act not in the material, a wrong court, a wider-search case used as authority, an enforced grounding check. These still get the second answer, and `soft` does not widen that.
- Log line `RETRY_SKIPPED_BY_CODE {...}`; `COST_QUESTION` switches carry `retry_by_code`. Layman answers unchanged.
- Tests: `test_retry_by_code.py` (15 checks: off = two calls; on = one call and the note; layman unchanged; wrong status, left-out fact plus an ungrounded section, and soft with a wrong status all still get the second call); suite 155 of 155. Model stubbed: nothing tried with the real model.
- What it cannot show: the savings. Each skipped retry saves one whole answer (about Rs 6 to 10), but how often omission-only or companion-only failures happen on real lawyer questions is unknown (two stored cases). The quality cost is also unmeasured: the note states the table's value or names the section; it does not write the missing analysis the second answer might have.

## NOT built, with the reason
- `PROMPT_CACHE`: it exists and is off. The fixed lawyer prefix is 11,199 characters (about 2,700 to 3,100 tokens). A cache hit saves about Rs 0.46 to 0.54 an answer; a miss costs about Rs 0.13 to 0.15 extra (5-minute cache) or Rs 0.51 to 0.60 (1-hour cache). It pays only if more than about 22% of questions (5-minute) or 53% (1-hour) arrive within the window of an earlier one. At today's traffic that is doubtful: leave it off until the log shows it.
- Cheaper retry (lower effort on the second answer): saves thinking tokens but risks a worse rewrite that fails its checks again and is withheld, which is the more expensive outcome. Not built without a measured trial.
- Trimming heavy prompts: three of ten sample questions carried 14,000 to 20,000 tokens, mostly whole statute sections (one BNSS chapter block was 40,000 characters). Cutting them changes what the model sees; no way to judge quality offline. Not built.
- Lower `ANSWER_EFFORT` for lawyers: an existing switch; a staging test of the owner's.

Say "no hallucination rate has been measured".
