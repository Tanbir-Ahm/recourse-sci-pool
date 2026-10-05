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

A sample of bucket judgments from each tier was downloaded, and each was compared with the crawl by shared 8-word runs. A real match shares 135 to 470 runs with the crawled text; a non-match shares under 35, so the line is clean. (A looser test of 8 shared runs would be fooled by court boilerplate; it is not used.)

| Tier | Sampled | The matched crawled text really is the same judgment |
|---|---|---|
| T1 | 40 | 40 |
| T2 | 20 | 20 |
| T3 | 50 | 49 |
| T3x | 40 | 39 are in the crawl; for 36 the best-matching text is one of those named |
| none | 70 | 54 are in the crawl anyway (77%); 16 are not (23%, 95% range 15% to 34%) |

So "none" mostly means "the names were too different to match" (spelling, OCR slips such as `V!SHWANATH`, a name not read from the crawled text), not "absent from the crawl".

## 4. What this means (est.)

- Of the bucket's 31,027 judgments up to 4 May 2017, about **29,800 (96%) are already in the crawl**. About **1,300 are not**: central estimate, plausible range 0.7 thousand to 2.5 thousand. [Likely]
- The earlier idea that the bucket fills the crawl's 1990s to 2004 gaps is **wrong**: the two sources overlap almost completely, so both are missing the same judgments. Against IK's list the crawl holds 58% of 1990 to 1999 and the bucket 54%; together they hold only a little more than the crawl alone.
- The crawl holds several thousand judgments the bucket lacks. [Likely]
- What the bucket really adds is (a) the 7,125 judgments after 4 May 2017, (b) about 1,300 older ones, and (c) metadata for the matched ones: neutral citation numbers (INSC) and law-report (SCR) citations, which the crawl lacks. Those can be attached to the crawl's judgments with no PDF download.

## 5. Download sizes (exact, from the bucket's own file listing)

| What | PDFs | Size |
|---|---|---|
| Judgments after 4 May 2017 | 7,125 (2 have no file under the standard name) | 2.90 GB |
| Unmatched older judgments ("none"), to find the roughly 1,300 truly missing ones by comparing texts | 4,833 (2 have no file under the standard name) | 2.45 GB |
| Everything in the bucket (the listing counts both copies of the 5,181 duplicates) | 43,327 | 22.6 GB |

The "about 2 GB" figure used earlier for the later judgments was too low; it is 2.9 GB. Never committed to git; downloaded in batches, text extracted, PDFs deleted.

## 6. Limits

- The tiers are name matches. Two different judgments with near-identical party names on the same day could be merged in T1 (none seen in the 40 checked). T3 and T3x have no date check, and one T3 and a few T3x samples did not match.
- The sample for "none" is 70, so the 77% has a wide range (66% to 85%).
- The crawl's own texts are searched on their first 3,500 characters only.
- Rows whose PDF is not under the standard name: `GIRIDHARI PARAMANAND VADHAVA` (path `S_1996_6_631_656`), `K. VENKATACHALAM` (`1999_2_857_879`), `HIGH COURT OF PUNJAB AND HARYANA ... ISHWAR CHAND JAIN` (`1999_2_834_856`), `MOHD. NAUSHAD` (`2023_10_160_288`), `ROOPWANTI` (`2023_3_30_compressed`).
- The sample PDFs were checked only for shared text with the crawl, not for text quality.

## Files

- `list_bucket_sizes.py`: lists the bucket's PDF files with sizes (anonymous listing).
- `bucket_registry_match.py`: removes second listings and does the match; writes `registry.csv` (here gzipped as `registry.csv.gz`: one row per distinct bucket judgment with date, title, citation, INSC number, file, size, tier and matched crawl IDs).
- `validate_match.py`, `validate_counts.py`: the sample check against real texts; `validation.json`, `validation_counts.json` are its outputs.
- `build_worklist.py`, `worklist.csv.gz`: the 11,958 judgments the downloader (`../../sci_bucket.py`) fetches, with their metadata (scope `after`: 7,125; scope `none`: 4,833; 4 rows have no file under the standard name).
- Paths inside the scripts point at the session's scratch folder; change them to re-run.
