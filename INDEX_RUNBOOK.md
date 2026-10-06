# INDEX RUNBOOK: one indexing session (read and follow exactly; this may be an unattended run)

Purpose: turn the crawled Supreme Court judgments (branch `claude/sci-pool`, read-only) into clean, tagged, embedded passages, saved block by block on branch `claude/sci-index`. The saved files are the ledger, so it is always safe to stop and safe to run again. Code is on `main` (your current checkout). The crawl data is attached as a read-only folder `../recourse-sci-pool-data`; the index branch is attached as `../recourse-sci-index`. NEVER merge or rebase between any of the branches. The task names one mode: TRIAL, FULL, EVAL, DEDUPE-PLAN, DEDUPE-APPLY, BUCKET-PLAN, BUCKET-TRIAL or BUCKET-FULL. The bucket modes also read the law-report text of 2017 on (branch `claude/sci-bucket`, attached read-only as `../recourse-sci-bucket-data`).

## Hard rules
- Never change any code file. Push ONLY the branch `claude/sci-index` (the script does it). Never push `claude/sci-pool`, `claude/sci-bucket` or `main`.
- Never print, echo, log, or write the value of `VOYAGE_API_KEY` anywhere. Never put it in a file or a command line.
- If a command is refused or blocked (a permission message, a 401/403/429, "allowance", "payment", a safety-classifier denial), STOP and report the exact text. Do not retry it, do not look for a way around it.
- Run only the commands below. Do not start any other session or call any routine or API yourself. Do nothing else.
- Do not run this at the same time as another indexing session (step 0 checks).

## Steps
0. `git fetch origin` then `python sci_index.py active-check`. If it prints `ACTIVE`, another indexing session is running: report that and STOP.
1. `git worktree add --detach ../recourse-sci-pool-data origin/claude/sci-pool`  (read-only view of the crawl; if that branch does not exist, STOP and report)
2. `pip install -q numpy voyageai`
3. `python test_sci_index.py`  (must end with ALL PASSED; otherwise STOP and report the failing lines)
4. `python sci_index.py init --index-dir ../recourse-sci-index`  (attaches the index branch; creates it empty the first time)
5. Check the key exists WITHOUT showing it: `python -c "import os; print('key present' if os.environ.get('VOYAGE_API_KEY') else 'KEY MISSING')"`. If it says KEY MISSING, STOP and report. (BUCKET-PLAN needs no key and spends nothing: skip this step for it.)
5b. Bucket modes only (BUCKET-PLAN, BUCKET-TRIAL, BUCKET-FULL, and DEDUPE-PLAN when the index already holds bucket judgments): `git fetch origin claude/sci-bucket`, then `git worktree add --detach ../recourse-sci-bucket-data origin/claude/sci-bucket` (read-only; if that folder already exists, reuse it; if the branch does not exist, STOP and report). Then check `ls coverage/bucket_match/none_resolution.csv.gz`: it lists the 3,084 bucket judgments the crawl already holds, and without it a bucket run would pay twice for them (the script refuses to run without it). If the file is missing, STOP and report.

### If the task says TRIAL (one block only, to measure and check)
6T. `python sci_index.py shift --pool-dir ../recourse-sci-pool-data --index-dir ../recourse-sci-index --minutes 20 --ceiling 1500000 --max-blocks 1 --pause 2.0`
7T. `python sci_index.py status --pool-dir ../recourse-sci-pool-data --index-dir ../recourse-sci-index`
8T. Report in at most 8 lines: the "Blocks done / docs / passages / tokens" line, the "Reason:" line, whether the push to `claude/sci-index` worked, the status line, and the files that now exist under `../recourse-sci-index/index/` (names and sizes). Then STOP. Do not run more shifts.

### If the task says FULL (the real run)
6F. SHIFT 1, as one command with a 60-minute (3600000 ms) timeout:
   `python sci_index.py shift --pool-dir ../recourse-sci-pool-data --index-dir ../recourse-sci-index --minutes 50 --ceiling 80000000 --pause 2.0`
7F. Look at the "Reason:" in its output. Continue to the next shift ONLY if it starts with "time budget used up". If it starts with "completed all pending blocks" or "nothing left to do", the job is finished: say so. For ANY other reason (token ceiling, allowance, refused, push failed, internal error, STOP file, stopped inside block...), stop running shifts and report the exact reason.
8F. SHIFT 2 and then SHIFT 3: run the identical command from step 6F again (60-minute timeout each), applying the same check from step 7F after each one.
9F. `python sci_index.py status --pool-dir ../recourse-sci-pool-data --index-dir ../recourse-sci-index --ceiling 80000000`
10F. Report in at most 8 lines: blocks, docs, passages and tokens for each shift, each stop reason, and the status line.

### If the task says EVAL (the known-answer check on what is already indexed)
6E. `python sci_index.py eval --index-dir ../recourse-sci-index --push`
7E. Report the SUMMARY line and the per-question lines exactly as printed. Then STOP.

### If the task says DEDUPE-PLAN (look for second copies of the same judgment; removes nothing, spends nothing)
Why: `shift` only skips copies that are word-for-word identical. The same case crawled twice with a different header or layout gets indexed twice, and the copies fill the search results. Run this after new blocks have been indexed.
3D. Also run `python test_index_dedupe.py` (must end with ALL PASSED; otherwise STOP and report the failing lines).
6D. `python index_dedupe.py scan --pool-dir ../recourse-sci-pool-data --index-dir ../recourse-sci-index --out ../dedupe-scan.json`  (if the index holds bucket judgments, add `--bucket-dir ../recourse-sci-bucket-data`, and run step 5b first; without it the scan prints how many bucket judgments it left out)
7D. `python index_dedupe.py plan --index-dir ../recourse-sci-index --scan ../dedupe-scan.json --out ../dedupe-plan.json --keep-landmarks --show 15 --save-to-index`
8D. Report in at most 8 lines: the "N groups, M judgments to remove, K pairs left in place" line, the groups it printed, and the file name it saved under `state/fixes/plans/`. Then STOP. Do NOT apply the plan. A person must read it first: the rules cannot recognise every second copy of a case, and a wrong removal needs a person to catch it.

