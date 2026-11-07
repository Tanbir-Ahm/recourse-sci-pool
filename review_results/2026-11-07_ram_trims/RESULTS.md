# RAM trims, items 2, 3 and 8 of the 2026-11-07 audit (owner: "Build items 1, 2, 3 and 8")

Item 1 (stop or sleep the staging services when idle) is a Railway setting, not code: see `DEPLOY_STAGING.md` Part 4av. Nothing was changed on Railway.
Measured here on the REAL indexes (`claude/sci-index` at `3c80a26`, production's pin, and at `d8811a9`, the newer staging index, each with its side indexes), old loader (`SCI_LOAD_COPY=on`) and new loader in separate processes. No model, no spend (the embedding client is a stand-in). Scripts in `scripts/`; raw results in the four `v_*.json`.

## Item 2: pre-sized load (sci_index.py, sci_search_service.py)
| | steady after load | peak during load | load time |
|---|---|---|---|
| pinned (production), old | 1,537 MB | 1,758 MB | 15 s |
| pinned, new | 1,279 MB | 1,286 MB | 14 s |
| newer (staging), old | 2,540 MB | 2,986 MB | 71 s |
| newer, new | 2,094 MB | 2,109 MB | 24 s |
**Identical:** SHA-256 of the whole vector matrix, of the metadata (all passages), and of the service's info are equal old vs new on both indexes (`M_sha256`, `metas_sha256`, `info_sha256` in the four JSON files); dtype float16, shapes (238,762 and 420,893 by 1,024); keyword-index row counts equal.
What was changed: the vectors are read into ONE array allocated from the .npy headers (no collect-then-`np.vstack`, no second vstack for the side indexes); metadata rows are trimmed to the seven fields the service uses as they are read (not afterwards); `sci_index._load_index` computed `ledger()` (which opens every vector file) once per shard, now once (this is most of the faster load). The steady-state saving is more than the 0 I had promised: it comes from trimming the rows as read.
Way back: `SCI_LOAD_COPY=on` (the old path, unchanged code). Inconsistent inputs (a side index of another width, made for another main index, repeating a document) are refused with the same messages on both paths (tested).

## Item 3: query block 50,000 -> 5,000 (SCI_SIM_BLOCK)
- Candidate lists (the 60 passages the re-ranker would see): identical for blocks of 5,000 and 50,000 in 350 of 350 searches on the newer index (150 real passage vectors, 150 noised, 50 random) and 350 of 350 on the pinned index. A block of 1,000 changed the candidates in 2 of 350 (near-tied passages swapped), so the value is floored at 5,000. Largest score difference 1.8e-07. Top-100 semantic order identical in 100 of 100.
- Peak during searches on the newer index: 2,300 MB (50,000) -> 2,118 MB (5,000). Time per retrieve (no other process running): 0.95 to 1.57 s with 50,000, 0.71 to 0.72 s with 5,000 (noisy, but not slower).
- Way back: `SCI_SIM_BLOCK=50000`.

## Item 8: engine processes (Recourse branch)
Engine process after load (ACT_SHELF on, CHECKER_LIST wide): **345 MB before, 219 MB after** (-126 MB), measured in fresh processes. Parts: PyMuPDF no longer imported at the top of `main.py` (about -83 MB; it is imported inside `extract_text_from_pdf`, its only use; the website, WhatsApp bot and API imports no longer load it); the per-record Python vector lists released after the matrix is built (about -42 MB; matrix and scores byte-identical; way back `KEEP_RECORD_VECTORS=on`); `maxUploadSize = 10` in `.streamlit/config.toml` (Streamlit's default is 200 MB and it holds the file before the page's own 8 MB check).
Not done (not in the go): item 9 (start Next.js directly), the WhatsApp PDF store caps, anything on the vectors' precision.

## Tests
Research: `test_sci_load_lowmem.py` (new, 29 checks: pre-sized equals classic load on an invented main index + two side indexes; the refusals; `sim_block`; 40 random questions over 23,000 passages give identical candidates for blocks 5000, 7000, 50000), `test_sci_search_service.py` 58 of 58, `test_sci_quotes.py`, `test_authority_graph.py`, `test_names_table.py`, `test_sci_search_fetch.py`, `review_tools/test_build_supplement.py` all pass. Recourse: `test_memory_footprint.py` (new, 15 checks) and the whole suite 134 of 134 before it was added.
## What is not shown
A real model answer; Railway's own meter; production (the service is not redeployed from here); whether the saving is the same on Railway's allocator (this is the sandbox's glibc).
