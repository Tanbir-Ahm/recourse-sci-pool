# "List of Overruled Cases" (PDF, 260 pages): what it is, how reliable it looks, and how the checker did on it

**Source label for everything here: an outside list of unknown origin, read by software I wrote, not checked by a lawyer.** The checker numbers are a test on the tuning half only (see "How the test was split").

The file: `inbox/520254941-List-of-Overruled-Cases.pdf`, uploaded by the owner on 2026-10-07. Word 2019 document, author field "PADMARAJA", created 2020-10-29, 260 A4 pages, real text layer (not a scan). Title "Supreme Court Overruled Cases". A two-column table, "List of Overruled Cases | Overruled by", numbered 1 to 1688. Nothing in the file says who compiled it, from what, or as of what date. Read as data only; nothing in it was run or followed.

## What it contains (counted by `tools/parse_overruled.py`; sequence 1 to 1688 complete, no gaps or repeats)

| | Entries | Share |
|---|---|---|
| All entries | 1,688 | |
| The overruled decision is a **High Court, tribunal or other non-Supreme-Court decision** | 1,196 | 71% |
| ... of which the "overruling" decision is the same dispute on appeal (same parties): the Supreme Court reversing that High Court, not overruling a precedent | 409 | 24% of all |
| The overruled decision is a **Supreme Court judgment** (overruled by a later Supreme Court judgment) | 492 | 29% |
| Entries with a criminal-law reporter marker (CriLJ, Crimes, SCC(Cri), RCR(Criminal) ...) in either cell | 279 | 17% |

- The list is grouped by court of origin: Allahabad first (about 1 to 300), then the Supreme Court section (about 226 to 750), then Punjab & Haryana, Bombay, Kerala, Karnataka and Gujarat, Delhi, Andhra Pradesh and Patna.
- **The only part that bears on our collection is the Supreme Court section**: our collection holds Supreme Court judgments only, so an overruled High Court decision cannot be a target in it.
- Overruling decisions by year (year taken from the AIR or SCC citation): thick from 1990 to 2009 (469 and 628), then 95 for 2010 to 2015: 2010: 17, 2011: 41, 2012: 22, 2013: 6, 2014: 7, 2015: 2, nothing later. **[Certain] The list stops around 2014 to 2015, although the file was created in 2020.** It cannot contain, for example, Mukesh Singh (2020) overruling Mohan Lal (2018).

## How reliable it looks

- **Incomplete even inside its own dates. [Certain on absence, Likely on the legal fact]** Prabha Shankar Dubey (2004), overruled by the Jadeja Constitution Bench (2010), is not in it, and neither is Krishna Janardhan Bhat (2008), whose view Rangappa (2010) rejected. Present: Golak Nath by Kesavananda, Satish Mehra by Debendra Nath Padhi, Raj Deo Sharma and Common Cause by P. Ramachandra Rao, K. Bhaskaran by Dashrath Rupsingh Rathod, and Naz Foundation by Koushal.
- **Internally inconsistent in places.** 6 pairs list each case as overruled by the other (rows 247/506, 265/242, 270/258, 446/645, 463/535, 594/474); 14 matched pairs name an overruling decision dated before the overruled one; row 75 has an empty "overruled by" cell; 27 of 1,354 citations I matched point at a different judgment in our store (for example row 678 gives "Kartar Singh v State of Punjab, AIR 1993 SC 341", which our store reads as a different case): typos in the list or a wrong key in our store, not told apart.
- **"Overruled" is used loosely.** 24% of rows are an appeal reversing the lower court. In the Supreme Court section, an entry can be a partial overruling, a "not followed", or a later bench that merely records what happened elsewhere (reading the missed pairs, several citing judgments state the overruling by a third case). The list gives no date, no bench, no paragraph, no "partly".
- **Provenance. [Certain] It is the same list as the "List of SC Over-ruled Cases" on www.referencer.in** (see the next section): a reference site for customs, excise and GST officers, whose disclaimer reserves the copyright and gives no licence to reproduce or distribute. Keep it as private test data and do not publish it or use it as site content; the list text itself should not sit in a public repository. This repository is described as private (not verified by Claude).

