# How good is the checker? (measured, with its limits)

Everything here is labelled by source: **pattern-rule reading of Supreme Court texts, not lawyer-validated.** The numbers describe how well the rules read the *treatment* of a case in later judgments. They do not measure whether a case is good law.

## The short version

- **A clean `NO_ADVERSE_FOUND` is weak evidence.** Against the law reporters' own citator codes (below), the checker finds an overruling or disagreement in about **one pair in three** it should (held-out: 20 of 57, 35%; development half: 27 of 59, 46%). It reads an explicit "overruled" in 15 of 53 (28%) held-out pairs.
- **A flag is a pointer, not a finding.** When it raises a clean adverse reading on a pair the reporter did not mark adverse, about **half** are real treatment of the case when read by hand (held-out: 19 of 40 clean readings, 5 of 30 "possible" ones). Every flag carries the sentence, so reading it takes seconds, but someone must read it.
- **Recent text (2017 to 2023) is measured only on 21 adverse pairs from the reporters' case-law tables, and 2024 to 2026 not at all**, apart from 20 well-known cases (7 overruled or doubted, 13 good law) whose labels I assembled and have not had checked by a lawyer. Those 20 all came out right, but I looked at them while fixing rules, so that result is optimistic.

## What the gold standard is

About 5,000 of the court-site judgments from roughly 1950 to 1985 print, in their header, the reporter's list of later cases that cite them, each with a code (followed, distinguished, overruled and so on). For each entry whose citing case is in our collection (16,449 resolved pairs; 116 are coded overruled, held overruled or not followed), the checker reads that one citing judgment and we compare its reading with the code.

Weaknesses of this gold standard, which matter:

- The code is the reporter's own judgement of the citing case; it can mark a whole judgment "overruled" for a partial or different point.
- It covers only old reporter-style text. Modern judgments are written differently, so these numbers may be better or worse on them. We do not know which.
- A hit means the checker read an adverse treatment in the citing judgment, not that it read the same sentence the reporter had in mind.
- Only 116 adverse pairs exist, so the figures move by several points with a handful of cases.

## How it was measured

The pairs were split by the target case's crawl number: even numbers are the **development half** (rules were tuned on it), odd numbers the **held-out half** (run once).

Order of events, so nobody has to guess:

1. Rules were written and repeatedly corrected using errors found on the development half, including three rounds of reading the checker's own adverse readings by hand.
2. Rules were frozen at commit `bb77a5e`. The held-out half was then run once.
3. I hand-scored all 70 adverse readings it produced on pairs the reporter did not mark adverse.
4. Seven simple bugs showed up in that scoring (for example "neither overruled nor", "cannot be said that ... overruled", the Attorney General's submissions read as the Court's words). I fixed them in a later commit and added tests. **Those fixes are not measured on the held-out half**, which is no longer a clean test for them.

## Results

Readings count only the court's own voice or the law report's headnote (not counsel, not a lower court).

| | Development (even, tuned) | Held-out (odd, run once) |
|---|---|---|
| Reporter-coded adverse pairs (overruled, held overruled, not followed) | 59 | 57 |
| Citing judgment names the case (mention found) | 56 (95%) | 52 (91%) |
| Read as overrules, disagrees or doubts | 27 (46%) | 20 (35%) |
| Read as an explicit overruling | 21 of 56 (38%) | 15 of 53 (28%) |
| Other pairs (the reporter saw no overruling) | 8,065 | 8,268 |
| Of those, read as adverse | 37 (0.5%) | 70 (0.8%) |
| of which clean (cue clearly about the case, not hedged) | 23 | 40 |
| of which possible (hedged, or another case may be what the cue is about) | 14 | 30 |

