# Items 4 and 5 of the 2026-11-07 RAM audit: passage text and keyword index on disk (SCI_STORE) -- owner: "Build items 4 and 5"

Code: `sci_store.py` (new), `sci_search_service.py` (the `SCI_STORE` branch of `SearchService.load`, `_text()`, `build-store` command), tests `test_sci_store.py` (27 checks). Switch `SCI_STORE` (default OFF; `on` = the text and the keyword index in a file). Measured on the REAL indexes (production's pin `3c80a26` and the newer `d8811a9`, each with its side indexes, names table), no model, no spend (stand-in embedding and re-rank clients).

## What it does
One file `sci_store.sqlite` next to the index (`SCI_STORE_PATH` for another place): `t(id, z)` the text of each passage zlib-compressed; `f` the SAME contentless FTS5 keyword table the service always built (same tokenizer, same rowids) now on disk; `info` a fingerprint (passage count + SHA-256 of every passage's text in order). In memory only doc, i, pn, page, section, h per passage (columns). Text is read from the file for the 60-90 passages re-ranked and the ten returned. Built on the first start with the switch on (45 s on the newer index), written under a temporary name, read back and compared, then renamed. Every later start compares the fingerprint of the text just read from the index with the file's: a changed index rebuilds the file, so it can never serve another index's text. Any problem with the file -> a log line and the in-memory service; refusals about the index itself still refuse.

## Memory and time (fresh processes)
| | in memory (items 2+3 only) | SCI_STORE=on | original (before 2dq) |
|---|---|---|---|
| newer index, steady | 2,096 MB | **1,113 MB** (1,131 after 30 retrieves + 20 searches) | 2,540 MB |
| newer index, peak | 2,109 MB | **1,135 MB** | 2,986 MB |
| pinned index, steady | 1,279 MB | **648 MB** | 1,537 MB |
| pinned index, peak | 1,286 MB | **655 MB** | 1,758 MB |
| start, newer: first (build) / later (reuse) | 24 s | 47 s / 8.7 s | 71 s |
| start, pinned: first / later | 14 s | 28 s / 5.1 s | 15 s |
| file on disk | | 408 MB (newer), 256 MB (pinned) | |
Time per search, 20 runs each, stub re-rank: 0.78 to 0.84 s in memory, 0.78 to 0.81 s from the file (no measurable difference).

## Equal to the in-memory service (one process, both services on the same real index, `scripts/verify_store.py`)
Pinned (238,762 passages) and newer (420,893): vectors identical; the six fields of every passage identical (0 differences); the text of EVERY passage identical (0 differences); service info, opening-lines table, titles of every judgment (10,522 and 19,255), court masks, rows-by-document identical; keyword index: the same rowid list in the same bm25 order for 300 random queries (ties included); `retrieve()`: the same 60 candidates for 450 queries (150 passage-vector, 150 noised-vector and 150 mixed queries, each with no court filter, "sc" and "hc"); the full `search()` reply (rank, score, passage text, case names, links) identical for 180 queries (the stand-in re-ranker scores from a hash of the text, so any changed byte would change the order). On the newer index with `SCI_QUOTES=on` and `SCI_AUTHORITY=on` as well: the 21,524 quote marks identical, the authority table loaded in both, the same results. Raw outputs: `verify_pinned.txt`, `verify_newer_with_quotes_and_authority.txt`.

## Not shown / limits
Railway's own meter (the 408 MB file is read through the operating system's file cache, which is not part of the process but may count toward a container's memory figure; it is reclaimable); a real re-rank/embedding call; production; disk-full behaviour on a real volume (tested: an unwritable path falls back to memory); that the same savings hold on Railway's allocator. The in-memory path is untouched and is what runs unless `SCI_STORE=on`.
