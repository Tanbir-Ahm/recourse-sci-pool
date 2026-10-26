# Which search index does staging-web use, and how many judgments can be searched? (checked 2026-10-25)

Question (owner, 2026-10-25): "staging-web is connected to which search index, and how many judgments, as of today, can be searched through that index ... to find out which index has to be connected to the main site ultimately."

> **CORRECTION, 2026-10-26.** Three statements below about the NEWER index (section 3.2 and the Warning sign) were wrong and are corrected in place: (1) the newer index is **not "Supreme Court only"**: it holds 11,683 Supreme Court judgments and **7,553 Gauhati High Court judgments** (the High Court ones come from three sources of the crawl: ghc_post2017 5,830, ghc_bucket 965, ghc_court 758); (2) it does **not** "end 13 July 2026": its newest decisions are 16 Oct 2026 (Supreme Court) and 14 Oct 2026 (Gauhati High Court); (3) the "at least 1,144 from 2026" counts mix both courts (781 of them are High Court). The pinned index checked in this file (`3c80a26`, 10,522 judgments) is unchanged and is Supreme Court only. Details and the loader test of the newer index: `review_results/2026-10-26_newer_index_staging/RESULTS.md`.

**What could NOT be checked:** the sandbox cannot open Railway addresses (the proxy answers 403 for `*.up.railway.app`), and Railway's variables and logs are not visible to Claude. Everything below is read from the code that the staging services deploy and from the data files at the exact commits; what only the owner can confirm is listed in section 5.

## 1. How a search on staging-web reaches an index

`staging-web` (Next.js, `recourse-web`) holds no index. Its server forwards `POST /api/search` (rule in `src/lib/forward.ts`) to `staging-api` (variable `API_URL`). `staging-api` (Recourse branch `register-hooks-and-overlay`, `a2bf305` at the time of writing) runs `search_service.search`, which reads THREE sources:

| # | Source | Where it lives | Used for |
|---|---|---|---|
| A | The reviewed library: **68** judgments listed (116 chunk files, `retrieval._JUDGMENT_CHUNK_FILES`); the page searches the paragraphs of only **46** of them (747 paragraphs in `embeddings/corpus_embeddings.json`). The other 22 (e.g. Tofan Singh, Noor Aga, Mohan Lal) are found by name but their text is not searched on the page (probed with rare words from three of them: not found) | files inside `staging-api` | the "Judgments" and "Passages in judgments Recourse holds" parts of the page |
| B | The Supreme Court title list `case_lookup_index.db`: **38,026** judgments, title, citation and date only | a file inside `staging-api`; byte-identical (same SHA-256) to the file on Recourse `main` `0d880bf` (production) | finding a case by name or citation |
| C | The wide full-text index behind the "Search wider" button: the separate `sci-search` service | `SCI_SEARCH_URL` + `SCI_SEARCH_TOKEN` on `staging-api`; if `SCI_SEARCH_URL` is unset the button says "The wider search is not available right now." | passages of Supreme Court judgments, labelled "not independently verified" |

## 2. Which index C is

`sci_search_service.py` (research repo, branch `claude/sharp-euler-unyfv0`) fetches the index at start from the research repo's branch `claude/sci-index`, **pinned to commit `3c80a26e42bea75e5858be6ed44a2649ec701355`** (`DEFAULT_INDEX_SHA`, pinned since `2036a63`, 2026-10-13; the comment says "the frozen index ... ends 13 July 2026") unless `SCI_INDEX_SHA` overrides it. Evidence that the code as written cannot serve a different index: `names_table/names_table.json.gz` was built for `3c80a26`, and the side indexes under `review_data/side_index/` name `3c80a26` as their main index; the service refuses to start otherwise (`ValueError`: "the names table was built for index ...", "the side index was made for main index 3c80a26, not d8811a9"). Both refusals were reproduced offline with the service's own loader.

## 3. The numbers (counted from the files; loader run offline with a dummy embedding client)

