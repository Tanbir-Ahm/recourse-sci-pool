# Court files read (2026-10-22)

The owner downloaded the 888 criminal-subject judgments that the open bucket lacks (`ghc/court_lists/missing_judgments_criminal.csv`) from ghconline.gov.in and uploaded them as `p01.zip` to `p11.zip` (94 MB). `ghc/store_court_files.py` reads them; the text is on branch `claude/ghc-bucket` in `shards/YYYY-MM.jsonl.gz`, tagged `text_source: "court"`, key `court:<file name>`.

| | files |
|---|---|
| PDFs in the zips | 868 (20 of the 888 failed to download; `retry_failed.ps1` is for them) |
| Skipped as not wanted (AB, BA, BailAppln, IA, I.A. types) | 57 |
| **Stored** | **811** (2011: 62, 2012: 183, 2013: 101, 2014: 44, 2015: 57, 2016: 160, 2017: 204) |
| Flagged "reasoned judgment" by the rough v1 rule | 776 |
| Unreadable | 0 |
| Image-only (scan, no text; no OCR tool here) | 2: `CrlPet5532016` (16 pages), `CrlRevP3842011` (9 pages) |
| Very short (1 page, 318 characters) | 1: `CrlMC5232012` (a Crl.MC; kept, since the owner's MC exclusion was for the bucket's MC type; say if it should go) |

Median length 12,660 characters; 13.5 million characters in all. Case types: mostly criminal appeals (jail), criminal petitions and criminal revisions, as expected. A file listed under several case numbers is stored once with all numbers in `case_number`. `court_lists/by_month/*.csv` rows now show `court_file_received=yes` for these files.

Still to do: the 20 failed downloads (retry script), the two scans (need OCR or the bucket's copy; the bucket does not hold them), and cleaning the 80-column word splits before any embedding. Nothing has been embedded.
