# Website build plan: from the current Streamlit site to a full product (drafted 2026-10-20; NOT approved, NOTHING built)

Owner's wish (2026-10-20): "I want to build a website like this [TathyaGrid] for Recourse ultimately. The UI may be better, but the idea is same." Then: "Lets proceed with the website part." This file is the plan for his approval. It keeps the staged path he approved on 2026-10-14 (CLAUDE.md): no stage starts before its trigger, and no code is written until he has answered the decisions in section 8.

## 1. What was looked at, and what was not
The TathyaGrid site could not be opened from the sandbox (its address does not resolve) and a web search found nothing about it. Everything about it comes from the owner's two screenshots: a home screen with one big question box and a one-click example query; a sidebar (New Chat, Research Workspace, Drafting Workspace, Legal Opportunities, Referral Invites, Notes, searchable chat history); attach, voice, a model picker and "Tools (6)" in the box; an "AI Drafting Studio" (free workspace for petitions, contracts and notices); topic chips; a chat view with a live "Thinking process" (steps such as Statutory Law Research, a Supreme Court search); a Pro plan with an "Unlock Pro" banner; Google login; a "can make mistakes" footer. Its plans, prices, data sources and accuracy are unknown.

## 2. What Recourse already has, and what it lacks
Has: the answer engine (`chat_assistant.py`) with grounding checks, the Act shelf (nine Acts) and official-text boxes, the Overruled Register, wider judgment search, cost log and daily budget, two audiences (layman, lawyer), Copy button, a petition draft and an arrest-document check, the WhatsApp bot, `web_chat.py` follow-ups, the reviewer routine.
Lacks: accounts, saved history, notes, payments, usage limits per person, a drafting editor, voice and Hindi input, a live real-steps display, a research page, an admin area, a modern interface, a privacy notice, a measured error rate.

## 3. What the pinned Streamlit (1.58.0) can and cannot do (checked 2026-10-20 by importing it)
Can: `st.login` / `st.user` (OpenID Connect, e.g. Google; needs the Authlib package and secrets), `st.chat_input`, `st.chat_message`, `st.write_stream`, `st.status` (a live steps display), `st.audio_input` (voice), `st.file_uploader`, `st.navigation`, `st.dialog`, `st.connection`. Not installed yet: Authlib, a Postgres driver. Not tried live: it needs Google OAuth credentials.
Cannot, [Likely]: receive Razorpay's payment webhooks (Streamlit does not host webhook endpoints), serve search-friendly public pages, or reach a polished mobile-first design. So payments need a small separate service anyway, which is the seed of Stage 2 (the exception already agreed: if payments prove unworkable inside Streamlit, Stage 2 comes sooner).
Consequence: a large part of the TathyaGrid experience (login, chat layout, live steps, voice, upload, history) can be had INSIDE Streamlit first, at a fraction of the cost of a new front end.

