# Website design document, option C (written 2026-10-20; DESIGN ONLY, NOT approved, NOTHING built)

Companion to `WEBSITE_BUILD_PLAN.md` (the order, section 5b) and to the owner's answers of 2026-10-20 (FOLLOW_UPS 2bh, 2bi). This file settles the four open design points of section 5b and sets out the tables, calls, screens, flows, folders, tests and work breakdown. No code is written until the owner says go. Confidence marks: [Certain] read in the code or tool today, [Likely] strong inference or from memory of a vendor's product (verify on first use), [Guessing] estimate.

## 0. The three things to know before reading the rest

1. **The interface is not the hard part; trust and law are.** No hallucination rate has been measured, no lawyer has read the Act texts or the production answers, and the privacy notice does not exist. Accounts start the day Phase A5 goes live, and from that day data-protection duties apply. So the order inside the plan is: the lawyer's notice and consent text (A4) BEFORE any real account (A5). That is a gate, not a suggestion.
2. **The engine does not stream text, and should not.** `answer_question()` returns one finished result (chat_assistant.py:4096). After the model writes, code rewrites the text (Act-name corrections, the quote check, cut-off handling, labels, the section boxes). A token stream would show words that are later changed. So the design streams the REAL STEPS live and delivers the answer whole, once checked. [Certain] about the rewriting; the choice is a judgment, and the honest-steps panel is the part of the TathyaGrid idea worth keeping.
3. **The engine is safe to call from many requests at once only if each request keeps its own thread.** Per-request state is held in `threading.local` (cost_log, sci_search_tier, grounding_checks, answer_style, excerpt_anchors, `_ACTS_CACHE`, `_OPEN_TOPIC`) [Certain]; the shared caches (`act_shelf._STATE`, `act_directory._STATE`) are read-mostly and lock-protected [Certain]. The daily-budget file is guarded by an in-process lock only (cost_log.py:129), so **one replica of the API service** until that is changed [Certain]. A concurrency test is a gate of A1.

## 1. The four open design points, settled (for the owner's approval)

### 1.1 Where the engine's code lives
**Recommendation: an `api/` folder inside the Recourse repository** (`Tanbir-Ahm/recourse`), importing the engine in place (`import chat_assistant`). Reasons: the engine is about a hundred modules that import each other by bare name and carry their data (`chunks/`, `act_shelf/`, `embeddings/`, the register bundle); extracting a package now would be a large refactor with no user-visible gain and would risk the behaviour 90 tests protect. The API is a thin wrapper, so it lives next to what it wraps. Cost: one repository drives three services (website, API, later the WhatsApp bot), so config files must be kept apart (1.2). Alternative (an installable package) is a later step if the engine is ever shared with a repo that is not Recourse; not needed for option C. [Likely]

### 1.2 How a new Railway service avoids the website's `railway.json` and `Procfile`
The trap: the repository root holds `railway.json` and `Procfile`, both of which start Streamlit with the website's healthcheck. A second service built from the same repository would read them and start Streamlit instead of the API (the WhatsApp bot hit this).
Design (three layers, so a slip in one is caught by the next):
1. **(Superseded 2026-10-21.) Own config file for the API service: NOT POSSIBLE for a new Railway service.** The dashboard says "Starting 2026-08-28, services that have never used Config as Code cannot opt in" and "Existing config files keep working until 2026-12-01". **What works instead (tested on `staging-api`, 2026-10-21):** the dashboard's Custom Start Command and Healthcheck Path plus the variable `NIXPACKS_START_CMD` (it overrides the website's `Procfile`); the log showed `Uvicorn running ...` and `GET /api/health 200 OK`. `api/railway.api.json` stays in the repository as a record of the intended settings but Railway does not read it. A Dockerfile (`RAILWAY_DOCKERFILE_PATH=api/Dockerfile`) remains the fallback if the dashboard route ever fails; a release branch is the last resort.
2. **Fallback if that setting is not offered:** a Dockerfile for the API at `api/Dockerfile` and the service variable `RAILWAY_DOCKERFILE_PATH=api/Dockerfile`; a Dockerfile ignores `Procfile`/Nixpacks start commands. [Likely]
3. **The healthcheck is the guard.** `/api/health` returns `{"role": "api", "commit": "<sha>", "db": "ok|down"}`. If Streamlit started by mistake, the check fails and Railway keeps the old deployment. A test asserts the route and the role string.
Also: set **Watch Paths** on each service (website: everything except `api/` and `web/`; API: `api/`, the engine modules and data) so a change meant for one does not redeploy the other. [Likely]
Never run `railway up` for the API from a folder that has the website's two files unless the config path is set (WHATSAPP_PLAN.md section 3 has the clean-clone recipe if the CLI is ever used; the API should deploy from GitHub, not the CLI).

