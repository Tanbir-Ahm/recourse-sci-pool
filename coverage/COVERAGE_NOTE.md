# Coverage note, 2026-10-05: what our sources hold, against Indian Kanoon's own list

Why this exists: to decide how to check whether a judgment is still good law using our crawl, and what the open AWS bucket and Indian Kanoon (IK) can add. Everything here is a measurement or an estimate, labelled as such. Nothing here is legal advice and nothing decides "good law": that stays a human's call (Recourse's own rule for its currency pipeline).

Numbers marked (est.) are estimates. The scripts that produced them are in `scripts_as_run/`, saved exactly as they were run; `year_counts.csv` holds the per-year numbers.

## 1. Where our crawl ends

| Item | Value |
|---|---|
| Source | `https://api.sci.gov.in/jonew/judis/<id>.pdf`, crawled 2026-09-30 to 2026-10-02 |
| Judgments saved | 36,928 (a little under 37,000), in IDs 1 to 44,905 |
| Empty IDs recorded | 8,821 in total; 844 in a row after the last judgment (IDs 44,906 to 45,749); 45,749 is the highest ID scanned |
| Last judgment saved | ID 44905: *Dev Raj and Ors etc. v. State of Punjab and Ors*, Civil Appeal No. 6346-54 of 2017, dated **4 May 2017** (a one-page order, 879 characters) |
| Last substantial judgment | ID 44898: *Sama Aruna v. State of Telangana & Anr.*, Criminal Appeal No. 885 of 2017, 3 May 2017, 15 pages |
| PDFs kept? | No. Each shift extracted the text and deleted the PDF. Kept per judgment: text, page count, PDF size, sha256 of the PDF |

An earlier remark that the crawl ends "around 2016" was wrong: it ends in early May 2017. Reproduce with `scripts_as_run/last_crawl_id.py`.

## 2. Coverage against IK's yearly list

IK's list: 55,332 Supreme Court judgments for 1968 to 2026, typed from a screenshot of `https://indiankanoon.org/browse/supremecourt/` on 2026-10-05 (not scraped; a digit could be misread). Cells are the number of judgments, with the share of IK's count.

| Period | IK | Our crawl (est.) | Open bucket | Recourse catalogue |
|---|---|---|---|---|
| 1968-79 | 5,919 | 3,623 (61%) | 3,619 (61%) | 3,619 (61%) |
| 1980-89 | 4,473 | 2,786 (62%) | 2,700 (60%) | 2,700 (60%) |
| 1990-99 | 11,983 | 6,910 (58%) | 6,497 (54%) | 6,496 (54%) |
| 2000-04 | 6,688 | 4,561 (68%) | 3,276 (49%) | 3,276 (49%) |
| 2005-09 | 8,843 | 7,934 (90%) | 5,815 (66%) | 5,812 (66%) |
| 2010-14 | 5,460 | 5,148 (94%) | 4,007 (73%) | 3,984 (73%) |
| 2015-17 | 2,337 | 2,437 (104%) | 2,080 (89%) | 2,034 (87%) |
| 2018-25 | 8,646 | 3 | 6,675 (77%) | 6,622 (77%) |
| 2026 (to 12 Aug) | 983 (to early Oct) | 0 | 214 (22%) | 0 |

**Correction, 2026-10-05:** an earlier version of this table counted the bucket's metadata rows (43,333). The tables list 5,181 judgments twice, so the bucket holds 38,152 distinct judgments; the figures above are distinct counts. The old figures for 1968 to 1979 (99%) and 1980 to 1989 (79%) were wrong. See `bucket_match/MATCH_REPORT.md`.

Cautions:
- The crawl's decision year is estimated from dates in the text. Single years near 2015 to 2017 are noisy (the estimate shows 2016 at 150% of IK), so read the period totals, not single years.
- IK may count things the other sources do not (unreported judgments, possibly duplicates or orders). "IK has more" does not prove every extra is a distinct judgment.
- The bucket and the crawl each hold about 60% of IK's count for 1968 to 1999, and they overlap almost completely (section 3a), so the bucket does not fill the crawl's gaps for those years. [Likely]
- The newest period is the weakest: the bucket has 897 of IK's 1,421 judgments for 2025 (63%) and 214 of IK's 983 for 2026 (22%, decisions to 12 August 2026); about 1,970 judgments from 2018 to 2025 are on IK but not in the bucket. The bucket's 2026 folder was added in small batches in June, July and August 2026; an earlier version of this note said 2026 was empty because only the 1950 to 2025 tables had been fetched.
- Recourse's case catalogue (38,026 cases) matches the bucket's distinct judgments almost exactly (about 120 recent ones are missing), so its "find any judgment" reach has the same gaps.