### If the task says DEDUPE-APPLY <plan file> (applies a plan that a person has already read and approved)
The task names the plan file, for example `../recourse-sci-index/state/fixes/plans/20261003T101500-plan.json` or `index_fixes/2026-10-02/plan.json`. Never apply a plan that was not named in the task.
3D. Also run `python test_index_dedupe.py` (must end with ALL PASSED; otherwise STOP and report the failing lines).
6A. `python index_dedupe.py apply --index-dir ../recourse-sci-index --plan <plan file> --push`  (it removes the planned copies' passages and vectors, keeps them listed in the docs files as near_duplicate, spends nothing, commits and pushes `claude/sci-index`; to undo, revert that one commit)
7A. `python sci_index.py status --pool-dir ../recourse-sci-pool-data --index-dir ../recourse-sci-index --ceiling 80000000`
8A. `python sci_index.py eval --index-dir ../recourse-sci-index --push`  (the only step that costs money: a few cents for the 12 test questions)
9A. Report in at most 8 lines: the totals line printed by step 6A, whether it printed "pushed", the status line, and the SUMMARY line of the eval. If step 6A prints "refused" or "push failed", STOP and report that exact text.

### If the task says BUCKET-PLAN (what indexing the bucket would cost; no key, no spending)
Why: the bucket's judgments (2017 on, plus older ones the crawl lacks) are not in the index. This prepares every pending bucket block exactly as a shift would and adds up the estimated tokens.
6B. `python sci_index.py plan-bucket --bucket-dir ../recourse-sci-bucket-data --index-dir ../recourse-sci-index --ceiling 80000000`  (takes several minutes)
7B. Report in at most 8 lines: the per-scope lines and the TOTAL line exactly as printed. Then STOP. The estimate says nothing about the service's own allowance: a person checks the allowance before BUCKET-FULL.

### If the task says BUCKET-TRIAL (one bucket block, to measure and check)
6BT. `python sci_index.py shift --pool-dir ../recourse-sci-pool-data --bucket-dir ../recourse-sci-bucket-data --index-dir ../recourse-sci-index --minutes 20 --max-new-tokens 1500000 --ceiling 80000000 --max-blocks 1 --pause 2.0`  (the first block is the newest bucket refresh; `--max-new-tokens` limits this run whatever was spent before)
7BT. `python sci_index.py status --pool-dir ../recourse-sci-pool-data --bucket-dir ../recourse-sci-bucket-data --index-dir ../recourse-sci-index --ceiling 80000000`
8BT. Report in at most 8 lines: the "Blocks done / docs / passages / tokens" line, the "Reason:" line, the block line (kept / skipped counts), whether the push worked, the "bucket" part of the status, and the new files under `../recourse-sci-index/index/` (names and sizes; bucket blocks have 10-digit names). Then STOP.

### If the task says BUCKET-FULL <C> (the real bucket run; the task names C, the total ceiling)
C is a ceiling on EVERYTHING ever spent on the index, so it must be higher than what is already spent (see the "tokens_spent" of `status`) by the amount the bucket is allowed to cost. A person must have checked the service's allowance and read a BUCKET-PLAN first. If the task gives no C, STOP and report that.
6BF. SHIFT 1, as one command with a 60-minute (3600000 ms) timeout: `python sci_index.py shift --pool-dir ../recourse-sci-pool-data --bucket-dir ../recourse-sci-bucket-data --index-dir ../recourse-sci-index --minutes 50 --ceiling <C> --pause 2.0`
7BF. Apply the check of step 7F ("time budget used up" means go on to the next shift; "completed all pending blocks" or "nothing left to do" means finished; anything else, a token ceiling included, means stop and report the exact reason). SHIFT 2 and SHIFT 3 use the identical command, with the same check after each; the ceiling already counts what the earlier shifts spent.
8BF. `python sci_index.py status --pool-dir ../recourse-sci-pool-data --bucket-dir ../recourse-sci-bucket-data --index-dir ../recourse-sci-index --ceiling <C>`
9BF. Report in at most 8 lines: blocks, docs, passages and tokens for each shift, each stop reason, and the status line (the "bucket" part). Then say that a DEDUPE-PLAN should follow, because the same judgment can sit in the crawl and the bucket in two layouts.

## Kill switch
If a file named `STOP` exists in the index folder (`ls ../recourse-sci-index/STOP`) the script stops before sending anything. Report it; that is intended. The DEDUPE steps that change or commit the index folder refuse too.

## What the script guarantees (so you do not need to worry)
It never spends past the token ceiling (a total over everything ever spent on the index) or past `--max-new-tokens` (a limit on one run), sends only criminal-law judgments, never sends exact duplicates or civil/tax cases (second copies that differ in header or layout are found afterwards by DEDUPE-PLAN), saves each finished block immediately (an unfinished block is discarded and redone), and stops by itself if the service refuses. For the bucket it also never sends a judgment the crawl is known to hold (the skip file), cuts the law report's editors' headnote and margin letters before embedding, and gives bucket judgments ids from 1,000,000,000 up so they cannot clash with a crawl id. Whether a judgment is criminal law is decided by the same wording rules as for the crawl, read on the report's full text including the headnote; it has not been checked against a lawyer's labels.
