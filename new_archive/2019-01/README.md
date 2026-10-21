# Full month: judgments of January 2019 from the court's newer archive (2026-10-21)

Source: the owner's search for 01-01-2019 to 31-01-2019 (CAPTCHA answered by him), links copied with the console snippet, no further result pages (his report). `links_all.txt` is the list as received (150 links, all distinct, including the 53 of `../2019-01-01_to_10/`). `../first_pass.py` is the script as run (it keeps PDFs outside the repo and does not fetch a PDF twice); `results.csv` has one row per link. PDFs and extracted text are not committed. 74 fetches this time, 41 reused from the first pass; 1.5 to 2 s apart, one request per link, no 403 or 429. The fetch took about 8 minutes.

## What the 150 links were
115 English judgments, 34 vernacular translations (Hindi, Marathi, Kannada, Assamese, Gujarati, Telugu, Urdu, Bengali; not fetched), and 1 link without a diary number (the court's defect, same as before; not fetchable).

## The 115 English judgments [Certain, read from the files]
All valid typeset PDFs: 3 to 150 pages (median 13), no embedded images, none under 1,500 characters, no two identical. No scans.

## Against the bucket (date plus party words; the earlier 9 misses were read by hand; the 32 below are by the matcher)
- **83 of 115 are in the bucket; 32 are not (28%).**
- **Non-reportable: 15 of 15 are missing.** Reportable: 15 of 95 missing (16%); no marker: 2 of 5.
- **Criminal (heading on page 1, a rough test): 18 of 34 missing (53%)**, against 14 of 81 for the rest (17%). Part of this is the same effect: 11 of the 11 criminal non-reportable judgments are missing. Among reportable ones only, criminal 6 of 21 missing (29%) against 9 of 74 (12%). [Likely] The gap is larger for criminal matters, which is the part the index keeps.
- **The copied list lacks 6 judgments the bucket holds for January 2019** (Madhav Hari Joshi v. LIC, 4 Jan; Chander Bhan Singh v. CBI, 8 Jan; Union of India v. Krishna Kumar, 14 Jan; Anss Rajashekar v. Augustus Jeba Ananth, 18 Jan; Raju Ambadas Gangekar v. State of Maharashtra, 24 Jan; Hirandra Kumar v. High Court of Allahabad, 29 Jan). [Certain] None of their names occurs on page 1 of any fetched judgment, so it is not a matching error. Cause unknown: the court's page may not list them, or the snippet missed their links (it keeps only links containing `_Judgement_`), or one of them is the link without a diary number.
- For this month: bucket 90 judgments, court list 115 English; union at least 121; the bucket holds at most 90 of 121 (74%). [Likely] This agrees with the 77% overall estimate in `coverage/COVERAGE_NOTE.md`.

## What this does not show
It is one month. Nothing here says whether any of these judgments is good law, and nothing was fed to the index, the checker or the register.
