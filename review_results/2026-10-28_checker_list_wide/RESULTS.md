# The invented-case check: a wider list and a spelling-tolerant name match (2026-10-28)

Owner's go, 2026-10-28: "add the wide index's names, including the High Court ones, to the list, and make the name match tolerant of spelling variants. That would remove most of the gaps. This matters before enforce is considered."

Built (Recourse branch `register-hooks-and-overlay`, commit `5e17b82` and the one after it): `name_match.py`, `checker_list.py`, `checker_names.json.gz` (294 KB: names, courts and dates only, no judgment text), the wiring in `grounding_checks.py`, tests `test_name_match.py` and `test_checker_list.py`; in the research repo `sci_checker_names.py` (writes and verifies the names file) and `test_sci_checker_names.py`. **Switch `CHECKER_LIST=wide`; unset or `title` is the old behaviour byte for byte.** Nothing is on Recourse `main`; nothing is deployed; nothing was tried with the answer model. The measurements below are Claude's, on Claude's own test names (code made them from the index; no lawyer chose or read them). They do not measure how often an answer names an invented case, and they are not a hallucination rate.

## What the check does, and what changes
The check lets a case in an answer pass when the material the model was given holds it. For a case that is NOT in the material it asks "is there a judgment with these parties in a list we hold?" and the notice says either "real, but not among the sources we read" or "we could not find it". A wrong "not found" makes `enforce` mode withhold an answer that names a real case; a wrong "found" makes a made-up case read as real. The list is for the wording of that notice and for `enforce`; it never lets a case through that is in neither the material nor a list.

