# Model test, result (2026-10-10): voyage-4-large on our own passages does NOT improve the search as it is built. Stay on voyage-law-2. [Certain for this test; see the limits]

Rule: `PREREGISTRATION.md` (commit `7c7bb9b`, before any paid call). Script: `model_test.py` (commit `0c95b6e`, before the run). Tuning half only; the sealed half was not run (the key file is parsed whole, as in the earlier scripts, and the sealed entries are dropped on the same line without being looked at or printed). Everything below is read from `results/results.json`; tables in `results/TABLES.md`.

## 1. Verdict by the pre-registered rule: NOT-PASS (the run is valid)

| Condition for a pass | Result |
|---|---|
| at least one recall miss rescued (R14 or R22 gets a key passage into the 60 candidates) | **none rescued**: no arm has a key passage among the 60 for either question |
| right judgment in the final top 10 for at least one more question than law-2 | **one fewer** (9 against 10) |
| no key judgment lost from the final top 10 or from the 60 candidates | **lost: R12** |
| top-5 count not lower | equal (9 and 9) |

All four conditions had to hold. Even the first alone fails, so the R12 loss (real but borderline, section 4) does not decide it.

Validity checks V1 to V5 all hold: the replica of the merge equals the engine's own 60 candidates for all 14 questions; they equal the saved ones for 14 of 14; the law-2 first stage inside the pool equals the whole-index first stage for all 14; law-2's simulated final places equal the recorded ones except R12 (6 against 5, within the pre-set tolerance); every vector came back with 1,024 numbers.

## 2. The numbers (14 answerable tuning questions; the search as it would run, only the first-stage list swapped)

| Arm | key judgment in the final top 1 | top 5 | top 10 | key passage among the 60 candidates |
|---|---|---|---|---|
| A0 voyage-law-2 (today) | 5 | 9 | 10 | 12 of 14 |
| A1 voyage-4-large passages and questions | 5 | 9 | 9 | 12 of 14 |
| A2 voyage-4-large passages, voyage-4-lite questions | 5 | 8 | 9 | 12 of 14 |
| A2b voyage-4-large passages, voyage-4 questions (extra) | 5 | 9 | 9 | 12 of 14 |

The two questions where the search fails because the key case never reaches the 60 (R14, R22) stay lost under every arm. The two where it fails because the re-ranker puts the key case low (R09, R20) are the same under every arm, as expected.

**What voyage-4-large did do, and why it does not matter here.** Ordering the pool's judgments by meaning alone (no keyword search, no re-ranker), the right judgment is in the top 3 for 7 questions (law-2: 5), the top 5 for 9 (8), the top 10 for 11 (9); mean reciprocal rank 0.485 against 0.430. That agrees in direction with the two earlier small tests (README of the Vaquill comparison, 10.5: top 3 nine against seven on identical text), so the claim "voyage-4-large orders a dense list better at the top" now has three small tests behind it [Likely]. It does not reach the final result: the re-ranker re-orders the 60 candidates anyway, and about a quarter of the candidates differ between A0 and A1 (on average 44 of 60 shared, range 38 to 56) with the final top places almost unchanged.

## 3. The two questions that could have been rescued