### 1.3 How Streamlit hands its signed-in person to the service
Two clients, one user table.
- **Streamlit (A5), trusted client.** Streamlit signs the person in (`st.login`, Google) and, on each call, mints a **short-lived signed token** (HS256 JWT, 5 minutes; claims `iss=streamlit`, `aud=recourse-api`, `sub=<Google sub>`, `email`, `email_verified`, `exp`, `jti`) signed with a secret `STREAMLIT_API_SECRET` shared with the API as a Railway variable. The call goes to the API's **public HTTPS address** (the token is the protection; Railway's private network was dropped after the A0 spike: it needs IPv6 listening, which uvicorn may not do alongside IPv4, and older Railway environments are IPv6 only). The API verifies signature, expiry, audience and `jti` (replay window), then finds or creates the user by `(provider='google', subject)`. [Spike 3, `review_results/2026-10-20_a0_spikes/RESULTS.md`]
- **Next.js (B), direct client.** The browser signs in with Google; the API verifies the Google ID token itself (signature against Google's keys, `aud` = our client ID, `exp`, `email_verified`), creates its own session (opaque random id in an HttpOnly, Secure, SameSite=Lax cookie, stored hashed in `sessions`), and the front end calls the API with that cookie. CSRF is handled with a double-submit token on every non-GET call.
- **Why not one scheme for both:** Streamlit cannot hold an HttpOnly API cookie, and the browser must never see the shared secret. The two paths meet in `get_current_user()`, which returns the same `User` object either way. The secret is never in the repo and is rotated by changing the variable on both services.
- **Why our own token and not Google's ID token (A0 spike 1, run in a browser):** `st.user` does carry `sub`, `email`, `email_verified`, `name` [Certain], and `st.user.tokens["id"]` can expose the ID token, but Streamlit never refreshes it: a person stays signed in for 30 days while the token expires in about an hour, so forwarding it would fail.

### 1.4 Where the new front end's repository lives
**A new repository, `Tanbir-Ahm/recourse-web`** (Next.js, TypeScript). It must not live inside Recourse because that repository's `main` drives the live website and its `railway.json` would capture a Node service. The owner creates the empty repository (and adds it to the Claude session's scope); Claude then builds in a branch, never `main`, and the owner merges by his own pull request, as for Recourse. The contract between the two is the API's **OpenAPI file**, generated by FastAPI and committed in Recourse as `api/openapi.json`; the front end generates its TypeScript types from it, and a CI check fails if the two drift. Hosting: a Railway service next to the API (one bill, one place for logs), or Vercel; recommendation Railway. [Likely]

## 2. Folder layout (in the Recourse repository; nothing moves out of the root)

```
recourse/                      (existing; the engine stays where it is)
  chat_assistant.py ... act_shelf/ chunks/ ...      (unchanged)
  progress.py                  NEW, tiny: emit(step, **detail) -> no-op unless a listener is set (threading.local)
  api/
    main.py                    FastAPI app, routers, middleware
    config.py                  settings from environment (never read secrets elsewhere)
    deps.py                    get_db(), get_current_user(), require_role(), enforce_quota()
    auth/                      google.py, streamlit_token.py, sessions.py, roles.py
    routers/                   ask.py, chats.py, notes.py, me.py, feedback.py, billing.py (later), admin.py, health.py
    engine_adapter.py          runs answer_question in a worker thread, maps the result dict to the API schema, emits steps
    quota.py                   reads entitlements, reserve/settle
    consent.py                 versions of notice and terms, records acceptance
    privacy.py                 export and delete my data
    db/                        models.py, migrations/ (Alembic), seed_plans.py
    schemas.py                 Pydantic models = the OpenAPI contract
    railway.api.json           the service's own config (1.2)
    Dockerfile                 fallback (1.2)
    tests/                     contract, auth, quota, concurrency, privacy, migration tests
  api/openapi.json             generated, committed, checked in CI
recourse-web/                  SEPARATE repository (1.4)
```
Streamlit change (A5) is confined to `recourse_app.py` plus a `site_client.py` (token mint, HTTP calls, switch `USE_API`); with the switch off the page calls the engine directly as today. That switch is the way back.

