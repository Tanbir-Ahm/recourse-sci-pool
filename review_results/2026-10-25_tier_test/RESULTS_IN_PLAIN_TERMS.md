# Separate-tier test: results in plain terms (2026-10-25)

Index `claude/sci-index` head `d8811a9`: 418,286 passages (Supreme Court 261,572; Guwahati 156,714 = 37%). Rules: `PLAN_AND_RULES.md`, committed as `7cd0d77` before any paid call. Code: `tier_test.py` (it imports the experiments' own search code, `review_tools/pool_runner.py`, unchanged). Nothing was written to the index and nothing is connected to the site.

## Verdict: PASS by the rules written beforehand, but the gain is modest [Certain that the four rules hold as written]

- Showing Supreme Court and Guwahati judgments as **two labelled lists** made the Supreme Court list better on the test questions: the key case in the top five for **8 of 14** questions (6 with one mixed list), first place 5 of 14 (2), landmark passes 2 of 12 (1).
- It does **not** undo what the growth of the library did. On the old index (236,155 passages, before the newer archive and Guwahati were added) the same search put the key case in the top five for 9 of 14 (recorded then: 10); on the still older 2 October index (156,235 passages) 4 of 12 landmark questions passed. The two-list design gets back 2 of the 3 key-case top-five places lost (9, then 6 with one mixed list, now 8) and only 1 of the 3 landmark passes lost (4, then 1, now 2). [Certain]
- The Guwahati list shows something for **23 of 26** questions. By my reading of every shown passage, **53 of 65 are on point, 8 related, 4 off the subject**. My reading is not a lawyer's. [Certain for the counts]
- Cost of the whole test: **$0.0805**. In use, the second list costs one more re-ranker call per search, about **$0.0009**. [Certain]
- The samples are tiny (12 and 14 questions). A difference of one question is noise; only the key-case change (6 to 8 of 14) is bigger than that. [Certain]

## The four rules, as written before the test

| Rule | What it asked | What happened | Holds? |
|---|---|---|---|
| R1 no harm | Supreme Court list no worse than the mixed list on key case in top 5, and on landmark in top 5 cases | key case 8 vs 6 of 14; landmark in top 5 cases 3 vs 2 of 12 | yes |
| R2 benefit | better by at least 1 on landmark passes, landmark in top 5, or key case in top 5 | +1, +1, +2 | yes (only the +2 is beyond noise) |
| R3 Guwahati list worth showing | something shown for at least half of the 26 questions, and at least half of the shown judgments on point or related | 23 of 26; 61 of 65 (94%) | yes |
| R4 cost | at most one extra re-ranker call per search | 3 calls per question (mixed, Supreme Court pool, Guwahati pool) = one more than the mixed list alone | yes |

`python3 -I summarise_ratings.py` re-checks all of this from the saved files, for free.

## The Supreme Court list: the numbers [Certain]

14 tuning questions (the half of the owner's 30 used while building the search; the sealed half was not touched). Counts of questions where the key case is first / in the top 5 / in the top 10 (passages counted, as `real30_score.py` does):

| Search | First | Top 5 | Top 10 |
|---|---|---|---|
| Old index, same code, reproduced today (recorded then: 5 / 10 / 10) | 5 | 9 | 10 |
| **One mixed list today** | **2** | **6** | **9** |
| Split after mixing (same 60 candidates, Supreme Court passages only) | 5 | 8 | 9 |
| **Separate pools (own search over the Supreme Court passages only)** | **5** | **8** | **9** |
| Mixed, Guwahati scores times 0.8 | 5 | 8 | 9 |

12 landmark questions (6 verified landmarks, one plain and one legal question each; pass = the landmark among the top 5 cases and its verified paragraph among its own top 3 passages):

| Search | Passes | Landmark in top 5 cases | In top 10 | Not among the 60 candidates |
|---|---|---|---|---|
| 2 Oct, old crawl only | 4 | 6 | | |
| 22 Oct | 2 | 2 | | |
| 24 Oct, whole index | 1 | 1 | | 4 |
| **One mixed list (this run)** | **1** | **2** | 4 | 4 |
| Split after mixing | 2 | 4 | 4 | 4 |
| **Separate pools** | **2** | **3** | 4 | **1** |
| Mixed, Guwahati times 0.8 | 2 | 4 | 4 | 4 |

The mixed arm gave 1 (24 Oct) and 2 (today) landmarks in the top 5 cases on the same index: the re-ranker is not perfectly repeatable, which is the one-question noise the plan allowed for.

**Harness check (done first, as the plan required):** the mixed search on the old index (236,155 passages) reproduced the recorded results for 13 of 14 questions exactly; R12 came 6th instead of 5th, so top 5 reads 9 instead of 10. Within the one-question allowance. [Certain]

Per question (landmark: place of the landmark among cases, `*` = pass, `-` = not among the 60 candidates):

| Landmark / question | Mixed | Split after mixing | Separate pools |
|---|---|---|---|
| Arnesh Kumar, plain | 4 | 4 | 7 |
| Arnesh Kumar, legal | 6 | 5* | 5* |
| Md Ibrahim, plain | - | - | - |
| Md Ibrahim, legal | - | - | 25 |
| Nanda Gopalan, plain | 33 | 18 | 29 |
| Nanda Gopalan, legal | 14 | 14 | 13 |
| Rangappa, plain | - | - | 13 |
| Rangappa, legal | 1* | 1* | 1* |
| Jadeja, plain | 18 | 15 | 15 |
| Jadeja, legal | 6 | 4 | 5 |
| Noor Aga, plain | 27 | 16 | 27 |
| Noor Aga, legal | - | - | 17 |

| Tuning question | Old index | Mixed | Split after mixing | Separate pools |
|---|---|---|---|---|
| R01 | 1 | 1 | 1 | 1 |
| R02 | 1 | 4 | 1 | 1 |
| R04 | 2 | 2 | 2 | 2 |
| R08 | 2 | 8 | 3 | 2 |
| R09 | - | 52 | 36 | 47 |
| R11 | 3 | 6 | 3 | 3 |
| R12 | 6 | 24 | 12 | 28 |
| R14 | - | - | - | - |
| R17 | 1 | 2 | 1 | 1 |
| R19 | 1 | 2 | 1 | 1 |
| R20 | - | - | - | 13 |
| R22 | - | - | - | - |
| R24 | 1 | 1 | 1 | 1 |
| R26 | 4 | 6 | 6 | 7 |

## Why the Supreme Court list improves, and what it does not fix

- In today's mixed list **45 of the 130 top-five places** (35%) over the 26 questions go to Guwahati judgments (Guwahati is 37% of the passages). Taking them out gives the Supreme Court authorities their places back. [Certain for the counts]
- Down-weighting Guwahati to 0.8 gives the same headline numbers as the split. So the gain comes from Guwahati no longer taking Supreme Court slots, not from anything clever in the separate pool. [Likely]
- **Split after mixing and separate pools are indistinguishable on the headline numbers** (5 / 8 / 9 and 2 passes each). The separate pool brings the landmark into its 60 candidates more often (not found: 1 of 12 against 4), but it did not turn into more passes or more top-5 places, and it is worse on some questions (Arnesh Kumar, plain: 7th against 4th; R12: 28th against 12th). With 12 and 14 questions I cannot choose between them on quality. [Certain]
- **What is still missing against the old index:** R12 (6th then, 28th now) and R26 (4th then, 7th now). The Supreme Court-only list contains no Guwahati passage, so whatever pushed them down is other Supreme Court judgments, most likely the newer archive added since. [Likely] I did not isolate the cause further.
- The landmark problem is only half-fixed: even the best arm has the landmark in the top 5 cases for 3 or 4 of 12 questions, and Md Ibrahim is not among the candidates for the plain question in any arm (25th for the legal question, in the separate pools only).

## The Guwahati list: what it showed

Built as the site's own pilot tier does it: its own search over the Guwahati passages only, similarity bar 0.50 (the site's core bar is 0.40), at most 3 judgments, one passage per judgment.

- **Shown:** 20 questions got three judgments, 2 got two, 1 got one, **3 got none** (the plain Jadeja question, R01 and R26). 65 shown in all, 64 different judgments. [Certain]
- **My reading, passage by passage (the whole passage; I did not read the whole judgments):** on point 53, related 8, off the subject 4. Landmark questions in plain language: 11 of 14 on point, 3 related; landmark questions in legal language: 18 of 18 on point; the 14 tuning questions: 24 of 33 on point, 5 related, 4 off. The four off-subject judgments are on two questions: R04 (one, a bail appeal that is not about anticipatory bail) and R24 (three, ordinary warrants and bail conditions, none about the Enforcement Directorate). All four sit at similarity 0.51 to 0.52. [Certain for the counts; the ratings are my judgment]
- **Most of what it shows is Guwahati judgments quoting Supreme Court rules** (Arnesh Kumar, Gian Singh, Noor Aga, Rangappa, Vinod Natesan, Satender Kumar Antil, Kunal Rameshbhai Kalyani and so on). That is useful as local applications, and it is also why Guwahati judgments crowd the mixed list. [Likely]
- **Benches:** of the 64 judgments, 44 are Assam (Guwahati), 9 Arunachal Pradesh (Itanagar), 4 Nagaland (Kohima), 3 Mizoram (Aizawl), and 4 are pre-2018 court files with no bench code (one is from Shillong, before Meghalaya's own High Court). 61 of the 65 are from 2018 or later. [Certain; bench from the file path, checked against the state named in each title]

### Problems this test turned up (2, 3 and 4 cost nothing to fix; 1 has no tested fix; none is fixed)

(Entry numbers are the `n` column of `hc_tier_ratings.csv`.)

1. **A passage can be the wrong side's or a lower court's words, or only background facts.** The search picks the passage that best matches the question's words, not the place where the court decides. Entry 21 (a cheque appeal) shows the trial court's reasoning that the complainant must prove the debt, quoted inside the appeal; read alone it points the wrong way (I did not read the rest of that judgment, so I do not know whether the High Court agreed). Entry 49 is mostly the lawyers' arguments, entry 50 only the complainant's allegations, entries 2, 3 and 35 only background facts: **6 of the 65 shown passages (9%)**. Entry 45 (R12) is on point, but the court refused to quash: it goes against the asker. "On point" is not "helps the asker"; the passage cannot show the outcome. The Supreme Court list has the same risk (the sealed run of 10 Oct found a lower-court view later reversed in 3 of its 22 misleading top-five passages). **No tested fix exists**; an untested idea is to prefer passages where the court itself speaks. The site's wording has to stay "reported ... not yet confirmed by our reviewer", and nothing here says a case is good law.
2. **The same passage twice.** Two pairs are two different petitions with identical passage text, decided on the same day (probably together): R08 (entries 38 and 39, Crl.Rev.P. 218/2025 and 221/2025) and R09 (entries 41 and 42, Tr.P.(Crl.) 2/2026 and 1/2026). Two of the three places carry the same words, so the reader gets two different results, not three. The site's "one passage per case" rule does not catch it, because they are two cases. Fix: drop a result whose passage text is identical to one already shown (or show it once with "also decided in ..."). After that the counts are 51 on point, 8 related, 4 off of 63 (59 of 63 on point or related, 94%).
3. **Labels.** Entry 23 (a 2011 Shillong revision petition) is stored with the title "M/S KOJANI'S DHANKHETI THE HON'BLE MR JUSTICE T VAIPHEI Vs" (a judge's name, no second party) and a case-number field that holds "CRL.REVN 33(SH)/2009 SHRI JOSE PULLAN @ JOSEPH P VS SMTI UMA JASRASARIA ...". The passage and the court's link are fine; only the label is wrong. Likely cause [Likely; I have not opened that file's first page]: the old court files print judges, parties and case number in a jumbled order on the first page, and the reader of that page picked the wrong pieces. By a simple check, 22 of the 7,557 Guwahati judgments in the index have this fault, 21 of them among the 758 court files from before 2018 (2.8% of that set). The check only finds the obvious kind (a judge's name in the title, a case number that is too long or contains "VS"); milder slips pass it, for example entry 2 reads "THE STATE OF ASSAM RANJAN PATHAK", probably two respondents run together. So the true number is higher by an unknown amount. Fix: for the flagged ones rebuild the label from the case-number line, or show court, case number and date only.
4. **Bench names.** The Gauhati High Court sits for Assam, Nagaland, Mizoram and Arunachal Pradesh, and before March 2013 also for Meghalaya, Manipur and Tripura. Of the 64 judgments shown, 44 are from Assam (Guwahati), 9 from Arunachal Pradesh (Itanagar), 4 from Nagaland (Kohima), 3 from Mizoram (Aizawl), and 4 are older court files with no bench code. All are genuine Gauhati High Court judgments, so showing them is not wrong, but "Gauhati High Court" alone does not tell the reader which bench decided it, and about a quarter of the judgments with a bench code (16 of 60) are from outside Guwahati. Local practice can differ [Likely]. Fix: the bench is already in the stored file path for the 2018 and later judgments; for the older court files the ending of the case number (such as (K) or (SH)) probably names it [Likely]. Both are free and not done.

None of the four changes the verdict. Problem 1 is the only one without a ready fix.

### Post hoc, not part of the verdict: a higher bar

| Bar | Judgments shown | On point / related / off | Questions with something |
|---|---|---|---|
| **0.50 (tested)** | 65 | 53 / 8 / 4 | 23 of 26 |
| 0.52 | 50 | 43 / 5 / 2 | 21 |
| 0.53 | 46 | 41 / 5 / 0 | 19 |
| 0.55 | 38 | 34 / 4 / 0 | 17 |
| 0.60 | 15 | 15 / 0 / 0 | 7 |

A bar of 0.53 would remove all four off-subject judgments, at the price of 12 on-point judgments and 4 questions' worth of results. I looked at this after reading the same data, so it is a hint, not a result, and the bar stays at 0.50 until a fresh set of questions can test it. [Guessing that 0.53 would hold up]

## What this test cannot tell you

- **Small samples.** 12 and 14 questions. The landmark changes (+1 pass) are inside the one-question noise; the key-case change (+2) is the only one beyond it. No significance test is claimed.
- **It measures where the known answer ranks and whether a Guwahati list looks relevant to me.** It does not measure whether a person with a real problem is better served, and it is not a lawyer's reading. The tuning questions were used when the search was built; the sealed half is used up.
- **Not checked:** whether any shown Guwahati judgment was appealed or reversed; what the 3 empty questions would show at a lower bar; the effect on speed and memory (the second list needs a second re-rank and a second retrieval, which I did not time separately; the whole test ran in 189 seconds including cold caches).
- **Not tested:** the split after mixing for the Guwahati list (only the separate-pool version of that list was read); a recent-versus-older Supreme Court split; a "cited by" boost; folding judgments that only quote a landmark into the landmark; a bar below 0.50.

## What I recommend [Likely]

1. **Use the two-list design when the site is connected, built as separate pools:** the main list from a search over the Supreme Court passages, a second labelled list from a search over the Guwahati passages (bar 0.50, three judgments at most, one passage each). It is the site's own pilot-tier pattern, passes the rules written beforehand, and costs about $0.0009 more per search. If a search finds no Guwahati passage at 0.50 the second re-ranker call can be skipped (3 of 26 questions here), which I did not test. Split after mixing is free and scored the same, so it is a fair alternative if the extra call is not wanted, but then the Guwahati list would have to come from the mixed 60 candidates, which I did not test.
2. **Before it is shown:** collapse identical passages, clean the 22 labels, name the bench, keep the "reported ... not yet confirmed by our reviewer" wording.
3. **Follow the owner's staged order:** shadow mode first (compute both lists, show the old one), then judge on new questions written by someone who has not seen ours, with lawyers' marks.
4. **Do not expect this to close the landmark gap.** The next ideas to test (each costs cents) are a "cited by" boost, a recent-versus-older Supreme Court split, and folding quoting judgments into the landmark. That is the owner's call.

## Steps done (nothing left out)

1. Plan and pass/fail rules committed before any paid call (`7cd0d77`). 2. Harness check on the old index (13 of 14 identical). 3. All arms on 12 landmark and 14 tuning questions. 4. Guwahati list built and all 65 shown passages read in full (the passage, not the whole judgment). 5. Rules applied: PASS. 6. Cost recorded: validation $0.0138 (14 query embeddings, 14 re-ranks, 273,621 tokens) plus full run $0.0667 (26 embeddings, 78 re-ranks, 1,330,484 tokens) = **$0.0805**, against the $0.30 cap; none of it is index embedding, so the 110.7M ceiling is untouched. 7. Results, code, readings and ratings saved here. 8. `FOLLOW_UPS.md` item 1p updated.

## Files

`tier_test.py` (run), `tier_full.json` and `tier_validate.json` (numbers), `hc_tier_readings.json` (the shown passages; question text kept only for the 12 public landmark questions), `hc_tier_ratings.csv` (my rating and a one-line reason for every shown judgment, with the court's link), `summarise_ratings.py` (re-checks the rules), `PLAN_AND_RULES.md`.