## 4. The target product (end to end)
Front end: home with the question box and example queries; chat with streaming answers; an honest steps panel (the real scope check, the Act found, the sections used, the checks run); a sources panel with tier labels; the grey official-text boxes; copy and export (PDF, Word); history and search; notes; research page (judgment search, case pages with the register's flags); drafting studio; upload; voice; Hindi and English; settings and billing; admin; phone-friendly, accessible, dark mode.
Back end: one API service wrapping the engine, with streaming, per-person quotas, background jobs (drafting, document reading), rate limits, one set of accounts for the website, WhatsApp and the lawyers' tool.
Data: Postgres (users, chats, messages, notes, drafts, subscriptions, usage, feedback, audit); vector data for the Acts and judgments; file storage; backups; retention and deletion rules.
Accounts: Google sign-in plus phone or email codes; roles (user, lawyer, reviewer, admin); a limited anonymous trial.
Payments: Razorpay subscriptions with UPI autopay, plans and quotas, GST invoices, refunds, failed-payment handling, coupons.
Documents: upload, reading scanned Indian-language papers, virus checks, defence against instructions hidden in files.
Trust and safety: disclaimers, emergency legal-aid help for arrests, refusal rules, abuse limits, red-team tests.
Quality: the lawyer-marked question set and first measured error rate, "report an error" in the product, weekly sampling (the support-and-fit plan, `SUPPORT_AND_FIT_PLAN.md`, is its first step and is still parked).
Law and compliance (a lawyer's job): data-protection law (consent, notice, deletion, minors: POCSO questions), privacy policy and terms, Bar Council rules on advice versus information, GST and Razorpay KYC, licences for the judgment data (CC-BY, attribution) and India Code, the Indian Kanoon API terms, a company and the "Recourse" trademark.
Operations: staging and production, tests before every release, error and uptime alerts, logs without personal data, secret rotation, backup restore drills, status page, support inbox, cost dashboard.
Growth: consent-respecting analytics, onboarding, reviewed explainer pages for sections, partnerships with legal-aid bodies.

## 5. The phases (each ends with its tests, the owner's staging test and a lawyer's sample)
- **Phase 0, launch readiness on the current site (now):** Mr. Advocate reads the answers and the Act texts (`acts/ACT_SHELF_SHEET.docx`); a lawyer drafts the privacy notice and terms; the first measured error rate (needs the support-and-fit plan's approval); `SCI_SEARCH_MODE` back to `shadow` and a higher `DAILY_BUDGET_INR` before the site is shared; the WhatsApp fix (`WHATSAPP_PLAN.md`, on hold).
- **Phase 1 = Stage 1 (trigger: the owner wants paying or tracked users):** inside Streamlit: Postgres on Railway; Google sign-in with `st.login`; saved chats and notes; per-person quotas from the existing cost log; consent screen and "delete my data"; a small separate billing service for Razorpay webhooks.
- **Phase 2 = Stage 2 (trigger: website, WhatsApp and the lawyers' tool need one set of accounts, or earlier if payments need it):** the engine behind a FastAPI service with streaming of the real steps, quotas and background jobs; the website and WhatsApp both call it.
- **Phase 3 = Stage 3 (trigger: users complain about the interface, or the lawyers' module needs what Streamlit cannot do):** the new Next.js front end: chat, steps panel, sources panel, official-text boxes, notes, history, billing, admin, installable on phones.
- **Phase 4:** drafting studio and document upload ("ask about my papers").
- **Phase 5:** voice, Hindi and regional languages, the research page, lawyers' features.
- **Phase 6:** scale, polish, growth pages.
Effort: [Guessing] weeks for Phase 1 and months for Phases 2 to 3 for one person with Claude; Claude cannot run the live model in the sandbox, so every phase leans on the owner's staging tests.

## 5b. Revised order after decision 5 (new front end first; the current Streamlit site stays live until the new one is as good, then the domain is switched)
- **A. Foundations (the engine service and the data):** FastAPI wrapping `chat_assistant.py` (streaming of the real steps, one `/ask` for the website and WhatsApp, quotas); Postgres (users, chats, messages, notes, usage, plans, subscriptions); Google sign-in done in the API; the entitlements table; privacy notice and consent; delete-my-data. Acceptance: the same questions give the same answers as the Streamlit site on the 3 production questions of 2026-10-20 plus the 50-question set when it exists; every existing test still passes.
- **B. The new front end (Next.js):** home, chat with streaming and the steps panel, sources panel, official-text boxes, copy and export, history and notes, settings. Acceptance: the owner's staging test and a lawyer's sample.
- **C. Billing:** Razorpay subscriptions, plans and quotas from the entitlements table, GST invoices, webhooks in the API.
- **D. Drafting studio and documents; E. voice, Hindi, research page, lawyers' features; F. cut-over, WhatsApp onto the same API, scale and growth.**
Each phase ends with the full test suite, the owner's staging test and a lawyer's sample; the old site is the way back until phase F.

## 6. Money
Measured cost per answer from the production logs (2026-10-20): Rs 2.7 to 4.6 for a layman answer, Rs 8 to 13 for a lawyer note. A plan that allows 100 answers a month costs Rs 300 to 1,300 in model fees alone; quotas, a cheaper model for easy questions and the answer cache are the levers. Infrastructure at the start is small (Railway services, a managed Postgres, storage). Legal work (privacy policy, terms, compliance) is a real cost that has no code workaround.

## 7. What not to copy
The steps panel must show the real steps, not theatre. A banner that covers the chat is poor design. "Legal Opportunities" and "Referral Invites" (a job-board and recruiting side) are a different business. No copying of another product's branding, wording or screens.

## 8. Decisions (owner's answers, 2026-10-20)
1. Main user: BOTH the public and lawyers (lawyers need legal research and drafting). One product, two modes, as the Layman/Lawyer switch does today.
2. Subscription model; the price is to be decided later. So plans, quotas and prices must be configuration, not code (an entitlements table from day one).
3. The owner will build, "anytime I am ready": Claude builds with him when he says go; nothing starts before that.
4. Budget: depends on the kind of build (rough bands in section 6 and in the 2026-10-20 reply: small monthly infrastructure, a one-off legal bill, model fees by usage; all [Guessing]).
5. A NEW FRONT END first (not accounts inside Streamlit). Claude had recommended Streamlit first; the owner's decision stands. Consequence: Phase 1 (login and billing inside Streamlit) is skipped; accounts, database, billing and quotas are built once, in the new stack (section 5b).
6. Brand: Claude advises keeping "Recourse" (meaningful, short, the tagline works, the domain and the WhatsApp app name already use it) after a trademark search by a lawyer (a common legal word is a weaker mark; classes for software and legal-information services) and securing nearby domains. Not decided by the owner yet.
Still open: the first step of the support-and-fit plan (the lawyer-marked question set), which gates any claim about accuracy; where the new code lives (a new repository is cleaner than folders inside Recourse, whose `railway.json` and `main` already drive the live website).

## 9. Risks
The interface is the easy part; trust is the hard part (no hallucination rate measured: never call the tool accurate or safe). The Indian legal-AI market has several established tools (a search found NyayAssist, Juristbot AI, Lexlegis.ai, CaseMine, Lawttorney.ai in listings, mostly promotional; none verified here). Data-protection law applies the day accounts exist. A full rebuild discards tested behaviour; the staged path avoids that.
