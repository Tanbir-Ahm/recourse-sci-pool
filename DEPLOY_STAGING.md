# Staging deployment, step by step (written 2026-10-13; nothing here has been done on Railway)

**For a first-timer on the Hobby plan, use `DEPLOY_STAGING_BEGINNER.md` instead (same plan, every click spelled out). This file is the technical reference.** Hobby facts found 2026-10-13: memory about $10/GB/month, volumes $0.15/GB/month and up to 5 GB, private networking is IPv6 and only within one project and environment (so the website and the search service must be in the same project).

Everything Claude can do without your Railway account is done and tested (below). The steps marked **YOU** need your Railway and GitHub accounts. Railway's screens change; where I describe a screen from memory it is marked [Likely]. Nothing in this runbook touches production (`recourse.co.in`) until Part 6.

## What is ready
| Piece | Where | State |
|---|---|---|
| Website with the register locks, the cards, the WhatsApp notes and the search-tier client (off by default) | `Tanbir-Ahm/recourse`, branch `register-hooks-and-overlay` (head `efbefff`) | 64 of 64 free tests pass; real model never run on it |
| Search service (recipe B), names and links, index loader | `Tanbir-Ahm/recourse-sci-pool`, branch `claude/sharp-euler-unyfv0` | Tested; run end to end here: fetched the real index from GitHub in 27 s (640 files, commit `3c80a26`), started, answered a real question in 2.9 s with names and court links, refused a request without the token |
| Start command, packages, health check | `Procfile`, `railway.json`, `requirements.txt` in that repository | Written; not yet run by Railway |

