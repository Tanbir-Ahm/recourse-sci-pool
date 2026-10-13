# sci-search: recipe B as a small private service (Phase 1 step 10, built 2026-10-12)

Code `sci_search_service.py`, tests `test_sci_search_service.py`, start command `Procfile`, packages `requirements.txt`. Not deployed anywhere. Numbers below were measured on 2026-10-12 on the real index (`claude/sci-index` at `3c80a26`, plus the three side indexes). [Certain] = measured or read; [Guessing] = judgment.

## What it does
`POST /search {"question": "...", "k": 10}` (header `X-Search-Token`) returns the top passages by recipe B: 100 by meaning + 50 keyword + up to 30 per "section N" -> reciprocal-rank merge -> 60 candidates -> rerank-3-lite x passage-type weights x 1.10 section boost -> top k. `GET /health` shows the index commit, passages, memory and today's spend. Every answer says it is the tier "wider_pool_not_independently_verified", gives the index commit and the date the index ends (2026-07-13), and carries the sentence that the search does not say whether a decision is still good law. The Overruled Register and the cards overlay go on the website side, on top of this (`REGISTER_SITE_PATCH.md`, `site_patch/`).

## Checks that were run
- **Same list as the experiments** [Certain]: on the real index, the service returned exactly the saved stage F list for B on the first four stage F questions (N01 to N04; same passages in the same order). `review_results/2026-10-12_search_service/real_check_output.txt`. In the unit tests the ranking equals `pool_runner.Engine` on an invented index, and the contentless keyword index gives the same candidates as the stored-text one the experiments used.
- `test_sci_search_service.py`: 26 checks (ranking, answer fields, k, empty/long/bad input, kill switch, daily cap and its renewal, token check, bad JSON, a failing Voyage call giving 502 without the error text, refusal to start without a token). Loopback only, no spend.
- Runs from three files copied to an empty folder (`sci_search_service.py`, `sci_index.py`, `chunk_judgments.py`) plus the index folder; no other part of this repository is needed.

## Size, memory, time (measured; `size_report.json`)
| | |
|---|---|
| Index files on disk (main + 3 side indexes) | 572 MB |
| Passages / judgments | 238,762 / 10,522 |
| Vectors in memory (float16, 1,024 wide) | 489 MB |
| Passage text | 260 MB of characters |
| **Memory after loading** | **about 1.5 GB** (1,524 MB) |
| **Memory at the peak, during loading** | **about 1.76 GB** |
| Load time | 27 to 33 seconds (keyword index built in memory at start) |
| One question | 1.3 to 3.7 seconds, one embedding + one re-rank call, about 21,700 re-rank tokens, about 0.1 cent |
So the container needs **at least 2 GB of memory; 3 GB is safer** [Likely]. Two changes made it smaller than the first build (1.8 GB): a keyword index that does not store the text a second time (-340 MB, same results) and dropping four unused fields per passage. The 5 Phase 0 questions about the Railway plan's memory limit stand.

## Safety
Fail-open for the caller: anything but 200 means "answer as the site does today". `SCI_SEARCH_ENABLED=0` turns search off (503) without redeploying the site; daily cap `SCI_DAILY_RERANK_TOKENS` (default 5,000,000, about 230 questions, about a quarter of a dollar) answers 429; one search at a time; question text is never logged; refuses to start without `SCI_SEARCH_TOKEN` (or `--no-auth` on 127.0.0.1). Meant to be reachable only on Railway's private network. The Voyage balance is shared with the live site (reserve $5): this service uses the same key unless you give it its own.

## Limits you must know before showing anything (read these)
1. **Case names.** Only 4,520 of 10,522 judgments have a petitioner/respondent record or a title; **5,678 (54%) are named only by their opening lines** (e.g. "IN THE SUPREME COURT OF INDIA CRIMINAL APPEAL No. 689 OF 2014 ... SUNDEEP KUMAR BAFNA ...APPELLANT vs STATE OF MAHARASHTRA ...") and **324 have no name at all** [Certain: `size_report.json`]. Each result has `name_is_opening_lines`. The website's "Other real court cases" panel shows a clickable case name and an Indian Kanoon link; with this service it would show raw header text for about half the results. A names table (parse the "X vs Y" out of the opening lines, a person checks a sample) is needed before the tier is shown. Until then it can only run in shadow mode (logging, not shown). This is a new finding, not in `DEPLOYMENT_PLAN.md` of this morning.
2. **No link.** The index holds no URL for a judgment. The site's existing tier links to Indian Kanoon; matching a result to an Indian Kanoon page needs a lookup (IK spending rules in `IK_PLAN.md` apply) or a link-less display.
3. **Quality.** Recipe B met the stage F floors (useful 79%, key authority in top 10 on 81%) with 14% Misleading against a 15% limit (weak pass), marks by ChatGPT and Gemini only; no lawyer has read them. Domains D, F, G, J may not be shown (`DEPLOYMENT_PLAN.md`); the service does not know the domain and does not filter.
4. **The index ends 13 July 2026** and has no monthly refresh yet.
5. **Not tested here:** an HTTP call from the real website over Railway's private network; behaviour under concurrent users (searches are serialised, so a slow Voyage call blocks the next user for up to a few seconds); a deploy.

## Deploying
See `DEPLOY_STAGING.md` (step by step, written 2026-10-13). The service fetches the index itself on first start (`python sci_search_service.py fetch-index`; defaults to the frozen index commit `3c80a26` of `Tanbir-Ahm/recourse-sci-pool`, downloaded as a public archive with no API call and no login; `SCI_INDEX_SHA`/`SCI_INDEX_REPO` to change, `GITHUB_TOKEN` for a private repository). A first version that asked GitHub's API without a login was refused with HTTP 403 from Railway's shared address on 2026-10-13 and crashed in a loop; fixed the same day, tested end to end on 2026-10-13: 640 files, 542 MB, 27 seconds, commit `3c80a26`.
