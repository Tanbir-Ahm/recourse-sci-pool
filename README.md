# recourse-sci-bucket (data branch `claude/sci-bucket`)

Text and metadata of Supreme Court of India judgments taken from the open `indian-supreme-court-judgments` dataset (s3://indian-supreme-court-judgments, CC-BY-4.0, Dattam Labs). No PDF is stored here; each PDF was read in memory and discarded. Private working data for Recourse's internal search. Nothing here is verified or cited to users.

Attribution: the judgments are the Supreme Court of India's; the compilation and law-report formatting are from the Dattam Labs open dataset (CC-BY-4.0). Keep both with anything reproduced.

- `shards/<scope>-<NNNN>.ok<k>.miss<m>.err<e>.jsonl.gz`: one file per block of 250 judgments. **A block is done exactly when its shard is committed** (this is the ledger). Scope `after`: judgments dated after 4 May 2017 (the crawl on `claude/sci-pool` ends on that date); 29 blocks, 7,123 saved, 2 have no file in the bucket. Scope `none`: older judgments the name match could not find in the crawl; 20 blocks, 4,831 saved, 2 no file. Which of those the crawl really lacks: `coverage/bucket_match/none_resolution.csv.gz` on the code branch.
- One line per judgment: bucket metadata (title, parties, decision date, law-report citation, neutral citation, judge, disposal, bucket file name), `bytes` and `sha256` of the PDF as served (so a re-fetch can be checked), `pages`, `scan_pages` (pages carrying an image, i.e. scanned), `producer`, `text_chars`, raw `text` (pages joined by form feeds), and `body_start` / `body_marker` where the court's own judgment seems to begin. The text is saved as extracted: margin letters A to H, running headers and the law report's editors' headnote are still in it. `sci_bucket.clean_text(record)` (code branch) returns reading text without changing the record.
- `state/worklist.sha256`: hash of the work list the block numbers refer to. `state/shifts/`: one small log per run.
- Kill switch: commit an empty file named `STOP` at the repo root and every run halts before fetching.

Code, tests, runbook and work list are on the code branch: `sci_bucket.py`, `test_sci_bucket.py`, `BUCKET_RUNBOOK.md`, `coverage/bucket_match/`.
