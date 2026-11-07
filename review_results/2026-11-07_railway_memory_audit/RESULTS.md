# Railway memory audit, 2026-11-07 (owner: "Audit my entire application for Railway hosting costs, particularly RAM consumption. Do not modify any code yet.")

READ-ONLY. No application code was changed. Measurements were made in the sandbox (Linux, 16 GB) with the real data, the real service loader and a STUBBED model/embedding client (no Anthropic key; no spend). Railway's own meter (resident set or container cgroup incl. page cache) was not seen: figures are resident memory (VmRSS) in this sandbox. Scripts: `scripts/`.

## Measured (resident MB)
| Component | MB | How |
|---|---|---|
| Streamlit server, idle, 0-4 landing-page sessions | 52-60 | real `streamlit run` + 4 headless browser sessions |
| Libraries pulled in by the first question (chat_assistant -> main.py -> PyMuPDF, anthropic, voyageai, reportlab, aiohttp) | ~226 total after import | PyMuPDF alone +103 (imported at the top of main.py, used once at main.py:91) |
| Recourse library embeddings (1,666 chunks; 1,024 floats each) | +68-83 | the vectors are 13.6 MB as a numpy matrix; ~55-70 MB is the same vectors kept again as Python float lists in `records` |
| Act shelf (13 Acts, 1,031 sections) | +27 | |
| Invented-case name list (CHECKER_LIST=wide) | +21-25 | |
| Overruled register | +7 | |
| **Engine process total, steady** | **345-366** | flat over 30 stub questions (341 -> 345) |
| FastAPI service import (before the engine) | 84 | engine adds ~345 -> ~430-500 for staging-api |
| Next.js `next-server` after 10 requests | 131 | plus `npm exec` wrapper 81 if started via npm/npx |
| **sci-search, pinned index 3c80a26 (production)** | **1,526 steady, 1,672 high-water (1.76 GB with side indexes)** | vectors 484 + text/rows ~690 + keyword index 237 + names 15 |
| **sci-search, newer index d8811a9 (staging)** | **2,510-2,541 steady, 2,852-2,987 high-water** | vectors 857 + text/rows ~1,143 + keyword index 361 |

## Why sci-search is big
1. Everything is in RAM: float16 vectors, the full passage text as Python strings (407 M characters, 45% non-ASCII = 2 bytes a character) in 418,286 dicts, and a keyword index built in memory at every start (16 s).
2. Load copies the vectors: `np.vstack` (x2 with the side indexes) = +857 MB transient each.
3. A query turns 50,000 vectors at a time into float32: +200 MB transient.
4. Not a leak: court masks, rows_by_doc, authority table, quotes all fit in already-held memory (+0 measured).

## Prototype of a lean loader (scratch only, newer index)
Vectors in RAM (preallocated, no vstack) + compressed text and the keyword index in a read-only on-disk sqlite file (409 MB) with a 32 MB page cache: **875 MB resident in total** (843 anonymous), high-water 1,058 MB with 50,000-row blocks. FTS query from disk 65 ms; 90 text fetches + decompress 3 ms. Scores with 5,000-row blocks differ from 50,000-row blocks by at most 2.4e-7; top-100 order identical in 25 of 25 tests (36k-row subset; not proof for exact ties). mmap'd vectors: 42 MB anonymous + 837 MB file-backed after one query (no steady saving; reclaimable).
Not included in the prototype: the compact per-passage metadata (doc, i, page, section, h) the real service needs (allowance +40-80 MB, a guess), the authority table and names table.

## Dollar picture (Railway Hobby, ~$10 per GB-month, from DEPLOY_STAGING_BEGINNER.md, unconfirmed on the bill; billed on use, not reservation: Likely)
Today if all run 24/7: sci-search prod 1.53 GB ~$15, sci-search staging 2.54 GB ~$25, website 0.4 ~$4, whatsapp 0.4 ~$4, staging-api 0.45 ~$4.5, staging-web 0.2 ~$2, staging-site ~0.1-0.4 ~$1-4, Postgres not measured. About $55-60 a month; the two search services are ~70%. CPU billing, Postgres and egress were not assessed.
