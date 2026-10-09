# Q15 (R15) searched again with Shivangi Bansal (2025) in the library, 2026-10-09 (PRIVATE)

Never send to reviewers (`pool.json` names the search versions; `AUTHORITY_HITS.md` uses the key). Exploratory, tuning half, one question.

## What was fetched

The owner gave the link `https://indiankanoon.org/doc/41565735/` (the link in the owner's file for Q15, doc 81618143, is *Social Action Forum* 2018, not this judgment). One page was fetched by that link (no search, no API, no scraping; the raw HTML is not in the repository). It is *Shivangi Bansal v. Sahib Bansal*, T.P.(C) 2367/2023 with connected petitions, 22 July 2025, **2025 INSC 883**, non-reportable, CJI B.R. Gavai and Augustine George Masih J. (Indian Kanoon's header says "Author: B. R. Gavai"; the judgment text says "AUGUSTINE GEORGE MASIH, J."). Text and provenance: `review_data/fetched/2026-10-09_shivangi_bansal_v_sahib_bansal_2025_insc_883/` (the repository is private; Indian Kanoon's own header lines were cut and the cut is recorded).

## What it says, against the owner's file [Certain, from the text]

It is a **consent settlement of a matrimonial dispute**, not a reasoned ruling on section 498A. Both sides asked to settle everything (para 5); the Court records custody and visitation, waiver of alimony, quashing of all pending cases, an apology, a transfer of land and undertakings, and uses Article 142 to dissolve the marriage (para 25). The part Q15 relies on is the last paragraph (para 26): the petitions are disposed of "in terms of the above order", and "the guidelines framed by the High Court of Allahabad in the impugned judgment dated 13.06.2022 in Criminal Revision No. 1126 of 2022 vide paras 32 to 38, with regard to 'Constitution of Family Welfare Committees for safeguards regarding misuse of Section 498A, IPC shall remain in effect and be implemented by the appropriate authorities."
- **What the owner's file says:** the two-judge bench "directed the Allahabad HC's FWC guidelines, with a 2-month cooling period and no arrest, to be implemented", not reconciled with the larger bench.
- **What the text shows:** the direction is there, in one sentence. Social Action Forum and Rajesh Sharma are not mentioned; no reasons are given; the two-month period and the bar on arrest are not in the Supreme Court's text (they are in the High Court's guidelines, which it cites by paragraph number). It is a non-reportable consent order under Article 142.
- **So** whether it counts as a ruling that revives the Family Welfare Committees against the three-judge Social Action Forum is the question the owner's own To Verify item 1 puts to an advocate; the note for him is `../2026-10-09_mr_advocate_sheet/ADDENDUM_Q15_Shivangi_Bansal.md`. Until he answers, Q15's expected answer should be read as "unsettled, resting on a one-sentence direction in a consent order", and Shivangi Bansal should not be treated as a ruling that settles the point.

## Side index and run

`review_data/side_index/2026-10-09_fetched_shivangi_bansal/` (builder's "fetched" mode, id 6000000002): 1 document, 23 passages, 4,635 tokens, **$0.0006**. Q15 re-run alone over main + the three side indexes (`pool_runner.py --only R15 --supplement ... x3`): 131,667 re-rank tokens, **$0.007**. Scored with `key_overlay.json` (Shivangi Bansal as Q15's key document; the key file is unchanged).

## Result (authority-hit test; no mark)

| | Main index only | Main + side indexes |
|---|---|---|
| Shivangi Bansal in the top 10 | not in the library | **not in the top 10 of A, B, E, F or S; rank 6 in the rewrite version C** |
| What the top results were | Rajesh Sharma (2017) at ranks 1 and 2, Social Action Forum (2018) at rank 4 | the same |
| Older rulings counted as stale in the top 5 | Rajesh Sharma | Rajesh Sharma (2 passages in A, B, E; 1 in C and F; 2 in S) |

**Why it is not found** (`diagnose_r15.py`, `diagnose_r15.json`, $0.0024; its retrieval can differ slightly from the recorded run): the 23 passages of Shivangi Bansal are far from the question by meaning (the nearest is rank 172 of 238,000; it is a list of pending petitions, not para 26); none is in the 100 nearest, the keyword top 50 or the section search; forced into the 60 candidates, its best passage would be 11th (score 0.393 against 0.404 for the 5th result). Rajesh Sharma's best passage is rank 2 by meaning and ends 1st; Social Action Forum's is rank 8 by meaning and ends 4th. The question is a story about a 64-year-old woman accused with her family under BNS 85/86; a settlement order about custody, an apology and a land transfer is not what that question is about. [Likely] **Q15's key-authority test is therefore a poor test of retrieval:** the search is arguably right not to put this judgment first. What the question needs is Social Action Forum and Arnesh Kumar with the old Rajesh Sharma directions marked as modified, which is a currency matter (the register does not hold Rajesh Sharma), not a library gap.

Files: `pool.json`, `questions.jsonl`, `spend.json`, `key_overlay.json`, `authority_hits.json`, `AUTHORITY_HITS.md`, `diagnose_r15.py`, `diagnose_r15.json`.
