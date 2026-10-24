# What the big search index holds and what can be searched (2026-10-24, index branch `claude/sci-index` head `38d1d3f`)

Counted from the index's own files (script `ghc/index_holdings_by_year.py`; nothing sent anywhere, nothing spent). **[Certain]** = counted; **[Likely]** = inference; **[Guessing]** = a gap filled.

**Embedded and searchable: 19,236 judgments, 418,286 passages** (every passage has a vector and its text is in the keyword table; vector rows = passage rows = the ledger's count in every block, no non-finite number). Criminal law only, by the index's design (a wording test on the text).

## 1. By court, source and period [Certain]
| | Judgments embedded | Decided up to 2017 | Decided 2018 to 2026 | Passages |
|---|---|---|---|---|
| **Supreme Court** | **11,683** | **8,506** | **3,177** | 261,572 |
| the old crawl (to 4 May 2017) | 8,100 | 8,100 | 0 | 153,383 |
| the open bucket | 2,344 | 369 | 1,975 | 80,865 |
| the court's newer archive (from 5 May 2017) | 1,239 | 37 | 1,202 | 27,324 |
| **Gauhati High Court** | **7,553** | **1,723** | **5,830** | 156,714 |
| the court's own files (2011 to 2017) | 758 | 758 | 0 | 15,233 |
| open-bucket text up to 2017 | 965 | 965 | 0 | 24,152 |
| open-bucket text 2018 to 2026 | 5,830 | 0 | 5,830 | 117,329 |
| **Both courts** | **19,236** | **10,229** | **9,007** | **418,286** |

"Up to 2017" means decided on or before 31 December 2017. The crawl ends on 4 May 2017, so every crawled judgment is "up to 2017" whatever its estimated year. Seven kept documents (one each in the crawl, the bucket and the newer archive, four post-2017 Guwahati) had no usable passage and are not searchable; they are not counted above.

## 2. By decision year (embedded judgments)
| Year | Supreme Court | Gauhati |
|---|---|---|
| 1950 to 1969 | 470 | 0 |
| 1970 to 1979 | 429 | 0 |
| 1980 to 1989 | 330 | 0 |
| 1990 to 1999 | 1,177 | 0 |
| 2000 to 2004 | 1,220 | 0 |
| 2005 to 2009 | 2,306 | 23 |
| 2010 to 2014 | 1,826 | 895 |
| 2015 and 2016 | 504 | 494 |
| 2017 | 244 | 311 |
| 2018 | 304 | 657 |
| 2019 | 406 | 546 |
| 2020 | 175 | 436 |
| 2021 | 242 | 355 |
| 2022 | 342 | 551 |
| 2023 | 374 | 713 |
| 2024 | 401 | 809 |
| 2025 | 568 | 982 |
| 2026 (to October) | 365 | 781 |

Supreme Court years before 2017 for the old crawl are read from the crawled text or the crawl-to-bucket match: 6,076 of 8,100 rest on a header date or a match with the bucket (reliable); 2,024 rest on a date or year found in the text (estimates; trust the periods, not single years). The other sources carry the decision date in their record.

## 3. How each can be found (the research recipe in `review_tools/pool_runner.py`, class `Engine`)
| Search | What it does | Reaches |
|---|---|---|
| By meaning | the question's vector against the vectors of every passage; best 100 | all 418,286 passages, 19,236 judgments |
| By keyword | word search (SQLite full text, BM25, stemmed) over the text of every passage; best 50 | all 418,286 passages |
| By section number | when the question names a section, the exact phrase "section N" over every passage (up to 30 per number), and a 10% boost to passages that name it | passages that literally say "section N": **39% of Supreme Court passages and 37% of Guwahati passages**; at least one such passage in **96% of judgments** (Supreme Court 93 to 98% by source, Guwahati 95 to 98%). Other spellings (sec., u/s, s.) add only 4 and 3 points. |

The three lists are merged into 60 candidates, a re-ranker (Voyage rerank-2) reads each with the question, weights are applied (court's reasoning 1.0 down to header 0.3) and the top 10 are shown.

## 4. What is held but not embedded, and why [Certain]
**Supreme Court, 52,843 looked at:** 11,683 embedded; 35,713 not criminal law (by the wording test); 3,084 bucket judgments the crawl already holds; 1,426 too short; 664 exact copies; 270 near-copies removed on 2026-10-22; 3 with no usable passage. Never sent: 6,662 newer-archive judgments the open bucket already holds (its run judged them).
**Gauhati, 16,165 looked at:** 7,553 embedded; 7,833 not criminal law by the wording test (17 + 7,291 + 525); 452 copies; 307 too short; 16 near-copies removed; 4 with no usable passage. Never sent: the bucket's other Guwahati documents (orders, bail, civil writs and the like: 195,861 of the 211,222 dated 2018 to 2026 were not even fetched; 3,081 pre-2018 orders and unreasoned documents; 8,235 stored post-2017 documents with no judgment signal; 11 with no PDF in the bucket) and the 291 court-listed judgments the bucket lacks.
**Case type of the embedded Guwahati judgments:** 7,463 of 7,553 (98.8%) have a criminal case number; 90 (all from the open-bucket text up to 2017) do not.

## 5. Is any of it connected to the main site? [Certain]
No. The Recourse site repository (head `0d880bf`, 20 Oct) has no reference to this index; its search runs on its own small corpus. The index is used by the experiments and by the planned private pilot. Connecting is the owner's staged order of 10 October (shadow mode first, then the "not independently verified" panel). What the whole index needs to run: measured today, 418,286 passages, vectors 857 MB and text 408 MB; **2.86 GB of memory in steady use, 3.06 GB at peak**, about 17 s to build the keyword table, about 0.9 s for the local part of a search (median; the re-rank call is extra). At the third-party Railway memory price quoted earlier ($10 per GB a month) that is about $29 to $31 a month **[Likely]**.
## 6. Not measured
Quality of retrieval on this enlarged index (the landmark check costs a few cents; the last real tests were on the earlier index and found 8% of shown passages misleading); how many second copies of a judgment remain; whether the criminal-law wording test lets through other non-criminal cases among the 5,830 post-2017 Guwahati judgments (all have criminal case numbers, so none by case type).
