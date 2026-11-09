# Staging, 9 Nov 2026: the follow-up that showed "Out of scope / Something isn't working right now"

Source: the owner's `staging-api` log for that run (commit `7427d329fbe7`, service `api`), read in full. The log itself is not stored here (it holds conversation ids and connection addresses); the figures below are from it.

## What happened (certain, except where marked)

| time (UTC) | event |
|---|---|
| 08:28:08 | question 1 arrives (lawyer, v3). Scope check twice (the first reply named a section the person never wrote, so the engine retried), `STATUTE_ALIAS` bnss_478 and bnss_480, `ACT_DETECT` (Haiku) names POCSO and the IT Act, Act shelf 5,560 characters, `STATUTE_WIDEN` adds BNS 17 (re-ranker 0.62), wider search feeds 8 cases |
| 08:29:34 | answer 1 written: 25,808 tokens in, 6,402 out, Rs 11.16; whole question Rs 12.38; about 87 s end to end |
| 08:35:23 | question 2 arrives (the request line is logged when the stream starts) |
| 08:35:28 | `CHAT_TURN` turn 2: `rewrite: dropped_guard:number_not_in_person_messages`, `folded: 1`, `carry: []` |
| 08:35:30 | library search on the bare follow-up: BNSS 236, 234, 244, 353, 237 (charge framing and discharge); the relevance gate (log mode) marks all five below its floor |
| 08:35:39 | wider search feeds 8 cases (a different set); the answer model starts |
| 08:37:39 | the owner downloads the conversation as Word: it holds question 1 only |
| 08:37:42 | answer 2 finished: 11,412 in, 10,977 out (the budget for a lawyer's note is 12,000, thinking included), Rs 12.80; whole question Rs 14.03 |

So answer 2 took about 139 s from request to finished answer (16 s of searching, 123 s of writing at about 89 tokens a second). The site stops waiting at `API_ASK_TIMEOUT_SECONDS` = 120 s. The log has no `engine failed` line and no save-failure warning, so the engine did not fail; the answer was finished and (very likely) saved while the page showed an error. **The exact start time is inferred from the access-log line; the 120 s default is read from the code, not from the Railway variable (not confirmed).**

## Why the box said "Out of scope"

The web front end (`messages.ts`) and the Python notice (`refusal_text.py`) gave every technical failure the label "Out of scope". The site's own give-up (`timeout`) had no wording of its own and fell into that catch-all. Nothing was out of scope.

## Why the follow-up had no context

`web_chat.rewrite` asked Haiku for a stand-alone question; the guard dropped it because it contained a number the person never wrote (likely a section number from our earlier answer; the rewrite text is not logged). `rewrite()` returns `new_topic` before the guard if the model says "not a follow-up", so a `dropped_guard` outcome means the model DID judge it a follow-up. `should_carry` nevertheless did not carry the earlier answer's sections for that outcome, so BNS 77, BNSS 35, 47, 187, 480 never travelled. The bare words then found procedure sections, no offence sections (reproduced offline with the answer model stubbed: BNSS 236, 234, 244, 353, 237).

## Other facts the log gives

- BNS 17 in answer 1 came from `STATUTE_WIDEN` (added, re-ranker 0.62, floor 0.55), not from the library search. The relevance gate in log mode would have kept BNS 77 only.
- The POCSO notice came from the Haiku Act pass; the scope check's own reasoning had assumed "child sexual abuse material", which the question never says. POCSO sections (24, 26, 36; later 42, 29, 30) were handed to the answer model at scores of about 0.27 to 0.41.
- Both questions cost one extra scope check because the first reply named a section the person never wrote (the safeguard working; about Rs 0.45 each).
- Wider-search cases handed to the answer: none of the 8 was named in answer 1 (checked by `answer_view.sci_named` on the saved text: 0 of 8; Prabir Purkayastha and Satender Kumar Antil, library cases, were named).

## Not established

Whether answer 2 can be opened in the saved conversation (the log shows the owner reopening the conversation at 08:53, not what was on screen). Whether the Railway variable `API_ASK_TIMEOUT_SECONDS` is set. What the Haiku rewrite said. No lawyer has read either answer. No hallucination rate has been measured.
