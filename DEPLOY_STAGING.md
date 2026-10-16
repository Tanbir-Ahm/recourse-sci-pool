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

## Part 4e: grounding checks and the four cost switches (added 2026-10-14)
Every variable below is optional and defaults to today's behaviour. Change ONE at a time on `staging-site`, then ask the same questions and read the `COST_QUESTION` / `GROUNDING_CHECK` lines in the Deploy Logs.

| Variable | Values | Default | What it does |
|---|---|---|---|
| `GROUNDING_CHECKS` | `off`, `log`, `warn`, `enforce` | `log` | The citation check (a case named in the answer that is not in the sources the model was given) and the quote check (words in quotation marks, five words or more, that are not in those sources). `log`: only a `GROUNDING_CHECK` line in the log. `warn`: also a notice under the answer ("Checked by code against the sources we read"). `enforce`: also asks the model once more with the problem named, and withholds the answer if a case found nowhere (not in the sources and not in the site's Supreme Court list) is still in it. |
| `ANSWER_EFFORT` | `low`, `medium`, `high`, `xhigh`, `max` | unset (the model's own default) | How hard the answer model thinks. Thinking is billed as output, so `medium` or `low` is the biggest saving. Needs a read of the answers: ask the 8 test questions at `medium`, compare with the earlier answers and the `COST_QUESTION` totals. If the API refuses the setting it is dropped automatically. |
| `SCOPE_MODEL` | a model id, e.g. `claude-haiku-5-5` | unset (Haiku 4.5) | The model for the scope check (the cheap routing call; its prompt is 16,000 characters). A Haiku 5 model is told not to think. On any error the default Haiku 4.5 is used. Check that the in-scope / out-of-scope decisions still look right on 10 questions. |
| `PROMPT_CACHE` | `on` (5 minutes), `1h` | unset | Caches the fixed rules at the start of the answer prompt. Pays only when the same prompt is used again within the window: below about one question every 5 minutes it costs a little more. Test: ask two questions within 5 minutes and look for `cache_read` in the second `COST_CALL`. |
| `DAILY_BUDGET_INR` | a number of rupees | unset (no limit) | From 80% of the limit (`DAILY_BUDGET_SOFT_PCT`) answers run at low effort; at the limit the site answers "Daily limit reached" and calls no model until the next Indian day. `COST_STATE_FILE` (a path on the `/data` volume, e.g. `/data/cost_state.json`) keeps the day's total across restarts. |

Suggested order: (1) leave `GROUNDING_CHECKS` at `log`, ask 10 questions, search the logs for `GROUNDING_CHECK`: each line is a case or quotation the check would flag (a false alarm shows here before any user sees it); then try `warn`, then `enforce`. (2) `ANSWER_EFFORT=medium`. (3) `SCOPE_MODEL=claude-haiku-5-5`. (4) `PROMPT_CACHE=on` once there is steady traffic. (5) `DAILY_BUDGET_INR=50` plus `COST_STATE_FILE` as a safety net before the site is public.
Not covered by these checks: what a wider-search case actually held (the model can still overstate it), the reasoning, and the "what you can do" steps.

## Part 4f: the controlling case, the "not checked" sentence and verbatim excerpts (added 2026-10-14, after the owner's "go")
Recourse branch `register-hooks-and-overlay`. Redeploy `staging-site` from the branch (it does so on a push), then:

1. **Controlling case (feed mode, nothing to set).** When a passage the search fed to the model merely NAMES a case on the Overruled Register (Raj Deo Sharma, Common Cause, Mohan Lal ...), the passage now carries the REGISTER FACT line and the case that corrected it (P. Ramachandra Rao) is added, fetched by a second search if it was not among the results (at most 2 such searches per question, never twice for one name). Look for: Deploy Logs `SCI_FEED passages naming register cases: ...`; in the box "Supreme Court passages from a wider search" the line "This passage names a case on our register: ...". A name is found by a reported citation, by both party names with a year, or by its first party's three-plus distinctive words followed by "(I)", "(II)", "case" ("the Raj Deo Sharma case") -- a bare two-word name such as "Mohan Lal" is never matched this way. Measured offline on 46 real passages that name Raj Deo Sharma: 43 found (the other three: the judgment's own header, and two passages with both party names but no year or citation, which the register treats as weak on purpose).
2. **The "not checked" sentence (nothing to set).** Cases the wider search supplied (feed mode) and the cases of the verbatim excerpts (below) are no longer listed in "Cases named in this answer that we have not checked": they carry their own bracketed label. Also fixed on the way: the sentence could show "Code. In Ram Prasad v. State of Bihar" when a sentence ended in a capitalised word.
3. **Verbatim excerpts: `ANCHORS=on` (default `off`; set it on `staging-site` only).** For a question about delay in a criminal trial the prompt gets two Supreme Court passages copied word for word from the court's own PDFs: P. Ramachandra Rao v. State of Karnataka (2002), the seven-judge Bench (its concluding propositions: no fixed outer time limit, but Article 21, the Antulay guidelines, the trial court's powers and the High Court route) and Hussainara Khatoon (I) (1979) (speedy trial is part of Article 21). Each passage was checked by a program against the court's PDF (`sci_anchors.py verify`); a person has NOT yet confirmed them, so the answer says "(verbatim excerpt, not yet confirmed by our reviewer)" after the case name, a box under the answer lists the passages with the court's link, and the lawyers' table of authorities has a third tier. Ask the delay question in both modules and look for: the log line `ANCHORS handed over: ...`; Article 21 and the High Court route in the answer; the label; the box. Extra cost on a matching question: about 1,700 more input tokens, about Rs 0.3. It applies only to questions it recognises as about delay in a trial (an explicit "speedy trial", "time limit for trial", Article 21 with delay, or a trial/case that is "going on", "dragging" or adjourned for years); a delay in filing an FIR or an appeal is not one, nor is a sentence of 7 years. If a question you expected it for gets nothing, send me the question: the recognition is plain patterns and is meant to be widened with real examples.
   **Confirming them:** send `anchors/ANCHOR_SHEET_trial_delay.docx` to Mr. Advocate. When Mr. Advocate has answered, tell me (and what was changed); I record it with `sci_anchors.py confirm`, export, push, and the "not yet confirmed" wording goes for the anchors that were confirmed.
   Switch off at any time: `ANCHORS=off`.