Where the held-out misses went (37 pairs): 18 the citing judgment names the case but no cue is in the same sentence (the overruling is stated elsewhere, or the reporter's code reflects something subtler); 5 the case is not found in the citing text; 4 only in counsel's or a lower court's voice; 10 read as distinguishes, limits, follows or legislative.

### Reading the flags by hand (the real precision)

I read every adverse reading on pairs the reporter did not mark adverse. "Real" means the sentence, in the Court's or headnote's voice, adversely treats the case it names.

| | Real | Wrong | Cannot tell |
|---|---|---|---|
| Held-out, all 70 | 24 | 41 | 5 |
| of which clean (40) | 19 | 18 | 3 |
| of which possible (30) | 5 | 23 | 2 |
| Development, 49 read before the second and third rounds of fixes | 20 | 24 | 5 |

The development figure was taken before fixes made in response to it, so it is out of date; the held-out figure is the honest one for commit `bb77a5e`.

The wrong readings fall into a short list of causes: a negation the rules missed ("neither overruled nor", "cannot be said that"), the case being the authority a decision ignored or conflicted with rather than the case judged, a prayer or contention rather than the Court's view, a headnote list where the cue belongs to the neighbouring case, and a hypothetical ("if it were overruled"). The first four are fixed after the held-out run. The rest remain.

### The 20 known cases

`goodlaw/targets/known.json`: 7 cases known to be overruled, doubted or legislatively overcome (Koushal, Sowmithri Vishnu, ADM Jabalpur, Prabha Shankar Dubey, Gopalan, Rajesh Sharma, Dashrath Rupsingh Rathod) and 13 well-settled ones (Maneka Gandhi, Bhajan Lal, Puttaswamy, Navtej Johar and others). Result at the latest commit: all 7 flagged (5 as `ADVERSE_SIGNAL`, 2 as `QUESTIONED`); none of the 13 raised `ADVERSE_SIGNAL`, and all 13 came out `NO_ADVERSE_FOUND`.

Read this with care. **I assembled these labels myself from general knowledge and they have not been checked by a lawyer.** I also used the list to find and fix bugs (a Dashrath signal that a weak-signal policy hid, 40 repeated "has not been followed" directions that made Arnesh Kumar look doubtful, a case-law table that made Maneka Gandhi look overruled), so it is not an independent test.


## Recent judgments (2017 to 2023): the second answer key

The old reporters' citator stops at about 1985, so on its own it says nothing about modern text. From about 2017 the Supreme Court Reports print a "Case Law Reference" table in each judgment's headnote: every earlier case cited, what the court did with it ("overruled", "followed", "referred to", "distinguished" and so on) and the paragraph. `goodlaw/modern_gold.py` reads those tables.

- 3,944 judgments carry a table; they hold 25,628 rows; 15,669 rows name a case we hold (the rest name cases we lack, High Court cases, or use a citation form we cannot read).
- Only **49 of those rows are adverse** (21 on the tuning half, 28 on the untouched half). That is a small test: one case moves a percentage by about 5 points.
- The table sits in the headnote, so the checker is tested on **the court's own judgment only** (headnote mentions are dropped). A full citation printed in the headnote still raises the confidence of a short-name mention in the body, as it does in the real checker.
- The pairs are split by a stable hash of the citing judgment. The untouched half has **not been run**.
- 2024 to 2026 judgments carry no such table, so nothing here covers them.

| Tuning half, 2017 to 2023 | Before any fix for modern text | After the first round of fixes |
|---|---|---|
| Adverse pairs read as overrules, disagrees or doubts | 9 of 21 (43%) | 12 of 21 (57%) |
| Read as an explicit overruling | 7 of 21 | 9 of 21 |
| Other pairs read as adverse | 114 of 8,290 (1.4%) | 113 of 8,290 (1.4%) |
| of which clean | 91 | 85 |

I hand-scored 60 of the 122 adverse readings on other pairs after the first round: 20 real, 24 wrong, 16 I could not tell (a sentence about two cases where the table does not say which is the target). Roughly a third to a half are real, about the same as on old text. The wrong ones were: a case named as the place where another case was overruled ("In T, the decision of Y has been overruled"), "per incuriam" as a topic, a negation the rules missed ("nothing ... which can be said to be per incuriam"), a High Court that did not follow a binding decision, a conditional ("In case this Court does not agree") and counsel's stand ("The reliance of Mr. Rao"). Fixes for those were made after the scoring and are tested only by unit tests and by the tuning half, so they are not yet measured on fresh data.

What the misses showed (all measured on the tuning half):

- Several misses were an artefact of the test, not the checker: the per-pair test cannot learn a case's other printed citations (for example the SCC citation under which a judgment actually cites it), which the full pipeline does. `evaluate.production_rows` runs the full pipeline for the adverse pairs; its numbers are the ones to quote (12 of 21, as above).
- Modern drafting says "X (supra)" or "X, which held that ..., does not lay down the correct law" far more often than old text; two wording fixes came from that.
- A case cited only by a footnote marker ("Jasmine Kaur2") is found only if the footnote's citation is known; this is why the citation-learning step matters more here.
- Of the 12 adverse pairs missed at the start, about 4 were overrulings stated away from the case's name, or that I could not locate in the judgment; 3 were cases not found in the body at all; the rest were wording problems (fixed). Step 2 of the improvement plan (reading the paragraph) targets the first group; with so few cases that is a rough count, not a rate.

### Step 2 of the improvement plan: reading past the sentence that names the case

I predicted that reading the surrounding paragraph would recover a third of the misses (roughly 8 to 10 points of recall). **That estimate was wrong.** Looking at where the missed overrulings actually sit (tuning halves only): of 32 old-text misses, 15 had no recognisable adverse wording within six sentences after any mention, 10 had the cue in the same sentence but misread, 4 had it in a later sentence and 3 had no mention found; of 9 modern misses, 1 was a later-sentence case. Cross-sentence reading is worth about one pair in ten of the misses, not a third.

What step 2 did instead, on the evidence of those misses: the mention of a case printed with its citation now begins at the case's name (a name followed by a comma and a separate citation had been read as two cases); "T, [cite], over-ruled in [cite]" is read as T having been overruled; "neither overruled nor ..." is read as passive; "be that as it may" is no longer a hedge; "the view which has been adopted in the above decision in T" is attached to T; two new cue wordings; a case number left on the front of a title is dropped; and the sentence after a mention is read as about the case when it opens with a concluding marker ("Thus, the decision is required to be overruled"). A first, looser version of the last rule added six flags and none was right, so it was tightened.

| Tuning halves | Before step 2 | After step 2 |
|---|---|---|
| Modern: adverse pairs read as adverse | 12 of 21 | 15 of 21 (71%) |
| Modern: explicit overruling | 9 of 21 | 10 of 21 |
| Modern: other pairs flagged adverse | 113 of 8,290 | 115 of 8,290 |
| Old: adverse pairs read as adverse | 27 of 59 | 28 of 59 (47%) |
| Old: other pairs flagged adverse | 38 of 8,065 | 41 of 8,065 |

**These gains are in-sample.** The fixes came from reading these very pairs, so on fresh cases expect less. The new flags are in the "possible" tier except one real one. The known cases are unchanged (7 of 7 and 13 of 13). The full-pipeline run of the old-text adverse pairs gives 28 of 59, the same as the fast reader, so the fast reader is not hiding recall on old text. Neither untouched half has been run.

### Step 3 of the improvement plan: the reporters' case-law tables as evidence

A report now lists, for the judgments of 2017 to 2023 that print the table, what the Supreme Court Reports marked for the case under review ("overruled", "relied on", "referred to" and so on), quoted word for word from the headnote (`goodlaw/tables.py`). It is labelled as the reporter's annotation, not the court's words. A row marking the case **overruled** counts like the headnote's "overruled": a clean adverse signal if the citing bench is at least as large as the case's, otherwise a possibility; **disapproved or not followed** is strong only from a larger bench, otherwise a possibility. The other rows are counted and the most recent "relied on" ones listed. Judgments of 2024 on print no table, so this evidence stops at 2023.

What was measured (tuning half only, so the untouched half still has not been run):

- All 22 reporter-marked adverse pairs on the tuning half now reach the target's report; 20 of the 21 targets come out `ADVERSE_SIGNAL` and one `QUESTIONED`. Three of the 22 reach the report **only** through the table. This says the report picks up what the reporter marked; it is a coverage check, not an accuracy figure, because the table is the answer key.
- The 13 well-settled known cases carry 3 to 51 table rows each and none of those rows marks the case overruled, so the table adds no false alarm there. The 7 overruled cases are unchanged (all flagged).
- Priority case **Meters and Instruments v. Kanchan Mehta (2017)** changed from `NO_ADVERSE_FOUND` to `ADVERSE_SIGNAL`: a five-judge bench in 2021 says the judgment "in so far as it conferred power on the Trial Court to discharge an accused is not good law". That is a real partial overruling the first run missed. It was found by the text reading (after the fixes of steps 1 and 2 and the citation fix below), and the reporter's table marks it "overruled" too.

A finding that came with this step: `cites.py` did not recognise the early reports' "[1953] S.C.R. 476" (a bracketed year with no volume), so those citations were invisible in headnotes and tables. Fixing it, and mending the scanner's damage to table citations ("[1993) 2 SCR 581", "(1994) 4 sec 260"), raised the usable table rows from 15,669 to 16,608 and the citations that give no key from 3,413 to 1,569 of 25,628 rows. On the old-text tuning half it brought 9 more adverse flags on other pairs, about six of them genuine (headnote entries such as "[1954] S.C.R. 817, not followed"), and it turned one reporter-marked "not followed" pair from missed to caught. After the step: old text 29 of 59 adverse pairs read as adverse; modern 16 of 22 (the key now has 22 adverse pairs on the tuning half).

Limits: the table is only as good as the reporters' annotation (not checked by a lawyer); a case is matched to a row by its printed citation, so a case whose citations we do not know in the form the table uses is missed; and the key grew by pairs that the rules were never tuned on, so the one new adverse pair is a small fresh check, not a measurement.

Reproduce: `python sci_goodlaw.py eval --corpus corpus.sqlite --half dev --gold modern` (add `--production` for the full-pipeline run of the adverse pairs).

## What this means for use

- Use `ADVERSE_SIGNAL` and `QUESTIONED` as "read this sentence first". About half the clean flags are real; the report prints the quote and says why a reading is weak.
- Do not read `NO_ADVERSE_FOUND` as "good law". On this evidence it can sit alongside an overruling the rules did not see, and the collection itself is missing roughly 40% of 1968 to 1999 and a quarter of 2018 to 2025 (see the coverage block in every report).
- The triage is per case, across all its citing judgments, so it catches more than the per-pair figures above suggest. That is **not measured**.

## What would make the measurement better

1. A lawyer-checked sample of 100 to 200 cases, half of them recent. This is the one thing that would turn "pattern rules" into something that can be called validated.
2. Indian Kanoon's "cited by" annotations for a few dozen cases (this needs the person with access; the checker does not fetch from Indian Kanoon).
3. Re-running this on a fresh held-out half once more rules are added, drawn from cases the rules have never seen.

## Reproduce

```
python sci_goodlaw.py build --corpus corpus.sqlite        # about 15 minutes
python sci_goodlaw.py eval --corpus corpus.sqlite --half dev          # about 3 minutes; the held-out half needs --confirm-held-out
python sci_goodlaw.py known --corpus corpus.sqlite                  # the 20 known cases
```

The agreement tables come from `goodlaw/evaluate.py` (`gold_pairs`, `split`, `run`, `summarise`) and the known cases from `evaluate.known_cases`. Results will differ slightly if the corpus is rebuilt with newer bucket data.
