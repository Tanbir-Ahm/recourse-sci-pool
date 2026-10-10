# Sealed-run runbook (PRIVATE; built 2026-10-10 under the frozen SEALED_RUN_RULES_v1.md)

Everything below is built and tested. **Nothing has been run on the sealed questions**: no hand-out is logged, the sealed content still has its freeze hash. Per the owner's accepted default, the run waits until the register patch has been applied by the owner (staging first) and Mr. Advocate has reviewed the 16 older rulings, if that is a matter of weeks; the bucket refresh waits until the run is over.

## Before the day
1. `python review_tools/sealed_preflight.py --owner-confirms register-patch,advocate-16,refresh-postponed,balance --date YYYY-MM-DD` must end with "READY" (it checks the frozen rules hash, a clean and pushed checkout, the index head, the freeze hash of the sealed content, that no hand-out is logged, the three side indexes, the Voyage key, all the machinery's test suites, and that the scorer rehearsal reproduced the tuning-half numbers). It prints the exact commands. It never hands a question out and never spends.
2. The owner reads the Voyage dashboard: balance above the $5 live-site reserve after about $0.05.

## The day (commands come from the preflight; this is what they do)
| Step | What | Guard |
|---|---|---|
| 1 | `pool_runner.py --half sealed --final --final-recipe ...`: A (rerank-2) and R (rerank-3-lite) on the same 60 candidates, the site's search, both safety nets, top 10 pooled, side indexes in | refuses BEFORE the hand-out unless: final recipe, challenger rerank-3-lite, top-k 10, site arm on, no other index head, cap at most 2,000,000 re-rank tokens, the three side indexes, rules equal their frozen hash, checkout clean. The label gets the rules hash and the code commit. About 0.5 million re-rank tokens (a few cents) |
| 2 | the same for the ruler's frozen half, then `ruler_keytest.py` (no marks needed) | its own guard |
| 3 | `build_sealed_pack.py --pool .../pool.json`: one prompt per question, order A only, every arm's passages in one shuffled list; refuses a pool that is not a sealed final-recipe pool or was made from uncommitted code. Send J and S **only** `Third_Batch_Pack.zip` (about 22 chats) | blindness checked on our own wording |
| 4 | replies come back: keep them as received, `normalise_replies.py` (backslashes only) | |
| 5 | `score_sealed_run.py marks`: coverage (every passage marked by both tools), reliability, shares, floors F1, F2, F4, rules 1, 2, 3, 5, the safety nets. **The key is not opened** | exits with status 2 if coverage is incomplete |
| 6 | `score_sealed_run.py key --half sealed [--tuning-pool ... --tuning-replies ...] [--register-flags ...]`: opens the key only now; answerable or gap, the named authority, known-stale rulings, rule 4, the choice of arm, F3, the floors on the chosen arm, the net rule, the lights, domain eligibility, the outcome of section 7. Writes `SEALED_RUN_REPORT.md` | refuses unless stage 1 is complete and the pool and replies are unchanged since; refuses a pool the guarded runner did not make |
| 7 | the register arm: `currency_pass.py` on the saved pool at the register's commit; pass its flags to step 6 and run it again | |
| 8 | the report in plain words (all four settlements, intervals, clear or weak pass, the label); Mr. Advocate reads every Misleading passage and a random 20 of the others before anything leaves the project | |

## Where the code makes a choice the rules left open (interpretation, not amendment; the rules file is untouched)
1. "Pooled" = the mean over questions of each question's share (macro), the way the tuning-half comparators were computed. Version A on the tuning half comes out at exactly 75%, 13% and 6%, 71%, 33% (the preflight checks this).
2. F1, F2, F4 and rules 1 to 3 use every sealed question that has a mark; F3 and rule 4 use the answerable ones; gaps and controls are listed apart.
3. "Better on a question" = the mean grade of the arm's top 5 (Misleading 0, No 1, Partly 2, Yes 3) higher by at least 0.4.
4. Lights: the plan's relevance and currency lights (thresholds in `real30_lights.py`), computed under both "both" settlements; a domain is eligible only if neither is red, the currency light is not red, the floors hold and each of its sealed questions alone is not red. With `--tuning-pool` the tuning half's marks of the chosen arm are added to the domain lights (the challenger's tuning lists exist for 14 of the 19 questions).
5. Clear or weak pass: a 95% bootstrap interval over questions (5,000 resamples, fixed seed) whose near end is beyond the floor = clear; otherwise weak.
6. The safety-net rule uses the chosen arm's net: Misleading share (macro) at most 5%, useful share at least 55%, at least 5 passages marked Yes by every run.

## Rehearsal (2026-10-10, `review_results/2026-10-10_sealed_run_rehearsal/`)
The scorer on the tuning data reproduces the comparators. **Applied mechanically to the tuning data, the frozen rules would NOT pick rerank-3-lite**: the marks favour it (it is better on 2 questions and worse on none) but rule 4 stops it, because the named authority in its top 5 falls from 10 of 14 to 9 (R12). The pool runner ran the final recipe on three tuning questions with the real service (122,344 re-rank tokens, $0.006), and the pack builder built a Rehearsal_Pack from that pool. Neither is evidence about the recipe.
