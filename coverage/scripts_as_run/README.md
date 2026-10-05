# scripts_as_run: the measurements behind COVERAGE_NOTE.md

Saved exactly as they were run on 2026-10-04 and 2026-10-05. They are a record, not a tool: paths point at that session's temporary folder and at local checkouts of the crawl, the index and the Recourse repo. Change them before running.

| Script | What it did |
|---|---|
| `last_crawl_id.py` | Where the crawl ends: highest id, last dates, the run of empty ids. |
| `dump_heads.py` | Saved the first 3,500 characters of every crawled judgment to `heads.jsonl.gz`. |
| `parse_heads.py` | Read party names and dates from those openings; writes `crawl_table.json`. |
| `crawl_years.py` | Read each later judgment's decision year from the date near the end of its text; writes `crawl_years.json`. |
| `cite_pilot.py` | Counted later judgments in the 8,101-judgment index that name each landmark, with cue words near the name. |
| `cite_full.py` | The same count over all 36,928 crawl texts. |
| `bucket_sample_scan_regime.py` | Sampled bucket PDFs across 2017 to 2025 (scans or typeset text, size). |
| `bucket_scan_by_year.py` | Scan share by year for 2012 to 2024. |
| `bucket_match_to_crawl.py` | Found which sampled bucket PDFs also exist in the crawl. |
| `bucket_text_fidelity.py` | Compared the two texts of the same judgment (8-word runs). |
| `bucket_case_name_recall.py` | Compared how many "X v. Y" citations both texts yield. |

The chain: `dump_heads.py` then `parse_heads.py` (crawl_table.json); `crawl_years.py` (crawl_years.json); the bucket scripts need the bucket's metadata tables and PDFs downloaded to a scratch folder. `../year_counts.py` combines them with IK's yearly list into `../year_counts.csv`. A first vocabulary-based text-quality test was inconclusive and is not kept.
