# January 2026 from the court's newer archive (2026-10-21)

Source: the owner's search for 01-01-2026 to 31-01-2026 (CAPTCHA answered by him), links saved by the console snippet as `links_01-01-2026_to_31-01-2026.txt`. `links_all.txt` is that list (107 links, all distinct, all English judgments: no translations and no link without a diary number this time). `../first_pass.py` is the script as run (now takes extra bucket lists); `results.csv` has one row per link. PDFs and text are not committed. 107 fetches, 1.5 to 2 s apart, one request each, no 403 or 429; the run took about 14 minutes (the court's server was slower than in the 2019 run).

The bucket's 2026 metadata is not in `coverage/bucket_match/worklist.csv.gz`; it comes from `state/worklists/refresh_20261005.csv.gz` on branch `claude/sci-bucket` (214 judgments of 2026, decisions to 12 Aug 2026; 43 of them are January).

## The 107 judgments [Certain, read from the files]
All valid PDFs, 2 to 271 pages (median 26), a text layer in every one (median 1,356 characters a page, none under 976), no two identical. An embedded image appears on 106 of 107, but on a median of 3.5% of pages (at most 20%), so these are typeset documents with an occasional image, not scans. [Guessing] the image is a seal or code on a page or two.

## Against the bucket
- **43 of 107 are in the bucket; 64 are not (60%).**
- **Non-reportable: 24 of 24 missing.** Reportable: 38 of 80 missing (48%). No marker: 2 of 3.
- **Criminal (heading on page 1, rough): 18 of 32 missing (56%)**, other matters 46 of 75 (61%). Unlike January 2019, no difference by subject.
- The bucket has 43 judgments for January 2026; 42 are matched by the list; **1 bucket judgment is not in the list** (State of U.P. v. Anurudh, 9 Jan, 2026 INSC 47). So the court's list holds at least 108 judgments for the month, the bucket 43: **the bucket holds at most about 40%**. [Likely] This agrees with the 22% (to 12 August) in `coverage/COVERAGE_NOTE.md`, which compared against Indian Kanoon's count.

## What this does not show
It is one month. Nothing here says whether any of these judgments is good law, and nothing was fed to the index, the checker or the register.
