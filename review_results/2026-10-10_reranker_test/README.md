# Re-ranker test, result (2026-10-10): rerank-3-lite passes the pre-registered rule, rerank-3 does not; the pass is narrow and does not justify a switch

Rule: `PREREGISTRATION.md` (commit `1459572`, before any paid call). Script: `reranker_test.py` (commit before the run; one lookup bug fixed before any paid call, see the git log). Tuning half only (the key file is parsed whole and the sealed entries dropped on the same line, unread). Same 60 saved candidates per question for every model; only the re-ranker changes. Everything is read from `results/results.json`.

## 1. Verdict by the rule

| Model | Gain (key judgment newly in the top 10, outside the top 10 of both rerank-2 runs) | Clear loss | Top-5 guard | Confirming second run | Result |
|---|---|---|---|---|---|
| **rerank-3-lite** | R20 (11th to 8th) | none | 9 against 9, ok | passes again (identical to the first run) | **PASS** |
| rerank-3 | R20 (11th to 2nd) | **R12** (6th to 11th) | 10 against 9, ok | not run | **NOT-PASS** |
| rerank-2.5 (extra, not in the rule) | R20 (11th to 2nd) | none | 10 against 9, ok | not run | meets the same conditions on its first run; not counted |

Control: `rerank-2` run twice gave the identical top ten on all 14 questions (so the controls show no within-session wobble).

## 2. Places (weighted as version A; the top 10 is what is shown; "-" = no key passage among the 60 candidates)

| Question | recorded A | rerank-2 (run 1 = run 2) | rerank-3 | rerank-3-lite (both runs) | rerank-2.5 |
|---|---|---|---|---|---|
| R01 | 1 | 1 | 2 | 1 | 1 |
| R02 | 1 | 1 | 1 | 1 | 1 |
| R04 | 2 | 2 | 3 | 4 | 5 |
| R08 | 2 | 2 | 1 | 1 | 4 |
| R09 | - (36th) | 35 | 27 | 31 | 27 |
| R11 | 3 | 3 | 2 | 3 | 3 |
| R12 | 5 | 6 | 11 | 9 | 6 |
| R14 | - | - | - | - | - |
| R17 | 1 | 1 | 3 | 2 | 2 |
| R19 | 1 | 1 | 1 | 4 | 1 |
| R20 | - (11th) | 11 | **2** | **8** | **2** |
| R22 | - | - | - | - | - |
| R24 | 1 | 1 | 1 | 1 | 1 |
| R26 | 4 | 4 | 3 | 3 | 4 |
| key in top 1 / 5 / 10 | 5 / 10 / 10 | 5 / 9 / 10 | 4 / 10 / 10 | 4 / 9 / 11 | 4 / 10 / 11 |

## 3. What this says, in plain terms

- **R20 is rescued by all three newer models** (11th to 2nd, 8th, 2nd). Under rerank-3 and rerank-2.5 the key passages' scores rise (0.652 to 0.695 and 0.664; 0.566 to 0.68 and 0.676); under the lite model less so, which is why it only reaches 8th. Three models agreeing is the best evidence in this test [Likely real].
- **R09 is not rescued.** It improves (35th to 27th under rerank-3 and rerank-2.5, 31st under the lite model) and stays far outside the top 10. Its key passages are labelled "statute_text", weight 0.75. Without the weights rerank-3 and rerank-2.5 put it 10th (rerank-2: 23rd) [Certain for these 14 lists]; version E (no weights) was worse for rerank-2 in the earlier marks, so whether the weights should change for a new model is a separate study that was not run.
- **R14 and R22 are untouched**, as they never reach the 60 candidates.
- **Costs of the newer models:** the first place is lost more often (key in place 1 for 4 questions against 5: R19 to 4th under rerank-3-lite, R17 to 2nd or 3rd, R01 to 2nd under rerank-3; R08 gains first place under rerank-3 and rerank-3-lite); R12 slides under rerank-3 (11th) and rerank-3-lite (9th). The rule tolerated sliding inside the top 10; it did not tolerate R12 leaving it under rerank-3. That is why the stronger model fails and the lighter one passes: the verdict turns on single boundary cases (R20 at 8th, R12 at 11th) [Certain], which is the reason not to read it as "rerank-3-lite is better than rerank-3".
- **The confirmation was not independent evidence.** The second run of rerank-3-lite was identical to the first, and the two rerank-2 runs were identical to each other: the service gives the same answer to the same question within a session. What the earlier model test saw (law-2's own re-run giving the recorded top ten on only 7 of 14 questions; here again 7 of 14 against the recorded run) must therefore be drift between days, which this test cannot see. A repeat on another day would show whether rerank-2's places move; it costs 1 to 2 cents per model.

## 4. What changes in what is shown

For the top 5 of the 14 questions (70 slots), 19 passages under rerank-3-lite (27%), 21 under rerank-3 and 21 under rerank-2.5 are not in rerank-2's top 5. Nobody has marked them (the marks by J and S were made on rerank-2 lists). The named-case measure cannot tell whether they are more useful, less useful, or older law; **that is the whole remaining uncertainty and it is a human one** [Certain].

## 5. Spend (dashboard to confirm)

1,641,726 re-rank tokens: rerank-2 two runs 547,242, rerank-3 273,621, rerank-3-lite two runs 547,242, rerank-2.5 273,621 (each run is 273,621 tokens, 19,544 per call). Upper bound at $0.05 per million for every model: **$0.082**; at the listed rates ($0.05 for rerank-2 and rerank-2.5, $0.02 for the lite model, rerank-3's price not read and assumed $0.05) about $0.066. Voyage lists a free allowance of 200M tokens for the 2.x models, but the project's earlier re-rank spend matched the paid estimate, so assume it is not free. Together with the model test ($0.34) the expected Voyage balance is about **$8.97 to $9.05** against the $5 live-site reserve. The pricing and release information comes from web-search summaries of Voyage's pages, which were not read directly (the sandbox blocks them).

## 6. Limits

14 questions; one question changed on the rule's terms (R20); named-case measure only; marks not redone; no instructions were given to the new models (they accept them; not tried); one day, one session; whole-index behaviour not tested; the register, the safety net and the Recourse site are untouched.

## 7. What changes (consequences fixed in advance, section 7 of the pre-registration)

A confirmed pass means "worth a proper trial", not a switch. In order: (a) the weights against the new scores, tuning half only (first look in section 3, nothing tuned); (b) J and S mark the passages newly in the top 5 of the chosen model (19 for rerank-3-lite, of which only 4 were unmarked and outside the built second pack; **bundled into the deferred 38-chat round on the owner's instruction, 2026-10-10: `../2026-10-10_real30_rerank_test_pack_v2/`**); (c) only then does the sealed run use it. `rerank-2` stays in production use until (b) is done. A side benefit if the listed prices are right: rerank-3-lite costs $0.02 per million against $0.05.

## Files
`PREREGISTRATION.md`, `reranker_test.py`, `extra_after_verdict.py` (exploratory), `results/results.json`, `results/raw_scores.json` (every score of every call, so any ordering can be recomputed), `results/extra_after_verdict.json`, `results/spend.json`. Re-run: `python3 -P reranker_test.py run --out DIR` (needs `VOYAGE_API_KEY`; the same spend).