## The same list on referencer.in (checked 2026-10-07)

- `https://www.referencer.in/SC_Overruled_Cases.aspx` shows the list in a table, 50 rows a page. **It has 34 pages (1,688 rows), not 21**: the pager shows a window of page links, so only pages up to 21 are visible from page 1. All 34 pages were read once, slowly (3 seconds between requests), with the same click-through the site's own pager uses; the site's robots.txt does not exclude this page. The pages were kept in scratch space only, not in this repository.
- **Content: 1,677 of the 1,688 (overruled, overruling) pairs are identical to the PDF's; the other 11 differ only in layout** (a cell split across a page in the PDF, or an old serial number left in the text). Same count, same errors (the empty "overruled by" cell, the contradictory pairs), same last year (2015) and the same number of overruling decisions per year. The web order differs: newest overruled decision first, down to a 1902 Madras case.
- **Provenance clue:** six web rows still carry the PDF's own serial number at the start of the case name (1606, 569, 1094, 1165, 1139 and 1), so the web table was loaded from the same numbered document, in its order, and then re-sorted. Which copy came first is not known.
- So the website adds **no new cases, no later years and no dates**; it is a second copy, not a newer one. The test pairs and results in this folder are unchanged. A cross-check of my PDF parser against the web copy: 6 of 1,688 rows differ in text (rows 289, 704, 764, 1038, 1172, 1383), none of them in the test pairs.

## How much of it is in our collection

Matching uses the printed AIR/SCC/SCR citation first. The collection holds no AIR or SCC keys for judgments after about 1997, so a second pass matched party names within one year (18 of 18 sampled matches looked right).

| | Found in the collection |
|---|---|
| Supreme Court decisions named as the overruled case (492) | 395 (80%): 1950s 85%, 1960s 100%, 1970s 86%, 1980s 81%, 1990s 69%, 2000s 58% |
| Supreme Court decisions named as the overruling case (1,683) | 1,417 (84%): 1950s to 1980s 94 to 100%, 1990s 80%, 2000s 78%, 2010s 87% |

Those percentages undercount (spelling variants, 81 ambiguous name matches left out), so read them as "at least". The list works as a rough outside probe of coverage: **our collection looks complete for 1950 to 1989 and thinner, perhaps 20% short, for 1990 to 2009**, which fits the crawl's 8,821 ids with no file at the court. [Likely]

**None of the 61 library judgments (the cases Recourse can show that are in our collection) appears as an overruled case in the list.** One, State of Maharashtra v Tapas D. Neogy, appears twice as an overruling case.

## The test pairs (an answer key the checker was never tuned on)

- Pairs where both the overruled and the overruling judgment are in the collection: 331. Dropped: 14 with the overruling decision dated before the overruled one; 9 more whose citation matched a judgment with a different name (27 rows were flagged this way, 9 of them in the pair set; `tools/` and `rows_parsed.csv` column `match_suspect`). **308 usable pairs** (`test_pairs.csv`), 59 of them with a criminal reporter marker.
- That is three times the 116 adverse pairs of the old reporter key and six times the 49 of the modern case-law tables, over 1950 to 2014. Weaknesses: the label is the list's, unverified; every pair is a positive, so it measures **recall only, not false alarms**.

### How the test was split

By the list's row number: **even rows are the tuning half (146 usable pairs, run on 2026-10-07), odd rows the untouched half (162 pairs, NOT run)**. Any rule change prompted by this list must be tuned on the even rows only; the odd rows are then run once at a frozen commit, as with the earlier keys. Rules at the time of the run: the work branch at commit `927fa9f`.

### Result on the tuning half (146 pairs; the checker reads the later judgment for each pair)

