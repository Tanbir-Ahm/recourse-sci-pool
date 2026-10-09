# Tuning half of the 30, searched again over "main index + side index", 2026-10-09 (PRIVATE)

Never send this folder to reviewers: `pool.json` names which search version found each passage, and `AUTHORITY_HITS.md` / `ARM_COMPARISON.md` use the private key.
This is an **exploratory extra arm on the tuning half only**. The measurement round (marks by J and S, the lights, the sealed run) is on the main index alone; nothing here changes it.

## What was added, and what was not touched

- **Main index:** `claude/sci-index` commit `3c80a26`, untouched (10,503 judgments with passages, 236,155 passages).
- **Side index:** `review_data/side_index/2026-10-09_correcting_judgments/` (6 MB, committed; built by `review_tools/build_supplement.py`; manifest `SUPPLEMENT.json`, manifest sha256 `28255c5d...c20d`): **17 judgments, 2,572 passages**, embedded with `voyage-law-2`, 818,253 tokens, **$0.098**. They are the judgments that the Overruled Register links to a ruling the main index holds and that the main index left out as "not criminal law" (cue-word density under 10 per 10,000 characters, no criminal heading). Each was checked by name as well as by citation key, and its text was checked to hash to the main index's own record of it. They keep the document ids the main index gave them. The list, with the register rows behind each, is `review_results/2026-10-09_index_gap_sizing/supplement_docs.json`.
- **The 17:** Puttaswamy (2017), A.R. Antulay (1988), Tulsiram Patel (1985), Samsher Singh (1974), **Arjun Panditrao Khotkar (2020)**, Bajaj Allianz v. Rambha Devi (2024), Common Cause (1999), Radhy Shyam (2011), Mukund Dewangan (2017), Vidyacharan Shukla (1963), Baliram Waman Hiray v. Lentin (1988), Cadila Healthcare (2001), State of U.P. v. Singhara Singh (1963), two Commissioner of Customs v. Indian Oil orders (2004), Gaurav Jain and Supreme Court Bar Association (1998), Rohtas Bhankhar v. Union of India (2014). Only Arjun Panditrao is the key authority of any of the 30 questions (R21).
- **Not added, and why:** the 23 Aug 2024 prisons order (R06) and Shivangi Bansal (R15) are not in the collection and the working environment cannot reach the court's site or Indian Kanoon (the gateway answers 403 to the connection); the 14 May 2024 order in the collection does not discuss section 479. The two Q28 control authorities (Amardeep Singh, Shilpa Sailesh) are deliberately left out so that the control stays a control.

## How it was run

`python review_tools/pool_runner.py --half dev --max-rerank-tokens 2500000 --supplement review_data/side_index/2026-10-09_correcting_judgments --out review_results/2026-10-09_real30_pool_dev_plus_side_index`
(same questions, same blind rewrites, same versions A, B, E, C, F, S as the main-index pool; the runner records the side index in `pool.json` under `run.side_index`). Spent: **1,809,425 re-rank tokens and 3,258 embedding tokens, about $0.091** (the main-index pool: 1,812,788). Together with the side index's $0.098 the arm cost about $0.19 of the $9.88 balance.
Scored with `real30_score.py --overlay key_overlay.json` (the overlay gives R21 its key document, Arjun Panditrao, which only the side index holds; the key file is not changed) and compared with `real30_compare_arms.py`.

## Result (authority-hit test; no reviewer mark; 19 tuning questions)

| | Main index | Main + side index |
|---|---|---|
| Answerable questions with the key authority in the top 5, versions A / B / E / S | 10 / 10 / 9 / 6 of 14 | 10 / 10 / 9 / 6 of 14 (the same) |
| R21 (CCTV footage, s.63 BSA / 65B certificate): key authority (Arjun Panditrao, 2020) | not in the library | **rank 2** in A, B and S, **rank 3** in E |
| R21: the overruled ruling (Shafhi Mohammad, 2018) | rank 1 in A and B | still rank 1 in A and B (rank 4 in S) |
| Question-version lists identical to the main-index lists (top 5; all that S showed) | | 88 of 100; the 12 that differ: 4 are R21 (the intended change), 8 are small reshuffles |
| Side-index judgments that reached any top 10 | | only Arjun Panditrao, and only for R21 (4 of its paragraphs in A's top 10) |
| Old rulings that count as stale in the top 5 (all questions) | A 4, B 4, E 6, S 4 | the same |

- **The library fix does what it should for R21:** the court's current ruling is now found, at rank 2, next to the old one. It does **not** remove the old ruling from first place: only the register badge on Shafhi Mohammad (it is in the register as a candidate-tier row) or a demotion can do that. That is the point of keeping the two parts.
- **No harm seen on the other 18 questions:** none of the other 16 added judgments appears in a top 10. The 8 small differences (R11 C and F: key authority 6 -> 7 and 5 -> 6; R12 C, R15 F, R20 A and E, R22 E and F: one passage swapped or two reordered) have no side-index passage in them. They are what adding any passages does to the keyword search (BM25 uses statistics over the whole collection) and to the 60-candidate cut. [Likely] A change of one rank on 14 questions is noise.
- **Passages nobody has marked:** 5 passages over 4 questions are in the arm's pools and not in the main-index pool (R02 1, R11 1, R12 1, R21 2 from the side index). The marks J and S return cover the main-index pool only. A small top-up (about 5 passages, 2 chats per question) can be added if the owner wants the arm marked; it is not needed for the main measurement.

## Limits

Tuning half only; 14 answerable questions; no marks, so "found by name" says nothing about whether a passage answers the question; the key authority for R21 was chosen by the owner's file, other authorities may also be right; the side index's choice of judgments was fixed by the register (not by the questions) before the run, but Arjun Panditrao was known to be needed for R21. The sealed half has not been touched. If the owner wants the final system to include the side index, the sealed run (once only) must use it: decide before that run.

## Files

`pool.json`, `questions.jsonl`, `spend.json` (as for the main-index pool); `key_overlay.json`; `authority_hits.json`, `AUTHORITY_HITS.md` (with the overlay); `arm_comparison.json`, `ARM_COMPARISON.md`; `RESULTS_IN_PLAIN_TERMS.md`.
