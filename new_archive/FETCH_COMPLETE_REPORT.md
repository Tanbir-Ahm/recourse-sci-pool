# Supreme Court newer archive: fetch complete (2026-10-22)

Court's newer archive, 5 May 2017 to October 2026 (links supplied by the owner from the court's listing page). Text is stored on branch `claude/sci-court-newer` (monthly shards). Nothing here says a judgment is good law.

## Totals
| | count |
|---|---|
| English judgments fetched, text stored | **10,409** (audit: 0 problems) |
| Vernacular translations (listed, not fetched) | 1,185 |
| Links with no diary number in the address (not fetchable) | **74** (2017: 26, 2018: 29, 2019: 19) |
| `new_archive/catalogue.csv` rows | 10,409 (7 links that appeared in two months' lists were merged) |
| With a parsed pair of parties | 10,258 (158 without; 151 after merging) |
| With a case number | 10,330 (79 without) |
| With a neutral citation (INSC) | 3,772 |
| With translations listed | 1,104 |

## Per year, against the open bucket (Dattam Labs)
Bucket match is by decision date plus party words. "beyond" = newer than the bucket's horizon (12 Aug 2026).

| Year | English judgments | In bucket | Not in bucket | Beyond bucket | Criminal heading* |
|---|---|---|---|---|---|
| 2017 (from 5 May) | 541 | 332 | 209 | 0 | 104 |
| 2018 | 1,119 | 743 | 376 | 0 | 307 |
| 2019 | 1,324 | 992 | 332 | 0 | 378 |
| 2020 | 695 | 545 | 150 | 0 | 175 |
| 2021 | 866 | 654 | 212 | 0 | 233 |
| 2022 | 1,280 | 972 | 308 | 0 | 323 |
| 2023 | 1,059 | 833 | 226 | 0 | 365 |
| 2024 | 1,025 | 740 | 285 | 0 | 396 |
| 2025 | 1,438 | 641 | 797 | 0 | 555 |
| 2026 | 1,062 | 210 | 591 | 261 | 357 |

*A rough marker (a criminal heading on page 1), not a legal classification; the index's own filter decides what is criminal law. Per-year numbers are by the results files; the catalogue's year split differs by 1 to 3 rows where a judgment's date sits at a month edge.

The open bucket's coverage falls from about 70% to 75% in 2017 to 2024 to under half in 2025 and well under a quarter in 2026, so this fetch is the only source for most 2025 and 2026 judgments.

## Neutral citation (INSC) completeness, 2023 onward
| Year | Rows | With INSC |
|---|---|---|
| 2023 | 1,060 | 283 (the court began printing INSC numbers during 2023) |
| 2024 | 1,026 | 1,014 |
| 2025 | 1,438 | 1,414 |
| 2026 | 1,062 | 1,055 |
Missing in 2024 to 2026: 12, 24 and 7 rows. Not checked one by one; likely older-style headers or a layout where the number is not on page 1 [Likely].

## Caveats
- The 74 links with no diary number are a defect on the court's page (`supremecourt//2018/2018__Judgement_...`). They are not in the catalogue. See FOLLOW_UPS item 1o.
- Case names come from page 1 of each judgment; names with many parties are shortened ("... and others").
- Files: `new_archive/<YYYY-MM>/results.csv` is the audit record per month; `new_archive/audit_fetch.py` re-checks everything.
