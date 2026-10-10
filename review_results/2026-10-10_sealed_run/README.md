# The sealed run, searched and packed 2026-10-10 (PRIVATE; no marks yet, key NOT opened, nothing scored)

**Status.** The 11 sealed questions (R03, R05, R07, R10, R13, R16, R18, R23, R25, R27, R30) were handed out **once** and searched on the frozen recipe; the marking pack for J and S is built. No reviewer mark exists. No answer key was opened by this step and no result was read. The owner said "Go" on 2026-10-10 after closing the four preflight items (see `FOLLOW_UPS.md`); `sealed_preflight.py` reported READY (25 checks OK, exit 0) at commit `3cee53f` before the run.

## What was run

| | |
|---|---|
| Rules | `review_data/ruler/SEALED_RUN_RULES_v1.md`, sha256 `1936fdc23a02...`, no amendments |
| Label (written by the guard) | `sealed run, final recipe \| rules 1936fdc23a02 \| code 3cee53fdf2` |
| Code | commit `3cee53fdf21f51eb3b6e5ecce7690bc9891c9d57`, no uncommitted files |
| Index | `claude/sci-index` `3c80a26e42` (236,155 passages) plus the three side indexes (17 + 1 + 1 judgments), voyage-law-2 |
| Arms | A = rerank-2, R = rerank-3-lite (same 60 candidates), S = the site's own search, safety nets for A and for R |
| Hand-out log | `review_data/ruler/real_frozen_runs.jsonl` (11 questions, `repeat: false`, 2026-10-10T11:56:02Z as written there) and `review_data/ruler/frozen_runs.jsonl` (the ruler's 8 frozen questions Q15, Q16, Q23, Q24, Q25, Q26, Q31, Q32). **These two files must stay in the repository: they are what stops a second hand-out.** |
| Spend | sealed 11: 437,456 re-rank tokens (rerank-2 218,728 + rerank-3-lite 218,728), 658 embedding tokens, about $0.022; ruler 8: 286,408 re-rank tokens, 303 embedding tokens, about $0.014; **together about $0.037** (the runner's own price table; the Voyage dashboard is the check) |

## Files

- `pool.json` **PRIVATE** (names the arms), `questions.jsonl`, `spend.json`, `pool_run.log`.
- `pack/Third_Batch_Pack.zip` (sha256 `8a58b513d32d44e9fca4c34419b1928d4abf319d7864c66c7e6c525c039dbc2a`, 96,757 bytes): 11 prompt files (order A only), 22 chats (11 files x ChatGPT and Gemini), 181 passages (R03 19, R05 16, R07 15, R10 14, R13 18, R16 21, R18 14, R23 15, R25 17, R27 15, R30 17), README and manifest. The pack says nothing about arms, re-rankers, halves or the purpose; the builder checks our own wording for leak words. `pack/build_info.json` holds the hashes.
- `../2026-10-10_sealed_run_ruler/`: the ruler's frozen half, searched with the same recipe, scored only by the automatic key test (`KEY_TEST.md`, `key_test.json`). **The heading of `KEY_TEST.md` says "tuning half"; that text is hard-coded in `ruler_keytest.py`. This file is the FROZEN half** (`run.half` is `sealed` in its `pool.json`). Not changed, because the code is frozen.

## Ruler frozen half, as the automatic test printed it (8 questions in 4 topics; Recourse's well-known settled topics; no reviewer mark; NOT an input to rules 1 to 5)

| Version | Expected judgment in top 5 / top 10 | Exact key paragraph in top 5 / top 10 |
|---|---|---|
| A today (rerank-2) | 6 / 7 | 1 / 4 |
| R challenger (rerank-3-lite) | 7 / 7 | 4 / 5 |
| S site shown | 7 / 7 | 1 / 1 |
| M safety net (A) | 5 / 5 | 1 / 1 |
| M safety net (R) | 5 / 5 | 0 / 0 |

Eight questions from four topics (two per topic) are not eight independent trials, the test is strict (another passage of the same judgment does not count), and these are famous settled topics. It is reported because the rules say so; it does not decide the re-ranker.

## What happens next (runbook `review_data/ruler/SEALED_RUN_RUNBOOK.md`, steps 4 to 8)

1. The owner forwards `Third_Batch_Pack.zip` (only the zip) to J and S; each of the 11 files is run in ChatGPT and in Gemini (22 chats), replies saved as `R03_A_ChatGPT.txt` and so on.
2. Replies are saved **as received** into `replies_as_received/` here, then `normalise_replies.py`, then `score_sealed_run.py marks` (stage 1, key not opened; coverage must be 100%).
3. Stage 2 (`score_sealed_run.py key`) opens the key only after stage 1 is saved and complete; then the register arm; then the plain-terms report; Mr. Advocate reads every passage anyone marked Misleading and a random 20 of the others.
4. **Nothing is re-run and nothing is changed after a mark exists.** A technical failure before any mark may be repeated and must be logged as such. The stale list stays at version 1 (sha256 `8498ae5f...`); the owner reported that Mr. Advocate agrees with it, which is relayed, not a ruling-by-ruling sign-off, so every figure that uses the list says "not lawyer-checked".

## Replies received 2026-10-10 (before any scoring)

`Third_Batch_J_and_S_as_received.zip` (sha256 `dc85a5e8dae8968e37b34f12f77212f5cbaf716bcd90da279dea901fad95cd10`), unpacked as received into `replies_as_received/`; `normalise_replies.py` output in `replies_for_the_reader/` (77 markdown escapes removed in 11 files, 0 left out, no prompt echoes, no identical files).

- Gemini: 22 of 22 files hold 181 of 181 passages. ChatGPT: 20 of 22 files usable, 151 of 181 passages.
- **Unusable, not scored: `R07_A_ChatGPT.txt` and `R23_A_ChatGPT.txt`** (invalid JSON inside a quoted `evidence` text; not truncated). Coverage is therefore 30 passages short, and the rules say no score is read before every passage is marked by both tools. Stage 1 has not been run. To be re-asked from J and S.
- Quote warnings (an `evidence` quote not found verbatim in the passage): 30 of 332 readable marks, Gemini 24 and ChatGPT 6; by a mark-blind check 19 keep both ends of the quote (an ellipsis or punctuation edit), 6 keep one end, 5 neither. A warning only; no mark is dropped for it.

### Update: the two re-asked replies (pasted by the owner into the chat, 2026-10-10)

`replies_reasked_as_pasted/R07_A_ChatGPT.txt` and `R23_A_ChatGPT.txt` are new replies (different wording from the originals) with the same two faults, so the cause is the copy button, not the model. `normalise_replies.py` now also removes a backslash before a backtick, and, only in a file that cannot be read otherwise, turns a doubled backslash before a quotation mark into a single one if the file then reads and its (number, mark) pairs are unchanged (tests added, all pass). `replies_for_the_reader/` = the 20 usable originals + these two (manifests: `replies_for_the_reader_NORMALISATION.json`, `replies_for_the_reader_reasked_NORMALISATION.json`). Coverage 181/181 for both tools. The choice of the re-asked replies over the originals was made before any mark was read.
