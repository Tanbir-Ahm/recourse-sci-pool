# How good is the checker? (measured, with its limits)

Everything here is labelled by source: **pattern-rule reading of Supreme Court texts, not lawyer-validated.** The numbers describe how well the rules read the *treatment* of a case in later judgments. They do not measure whether a case is good law.

## The short version

- **A clean `NO_ADVERSE_FOUND` is weak evidence.** Against the law reporters' own citator codes (below), the checker finds an overruling or disagreement in about **one pair in three** it should (held-out: 20 of 57, 35%; development half: 27 of 59, 46%). It reads an explicit "overruled" in 15 of 53 (28%) held-out pairs.
- **A flag is a pointer, not a finding.** When it raises a clean adverse reading on a pair the reporter did not mark adverse, about **half** are real treatment of the case when read by hand (held-out: 19 of 40 clean readings, 5 of 30 "possible" ones). Every flag carries the sentence, so reading it takes seconds, but someone must read it.
- **Not measured at all on 2018 to 2026 text** except for 20 well-known cases (7 overruled or doubted, 13 good law) whose labels I assembled and have not had checked by a lawyer. Those 20 all came out right, but I looked at them while fixing rules, so that result is optimistic.

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
