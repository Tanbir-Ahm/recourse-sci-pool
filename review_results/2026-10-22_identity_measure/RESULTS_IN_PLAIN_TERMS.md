# Can the connector name the judgments, and what does the formatter then say? (measured 2026-10-22)

**Short answer.** Naming is not the problem: the connector names 99.8% of the judgments in the index and every one of the 289 hits of the 29 questions. The problem is what is known about them once they are named: only 76 judgments have a currency card, so 283 of the 289 hits (98%) come out "Not checked by us". Source label: the checker's corpus (rebuilt today) and the index's own records; nothing here is lawyer-checked.

## What was measured

- The corpus was rebuilt from the two data branches on 2026-10-22 (46,012 texts: 36,928 crawl, 9,084 bucket; `python sci_goodlaw.py build`, about 7 minutes on this machine).
- The index's document records (214 files, 10,505 kept judgments, 236,155 passages) were read from `claude/sci-index` at the commit the stage F run used (`3c80a26`).
- The hits are the pooled results of the stage F run (29 questions, 289 pooled hits) and the lists of the recipe that stayed ("B baseline"): its top 5 (145 hits) and top 10 (290 hits).
- Script: `review_tools/experiments/measure_identity_2026-10-22.py` (read-only, no network, no spend). Totals only; the pool is a private answer key, so nothing per version and no passage or question text is written here. Numbers: `numbers.json`; the 18 judgments nobody can name: `unidentified.csv`.

## 1. Can the connector name a judgment?

| | Judgments in the index | Named | Passages in named judgments |
|---|---|---|---|
| Crawl | 8,101 | 8,083 (99.8%) | 153,153 of 153,383 (99.9%) |
| Bucket | 2,404 | 2,404 (100%) | 82,772 of 82,772 |
| Together | 10,505 | 10,487 (99.8%) | 235,925 of 236,155 (99.9%) |

- Every name comes from the corpus. The 18 it cannot name are crawl judgments the corpus holds but with no title, petitioner or respondent (`unidentified.csv`).
- **Hits: 289 of 289 named**, 145 of 145 in the recipe's top 5.
- **Year.** Bucket: all 2,404 read from the judgment. Crawl: 7,458 of 8,083 (92%) read from the judgment (its header, the place line at its end, or the bucket's record); 625 (8%) were estimated from neighbouring judgments, and the connector says so in `source_info.notes`. Among the hits, 6 of 289.
- **Citation.** Bucket: all. Crawl: 5,505 of 8,083 (68%). Among the hits, 258 of 289 (89%). Without a citation or a clean year the register can still match by name and year, or not at all.

## 2. Are the names right?

Not proven, but nothing found against it.
- For each named hit I compared the corpus name with the title the earlier search harness had shown. 278 agree; 9 had no title at all; 2 "disagree", and both are one judgment (Sushil Ansal v. State Through CBI) whose earlier title was a fragment of the judgment's text with no party names, so there was nothing to compare.
- I read the 9 untitled hits and that judgment against their own passage text (not a lawyer's reading). Each name fits what its passage is about (for example a drunken-driving case cited in the Sushil Ansal passage, an Arms Act possession case, a 1993 blasts confession passage). So the corpus gave a plausible name to every hit the earlier harness could not title.
- This is a check of agreement, not of truth: it would miss a case where both the old title and the corpus are wrong in the same way, and it does not look at second copies (`dup_of`) in the corpus.

## 3. What the formatter says about those hits

| First line of the message | All 289 pooled hits | Top 5 of the recipe (145) |
|---|---|---|
| Register: candidate row (warning) | 1 | 0 |
| A card warns (adverse or questioned) | 0 | 0 |
| Quiet card | 5 | 3 |
| **Not checked by us (no card, or too few later judgments)** | **283** | **142** |
| Judgment not identified | 0 | 0 |

(The "silent" setting for quiet cards changes only the 5 quiet-card hits: they get no currency line. It does not change the rest.)

**Why almost all are "Not checked".** Only 76 of the 10,505 judgments in the index have a currency card (0.7%), because the cards were built for the 76 cases the live Recourse site can cite. The 290 hits of the recipe's top 10 come from 183 different judgments, and 5 of those have a card. The register matched one hit (a candidate row). The register lists mostly decisions overruled up to about 2015, so a modern bail or arrest judgment rarely appears on it.

## What it means

1. **The connector works; it is not the bottleneck.** A search hit can be turned into a named, cited, paragraph-and-page passage for essentially every judgment in the index.
2. **Honest but not useful yet.** With today's cards, 98% of messages would open with the same grey "Not checked by us" line. That is true, but it tells a lawyer nothing, and it would soon be ignored.
3. **The next piece is cards for the judgments that appear in results.** The checker can read any judgment in the corpus; it has only been asked about 76. For these 29 questions that is 183 judgments. By the repository's own figure (76 cards in about 2.5 minutes) that is roughly 6 minutes, and all 10,505 judgments about 6 hours. [Guessing: a straight scaling of that figure; the external-target and matching steps may take longer for judgments Recourse does not list.] This is also what standing item 0 in `FOLLOW_UPS.md` asks for ("extended to every case the site can cite").
4. **More cards will still mostly be quiet.** The checker catches about 3 in 10 of the overrulings it was tested on. More coverage turns "Not checked" into "No warning found", not into reassurance, and that is where the owner's open decision about how to show a quiet card matters most.

## Limits

- One pool: 29 questions, criminal law, Supreme Court only, one index snapshot. Other questions may land on judgments the corpus names less well.
- "Named" means the corpus has a title or petitioner and respondent for it. It does not mean the name is the exact form the register uses; the register matches by citation, or by both party names and a year within one.
- Second copies: 826 crawl texts are marked as second copies of another. Hits on a second copy are named from the copy's own row; not examined separately.
- The corpus is a snapshot of 2026-10-22; the index of `3c80a26`. The monthly bucket refresh will change both.

## Re-running

```
python sci_goodlaw.py build --crawl-dir ../recourse-sci-pool-data --bucket-dir ../recourse-sci-bucket-data --corpus corpus.sqlite
python review_tools/experiments/measure_identity_2026-10-22.py --corpus corpus.sqlite --index-docs DIR --pool review_results/2026-10-12_fix_test_f/pool.json --out review_results/2026-10-22_identity_measure
```

`DIR` holds the index branch's `index/*.docs.jsonl.gz` files (about 2 MB; a partial clone of `claude/sci-index` with `--filter=blob:none` fetches only those). The two data branches are cloned into `../recourse-sci-pool-data` and `../recourse-sci-bucket-data`.
