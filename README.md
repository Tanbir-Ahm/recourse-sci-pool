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

## Open-bucket text (post-May-2017 judgments and older gap-fill)

`sci_bucket.py` downloads PDFs from the open `indian-supreme-court-judgments` bucket (CC-BY-4.0, Dattam Labs), extracts the text and saves it, block by block, on branch `claude/sci-bucket` (text and metadata only; PDFs are held in memory and never written to disk or committed). The work list is `coverage/bucket_match/worklist.csv.gz` (7,125 judgments dated after 4 May 2017, scope `after`; 4,833 older ones the crawl seems to lack, scope `none`). `bucket_refresh.py` finds judgments added to the bucket since the last run and writes a refresh work list (the 214 judgments of 2026 were the first). How to run it: `BUCKET_RUNBOOK.md`. Tests: `python test_sci_bucket.py`, `python test_bucket_refresh.py`. Source acknowledgement: keep the Supreme Court of India and Dattam Labs attribution with anything reproduced.

## Still-good-law checker

`sci_goodlaw.py` builds one searchable store from the crawl and the bucket text (`python sci_goodlaw.py build`, about 15 minutes) and writes, for one judgment, a review report: which later Supreme Court judgments cite it, the exact sentences in which they follow, distinguish, doubt or overrule it, the reporter's own citator for older cases, what became of the statute sections it cites under the 2023 recodification, a triage label (`ADVERSE_SIGNAL`, `QUESTIONED`, `NO_ADVERSE_FOUND`, `INSUFFICIENT`) and a statement of what the collection cannot see. It never says a case is good law; `NO_ADVERSE_FOUND` is silence in what we hold. `GOODLAW.md` explains the design and the labels; `goodlaw/EVALUATION.md` gives the measured accuracy (it finds about a third to a half of the overrulings the reporters recorded, and about half of its clean flags are real) and says what was not measured; `reports/` has reports for the priority cases. `cards/` holds a precomputed currency card for each of the 76 cases Recourse can show, a review sheet and a stdlib-only reader for the answer step (`cards/README.md`); it is not connected to the live site. Tests: `test_goodlaw_*.py`.

## Offline message formatter (not connected)

`goodlaw/chat_format.py` turns a retrieved passage plus what the Overruled Register and the currency cards say about its case into one plain-text chat message with the warning first ("Reported adverse", "Questioned", "Not checked by us", and so on). It words only what the register and the cards already say, never calls a case "good law", and never cuts a warning to fit; only the passage is shortened. Nothing is sent and nothing is connected. How a quiet card is shown (`quiet_policy`, no default in the code) was decided on 2026-10-22 and is recorded in `goodlaw/data/pilot_settings.json`. `goodlaw/passage_input.py` turns a search hit (an index passage row) into the formatter's input, naming the judgment from the checker's corpus (the index itself carries no title for most crawl judgments). Details: `FOLLOW_UPS.md` items 1o and 1p. Tests: `python test_goodlaw_chat_format.py`, `python test_goodlaw_passage_input.py`.

## Watchlist (offline slice, not connected)

`goodlaw/watchlist.py` keeps a lawyer's saved cases, re-checks them against the register and the cards, and writes draft alerts for a person to approve: only for a new, confirmed, changed or withdrawn warning, never an "all clear". It schedules nothing and sends nothing. Details and limits: `FOLLOW_UPS.md` item 1q. Tests: `python test_goodlaw_watchlist.py`.

## Pilot bookkeeping (offline slice, not connected)

`goodlaw/pilot.py` holds the private pilot's allow-list, the three rules a user must accept, and the lawyers' marks (Relevant, Not relevant, Misleading) on the passages shown, with feedback buttons for a formatted message and a summary and CSV sheet for the owner. No sender, no accounts, nobody on any list. Details and gates: `FOLLOW_UPS.md` item 1r. Tests: `python test_goodlaw_pilot.py`.

## CSV export of a list of cases (offline slice, not connected)

`goodlaw/authority_export.py` writes a list of cases, or a saved watchlist, as a CSV: for each case a status, what we know, the date that evidence is as of, who checked it, and a note on every row ("pattern-rule reading, not lawyer-validated", or "not checked"). A quiet case is spelled out, never left blank. Details: `FOLLOW_UPS.md` item 1s. Tests: `python test_goodlaw_authority_export.py`.

## Pilot bot core (offline slice, not connected)

`goodlaw/bot_core.py` takes a message or a button tap and returns the replies: the three rules, a question answered with three passages (warning first, feedback buttons), `/watch`, `/watchlist`, `/export`. No chat service, no accounts, no real search; every search is capped per user and per day. A dry run written out as a conversation: `review_results/2026-10-22_bot_dry_run/TRANSCRIPT.md`. Details and what still needs the owner: `FOLLOW_UPS.md` item 1t. Tests: `python test_goodlaw_bot_core.py`.

## Pilot settings and the owner's tools (offline, not connected)

`goodlaw/data/pilot_settings.json` records each pilot setting and who decided it (the quiet-card choice was decided on 2026-10-22; the rest are defaults or placeholders). `python -m goodlaw.pilot_admin` adds users, switches them off, shows a summary, exports the marks and pauses the bot; the list is empty. How to run the pilot, when the owner decides to: `PILOT_RUNBOOK.md`. Details: `FOLLOW_UPS.md` item 1u. Tests: `python test_goodlaw_pilot_settings.py`. What one question costs (about $0.0004 to $0.001, hosting not included) and why questions over 1,000 characters are refused: `review_results/2026-10-22_pilot_cost/COST_IN_PLAIN_TERMS.md`, `FOLLOW_UPS.md` item 1v. What the index needs in memory (about 1.8 GB) and where to host it: `review_results/2026-10-22_index_memory/HOSTING_IN_PLAIN_TERMS.md`.

## Internal case-data layer (offline slice, not connected)

`casedata/` is the "front desk" for a possible case-tracking brief: one standard case record, five calls (get the case, check listings, refresh, get an order, what changed), a saved copy, a daily spending cap, a ledger and a dry-run nightly plan, over a swappable adapter. Only a made-up adapter exists (`casedata/fake.py`); nothing makes a network call, needs a key or spends money, and no real court source is wired. Details and limits: `casedata/layer.py`, `FOLLOW_UPS.md` item 1n. Tests: `python test_casedata.py`.

## Coverage note

`coverage/COVERAGE_NOTE.md` records where the crawl ends (4 May 2017), how many Supreme Court judgments each source holds per year against Indian Kanoon's own list, what the open AWS bucket contains and how good its text is, and the proposed plan for checking whether judgments are still good law. `coverage/year_counts.csv` has the per-year numbers; `coverage/scripts_as_run/` has the scripts that produced them, saved as run. `coverage/bucket_match/` holds the metadata-only match of the bucket against the crawl (`MATCH_REPORT.md`, the per-judgment `registry.csv.gz`, scripts); it also corrects an earlier double count of the bucket (38,152 distinct judgments, not 43,333).
