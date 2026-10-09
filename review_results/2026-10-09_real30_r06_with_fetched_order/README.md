# Q6 (R06) searched again with the order of 23 August 2024 in the library, 2026-10-09 (PRIVATE)

Never send to reviewers (`pool.json` names the search versions; `AUTHORITY_HITS.md` uses the key). Exploratory, tuning half, one question.

## What was fetched

The owner's file gives the key authority of Q6 as the Supreme Court's order of 23 Aug 2024 in W.P.(C) 406/2013 (Hima Kohli and Sandeep Mehta JJ.) with the court's own PDF link. The environment's network access was opened for `api.sci.gov.in` and the PDF was fetched on 2026-10-09 09:56 UTC (HTTP 200, 8 pages, 69,056 bytes, last modified by the court 27 Aug 2024). Original, plain text (pdftotext, unedited), provenance and what I checked by reading: `review_data/fetched/2026-10-09_wpc406_2013_order_23aug2024/` (public court document).

**Checked against the owner's file [Certain, from the text]:** case, date and bench match. The order records the amicus' point about the first proviso to s.479 BNSS (first-time offender, one-third), records the Additional Solicitor General's statement, on the Department's instructions, that the provision applies to all undertrials in pending cases whether or not the case was registered before 1 July 2024, and **directs immediate implementation** (jail superintendents to process applications on completion of one-half or one-third; two months; affidavits; District and Sessions Judges to see to compliance). **One difference from the file's wording:** the file says the Court "held" that s.479 applies to cases registered before 1 July 2024; the order records the Union's position and directs implementation, with no reasons and no "held". The exclusion of death and life-imprisonment offences is in the statute, not in this order. This does not change what a good answer says; Mr. Advocate's workbook (sheet C, Q6) lets him confirm the wording.

## Side index and run

`review_data/side_index/2026-10-09_fetched_documents/` (built with `build_supplement.py --docs review_data/fetched/fetched_docs.json`, the new "fetched" mode: id 6000000001, must be new to the main index): 1 document, 12 passages (5 of them the order's list of counsel, cut by the index's own rules like any such order), 3,456 tokens, **$0.0004**. The runner now takes several `--supplement` folders.
`pool_runner.py --half dev --only R06 --supplement ...correcting_judgments --supplement ...fetched_documents`: 116,248 re-rank tokens, **$0.006**. Scored with `key_overlay.json` (the fetched order is Q6's key document; the key file is not changed).

## Result (authority-hit test; no mark)

| | Main index only | Main + both side indexes |
|---|---|---|
| Key authority (the 23 Aug 2024 order) | not in the library | **rank 2** in A and B; **rank 1** in C, E, F and S; 4 of A's top 5 passages are the order's own paragraphs |
| What the top results were | Parvinder Singh v. ED (2026), Partha Chatterjee v. ED (2024): bail in money-laundering cases | the order first or second; Parvinder Singh next |

What this shows [Certain]: Q6's miss was a library gap, not a search failure; once the order is in, every version finds it. What it does not show: how the search does on questions whose key document nobody added (that is what the main-index marks measure). The new passages are not marked by anyone.

## Q15 is still open

The Indian Kanoon link in the owner's file for Q15 (`https://indiankanoon.org/doc/81618143/`) is **not Shivangi Bansal v. Sahib Bansal (2025)**: it is *Social Action Forum for Manav Adhikar v. Union of India* (14 Sept 2018, three judges: D.Y. Chandrachud, A.M. Khanwilkar, Dipak Misra), which the collection already holds. The right document needs its own link (the court's PDF or an Indian Kanoon page); the court's API host has no directory listing and scraping Indian Kanoon's pages is ruled out in `IK_PLAN.md`, so I did not search for it. The one page fetched from Indian Kanoon was kept in scratch space only and is not in the repository.
