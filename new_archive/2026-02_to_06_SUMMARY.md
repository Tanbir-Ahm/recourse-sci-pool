# February to June 2026 from the court's newer archive (2026-10-21)

Source: five 30-day searches the owner ran in his own browser (CAPTCHA answered by him), links saved by the console snippet. Per month: `2026-MM/links_all.txt` (as received) and `2026-MM/results.csv` (one row per link). Script `first_pass.py`, as run, with the bucket's 2026 list (`state/worklists/refresh_20261005.csv.gz` on branch `claude/sci-bucket`). Fetched one request per link, 1.5 to 2 s apart, in one unattended run of about 65 minutes (10:17 to 11:22); no 403, 429 or challenge. PDFs and text are not committed.

## What the 504 links were [Certain]
All 504 were English judgments (no translations, no link without a diary number) and all 504 fetched as valid PDFs. No two identical. 2 to 417 pages, none under 1,500 characters; an image occurs on almost all of them but on a few pages each, as in January 2026 (typeset documents, not scans).

## Against the open bucket, month by month
| Month | Court list | Not in bucket | Non-reportable (all missing) | Bucket's rows for the month | Bucket judgments not in the list |
|---|---|---|---|---|---|
| Jan 2026 | 107 | 64 (60%) | 24 of 24 | 43 | 1 |
| Feb 2026 | 94 | 57 (61%) | 22 of 22 | 38 | 1 |
| Mar 2026 | 86 | 59 (69%) | 16 of 16 | 27 | 0 |
| Apr 2026 | 126 | 93 (74%) | 23 of 23 | 35 | 2 |
| May 2026 | 161 | 132 (82%) | 39 of 39 | 29 | 0 |
| Jun 2026 | 37 | 19 (51%) | 5 of 5 | 19 | 1 |
| **Jan to Jun** | **611** | **424 (69%)** | **129 of 129** | **191** | **5** |

- Reportable: 276 of 455 missing (61%); no marker: 19 of 27. Criminal heading (rough test): 136 of 194 missing (70%), other matters 288 of 417 (69%). In 2026 the gap does not depend on subject; it depends on the month.
- **The bucket's share of the court's list falls through the year:** about 40% in January, 30% in March, 22% in May (it holds 191 of at least 616 for the six months, at most 31%). The bucket's last 2026 batch was 12 August, and the court's list is longer even for months it covers. [Likely] The bucket lags more for recent months, and it never takes most non-reportable judgments.
- The bucket holds 5 judgments (of 191) that the owner's lists do not, so the copied lists were nearly complete for 2026 (5 in 616).
- June has only 37 judgments, the court's summer vacation period [Guessing].

## What this does not show
Nothing says whether any judgment is good law. Nothing was fed to the index, the checker or the register.
