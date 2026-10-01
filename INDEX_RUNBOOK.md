# INDEX RUNBOOK: one indexing session (read and follow exactly; this may be an unattended run)

Purpose: turn the crawled Supreme Court judgments (branch `claude/sci-pool`, read-only) into clean, tagged, embedded passages, saved block by block on branch `claude/sci-index`. The saved files are the ledger, so it is always safe to stop and safe to run again. Code is on `main` (your current checkout). The crawl data is attached as a read-only folder `../recourse-sci-pool-data`; the index branch is attached as `../recourse-sci-index`. NEVER merge or rebase between any of the branches.

## Hard rules
- Never change any code file. Push ONLY the branch `claude/sci-index` (the script does it). Never push `claude/sci-pool` or `main`.
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
5. Check the key exists WITHOUT showing it: `python -c "import os; print('key present' if os.environ.get('VOYAGE_API_KEY') else 'KEY MISSING')"`. If it says KEY MISSING, STOP and report.

### If the task says TRIAL (one block only, to measure and check)
6T. `python sci_index.py shift --pool-dir ../recourse-sci-pool-data --index-dir ../recourse-sci-index --minutes 20 --ceiling 1500000 --max-blocks 1 --pause 2.0`
7T. `python sci_index.py status --pool-dir ../recourse-sci-pool-data --index-dir ../recourse-sci-index`
8T. Report in at most 8 lines: the "Blocks done / docs / passages / tokens" line, the "Reason:" line, whether the push to `claude/sci-index` worked, the status line, and the files that now exist under `../recourse-sci-index/index/` (names and sizes). Then STOP. Do not run more shifts.

### If the task says FULL (the real run)
6F. SHIFT 1, as one command with a 60-minute (3600000 ms) timeout:
   `python sci_index.py shift --pool-dir ../recourse-sci-pool-data --index-dir ../recourse-sci-index --minutes 50 --ceiling 40000000 --pause 2.0`
7F. Look at the "Reason:" in its output. Continue to the next shift ONLY if it starts with "time budget used up". If it starts with "completed all pending blocks" or "nothing left to do", the job is finished: say so. For ANY other reason (token ceiling, allowance, refused, push failed, internal error, STOP file, stopped inside block...), stop running shifts and report the exact reason.
8F. SHIFT 2 and then SHIFT 3: run the identical command from step 6F again (60-minute timeout each), applying the same check from step 7F after each one.
9F. `python sci_index.py status --pool-dir ../recourse-sci-pool-data --index-dir ../recourse-sci-index`
10F. Report in at most 8 lines: blocks, docs, passages and tokens for each shift, each stop reason, and the status line.

### If the task says EVAL (the known-answer check on what is already indexed)
6E. `python sci_index.py eval --index-dir ../recourse-sci-index --push`
7E. Report the SUMMARY line and the per-question lines exactly as printed. Then STOP.

## Kill switch
If a file named `STOP` exists in the index folder (`ls ../recourse-sci-index/STOP`) the script stops before sending anything. Report it; that is intended.

## What the script guarantees (so you do not need to worry)
It never spends past the token ceiling, sends only criminal-law judgments, never sends duplicates or civil/tax cases, saves each finished block immediately (an unfinished block is discarded and redone), and stops by itself if the service refuses.
