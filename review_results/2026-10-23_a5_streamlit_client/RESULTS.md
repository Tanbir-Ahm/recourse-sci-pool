# A5: the Streamlit page as the first client of the API, and the work before it (built 2026-10-23)

Recourse branch `register-hooks-and-overlay`, NOT on `main`, nothing deployed by Claude. Owner's go (2026-10-23): "yes build the refusal wording and cap, then start A5; keep 20" (the per-address trial cap stays 20).

## Before A5 (owner's go, same message)
1. **Refusal wording in one place** (`refusal_text.py`): the page and the API now take the words for a non-answer from one module. The page's rendered text for all 12 refusal cases is byte-identical to a golden copy captured BEFORE the change (`refusal_page_golden.json`, `test_refusal_text.py`). The API reply (`/api/ask`, `/api/anon/ask`, `/api/chats/{id}/ask`, and a saved chat's messages) carries a `notice` (label, title, body, footer) for a non-answer; `text` stays null.
2. **Refusal caps**: a signed-in person's refused questions (free of the daily allowance, each costing the model's topic check, about Rs 0.4): 20 an IST day (`REFUSAL_DAILY_LIMIT`); a trial device: 10 (`ANON_REFUSAL_DAILY_LIMIT`). Our own failures (no cost recorded) are not counted against the person; deleting chats does not reset the count. Tests: `test_api_quota.py`, `test_api_chats.py`.
3. Per-address trial cap stays 20 (owner). Note: it does not work on Railway as built (the address guess failed; FOLLOW_UPS 2bz; the diagnostic is waiting for the owner).

## A5: what was built (all behind `USE_API`, default OFF: off = the page is exactly as before)
- `site_client.py`: the page's client of the API: mints the short-lived signed token (5 minutes, used once) with `STREAMLIT_API_SECRET`, calls the API over its public address, reads the server-sent steps as they arrive; every API refusal arrives as an `ApiError` with the API's own code.
- `site_account.py`: what the page shows when `USE_API` is on: Google sign-in (`st.login`; the login settings come from environment variables and are handed to Streamlit IN MEMORY, nothing is written to disk), the consent card (documents, tick boxes for the documents and for 18+), the account bar (who, "N of M answers left today", sign out), the question through the API in a saved chat with the real steps drawn, today's usage line under the answer, "report a problem with this answer", "my data and account" (download everything, delete the account).
- `recourse_app.py`: small edits only: the switch, the gate before the question box, the ask call, the notice state, a note that the conversation is saved. Follow-ups stay in one saved chat (the server folds in the earlier QUESTIONS, never earlier answers); a new question or a change of voice starts a new chat.
- `/api/me` now carries today's usage and limits. `requirements.txt` gains `Authlib==1.9.1` (needed by `st.login`; it installs on the website's next deploy whether or not `USE_API` is on).

## Tests (free, offline, stub engine, no cost)
- `test_site_client.py`: the client over REAL HTTP against a real API server and a real PostgreSQL: the minted token works once; sign-in, consent, age, chat, a streamed question (steps arrive one at a time, 0.15 s apart), usage 1/2/3, replay of the same Idempotency-Key, a refusal with the shared notice, every API error code (consent_required, limit_reached, turn_limit, not_found, bad_token, engine_error, unreachable) without leaking the exception text, feedback, export, delete.
- `test_site_account.py` (33 checks): the page with `USE_API` on, in Streamlit's AppTest with the API client replaced: signed out, not accepted, ready, a question, the usage line, a follow-up in the same chat, a new question in a new chat, a change of voice, each limit notice (never the technical-trouble text), a refusal, feedback, delete.
- `test_site_e2e.py`: the WHOLE path in headless Chromium: a real Streamlit page, the real API, a local stand-in for Google, a throwaway PostgreSQL: sign-in card, sign-in round trip, consent card, accept, a question and its answer through the API, "9 of 10 answers left today", still signed in after a reload, the person, two consents, one chat and two messages in the database, sign out.

## What was NOT tested / what you must not conclude
- **Real Google was never used.** The browser test uses a stand-in OpenID provider with the same standard claims; only the owner's staging test with a real Google OAuth client proves the real sign-in (and Google may behave differently: consent-screen status, test users, the redirect address).
- **No live model**: the engine in these tests is a stub. Answer quality is untouched by A5 (the API runs the same engine) and no hallucination rate has been measured.
- **`TRUSTED_PROXY_HOPS` is wrong on Railway** (FOLLOW_UPS 2bz): the per-address limits do nothing until the address diagnostic is run and the rule fixed. Do not open sign-ups to the public before that.
- **Legal text is a placeholder** (gate G1): the consent card shows TEST text; accounts for real people need the lawyer's privacy notice and terms. `ACCOUNTS_ALLOW_PLACEHOLDER_LEGAL` is staging-only.
- Streamlit's login cookie lasts 30 days; the person is signed in on the page for that long but each API call uses a fresh 5-minute token, so a person whose Google account is later disabled stays signed in on the page until the cookie ends [Likely].
- One replica only (the token replay memory is in the API process).
- Conversations are saved but the page has no list of past chats yet (that is part of the new front end, step B); deleting one conversation is only possible through the API today, not on the page; "delete my account" is on the page.
- Production: `USE_API` must NOT be set on production before the lawyer's text, the address fix and the owner's decision; the website service's `railway.json` still uses config-as-code that Railway retires on 2026-12-01.
