# How many judgments could a "Judgment at a Glance" page serve? Measured 2026-10-20 (owner's question after the mockup)

Data: the search index `claude/sci-index` commit `3c80a26` (the same one the search service loads; local checkout `../recourse-sci-index`) and `names_table/names_table.json.gz`. Counted with a short script over every `*.meta.jsonl.gz` shard (one record per passage: `doc`, `pn` paragraph number or none, `section` tag, `method`) joined to the names table by `doc`. Not run on Railway; nothing here is deployed.

| Requirement | Judgments |
|---|---|
| In the index (criminal-law Supreme Court judgments, index ends 2026-07-13) | 10,503 with passages (10,522 in the names table incl. 19 side-index) |
| 1. name + date + link all present | 9,727 |
| 2. = 1 and a real judgment (3,000+ characters of indexed text) | 9,244 |
| 3. = 2 and paragraph numbers (a quote can carry a paragraph) | 5,241 |
| 4. = 3 and a passage tagged "order" (for a decision panel) | 3,012 |
| 5. = 4 and passages tagged facts and reasoning | 2,933 |
| 6. = 5 and a passage tagged "argument" | 2,687 |
| Order-tagged, 3,000+ chars, with or without paragraph numbers | 5,367 |
| Of row 4: dated 2010 or later / with an SCR or AIR citation | 2,338 / 1,913 |

Paragraph numbers are all-or-nothing per judgment: 5,934 judgments were split by paragraph (every passage numbered), 4,569 were split by sentences (none numbered).
Section tags (facts, argument, reasoning, order, statute_text, header) come from rules that have not been checked against a lawyer's labels (INDEX_RUNBOOK): rows 4 to 6 are upper bounds.
Names table: 10,454 of 10,522 named; 727 have no date; 4,010 have an SCR or AIR citation; 68 unnamed rows flagged for review; no person has checked the sample (`names_table/README.md`).
Not in the index: 33,395 of 49,096 judgment records seen were skipped as not criminal law (civil, tax and so on); also skipped 1,313 short, 660 duplicate, 139 near-duplicate; 3,084 bucket judgments were already in the crawl. No High Court judgments.
Lawyer-reviewed cases: none. Currency cards (who cites it, followed/doubted): 66 library cases (76 library rows: 61 matched to a corpus judgment, 10 High Court and not checkable); the mention finder could be run for any target, it has not been.
Library full text (Recourse `chunks/`): about 60 judgments from Indian Kanoon, separate from the index.
