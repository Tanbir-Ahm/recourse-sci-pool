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
