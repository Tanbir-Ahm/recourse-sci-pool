# Model test: voyage-4-large against voyage-law-2 on our own passages. Design and decision rule, written BEFORE any paid call

Written 2026-10-10 on the owner's instruction ("Yes, run the model test ... keep the reserve at $5 for live site"). Nothing in this folder has been run when this file is committed; the commit that holds it comes before the commit of the script and before any result. The rule below is applied mechanically to the numbers; if a number is awkward, the rule still stands and the awkwardness is reported next to it.

Tuning half only (19 questions; 14 of them have a key authority the index holds). The sealed half is not run and its key is not read. The key of the tuning half is read the way `with_the_host_open/scripts/f0_map.py` reads it: all 30 entries are loaded and filtered to the tuning ids on the same line.

## 1. What decides whether a better embedding model can help (read this first)

The search sends 60 candidates to the re-ranker. The embedding model changes the final top 5 in one way only: it changes **which passages get into those 60** (the 100 nearest by meaning are one of three lists that are merged). Once a passage is a candidate, the re-ranker decides where it lands, whatever model made the first stage. So the question that matters is not "does voyage-4-large order the top 10 better", but "does it bring in key passages that law-2 does not, and keep the ones law-2 brings in".

What the saved diagnosis of the four tuning questions where version A does not show the key authority in its top 10 (`review_results/2026-10-09_real30_pool_dev/miss_diagnosis/miss_diagnosis.json`, `AUTHORITY_HITS.md`) says [Certain, counted]:

| Question | Where the key passage is lost today | Can a better first stage fix it? |
|---|---|---|
| R09 | is a candidate (meaning rank 31, keyword top 50); the re-ranker puts it at 36 | No: the embedding model is not involved |
| R14 | not retrieved at all (best rank by meaning 2,241; not in keyword or section lists); if forced in, the re-ranker puts it **first** | **Yes, if** the model brings it into the 60 |
| R20 | is a candidate (meaning rank 15); the re-ranker puts it at 11, one place outside the top 10 | No: re-ranker order, not retrieval |
| R22 | meaning rank 58 (inside the 100 nearest) but pushed out of the 60 by the merge; if forced in, the re-ranker puts it at 10 | Partly: it could reach the top 10, not the top 5 |

So the most an embedding upgrade can add to version A's score on these 14 questions is about +1 question in the top 5 (R14) and +2 in the top 10 (R14, R22) [Likely]. The earlier model results (README section 10.5 of the Vaquill comparison: voyage-4-large better on 6 or 7 of 13 questions) came mostly from questions version A already answers (R04, R08, R24 and R26 moved up inside the top 10 and are already in the final top 5) or already retrieves (R20), which the re-ranker already settles. On the two recall misses, voyage-4-large on Vaquill's chunks put R14's key chunk at rank 946 (law-2 on our passages of the same judgments: 1,654) and R22's at 163 (law-2: 49) [Certain, `ab_result.json`]. Those earlier numbers are therefore discounted as evidence for a pipeline gain.

**Expectation recorded before the run:** [Likely, about 75%] the test will not pass. If it does pass, the next step is the whole-index test, not the switch.

## 2. Arms

All arms use the same question texts, the same candidate pools, the same keyword and section lists and the same re-ranker. Only the first-stage "100 nearest by meaning" list differs.

| Arm | Passage vectors | Question vector |
|---|---|---|
| A0 | voyage-law-2, the vectors already in the index | voyage-law-2 (`input_type="query"`) |
| A1 | voyage-4-large (`input_type="document"`), our passage text unchanged | voyage-4-large (`query`) |
| A2 | the same voyage-4-large passage vectors | voyage-4-lite (`query`): the "quick mode" of the owner's two-mode idea |
| A2b | the same voyage-4-large passage vectors | voyage-4 (`query`): extra, costs a few tokens, does not enter the rule |

