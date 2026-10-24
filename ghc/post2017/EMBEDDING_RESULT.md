# Guwahati post-2017 judgments embedded (set P1), 2026-10-24

Owner's decisions (2026-10-24): set P1 (every stored post-2017 criminal-type document with a judgment signal), ceiling raised to 110,700,000 tokens in all, new indexer scope with its own id range, one trial block then the rest, blocks added to `claude/sci-index`.

| | |
|---|---|
| Documents looked at (blocks `ghc_post2017-0000` to `-0028` on `claude/ghc-bucket`, ids 2,000,750,000 to 2,000,757,117) | 7,118 |
| Judgments embedded (with passages) | **5,830** (the run counted 5,834 kept; 4 had no usable passage after noise removal) |
| Skipped | not criminal by the wording test 525, copies of text already seen 452, too short 307 (the same figures as the no-spend plan) |
| Passages | 117,329 (same as the plan) |
| Tokens charged | 25,392,004 (plan estimate 26,218,695: 3.2% lower; the trial block came in 4.4% lower), nothing wasted |
| Dollars at the listed $0.12 per million | about $3.05 |
| By decision year | 2018: 657, 2019: 546, 2020: 436, 2021: 355, 2022: 551, 2023: 713, 2024: 809, 2025: 982, 2026: 781 |
| With a neutral citation | 2,960; court-listed 2,582 |

Index after the run: 296 blocks, 418,286 passages, **108,263,532 tokens spent in all** (ceiling 110,700,000; 2,436,468 left). Branch `claude/sci-index` head `38d1d3f`. Checks on all 29 new blocks: vector rows equal passage rows, 1,024 finite numbers each, unit length, every id in its block's range, every embedded judgment has court, date, link and case number; no repeated text among the embedded judgments.

Each index record's `src` carries: source `ghc_post2017`, title (the parties), date, citation = case number, `url` (the court's own PDF link where the court lists the judgment, else the open bucket's PDF link), `bucket_url`, `neutral_citation`, `court_listed`, `signals` (court_listed, heading_judgment, long_body), court "Gauhati High Court".

Not done: a DEDUPE-PLAN for these blocks, a landmark evaluation (a few cents), connecting any of this to the site. About 90 of the earlier 1,739 Guwahati embeds were not criminal-type cases that the wording test let through; the same can be expected here (not measured).