### 3.1 The pinned index (`3c80a26`, built 2026-10-08): what the live `/health` should report
* `documents` **10,522**; `passages` **238,762**; `as_of` 2026-07-13; model voyage-law-2. (Output of the service's own `SearchService.load`: `loader_info_frozen_3c80a26.json`.)
* = 10,503 judgments in the main index (236,155 passages; every passage has its vector) + 19 judgments in three hand-made side indexes (17 correcting judgments, 1 fetched document, Shivangi Bansal; 2,607 passages).
* Of **49,096 files looked at**, **38,591 were set aside on purpose**: 33,395 not criminal law (a keyword test in `sci_index.is_criminal`), 3,084 bucket copies of judgments the crawl already held, 1,313 too short, 660 exact duplicates, 139 near-duplicates. So the index is a **criminal-law subset**, about 21% of the files looked at.
* Origin of the 10,522: 8,113 court-archive PDFs, 2,407 open-bucket PDFs (CC-BY-4.0, Dattam Labs), 2 other.
* Dates (names table): 9,795 dated, 727 undated; earliest 1950-05-05, latest 2026-07-13. By decade: 1950s 167, 1960s 329, 1970s 436, 1980s 313, 1990s 1,139, 2000s 3,471, 2010s 2,367, 2020s 1,573 (2025: 362; 2026: 69).
* 10,454 have a readable case name; 68 are flagged for review.

### 3.2 The newer index (branch tip `d8811a9`, built in shifts up to 2026-10-24) - NOT what the service loads
* **19,236** judgments with passages (**11,683 Supreme Court + 7,553 Gauhati High Court**); **418,286** passages; newest decision 2026-10-16 (Supreme Court) and 2026-10-14 (Gauhati High Court) [corrected 2026-10-26; this line said "as_of still 2026-07-13"]. Of **69,008 files looked at**, 49,765 set aside (43,546 not criminal, 3,084 already in the crawl, 1,733 short, 1,116 duplicates, 286 near-duplicates).
* 10,444 of the pinned index's judgments are in it; 8,792 are new; 59 of the old ones were taken out in the duplicate clean-up of 2026-10-22 (all 59 are named in `state/fixes/20261022T172525-duplicates.json`).
* Recent years (counted only from judgments whose title carries a date, so these are minimums; **both courts together**, 781 of the 2026 ones are Gauhati High Court judgments): 2025 at least 1,547 (pinned index 362), 2026 at least 1,144 (pinned index 69).
* The last build shift (2026-10-24, 50 minutes) ended with `stop_reason: "completed all pending blocks"`.
* **The service could not load it as it stood on 2026-10-25** (section 2): the names table and the side indexes had to be rebuilt for it. Done on 2026-10-26 (additive; the pinned index still loads exactly as before): `review_results/2026-10-26_newer_index_staging/RESULTS.md`.
* **Warning sign:** the branch's own known-answer test (`eval/landmark-*.json`: 6 landmark cases, each asked in a layman's and a lawyer's words = 12 questions; success = the case in the top 5 AND the verified paragraph in the top 3; it tests the raw index, not the service's full recipe) scored 4/12 at 156,235 passages (2 Oct), 3/12 at 153,981, 2/12 at 300,957 (22 Oct) and **1/12 at 418,286 (24 Oct)**. Twelve questions prove nothing, but the direction is steady: more judgments made the known cases harder to find. No run was recorded at 236,155 passages (the pinned index), so its score is unknown.

### 3.3 The title list (B)
* **38,026** Supreme Court judgments; decision dates **1950-03-14 to 2025-12-12; none from 2026**. 37,900 have an INSC number, 126 an S.C.R. number; every row has an S.C.R. citation. By decade: 1950s 1,004, 1960s 3,170, 1970s 2,928, 1980s 2,700, 1990s 6,496, 2000s 9,088, 2010s 7,829, 2020s 4,811.
* It holds no judgment text. (`n_chunks` is a count from the dataset it was built from; the text is not in the file.)

### 3.4 How A, B and C overlap (approximate: matched by decision date and similar party names)
Of the 10,522 judgments of C: about **8,396** are also rows of B; 69 are from 2026 (B has none); about 1,771 dated before 2026 were not found in B (many are 1950s-60s cases; some may be spelling differences); 286 undated ones were not found. So A+B+C together know roughly **40,000** distinct judgments by name (38,026 + about 2,100), but only **10,522 by content** (plus the 46 library cases' 747 paragraphs).

## 4. What this means for "the index to connect to the main site"
* The main site already holds B (same file) and, if the owner's report of 2026-10-16/20 is right (`SCI_SEARCH_MODE=feed`, a `sci-search` service in the production project), C on the same pin. The new search page (`search_service.py`) is NOT on `main`.
* "Judgments searchable by their text": **10,522** now; at most 19,236 (+19 side) if the newer index were adopted after a rebuild of the names table and side indexes AND a proper retrieval test (recipe B, not the raw 12-question test) showed it is not worse.
* The full-text index is criminal-law only by design; a civil, tax or service-law question finds little or nothing relevant in it (33,395 civil/other files were set aside).
* The numbers 49,096 (and 69,008) are files looked at, not judgments you can search.

## 5. What only the owner can confirm in Railway (about five minutes)
1. `staging-api` -> Variables: is `SCI_SEARCH_URL` present? (name and host only; never the token). If not, the page searches only A and B.
2. The `sci-search` service the URL points at -> Deploy logs: the line `sci-search listening on 0.0.0.0:8080; index 3c80a26e42, 238,762 passages`. Another commit or number means it is not the pinned index.
3. On the staging page: search for `search and seizure`, press "Search wider": the page prints "The index holds judgments up to ..." (expect 13 July 2026; note both indexes end on that date, so this line alone does not tell them apart).

## Files here
`count_index.py` (counts documents, set-aside reasons, passages and vectors from the shard files of an index folder), `real_loader_offline.py` (runs the service's own loader with a dummy embedding client), `overlap_with_title_list.py`, `loader_info_frozen_3c80a26.json`, `summary.json`. To reproduce: `git archive <commit> index | tar -x -C <empty folder>` on branch `claude/sci-index`, then `python -I count_index.py <folder>/index <label>`.
