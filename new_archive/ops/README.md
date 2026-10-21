# Running the fetch jobs (how they were run on 2026-10-21; the container restarts about every 35 minutes and kills background jobs)

Scripts (copied here from /tmp/claude-0 so a restored session can use them; they hard-code the paths of that session: repo /home/user/recourse-sci-pool, data worktrees /home/user/recourse-sci-court-newer (branch claude/sci-court-newer) and /home/user/recourse-ghc-bucket (branch claude/ghc-bucket), PDF cache and the bucket's 2026 list in the session scratchpad):
- `run_queue3.sh`: Supreme Court queue. Pulls the owner's uploads, turns new link files into month folders `new_archive/YYYY-MM/`, fetches every month that has `links_all.txt` and no `results.csv`, newest year first, via `run_year2.sh`. Stops on any 403/429/challenge. Appends "QUEUE2 DONE" to run_queue2.log when 2017 to 2019 are complete.
- `run_year2.sh YEAR`: fetches the pending months of one year with `first_pass.py`, commits and pushes each month's results.
- `text_watcher2.sh`: stores the text of each finished month on `claude/sci-court-newer` (via `store_text.py`).
- Guwahati: `python3 -I -W ignore ghc/fetch_ghc.py /home/user/recourse-ghc-bucket 10000` (resumable; skips AB, BA, MC, IA case types).
Restart after a container restart: start each with nohup; never use `pkill -f` with a pattern that also appears in your own command line (it kills your own shell). All jobs are resumable: finished months are skipped.

## Finding of 2026-10-21 evening: background jobs only make progress while the session has an active turn
The container is suspended or reset when the session is idle (the PDF cache showed no new file after the idle gap began; a 55-minute foreground run on 2026-10-21 19:11 to 20:06 finished 5 months, 580 judgments, with no restart). So unattended nohup jobs do not work. Work in the FOREGROUND: each scheduled check-in runs `work_session.sh 3300` (a foreground command with a 3,500,000 ms tool timeout), then pushes, then schedules the next check-in about 3 minutes later. `intake_months.py` and `work_session.sh` are the files; `run_year2.sh` and `text_watcher2.sh` (background, alive during the turn) are as before.
