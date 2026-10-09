# Workbook for Mr. Advocate, 2026-10-09 (PRIVATE: holds the answer key; send to him only)

`Mr_Advocate_Sheet.xlsx`, built by `review_tools/build_advocate_sheet.py` (tests `test_build_advocate_sheet.py`) from the owner's workbook, `real30_key_v1.json` and `real30_stale_status_v1.json`. Never to J, S or an AI tool.

| Sheet | Asks | Why we need it |
|---|---|---|
| A Older rulings (16) | Agree or correct what we think the later court did to each older ruling the trap questions use (Salauddin, Ritu Chhabaria, Damodar Prabhu, Dashrath, Mohan Lal, Kanhaiyalal, Karwal, Rajesh Sharma, Social Action Forum, Shafhi Mohammad, Subhash Kashinath Mahajan, Sangeet, and the narrower ones) | The currency light counts a passage as "stale" only for rulings listed as overruled, modified, put on hold or replaced by statute. That list is Claude's reading and is not lawyer-checked. |
| B To verify (7) | The owner's own seven items, word for word | The owner's file says these need a practising advocate. |
| C The 30 questions | 2 to 3 other authorities that would also be a right answer; older or replaced rulings a search might wrongly show; is the expected answer correct and current | The authority-hit test names one authority per question; other right answers are counted as misses today. |
| D Replaced by statute | Rulings whose holding a later statute displaced (Dashrath filled in as the example) | The register and the checker see only court-to-court overrulings; a statute that replaces a ruling (Q9) is invisible to them. |
| E Clean control | One or two questions answerable only from a High Court ruling | Q29 is a cut-off trap, not a clean control (the library lacks the 27 Jul 2026 ruling by chance of coverage). |

When it comes back: his answers go into the private key (never into the search). Authorities he names are looked up in the collection by name and year (`real30_authority_coverage.py` logic); an index document becomes an "acceptable key document" for the authority-hit test, and every figure that uses it says "checked by a practising advocate". The sealed questions' answers can be added too: they only widen the scoring and do not touch any search. Nothing here changes a question's text.
