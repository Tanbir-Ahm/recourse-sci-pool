# Follow-ups (kept here because the working environment has no persistent memory)

Last updated 2026-10-05 (checker built and measured). Each item says what it is, why it waits, and what to do.

## 1. Monthly refresh of the bucket text (cloud routine) - decide after the good-law checker is reviewed
- What: a routine that, each month, lists the open bucket, downloads judgments added since the last run, extracts the text and pushes it to `claude/sci-bucket`, then updates the checker's data. `BUCKET_RUNBOOK.md` and `sci_bucket.py` already work this way for one run.
- Why it waits: (a) a routine session starts from `main`, and `sci_bucket.py`, the checker and the runbooks are only on `claude/sharp-euler-unyfv0`; merging to `main` is the owner's decision (no PR has been opened); (b) the routine needs an environment that can reach the bucket (`sci-index` can); (c) the checker should be reviewed first, so the routine refreshes something the owner trusts.
- Evidence for the cadence: the bucket is added to in small batches. Its 2026 folder holds 214 judgments added in June, July and August 2026, and its metadata was last written 2026-08-30. A monthly check (a listing of about 80 small requests) is cheap.
- To do: merge decision; create the routine (cron, one session, `BUCKET_RUNBOOK.md` steps plus the checker's refresh step: after new text is pushed, rebuild the store (`sci_goodlaw.py build`, about 15 minutes, 2 GB) and re-run `batch` on `goodlaw/targets/priority.json`); test it once with a TEST note like the crawl's; keep a STOP file as the kill switch.
- Reminder set for 2026-10-12.

## 1b. Checker: what is still open after the first build
- Lawyer-checked sample: 100 to 200 cases, half recent, is the one thing that would let anyone call the checker validated. Until then every output carries "pattern-rule reading, not lawyer-validated".
- The 20 known cases (`goodlaw/targets/known.json`) were labelled by me from general knowledge, not checked by a lawyer.
- Held-out half: run once at commit `bb77a5e` (see `goodlaw/EVALUATION.md`). Seven bugs fixed afterwards are not measured on it. Further rule changes should be tested on a freshly drawn half, not on that one again.
- Known weaknesses in the rules (from the hand-scored held-out readings): a headnote list where the cue belongs to the neighbouring case; a case named as the authority in a sentence that judges something else; hypotheticals and counsel's contentions in the Court's own narration. Overrulings stated away from the case's name (the next paragraph, or "that view") are mostly missed.
- Nothing measures 2018 to 2026 text beyond the 20 known cases; the reporters' citator stops at about 1985.
- High Court treatment is invisible; the IK API (priority cases and 2025 to now) is the planned way to add it, through Recourse's pipeline.
- `NO_ADVERSE_FOUND` plus the coverage block is the honest reading; the collection lacks about 40% of IK's 1968 to 1999 list and a quarter of 2018 to 2025.

## 1c. Wire the bucket text into the crawl, embed it, and connect the big index to the site - decided later (owner's decision, 2026-10-05)
- Decision recorded: do this later, not now. Order the owner gave: (1) wire the bucket text (`claude/sci-bucket`, 2017 to 2026) into the crawl pipeline so the indexer reads both; (2) embed it; (3) connect the big index (`claude/sci-index`) to the Recourse site so users are shown these judgments too.
- State today (checked 2026-10-05): the big index holds only crawl judgments, criminal-law only: 8,102 judgments embedded (153,981 passages), only 118 of them from 2017, none from 2018 to 2026. `sci_index.py status` prints `docs_embedded: 36,928`, which is judgments *processed* (26,760 non-criminal, 656 duplicate, 1,275 short and 135 near-duplicate were skipped); the real embedded count is 8,102.
- The big index is not connected to the Recourse site (no reference to it in the Recourse code checked on 2026-09-29; the deployed site was not inspected). The site searches a core library of 42 hand-checked judgments and a pilot pool of 16 hand-checked cases, with at most a handful from 2018 onward.
- What it will take: the indexer (`sci_index.py`) must read the bucket shards (use `sci_bucket.clean_text()` and `body_start`), keep the criminal-law filter or decide otherwise, and spend embedding tokens (rough guess 9 to 15 million for the 2018 to 2026 criminal judgments; not checked against the current Voyage allowance, which the live site shares). Recourse's own rule applies when connecting: a less-reviewed pool goes in as a separately labelled tier with a stricter similarity bar (see `pilot_tier_search.py` in the Recourse repo).
- Independent of the good-law checker, which already reads crawl and bucket text together in its own store.

## 2. Open items from earlier (unchanged)
- Serve the original Supreme Court PDF to Recourse users from the crawl's IDs (`api.sci.gov.in/jonew/judis/<id>.pdf`): plan was link-only first, live test from Railway, then fetch-and-send, then add the roughly 5,968 crawl judgments the catalogue lacks. The crawl kept no PDFs (text, size and sha256 only); the court's server is blocked from cloud sessions.
- IK "Cited by" numbers for Rangappa (https://indiankanoon.org/doc/150051/) and Bhajan Lal (https://indiankanoon.org/doc/1033637/), read by hand, to compare with our counts (12 and 237 in the crawl).
- Authority workbook, `Judgments` sheet (is each case still good law) is blank; the checker's output is meant to feed it for human review.
- Email Indian Kanoon about licence/API terms before relying on its API.
- Answer-key privacy (`review_data/pool_all.json`), Q06 question wording fix before any re-run, J's Q07 to Q12 replies, S's top-up replies: still open.
