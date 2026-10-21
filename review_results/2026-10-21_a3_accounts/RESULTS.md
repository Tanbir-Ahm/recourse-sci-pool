# A3: accounts, consent, limits, saved chats, free trial, retention (built 2026-10-21)

Recourse branch `register-hooks-and-overlay`, NOT on `main`, nothing deployed by Claude. Commits: `e5fa226` (A3.1 sign-in core), `dafbb7c` (A3.2 consent, age, export, delete), `022da13` (A3.3 quotas), `31e121a` (A3.4 chats, free trial, notes, feedback), `32ba6c1` (A3.5 purge, CORS, flood guard), and the A3.6 commit (the account command-line tool).

## What exists now (routes)
| Route | What it does |
|---|---|
| `POST /api/auth/google`, `POST /api/auth/logout` | browser sign-in with a Google ID token; cookie session + CSRF token |
| `GET /api/me`, `GET /api/legal/{doc}`, `POST /api/me/consent`, `POST /api/me/age`, `POST /api/me/export`, `DELETE /api/me?confirm=DELETE` | who am I; the documents; accept them; 18+; my data as a file; delete everything now |
| `GET/POST /api/chats`, `GET/PATCH/DELETE /api/chats/{id}`, `POST /api/chats/{id}/ask` | saved conversations; the question (server-sent steps; needs `Idempotency-Key`) |
| `POST /api/anon/ask` | the free trial without signing in (3 layman questions a day per device) |
| `GET/POST /api/notes`, `PATCH/DELETE /api/notes/{id}`, `POST /api/feedback` | notes (limited by plan); "report an error" on an answer |
| plus the A1 `POST /api/ask` (shared key) and `GET /api/health` | unchanged |

Streamlit will call the same routes with a short-lived signed token (`Authorization: Bearer`) instead of a cookie.

## What the tests prove (all free, offline, stub engine, real throwaway PostgreSQL)
- `test_api_auth.py` 79 checks, `test_api_me.py` 41, `test_api_quota.py` (windows, reserve/settle/release, 48-way and 40-way races), `test_api_chats.py` (ownership, idempotency, follow-ups, limits, notes, feedback, trial, 12-way budget burst), `test_api_hardening.py` 32 checks (purge, CORS, flood guard).
- Quota: a limit of 10 holds under 48 simultaneous requests (exactly 10 allowed and counted); a refusal or an engine failure costs nothing; the day starts at IST midnight.
- Chats: another person gets 404, never 403; a repeated key returns the stored answer and charges nothing; the same key with other words is refused; the same key while the first still runs is refused; the question and the answer are saved by the worker thread, so a caller who disconnects loses nothing; a follow-up sends the engine the person's earlier QUESTIONS and never an earlier answer.
- Trial: closed unless `ANON_TRIAL=on` + `IP_HASH_SECRET` + a budget; question kept 90 days under a random device id, no IP stored (checked in the rows); 3 a day per device; a separate per-address flood guard; the trial's own daily budget holds even for 12 questions arriving at once (4 admitted at Rs 10 estimate against Rs 40).
- Purge: expired trial questions, expired sessions, old counters, chats past a plan's history limit are deleted and nothing else; one audit row with counts only; a second copy running at once does nothing.
- Real HTTP (not the test client): a local server with a stub engine, driven by `api/try_account.py`: steps arrive one by one (0.4 s apart), usage `1 of 10`, the trial counts 1, 2, 3 and then `429 device_limit`.

## What was NOT tested / limits (say these)
- No live model (no Anthropic key here): every answer in these tests is a stub. The owner's staging run is the first real one.
- Google sign-in itself was never run against Google (tests use a locally signed token and a stand-in key set). It needs a Google OAuth client (the owner's step, when the front end exists).
- `TRUSTED_PROXY_HOPS=1` is [Guessing] for Railway: Part 4u step 7 checks it from two networks. If wrong, every visitor shares one address and the flood guards cut real people off (the trial's address cap would then refuse everybody after 20 questions).
- The trial's per-device cap is bypassed by clearing cookies: the address flood guard (default 20 a day per address) and the trial budget are the real brakes. The owner's D4 said "capped hard by IP and the daily budget"; I did NOT make the per-address cap 3, because many people share one mobile or office address (carrier NAT) and 3 would turn them away. Needs his confirmation.
- Legal text is placeholder (gate G1): `ACCOUNTS_OPEN` plus real people needs the lawyer's privacy notice and terms; `ACCOUNTS_ALLOW_PLACEHOLDER_LEGAL=on` is for staging only.
- One replica only: the replay cache for Streamlit tokens, the in-flight key table, the flood guard counters and the budget file are in-process.
- Plan numbers (10 layman and 3 lawyer a day for a free account; 3 for the trial) are provisional until step A5.
- The 90-day, retention and deletion behaviour is code, not legal advice; a lawyer must read the notice before real people use it. Backups roll off on Railway's schedule (the notice must say so).
- `/api/health` no longer avoids importing SQLAlchemy (the signed-in routes import it); it still does not import the engine or Streamlit, and a connection is made only when `DATABASE_URL` is set.
- No hallucination rate has been measured; nothing here changes the answer engine.
