# Follow-ups (kept here because the working environment has no persistent memory)

Last updated 2026-10-05. Each item says what it is, why it waits, and what to do.

## 1. Monthly refresh of the bucket text (cloud routine) - decide after the good-law checker is reviewed
- What: a routine that, each month, lists the open bucket, downloads judgments added since the last run, extracts the text and pushes it to `claude/sci-bucket`, then updates the checker's data. `BUCKET_RUNBOOK.md` and `sci_bucket.py` already work this way for one run.
- Why it waits: (a) a routine session starts from `main`, and `sci_bucket.py`, the checker and the runbooks are only on `claude/sharp-euler-unyfv0`; merging to `main` is the owner's decision (no PR has been opened); (b) the routine needs an environment that can reach the bucket (`sci-index` can); (c) the checker should be reviewed first, so the routine refreshes something the owner trusts.
- Evidence for the cadence: the bucket is added to in small batches. Its 2026 folder holds 214 judgments added in June, July and August 2026, and its metadata was last written 2026-08-30. A monthly check (a listing of about 80 small requests) is cheap.
- To do: merge decision; create the routine (cron, one session, `BUCKET_RUNBOOK.md` steps plus the checker's refresh step); test it once with a TEST note like the crawl's; keep a STOP file as the kill switch.
- Reminder set for 2026-10-12.

## 2. Open items from earlier (unchanged)
- Serve the original Supreme Court PDF to Recourse users from the crawl's IDs (`api.sci.gov.in/jonew/judis/<id>.pdf`): plan was link-only first, live test from Railway, then fetch-and-send, then add the roughly 5,968 crawl judgments the catalogue lacks. The crawl kept no PDFs (text, size and sha256 only); the court's server is blocked from cloud sessions.
- IK "Cited by" numbers for Rangappa (https://indiankanoon.org/doc/150051/) and Bhajan Lal (https://indiankanoon.org/doc/1033637/), read by hand, to compare with our counts (12 and 237 in the crawl).
- Authority workbook, `Judgments` sheet (is each case still good law) is blank; the checker's output is meant to feed it for human review.
- Email Indian Kanoon about licence/API terms before relying on its API.
- Answer-key privacy (`review_data/pool_all.json`), Q06 question wording fix before any re-run, J's Q07 to Q12 replies, S's top-up replies: still open.