| | Pairs |
|---|---|
| The later judgment names the overruled case (mention found) | 122 (84%) |
| Read as overrules, disagrees or doubts | **38 (26%)** |
| ... of which in the Court's or headnote's own voice and confident | 33 |
| Read as an explicit overruling | 30 (21%) |
| Read as neutral, follows, distinguishes or limits | 82 |
| No mention found | 24 |

- The fast per-pair reader and the full pipeline (candidates from the citation index, citations learned from the corpus) give **the same reading on all 146 pairs**.
- By the later judgment's decade: 1950 to 1979: 15 of 52 (29%); 1980 to 1999: 15 of 64 (23%); 2000 to 2015: 8 of 30 (27%). **Criminal-marked pairs: 4 of 24 (17%)** against 34 of 122 (28%) for the rest; 24 is too few to call it a difference. [Guessing]
- Earlier recall figures for comparison: 35% held-out and 46% development on the old reporter key; 71% (15 of 21) on the tuning half of the modern tables (those were in-sample). 26% here is the first number on an outside key that the rules were not tuned on, so it is the better guide to how many overrulings in the collection the checker would flag. [Likely]

### What the 108 non-flagged pairs look like (I read the 28 that had an overruling-type phrase near the case's name)

About 9 are real statements the checker misses; the rest are statements about a different overruling or a headnote line about another case. Causes seen, on the tuning half:

- **Row 668 (Rajinder Kaur, overruled in Sukhwinder Singh):** the court writes "The decision in Smt. Rajinder Kaur vs. State of Punjab is hereby over-ruled". The only mention the reader found was counsel's earlier reliance on the case (full citation), so it read neutral. The overruling sentence uses the name without a citation or "and another" and was not recognised as a mention.
- **Row 422 (Jugraj Singh, overruled in Ramawadh):** "We are of the view that the decision in Jugraj Singh's case 1s erroneous". Name-only mentions are low confidence, and the scanned text misreads "is" as "1s".
- **Row 420 (Paras Ram, treated as not good law in Balbir Singh):** the sentence is "The law laid down by this Court in Paras Ram ... has been held to be not good law by the Constitution Bench in Sanjay Dutt". The reader read the opening as **follows**. This is the worst kind: a positive reading of a case the sentence calls not good law.
- Also seen: "stood overruled" said of a case in a list, "erroneous" and "over-ruled" appearing only in the headnote summary, and overrulings reported by the citing court as another bench's work.

None of these was fixed; the owner asked only for the analysis.

## What to do with the list

1. **As an outside answer key, yes**, on the even rows now (to find and fix causes like the three above) and the odd rows once, afterwards, at a frozen commit. It cannot tell us about false alarms or about anything after 2015.
2. **Not as a source for Recourse**: it is unverified, ends around 2015, and carries loose "overruled" labels. It does not mention any library case.
3. Not as a substitute for a lawyer reading the review sheet.

## Files

The list's own text (case names and citations as printed) is **not** kept in these files, because of the copyright reserved by the site that publishes the same list (see above). It stays in the PDF in `inbox/` and in earlier commits of this branch (`927fa9f` and `2628161` hold the first versions of the two CSVs with the text).

- `rows_parsed.csv`: one line per list row (1 to 1688): PDF page, whether the overruled decision is a Supreme Court one, same-parties flag, criminal marker, the matched collection document keys and how they were matched, suspect flag, test half.
- `test_pairs.csv`: the usable pairs (collection document keys, dates) and their half.
- `checker_results_tuning_half.csv`: the checker's reading, cue, voice and the sentence it read (the court's own words, from our collection) for the tuning pairs, by list row number.
- `tools/`: the scripts, as run (they point at scratch paths of the cloud session; `parse_overruled.py` reads the PDF with PyMuPDF, `match_overruled.py` and `match2_overruled.py` match to the corpus store, `run_overruled_fast.py` and `run_overruled_prod2.py` run the checker, `score_overruled.py` and `miss_context.py` summarise). The corpus store is rebuilt with `python sci_goodlaw.py build`; the row text needed to rerun them is re-read from the PDF.
