# The still-good-law checker

What it is: a tool that, for one Supreme Court judgment, gathers the evidence a lawyer needs to judge whether it is still good law, ranks it, and says plainly what it could not see. It follows the rule in Recourse's own currency pipeline: **no code here decides that a case is good law.** The output is a triage label and the exact sentences behind it, for a person to read.

Everything below is labelled by its source: results are *pattern-rule reading of Supreme Court texts*, not lawyer-validated.

## What one report contains

Run `python sci_goodlaw.py check --corpus corpus.sqlite "Rangappa v. Sri Mohan" --year 2010 --out reports/`.

| Block | What it gives | How it is made |
|---|---|---|
| Triage | `ADVERSE_SIGNAL`, `QUESTIONED`, `NO_ADVERSE_FOUND` or `INSUFFICIENT`, with one plain sentence, plus a separate `STATUTE_CHANGED` flag | rules over the evidence below (`goodlaw/report.py`) |
| Who cites it | later judgments that name the case, by decade, latest year, how many in the last ten years | citation, party-name and short-name matching (`goodlaw/mentions.py`) |
| What they do with it | for each citing judgment the strongest sentence: overrules, disagrees, doubts or refers, legislative response, distinguishes, limits, follows, not overruled | sentence rules with negation, who-overruled-whom, speaker (the Court, counsel, a lower court, the law report's headnote) and bench rules (`goodlaw/treatment.py`) |
| Evidence | the exact sentences, each checked word for word against the judgment's text, with the cue words, the speaker, the confidence and the bench relation | `goodlaw/textutil.py` |
| The reporter's citator | for judgments to about 1985, the reporters' own printed list of later citing cases and what they did (followed, distinguished, overruled ...), with each citing case found in the collection | `goodlaw/headers.py` |
| The law reporter's case-law table | for judgments of 2017 to 2023, what the Supreme Court Reports marked for the case in each later judgment's headnote table (overruled, relied on, referred to ...), quoted and labelled as the reporter's annotation | `goodlaw/tables.py`, `goodlaw/modern_gold.py` |
| Statute dimension | the IPC and CrPC sections the judgment cites and what became of them under the 2023 recodification (IPC to BNS, CrPC to BNSS) | NCRB concordance vendored from Recourse (`goodlaw/statutes.py`) |
| Coverage | where the collection ends and how much of what came after the case it holds, against Indian Kanoon's yearly counts | `coverage/year_counts.csv` |

## Precomputed cards for the answer step

For the cases Recourse can show, `python sci_goodlaw.py cards` writes one card each (`cards/currency_cards.json`) so that answering a question is a lookup: the status, one or two plain sentences for a user (only when there is a warning or a caution; never "good law"), the quoted evidence for a reviewer, a review sheet a person fills in, and a report of what changed since the last run. `goodlaw/cardreader.py` is the stdlib-only reader Recourse would copy. See `cards/README.md`. Nothing is connected to the live site yet.

## The second reader

A model can read the passage around each mention, which the pattern rules cannot. `goodlaw/reader.py` exports the passages (without the rules' labels), checks each answer's quote word for word, and ties each verdict to the passages it read. The results sit on each card (`second_reader`) and on the review sheet; they never change a status or a user note. Measured blind on the tuning halves it found 75% of the pairs the reporters marked adverse (the rules 65%), read 34 of 48 rule flags on unmarked pairs as not adverse, and found nothing on 42 quiet pairs; it is the checker's author, not an independent reader, and it can read a quoted earlier doubt as the Court's own. See `goodlaw/EVALUATION.md` (step 5) and `cards/README.md`.

## Cases whose own judgment we do not hold

A library case whose judgment is not in the collection is checked as an **external target** (`goodlaw/targets/external.json`): the mention finder looks for it by name and citation in the later judgments we hold, and its card says it was checked from the outside. The Indian Kanoon API would add the later judgments we do not hold. `goodlaw/ik.py` is the guarded client for it (a dry run, rupee caps, a ledger, a cache, stop on the first error; see its docstring and `IK_PLAN.md`); only a metadata call has been made so far, and nothing from the API feeds a card yet.

## What the labels mean, and do not mean

- `ADVERSE_SIGNAL`: a later judgment of this Court, in its own voice, appears to overrule or reject the case (or a larger bench disagrees with it, or the law report's headnote says "over-ruled", or the reporter's citator marks it overruled). Read it before relying on the case.
- `QUESTIONED`: later judgments disagree, doubt, refer or limit it; a smaller bench appears to overrule it; the cue is hedged or may be about another case; or the legislature responded.
- `NO_ADVERSE_FOUND`: at least three later judgments we hold cite it and nothing adverse turned up. **This is silence in what we hold, not a finding that it is good law.** The coverage block says how much we hold.
- `INSUFFICIENT`: fewer than three citing judgments found.
- `STATUTE_CHANGED`: a provision it cites was renumbered, repealed or marked changed. That is a fact about the section, not about the doctrine, which usually carries over.

## How good is it (measured)

See `goodlaw/EVALUATION.md` for the numbers, how they were produced, and what they do not show. In short: against the law reporters' own citator codes (older judgments only) it found an overruling or disagreement in 35% of pairs on the held-out half (46% on the half it was tuned on), and about half of its clean adverse flags were real treatment when read by hand. `NO_ADVERSE_FOUND` is therefore weak evidence. Recent judgments (2017 to 2023) are measured on a second answer key read from the reporters' case-law tables, but it holds only 49 adverse pairs, and 2024 to 2026 judgments are measured only on 20 known cases whose labels are mine and not lawyer-checked.

## The Overruled Register (2026-10-07)

The checker only warns. What a person has confirmed, or an outside list says, about decisions that a later court overruled is kept in the Overruled Register (1,765 rows: the verified 2015 list, the post-2015 list as candidates, and sibling decisions), with an answer guard, a weekly review and a trap-question exam. See `REGISTER.md`; for the live site, `REGISTER_SITE_PATCH.md`. Tests: `python test_goodlaw_register.py`.

## Running it

1. Build the store (about 15 minutes, 2 GB, needs the two data branches checked out): `python sci_goodlaw.py build --crawl-dir ../recourse-sci-pool-data --bucket-dir ../recourse-sci-bucket-data --corpus corpus.sqlite`.
2. `python sci_goodlaw.py find --corpus corpus.sqlite "rangappa"` lists candidate judgments; `check` writes `<doc_key>.json` and `<doc_key>.md`; `batch --targets goodlaw/targets/priority.json --out reports/` does a list.
3. `python sci_goodlaw.py library`, `cards`, `cards-review` and `card` make, review and read the precomputed cards (`cards/README.md`). `python sci_goodlaw.py known --corpus corpus.sqlite` runs the 20 known cases; `python sci_goodlaw.py eval --corpus corpus.sqlite --half dev` measures agreement with the reporter's citator (the held-out half needs `--confirm-held-out` and should be run once per frozen rule set).
4. Tests: `python test_goodlaw_headers.py`, `test_goodlaw_cites.py`, `test_goodlaw_corpus.py`, `test_goodlaw_mentions.py`, `test_goodlaw_treatment.py`, `test_goodlaw_statutes.py`, `test_goodlaw_report.py`, `test_goodlaw_evaluate.py`, `test_goodlaw_modern_gold.py`, `test_goodlaw_tables.py`, `test_goodlaw_library.py`, `test_goodlaw_cards.py`, `test_goodlaw_reader.py`, `test_goodlaw_ik.py` (no real call: a fake server on 127.0.0.1).

## What it cannot do

- It sees only Supreme Court judgments we hold: the court's own site to 4 May 2017 and the open Dattam Labs bucket after that, which holds part of each year. Our crawl and the bucket together miss roughly 40% of what Indian Kanoon lists for 1968 to 1999, and about a quarter of 2018 to 2025. A judgment we lack cannot overrule anything we can see.
- High Court treatment is invisible.
- The second reader sees only the passages around a mention, so it can take a recited earlier order or a reported view for the Court's own stance.
- Rules read sentences; they miss overrulings stated without the usual words, and they can mistake a sentence about another case for one about the target (the report flags the weak ones).
- Bench strength is known completely only for judgments up to 1994 and for law-report PDFs; elsewhere it is a lower bound, and the comparison is made only when the bound already settles it (step 4 in `goodlaw/EVALUATION.md`). A larger bench's disagreement with a 1995 to 2016 judgment therefore stays a caution, not a warning.
- Case names in old OCR texts are spelled inconsistently; a case named in an unusual spelling can be missed.
