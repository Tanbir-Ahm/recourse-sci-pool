# IK start-up checklist: what was found when it was run (2026-10-06)

Hand-over for the next session, including an INDEX runbook trial. It says what the start-up checklist in `IK_PLAN.md` asked for, what actually happened, the corrected commands, the traps, and the Indian Kanoon (IK) facts worth carrying. Labels: **[seen]** happened or was read in this session; **[likely]** a fair inference; **[unverified]** not tested.

**Where it lives.** This file is on the work branch `claude/sharp-euler-unyfv0` only (not on `main`). A session that starts from `main` (the INDEX runbook says its code is on `main`) will not see it. To read it from there: `git fetch origin claude/sharp-euler-unyfv0 && git show origin/claude/sharp-euler-unyfv0:IK_STARTUP_FINDINGS.md`.

## 1. The checklist as written, and what happened

| Step as written in `IK_PLAN.md` | What happened | Do this instead |
|---|---|---|
| 1. Read `IK_PLAN.md` and `FOLLOW_UPS.md` 1e and 1f | Fine. | Also read `IK_PLAN.md` "Stopped by the owner" at the end. |
| 2. Attach `recourse-sci-pool-data` and `recourse-sci-bucket-data` with `add_repo` | **Failed [seen].** `add_repo` answered "not found or no access" for both, and `list_repos` shows only three repositories (`recourse-sci-pool`, `recourse`, `recourse-walkthrough`). The two names are not GitHub repositories: they are folders (git worktrees) of the branches `claude/sci-pool` and `claude/sci-bucket` of this same repository. | Section 2 below (git worktrees). `add_repo` is not needed for them. For the Recourse repo (public, read-only) `add_repo` answered that anonymous reads already work: `GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 https://github.com/Tanbir-Ahm/recourse /home/user/tanbir-ahm/recourse`. |
| 3. `python sci_goodlaw.py build --corpus corpus.sqlite` ("about 15 minutes") and run the tests | The build needs the two data folders. It took **about 5 minutes** here (08:17:33 to 08:22:22 UTC), not 15 [seen]. It produced 46,012 judgments (36,928 from the crawl, 9,084 from the bucket), 276,803 citation pairs, a 1.8 GB file plus a small `.cites` file. **Three test scripts failed at first** (`test_bucket_refresh.py`, `test_sci_bucket.py`, `test_sci_relay.py`) because `pyarrow` and `pymupdf` were not installed. After `pip install -q pyarrow pymupdf`, all test scripts passed (20 with the IK test). | Install those two first (section 2). |
| 4. Check `INDIANKANOON_API_KEY` is set without printing it, and that `api.indiankanoon.org` is reachable | Key present [seen]. An unauthenticated `curl` to `https://api.indiankanoon.org/` returned HTTP 200 at no cost. That proves the network path, **not** the key. The key was proved only by the first real call (Phase 0, Rs 0.02, balance 391.16 to 391.14). | Keep this check, but do not treat it as proof the key works. |

## 2. Corrected start-up commands (all of these ran in this session)

```
git fetch origin claude/sci-pool claude/sci-bucket
git worktree add --detach ../recourse-sci-pool-data   origin/claude/sci-pool     # about 276 MB
git worktree add --detach ../recourse-sci-bucket-data origin/claude/sci-bucket   # about 154 MB
pip install -q pyarrow pymupdf                                                   # needed by the crawl and bucket tests
nohup python sci_goodlaw.py build --crawl-dir ../recourse-sci-pool-data --bucket-dir ../recourse-sci-bucket-data --corpus corpus.sqlite > build.log 2>&1 &
# about 5 minutes; progress: tail build.log ("crawled texts", "bucket texts", "stored N", "cite index done")
for t in test_*.py; do env -u INDIANKANOON_API_KEY python3 "$t" >/dev/null 2>&1 && echo "PASS $t" || echo "FAIL $t"; done
[ -n "$INDIANKANOON_API_KEY" ] && echo "key set" || echo "key NOT set"             # never print the value
python sci_goodlaw.py ik status                                                    # the ledger: what has been spent
```

