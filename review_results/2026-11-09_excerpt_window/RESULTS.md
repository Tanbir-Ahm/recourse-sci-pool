# Why the Papu Das passage showed only case details (2026-11-09) -- ANALYSIS ONLY, nothing built

Owner: "One judgement Papu Das @ Sanjoy Das v. The State of Assam (2024-05-02), Gauhati High Court: only the case citation details were shown in the answer and those were noise ... The relevant sentences were never shown. Check why this happened, and how many such judgements face this problem."

## Why (reproduced on the real index, d8811a9)
The passage is the first chunk of the order (`preamble/1`), 1,405 characters. Its text opens with the heading and case details ("BEFORE HONOURABLE MRS. JUSTICE ... ORDER 03.05.2024 Heard Mr. ... Section 482 ... Kampur PS Case No. 170/2023 ... the vehicle bearing No. AS 02 AN 0787 was seized"). The sentences that matter to the question ("the co-accused Mahabar Ali took lift from him ... the petitioner gave lift to Mahabar Ali and dropped him there") start at character 706.
* **The page** shows `EXCERPT` = 600 characters, cut back to a sentence end: 579 characters, which stop at "... along with other articles. ..." -- 127 characters BEFORE the first mention of the lift. (`sci_search_tier._cut`, `EXCERPT = 600`.)
* **The answer model** sees `FEED_PASSAGE_CHARS` = 900 characters, hard cut: it reads the lift sentences but stops at "While the p", mid-sentence, so it never saw that heroin was found in the vehicle, that the petitioner was arrested and bailed, or that the order is only about releasing the seized vehicle (Section 451) and says nothing on knowledge.
* Both windows start at the START of the passage. The search finds a passage by words anywhere in it; nothing moves the window to where the words are, and nothing skips a court heading. So the reader is shown the head of a chunk, and a chunk that opens with a heading and case numbers shows mostly noise.
The answer's Gaps line ("records a petitioner's own submission of an identical 'gave lift' account") was therefore written from the model's window, while the lawyer reading the page box could not see the lift at all.

## How many judgments face it (newer index: 19,236 judgments, 418,286 passages; scripts `scan_index.py`, `fts_proxy.py`, `summarize.py`)
**Structure of the index.**
* 66% of all passages are longer than the 600 characters the page shows, and 51% are longer than the 900 the model sees (Supreme Court 75% / 63%; Gauhati High Court 54% / 36%). For these the reader gets the head only.
* A passage that opens with a court / bench / counsel heading ("BEFORE ...", "IN THE HIGH COURT", "PETITIONER: ... RESPONDENT:", "ORDER", "Heard Mr ..."): 10,707 passages (2.6%) in 10,493 judgments. The judgment's FIRST passage is heading-led in 10,373 of 19,236 judgments (54%); heading-led and longer than 600 characters (so the page shows the heading and cuts the rest): **4,577 judgments (24%)**: 3,309 of 10,444 Supreme Court ones (32%), 1,268 of 8,792 Gauhati High Court ones (14%).
**What happens when a search retrieves them** (a lexical proxy: for 387 questions of the earlier question sets, the 12 best passages by the index's keyword table; the real search also ranks by meaning, so this is indicative; the questions are Claude's):
* In 3.0% of the retrieved passages (131 of 4,440, in 118 judgments) the passage holds at least two of the question's words and the page excerpt holds none (Supreme Court 3.3%, Gauhati HC 2.4%): the Papu Das situation.
* In 15.5% the page excerpt shows fewer than half of the words that matched.
* The answer model's 900 characters hold none of them in 0.3% (12 passages) and are cut mid-sentence in most long passages.
So the failure the owner saw is real but not common in this proxy: about 3 in 100 retrieved passages show nothing relevant on the page, about 1 in 6 show less than half of what matched; and the number of judgments that CAN show a heading-led first passage is about 4,600 (24% of the index).

## What this does not show
Real searches rank by meaning as well, so their share could differ in either direction (nobody has run the real service over these questions in this check). The proxy counts question words, not whether a sentence is relevant. "Heading-led" is a pattern list (court / bench / counsel words), not a reading of the text. No lawyer has judged any passage. Nothing was built.

## What would fix it (not built, awaiting the owner)
Show, on the page and to the model, the 600 / 900 characters around where the question's words are densest, snapped to sentence ends, with "..." at both ends, and skip a heading at the start of a passage; keep the head only when no word matches. Effects to check: the model would see different text (staging test needed); the quote check, the register scan and the "passage the model saw" log read the same window; sources already shown to users would change. Cheaper partial step: raise the page excerpt to the model's 900 characters (the Papu Das lift sentences would then show), at the cost of longer boxes.