## 3. The open bucket (indian-supreme-court-judgments, CC-BY-4.0, Dattam Labs)

- **38,366 distinct judgments** for 1950 to 2026 (38,152 for 1950 to 2025, plus 214 for 2026) in per-year metadata tables (43,333 rows; 5,181 judgments are listed twice). 7,125 of the 1950-to-2025 judgments are dated after the crawl's last date (450 of the 732 for 2017), and all 214 of 2026 are. The bucket's PDFs total 22.6 GB (43,327 files; both copies of the duplicates count); the 7,125 later ones are 2.90 GB.
- Each record has title, petitioner, respondent, judge, law-report citation, neutral citation (INSC), decision date, how it was disposed of, and the PDF's file name (law-report volume and pages).
- **Scanned or not:** every sampled PDF from 2012 to 2017 is a scan with machine-read text (35 of 35; 685 of 685 pages carry an embedded image). Every sampled PDF from 2018 to 2025 is typeset text (56 of 56; 0 of 1,025 pages). So only 2017 is scanned within the proposed extension.
- **Clutter to clean:** 2018 to 2022 PDFs carry margin letters A to H as lone lines (roughly 100 to 180 per PDF in the sample); 2023 has a few, 2024 on none. Running headers and the law-report headnote appear in all years.
- **Text fidelity on scanned years** (27 judgments present in both the crawl and the bucket, 2012 to 2017): a median of 76% of the crawl's 8-word runs also appear in the bucket text, implying a word-level difference of roughly 3% (median 3.4%). This is an upper-bound-style estimate, because it also counts headers, margin letters and page breaks. Of 305 "X v. Y" case-name citations spotted in the crawl text, 250 (82%) were also found in the bucket text; per judgment the median is 87% (range 59% to 100%, 16 judgments). Visible scan errors: split names ("ASH OK BHUSHAN"), stray apostrophes.
- **Text fidelity on 2018 to 2025:** no court-site copy exists to compare against, so accuracy there is untested against ground truth. A vocabulary-based quality test was inconclusive and is not kept.
- Sample: *Basalingappa v. Mudibasappa* (Criminal Appeal No. 636 of 2019) is `2019_6_555_576_EN.pdf`; its text names *Rangappa v. Sri Mohan, (2010) 11 SCC 441* as "A Three-Judge Bench of this Court".

## 3a. How much of the bucket is already in the crawl

Matched on party names and dates, then settled for the unmatched older judgments by comparing the downloaded texts with the crawl's; full detail in `bucket_match/MATCH_REPORT.md`.

- Of the bucket's 31,027 distinct judgments dated up to 4 May 2017, about **94% (about 29,200) are already in the crawl**. About **1,840 are not** (range roughly 1,700 to 2,000). Sample check of the name matches: 39 of 40 and 20 of 20 for the strongest tiers, 88 of 90 for the name-only tiers. [Likely]
- The first estimate (96%, about 1,300 missing) was too optimistic: it counted 50 shared 8-word runs as proof of the same judgment, and the full run showed that band is mostly different judgments quoting the same passages.
- So for 1990 to 2004 the bucket adds a few hundred to about a thousand, not the thousands needed to close the gap. Both sources lack roughly the same 40% of what IK lists for 1968 to 1999. That gap would need IK's API or the court's own newer archive.
- The judgments the crawl lacks are concentrated in a few years (1994: 354; 1999: 190; 1995: 148; 1993: 133; 2004: 114), which suggests holes in the crawl for those years. [Likely]
- What the bucket adds: the 7,125 judgments after 4 May 2017, about 1,840 older ones, and neutral (INSC) and law-report (SCR) citation numbers for the judgments it shares with the crawl.

## 4. Citation pilot: later judgments that name a landmark

Counted by name, later IDs only. "Index" is the 8,101-judgment criminal-law index; "full crawl" is all 36,928 texts (to May 2017).

