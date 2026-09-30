# RUNBOOK: one crawl session (read and follow exactly; this is an unattended run)

Purpose: continue the resumable crawl of the Supreme Court of India's open judgment archive and save the results to the branch `claude/sci-pool` of this repo. The saved shard files are the ledger, so it is always safe to stop and safe to run again.

## Hard rules
- Never change any code file. Never push any branch except `claude/sci-pool`.
- Never try to get around a block, CAPTCHA, login page or "access denied". If the script reports one, STOP and report it. Do not retry.
- Never run more than the two shift commands below. Do nothing else.

## Steps
1. `git fetch origin`
2. `git checkout -B claude/sci-pool origin/claude/sci-pool`  (if that branch does not exist, STOP and report)
3. `git merge --no-edit origin/main`  (brings in updated scripts; if it conflicts, run `git merge --abort`, STOP and report)
4. `pip install -q pymupdf requests`
5. `python test_sci_relay.py`  (must end with ALL PASSED; otherwise STOP and report)
6. SHIFT 1, as one command with a 60-minute (3600000 ms) timeout:
   `python sci_relay.py shift --from-id 44999 --to-id 0 --minutes 50 --workers 2 --pause 1.5`
7. Look at the "Reason:" in its output. Continue to step 8 ONLY if it starts with "time budget used up". If it starts with "completed all pending blocks" or "nothing left to do", the crawl is finished: skip step 8 and say so. For any other reason (blocked, challenge, push failed, internal error, possible end of archive, STOP file, stopped inside block...), skip step 8 and report the exact reason.
8. SHIFT 2: run the identical command from step 6 again (60-minute timeout).
9. `python sci_relay.py status --from-id 44999 --to-id 0`
10. Report in at most 8 lines: blocks done and ok/empty/error counts for each shift, the stop reason of each shift, the status line from step 9, and any 403, 429, timeout or slowdown you noticed.

## Kill switch
If a file named `STOP` exists in the repo (on `main` or on `claude/sci-pool`), the script stops before fetching anything. That is intended; just report it.
