# What was done with the "List of Overruled Cases", from the PDF to the last step (plain terms)

**Source label: an outside list of unknown origin, read by software I wrote. Nothing here is checked by a lawyer.** Written 2026-10-07.

## The uncomfortable truth first

After all this work the checker still flags only **29%** of the overrulings in your list (it was 26%). The list itself is an unverified compilation that stops around 2015 and has mistakes of its own. What is solid: I found out *why* the checker misses things, fixed those specific causes without breaking anything else we measure, and kept half of the list untouched for a clean test later.

## Words used here

- **The checker**: our tool that asks, for one Supreme Court case, "has a later judgment in our collection said something against it?" (overruled, disagreed, doubted, sent to a larger bench, or Parliament overcame it). It gives a label, never a verdict: ADVERSE_SIGNAL, QUESTIONED, NO_ADVERSE_FOUND or INSUFFICIENT.
- **The list**: your PDF, 1,688 entries, each "case A, overruled by case B".
- **A pair**: case A and the later judgment B. I ask: reading B's text, does the checker notice B saying A is overruled?
- **Flagged**: the checker read B as overruling, disagreeing with, or doubting A.
- **Confident flag**: flagged, in the court's own voice (or the law report's headnote), and not hedged.
- **False alarm**: a flag on a case that is fine.
- **Tuning half / untouched half**: I split the test pairs by the list's row number, before running anything. Even rows are for finding and fixing problems; odd rows stay unseen for one clean test at the end.
- **Fast reader / full pipeline**: two ways of running the checker on a pair. The full pipeline is what a real report uses. Both gave identical readings here.
- **Library cards**: our precomputed checks on the 76 cases the Recourse site can show.

## Step by step

### 1. Getting the file to me
Your first two attempts did not reach this session. You asked where to put it, so I created an `inbox/` folder on the work branch with a README. You uploaded `520254941-List-of-Overruled-Cases.pdf`. I treated it as data only: never run, and nothing inside it followed as an instruction.

### 2. Reading the PDF
- 260 pages, a Word 2019 document, author field "PADMARAJA", created 2020-10-29, real text (not a scan). No stated compiler, source or date.
- It is a two-column table. My first reading went wrong in three ways, and I fixed each: a cell that continues over a page break was attached to the wrong row; some rows were printed as one block across both columns (13 rows came out with an empty right side); and one row (75) truly has an empty "overruled by" cell in the source.
- Result: 1,688 rows, numbered 1 to 1688, no gaps, no repeats.

### 3. What is in the list, and how reliable it is
- **71% (1,196) are High Court or tribunal decisions**, which our collection cannot hold (it holds Supreme Court judgments only). 409 of these (24% of all rows) are just the Supreme Court reversing the same case on appeal, not overruling a precedent.
- **29% (492) are Supreme Court judgments overruled by a later Supreme Court judgment.** Only these matter for us.
- **It stops around 2014 to 2015**, though the file is dated 2020. By year: 2010: 17, 2011: 41, 2012: 22, 2013: 6, 2014: 7, 2015: 2, nothing later. So it cannot contain, for example, Mukesh Singh (2020) overruling Mohan Lal (2018).
- **It is incomplete even inside its dates.** Prabha Shankar Dubey (overruled by the Jadeja Constitution Bench, 2010) and Krishna Janardhan Bhat (Rangappa, 2010) are missing. Present: Golak Nath/Kesavananda, Satish Mehra/Debendra Nath Padhi, Raj Deo Sharma and Common Cause/P. Ramachandra Rao, K. Bhaskaran/Dashrath Rupsingh Rathod, Naz Foundation/Koushal.
- **It contradicts itself in places**: 6 pairs list each case as overruled by the other; 14 matched pairs name an overruling decision dated before the overruled one; about 2% of its citations point at a different judgment (27 rows).
- **It uses "overruled" loosely** (appeals, partial overrulings, "not followed"), with no dates, benches or paragraphs.
- **It is probably someone's commercial compilation** (see step 7), so keep it as private test data.
- 279 rows (17%) carry a criminal-law reporter marker.

### 4. Matching the list to our collection
- First by the printed citation (AIR, SCC, SCR). This turned out to fail for later years: **our collection holds no AIR or SCC citation keys for judgments after about 1997**. So I added a second pass by party names and year (I checked samples by hand: 18 of 18 looked right).
- Result: **80% of the overruled Supreme Court cases and 84% of the overruling ones are in our collection** (at least). By decade: 94 to 100% for the 1950s to 1980s, about 80% for the 1990s, about 78% for the 2000s. So the collection looks thinner for 1990 to 2009, which fits the 8,821 crawl ids with no file at the court.
- **None of the 61 library cases that are in our collection is listed as overruled** in the list. So the list adds nothing to the checker's two warnings (Mohan Lal, Mhetre).

