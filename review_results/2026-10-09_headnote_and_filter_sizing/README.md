# Two sizings: law-report headnotes, and what the criminal-law filter drops (2026-10-09; PRIVATE: one table uses the key)

`size_headnotes_and_filter.py` (output `sizing.json`). Read-only; no search; no spend. Nothing was embedded.

## 1. Headnotes as extra passages: cheap, but probably not what the four misses need

- The main index holds **2,403 judgments that came from the court's law-report files (2017 onwards, plus some older ones)**; **2,247** of them have front matter that the index cut off before making passages: catchwords, "Issue for Consideration", "Held". Median 6,000 characters, 90% under 13,700.
- To embed it as extra passages: **about $0.20** if only the first 3,000 characters of each are used, $0.26 at 4,000, $0.35 at 6,000, **$0.53 for all of it** (17.2 million characters). Judgments before 2017 (the crawl) have no such front matter.
- **Does it fit the misses?** Of the 14 answerable tuning questions, 11 have a key authority with a headnote. Of the 4 where version A had no key authority in its top 10 (R09, R14, R20, R22), **only R20 does**; R09's (Bridgestone, 2015), R14's and R22's are crawl judgments. A headnote cannot help those three. [Certain, from the table in `sizing.json`.]
- Together with the miss diagnosis (`../2026-10-09_real30_pool_dev/miss_diagnosis/`): R09 was a candidate that the re-ranker put 36th (the older cases the 2015 Act replaced ranked above it); R14 was rank 2,241 by meaning, so only a different kind of text could reach it; R22 was in the first 100 by meaning (rank 58) but outside the 60 candidates, and widening the pool would bring it only to about 10th; R20 was 11th. **So a wider pool and headnotes together would lift at most R20 into the top 5.** My earlier guess that these two cheap fixes might help the everyday and story questions is not supported by the four misses we can see. [Likely] Where headnotes could help is the ordering of questions that already find their case (ranks 2 to 5), which can only be judged with the marks.
- To test it later without touching the main index, the headnote passages would go into a second side index. Two things have to be added then: the loader currently refuses a side index whose documents already have passages in the main index (a headnote index would add passages to documents the main index holds), and a section weight for "headnote" must be chosen on the tuning half only. **Not started; no embedding before the marks are in** (the promise made when the way forward was agreed).

## 2. The criminal-law filter drops a lot of criminal-law judgments

The index keeps a judgment only if its opening block names a criminal proceeding or its cue-word density (accused, prosecution, IPC, CrPC, NDPS, FIR, offence, bail, conviction, acquittal and the like) is at least 10 per 10,000 characters. Below that line, in the whole collection:

| Density (per 10,000 characters) | Judgments left out | Cost to embed them all | Cumulative |
|---|---|---|---|
| 8 to 10 | 260 | $0.26 | 260 judgments, $0.26 |
| 6 to 8 | 299 | $0.29 | 559, $0.55 |
| 5 to 6 | 182 | $0.18 | 741, $0.73 |
| 4 to 5 | 210 | $0.22 | 951, $0.95 |
| 3 to 4 | 293 | $0.28 | 1,244, $1.23 |
| 2 to 3 | 473 | $0.52 | 1,717, $1.75 |
| 1 to 2 | 965 | $1.20 | 2,682, $2.94 |
| under 1 | 30,710 | about $29 | (civil, tax, service, land and the like) |

- **My reading of 14 random titles in each of the two top bands (`sizing.json`, `samples`; titles only, not marks, not a lawyer's reading):** from 6 to 10 the large majority look like criminal-law or criminal-procedure cases (for example Suresh Kumar Koushal v. Naz Foundation, the section 377 case, density 9.5; Laxman Naik v. State of Orissa; Bhalchandra v. State of Maharashtra; Republic of Italy v. Union of India, the marines case); from 3 to 6 it is mixed (Pawan Kumar Gupta v. State (NCT of Delhi), a Nirbhaya convict's pleas, next to service and company-law cases). [Likely]
- **It already cost us on the owner's questions:** of the 35 key authorities in the owner's file, 31 are in the index; **1 was dropped by this filter (Arjun Panditrao, density 3.4)**; for Q6 the file names the 23 August 2024 prisons order, which is not in the collection (the collection holds only the earlier order of 14 May 2024, which the filter also dropped, density 0.0, and which does not discuss section 479); and 2 are not in the collection (Shivangi Bansal; Bhagwan Rama Shinde Gosai). So the filter accounts for 1 of the 4 gaps outright, 2.9% of the key authorities, from one question set whose authorities were picked by a person who looked for well-known cases. [Certain for the count; the rate for other questions is a guess]
- **What this suggests for a new snapshot (a proposal for the owner; nothing has been built):** lower the line to 6 (559 more judgments, about $0.55) or to 3 (1,244 more, about $1.23), and add the correcting judgments the register links to rulings the index holds (the 17 already built, $0.10). Judging by cost alone, the 30-question budget would carry the first, and the second would use most of what remains above the $8 kept for the live site. A better rule than density alone may be "cited by criminal judgments the index holds" (a judgment that criminal courts keep citing is criminal-law material whatever its cue-word density), which the citation data in the corpus store can size at no cost. Not done.
- **Why not now:** any change to the main index must wait until the measurement round is over (the index is held at `3c80a26`); this is a proposal for the new snapshot.
