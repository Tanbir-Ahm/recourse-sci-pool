# Guwahati post-2017 criminal-type documents: what is stored

| Year | In worklist | Stored | Errors | Court-listed | JUDGMENT heading | Body 5,000+ chars | Any signal | Scan-like |
|---|---|---|---|---|---|---|---|---|
| 2018 | 1834 | 1834 | 0 | 474 | 628 | 644 | 819 | 1 |
| 2019 | 1809 | 1809 | 0 | 404 | 535 | 555 | 676 | 0 |
| 2020 | 1020 | 1020 | 0 | 213 | 332 | 450 | 510 | 0 |
| 2021 | 1142 | 1142 | 0 | 194 | 324 | 431 | 472 | 0 |
| 2022 | 1589 | 1589 | 0 | 246 | 442 | 619 | 706 | 0 |
| 2023 | 1872 | 1872 | 0 | 389 | 574 | 778 | 855 | 0 |
| 2024 | 1968 | 1909 | 0 | 345 | 623 | 877 | 962 | 0 |
| 2025 | 2255 | 2255 | 0 | 440 | 758 | 1080 | 1164 | 0 |
| 2026 | 1934 | 1923 | 11 | 325 | 540 | 881 | 954 | 0 |
| **All** | 15423 | 15353 | 11 | 3030 | 4756 | 6315 | 7118 | 1 |

Text stored: 156,920,145 characters (about 40.5M tokens if all of it were embedded; only the judgments would be).

## Notes (2026-10-23, fetch finished)
- Worklist 15,423 rows = 15,361 distinct PDF files (62 rows share a file). Stored with text: 15,353 rows; **11 documents have no PDF in the bucket** (the bucket's own metadata says it does not hold the file; answers 404): all decided 9 and 10 August 2026. 59 rows of 2024 and a few others share a file with another row, so "Stored" is below "In worklist" for 2024.
- One scan-like document (2018, no readable text): flagged `scan_like`.
- Signals: court-listed (the court's own "Judgement" list), heading says JUDGMENT after the cause title, body of 5,000+ characters; "Any signal" is the union. Nothing is embedded and nothing was spent.
- Data: branch `claude/ghc-bucket`, folder `shards_post2017/` (monthly shards, 46 MB).
