# recourse-sci-pool

Private working library of Supreme Court of India judgments (text only) crawled from the court's open sequential archive
(`https://api.sci.gov.in/jonew/judis/<id>.pdf`), for Recourse's internal candidate search. Nothing here is verified or cited to users.

- `shards/` - one compressed file per block of 250 IDs. The file name records the range and counts. **A block is done exactly when its shard is committed** (this is the ledger).
- `state/shifts/` - one small log per crawl shift.
- `sci_crawl.py` - polite, resumable downloader. `sci_relay.py` - runs one time-boxed shift and pushes.
- Kill switch: commit an empty file named `STOP` at the repo root and every shift halts before fetching.

Run a shift (any machine with git push access and `pip install pymupdf requests`):

    python sci_relay.py shift --from-id 44000 --to-id 0 --minutes 50 --workers 2 --pause 1.5

Progress: `python sci_relay.py status --from-id 44000 --to-id 0`.

Source acknowledgement: all judgments are from the Supreme Court of India website; keep the source link with anything reproduced.

## Passage index (embeddings)

`sci_index.py` turns the crawled judgments into clean, tagged, embedded passages, one block of 250 IDs at a time, saved on branch `claude/sci-index` (the crawl data on `claude/sci-pool` is only read). It keeps criminal-law judgments only, skips copies, tiny orders and junk, never spends past a token ceiling, and stops cleanly (keeping everything saved) if the Voyage service refuses. Tests: `python test_sci_index.py` (fake service, real temporary git repos, costs nothing). How to run it: see `INDEX_RUNBOOK.md`. `landmarks.json` holds the project's verified landmark paragraphs for the known-answer check (`sci_index.py eval`). `chunk_judgments.py` is a vendored copy of the splitter from the main Recourse repo.

`index_dedupe.py` finds and removes second copies of the same judgment from a finished index (copies that differ in header or layout, which `sci_index.py` cannot see). It spends nothing, never removes a judgment decided together with others under a different case number, and a person reads its plan before it is applied. Tests: `python test_index_dedupe.py`. How to run it: the DEDUPE-PLAN and DEDUPE-APPLY modes in `INDEX_RUNBOOK.md`. `index_fixes/` holds the plans that were applied (2026-10-02: 135 judgments removed, 2,254 passages).

## Search-quality review (AI reviewers and people)

`review_tools/` builds the packs that reviewers mark (a first AI-reviewer pack, a top-up pack, a human review sheet and an authority-check workbook) and reads the replies back, scoring each search version on what it showed. `review_data/pool_all.json` is the passage pool those packs are built from. **It is a private answer key (it records which search found each passage): never send it to reviewers.** Everything it reports is labelled LLM-judged or human-judged; none of it is lawyer validation. See `review_tools/README.md`. Tests: `python review_tools/test_ingest_llm_reviews.py` and `python review_tools/test_builders.py` (need `pip install openpyxl`).

## Coverage note

`coverage/COVERAGE_NOTE.md` records where the crawl ends (4 May 2017), how many Supreme Court judgments each source holds per year against Indian Kanoon's own list, what the open AWS bucket contains and how good its text is, and the proposed plan for checking whether judgments are still good law. `coverage/year_counts.csv` has the per-year numbers; `coverage/scripts_as_run/` has the scripts that produced them, saved as run. `coverage/bucket_match/` holds the metadata-only match of the bucket against the crawl (`MATCH_REPORT.md`, the per-judgment `registry.csv.gz`, scripts); it also corrects an earlier double count of the bucket (38,152 distinct judgments, not 43,333).