### 5. The test I set the checker
- 331 pairs had both judgments in our collection. I dropped 14 (overruling dated before overruled) and 9 more (a citation that matched a different case): **308 usable pairs, 59 of them with a criminal marker**.
- Split by row number: **even rows = 146 pairs (the tuning half, run); odd rows = 162 pairs (untouched, NOT run)**.
- Every pair is a "yes, it was overruled", so this measures recall only (how many the checker catches), not false alarms.

### 6. First result, before any change
- The later judgment names the case in 84% of pairs.
- **38 of 146 (26%) flagged**; 33 confident; 30 as an explicit overruling. By era: 29%, 23%, 27%. Criminal-marked pairs: 4 of 24 (too few to judge).
- That is lower than the older keys (35% held-out, 46% development), which is the honest guide.
- I read the misses: of 28 where an overruling-type phrase sat near the case's name, about **9 were real statements the checker misses**. Three examples: row 668 ("The decision in Rajinder Kaur is hereby over-ruled" was not recognised as naming the case), row 422 ("the decision in Jugraj Singh's case 1s erroneous": a scanned "is", and a low-confidence name), row 420 ("The law laid down in Paras Ram ... has been held to be not good law": the checker read "law laid down" as *following* it, a positive reading of a case the sentence condemns).
- I wrote this up and committed the analysis folder `external_lists/2026-10-07_overruled_cases_pdf/` (a README, the parsed table, the pair list, the checker's readings, my scripts) and a note in FOLLOW_UPS.

### 7. The referencer.in website
- You asked me to read all 21 pages of `https://www.referencer.in/SC_Overruled_Cases.aspx`. The environment blocked the site. I read the documentation and told you to add `www.referencer.in` to the allowed domains. It still failed in the same session, then worked after your change took effect. I did not try to get round the block.
- Before reading, I fetched the site's robots.txt (it does not exclude this page) and its disclaimer: **the copyright stays with the site's administrator and access gives no licence to reproduce or distribute.** So I read the pages into scratch space only and put none of the list text in the repo.
- **There are 34 pages, not 21** (the page links shown are only a window). I read all 34, once, 3 seconds apart, the way the page's own links work; one dropped connection was retried.
- **Result: it is the same list.** 1,677 of the 1,688 pairs are identical to the PDF's; the other 11 differ only in layout. Same count, same errors, same last year (2015). Six website rows still carry the PDF's own serial numbers in the text, so the table was loaded from the same numbered document (which came first is unknown). The website adds no new cases and no dates.
- A useful by-product: my PDF reading agrees with the website's on all but 6 rows, none of them in the test pairs.

### 8. "Strip the text columns, then fix the three misses"
- **Strip**: I removed the case names and citations as printed from the CSV files in the repo (and the judgment titles from the results file). The row numbers, flags, document keys and the court's own sentences stay. The earlier versions still exist in git history (the PDF itself, uploaded by you, is also in `inbox/`).
- **Baseline first**: I copied the code as it stood, ran all unit tests (all passed), and measured the old-text and modern-text evaluations, the 20 known cases and a "production" run, so every later change could be compared with a clean "before".

### 9. The fixes, and what each one does
Causes found by reading the misses, with the fix for each (all with unit tests):
1. **Names**: the checker looked for "X v. Y" but later judgments print "X and Another v. Y" or "X & Anr. vs. Y"; it also treated "State of Punjab" and "Punjab State" as different. Both are now accepted (this lets it find more later judgments).
2. **Wording**: "has been held to be not good law" and "held not to be good law" are now verdicts. A double negative ("cannot be held to be not good law") is not. "T held X to be not good law" is a verdict on X, not on T.
3. **Scanned text**: "1s" is read as "is" (and shown as printed).
4. **Negation**: a "not" in an earlier clause ("is not correct and is overruled") no longer turns the overruling into its opposite.
5. **Counsel**: "According to Mr. X ..." is counsel's argument, not the court.
6. **"Held in T"**: "held by this Court in T that ..." and "held to be per incuriam in T" name the authority, not the case judged; this also holds with a footnote number or "& Ors." after the name.
7. **Time and grounds**: "up to T" and an opening "In view of T, ..." do not make T the subject of what follows.
8. **Voice**: "overruled subsequently by the Constitution Bench in T": the word "subsequently" no longer hides that T did the overruling.
9. **Run-together sentences**: when the splitter joined two sentences (closing quote, footnote number, capital letter), a phrase from one is no longer attached to the case in the other.
10. **Report**: a weak reading and a firm reading with the same wording in one judgment are no longer merged. Before, the firm one could be hidden behind the weak one.

### 10. What went wrong on the way (and was corrected)
- The better name matching made more later judgments count as confident mentions, and that **exposed older misreads**. On the 76 library cards, **two settled cases (Mukesh Singh, Sushila Aggarwal) and the known case Puttaswamy turned from "no problem found" to "questioned"**: false alarms.
- **I first blamed the wrong change.** I had also added a "re-read the texts after a citation is learned" idea (it fixed row 422). I undid it, re-checked, and the false alarms stayed. I told you my diagnosis was wrong. Then I traced the real causes: my own new "be not good law" wording, plus three old misreads (items 8, 2 and 9 above). Even the original code read those sentences the same wrong way; it escaped only because the report's merge (item 10) happened to hide the firm misreading. I had also compared the cards with the committed ones and not with a fresh run of the original code, which hid this for a while.
- I committed the first set of fixes before all checks were done (the repository's hook asked for committed work), so that commit included the risky change; the undo and the corrected fixes followed as separate commits.
- Three times my own "stop the old run" command also stopped my own shell, so I had to restart runs to keep every result from one frozen version of the code. That cost time but kept the numbers clean.
- I stopped a long wait when you interrupted, and asked you before spending another 45 minutes. You approved each step.

### 11. Final results

| | Before | After |
|---|---|---|
| Old text, adverse pairs the checker catches | 29 of 59 | 29 of 59 |
| Old text, false flags among 8,065 other pairs | 49 | 49 |
| Modern text, adverse pairs caught | 16 of 22 (also in the full pipeline) | 16 of 22 |
| Modern text, false flags among 8,776 | 114 | 115 (the new one is a real doubt: a two-judge reference bench doubted B.S. Joshi) |
| 20 known cases | 7 of 7 flagged, 13 of 13 clean | every label identical |
| 76 library cards | 46 / 18 / 10 / 2 | same, no status changed (one card lists one weak reading instead of two; four cards gained 1 to 3 citing judgments) |
| The list's 146 tuning pairs flagged | 38 (26%), 33 confident | **42 (29%), 37 confident** |
| Report fix (item 10) | n/a | no change on any of the 76 cards; known cases identical |

- Rows 668, 420, 254 and 288 now read as the verdicts the later judgments state. Row 422 reads adverse but not confidently.
- **These are in-sample figures**: I found the fixes by reading these very pairs and the library cards, so expect less on fresh cases. The gain on the list is small (4 pairs).

### 12. What I did NOT do, and what is still open
- I did **not** run the odd half of the list (162 pairs); it is kept for one clean run after any further tuning.
- I did **not** run the second reader (the model that reads passages) on the list; the 29% is the pattern rules alone, so the second reader might do better.
- I did **not** regenerate the committed library cards (the new code gives the same statuses).
- Nothing was merged to `main` and no pull request was opened. Nothing was connected to the live Recourse site. No Voyage or Indian Kanoon money was spent in this work.
- **Open:** row 422 needs the "re-read after a citation is learned" idea, retried as its own tested round; two cases named together before "is not correct and is over-ruled" are read wrongly for the first-listed one (seen, not examined); an overruling by a smaller bench is listed as a firm possibility, not a weak one; the list's labels are unverified, and no lawyer has checked any reading.
- **The list should not be used as Recourse content**: it is unverified, ends around 2015, uses "overruled" loosely, and the website that publishes it reserves its copyright.

### 13. Where everything is
Branch `claude/sharp-euler-unyfv0`. Commits, in order: `697a5c0` (inbox folder), `927fa9f` (your PDF), `2628161` (analysis), `d9a4c5f` (website finding), `1270276` (text columns stripped), `bd0bc72` (first fixes), `14111ea` (undo of the re-read idea), `5669fac` (the three misread fixes), `1d66e6a` (results and notes), and `aedaceb` (the report fix). Notes: `goodlaw/EVALUATION.md` (section "An outside list of overruled cases"), `FOLLOW_UPS.md` (item 1j), and `external_lists/2026-10-07_overruled_cases_pdf/README.md`.
