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
| Statute dimension | the sections the case turns on and what became of them under the 2023 recodification (IPC to BNS, CrPC to BNSS) | NCRB concordance vendored from Recourse (`goodlaw/statutes.py`) |
| Coverage | where the collection ends and how much of what came after the case it holds, against Indian Kanoon's yearly counts | `coverage/year_counts.csv` |

## What the labels mean, and do not mean

- `ADVERSE_SIGNAL`: a later judgment of this Court, in its own voice, appears to overrule or reject the case (or a larger bench disagrees with it, or the law report's headnote says "over-ruled", or the reporter's citator marks it overruled). Read it before relying on the case.
- `QUESTIONED`: later judgments disagree, doubt, refer or limit it; a smaller bench appears to overrule it; the cue is hedged or may be about another case; or the legislature responded.
- `NO_ADVERSE_FOUND`: at least three later judgments we hold cite it and nothing adverse turned up. **This is silence in what we hold, not a finding that it is good law.** The coverage block says how much we hold.
- `INSUFFICIENT`: fewer than three citing judgments found.
- `STATUTE_CHANGED`: a provision it turns on was renumbered, repealed or marked changed. That is a fact about the section, not about the doctrine, which usually carries over.

## How good is it (measured)

See `goodlaw/EVALUATION.md` for the numbers, how they were produced, and what they do not show. In short: against the law reporters' own citator codes (older judgments only) it found an overruling or disagreement in 35% of pairs on the held-out half (46% on the half it was tuned on), and about half of its clean adverse flags were real treatment when read by hand. `NO_ADVERSE_FOUND` is therefore weak evidence. Recent judgments (2017 to 2023) are measured on a second answer key read from the reporters' case-law tables, but it holds only 49 adverse pairs, and 2024 to 2026 judgments are measured only on 20 known cases whose labels are mine and not lawyer-checked.

## Running it

1. Build the store (about 15 minutes, 2 GB, needs the two data branches checked out): `python sci_goodlaw.py build --crawl-dir ../recourse-sci-pool-data --bucket-dir ../recourse-sci-bucket-data --corpus corpus.sqlite`.
2. `python sci_goodlaw.py find --corpus corpus.sqlite "rangappa"` lists candidate judgments; `check` writes `<doc_key>.json` and `<doc_key>.md`; `batch --targets goodlaw/targets/priority.json --out reports/` does a list.
3. `python sci_goodlaw.py known --corpus corpus.sqlite` runs the 20 known cases; `python sci_goodlaw.py eval --corpus corpus.sqlite --half dev` measures agreement with the reporter's citator (the held-out half needs `--confirm-held-out` and should be run once per frozen rule set).
4. Tests: `python test_goodlaw_headers.py`, `test_goodlaw_cites.py`, `test_goodlaw_corpus.py`, `test_goodlaw_mentions.py`, `test_goodlaw_treatment.py`, `test_goodlaw_statutes.py`, `test_goodlaw_report.py`, `test_goodlaw_evaluate.py`.

## What it cannot do

- It sees only Supreme Court judgments we hold: the court's own site to 4 May 2017 and the open Dattam Labs bucket after that, which holds part of each year. Our crawl and the bucket together miss roughly 40% of what Indian Kanoon lists for 1968 to 1999, and about a quarter of 2018 to 2025. A judgment we lack cannot overrule anything we can see.
- High Court treatment is invisible.
- Rules read sentences; they miss overrulings stated without the usual words, and they can mistake a sentence about another case for one about the target (the report flags the weak ones).
- Bench strength is known completely only for judgments up to 1994 and for law-report PDFs; elsewhere the bench comparison is skipped.
- Case names in old OCR texts are spelled inconsistently; a case named in an unusual spelling can be missed.