The voyage-4 models are asked for 1,024 numbers (`output_dimension=1024`, the index size); a different size back stops the run. A1 passage vectors are stored as float16 like the index, questions in float32.

## 3. The pools (what is embedded with voyage-4-large)

For each of the 14 questions (R01, R02, R04, R08, R09, R11, R12, R14, R17, R19, R20, R22, R24, R26), the union of:

1. **KEY**: every passage of every key judgment of the question (1,701 passages in all, about 0.57M tokens).
2. **CAND**: the 60 candidates version A sends to the re-ranker, recomputed with the pipeline's own code.
3. **LAW2-NEAR**: the 300 passages nearest to the question under voyage-law-2 over the whole index (so that A0's 100 nearest are exactly inside the pool).
4. **V4-NEAR**: every passage of the 12 judgments whose best chunk is nearest to the question under Vaquill's stored voyage-4-large chunk vectors (English chunks, judgments that map to ours, `with_the_host_open/results/ab_mapping.json`). This is the best available stand-in for "what voyage-4-large itself finds" without embedding the whole index.

Passages with the same text hash are embedded once.

**Known bias, stated now:** for A0 the pool holds the true 100 nearest, so A0's first stage is exact. For A1 the pool holds only what LAW2-NEAR, V4-NEAR, CAND and KEY contain: 33% of our judgments have no Vaquill chunks, and V4-NEAR uses Vaquill's noisier chunk text as a proxy. Competitors that voyage-4-large would find outside the pool are missing, so **A1 is flattered**: a rescue in this test is weak evidence, a failure to rescue is strong evidence. That is why the rule below ends in a gate for a further test, not in a switch.

## 4. The simulated search (per arm)

1. First-stage list = the 100 pool passages nearest to the arm's question vector (dot product).
2. Keyword list (50, BM25 over the whole index) and "section N" list (30 per number) exactly as in `pool_runner.Engine.retrieve`.
3. Merge by reciprocal rank, K = 60, top 60 = candidates (the same code path, with the arm's list in place of the 100 nearest).
4. Re-rank with Voyage rerank-2 (text cut at 3,500 characters; one call per question over the union of the arms' candidates, so every arm's passages are scored in the same call), multiply by the passage-type weight and the section boost (`Engine.weight`), top 10.

## 5. Measures

- **E2E (the one that matters)**: rank of the first passage of a key judgment in the final top 10 (counting passages, as `real30_score.py` does); hits at 1, 5, 10 per arm.
- **Candidate membership**: is any key-judgment passage among the 60 candidates.
- **Rescue**: a question whose key judgment has no passage among A0's 60 candidates (R14 and R22 expected; the run decides) and has one among A1's 60.
- **Loss**: a question where A0 has a key passage in the final top 10 and A1 does not, or where A0 has one among the 60 candidates and A1 does not. (A key that slides inside the top 10, for example from place 5 to place 7, is reported as movement, not as a loss; the top-5 count is guarded separately in the rule.)
- Secondary, reported, not in the rule: dense-only judgment-level rank of the key judgment inside the pool (hits at 1, 3, 5, 10; mean reciprocal rank), per arm; A2 and A2b E2E; for each rescue question the key passage's rank in the arm's first-stage list and the pool coverage of Vaquill's own top 100 chunks.

## 6. Validity checks (any failure: the test is INVALID, no verdict is drawn, nothing is re-tuned silently)

- V1: the replica of the merge, fed with law-2's whole-index 100 nearest, gives the engine's own 60 candidates for all 14 questions.
- V2: the recomputed candidates equal the saved ones (`rerank_effect/fused_lists.json`, same passage hashes in the same order) for at least 13 of the 14 questions.
- V3: A0's 100 nearest inside the pool equal law-2's whole-index 100 nearest for all 14.
- V4: A0's E2E first-key-ranks reproduce the recorded ones (R01 1, R02 1, R04 2, R08 2, R09 none, R11 3, R12 5, R14 none, R17 1, R19 1, R20 none, R22 none, R24 1, R26 4; `AUTHORITY_HITS.md`) with at most two questions off by one place and none off by more.
- V5: every vector has the expected size; every API answer accounted for.

## 7. The rule

Let `rescues` = number of rescue questions; `gain5` and `gain10` = hits at 5 and at 10 of A1 minus those of A0; `losses` as defined above.

**PASS** if and only if all four hold: `rescues >= 1`; `gain10 >= 1`; `losses == 0`; `gain5 >= 0`.
Anything else is **NOT-PASS** (the report names which condition failed). INVALID overrides both.

On PASS, one **confirmation step**, fixed now: for the rescued question(s) only, double the competitor field (LAW2-NEAR 1,000 passages, V4-NEAR 30 judgments, in place of 300 and 12), repeat the simulation for all arms on those question(s); the PASS stands only if a rescue and `gain10 >= 1` still hold there. A failed confirmation turns the result into NOT-PASS. Its own cap: 0.8M embedding tokens.

A gain without a rescue (for example R20 moving from 11 to 10 because the mix of competitors in the 60 changed) is reported as a "candidate-mix effect": it is not a recall gain, it depends on which decoys happen to be included, and it does not pass.

Consequences, agreed in advance:

- **PASS (confirmed)**: the whole-index trial is worth its price. Re-embed all 236,155 passages with voyage-4-large (about 67.3M tokens, about $8 at the listed $0.12 per million, a third-party price not checked with Voyage; the owner tops up first; the old index stays as the way back), then score the 19 tuning questions by the key (no marking needed unless new passages enter the top 5). Only then is a switch decided. The sealed run waits for that decision. If A2 (voyage-4-lite questions) passes the same rule as A1 the two-mode idea works on one index; if A2 does not pass, every question uses voyage-4-large (a question vector costs about a thousandth of a cent whichever model makes it, so the only reason for a lighter question model would be speed).
- **NOT-PASS**: no re-embedding. Version A stays on voyage-law-2. The "deep research mode switches to voyage-4-large" idea is dropped as a retrieval measure (it needs a voyage-4-large index to switch to) and revisited only if the evidence changes (a new Voyage model, a different failure pattern). The re-ranker, not the first-stage model, is then the lever to look at next.
- **INVALID**: the cause is fixed and recorded; the rule above is not changed.

## 8. Spend and limits

- Reserve for the live site: **$5** (owner, 2026-10-10). Voyage balance by estimate about $9.39 before this run, so about $4.39 of headroom; the hard cap for this whole test is about $0.60, and a full re-embed (about $8) is not affordable until the owner tops up.
- Prices used (per million tokens, third-party price lists, to be checked against the Voyage dashboard): voyage-4-large $0.12, voyage-4 $0.06, voyage-4-lite $0.02, voyage-law-2 $0.12, rerank-2 $0.05.
- Token estimate before any passage is embedded (3.87 characters per token x 1.062, the index builder's own calibration). If the estimate is above **3.4M** tokens, shrink LAW2-NEAR to 200 and then V4-NEAR to 8 judgments, once, and re-estimate; if still above, stop and report. While embedding, stop if billed tokens pass **3.6M**; the confirmation step has its own extra 0.8M. Re-rank cap **1.0M** tokens for the whole test. Worst case in money: (3.6M + 0.8M) x $0.12 + 1.0M x $0.05 + a few thousand question tokens = about $0.58. Embeddings are cached on disk by passage hash, so a restart is not billed twice.
- The run is stopped, not silently shortened, if a model name is refused or a vector size differs.

## 9. What this test cannot show

- It cannot show that voyage-4-large helps or hurts the whole index: recall over 236,155 passages is the whole-index trial's job.
- 14 questions, one key authority list made by the owner; one question changing is within noise. The rule therefore only gates a further, larger test.
- Dense-only ordering and marked relevance are not measured here (the earlier marks are AI marks of the search, and nothing here changes them).
- The answer-writing step, the register and the checker are untouched by this test.