## Part 1: a separate staging project (YOU, about 15 minutes)
1. Railway, **New Project** named `recourse-staging` (a separate project keeps production's variables and domain out of reach) [Likely: same plan and bill].
2. In it, **New Service, Deploy from GitHub repo**, `Tanbir-Ahm/recourse`, branch **`register-hooks-and-overlay`**. (Do not choose `main`.) If Railway asks which branch under Settings, Source, set it there.
3. Variables for this service (copy the two values from the production service): `ANTHROPIC_API_KEY`, `VOYAGE_API_KEY`. Nothing else is needed for the website; **do not copy the WhatsApp/Gupshup variables** (`GUPSHUP_*`, `WHATSAPP_*`): staging must never answer real WhatsApp messages. Leave `SCI_SEARCH_MODE` unset (= off) for now.
4. Settings, Networking: **Generate Domain** (a `*.up.railway.app` address). Do not attach `recourse.co.in`.
5. Wait for the first deploy; open the address; ask the five ordinary questions of Part 4. This tests the register patch alone, with the search tier off.

## Part 2: the search service (YOU, about 20 minutes)
1. Same staging project, **New Service, Deploy from GitHub repo**, `Tanbir-Ahm/recourse-sci-pool`, branch **`claude/sharp-euler-unyfv0`** (the service code is on this branch, not on `main`). Railway reads `railway.json` (start command, health check on `/health`, 15-minute allowance for the first start).
2. **Memory:** the service needs about 1.5 GB loaded and 1.8 GB at peak while loading. Choose a plan/limit of **at least 2 GB, 3 GB is safer** [Likely: under Settings, Resources]. I do not know your plan's limit; if it is below 2 GB the service will be killed while loading and you will see "out of memory" in its logs.
3. **Volume:** add a Volume of **2 GB** mounted at `/data` (the index is 540 MB; the loader needs it once).
4. **Variables:**
   - `SCI_INDEX_DIR=/data/sci-index`
   - `SCI_INDEX_REPO=Tanbir-Ahm/recourse-sci-pool` (optional: the default is this repository and the frozen index commit `3c80a26`, fetched as a public archive with no login; if you make the repository private, add a read-only token as `GITHUB_TOKEN`; `SCI_INDEX_SHA` selects another commit)
   - `VOYAGE_API_KEY` (same key as the site; the balance is shared, reserve $5)
   - `SCI_SEARCH_TOKEN` = a long random string (make one; keep it for Part 3)
   - `PORT=8080`
5. Deploy. On the first start the service downloads the index into `/data` (about 30 seconds here), loads it (about 40 seconds), and then `/health` answers. Later restarts reuse the volume.
6. **Do not give this service a public domain.** It is reached from the website over Railway's private network.
7. Check in the service's logs: a line like `sci-search listening on 0.0.0.0:8080; index 3c80a26e42, 238,762 passages`.

## Part 3: connect the website to it in shadow mode (YOU, 5 minutes)
In the staging **website** service, add variables:
- `SCI_SEARCH_URL=http://sci-search.railway.internal:8080` (name the service exactly `sci-search`)
- `SCI_SEARCH_TOKEN=` the same string as in Part 2
- `SCI_SEARCH_MODE=shadow`
- optional `SCI_SHADOW_LOG_FILE` is not needed (the website's logs hold the records). Leave `SCI_SHADOW_LOG_QUESTIONS` unset: the log then holds a hash of each question, not its text. Set it to `1` only on staging, for your own test questions.

Redeploy. In shadow mode a real answer is produced as before and, afterwards in the background, the question goes to the service; the website's log gets one line starting `SCI_SHADOW {...}` listing the 10 passages, the case names and links, and for each whether the register or a card flags it. **Users see nothing and wait for nothing.**

## Part 4: what to test on staging before anything else (YOU, or I read your logs)
1. **Five ordinary questions** (an arrest, a bounced cheque, a bail question, a section question, a "what does Section 318 BNS say"): the answers must look the same as on production. Compare side by side with `recourse.co.in`.
2. **Three questions naming a register case**: "Is Raj Deo Sharma v. State of Bihar (1999) still good law?", the same for Bilal Ahmed Kaloo v. State of Andhra Pradesh (1997) and Mohan Lal v. State of Punjab (2018). Expect: the answer says the case was overruled/reported to be overruled, and a box "Currency notes (checked by code, not by the model)".
3. **The kill switch**: set `REGISTER_HOOKS=off`, redeploy, repeat step 2: the box and the prompt facts disappear.
4. **Shadow log**: ask 10 ordinary questions, then in the website's logs search `SCI_SHADOW`; send me 10 lines (or the whole log) and I will read them: relevance, names, links, and how often a passage is flagged.
5. **The criminal exam** (you said after deployment): from your computer, `python site_patch/run_trap_exam.py --recourse <checkout of the staging branch> --out-dir exam_run_1 --limit 3`, then the full run. Costs Anthropic credit. Send me the folder.
6. **WhatsApp**: cannot be tested on staging without a separate WhatsApp test number. The WhatsApp formatter change is covered by tests only. Test it after production, with the switch ready (Part 6).

## Part 4b: feed mode (EXPERIMENT, staging only; added 2026-10-13)
`SCI_SEARCH_MODE=feed` gives the wider-search passages to the language model, so the answer itself may name and rely on those cases (the site's own pilot tier only allows a descriptive mention). Overruled cases carry a REGISTER FACT line, the page lists the passages the answer read (labelled not independently verified), and the post-answer register lock still runs. It exists to show what such answers look like. It is not a way to publish them: a lawyer must read these answers first. Never switch it on for production without that review.

Feed-mode rules (2026-10-13, after the first staging test): (1) when the register flags a case, the case that overruled it is always fed too (taken from the results, or fetched by a second search "<name> + the question"), so the model can name the controlling case; (2) one passage per case, up to 8 cases, the flagged case last, each excerpt cut at the end of a sentence; (3) every wider-search case named in the finished answer is tagged "(from a wider search, not independently verified)" by code, whatever the model wrote. The log line is `SCI_FEED fed N case(s): ...`. Re-test with the trial-delay question; the answer should name P. Ramachandra Rao, and each wider-search case should carry the tag.

## Part 4c: answer style v3, "The Adviser" and "The Research Note" (added 2026-10-14, owner-approved)
`RESPONSE_STYLE` picks the answer voice. It is read at every question, so changing it needs only a redeploy of the variable, not a code change.

| `RESPONSE_STYLE` | What users get |
|---|---|
| `v1` (default, and what production runs) | today's answers |
| `v2` | the first livelier prompt (tested 2026-10-14) |
| `v3` | the page shows a **Layman / Lawyer** switch above the box. Layman: the Adviser (opening answer, what the law says, how this cuts for and against you, 2-4 steps). Lawyer: the Research Note (bottom line, facts assumed, numbered issues, application to the facts, grounds that can be urged, gaps and checks) plus a **table of authorities built by code** in two tiers (reviewed library; wider search, not independently verified). WhatsApp always gets the Adviser, in 4-5 short messages. |
| `v3-lawyer` | the Research Note for everybody, no switch (for testing) |

Safety valves: set `RESPONSE_STYLE` back to `v1` (or delete it) to return to today's answers; the hard rules, the register locks and the post-answer checks are the same in every style.
Things that behave differently under v2/v3 (by design): the human-approved answer cache is not used (it holds v1 wording, written for laypeople); the "Right now" opening that situation detection relied on is replaced by the heading "What you can do right now" (and v2's later "Right now" heading), which the code now also recognises; bold is used only for headings and case names are in italics, because the page's style sheet turns any paragraph whose only styled part is bold into an upper-case sub-head.

How to test on staging (change nothing else): add `RESPONSE_STYLE` = `v3` to `staging-site`, wait for the deploy, then ask these and compare with the earlier v1/v2 answers:
1. "My trial has been going on for 9 years and the prosecution keeps asking for time. Can the case be closed because of the delay?" (Layman, then Lawyer)
2. The Section 318 cheating question
3. The cheque bounce question
4. The Mohan Lal situation question (check the register note still appears)
5. A frightened arrest question ("My brother was taken by the police last night and nobody tells us anything")
6. A question that uses legal terms ("Can I seek default bail under Section 187 BNSS if the chargesheet was filed on day 91?")
7. and 8. Two lawyer-style questions with the switch on Lawyer (one on delay, one on anticipatory bail conditions)
Check: the first sentence answers the question and uses your facts; headings are plain and not shouted; steps start with a verb; case names are in italics; no SCC/AIR number appears unless the sources box has it; in Lawyer mode the "Authorities" tables appear under the note with the right tier; the register note and the "Not checked by us" line still appear; a wider-search case (feed mode) carries "(from a wider search, not independently verified)" after its name, outside the italics.

## Part 4d: what one question costs (added 2026-10-14)
The site prints two kinds of line to the Deploy Logs: `COST_CALL {...}` for every model, embedding or re-rank call, and `COST_QUESTION {...}` once per question with every call, the total in dollars and rupees, the style and the audience. Search the logs for `COST_QUESTION`. The question appears only as a short hash. These are measured from the tokens each call really used, so they are the exact figures; the table in `FOLLOW_UPS.md` item 0g is only a forecast.
Optional variables on the site service: `USD_INR` (rupees per dollar; default 96.5, set the real rate), `PRICES_JSON` (override a price, e.g. `{"claude-sonnet-5": [2, 10]}`; Voyage models take one number). A call to a model with no price is flagged `unpriced`, never guessed.
The search service now also returns the tokens each search used (`usage`), so the Voyage part is exact too (a service restart of about 40 seconds follows each deploy).

## Part 5: show mode (later, only after a lawyer has read shadow logs)
`SCI_SEARCH_MODE=show` on staging puts a box "More Supreme Court judgments that may be relevant (a wider search; not independently verified)" under the answer, with names, dates, paragraph, the court/bucket link, and the register note beside any flagged case; judgments with no readable name are left out. Look at it yourself on staging first.

## Part 6: production (only when you decide; each step reversible in seconds)
1. Before merging, in the **production** website service set `REGISTER_HOOKS=off`.
2. You (or you tell me in so many words to) merge `register-hooks-and-overlay` into `main` of `Tanbir-Ahm/recourse`. I will not merge without that instruction. If the WhatsApp bot service also deploys from `main`, it redeploys too [Likely].
3. Confirm the site and one WhatsApp message behave exactly as before. Then set `REGISTER_HOOKS=on` (delete the variable or set `on`), and repeat Part 4 steps 1 and 2 on production, including a WhatsApp message. Watch it for a day.
4. Search tier in production: not before Part 5 has been reviewed. Add the search service to the production project the same way as Part 2, then `SCI_SEARCH_MODE=shadow` first.
5. Instant switches: `REGISTER_HOOKS=off`; `SCI_SEARCH_MODE=off`; on the service, `SCI_SEARCH_ENABLED=0`.

## What to watch (cost and memory)
- **Memory** of the search service is the main cost; check Railway's usage page after a day. [Guessing] it is the largest line.
- **Voyage:** about 0.1 cent per search; the service stops itself at 5,000,000 re-rank tokens a day (about 230 questions, about a quarter of a dollar).
- **Volume:** 2 GB.

## Known gaps
The answer PDF does not carry the currency notes. WhatsApp shows the notes but not the search tier. The lawyers' module does not exist yet. The case-name table has 68 unnamed judgments and a 150-row sample no person has checked. The index ends 13 July 2026.
