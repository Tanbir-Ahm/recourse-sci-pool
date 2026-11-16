# The retrieval miss behind the comparison article (2026-11-16)

Owner: "Yes, look at the retrieval miss". Read-only investigation: nothing built, nothing changed in either repository. Questions and leads committed in `20fa99f` before any run (paraphrases of the article's prompts D and E, which the document gives only in gist; the leads are the article's five plus four well-known section 141 authorities I added: Claude's list, not a lawyer's). Real search service, newer index d8811a9 (19,255 judgments), real Voyage embedding and re-rank, run by `run_retrieval.py` (about a cent); `count_mentions.py` and `name_reader_loss.py` are free.

## What happens (three phrasings of the section 141 question; position of the judgment in the list of judgments, 1 = first; the site feeds about 8)
| lead | authority step OFF | authority step ON (as on staging) |
|---|---|---|
| Gunmala Sales (2014) | 6, 5, 5 | **12, 20, 13** |
| S.M.S. Pharmaceuticals (2005) | 2, 19, none | 8, 24, none |
| S.M.S. Pharmaceuticals (2007) | 28, 22, 6 | 35, 27, 12 |
| HDFC Bank v Maharashtra (2025) | 20, 15, 7 | 24, 14, 10 |
| K.K. Ahuja (2009) | 14, 1, none | 1, 1, 1 |
| Aneeta Hada (2012) | none | 10, 7, 7 |
| Kamalkishor (2025) | none, 31, none | none, 39, none |
| Bridgestone (2015) | not in the first 60 for any phrasing (its best passage ranks 5,000+ by meaning: it does not read as a section 141 case; I cannot confirm that for it the article's "miss" was one) |

So with the step OFF Gunmala and S.M.S. (2005) are inside what the site feeds for the plain phrasing; with it ON (staging had it on: the 12 Nov staging-api log carries `SCI_FEED_AUTHORITY` lines and the answers carry "Named by other judgments" reading notes) Gunmala falls to 12 to 20 and S.M.S. to 8 to 24. The article's omission is reproduced by the authority step, not by title-only coverage.

## Cause
The step favours judgments it counts as named by others. It cannot see the two that matter here:
- S.M.S. Pharmaceuticals is named in the text of **69 and 70** other judgments of the index; the authority table counts **2 and 1**. Gunmala is named in **15**; the table counts **none**. (Aneeta Hada 2012: 40 named, 37 counted; K.K. Ahuja 27 named, 23 counted; Dashrath Rupsingh Rathod 22 named, 21 counted: the reader works for them.)
- Why (authority_graph.py name reader, tested on real sentences): (1) "S.M.S. Pharmaceuticals Ltd. v. Neeta Bhalla and Another" returns NOTHING: a dotted abbreviation before "v." (Ltd., Pvt., Co., Corp.) is read as the end of a sentence; the same sentence with "Ltd" and no dot is read. (2) "Gunmala Sales Private Limited v. Anu Mehta and Others" is read as first party "in gunmala sales private limited", second party "anumehtaand" against the case's own keys "gunmalasalesprivateltd" and "anumehta": the leading word "in", "Limited" against "Ltd", and "and Others" kept in the second party all stop the join.
- Size: over all 420,893 passages there are 83,957 " v. " occurrences; 1,802 (2.2%) follow a dotted abbreviation; the reader returns 74,245 mentions (0.88 per occurrence). The loss is small overall and lands on company-named cases, which are the commercial and cheque-bounce cases.
This is the "spelling variants of names in the table" limit recorded for the step on 2026-10-29 (version 2, not built).

## What I could not check
- The article's exact prompt D, and which judgments staging actually fed: the staging-api `SCI_FEED fed N case(s): ...` line for that question would show it. A fed case the answer does not name goes to the "Also read, but not named in the answer" list, so the article may also have missed a case that was fed.
- The answer model's behaviour: nothing here involves it.
- My set E leads (Damodar Prabhu, Jai Balaji) are not retrieved by either setting; the article's own five leads for E differ, so the article's 4 of 5 is not contradicted.

## Options (none started)
1. Fix the reader (dotted abbreviations, Limited/Ltd and Private/Pvt, "and Another / Others / Ors" in the second party, a leading "in") and rebuild both authority tables (offline, free); then judge it on a NEW held-out question set (the 104 used for the step's first version, and these six, must not be used to tune it). Expected: S.M.S. and Gunmala counted, so boosted rather than outweighed.
2. Meanwhile set `SCI_AUTHORITY` off on the staging `sci-search` and rerun the article's section 141 question; the step's measured gain (landmark among the first 8: 52% to 79% on production's index, 44% to 75% on the newer one, on questions Claude wrote) would be lost until the reader is fixed.
3. Send the staging-api `SCI_FEED` line for the article's question to settle what was fed.
Do not call any of this "fixed for good".
