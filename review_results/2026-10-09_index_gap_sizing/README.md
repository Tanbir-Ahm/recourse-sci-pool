# How many correcting judgments are missing from the index? (sizing, 2026-10-09; PRIVATE)

`size_overruling_gaps.py` takes the 1,765 rows of the Overruled Register, finds each side (the ruling that was overruled, the ruling that overruled it) in the collection by citation key **and** by name, and asks: is the overruled ruling held by the main index (`claude/sci-index` `3c80a26`) while the ruling that corrects it is not? No search, no spend.

## Result (the version committed here)

- 1,765 rows; the overruled ruling is held by the index (itself or an identical or near-identical copy) in **86** of them (536 of the 1,765 are in the collection at all).
- In **23** of those the correcting ruling is **not** held:
  - **17 judgments** (for 17 rows) are in the collection but were left out by the index's criminal-law filter (cue-word density under 10 per 10,000 characters, no criminal heading): about 3.5 million characters, 0.9 million tokens, **about $0.11** to embed. They are the side index built the same day (`review_data/side_index/2026-10-09_correcting_judgments/`; list: `supplement_docs.json`).
  - **6 rows** whose correcting judgment I did not find by name: Shanmugam @ Kulandaivelu v. State of T.N. (2003), Birendra K. Singh v. State of Bihar (2000), Aslam Babalal Desai v. State of Maharashtra (1992), Kartar Singh v. State of Punjab (the TADA judgment, 1994), Kondiba Dagadu Kadam v. Savitribai Sopan Gujar (1999) look **absent from the collection** (a second search of the texts by year found no candidate) [Likely]; Anand Commercial Agencies v. Commercial Tax Officer (1998) is in the collection under a misspelt title (c13694, "COMMERICAL", 1997; a tax case, about $0.006; not added in this build).
- These figures are approximate: a register name with a typo, a corpus title that lost a word and a citation key shared by two cases each move a row in or out by hand. Two such cases were put in as documented aliases (Vinubhai Haribhai Malaviya, held as "HARIBHAI MALAVIYA"; "P. Prabhakaran" for K. Prabhakaran v. P. Jayarajan). The pairs listed in `overruling_gaps.json` can be read one by one.

## The first version was wrong, and why

The first run (20 judgments, $0.118, 22 pairs) treated a shared citation key as proof of the same decision. The register drops the "Supp" mark of an SCR citation, so "(1992) 1 SCR 545 Supp" (Aslam Babalal Desai) matched the ordinary SCR page 545 of 1992 (Dagi Ram Pindi Lal v. Trilok Chand Jain), and the same happened for Kartar Singh (T.M. Balakrishna Mudaliar), Antulay (Prabhakaran Nair) and others; it also took later orders of the same name (Common Cause 2001, Mukund Dewangan 2016) for the decision. The committed version requires the names to agree as well and prefers the register's own year. `overruling_gaps.json` keeps, under `earlier_loose_matching`, the same run with the loose rule (a shared key is enough; 25 pairs, 24 judgments, $0.121) for comparison; the first version's own figures were 22 pairs, 20 judgments, $0.118 (they are in the commit history). Nothing was embedded from the first version.

## Why it matters

The index cannot say "this ruling has been replaced" unless the replacing ruling is in it, or the register marks the old one. Five of the correcting judgments the register knows are not in the collection at all (the crawl's catalogue has holes: FOLLOW_UPS item 2 counts about 5,968 missing judgments). They would have to be fetched from another source (Indian Kanoon, the court's site), which this working environment cannot reach.
