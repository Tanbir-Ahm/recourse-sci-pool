# Landmark check on the whole index (2026-10-24, index head `38d1d3f`, record `eval/landmark-20261024T175049.json` on `claude/sci-index`)

The index's own known-answer test: 6 verified Supreme Court landmarks, 12 questions (a plain-language one and a legal one for each). A question **passes** only if the landmark is among the top 5 *cases* AND its verified paragraph is among its own top 3 passages. Same method and questions as the earlier runs. Cost of this run: 12 question embeddings and 24 re-rank calls (12 for the whole index, 12 for the Supreme-Court-only view), 388,847 re-rank tokens, **about $0.02**.

## The result [Certain]
| When | Passages searched | Passes (of 12) | Landmark among the top 5 cases | Verified paragraph in its top 3 |
|---|---|---|---|---|
| 2 Oct, the old crawl (and a few bucket passages) | 156,235 | **4** | 6 | 8 |
| 22 Oct 17:27, after the newer archive, Guwahati to 2017 and the duplicate removal | 300,957 | **2** | 2 | 4 |
| **Today, the whole index** | **418,286** | **1** | **1** | **3** |
| Today, the same index with every Guwahati judgment taken out | 261,572 | **2** | 4 | 5 |

Today, whole index: where the landmark came, question by question: 1st (Rangappa, legal question: the only pass), 6th and 7th (Arnesh Kumar), 6th (Jadeja, legal), 14th, 18th, 27th, 33rd, and **4 questions where it was not among the 60 candidates at all** (Md Ibrahim both questions, Rangappa plain question, Noor Aga legal question). By meaning alone (before the re-ranker): 0 of 12 (it was 3 of 12 on 2 October).

## Who takes the top five places [Certain]
12 questions x 5 places = 60: Supreme Court old crawl 19, open bucket 19, newer archive 6, **Guwahati 16 (27%)**; Guwahati judgments are 37% of the passages. In 7 of the 12 questions at least one Guwahati judgment is in the top five. Examples: for the Md Ibrahim legal question three of the top five are Guwahati judgments; for the Noor Aga legal question three of the five are Guwahati and the landmark is absent.

## What it means
- **Nothing is broken [Certain]:** every vector and passage is where it should be; the search finds judgments on the right subject. The test is strict: it wants the landmark itself in the top five, while later judgments that quote and apply the landmark (for example Satender Kumar Antil 2022 and Social Action Forum 2018 above Arnesh Kumar) crowd it out. Such later judgments can be useful to a lawyer, but a lawyer asking for the leading case would not want the leading case at 7th place.
- **The trend is real but the sample is small [Likely]:** 12 questions on 6 cases; one question is 8 points. The direction is the same on all three measures (6, 2, 1 of 12 for the case in the top five) and the Guwahati-removed view gives back 3 questions in the top five.
- **Two causes [Likely]:** (1) the library grew by about 2.7 times and later Supreme Court judgments (open bucket and newer archive: 2,344 + 1,239 judgments) compete with the old landmarks; (2) the Guwahati judgments (7,553) add a second layer, because High Court judgments quote Supreme Court paragraphs at length.
- **Ideas, none tried [Guessing]:** show High Court judgments as a separate, labelled tier below the Supreme Court list (this is also the rule `FOLLOW_UPS.md` item 1c records for a less-reviewed pool); a court weight in the final score; a "cited by" boost for landmarks; folding later judgments that merely quote the same paragraph into the original. Each can be tested on these 12 questions for a few cents; the 12 questions are too few to choose between them, so a larger set (and lawyers' marks) would be needed.
