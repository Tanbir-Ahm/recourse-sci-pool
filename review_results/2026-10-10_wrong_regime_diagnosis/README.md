# Where the right passage gets lost: diagnosis on five used-up sealed questions (2026-10-10; PRIVATE; diagnosis only, no fix tested, no rule changed)

`diagnose.py` (output `diagnosis.json`) follows the key judgment's best passage through the search stages for R16, R03, R10, R13 and R23; `diag_r16.py` looks closer at R16. Spend about $0.02 (Voyage calls). These questions are used up: nothing here is evidence that a fix works.

**This corrects what was said before the diagnosis.** The "wrong legal regime" failure was guessed to be a retrieval problem (the neighbour crowding out the right passage). For R16 it is not.

| Q | What happened | Stage that failed |
|---|---|---|
| R16 (domestic-violence limitation) | The right judgment (Kamatchi) is the best match **by meaning in the whole index (rank 1 of 238,762)**, fourth in the fused order, inside the 60 candidates. Both re-rankers then put its best passage 13th (rerank-2) and 9th (rerank-3-lite), 11th after the weights. Rerank-2's first seven are all limitation-doctrine passages that never mention the Domestic Violence Act, from only two judgments. 40 of the 60 candidates do mention the Act; the first sits 8th. | **re-ranker** |
| R03 (CrPC arrest duties) | The 1997 D.K. Basu judgment's own passages are 137th or lower by meaning and not candidates; later judgments that restate Basu are the top 3 by meaning. The question names sections (41B, 41D, 50A) that the 1997 judgment predates. Rerank-2 put 3 passages on the NDPS Act's section 50 in the top 5; rerank-3-lite put none. | mostly **how the key was written** (one judgment named); rerank-2 also let a neighbour in |
| R10 (NDPS dual role) | Key is first by meaning and first after both re-rankers. The Misleading marks come from passages of the overruled Mohan Lal (2018). | not retrieval or ranking: **currency** (the register's job) |
| R13 (quashing on settlement) | Key found (13th by meaning, fifth fused); the re-rankers put it 20th and 21st, but the top 5 were still marked Yes by most marks. | **key too narrow** (other right authorities) |
| R23 (single blow, parking fight) | The right passage is 46th by meaning but **88th in the fused order, so it is cut before the re-ranker sees it** (60 candidates). If added, the re-ranker puts it 2nd or 3rd. | **candidate cut-off (60)** |

Five questions, four different causes. The earlier statement that wrong-regime passages are a general retrieval pattern is **not supported**; the only demonstrated regime failure is R16, and it is a re-ranking failure.

Candidate fixes this suggests (none tested; each needs the pre-registered rule and NEW questions): for R23-type, a wider candidate pool (cost: more re-rank tokens, and the earlier tuning found a deeper net added noise elsewhere); for R16-type, something that stops two judgments filling the top five, or a small boost for passages that contain the Act the question names (the section boost of 1.10 is the existing precedent); for R10-type, the register, not the search.
