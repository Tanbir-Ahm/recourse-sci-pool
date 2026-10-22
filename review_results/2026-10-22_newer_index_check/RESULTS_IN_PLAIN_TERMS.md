# The court's newer archive in the search index, in plain terms (2026-10-22)

> **Update, 15:50 UTC the same day:** a third session then embedded the Guwahati open-bucket text, so the index is now 305,935 passages (this note describes it as 281,424) and 2.21 GB of memory. The final numbers, and why not everything is embedded, are in `../2026-10-22_index_holdings/RESULTS_IN_PLAIN_TERMS.md`.

**The Supreme Court's newer archive was already in the search index when you said "add it". Another session embedded it between 13:09 and 14:10 UTC today, so I did not embed anything and spent nothing.** What I could do was check it, compare it with the text store, and make the pilot's message code handle it. Tags: **[Certain]** = read from the index branch's own files; **[Likely]** = inference.

## What the index now holds [Certain]
All of it is on the branch `claude/sci-index` (the same index, new ids from 2,000,000,000 up). The index's own ledger and shift logs say:

| Source | Judgments looked at | Kept (criminal law) | Passages | Tokens charged | Cost at the listed $0.12 per million |
|---|---|---|---|---|---|
| **Supreme Court, newer archive** (ids 2,000,250,000 up) | 3,747 | **1,312** | 30,028 | 6,871,758 | about **$0.82** |
| Gauhati High Court, court's own files (ids 2,000,000,000 up) | 776 | 759 | 15,241 | 3,286,035 | about $0.39 |
| Earlier: crawl and bucket | | | 236,155 | | |
| **The index now** | | | **281,424 passages** | 77,463,772 tokens spent in all, against the ceiling of 85,000,000 | |

- Four embedding runs, all finished with "completed all pending blocks" or the one-block limit, **no wasted tokens**. The price is the listed one, not read from Voyage; the dashboard is the check.
- **Only criminal-law judgments are embedded, by the index's own design.** Of the 3,747, 2,318 were not criminal law, 113 were too short and 4 were exact copies, so they are in the text store but not searchable. My earlier "about 3,500 judgments to embed" was wrong: it is 1,312.
- I did not push anything to `claude/sci-index` and I did not apply the dedupe plan that is sitting there.

## The problem: copies [Certain]
The archive's "not in the bucket" list included judgments the bucket already holds under another date or spelling. The text store found these, and the index's own dedupe plan (131 groups, **not applied**) found most of them too:
- **127 of the 1,312** new judgments (3,939 of the 30,028 new passages, 13%) are copies of a bucket text already in the index (126) or of each other (1).
- **Until the plan is applied, a search can show the same paragraph twice**, once under the bucket's id and once under the newer archive's.
- The plan and the store agree on 119 of the 127. The store found 8 the plan did not (103 passages; the plan's rules are stricter about consolidated judgments). The plan found 12 the store did not: 8 because the bucket's date is 4 to 62 days away from the court's (the store only looked within 3 days), and 4 because the store compared only the first 20,000 characters, where the bucket's law-report headnote hides the matching body (the store had flagged one of them as uncertain). So the store's "48,647 distinct judgments" may be overstated by about a dozen; the remedy (compare the court's opening text with the whole bucket text, and look further than 3 days when the titles agree) is not done. Lists: `store_copies_not_in_the_plan.csv`, `plan_pairs_the_store_does_not_call_copies.csv`.
- The plan keeps the newer-archive copy in 59 groups and the other copy in 72. Choosing and applying it is yours; I have not.

## What I changed so the pilot can use it
- **Naming:** the connector (`goodlaw/passage_input.py`) now names a newer-archive passage from the store (1,301 of 1,312; 11 have no party names in the archive and read as "title not available"), and a passage from a **copy** is read as the judgment it copies, so the register row and the card apply whichever copy a search finds (127 of them).
- **Other courts:** the 759 Gauhati judgments are named from the index (759 of 759) and labelled "Gauhati High Court". **The message code no longer matches a High Court passage against the Supreme Court register and cards** (a name match across courts would be a guess; before this, a High Court case with the same name and year as a register row would have got a register warning). It says "Not checked by us. This is not a Supreme Court judgment...", and a reply that mixes courts says so in its header.
- Tests for all of it, each breakage I tried was caught.

## What this does not tell you, and what I would want you to decide
1. **The search quality numbers are for the old index.** The stage F figures (14% of shown passages marked misleading by AI reviewers, floor limit 15%) were measured on the index at commit `3c80a26`. The index is now 19% bigger and contains High Court passages, so the pilot would test a search nobody has measured. `review_tools/pool_runner.py` refuses to run an old experiment against the new index head, on purpose.
2. **Do you want High Court passages in the pilot's results at all?** They are now labelled and not checked. Lawyers in other states may not want a Gauhati High Court paragraph in a bail answer. The simplest control is to leave them out of the pilot's search results; I have not built the search adapter, so nothing is decided.
3. **Apply the dedupe plan?** It removes copies and cleans the search; it changes the index branch.
4. **Hosting:** the index now needs about 2.05 GB of memory (peak 2.25 GB), up from 1.76 GB (peak 1.96 GB): `review_results/2026-10-22_index_memory/after_extra_sources/numbers.json`. That moves Railway's memory cost from about $18-20 to about $21-23 a month.

Reproduce: `python review_tools/experiments/newer_index_check_2026-10-22.py --index-dir <checkout of claude/sci-index> --store corpus.sqlite --out review_results/2026-10-22_newer_index_check` (reads files only).
