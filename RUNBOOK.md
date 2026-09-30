# RUNBOOK: one crawl session (read and follow exactly; this is an unattended run)

Purpose: continue the resumable crawl of the Supreme Court of India's open judgment archive and save the results to the branch `claude/sci-pool` of this repo. The saved shard files are the ledger, so it is always safe to stop and safe to run again. Code lives on `main` (your current checkout); data lives on `claude/sci-pool`, attached as a separate folder `../recourse-sci-pool-data`. NEVER merge or rebase between the two branches.

## Hard rules
- Never change any code file. Never push any branch except `claude/sci-pool`.
- Never try to get around a block, CAPTCHA, login page or "access denied". If the script reports one, STOP and report it. Do not retry.
- Never run more than the commands below. Do nothing else.
- If the task text contains a routine-fire-payload starting with `TEST`, do NOTHING except reply "chain test ok" and stop.

## Steps
0. `git fetch origin` then `python sci_relay.py active-check`. If it prints `ACTIVE`, another session is already running: report that and STOP (do not run anything else).
1. `git worktree add -B claude/sci-pool ../recourse-sci-pool-data origin/claude/sci-pool`  (if that branch does not exist, STOP and report)
2. `pip install -q pymupdf requests`
3. `python test_sci_relay.py`  (must end with ALL PASSED; otherwise STOP and report)
4. SHIFT 1, as one command with a 60-minute (3600000 ms) timeout:
   `python sci_relay.py shift --data-dir ../recourse-sci-pool-data --from-id 45749 --to-id 0 --minutes 50 --workers 2 --pause 1.5`
5. Look at the "Reason:" in its output. Continue to step 6 ONLY if it starts with "time budget used up". If it starts with "completed all pending blocks" or "nothing left to do", the crawl is finished: skip step 6 and say so. For any other reason (blocked, challenge, push failed, internal error, possible end of archive, STOP file, stopped inside block...), skip step 6 and report the exact reason.
6. SHIFT 2: run the identical command from step 4 again (60-minute timeout).
7. `python sci_relay.py status --data-dir ../recourse-sci-pool-data --from-id 45749 --to-id 0`
8. `python sci_relay.py chain --data-dir ../recourse-sci-pool-data --from-id 45749 --to-id 0 --max-shifts-per-day 12`  (starts the next session only if it is safe; it may print NOT CHAINED, which is fine)
9. Report in at most 8 lines: blocks done and ok/empty/error counts for each shift, the stop reason of each shift, the status line from step 7, the CHAINED / NOT CHAINED line from step 8, and any 403, 429, timeout or slowdown you noticed.

## Kill switch
If a file named `STOP` exists in the data folder (branch `claude/sci-pool`) or in this checkout (`main`), the script stops before fetching anything and chaining is refused. Check for it in the data folder: `ls ../recourse-sci-pool-data/STOP`. That is intended; just report it.
