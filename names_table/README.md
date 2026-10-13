# Names table (built 2026-10-13)

`names_table.json.gz` (about 0.5 MB): one row per judgment in the search index (10,522: 10,503 in the main index + 19 in the side indexes) for index commit `3c80a26`. Built by `build_names_table.py`; tests `test_names_table.py`; the search service reads it (`SEARCH_SERVICE.md`).

Row: `doc`, `name` (readable "Petitioner v. Respondent", or null), `petitioner`, `respondent`, `date` (ISO, or null), `year`, `citations`, `name_source`, `link`, `link_kind`, `review`.

## Where each part comes from
| Judgments | Name, date, citation | Link |
|---|---|---|
| 8,113 from the court's own archive (crawl) | read from the judgment's own opening by `goodlaw/headers.py` (7,815), a caption fallback (231), the index's case record or the bucket's copy of the same case | `https://api.sci.gov.in/jonew/judis/<id>.pdf` (`court_archive_pdf`) |
| 2,407 from the open bucket (CC-BY-4.0, Dattam Labs) | the bucket's own metadata (title, parties, date, SCR citation, INSC number) | the PDF in the bucket, `https://indian-supreme-court-judgments.s3.ap-south-1.amazonaws.com/<key>` (`open_bucket_pdf`) |
| 2 fetched by hand | the title recorded then | the URL recorded then |

## What was checked
- **Link points to the right judgment (court links), 2026-10-13: 8,100 of 8,100.** Each crawl judgment's indexed passages were found inside the crawl record with the same id: 8,096 by text, and the other 4 (short records whose numbering differs slightly) by reading the opening lines.
- **Links, live, 2026-10-13: 240 of 240.** A random 120 of each kind (`link_check.json`): every one returned a PDF whose size equals the size stored when it was downloaded. This shows the link opens the same file we read; it does not show the court will keep the URL.
- **Names:** 10,454 of 10,522 have a name; **68 are unnamed and flagged `review`** (their link and date are kept). `review_sample.csv` lists 150 random named rows plus all 68 unnamed, beside the first 260 characters of the judgment, with columns for a person to mark. **No person has checked it yet.**
- 727 rows have no date (modern judgments whose date is only at the end of the text and was not read).

## Limits
- Titles in capitals are converted to title case by rule; unknown acronyms become "Abc Ltd". The raw `petitioner`/`respondent` are kept.
- Spelling errors in the court's own text are kept (for example "Madrashigh Court").
- Bucket judgments link to a public mirror, not to the court's website; the bucket asks for credit (CC-BY-4.0): show "Judgments from the open Supreme Court judgments bucket, Dattam Labs".
- Rebuild after any change of index (`python names_table/build_names_table.py --review-sample 150 --verify-links 120`); the service refuses to start on a table built for a different index commit.
