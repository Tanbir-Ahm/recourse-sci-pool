# Bucket against crawl: a match on metadata only, 2026-10-05

Nothing was downloaded for the match itself. It used the bucket's metadata tables, the bucket's own file listing (names and sizes), and the first 3,500 characters of each crawled text. A few hundred PDFs were downloaded afterwards, only to check the match against the real texts. Numbers marked (est.) are estimates from a sample. The scripts are saved as run in this folder.

## 1. A correction to the earlier bucket count

The bucket's metadata tables list **5,181 judgments twice** (same file path, same date, same title, in two different years' tables). Earlier notes counted rows, so they said 43,333 judgments. The number of distinct judgments is **38,152**. The duplicates sit mostly in the 1950s to 1980s. Consequences:

- The bucket's coverage of those decades against Indian Kanoon (IK) is about 60%, not 99% (1968 to 1979) or 79% (1980 to 1989).
- Recourse's case catalogue (38,026) is therefore not "missing 5,300 bucket cases". It matches the distinct bucket almost exactly. The only gaps are about 120 recent judgments (2010 to 2025).
- Of the bucket's 7,408 rows for 2017 to 2025, 7,125 distinct judgments are dated after 4 May 2017.

`../year_counts.py` now counts distinct judgments and `../year_counts.csv` is regenerated.

## 2. What the match found

The bucket's 31,027 distinct judgments dated on or before 4 May 2017 (the crawl's last date) were looked up in the crawl by party names and, where the crawled text gave a date, by date.

| Tier | Meaning | Judgments |
|---|---|---|
| T1 | names match and the crawled text's own date equals the decision date | 18,470 |
| T2 | names match, crawled date within 7 days | 122 |
| T3 | names match one crawled text that gave no date | 5,527 |
| T3x | names match several crawled texts that gave no date | 2,075 |
| none | no crawled text matched on names | 4,833 |
| after | dated after 4 May 2017 | 7,125 |
| | total | 38,152 |

By period (distinct judgments; columns T1 to after as above):

| Period | Distinct | T1 | T2 | T3 | T3x | none | after |
|---|---|---|---|---|---|---|---|
| 1950-67 | 3,483 | 2,855 | 31 | 10 | 11 | 576 | 0 |
| 1968-79 | 3,619 | 3,255 | 11 | 5 | 6 | 342 | 0 |
| 1980-89 | 2,700 | 2,450 | 11 | 5 | 9 | 225 | 0 |
| 1990-99 | 6,497 | 4,125 | 42 | 143 | 165 | 2,022 | 0 |
| 2000-04 | 3,276 | 2,574 | 21 | 50 | 54 | 577 | 0 |
| 2005-09 | 5,815 | 3,208 | 6 | 1,554 | 554 | 493 | 0 |
| 2010-14 | 4,007 | 3 | 0 | 2,732 | 974 | 298 | 0 |
| 2015-17 | 2,080 | 0 | 0 | 1,028 | 302 | 300 | 450 |
| 2018-25 | 6,675 | 0 | 0 | 0 | 0 | 0 | 6,675 |

T1 is rare after 2009 because the date was read only from the crawl's old-format opening ("DATE OF JUDGMENT"), so later texts have no date and their matches land in T3 or T3x.

## 3. Checking the match against the real texts

A sample of bucket judgments from each tier was downloaded, and each was compared with the crawl by shared 8-word runs. The measure that separates real copies is the **share** of the crawled text's opening (`frac`) that the bucket text contains. A raw count of shared runs is not enough: the full run (section 7) showed that a count of 50 lets in different judgments that quote the same passages. The cut-offs, set on the full run, are 0.3 or more = the same judgment, 0.2 to 0.3 = uncertain, under 0.2 = not the same.

| Tier | Sampled | Same judgment found in the crawl (frac 0.3 or more) |
|---|---|---|
| T1 | 40 | 39 (the other was uncertain) |
| T2 | 20 | 20 |
| T3 | 50 | 49 |
| T3x | 40 | 39 are in the crawl; for 36 the best-matching text is one of those named |
| none | 70 | 48 are in the crawl anyway (69%); 2 uncertain; 20 are not (29%) |

So "none" is a mixture: about two thirds are judgments whose names were too different to match (spelling, OCR slips such as `V!SHWANATH`, a name not read from the crawled text), and about a third are truly absent.

## 4. What this means (est.; revised after the full text comparison in section 7)

- Of the bucket's 31,027 judgments up to 4 May 2017, about **29,200 (94%) are already in the crawl**. About **1,840 are not** (range roughly 1,700 to 2,000): 1,610 shown by the full comparison, 137 uncertain, 2 with no file, plus an allowance of about 160 from the name-only tiers (T3, T3x). [Likely]
- The earlier idea that the bucket fills the crawl's 1990s to 2004 gaps is **mostly wrong**: the two sources overlap almost completely, so both are missing the same judgments. Against IK's list the crawl holds 58% of 1990 to 1999 and the bucket 54%; the 1,840 add only a little.
- The crawl holds several thousand judgments the bucket lacks. [Likely]
- What the bucket really adds is (a) the 7,125 judgments after 4 May 2017, (b) about 1,840 older ones, concentrated in the 1990s (see section 7), and (c) metadata for the matched ones: neutral citation numbers (INSC) and law-report (SCR) citations, which the crawl lacks. Those can be attached to the crawl's judgments with no PDF download.

