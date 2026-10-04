# experiments: the one-off scripts that made the review pool

These are the scripts that built `review_data/pool_all.json` and ran the site-versus-mine comparison on 2026-10-02. They are saved **exactly as they were run** (byte for byte), so you can see what each search version did. They are a record, not a tool. For a plain-words table of the six versions and the two top-up sources, see `VERSIONS.md`.

**Do not send this folder to reviewers.** It names the search versions, and the pool is a private answer key (see `review_data/README.md`).

## What each file did

| File | What it did |
|---|---|
| `pool.py` | Built the first batch. For each of the 12 test questions it ran six search versions, took each version's top 10, collapsed identical passages, kept up to 16, shuffled with a fixed seed and numbered them. Writes `pool_raw.json`. |
| `rewrites.json` | The legal-wording rewrites of the six plain-language questions, used by versions C and F. The same text is also stored in each question's `rewrite` field in `pool_all.json`. |
| `site_on_wide.py` | Ran the Recourse site's own search function (`semantic_retrieval.find_relevant_sections`, unmodified, statute lookups switched off) on the wide index for the 12 questions, and ran my own pipeline on the same index for comparison. |
| `site_on_wide2.py` | The fair-size check: if my pipeline showed as many passages as the site does (top 6), does it include the landmark case and the verified paragraph? Also finds where the verified paragraph ranks by plain meaning. |
| `build_topup.py` | Found the passages the site's search (or my top 6) showed that were not yet in the pool, wrote them as continuation rows (numbers continue after the first batch, `topup: true`), and tagged every pool row `S site shown` / `M mine top 6`. Writes `pool_topup.json` and `pool_all.json`. |

## The six versions in `pool.py`

All six share the same retrieval: nearest 100 passages by meaning, plus a keyword search (top 50) and a "section N" search (top 30), merged by reciprocal rank (K = 60) into 60 candidates, then re-ranked with Voyage `rerank-2`. The core of this is also in `sci_index.run_eval`.

| Version | Difference |
|---|---|
| A today | Re-ranker score times the passage-type weight `W` and a 1.10 boost if the passage mentions a section named in the question. |
| E no multiplier | A's re-ranker scores with no weights and no boost. |
| B no repeats | Identical-text passages are removed before the 60 candidates are chosen, then scored like A. |
| C rewrite | Plain-language questions only: the same pipeline run on the legal-wording rewrite. |
| F merged | Plain-language questions only: A's and C's candidates together, each scored by the better of its two scores. |
| L landmark key passages | The one or two passages of the expected case that match the project's verified paragraphs, added by hand so they are judged even if no version returns them. |

## Things to know before trusting a re-run

- **Hard-coded paths.** The scripts point at this session's temporary folder (`SCR`), at `/home/user/recourse-sci-index`, at `/home/user/recourse-sci-pool-data` and at a read-only clone of the Recourse repo (`/home/user/tanbir-ahm/recourse`). Change them before running. Nothing was edited, so the saved text matches what ran.
- **A re-run will not reproduce the pool.** The first batch was built before the duplicate fix of 2026-10-02 (it removed 135 judgments), and the index has changed since. `pool_all.json` is the record of what reviewers saw; rebuild packs from it, never from these scripts.
- **A step is missing.** `build_topup.py` reads `pool_raw_v2.json`. That file is `pool_raw.json` with 9 missing case titles filled in from each judgment's opening text, done by a one-line command that was not saved. Numbers, hashes and texts are identical in both.
- **They cost money.** Each run makes Voyage embedding and re-rank calls (small: a few cents per run).
- **The site run leaves out the site's own routing and hand-pinned paragraphs.** It measures the site's search step alone, not the live site.
