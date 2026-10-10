# Re-ranker test: Voyage's newer re-rankers on the 14 saved candidate lists. Design and decision rule, written BEFORE any paid call

Written 2026-10-10 after the owner's "Go". Committed before the script and before any result. The rule is applied mechanically to the numbers.

## 1. Question

Two of the four tuning questions where version A misses the key authority are lost at the re-ranker: the named case is among the 60 candidates but `rerank-2` puts it too low (R09: Bridgestone, 36th; R20: Pramod Suryabhan Pawar, 11th, one place outside the top 10). R14 and R22 never reach the 60, so no re-ranker can help them. **Does a newer Voyage re-ranker get R09 or R20 into the top 10 without losing any of the ten questions version A answers today?** Nothing else is asked.

## 2. What is known and what is not (checked 2026-10-10)

- Version A uses `rerank-2` (`review_tools/pool_runner.py` line 47) [Certain].
- Your Voyage account accepts `rerank-2`, `rerank-2-lite`, `rerank-2.5`, `rerank-2.5-lite`, `rerank-3` and `rerank-3-lite` (six test calls of 21 tokens each) [Certain].
- That `rerank-3` and `rerank-3-lite` are Voyage's newest (post dated 30 Sep 2026) and the 2.5 pair older comes from a web-search summary of Voyage's pages; the pages themselves are blocked in this sandbox and were not read. Prices ($0.05 and $0.02 per million tokens, first 200 million tokens free per account for the 2.x models) are from the same summaries and are unverified [Likely].
- Different models score on slightly different scales (the same test pair scored 0.523, 0.498, 0.520 under `rerank-2`, `rerank-2.5`, `rerank-3`), and the passage-type weights were set around `rerank-2` [Certain for the scores].
- `rerank-2` is not repeatable: re-running the same search gave the recorded ten for 7 of 14 questions (model test, README section 4) [Certain]. So every comparison below is against `rerank-2` run twice, today, on the same lists.

## 3. Inputs

The 14 answerable tuning questions (R01, R02, R04, R08, R09, R11, R12, R14, R17, R19, R20, R22, R24, R26), exactly as written in `real30_v1.json`; no rewrite, **no instructions** added to the question (the 2.5 and 3 models accept instructions; that is a separate experiment, not run). The 60 saved candidates of each (`rerank_effect/fused_lists.json`; the model test's check V2 showed they equal a fresh recomputation for all 14), passage text cut at 3,500 characters as in the pipeline. Tuning half only; the key file is parsed whole and the sealed entries dropped on the same line, unread, as in the earlier scripts.

## 4. Arms

| Arm | Model | Calls |
|---|---|---|
| C1, C2 | `rerank-2` (today's), run twice | 14 each |
| N1 | `rerank-3` | 14 |
| N2 | `rerank-3-lite` | 14 |
| X | `rerank-2.5` | 14 (extra: reported, not in the rule) |

Per question the whole 60 are scored in one call; final score = re-ranker score x passage-type weight x section boost (`Engine.weight`), top 10 shown, exactly as version A. Secondary ordering without the weights (version E) is also computed and reported, not in the rule.

## 5. Measures

Per question and arm: the place (1 to 60) of the first passage of a key judgment in the final ordering (the top 10 is the list shown); hits at 1, 5 and 10; for each new model, how many passages of its top 5 are not in the top 5 of C1 (the number a human would have to mark again); score level of each model (median top score).

## 6. The rule

For a new model M in {N1, N2}, a run **passes** if all three hold:

1. **Gain:** at least one question has its key judgment in M's top 10 and **outside the top 10 of both C1 and C2** (a clear gain, not a one-place wobble; R09 and R20 are the only questions that can qualify).
2. **No loss:** no question has its key judgment in the top 10 of **both** C1 and C2 and outside M's top 10.
3. **Top-5 guard:** hits at 5 of M are not lower than the lower of C1's and C2's.

**Confirmation:** M is run a second time (14 more calls) and must pass again on its own second run against the same C1 and C2. **PASS = both runs pass.** Anything else is NOT-PASS. If both N1 and N2 pass, the report says so and recommends the cheaper one only if its places are as good.

## 7. Consequences, agreed in advance

- **PASS (confirmed):** the re-ranker is worth a proper trial; it does **not** authorise a switch. Next, in this order: (a) look at how the new scores sit against the weights (tuning half only); (b) J and S mark the passages that newly enter the top 5 (the count reported in section 5 is the workload); (c) only then does the sealed run use the new re-ranker. The register, the safety net and the Recourse site are untouched.
- **NOT-PASS:** `rerank-2` stays. The re-ranker lever is closed for R09 and R20 on this evidence; recorded in `FOLLOW_UPS.md`.
- **Expectation recorded before the run:** [Guessing] about 20 to 25% that the rule passes.

## 8. Spend and limits

Calls: C1, C2, N1, N2, X = 70 calls, plus 14 for a confirmation, plus up to 14 for a second model's confirmation. About 20,000 tokens per call, so about 1.3M tokens for the main run, about 1.9M with both confirmations. **Hard stop at 2.0M re-rank tokens** (about $0.10 at the listed $0.05 per million, and possibly $0 inside Voyage's free allowance; the dashboard will show which). No embedding is bought. The Voyage reserve for the live site ($5) is unaffected.

Limits: 14 questions, two of which can change; the named-case measure says nothing about whether the passages shown are useful or current; the passage marks by J and S were made on `rerank-2` lists and are not redone here; a new model's pass or fail on 14 saved lists is not a statement about the whole index.
