# The marking pack, version 2 (built 2026-10-10; PRIVATE; only `Second_Batch_Pack.zip` goes to J and S)

**This replaces `../2026-10-09_real30_rerank_test_pack/Second_Batch_Pack.zip` (sha256 `5fccb603...`), which was built but never sent** (the owner deferred the round; no reply to it exists in `review_replies/`). If that old zip has in fact gone to J and S, tell me before anything else is sent: this version would then be issued as an addendum instead.

## What changed, and why (owner: "Yes, bundle them into the marking round", 2026-10-10)

The re-ranker test (`../2026-10-10_reranker_test/README.md`) found that `rerank-3-lite` passes the pre-registered rule narrowly. Its top 5 brings 19 passages into the 14 answerable questions' top 5 that today's `rerank-2` does not show. **Only 4 of those 19 were unmarked and outside the pack already built**; the other 15 are first-batch passages or already in the pack's core and extra passages. So the bundle adds 4 passages, not 19:

| | Old pack | This pack |
|---|---|---|
| prompt files / chats | 19 / 38 | 19 / 38 (no new files) |
| passages | 143 (39 core, 66 extra, 38 anchors) | **147** (39 core, 66 extra, 38 anchors, **4 for the challenger**) |
| files that differ | | R09, R14, R17, R26 (one passage more each; the passages of these four files are renumbered, because the new ones are shuffled in with the old ones exactly as the other kinds are) |
| files identical to the old pack | | the other 15, byte for byte |
| zip sha256 | `5fccb60371b6...` | `21fa214e8dd6dfd2b1d715728dfdfddd91d5ac6993fa43ceea50c06549836da8` (106,060 bytes) |

Nothing in the prompts or the pack README says what the pack is for or that a second re-ranker exists (checked on all 19 real files: the only matches for words such as "extra", "core", "version" are inside judgment text). The extended pool `pool_with_rerank_arms.json` (private) now carries two more arms: `B today's re-ranker top 5` (what `rerank-2` gives today, which differs from the recorded version A for 3 passages) and `R challenger re-ranker top 5` (`rerank-3-lite`).

## Instructions for J and S: unchanged

The zip's own README (38 chats, ChatGPT and Gemini, replies saved as `R09_TA_ChatGPT.txt` etc.) is the same text with the same numbers of files. Replies go through `normalise_replies.py`, then both scorers:

1. `python review_tools/score_rerank_arms.py --pool .../pool_with_rerank_arms.json --replies DIR --out DIR2` (the earlier questions: does the first-stage order or the re-ranker matter; the safety net).
2. `python review_tools/score_challenger_arm.py --pool .../pool_with_rerank_arms.json --replies DIR --out DIR2` (new: are the passages `rerank-3-lite` brings into the top 5 at least as good as the ones it pushes out). Tests: `review_tools/test_score_challenger_arm.py`.

## The rule for the second scorer, written before any mark exists

PROCEED to a sealed run on `rerank-3-lite` only if every passage of both top 5s is marked, and in **both** "both-tools" settlements (ties to the lower mark, ties to the higher mark) the passages entering the top 5 have at least as many useful marks (Yes or Partly) as the passages leaving, minus one, and no more Misleading marks than the passages leaving, plus one; **and** no known-stale ruling enters the top 5. With about 20 passages on each side one passage is 5 points, so this means "not worse by more than one passage"; it is not proof of an improvement. Missing marks give INCOMPLETE, never a verdict.

**Stale-ruling check, done now** (`../2026-10-10_reranker_test/stale_check.py`, offline): the only known-stale ruling in either top 5 of the 14 questions is Dashrath Rupsingh Rathod (R09, replaced by statute); it is in both. None enters, none leaves. The key's stale list is not complete (the marks found replaced law it did not list), so this is a floor, not a clearance [Likely].

## Files
`Second_Batch_Pack.zip` and the unzipped `Second_Batch_Pack/` (to J and S: the zip only), `pool_with_rerank_arms.json` (private), `build_info.json` (private). Built by: `python3 -P review_tools/build_rerank_test_pack.py --pool review_results/2026-10-09_real30_pool_dev/pool.json --fused review_results/2026-10-09_real30_pool_dev/rerank_effect/fused_lists.json --out review_results/2026-10-10_real30_rerank_test_pack_v2 --challenger review_results/2026-10-10_reranker_test/results/challenger_rerank3lite_top5.json` (no network, no spend).
