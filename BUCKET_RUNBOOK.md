# BUCKET RUNBOOK: one download session (read and follow exactly; this may be an unattended run)

Purpose: fetch the open Supreme Court bucket's PDFs named in `coverage/bucket_match/worklist.csv.gz`, extract their text, and save it block by block on the branch `claude/sci-bucket`. The saved shard files are the ledger, so it is always safe to stop and safe to run again. Code lives on `main` (your current checkout); data lives on `claude/sci-bucket`, attached as a separate folder `../recourse-sci-bucket-data`. NEVER merge or rebase between the two branches. PDFs are held in memory and never written to disk. Only text and metadata are saved.

The bucket is public (s3://indian-supreme-court-judgments, CC-BY-4.0, Dattam Labs) and needs no key. The session's environment must be allowed to reach `indian-supreme-court-judgments.s3.ap-south-1.amazonaws.com` (the `sci-index` environment can).

The task names the scope: `after` (7,125 judgments dated after 4 May 2017), `none` (4,833 older judgments the crawl seems to lack, fetched so their texts can be compared with the crawl's), or REFRESH (judgments added to the bucket since the last run; see the end). `after` and `none` are finished.

## Hard rules
- Never change any code file. Never push any branch except `claude/sci-bucket` (the script does it).
- If a command is refused or blocked (a permission message, a 403 or 429 for the bucket, "access denied", an environment network block), STOP and report the exact text. Do not retry it, do not look for a way around it.
- Run only the commands below. Do not start any other session or call any routine or API yourself. Do nothing else.

## Steps
0. `git fetch origin` then `python sci_bucket.py active-check`. If it prints `ACTIVE`, another session is already running: report that and STOP.
1. `pip install -q pymupdf`
2. `python test_sci_bucket.py`  (must end with ALL PASSED; otherwise STOP and report the failing lines)
3. `python sci_bucket.py init --data-dir ../recourse-sci-bucket-data`  (attaches the data branch; creates it empty the first time)
4. SHIFT 1, as one command with a 60-minute (3600000 ms) timeout:
   `python sci_bucket.py shift --scope <scope> --data-dir ../recourse-sci-bucket-data --minutes 50 --workers 8`
5. Look at the "Reason:" in its output. Continue to the next shift ONLY if it starts with "time budget used up". If it starts with "completed all pending blocks" or "nothing left to do", the scope is finished: stop running shifts and say so. For any other reason (stopped inside block, push failed, STOP file, internal error...), stop running shifts and report the exact reason.
6. SHIFT 2 and then SHIFT 3: run the identical command from step 4 again (60-minute timeout each), applying the same check from step 5 after each one.
7. `python sci_bucket.py status --data-dir ../recourse-sci-bucket-data`
8. Report in at most 8 lines: blocks done and ok/missing/error counts for each shift, the stop reason of each shift, and the status lines from step 7.

## If the task says REFRESH (judgments added to the bucket since the last run)
The bucket gains judgments in small batches (its 2026 folder was filled in June, July and August 2026). A refresh finds what is new and downloads only that. Same hard rules as above.
0. `git fetch origin` then `python sci_bucket.py active-check`. If it prints `ACTIVE`, STOP.
1. `pip install -q pymupdf pyarrow`
2. `python test_sci_bucket.py` and `python test_bucket_refresh.py` (both must end with ALL PASSED; otherwise STOP and report).
3. `python sci_bucket.py init --data-dir ../recourse-sci-bucket-data`
4. `python bucket_refresh.py plan --data-dir ../recourse-sci-bucket-data`. It prints `PLAN: ...`. If it says nothing is new, report that and STOP. Otherwise note the `scope:` and `work list:` lines it prints (a scope looks like `refresh_20261005`).
5. SHIFT (one command, 60-minute timeout), using that scope and work list:
   `python sci_bucket.py shift --scope <scope> --worklist <work list> --data-dir ../recourse-sci-bucket-data --minutes 50 --workers 8`
   Apply the step 5 check above ("time budget used up" means run it again, up to three shifts).
6. `python sci_bucket.py status --data-dir ../recourse-sci-bucket-data` and report in at most 8 lines: what the plan found, blocks done and ok/missing/error counts, the stop reason, the status lines.
The planner treats every file path in `coverage/bucket_match/registry.csv.gz` and in earlier refresh work lists (kept on the data branch under `state/worklists/`) as already known, so each run downloads only what is new.

## Kill switch
If a file named `STOP` exists in the data folder (branch `claude/sci-bucket`), the script stops before fetching anything. Check: `ls ../recourse-sci-bucket-data/STOP`. That is intended; just report it.

## What the script guarantees
It pins the work list's hash on the first shift and refuses a different work list afterwards; saves each finished block (250 judgments) immediately and pushes it before starting the next; discards and redoes a block that hit a network failure; records a file that is not in the bucket as `missing` and a file that is not a readable PDF as `error` (each is counted in the shard's name); keeps the PDF's sha256 and size so a later re-fetch can be checked against what the text came from; and never writes a PDF to disk.

## Saved record (one line per judgment in `shards/<scope>-<NNNN>.ok<k>.miss<m>.err<e>.jsonl.gz`)
Bucket metadata (title, parties, decision date, law-report citation, neutral citation `case_id`/`nc_display`, judge, how it was disposed of, bucket file name), `bytes`, `sha256`, `pages`, `scan_pages` (pages that carry an image, so a scanned PDF shows up), `producer`, `text_chars`, the raw `text` (pages joined by form feeds), and `body_start` / `body_marker` where the court's own judgment seems to begin (after the law report's headnote). `sci_bucket.clean_text(record)` returns reading text: headnote cut, margin letters, page numbers and running headers dropped. The saved text itself is never edited.
