# REGISTER_ROUTINE_RUNBOOK: one weekly session of the Overruled Register (read and follow exactly; this is an unattended run)

Purpose: every 7 days, write the week's review sheet for the Overruled Register (`REGISTER.md`) so that the reviewer (Mr. Advocate) has something to fill in. The run is **read-only on the register**: it changes no row, flag or proposal. Decisions are recorded later, in a working session, from the sheet the reviewer fills in.

Created 2026-10-08 on the owner's instruction ("create the weekly register routine"). Cadence: weekly, Thursday 08:49 India time (the first sheet was written on Thursday 2026-10-08; the first scheduled run is Thursday 2026-10-15).

**CURRENT STATE (2026-10-08, evening):** the routine that runs is the stand-alone one the owner created in the Claude app ("Register weekly review sheet", Thursday 9:35 India time, this repository attached, Default environment). Its first push worked (commit "Weekly register review sheet 2026-10-08 (automated)", 16:24 UTC). The session-bound routine described next no longer exists (it was not found when Claude tried to disable it), so the two cannot collide.

**How the first version was wired (history).** That routine was bound to the working session `session_01YEUNXbYb9LDbJLc2ziqL3n` (trigger `trig_01RvfxUFMQWUN9bFGKsmgUBc`, "Register weekly review sheet"): each Thursday it sends the run instruction into that session, which already has this repository checked out. A stand-alone routine (a fresh session each week) could NOT be created with the tools available to Claude: two test runs on 2026-10-08 started in an empty working directory with no repository and no valid GitHub token, and `add_repo` was not available there. So step 0 below is only needed if the routine is ever moved to a fresh-session routine created in the Claude app with this repository attached (see "How to stop it / move it" in `REGISTER.md`). If the working session is archived or deleted, the weekly sheet stops until a new routine is created.

## Hard rules
- A routine session starts from `main`, which does NOT hold the register code. Step 0 checks out the development branch. Do not merge anything to `main`; do not open a pull request.
- Push only to `claude/sharp-euler-unyfv0`, and add only files under `register_review/`. Never change a code file or anything in `goodlaw/data/register/`.
- Never run `register-build`, `register-review`, `register-sweep`, `register-flags`, `register-export-site`, or any command that writes the register, the flags or the proposals.
- Never create, change or delete a routine or schedule. Never start another session.
- If any step fails, retry it once; if it fails again, STOP and report the exact error. Do nothing else.

## Steps
0. **Get the repository.** A routine session may start with NO repository (the first test run on 2026-10-08 found an empty working directory and an invalid GitHub token). If `git rev-parse --show-toplevel` fails, call the tool `mcp__claude-code-remote__add_repo` with owner `Tanbir-Ahm`, repo `recourse-sci-pool` and access `push`, run the clone command it returns, then call `register_repo_root` if it asks. Do not check the repository by other means first, and do not use `gh`. Then `git fetch origin claude/sharp-euler-unyfv0` and `git checkout -B claude/sharp-euler-unyfv0 origin/claude/sharp-euler-unyfv0`  (if the branch does not exist, STOP and report).
1. `python -m pip install -q openpyxl`  (use `python -m pip`, not a bare `pip`: in the first test run of the stand-alone routine on 2026-10-08 `pip` and `python` pointed at different interpreters and the Excel test failed on a missing openpyxl).
2. `python test_goodlaw_register.py` and `python test_goodlaw_register_xlsx.py`  (both must end with ALL PASSED; otherwise STOP and report, and do not write a sheet).
3. `python sci_goodlaw.py register-weekly --out-root register_review`  (writes `register_review/<today>/review_queue.csv`, `Review_Sheet_<today>.xlsx`, `SUMMARY.md`).
4. `git status --short register_review`. `register_review/RUN_LOG.md` gains a line on every run, so there is always something to commit: do NOT restore or drop any change in `register_review/`, even when the Excel file differs only by a few bytes. `git add register_review`, commit with the message `Weekly register review sheet <today> (automated)`, then `git pull --rebase origin claude/sharp-euler-unyfv0` and `git push origin claude/sharp-euler-unyfv0` (on a network error only, retry up to 4 times, waiting 2, 4, 8 and 16 seconds).
5. Print `register_review/<today>/SUMMARY.md`, then report in at most 6 lines: the date, items on the sheet by kind, the size of the whole backlog and weeks to clear it, open flags, open proposals, the commit hash and whether the push worked.

## What this run does NOT do
- **The sweep** (`register-sweep`, which finds overrulings the register does not hold) needs the 1.8 GB corpus store, which a fresh session does not have (rebuilding takes about 15 minutes from the data branches). It is a monthly step run in a working session after the bucket refresh. It writes proposals only.
- **Recording decisions.** The reviewer fills the yellow columns of the Excel sheet and sends it back; a working session records it with `python sci_goodlaw.py register-review --sheet FILE.xlsx --reviewer "Mr. Advocate"` and commits the changed register files.
- **The checker's cards** are refreshed with `cards` (needs the corpus store); `register-flags` then takes new warnings into the ledger.
- Nothing here is connected to the live Recourse site.
