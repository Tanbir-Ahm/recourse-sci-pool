# A3 on staging-api, first real run (owner's paste, 2026-10-23)

Service: staging-api, commit `fdcb6cca4f0b` (health: role api, db ok). Owner's way of running: `api/try_account.py` from his Windows PowerShell. Claude did not see the service; this is the owner's output, pasted.

## What happened
- The first redeploy attempts stayed on `0d13b8ea1111` (Railway build pause; the five A3 variables had also been lost: the list showed 8 variables, not 13, so Claude's "they are there" was wrong). After re-adding them and deploying, health showed `fdcb6cca4f0b`.
- `me` first gave `401 bad_token` because the owner's local copy of STREAMLIT_API_SECRET was 85 characters, not the 48 of the server's. After setting both from one fresh 48-character value: `200`, a new person on plan `free`, privacy and terms (PLACEHOLDER-0) still to accept.
- Passed: sign-in by the Streamlit-style token; consent gate; ask; steps in order (scope, acts, library, write, register, checks); answer saved (chat id 9b140803-...); `usage` 1 then 2 of 10, reset 2026-10-23T18:30Z (IST midnight); follow-up in the same chat treated as a follow-up; `chats` lists it with the first question as title; `show` returns the messages (user message `result` null, answer with the engine's whole result).
- Costs (real model): Rs 2.3027 and Rs 1.3292. NOT a production estimate: staging-api has no RESPONSE_STYLE, ANSWER_EFFORT, GROUNDING_CHECKS, ACT_SHELF etc. set (it was never given the staging-site's switches), so it ran the engine's defaults (style v1).

## The two answers (real model, staging-api defaults) and what a lawyer must check
Q1 "What happens at a remand hearing before a magistrate?" and Q2 (follow-up) "And what if I am not given a lawyer there?". No lawyer has read them. Claude's reading, [Likely], not legal advice:
1. Q1 says police custody is "only possible within the first 15 days". Under BNSS s.187(2) the 15 days of police custody may be spread over the first 40 or 60 days of detention; the sentence as written looks too narrow.
2. Q1 cites "Section 187(7)" for written reasons for police custody: Claude cannot confirm the sub-section number.
3. Q2 says s.341(1) BNSS "applies to trials and appeals, and a remand hearing is part of that same proceeding": the last clause is the model's own step and is not in the sections it was given; legal aid at a remand hearing rests on Article 22(1) and case law, which the answer does not name.
4. Q1 states the holdings of Vihaan Kumar v State of Haryana and Prabir Purkayastha v State (NCT of Delhi) from wider-search passages; the second carries the "not yet verified" note, the first does not.
None of this was caused by A3 (the engine is unchanged); it shows why "no hallucination rate has been measured" still stands.

## Not yet done (Part 4u steps 4 to 8)
The free trial, the Data-tab look, delete-me, and the two-network address check (TRUSTED_PROXY_HOPS).