## 3. The engine hook for real steps (the only engine change)

`progress.py` holds a per-thread listener and `emit(step_id, label=None, **detail)`. With no listener it does nothing, so the engine, the WhatsApp bot and Streamlit are unchanged unless they set one. One-line `emit` calls go at points the engine already passes (fail-open: an exception in a listener is swallowed):

| step id | where | detail sent |
|---|---|---|
| `scope` | after `classify_scope` | the state (answer inline, special-law, not covered) |
| `acts` | after the Act Directory / ACT_DETECT | Act names found (or none) |
| `sections` | after the shelf search and SECTION_XREF | "Act, section N (and cited section C)" |
| `library` | after retrieval | count of library passages used (a number, not text) |
| `register` | after the register lookup | how many cases flagged |
| `wider` | when SCI_SEARCH feed runs | "searching the wider Supreme Court index" / how many passages |
| `write` | before the model call | audience and style |
| `checks` | after the grounding/quote checks | counts of notes |
| `done` | at the end | none |

Rules: a step says only what the code actually did (never "analysing precedents" as theatre); no question text or passage text goes in a step; steps that did not run are not shown. [Certain] the points exist; exact line placement is the work of A1 and each `emit` gets a test.

## 4. Data model (PostgreSQL on Railway)

All ids are UUIDs; every table has `created_at`; user-owned rows carry `user_id` and are deleted by cascade from `users`. Types are indicative.