| Case | Index | Full crawl |
|---|---|---|
| Bhajan Lal (1990) | 191 | 237 |
| Baldev Singh (1999) | 64 | 104 |
| Jadeja (2010) | 22 | 29 |
| Noor Aga (2008) | 21 | 22 |
| Rangappa (2010) | 7 | 12 |
| Md. Ibrahim (2009) | 1 | 9 |
| Lalita Kumari (2013) | 7 | 8 |
| Arnesh Kumar (2014) | 1 | 1 |
| Nanda Gopalan (2015) | 0 | 0 |

- A worked example: Jadeja (2010) says the "substantial compliance" idea introduced in Joseph Fernandez and Prabha Shankar Dubey (id 25607) "is neither borne out from the language of sub-section (1) of Section 50 nor … in consonance with … Baldev Singh". A pattern search found it; whether it counts as overruling is for a human.
- Crude cue words misfire ("doubted" fired on "settled beyond doubt"; "overruled" fired on counsel's argument). Keep only sentences from passages tagged as the court's reasoning.
- The newest landmarks (2014 to 2015) have almost no later citations in our data, because the crawl ends in May 2017.

## 5. What can and cannot be reached from a cloud session

| Host | From a session |
|---|---|
| Open bucket (S3, ap-south-1) | reachable |
| `api.sci.gov.in` (the court's server) | blocked (proxy 403) |
| `indiankanoon.org` and `api.indiankanoon.org` | blocked (proxy error) |

Changing this is a setting on the cloud environment's network access, the owner's choice. We do not scrape IK's site: our own review workbook says not to scrape or bulk-download, IK sells API access, and we have not read its terms.

## 6. Plan (revised 2026-10-05; steps 1 to 3 done, the rest not started)

Decided with the project owner: text only is kept (no PDFs in any repo); the data branch `claude/sci-bucket`; the metadata-only match came first.

1. Treat the **crawl as the corpus up to 4 May 2017**. Attach the bucket's neutral (INSC) and law-report (SCR) citation numbers to the crawl's judgments from the match (no download). *Not yet done: the match table `bucket_match/registry.csv.gz` has the links; nothing yet writes them into a combined registry.*
2. **Done:** the 7,125 judgments after 4 May 2017 (7,123 saved, 2 have no file in the bucket) are on `claude/sci-bucket`, about 105 MB, text only. Margin letters, running headers and the law-report headnote are *not* removed from the saved text; `sci_bucket.clean_text()` does that when reading, and `body_start` marks where the court's own judgment begins (found for 89% to 100% of judgments).
3. **Done:** the 4,833 unmatched older judgments (4,831 saved) were downloaded and compared with the crawl's texts: 3,084 are in the crawl, 137 uncertain, 1,610 not (`bucket_match/none_resolution.csv.gz`). Those 1,610 (plus the uncertain ones) are the older judgments the crawl lacks.
4. Build the currency evidence as a **review bundle per case** (later citing cases, the court's own sentences, bench strength, the statute's BNS/BNSS successor), never a verdict. Run one extractor over the crawl and the bucket.
5. Use the IK **API**, only for the 33 priority cases and the newest period (2025 to now), through Recourse's existing pipeline. IK's yearly list is an audit yardstick, not a data source. Both open sources lack about 40% of what IK lists for 1968 to 1999; only IK's API or the court's own newer archive could fill that.
6. Test whether citation counts improve ranking (the search misses some landmarks) on the 12-question test.
7. Monthly refresh needs a cloud routine like the crawl's (`BUCKET_RUNBOOK.md`, an environment that can reach the bucket; `sci-index` can). A routine session starts from `main`, so the downloader would first have to be on `main`; that is a merge for the owner to approve.

## 7. Open items

- The "Cited by" numbers for Rangappa (`https://indiankanoon.org/doc/150051/`) and Bhajan Lal (`https://indiankanoon.org/doc/1033637/`) are to be read off the pages by hand. Compare with Rangappa 12 and Bhajan Lal 237 above; IK's figure includes High Courts and later years unless filtered.
- The `Judgments` sheet of the authority workbook (is each case still good law) is still blank.
- Five bucket rows have no file under the standard name (listed in `bucket_match/MATCH_REPORT.md`; 4 are in the download lists).
- The text quality of the 2018 to 2025 downloads has not been tested against ground truth (no second copy exists); the 2017 judgments are scans with machine-read text, so expect the same small errors as the crawl's older texts.