First-stage place of the best key passage (pool = the arm's nearest-passage list over the pool; for law-2 the whole-index place is given as well), `results/extra_diagnostics.json` [exploratory, after the verdict, no spend]:

| Question | law-2, whole index | law-2, pool (614 or 985 passages) | voyage-4-large | voyage-4-lite questions | voyage-4 questions | needed to become a candidate |
|---|---|---|---|---|---|---|
| R14 (key lost before the re-ranker) | 2,241 | 360 | **190** | 141 | 93 | the first 17 to 39 places, typically 30 |
| R22 (pushed out of the 60) | 58 | 58 | **112** | 130 | 99 | the same |

R14: voyage-4-large moves the key passage from 360th to 190th in a pool of 614 that was built to favour it. It would be far lower in the whole index. The question's wording and the key case do not meet by meaning under either model [Likely]; the blind rewrite arm (versions C and F) raised R14's marks (more direct answers shown) but did not bring the named case into the top 10 either (`AUTHORITY_HITS.md`), so no tested remedy rescues it yet. R22: voyage-4-large puts the key passage **lower** than law-2 does (112th against 58th). ("Needed" was measured on law-2's own search: a passage found only by meaning made the 60 when it stood within the first 17 to 39 places of the 100 nearest, median 30, on the 14 questions.) Pre-registered reading: a failure to rescue in a pool that favours voyage-4-large is strong evidence [Certain for this pool, Likely for the index].

## 4. The loss, and how much of the end-to-end comparison is noise

R12 (Rikhab Birani): law-2 has the key judgment 17th of 189 judgments in the pool, voyage-4-large 46th; the best key passage 23rd against 64th; one key passage reaches the 60 candidates instead of two, and the one that remains is not placed in the final ten. This is a real, small loss caused by the model. It is also a borderline question: the recorded run had it 5th, this re-run of the same law-2 search 6th.

The re-ranker is not repeatable enough to resolve one-place differences: law-2's own re-run gave exactly the recorded ten for 7 of the 14 questions (the earlier note, 9 of 19, said the same). So the end-to-end table can show a large effect (a rescue) but not a difference of one question. That is why the rule was written around rescues.

## 5. The "quick mode / deep mode" idea (owner, 2026-10-10)

Only relevant if a voyage-4-large index existed, which this result does not support. For the record: with voyage-4-large passages, questions embedded by voyage-4-lite were worse than by voyage-4-large (dense top 1: 3 against 5 questions; mean reciprocal rank 0.397 against 0.485; in the search, R11 fell from 2nd to 9th); questions embedded by voyage-4 (middle model) matched voyage-4-large (0.480). A question vector costs about a thousandth of a cent whichever model makes it, so a cheaper question model would only ever be for speed. **The two-model switch would not have saved money, and with a voyage-law-2 index there is nothing to switch.** If a "deep mode" is still wanted, the levers that exist on the current index are measured elsewhere: the blind-rewrite arm (F merged) raised R14's marks and pulled in more old law (not a default, possible as an opt-in with register warnings), a longer list (the safety net), and a stronger re-ranker (untested, section 8).

## 6. Spend (the Voyage dashboard should confirm)

| Item | Tokens | At the listed (third-party, unchecked) price |
|---|---|---|
| voyage-4-large passages (10,505 unique texts, 12,063 pool rows) | 2,660,190 | $0.3192 |
| question vectors (14 questions x 4 models) | 3,131 | $0.0003 |
| rerank-2, one call per question over the arms' union (69 to 98 passages) | 382,726 | $0.0191 |
| **Total** | | **$0.3386** |

The token estimate (3.2M at the index builder's calibration for voyage-law-2) was 20% too high: **voyage-4-large counts 17% fewer tokens for our text (83.1% of the estimate)** [Certain, measured on all 51 batches: 78 to 93% per batch]. A full re-embed, had it been wanted, would therefore have cost about 67.3M x 0.83 = 55.9M tokens, about **$6.7**, not $8, if the listed $0.12 is right. Expected Voyage balance after this test: about $9.39 - $0.34 = **$9.05**; the live-site reserve of $5 leaves about $4.05 to spend. If the dashboard shows something else, the listed price (or a free allowance) is the first suspect; please tell me the figure and I will correct every price in these notes.

## 7. Limits (read before quoting this)

- 14 questions, AI-marked pools elsewhere, one key list. The test is a falsification test of a large effect, not a measurement of a small one.
- The pool flatters voyage-4-large (section 3 of the pre-registration): of the 100 judgments nearest to each question under Vaquill's voyage-4-large vectors, only 33 to 65 had any passage in the pool and 12 to 15 had every passage. The result is NOT-PASS in spite of that.
- The whole-index behaviour of voyage-4-large on our passages was not measured (it costs about $6.7). The evidence says it is unlikely to matter for the final result (section 3), not that it is impossible.
- Only the first-stage list was swapped. Keyword and section search, the merge, the re-ranker and the weights are the ones in version A.
- Nothing here says anything about answer quality, the register, or the sealed half.

## 8. What changes

1. **No re-embedding with voyage-4-large.** The model question the plan asked to settle before the sealed run is settled: the sealed run can use the existing index (`claude/sci-index` `3c80a26`) whenever the owner decides to run it. Nothing needs topping up for this purpose.
2. **"Deep research mode switches to voyage-4-large" is dropped as a retrieval measure.** Revisit only if Voyage releases a different model class or the failure pattern changes.
3. **The first stage is not the lever.** Of the four tuning questions where version A misses the key authority, two are lost at the re-ranker (R09, R20), one is a wording gap (R14), one is pushed out by the merge (R22). The cheapest test that can still move the result is the re-ranker: Voyage's newer re-ranker model on the 14 saved candidate lists (re-rank only; about 380,000 tokens, about two cents at the listed price). It is not run: it needs the owner's go-ahead because it is a different experiment from the one approved, and its rule should be written first.
4. Corrections to earlier notes: "the one thing worth taking from Vaquill is its model" (`DECISION_VAQUILL_VS_OURS.md`) is withdrawn: tested on our passages, the model orders a dense list somewhat better and changes nothing in the search; the estimate of $8 for a re-embed was 20% high (about $6.7).

## Files
- `PREREGISTRATION.md` (design and rule, before any paid call), `model_test.py` (stages 0 to 3; stage 3, the confirmation step, was not needed), `make_tables.py`, `extra_diagnostics.py` (exploratory).
- `results/results.json` (everything), `results/TABLES.md`, `results/extra_diagnostics.json`, `results/pools.json` (the pools: row numbers of the index; PRIVATE, they name the key judgments), `results/spend.json`, `results/stage0.log` to `stage2.log`.
- Not kept: the 10,505 voyage-4-large passage vectors (21 MB; $0.32 to make again) and the question vectors.
- Re-run: `python3 -P model_test.py stage0 --work DIR --vq <Vaquill data dir>`, then `stage1`, `stage2 --out results` (needs `VOYAGE_API_KEY`; the same spend).
