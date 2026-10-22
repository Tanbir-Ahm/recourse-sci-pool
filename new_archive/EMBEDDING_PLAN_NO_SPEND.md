# No-spend embedding plan (2026-10-22). Nothing was embedded, nothing was sent to any service, no key was read.

Made with `new_archive/plan_embedding.py`, which prepares each judgment with the indexer's own code (`sci_index.prepare_block`: criminal-law wording test, duplicate test against the 236,155 passages already indexed, passage building, token estimate). Details per year: `embedding_plan_2026-10-22.json`. Model `voyage-law-2`; price $0.12 per million tokens is the listed price from the owner's notes, not read from the service. Past estimates have run about 5 to 6% low.

| Set | Judgments looked at | Kept (criminal law) | Passages | Est. tokens | Est. dollars |
|---|---|---|---|---|---|
| A. Supreme Court, newer archive, not held by the open bucket (2017 to Oct 2026) | 3,747 | 1,312 | 30,028 | 7,128,905 | $0.86 |
| B. Guwahati, court's own files (reasoned) | 776 | 759 | 15,241 | 3,360,585 | $0.40 |
| C. Guwahati, open-bucket text (reasoned, wanted types) | 8,271 | 974 | 25,489 | 5,560,370 | $0.67 |
| **Total** | | **3,045** | **70,758** | **16,049,860** | **$1.93** (about $2.05 with the usual under-estimate) |

Not planned: the 6,662 Supreme Court judgments the bucket holds (its October run already looked at them); orders, AB/BA/bail/IA types, non-reasoned Guwahati documents (3,081), civil and service cases (A: 2,318, C: 7,297 left out by the criminal test), 113 + 4 tiny or duplicate in A, the 2 scans, the 74 skipped links.

## Limits that stop it today
- Token ceiling you set: 72,000,000 in all. Spent: 67,305,979. Headroom: 4,694,021. The plan needs 16,049,860, so the total would be 83,355,839: **it does not fit.** B alone (3.36M) fits; A (7.13M) and C (5.56M) do not. To do all three the ceiling must go to about 85M.
- Voyage balance about $9 (the owner's note of 2026-10-10, not re-checked), live-site reserve $5: about $4 spendable, so the dollars are fine; the ceiling is the binding rule.

## Quality findings that change the order
1. **Set C's text is not clean enough.** The bucket's Guwahati PDFs are typed at a fixed width and words are cut at the line end. Joining full-width lines first (`unwrap_fixed` in the script) lifts recognisable words only from 76.4% to 78.7% in a 150-document sample, and splits like "Secti on 304(B)" remain (some may be in the source PDF itself). A real fix needs a dictionary-based rejoin built from the corpus; it must be built and measured before C is embedded.
2. **A and B are clean** (normal line layout; passages are numbered paragraphs for 94% of Guwahati passages, the rest sentence windows).
3. The criminal-law filter is the crawl's wording rules, not checked against labels. On A it keeps 1,312 judgments, close to the 1,316 with a criminal heading on page 1.

## What running it would need (not done)
- Wiring: `sci_index.py` reads only crawl and bucket blocks. A new reader for the `claude/sci-court-newer` and `claude/ghc-bucket` shards (own id ranges, source recorded) plus tests: a code change, to be done and tested before any block is embedded; then a trial block (about 1.5M tokens maximum) as for the bucket.
- The index at `3c80a26` is the reference of the finished experiments. Adding to it makes a new snapshot; keeping that one untouched and writing new blocks to a separate index branch is the safer choice (owner's call).
- DEDUPE-PLAN afterwards, as for the bucket.

## Recommended order (needs the owner's go-ahead at each step)
1. B (Guwahati court files, $0.40, fits the current ceiling) as the first real trial, after the wiring and a free trial.
2. A (Supreme Court, $0.86) after the owner raises the ceiling.
3. C last, only after the word-rejoin is built and measured.

## Owner's decisions, 2026-10-22 (after this plan)
1. Wiring and a free trial for B first: done (see below). 2. Ceiling raised to **85,000,000** for A and C ("voyage balance is still there to cover this"). 3. New blocks go to `claude/sci-index` (not a separate branch).

## Wiring and free trial (done, nothing spent)
- `sci_index.py`: `--extra-dir` (shift, status), `extra_blocks`, a reader for prepared records, ids from `EXTRA_BASE` = 2,000,000,000; 13 new checks in `test_sci_index.py`, ALL PASSED (also `test_index_dedupe.py`, `test_sci_bucket.py`, `test_build_supplement.py`). Ids at 2e9 and up are also "at or above BUCKET_BASE": scripts that mean "bucket" by that test (`index_dedupe.py` counts, `review_tools/build_supplement.py`, `pool_runner.py` pinning) see them as bucket judgments; check before using them on the new blocks.
- Blocks built and committed: `claude/ghc-bucket:index_blocks/` (ghc_court, 4 blocks, 3.9 MB) and `claude/sci-court-newer:index_blocks/` (sci_newer, 15 blocks, 27 MB).
- Free trial of B: a throwaway copy of the real index (`3c80a26`, local remote), a fake embedder that calls nothing: 4 blocks, 759 judgments, **15,241 passages (same as the plan)**, 3,164,363 estimated tokens before the 1.062 calibration (3.36M after), vectors 1,024 numbers each, finite, rows equal passage rows, every judgment records its source (court, link, case number). The real `claude/sci-index` stayed at `3c80a26`.
- Cosmetic flaw to fix before the real run: a Guwahati title can end with a judge's name from the court list (for example "... Vs THE STATE OF ASSAM. MR MADAN B. LOKUR GOSWAMI"). It is metadata only, not embedded text.