If `../recourse-sci-pool-data` already exists, `git worktree add` will refuse: reuse the folder (check with `git -C ../recourse-sci-pool-data log -1`).

## 3. Traps met (so they are not met again)

- **`pgrep -f` matches its own command line.** A watcher loop `while pgrep -f "sci_goodlaw.py build"; do sleep 15; done` never ended because it matched itself and reported "RUNNING" after the build had finished. Use an anchored pattern: `pgrep -af "^python sci_goodlaw.py build"`.
- **"Background task completed" means the launcher shell exited, not the work.** The build was started with `nohup ... &`, so the first notice arrived at once. Check the log or the process.
- **`corpus.sqlite` was not git-ignored.** A stray `git add -A` could have committed 1.8 GB. `.gitignore` now has `corpus.sqlite*`, `ik_cache/`, `.env`, `IK_STOP` and `goodlaw/data/*.lock`.
- **`python sci_goodlaw.py known` is slow** (over 10 minutes) and is not part of start-up; do not run it as a check.
- **The stop hook** refuses to end a turn with uncommitted changes: commit and push to the work branch (no pull request unless asked).
- **A session limit can stop a long background job** (a 60-agent review died partway and was resumed from its cached results). Save work before starting one.
- **Uploaded Word files**: read them as data (`python3 -I`, `zipfile`, the `w:t` text), in a fresh folder, never executed. Both link files were plain text.
- **My own mistakes worth not repeating**: a title-matching rule that treated "Union of India" as a stop word (it matched nothing); `cites:X` used where `citedby:X` was meant (cost Rs 0.50); assuming an IK id from a library link was the landmark judgment (D.K. Basu).

## 4. Indian Kanoon facts to carry [all seen unless marked]

