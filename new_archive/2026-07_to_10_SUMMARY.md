# July to October 2026 from the court's newer archive (2026-10-21)

Source: four 30-day searches the owner ran in his own browser (CAPTCHA answered by him), links saved by the console snippet. Per month: `2026-MM/links_all.txt` (as received) and `2026-MM/results.csv`. Script `first_pass.py` as run, with the bucket's 2026 list (`state/worklists/refresh_20261005.csv.gz` on branch `claude/sci-bucket`). One request per link, 1.5 to 2 s apart, one unattended run of about 60 minutes (11:26 to 12:25); no 403, 429 or challenge. PDFs and text are not committed.

## What the 451 links were [Certain]
All 451 were English judgments (no translations, no link without a diary number) and all fetched as valid PDFs. No two identical; 2 to 489 pages (median 17); none under 1,500 characters. Page 1 marker: 304 REPORTABLE, 133 NON-REPORTABLE, 14 unmarked.

## Against the open bucket
The bucket's newest decision date is 12 August 2026 (`first_pass.py` now marks later judgments `beyond`, not missing).

| Month | Court list | In the bucket | Not in the bucket | Newer than the bucket (12 Aug) |
|---|---|---|---|---|
| Jul 2026 | 127 | 15 | 112 (88%) | 0 |
| Aug 2026 | 138 | 8 | 55 of 63 (87%) | 75 |
| Sep 2026 | 121 | 0 | 0 | 121 |
| Oct 2026 (to 16 Oct) | 65 | 0 | 0 | 65 |
| **Total** | **451** | **23** | **167** | **261** |

- Within the bucket's dates the bucket holds 23 of 190 (12%) for July and early August; all 56 non-reportable judgments of those dates are missing.
- 261 judgments (58%) are newer than anything the bucket lists. They are not "missing" yet; they are simply not covered. Whether the bucket has added batches since 5 October was not checked (`bucket_refresh.py plan` would show; it needs the bucket reachable).
- **January to mid-October 2026 together:** 1,062 judgments. Of the 801 decided on dates the bucket covers, 210 are in the bucket (26%) and 591 are not (74%); 261 are newer. The bucket also holds 5 judgments that the owner's lists lack.

## A second check: are the owner's lists complete? (neutral citations)
The court gives every 2026 judgment a running neutral citation ("2026 INSC n"), and the PDFs print it. The catalogue holds 1,055 distinct numbers out of 1 to 1,149 (the highest printed). **94 numbers are missing (8%).** The bucket holds 5 of them (the 5 judgments above); the other 89 are neither in the owner's lists nor in the bucket. [Likely] The lists are about 92% complete. A missing number may be a judgment the page did not return, a link the snippet did not catch, or a number with no public judgment; which one is not known. `2026_missing_insc_numbers.csv` lists the 94 numbers with the decision dates of their neighbours (35 sit between two judgments of the same day), so a person can look at a day on the court's page and check. The same test works for 2025 and 2024 once those years are fetched.

## What this does not show
Nothing says whether any judgment is good law. Nothing was fed to the index, the checker or the register.