```
users            id, email (unique, lower), email_verified bool, display_name, role enum(user,lawyer,reviewer,admin) default user,
                 plan_id fk, language, age_confirmed_at, status enum(active,suspended,deleted), last_seen_at, deleted_at
identities       id, user_id fk, provider ('google'|'phone'|'email'), subject text, unique(provider, subject)
sessions         id (hash of cookie value), user_id fk, expires_at, user_agent_hash, ip_hash   -- Next.js path only
consents         id, user_id fk, document enum(privacy,terms,data_use), version text, accepted_at, ip_hash, text_hash
chats            id, user_id fk, title, audience enum(layman,lawyer), archived bool, updated_at
messages         id, chat_id fk, role enum(user,assistant), seq int, content text,
                 result jsonb null     -- the assistant message's whole structured result (sources, notices, boxes, authorities, anchors, notes)
                 engine_commit text, style text, state text, request_id, cost_inr numeric(8,2) null, input_tokens, output_tokens
notes            id, user_id fk, message_id fk null, body text, updated_at
feedback         id, user_id fk, message_id fk, kind enum(wrong_law,wrong_case,wrong_quote,missing,unclear,helpful,other), comment text, status enum(new,reviewed,closed), reviewed_by
usage_events     id, user_id fk, message_id fk null, at, kind enum(answer_layman,answer_lawyer,draft,doc_read), cost_inr, counted bool, plan_id_at_time
plans            id, code ('free','pro','lawyer', ...), name, active, sort
entitlements     id, plan_id fk, feature text, period enum(day,month,none), limit int null, version, effective_from   -- null limit = unlimited
subscriptions    id, user_id fk, plan_id fk, provider ('razorpay'), provider_subscription_id, status, current_period_end, cancel_at, mandate_id   -- Phase C
payments         id, subscription_id fk, provider_payment_id unique, amount_paise, gst_paise, status, invoice_no, paid_at                   -- Phase C
webhook_events   id, provider, provider_event_id unique, payload jsonb, received_at, processed_at, error                                      -- idempotency
audit_log        id, at, actor_user_id, action, target_type, target_id, detail jsonb (no message text)
deletion_requests id, user_id, requested_at, completed_at
```
Plans and prices are rows, not code (owner's decision 2): an `entitlements` change takes effect without a deploy. Prices live with Razorpay's plan ids in Phase C, not in this table. The drafting/document tables (drafts, uploaded files, extracted text) are added in Phase D, with their own retention rules.

**Retention (default; the lawyer decides):** chats and notes kept while the account is active and deleted on "delete my data" within 30 days; `usage_events` and `audit_log` keep no message text, kept 24 months for billing and abuse; backups roll off within 35 days (state this in the notice). Logs never hold question or answer text (the cost log already stores a hash, not the question) [Certain: PRODUCTION_SWITCHOVER item 3].

## 5. The API (FastAPI; JSON; every route under `/api`)

| Route | Purpose | Notes |
|---|---|---|
| `GET /api/health` | liveness, role, commit, db | no auth; the deploy guard (1.2) |
| `POST /api/auth/google` | exchange a Google ID token for a session | Next.js path; sets the cookie |
| `POST /api/auth/logout` | end session | |
| `GET /api/me` | user, plan, today's usage and limits, consent state | the front end's first call |
| `POST /api/me/consent` | accept `{document, version}` | required before `/ask` |
| `POST /api/me/export` / `DELETE /api/me` | export / delete my data | 30-day completion, audit-logged |
| `GET /api/chats`, `POST /api/chats` | list (search by title) / create | |
| `GET /api/chats/{id}` | messages with their results | owner only |
| `PATCH /api/chats/{id}` / `DELETE` | rename, archive, delete | |
| `POST /api/chats/{id}/ask` | the question; **server-sent events** reply (5.1) | needs consent, quota, `Idempotency-Key` |
| `POST /api/ask` | same without saving (anonymous trial / WhatsApp later) | stricter quota |
| `GET/POST/PATCH/DELETE /api/notes` | notes | |
| `POST /api/feedback` | "report an error" on a message | feeds the weekly review |
| `GET /api/plans` | public plan list from `plans`/`entitlements` | |
| `POST /api/billing/subscribe`, `POST /api/webhooks/razorpay` | Phase C | webhook verifies the signature, stores the event once, then processes |
| `GET /api/admin/...` | users, spend, feedback queue, switches readout | role admin only, 2-step sign-in |

### 5.1 The `ask` event stream (text/event-stream)
```
event: step     data: {"id":"scope","label":"Checked that the question is about criminal procedure","status":"done"}
event: step     data: {"id":"acts","label":"Found the Prevention of Corruption Act, 1988","status":"done","detail":{"acts":["PC Act"]}}
event: step     data: {"id":"sections","label":"Pulled section 17 and the section it points to (13)","status":"done"}
event: step     data: {"id":"write","label":"Writing the answer","status":"running"}
event: result   data: {"message_id":"...","state":"single_match","audience":"layman","text":"...markdown...","sources":[...],"notices":{...},"section_boxes":[...],"authorities":[...],"anchors":[...],"grounding_notes":[...],"register":{...},"cost_inr":3.4,"disclaimer_version":"..."}
event: error    data: {"code":"budget_paused|quota|scope|engine_error|auth","message":"...","retry_after":null}
event: done     data: {}
```
`result` maps the engine's result keys one-to-one: `state, response_text -> text, matches/cited_judgment_links -> sources, act_notice, section_note -> section_boxes, authorities, anchor_excerpts, grounding_notes, register_notes/possible/not_checked, outside_scope_note, sci_fed/sci_related_judgments/sci_as_of, situation_detected, reasoning, redirect_domain, error` [Certain: the keys the page reads today]. **Nothing the page shows today may be dropped**: the schema carries every key, and a contract test feeds the three 2026-10-20 production results through the adapter and compares the rendered text field by field.
A reverse proxy may buffer SSE; the route sends `X-Accel-Buffering: no` and a heartbeat comment every 15 s. If streaming fails in a browser, the front end falls back to `POST` with `Accept: application/json` (same body, one reply).

### 5.2 Running the engine (engine_adapter.py)
- A bounded `ThreadPoolExecutor` (start at 4 workers; each call may take 10 to 60 s). The whole `answer_question` call runs in ONE worker thread so its thread-local state stays together [Certain: required by the design of the engine's state].
- The worker sets a `progress` listener that pushes events to a `queue.Queue`; the async route drains it into the SSE stream. A client disconnect cancels the wait, not the model call (the cost is already incurred); the answer is still saved so a refresh shows it.
- Timeouts: 120 s hard; on timeout an `error` event, no charge counted as an answer.
- Queue full: 429 with `retry_after`, not an unbounded wait.
- `audience` ('layman'|'lawyer') comes from the chat, not from the request body of a single message; lawyer mode requires role `lawyer` or an entitlement `lawyer_mode`.
- `channel=None` for the website. Follow-ups use `web_chat.py` unchanged (only the person's own earlier messages are folded in; never our answers) [Certain].
- The global `DAILY_BUDGET_INR` stays as the circuit breaker (state `budget_paused`), separate from per-person quotas.

## 6. Quotas and entitlements

Features: `answer_layman`, `answer_lawyer`, `chat_history_days`, `notes_max`, later `draft`, `doc_read`. Period `day` or `month`; a null limit is unlimited. Flow per `ask`: (1) load the user's plan and entitlements; (2) **reserve** one unit in a transaction (row-level lock on the user's counter) so two parallel requests cannot both pass the last unit; (3) run the engine; (4) **settle**: write `usage_events` with the real `cost_inr` from the cost log; if the engine failed, release the unit. Refusals (scope `unrelated`, `budget_paused`) do not consume a unit. The page shows "N of M answers left today". Unit tests cover the race (parallel asks at the limit). Starting values are the owner's choice at A5 (config, not code); the measured costs for context: Rs 2.7 to 4.6 layman, Rs 8 to 13 lawyer note [Certain: production logs 2026-10-20]. Abuse limits (separate from quota): per-IP and per-user requests per minute, in the API process for one replica, moved to Redis if replicas grow.

## 7. Screens (Phase B; wireframes are layout intent, not visual design)

```
HOME (signed in)                                        MOBILE: sidebar is a slide-over; one column
+-----------+--------------------------------------+
| New chat  |   What would you like to understand?    |
| Search    |   [ question box ............ ][Send]   |
| History   |   [Layman | Lawyer]     3 of 5 left     |
|  chat 1   |   Examples: arrest rights / bail / FIR |
|  chat 2   |   (one-click example fills the box)     |
| Notes     |                                         |
| Settings  |   Not legal advice; can be wrong. [i]   |
+-----------+--------------------------------------+

CHAT
+-----------+--------------------------------------+---------------------+
| history   | You: question                           | Steps (live)        |
|           | Recourse: answer (markdown)             |  done scope         |
|           |  [Copy] [Save to notes] [Report error]  |  done acts          |
|           |  grey box: official text of section N   |  ... write          |
|           |  Act notice / register notes            | Sources             |
|           | [ follow-up box ........... ]           |  tier label, link   |
+-----------+--------------------------------------+---------------------+
```
Rules carried from the engine: every notice, label ("from a wider search, not independently verified"), register note and grey box that the page shows today is shown; the Copy button copies the answer only; the sources panel shows full name, year, citation if held, paragraph, link, tier label and currency line; the lawyer view shows the table of authorities. Settings: language, export, delete my data, plan and usage, consent versions. Accessibility: keyboard use, visible focus, contrast AA, screen-reader labels (the Copy button already has an accessible name and a status role) [Certain]. Dark mode and phone width from the start. Later pages (drafting, upload, research) are Phase D/E and get their own design.

## 8. Flows

**Sign-up and first answer (Streamlit, A5):** open site, "Sign in with Google" (`st.login`), age confirmation (18+) and consent screen with the lawyer's notice and terms, record in `consents`, home with quota line, ask, answer saved to `chats`/`messages`. Signed-out visitors keep today's behaviour only if the owner chooses an anonymous trial (decision D4).
**Delete my data:** Settings, confirm by typing the word, `deletion_requests` row, user set `deleted`, content removed at once from the product, hard delete within 30 days, usage rows de-identified, confirmation email.
**Payment (Phase C, sketch) [Likely: Razorpay Subscriptions + UPI AutoPay; verify the current API and KYC steps]:** the person picks a plan, the API creates a Razorpay subscription and returns its checkout details, the browser pays, Razorpay calls `/api/webhooks/razorpay`; the API verifies the signature, stores `webhook_events` once (unique event id), then updates `subscriptions`/`payments` and `users.plan_id`. Failure paths: payment failed (grace days, then downgrade to free), cancelled (active to period end), refund (manual, admin), duplicate webhook (ignored by the unique key), out-of-order webhooks (apply by event time). GST invoices numbered in sequence. Nothing is charged before the gates in 11.

## 9. Security, privacy and safety

- Secrets only as Railway variables; separate keys for staging and production; rotate on a schedule and on any leak (the WhatsApp webhook secret is the open example). Never commit or paste logs with secrets or phone numbers.
- Cookies HttpOnly, Secure, SameSite=Lax; CSRF token on non-GET; CORS allow-list of our own origins; strict `Content-Security-Policy` on the front end.
- Input limits: question length cap, request size cap, per-user concurrency of one in-flight ask.
- Authorization on every row by `user_id` (tests try to read another person's chat by guessing an id).
- Admin: role check plus a second factor at the identity provider; every admin action in `audit_log`.
- Prompt injection: today the only untrusted input is the person's own question (already inside the Hard rules block, which no style may change) [Certain]. Uploaded documents (Phase D) are a new attack surface and get a separate design before they exist.
- Logs and error reports contain request id, user id, route, status, cost and timings, never question or answer text; any third-party error tracker is configured to scrub bodies.
- Minors and sensitive questions (POCSO, domestic violence): an 18+ declaration at sign-up and a clear notice are proposals only; what the law requires is the lawyer's call. Emergency text (legal-aid and helpline guidance for arrests) stays in the product; the invented-phone-number check is gone by the owner's instruction, so any number shown must come from reviewed text, not the model.
- Dependencies pinned (as Streamlit already is, 1.58.0); an audit step in CI.
- Backups: Railway Postgres backups on, plus a monthly restore drill into a scratch database (a backup never restored is not a backup).

## 10. Observability and operations

Structured JSON logs; request id passed from route to engine so the `COST_QUESTION` line can be joined to the request; uptime monitor on `/api/health` and on the site; alerts: error rate, p95 latency of `ask`, daily spend against `DAILY_BUDGET_INR`, queue-full rate, webhook failures. Admin page: spend per day and per plan, quota hits, feedback queue. A status/incident note for Railway outages (builds paused 2026-10-20 from 17:03 UTC showed that a build outage blocks a fix but not running services). Staging environment for every phase (the existing `recourse-staging` project pattern), with the production switches in `PRODUCTION_SWITCHOVER.md` and one new switch per phase.

## 11. Gates (nothing is skipped to save time)

- **G1, before any real account (before A5 goes live):** lawyer-drafted privacy notice, terms and consent text in place; age and minors approach decided; retention and deletion working; deletion test passes.
- **G2, before sharing the site publicly:** `SCI_SEARCH_MODE` back to `shadow` (or a lawyer has read feed answers) and a higher `DAILY_BUDGET_INR` (owner's steps); Mr. Advocate's reading of the Act texts and the production answers recorded.
- **G3, before charging money:** an error rate exists (the lawyer-marked set, the first step of `SUPPORT_AND_FIT_PLAN.md`, still parked) or the product wording makes no claim that needs one; refund and GST process agreed; Razorpay KYC done. Say "no hallucination rate has been measured" until then.
- **G4, before the domain moves to the new front end:** the owner's staging test, a lawyer's sample of answers on the new front end, the full engine suite green, and the Streamlit site still deployable as the way back.

## 12. Tests (each phase adds its own; the engine's 90-check suite must stay green throughout)

1. **Contract:** FastAPI schema vs committed `openapi.json`; front-end types regenerate with no diff.
2. **Parity (A1):** the three production questions of 2026-10-20 (PC Act s.17, POCSO s.19, PMLA s.45) through the API with the model stubbed to the recorded answers: every field the page shows today is present and identical. Then once with the live model by the owner on staging.
3. **Concurrency (A1):** 8 to 16 mixed questions in parallel with stubbed model calls; each result must equal its sequential result (no leakage of Act, audience, notes or cost between requests). Includes a layman and a lawyer request at once and a request that is cancelled mid-way.
4. **Auth:** forged, expired, replayed (`jti`), wrong-audience tokens refused; a deleted user cannot sign in; another person's chat unreachable.
5. **Quota:** the race at the last unit; failed engine call releases the unit; refusals are free; period roll-over at midnight IST.
6. **Privacy:** export contains exactly the person's data; delete removes content from every table; logs checked for absence of question text.
7. **Migration:** Alembic upgrade and downgrade on a copy; a seed of plans.
8. **Streaming:** steps arrive in order, `result` once, proxy buffering disabled, JSON fallback works.
9. **Front end:** component tests, end-to-end test with a browser on staging, accessibility check, phone-width check.
10. **Security:** dependency audit, header checks, a short checklist pass before G2.
11. **Load:** small ramp on staging to find the worker count; the quota and budget guards tested at the cap.
Live-model behaviour cannot be tested from the sandbox (no Anthropic key): every phase ends with the owner's staging test (`DEPLOY_STAGING.md` pattern) and a lawyer's sample.

## 13. Cut-over and way back

A5 is behind `USE_API` on the Streamlit service: off means today's direct engine call. The API has its own switch (`API_ENABLED`) and the front end its own service; the live domain keeps pointing at Streamlit until G4. Cut-over = point the domain at the new front end; way back = point it back (minutes) and leave `USE_API` as it was. Database changes are additive until the old path is retired. WhatsApp moves onto the API only after its own fixes (`WHATSAPP_PLAN.md`, on hold) and never before.

## 14. Work breakdown (order; sizes are [Guessing] for one person with Claude, in working sessions)

| # | Work | Acceptance | Size |
|---|---|---|---|
| A0 | Spikes: `st.user` claims; Railway custom config path and private networking; Authlib + `st.login` with Google on staging | one-page result each | 1 |
| A1.0 | Audit module-level mutable state in the engine; add `progress.py` and the `emit` points with tests | existing suite green; each step has a test | 2 |
| A1 | `api/` skeleton, `/api/health`, `engine_adapter`, `ask` stream, JSON fallback, config, container | parity + concurrency tests; deploys to staging as its own service (1.2) | 3 to 4 |
| A2 | Postgres, Alembic, tables 4, seed plans | migration tests | 2 |
| A3 | Google sign-in (both paths), roles, sessions, `/me`, export/delete, consent endpoints | auth + privacy tests | 3 |
| A4 | Lawyer-drafted notice and terms; consent screen; G1 | owner and lawyer sign-off | external |
| A5 | Streamlit as first client: `st.login`, token mint, `site_client.py`, saved chats, quota line, feedback button; `USE_API` | owner's staging test; free accounts only | 3 |
| B1 to B4 | Next.js: shell and sign-in, chat with steps panel, sources and boxes, history/notes/settings | G4 | 8 to 12 |
| C | Payments (after the price) | G3 | 4 to 6 |
| D to F | Drafting studio and documents; voice, Hindi, research page; domain switch, WhatsApp onto the API | each its own design first | later |

**Status 2026-10-21:** A0 done; **A1 built on the Recourse branch** (`POST /api/ask` with the real steps, fail-closed key, one worker thread per question, `progress.py` hook, contract file `api/openapi.json`; see `review_results/2026-10-21_a1_api/RESULTS.md`). **A2 built 2026-10-21** (15 tables, migration, seed, startup migration, health `db`; `review_results/2026-10-21_a2_database/RESULTS.md`; owner's step Part 4t). **A3 built 2026-10-21** (sign-in, consent, 18+, limits, saved chats, free trial, notes, feedback, purge, CORS, flood guard; `review_results/2026-10-21_a3_accounts/RESULTS.md`; owner's step Part 4u; FOLLOW_UPS 2bw). **A5 built 2026-10-23** (Streamlit as the first client behind `USE_API`: Google sign-in, consent card, saved chats with live steps, usage line, report a problem, my data; with the refusal wording in one module and refusal caps; `review_results/2026-10-23_a5_streamlit_client/RESULTS.md`; owner's step Part 4v; FOLLOW_UPS 2ca; real Google not yet tried). The address rule is wrong on Railway (FOLLOW_UPS 2bz). A4 (lawyer's notice) and B (Next.js) are not started. Two things found while building that change the text above: (a) the API must pass the same `inline_domains` the page passes (done); (b) the first ask route is protected by one shared key only and is not for public use.

## 15. Decisions (owner's answers, 2026-10-20; the design's recommendations were taken as they stand except D4)

- **D1 Engine location:** `api/` inside Recourse. YES.
- **D2 Front end host:** Railway.
- **D3 Chat retention:** kept until the person deletes, with a visible "delete" and the lawyer's view on the notice (the lawyer may change this default).
- **D4 Anonymous trial: DECIDED (owner, 2026-10-20): 3 questions without signing in**, layman mode only; lawyer mode needs sign-in. Caps: per device (cookie) and per IP, plus its own anonymous daily budget so anonymous use cannot eat the signed-in users' budget. Known weakness: many Indian mobile users share one IP, and a cookie can be cleared, so the cap deters casual use, not a determined bot. **Sub-question settled ("go as per your plan", 2026-10-20): the owner MAY read them, on the proposal below.** By design they are not stored (logs hold a hash only). If he wants them, they must be stored, and the notice and a visible line at the box must say so (questions can hold arrests, abuse, minors); proposal: stored with a random device id, no IP (a hash for rate-limiting only, short life), 90 days, readable only by owner and reviewer, used for quality review, never sold or shared; the lawyer confirms.
- **D5 Sign-in methods:** Google only at first.
- **D6 Age gate:** 18+ declaration (the lawyer confirms what the law requires).
- **D7 Free-tier numbers:** set at A5 from real use, as configuration.
- **D8 Lawyer-marked question set:** "Keep it": it stays ahead of payments (gate G3). It means: about 50 varied questions run through the full site, Mr. Advocate marks every cited case and quotation (right / wrong / does not support the point), giving the first measured error rate. Needed before charging money, not before free accounts.
- **D9 Brand:** keep "Recourse" after a lawyer's trademark search.

## 16. What this document does not claim

It is a design, not a test: no part has been built, no estimate is measured, the Railway, Razorpay and Streamlit details marked [Likely] must be checked on first use, and nothing here makes the answers more accurate or safe. The honest status of the product stays: no hallucination rate has been measured; the Act texts are `machine_checked`, nobody has read them.

## 17. The new front end (Phase B), decisions taken when building it (2026-10-23, owner's "Go straight to D")
These refine sections 1.3, 1.4, 7 and 9; where they differ, this section wins.
1. **Own repository `Tanbir-Ahm/recourse-web`** (section 1.4 stands): Next.js (App Router) and TypeScript; dependencies kept few and pinned (next, react, react-dom, react-markdown with remark-gfm, DOMPurify; dev: Vitest, Testing Library, Playwright, jose for test tokens). The owner creates the empty repository and adds it to the session; until it exists the work is kept as a git bundle in the research repository (`web_draft/`), which is deleted once the repository exists.
2. **The browser talks to the front end's OWN server, which forwards to the API (a "backend for the front end").** Section 1.3 said the browser calls the API with the cookie. On Railway the front end and the API live on different `up.railway.app` addresses, which are different SITES (the suffix is on the public-suffix list [Likely]): a `SameSite=Lax` session cookie is not sent on such cross-site requests, and Safari and some Firefox settings drop cross-site cookies altogether [Likely, widely documented]. With the server-side forward, the cookie is set on the front end's own address (same-site, Lax stands), no CORS is needed, and the API's address never reaches the browser. Cost: one extra hop (milliseconds), and the API would see the front end's address instead of the visitor's. Cure (built in the API): `FRONTEND_PROXY_SECRET` shared by the two services; the front end sends `X-Frontend-Secret` and `X-Visitor-IP` (the visitor's address taken from the platform's own `X-Real-IP`, which Railway's edge sets, FOLLOW_UPS 2ce) and the API then uses that address for its per-address limits; without the secret the header is ignored. The forward is an allow-list (only the API routes the screens use, never `/api/debug/*` or `/api/ask`), strips hop-by-hop headers, passes `Set-Cookie`, and streams the question's server-sent events unbuffered (tested for timing).
3. **Sign-in:** Google Identity Services in the browser gets an ID token, the front end's server posts it to `/api/auth/google`, the API verifies it and sets the session cookie. The same Google OAuth client is used (its "Authorized JavaScript origins" must list the front end's address; the client ID must also be set as `GOOGLE_CLIENT_ID` on the API). In tests a stand-in for Google's script and keys is used; only the owner's staging test proves the real thing.
4. **No UI framework**: plain CSS with design tokens, light and dark by `prefers-color-scheme`, mobile first (sidebar becomes a slide-over), visible focus, AA contrast, labelled controls.
5. **What the screens must carry over from the Streamlit page** (the page's `render_answer` is the specification; a test compares what each answer shape shows): the answer; the notices (Act notice, outside-scope note, register notes, quote and citation notices, refusal wording from `refusal_text`); the "wider search, not independently verified" labels; the grey box with a section's whole official text; the sources with tier labels; the table of authorities in the lawyer voice; Copy (answer only); report a problem; save to notes. Nothing is invented on the client: a result field the client does not know is ignored, never guessed.
6. **Safety of rendering:** the answer is markdown rendered without raw HTML; engine-built HTML (the Act notice) is sanitised with an allow-list; links open with `rel=noopener noreferrer`; a strict Content-Security-Policy; the answer text is never put in URLs, logs or error reports.
7. **Gates unchanged:** G1 (lawyer's text) before any real account; G4 before the domain moves. The Streamlit page stays deployable as the way back.