## 5. Download sizes (exact, from the bucket's own file listing)

| What | PDFs | Size |
|---|---|---|
| Judgments after 4 May 2017 | 7,125 (2 have no file under the standard name) | 2.90 GB |
| Unmatched older judgments ("none"), to find the truly missing ones by comparing texts | 4,833 (2 have no file under the standard name) | 2.45 GB |
| Everything in the bucket (the listing counts both copies of the 5,181 duplicates) | 43,327 | 22.6 GB |

The "about 2 GB" figure used earlier for the later judgments was too low; it is 2.9 GB. Never committed to git; downloaded in batches, text extracted, PDFs deleted.

## 6. Limits

- The tiers are name matches. Two different judgments with near-identical party names on the same day could be merged in T1 (none seen in the 40 checked). T3 and T3x have no date check, and one T3 and a few T3x samples did not match.
- The sample for "none" was only 70, and its 77% "in the crawl" (by the first, looser rule) was too high; the full run gives 64% (3,084 of 4,833), or 66% counting half the uncertain ones.
- The crawl's own texts are searched on their first 3,500 characters only.
- Rows whose PDF is not under the standard name: `GIRIDHARI PARAMANAND VADHAVA` (path `S_1996_6_631_656`), `K. VENKATACHALAM` (`1999_2_857_879`), `HIGH COURT OF PUNJAB AND HARYANA ... ISHWAR CHAND JAIN` (`1999_2_834_856`), `MOHD. NAUSHAD` (`2023_10_160_288`), `ROOPWANTI` (`2023_3_30_compressed`).
- The sample PDFs were checked only for shared text with the crawl, not for text quality.

## 7. The full download and text comparison (done 2026-10-05)

Both scopes were downloaded with `sci_bucket.py` and saved on branch `claude/sci-bucket`: 7,123 of 7,125 later judgments and 4,831 of 4,833 older ones (the other 4 have no file in the bucket); no errors; no PDF's size differed from the bucket's listing. `resolve_none.py` then compared each of the 4,831 older texts with every crawled text.

| Period | Judgments | In the crawl | Uncertain | Not in the crawl | No file |
|---|---|---|---|---|---|
| 1950-1967 | 576 | 517 | 30 | 29 | 0 |
| 1968-1979 | 342 | 292 | 19 | 31 | 0 |
| 1980-1989 | 225 | 208 | 8 | 9 | 0 |
| 1990-1999 | 2,022 | 891 | 48 | 1,081 | 2 |
| 2000-2004 | 577 | 377 | 10 | 190 | 0 |
| 2005-2009 | 493 | 485 | 1 | 7 | 0 |
| 2010-2014 | 298 | 160 | 7 | 131 | 0 |
| 2015-2017 | 300 | 154 | 14 | 132 | 0 |
| Total | 4,833 | 3,084 | 137 | 1,610 | 2 |

- The judgments the crawl lacks are concentrated: 1994 alone has 354 (of the 1,747 not-in-crawl or uncertain), then 1999 (190), 1995 (148), 1993 (133), 2004 (114). The crawl probably has holes in those years. [Likely; not checked against the crawl's empty-ID ranges]
- Their median length is about 20,000 characters (median 9 pages); only 27 are under 3,000 characters, so they are real judgments, not stubs.
- Why the rule changed: the first version counted 50 or more shared runs as "in the crawl". The full run showed that band (50 to about 150 runs) is mostly different judgments sharing quoted passages: their party names and dates differ. By the share of the crawled opening that matches, the same-decision-date rate is about 3% under 0.2, about 48% at 0.2 to 0.3, and 80 to 91% at 0.3 and above (the remainder differ only by a mistyped date or name). The earlier sample check and the first run's numbers (96%, about 1,300) were too optimistic for that reason.
- `none_resolution.csv.gz` has one row per older judgment (bucket file, title, date, best-matching crawl ID, shared runs, share, verdict).

## Files

- `list_bucket_sizes.py`: lists the bucket's PDF files with sizes (anonymous listing).
- `bucket_registry_match.py`: removes second listings and does the match; writes `registry.csv` (here gzipped as `registry.csv.gz`: one row per distinct bucket judgment with date, title, citation, INSC number, file, size, tier and matched crawl IDs).
- `validate_match.py`, `validate_counts.py`: the sample check against real texts; `validation.json`, `validation_counts.json` are its outputs.
- `resolve_none.py`, `none_resolution.csv.gz`: the full text comparison of the 4,833 older judgments with the crawl (section 7).
- `build_worklist.py`, `worklist.csv.gz`: the 11,958 judgments the downloader (`../../sci_bucket.py`) fetches, with their metadata (scope `after`: 7,125; scope `none`: 4,833; 4 rows have no file under the standard name).
- Paths inside the scripts point at the session's scratch folder; change them to re-run.
