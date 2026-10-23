# The new front end (Next.js), built 2026-10-23 (task D; owner's "Go straight to D")

**What exists:** a new web front end in its own project `recourse-web` (Next.js 16 App Router, TypeScript, React 19; no UI framework). It is NOT in a GitHub repository yet (the owner creates `Tanbir-Ahm/recourse-web`; until then the work is kept as a git bundle in `web_draft/recourse-web.bundle` of this repository). Nothing is deployed. The Streamlit site is untouched and stays the way back.

## What it does (screens)
- **Not signed in:** the home screen with the free trial (layman answers, three a day per device, kept on the page only, count shown) and the Google sign-in button.
- **Sign-in and notices:** Google sign-in (Google Identity Services), the "Before you start" screen (privacy notice, terms, age), draft-wording banner while the legal text is a placeholder.
- **Home (signed in):** choose "I need help" or "I am a lawyer", example questions, the question box with the day's remaining answers.
- **Conversation page:** live steps while the engine works (real events, not a fake bar), the answer, follow-up questions (up to eight per conversation), "Try again" after a dropped connection (same idempotency key, so no double charge), plain-words notices for every limit (`messages.ts`).
- **The answer:** drawn from the API's `view` (see below): label, the "more than one provision" note, outside-scope note, the answer box, Copy, Act notice, the section's whole official text, the lawyer's table of authorities, "Read the source" (statutes, judgments, paragraphs, currency caveats), judgments relied on, currency notes, code-checked notes, wider-search and verbatim-excerpt boxes with their "not independently verified" wording, other cases.
- **Under an answer:** Copy, Save to notes, It helped, Report a problem (kind + comment).
- **History sidebar** (slide-over on a phone): search, rename, archive and restore, delete (with a confirm), "Show archived". **My notes** (write, edit, delete, copy). **My data** (today's use, download everything as a file, delete the account by typing DELETE). Privacy and terms pages. Light, dark and "follow the device".

## How it is built (decisions in WEBSITE_DESIGN 17)
- The browser talks ONLY to the front end's own server, which forwards a short allow-list of API routes (`src/lib/forward.ts`, 16 routes plus the trial), rebuilds the request from a short list of headers, passes the session cookies back, streams the answer's events unbuffered, and vouches for the visitor's address with a shared secret (`FRONTEND_PROXY_SECRET`) so the API's per-address limits still see the real visitor. The API's address and the session token never reach the browser code.
- A strict Content-Security-Policy with a fresh nonce per page (`src/proxy.ts`).
- **The answer is drawn from `view`, built in Python** (`answer_view.py` in the Recourse repository, added to every ask reply and every saved message). The page's own rules (which sources are worth showing, how the bold labels become headings, what Copy copies) were copied into that module and a test (`test_answer_view.py`, 230 checks) takes the page's own functions out of `recourse_app.py` and compares output on the same inputs, so the two cannot drift apart unnoticed. The front end re-implements none of that logic.
- Rendering safety: markdown without raw HTML, no images, links only http(s) with `rel=noopener noreferrer`; the Act notice (engine-built HTML) is cleaned again with an allow-list (DOMPurify); a test feeds `<script>`, event handlers, frames and `javascript:` links and checks that nothing runs.

## What was run, and what it shows
| Check | Result |
|---|---|
| Front-end unit tests (Vitest): event-stream reader, forward allow-list and headers, API client, sanitizers, turn model, usage lines | 45 passed |
| TypeScript, production `next build` | clean |
| Recourse repo `test_answer_view.py` (parity with the page's helpers, rich/junk inputs, API carries `view`) and the API suites `test_api_ask`, `test_api_chats`, `test_api_health`, `test_api_me`, `test_refusal_text` | all passed (full-suite line below) |
| Browser tests (Playwright, Chromium, production build of the front end + the REAL API + a real throwaway PostgreSQL + a stand-in for Google's signing keys + a STUB engine): 17 tests on desktop and phone width | 17 passed |
What the 17 cover: health check and per-request nonce policy; the forward refuses `/api/debug`, `/api/ask`, `/api/health`; the trial (three answers, the fourth refused with its notice); sign-in, notices, reload keeps the session; a question with live steps, a follow-up folded into the person's earlier words (not our answers), reload shows the conversation; refusal in the shared words; an engine failure shows no exception text; a rich answer (sources, notes, safe links, no script runs, Copy puts plain text on the clipboard, Save to notes, Report, notes page); notes edit and delete; history search, rename, archive, restore, delete; a conversation is full after eight questions; download and delete the account; sign out and the public notice pages; no sideways scrolling, working menu and no WCAG 2 A/AA violations found by axe on the main screens at desktop and phone width and in dark colours; and in the rich-answer flow the browser console shows no Content-Security-Policy violation and no error except the one expected 401 of the first look at `/api/me` when nobody is signed in.
Four of the first run's failures were wrong test expectations (the stub echoes the folded question), one was a real defect found by the axe check (a group without a role carried an aria-label): fixed. One real test-harness defect: the first teardown left the old web server running on the port, so a rerun silently tested the OLD build; fixed (process groups are ended).

## What it does NOT show (say this, do not blur it)
- **Google sign-in was never run against the real Google in this front end.** The tests use a stand-in for Google's script and keys. Only the owner's staging test proves the real button, the Google console "Authorized JavaScript origins" entry and the cookie behaviour on Railway's addresses.
- **No real model answer was ever drawn.** The engine in all browser tests is a stub. Real answers have longer text, tables, odd markdown and all the notice combinations; the renderer is checked against hand-made results (including the real remand-answer shape) and by the parity test, not against live output. No hallucination rate has been measured; never call the answers accurate or safe.
- Runs on `localhost` only, never on Railway; the production build, the cookie names and the forwarded-address rule on Railway are the owner's staging test.
- Accessibility: an automated check (axe) on three screens in two colour modes. Not a full audit: no screen-reader test, no keyboard-only walk by a person, no contrast check of every state.
- The legal text is still a placeholder (gate G1): the screens say so; real people must not be asked to accept it.
- Plan numbers (daily limits) are still provisional (decision D7); payments are not built.
- The trial's closed/open state is not read from the API before the first question: a closed trial is discovered when the first question is refused (then the box is replaced by the sign-in card).