| | before (production) | with `CHECKER_LIST=wide` |
|---|---|---|
| Supreme Court title list (38,026 titles, to 12 Dec 2025) | read word for word | read with spelling tolerance |
| judgments of the wide index d8811a9 | not consulted | all named ones: 11,588 Supreme Court + 7,484 Gauhati High Court names (the index holds 19,255 judgments; 108 have no name in the names table; 75 rows repeat another's name, court and date) |
| the 68 reviewed library cases | only those in the title list (50) | all 68 |
| other High Courts, Supreme Court judgments in neither list | not found | **still not found** |

## The name match (`name_match.py`)
Two names read as the same parties when: honorifics ("Shri", "M/s"), "& Ors", "(Dead) by LRs", "through ...", "(with connected appeals)" are set aside; U.P./Uttar Pradesh, Govt./Government, Ltd./Limited and a few more are written one way; a bracket is read both ways ("State (NCT of Delhi)"); a party that lists several names (commas, "and", "@") matches on any one name that can stand alone; the letters agree after spacing and punctuation are ignored, or differ by the slips a scanner makes (a missing or extra letter, I/L/J, O/0, C/E, U/V, two letters swapped): none allowed under 14 letters, one up to 23, two up to 33, and an unrelated letter costs two, so "Rakesh" is not "Ramesh", "Sushil Kumar" is not "Sushila Kumar"; initials must agree when both names have them; the first parties must match and the second parties must not contradict (they must share a word that tells them apart, not "Singh" or "Mohd" alone; "State of Bihar" is not "State of Punjab"; a short one-word first party such as "Sanjay" needs its second party shown to match, not merely not contradicted); the two parties may be given the other way round. A party that is only one or two initials ("X", "Ms. P") matches nothing: 20 of the 19,147 named index judgments are anonymised that way.

## Measured (`measure_checker_list.py`; written and committed before any run; seeds 28 and 30; `final_seed28.json`, `final_seed30_clean.json`)
**Process, said plainly:** the first run (`run1_first_version_before_rework.json`, seed 28) showed that my first matcher was too loose (one-letter twins 20%, swapped-party fakes 8.4%) and had bugs (an initial "V." read as the versus marker, the initial V thrown away, "State rep. by the Inspector of Police" matching any State, a very common surname pushing the real entry out of the candidate list). I reworked it. Seed 28 was then re-run on the final code (it is no longer a hold-out: the rework was made after seeing it). **Seed 30 was generated and run only on the final code.** Numbers below are seed 30; seed 28 differs by under a point except where stated.

**1. Names the old match misses but are in the Supreme Court title list.** Of 11,619 named Supreme Court judgments of the wide index, the old match finds 7,982 and misses 3,637. The tolerant match finds 826 of those 3,637 in the title list: 485 with the same decision date as the index judgment (the same judgment), 26 within the same year, 48 where a date is missing, and 267 where the matching title is another year's (the same two parties in a different case, e.g. "State of U.P. v. Hari Ram" 1983 and 2013; a few are doubtful, e.g. "Gurnam Singh & Anr v. State of Punjab" matched through an alias of "Kala Singh @ Gurnam Singh"). The other 2,811 are not in the title list at all: the names file supplies them.

**2. Names a model might write for real cases (made by rule from real names that are in the title list):**

| variant | n | old match finds | tolerant match, title list only | the new check (wide) |
|---|---|---|---|---|
| "& Ors"/"Another" dropped | 1,053 | 1,053 | 1,046 | 1,051 |
| State or word abbreviated/expanded (U.P., Govt., Ltd.) | 305 | 138 | 305 | 305 |
| "Shri" added | 1,720 | 1 | 1,711 | 1,716 |
| parties the other way round | 2,000 | 102 | 1,969 | 1,998 |
| one letter lost (a scanner slip) | 1,207 | 2 | 581 | 582 |

(The shipped function is "old match OR new match", so it never finds less than the old one; the "wide" column is the new matcher alone and in the first row finds 2 names fewer than the old one: "Ms. P"-type names it cannot read.) A slip is forgiven only in long names (46 to 48% of the one-letter-lost names are found); in a short name it is not, on purpose.

**3. Names that are NOT real (3,000 each, made by code from the index; this is the risk side):**

| kind | old match accepts | new check accepts | of which a real pair written the other way round | the rest (same order as a real pair) |
|---|---|---|---|---|
| first party of one real case + second party of another | 135 (4.5%) | 153 (5.1%) | 18 | 135 (4.5%) |
| plausible: a given name and a surname from the corpus against a State or the Union | 45 (1.5%) | 59 (2.0%) | 24 | 35 (1.2%) |
| a real name with one unrelated letter changed (a misspelt real name) | 3 (0.1%) | 412 (13.7%) | 5 | 407 |

Read this carefully. The extra accepts in the first two rows are mostly real pairs written the other way round ("Babu Singh v. Union of India" for "Union of India v. Babu Singh"), which are the same case and are rightly found; the same-order rate is where the old match was (4.5% and 1.2% to 1.5%). Seed 28: 4.5% to 5.5% (130 same-order = 4.3%) and 1.3% to 1.9% (41 same-order = 1.4%). **A made-up name is accepted about 1 time in 20 when it is built from the first party of one real case and the second party of another, and about 1 in 50 when it is plausible but invented from common name parts; a name that happens to be a real pair (the court has many Rajesh Kumars and Rakesh Kumars against many States) cannot be told from a real case by any name test.** The third row is not a false-accept rate: a name one wrong letter away from a long real name is almost always a misspelling of that real case, and is accepted by design.

**4. Does every named judgment of the wide index find itself in the new list?** (`self_find.json`; a check of the matcher, since the names are in the list.) 19,124 of 19,147 (99.88%); 20 cannot be read (anonymised parties such as "X v. State of Kerala", "Ms. P"), 3 not found.

**5. The 68 library cases.** Old match 50; tolerant match on the title list alone 54; title list + wide index without adding the library's own names **57**; with the library's names 68 (circular). **The 11 still missing when the library's own names are left out: 10 are High Court judgments (Madras, Gujarat, Kerala, Delhi x3, Patna, Calcutta, Karnataka, Bombay) and 1 is a Supreme Court judgment that is in neither list (Youth Bar Association v. Union of India, AIR 2016 SC 4136).** So after this change the visible gap is other High Courts, plus a smaller, unmeasured number of Supreme Court judgments that neither list holds.

**6. Speed and memory.** Building the index takes about 1.2 s on first use per process (logged once as `CHECKER_LIST_READY {...}`), about 41 MB; a lookup takes about 6 ms on average, 26 ms at the 95th percentile, up to about 0.2 s. The check runs once per finished answer.

## What is still not covered, and what that means for `enforce`
- **Other High Courts (24 or more), and Supreme Court judgments in neither list: no list at all.** In the library, 10 of 68 cases are such High Court judgments. With `enforce`, an answer that names one of them from the model's memory is withheld after the second try as "not found", although the case is real. This is the biggest remaining reason to keep `enforce` off.
- **A made-up name that happens to be a real pair passes as real** (about 1 in 20 to 1 in 50 for names built as above).
- The 108 unnamed index judgments and anonymised parties cannot be looked up by name.
- The names file must be rebuilt when the index changes (`python3 sci_checker_names.py export ... ; verify ...`); it records the index commit it was built from; nothing refuses to run on a stale file.
- Nothing here says that a case is the one meant, decides what it says, or says it is good law. No lawyer has read the matches. No hallucination rate has been measured for answers.

## Files
`measure_checker_list.py` (sets S0 to S3; reads only), `self_find.py`, `final_seed28.json`, `final_seed30_clean.json`, `run1_first_version_before_rework.json`, `self_find.json`.