## Part 4g: the topic bar, `SCOPE_GATE` (added 2026-10-16, owner's instruction "the site should accept all topics now"; Recourse branch `register-hooks-and-overlay`, `9ea94bb`)
**What the bar was, corrected.** On the website the questions about cheque bounce, a frozen bank account, domestic violence and NDPS (drug) offences are ALREADY answered (`recourse_app.py` passes `inline_domains`). The situation exam runs 1 to 3 showed the NDPS questions as refusals only because the exam runner did not pass those four domains (fixed in the runner on 2026-10-16). The questions the site really turns away are the ones the classifier calls `adjacent_uncovered`: special laws (TADA, the Prevention of Corruption Act, POCSO, UAPA), and civil, family, tax, service and company matters. A question that is not a legal question at all (`unrelated`) is also turned away and stays so.

**The switch.** `SCOPE_GATE=open` on a website service lifts that bar. Unset, or anything else, is today's behaviour. What `open` does: such a question goes through the same steps as any other (curated anchors, library search, the register, every check); the prompt gets a short scope note (do not refuse for this reason; say plainly what the material does not cover; the Hard rules are untouched); the answer carries a fixed notice written by code ("This question is about an area Recourse has not checked in depth ... confirm it with a lawyer ..."); and one log line `SCOPE_OPEN {"q": hash, "reasoning": ..., "state": ..., "wider_only": ...}` per opened question. If the library finds nothing AND `SCI_SEARCH_MODE=feed`, the answer is written from the wider-search passages alone (`wider_only: true`); with the search off or in shadow mode, a question with nothing in the library ends as "Not enough to go on yet" (`no_match`), which is what an ordinary question with no match gets.
**What it cannot do.** The library has no TADA, corruption-law or civil material. An opened question is answered from the wider Supreme Court search (feed mode) or not at all; in either case the answer rests on passages nobody at Recourse has read. [Likely] many answers will say "I don't have information on ..." and some will be thin; [Guessing] a few may be wrong in ways only a lawyer would see. No rate has been measured. Cost: a turned-away question cost Rs 0.44; an opened one costs about Rs 3 to 8 (up to about Rs 13 with a retry).

**Test it on `staging-site` first (YOU):**
1. Set `SCOPE_GATE` = `open` on `staging-site` (and keep `SCI_SEARCH_MODE=feed` there). Wait for the redeploy.
2. Ask the TADA question and the corruption-trial-stay question (they are S03 and S23 in the situation exam). Look for: an answer instead of "Recourse can't help with this one"; the grey notice above the answer; the Deploy Logs line `SCOPE_OPEN` with `"state": "single_match"`; and, in feed mode, the box of wider-search passages under the answer.
3. Optional, on your PC (about Rs 150): `$env:SCOPE_GATE="open"`, then the situation exam as before into `exam_run_4`. The runner now calls the assistant like the website does. [Certain] On your PC the search is off (the search service's Railway address is internal and cannot be reached from outside), so most opened questions will end as "Not enough to go on yet" or as a thin library answer: that run tells you little about the live site. The staging site (search on) is the real test.
4. Only if the answers look acceptable to you and, better, to Mr. Advocate: set `SCOPE_GATE=open` on the production website service. To undo: set it to `on` or delete it (about a minute).
Watch the first day's cost: opened questions are about ten times dearer than the refusals they replace; the daily budget (`DAILY_BUDGET_INR`) still applies.

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