- **Auth:** `Authorization: Token <key>`, POST, parameters in the query string. Only letters, digits, `.`, `_`, `-` are accepted in the key by our client. Host `api.indiankanoon.org` must be in the environment's allowed domains.
- **Calls, prices (each reconciled to the owner's dashboard), and what they return**

| Call | Price | Returns |
|---|---|---|
| `/docmeta/<id>/` | Rs 0.02 | `tid, publishdate, doctype, relurl, caseno, numcites, numcitedby, title`. `numcitedby` counts documents of **all** courts. |
| `/doc/<id>/` with `maxcitedby=50` | Rs 0.20 | the full text (`doc`), `docsource` (the court), `citedby` as a list of `{tid, title}` only (no court, no date; it gave 50 entries where `numcitedby` said 41). |
| `/search/` with `formInput` and `pagenum` | Rs 0.50 per page of 10 | `found` ("1 - 10 of N") and, per result, `docsource, publishdate, citation, bench, numcites, numcitedby, docsize, headline, fragment, title`. |
| `/docfragment/<id>/` with `formInput=<term>` | Rs 0.05 | `headline`: two passages of about 850 characters around the term (with highlight markup), `title`, `tid`. |

- **Search syntax that worked:** `doctypes:supremecourt` limits to Supreme Court judgments. `citedby:<id>` gives the documents that **cite** `<id>`. `cites:<id>` gives the documents that `<id>` cites (the reverse). Daily orders are probably left out by `doctypes:supremecourt` [likely].
- **IK's citation index is incomplete for judgments from about late 2023 on:** IK listed 3, 0 and 0 citing documents for three judgments that we hold 10, 7 and 3 Supreme Court judgments citing. Do not use IK to measure the gap for recent cases.
- **Library ids:** 48 of the 76 library cases had an IK id in `source_url`; 28 had a court-site PDF link. Recourse's id for D.K. Basu (235756) is the 1 August 1997 follow-up order; the landmark judgment is IK 501198. The owner sent verified ids for 12 more cases (`goodlaw/data/ik_ids_owner_batch1.json`, `..._batch2.json`); NALSA (36567208 is a 2026 order) and Pankaj Bansal (121377653 is the Daily Orders copy) are still unresolved; 16 cases have no link (`IK_LINKS_NEEDED.md`).
- **Results in one paragraph:** 11 priority cases: 93 of 104 first-page Supreme Court citing judgments are in our collection (about 89%); the 10 distinct ones we lack (plus the Borhade probe) were read by fragment and none is adverse (7 follow or rely on the case, 1 distinguishes, 3 only cite). Youth Bar's two IK-listed Supreme Court citers are exactly the two we hold. Details: `IK_PLAN.md`; labels and ids in `goodlaw/data/ik_*.json` (no IK text).

## 5. State at the end of the session

- **Spend: Rs 8.49 of the Rs 150 plan, 87 calls** (62 `meta` Rs 1.24; 1 `doc` Rs 0.20; 13 `search` Rs 6.50; 11 `fragment` Rs 0.55). Dashboard readings the owner confirmed: 391.14, 390.00, 389.42, 383.17; the last expected value is 382.67 (not yet read).
- **The client is frozen:** `TOTAL_CAP_RS = 8.49` in `goodlaw/ik.py`, so any call that costs money is refused; cached calls are free. To resume, raise it (a visible edit), update the pinned value in `test_goodlaw_ik.py`, and use `plan` then `run` with `--approved-rs` and `--plan-id` as before.
- **In git (branch `claude/sharp-euler-unyfv0`):** the client (`goodlaw/ik.py`), its tests (231 checks, no real call), the CLI (`python sci_goodlaw.py ik status|plan|run|confirm`), the ledger (`goodlaw/data/ik_ledger.jsonl`), the saved ids, counts and readings (`goodlaw/data/ik_*.json`), the plan (`IK_PLAN.md`), the links list (`IK_LINKS_NEEDED.md`), and the follow-ups (`FOLLOW_UPS.md` 1f).
- **Not in git, gone with the session:** `corpus.sqlite` (rebuild, section 2), `ik_cache/` (the raw IK answers, by design), the scratch files. Because the cache is lost, the client refuses to buy again a call the ledger says was paid for unless `--refetch` is given.
- **No pull request has been opened and nothing was merged into `main`.** The checker is not connected to the live site.

## 6. For the INDEX runbook trial specifically

- **What `main` has:** `INDEX_RUNBOOK.md`, `sci_index.py` and `test_sci_index.py` are on `main` [seen on the remote]. The checker, the IK code and this file are not; they are only on `claude/sharp-euler-unyfv0`. An INDEX session started from `main` will not need them.
- **Different key:** the index run uses `VOYAGE_API_KEY`, not the IK key. Its own check line (in the runbook step 5) never prints the value. The two keys and the two spending limits are unrelated; the IK freeze does not affect it, and the runbook's token ceiling does not affect IK.
- **The start-up lessons that carry over:**
  - The crawl folder is again a git worktree of `claude/sci-pool` (runbook step 1 already says so); the index branch is attached by `sci_index.py init` as `../recourse-sci-index`. No `add_repo` is needed.
  - `pip install -q numpy voyageai` (runbook step 2), then `python test_sci_index.py` must say ALL PASSED (it passed in this session).
  - Run `python sci_index.py active-check` first and never run two indexing sessions at once.
  - Use an anchored `pgrep -af` pattern, never `pgrep -f "<script>"` inside a wait loop.
  - Do not build the checker's 1.8 GB store in the same session unless that is the task.
- **Hard rules from the runbook that this file does not override:** change no code file; push only `claude/sci-index`; never print a key; stop and report on any refusal; do not retry.
- **Not tested here [unverified]:** whether the INDEX trial's environment can reach the Voyage service, and how much disk it has (`df -h` first).

## 7. Decisions still with the owner (pointers only)

Who reviews `cards/REVIEW_SHEET.csv` (six rows; a lawyer is best); whether and how to connect the warnings-only cards to Recourse; the merge to `main` and the monthly refresh routine (reminder for 2026-10-12 in `FOLLOW_UPS.md` item 1); whether verified reader-only findings should raise quiet cards to a caution; the "powered by IKanoon" logo in Recourse; the non-commercial allowance; optionally removing the IK key and allowed domain from the cloud environment.
