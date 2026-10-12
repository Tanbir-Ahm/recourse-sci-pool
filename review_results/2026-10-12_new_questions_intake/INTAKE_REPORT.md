# Intake report: the new 30-question file (received 2026-10-12) — PRIVATE

File: `Fix_Test_New_Questions_N01-N30.xlsx`, kept as received at `review_data/ruler/inputs/2026-10-12_Fix_Test_New_Questions_N01-N30_as_received.xlsx` (sha256 `88d32592417b91d331868467cf8489361d5d3410311c20baf5779a84d3b81586`).
Rules applied: `FIX_TEST_RULES_v2.md` (frozen, with v1) and `question_rules/New_Test_Questions_Rules_and_Guidelines.docx`. Nothing was searched, nothing was sent to Voyage, nothing was spent, and no question was handed out. **Nothing is sealed.**
All legal statements below about what a case holds are the writer's, checked against the judgments' indexed text where the judgment is in the index; none is lawyer-checked. Confidence tags: [Certain] read from a file or computed; [Likely] strong inference; [Guessing] judgment.

## 1. Bottom line

**The set cannot be sealed yet.** The counts and the format are right; three questions repeat topics we already used, the declaration is incomplete, and one point (the leading PWDVA case) conflicts with the owner's decision of 12 October. Mr. Advocate's key review is still to do.

| | Result |
|---|---|
| Format and counts (36 automatic checks) | 32 pass, 4 fail. The four are all about the key and the declaration, not about the mix. |
| Mix rules of section 5 | All pass. Closest to the limit: currency traps that can be measured (4 of the 4 needed), questions whose primary authority is outside the index (3 of the 3 allowed), OLD-code questions (6 of 6). |
| Duplicates | **Three hard duplicates of the ruler's topics (N02, N12, N15)** and four soft overlaps. The rules say overlaps are returned. |
| Index coverage | 58 of the 77 authorities named for N01 to N27 are in the index. Every one of the 27 has at least one key authority in the index. |
| Trigger check | N1 fires on the tagged Act in 9 of 16, N2 in 13 of 16. One misfire (N13, by design). No sign the questions were built around the anchors. |
| Declaration | Missing the line on AI tools; says the writer read the trigger-word list before writing (the rules ask the writer not to). |
| Writer's own freeze hash | Reproduced exactly: the question texts are the ones the writer froze. [Certain] |

## 2. What I need decided (owner)

1. **Who or what wrote the file?** The declaration says the writer worked "in this session", drafted the earlier 30 "in an earlier part of the same conversation", and has no line for AI tools. If an AI assistant drafted the questions or any part of the key, the rules (section 3) require the declaration to say which tool and for what. It also matters for weight: the rules call the first set "an AI research pass whose keys were only partly checked". [Likely that the writer is an AI assistant; I cannot verify it.]
2. **Return N02, N12 and N15 for replacement** (reasons in section 5). There is no reserve for domains A, E or F, so the writer must write them once (rules section 11.2, "rewritten once"). Keep what the rest of the set needs (section 5.3).
3. **Soft overlaps (N06, N07, N13, N04):** keep and disclose (my recommendation), or return? Section 5.2.
4. **Accept the declaration deviation** (trigger-word list read before writing) as a disclosed deviation? My recommendation: yes, because the trigger check shows no tailoring (section 7), and the question rules' ban was about choosing wording.
5. **Mr. Advocate reviews the key.** The sheet is ready (`Key_Review_Sheet_for_Mr_Advocate.xlsx`). He can start now on the 24 questions that are not being replaced.

## 3. Rules recount (script `review_tools/check_new_questions.py`, tested in `test_check_new_questions.py`)

PASS: sheets and column names; ids N01 to N30 and reserves NR1 to NR3; every question has a key row; domain counts A3 B3 C3 D2 E3 F3 G3 H3 I2 J2 K3; controls K1, K2, K3; phrasing E 9, L 10, N 8; Hinglish 1 (N11); code tags NEW 7, OLD 6, NONE 14 and every tag agrees with the numbers written in the text; currency traps tagged 6; best law from 2017 or later 15; Act-concerning 16; general 11; 12 of the 13 Acts covered (MV Act missing; 10 needed); NDPS 3, NI 3, PWDVA 2, POCSO 2; look-alikes 17; look-alikes that do not name their Act 8; every look-alike names its neighbour regime; twin pairs N07/N13, N15/N17, N18/N20, cross-referenced; reserves NR1 (B), NR2 (I), NR3 (K); length and sentence limits; no case name, case number, phone or e-mail in any question; no empty key cell; Conf values; each trap has the four parts; no primary authority after 30 June 2026.

FAIL (all four are findings for the writer, none is about the mix):
- **K3** N29: verified by "secondary sources only" but Conf is L. The rules force Conf = G.
- **K5** "Other acceptable authorities" says none for N10, N14, N17, N24 and NR2. The rules ask for every acceptable authority, at least two where they exist; the writer or Mr. Advocate should confirm none exists.
- **D1** The declaration has no "AI tools used and for what" line.
- **D2** The declaration says the writer read the trigger-word list (all eight sheets, including my draft Machine Spec and Index Reality Check sheets) before writing.

## 4. Index coverage (script `coverage.py`, my reading in `adjudication.py`)

Method: each named authority is looked up by its party names in the index's titles and opening text (10,503 judgments plus the 19 side-index judgments), and in the collection's records of judgments the index left out. Every match was read by eye; a name inside another judgment's opening lines (a counsel, a cited case) was not counted. [Likely complete; a judgment filed under an unexpected title could be missed.]

- **Primary authority outside the index: 3** (the most the rules allow): N01 Siddharth v. State of U.P. (2021), N05 Dilip Singh v. State of M.P. (2021), N15 Satish Chander Ahuja (2020; the collection has it but the index's criminal-law filter left it out). Each of the three still has an acceptable authority in the index (Antil; Ramesh Kumar; Prabha Tyagi), so none is unanswerable. If N15 is replaced by a question whose primary authority is in the index the count falls to 2.
- **Currency traps whose older ruling is in the index (so the trap can be measured): 4**, exactly the minimum: N08 (Narsingh Das Tapadia), N10 (E. Micheal Raj), N23 (Paparambaka Rosamma), N24 (Manharibhai Kakadia). The other two tagged traps cannot be measured: N15 (S.R. Batra is not in the index) and N26 (Radheshyam Bhagwandas Shah is not in the index). **If any of the four measurable traps is lost, the set falls below the minimum.**
- NR2 (reserve) is a strong trap: all three older rulings (Arup Bhuyan 2011, Raneef, Indra Das) are in the index.
- Key authorities (primary or acceptable, N01 to N27) that are not in the collection at all (16): Siddharth, Aman Preet Singh, Joginder Kumar, Dilip Singh, U.N. Gupta, Womb Laboratories, K. Bhaskaran, Mohan Lal v. State of Rajasthan (2015), Sorabkhan Gandhkhan Pathan, Sarabjit Kaur, Rajinder Singh v. State of Punjab (2015), Suresh v. State of U.P. (2024), Jagdish Lakra (2026), Surendra Bangali, Jagtar Singh v. State of Punjab (2023), Vishnu Kumar Gupta (2026). Left out by the index's criminal-law filter (3): Satish Chander Ahuja, S. Vanitha, Independent Thought. Older rulings not in the index: S.R. Batra, Radheshyam Bhagwandas Shah, Laxmi v. Om Prakash (only a duplicate copy was dropped), State of M.P. v. Rustam (reserve).
- The index ends in July 2026 (49 judgments dated 2026; the latest 13 July 2026), so the two judgments the key cites from July 2026 (Jagdish Lakra, Vishnu Kumar Gupta) are not in it.
- Control K2 (N29, audio-video recording of searches under s.105 BNSS): **no passage in the index mentions s.105 BNSS together with audio-video recording**; seven judgments mention videography of searches in other contexts (for example Kailas Pawar, Sept 2025, where the search was videographed and the High Court ordered a re-trial). So K2 is clean inside the index. Whether a Supreme Court judgment on or before 30 June 2026 exists outside the index is for Mr. Advocate to confirm (the writer checked by web search only).

## 5. Duplicates (script `duplicates.py`)

Method: (a) word overlap between each new question and the earlier 30 and the ruler's 33 questions (cosine on words and word pairs, no external service) — **no pair is close (highest 0.19)**, so no question was copied or lightly reworded; (b) overlap of authorities and of the legal issue with the earlier 30 and the ruler's 16 topics, which the word check cannot see. (b) is where the problems are.

### 5.1 Hard duplicates (same issue and same authority): return
| New | Earlier | Why |
|---|---|---|
| **N02** (domain A) | ruler topic T05 (dev half), Q09 and Q10 | Both ask whether the police must tell the person of the s.50 NDPS right before a personal search. Same primary authority (Vijaysinh Chandubha Jadeja); Baldev Singh is also shared. |
| **N12** (domain E) | ruler topic T02 (dev half), Q03 and Q04 | Both ask whether a civil land dispute can be turned into a forgery case. Same primary authority (Md. Ibrahim). |
| **N15** (domain F) | ruler topic T16 (frozen half), Q31 and Q32 | Both are the PWDVA shared-household issue. The only in-index authority for N15 is Prabha Tyagi, T16's expected case. N15's own primary, Satish Chander Ahuja, is not in the index and the owner decided on 12 October that it is not to be used. Its trap (S.R. Batra) is not in the index either. |

### 5.2 Soft overlaps (same legal ground, different facts or authority): your decision
- **N07** and ruler T15 (dev half): both ask whether a cheque given as security can still found a s.138 case. N07's primary (Sripati Singh) differs from T15's (Bir Singh). It is also the twin of N13, which is useful for the test.
- **N13** and ruler T10 and earlier R14: failure to repay a loan is not cheating. Different authorities.
- **N06** and earlier R25 (sealed set): both turn on the s.18 SC/ST bar on anticipatory bail; N06's own core is "public view" and its primary is Shajan Skaria. Prathvi Raj Chauhan is shared. The writer flagged this.
- **N04** and ruler T08 (frozen half): same authorities (Bikramjit Singh, M. Ravindran), different point (who may extend the period under UAPA s.43D(2)).
- Smaller: N01 and R02 share Antil; N11 and ruler T12 share Md. Nawaz Khan; N20 and R20 are both about consent in rape (promise of marriage versus earlier relationship).

My recommendation: keep N04, N06, N07 and N13, record them as disclosed overlaps, and report the results with and without them. [Guessing] A repeated issue helps every version equally, so the comparison between versions is not hurt; it flatters the floors a little.

### 5.3 What the three replacements must preserve
After removing N02, N12 and N15 the set still satisfies every rule **except**: PWDVA falls to 1 (needs 2), Act-concerning falls to exactly 14 (the minimum), the N15/N17 twin pair loses its partner, and domains A, E and F each have 2 of 3. So:
- N15's replacement should be a PWDVA question in domain F and the twin of N17 (the same facts as N17, under PWDVA instead of general law), with a primary authority in the index, a different issue from T16, and no Ahuja.
- N02's replacement (domain A) and N12's replacement (domain E): any topic that does not repeat T01 to T16 or the earlier 30; an Act-concerning look-alike would keep the Act count above the minimum.
- Do not remove a measurable trap (N08, N10, N23, N24).
- Authorities that are in the index and unused so far for PWDVA: Juveria Abdul Majid Patni (2014), Shyamlal Devda (2020), Rajnesh v. Neha (2020), Kiran Jyot Maini (2024), Kailashben Mahendrabhai Patel (2024), Geddam Jhansi (2025), Shaurabh Kumar Tripathi (2025), Dhananjay Rathi (2026). Hiral Harsora, Indra Sarma and Krishna Bhatacharjee are **not** in the index. Any new authority should be checked against the index before the question is written; I can do that in minutes.

## 6. The key (written by the writer; spot-checked by me against indexed text, not lawyer-checked)

- I tested 31 statements of the key against the indexed text of the judgments that are in the index. In all 31 the text contains the matching words; I read the passage for each example below (a word match shows the words are there, not that the judgment decides the point as the key says). Examples: Sripati Singh does say the s.420 IPC complaint was "not sustainable" while the s.138 complaint was maintainable (N13); Yogendra Pratap Singh does say "we do not approve the view taken in Narsingh Das Tapadia" (N08); Bikramjit Singh does hold that the Special Court alone can extend under s.43-D(2)(b) (N04); Gunwantlal does require "consciousness or knowledge" for possession (N21); Hira Singh does record disagreement with E. Micheal Raj (N10); Antil's guidelines cite Siddharth for "no need to forward such an accused along with the chargesheet" and give its citation as 2021 SCC OnLine SC 615 (N01). Details: `claims_out.txt`.
- **One mismatch:** N19. P. Yuvaprakash, the key's primary, is about the age of a **victim** (a girl said to be 17), not of an accused. The question is about the accused's age. Rishipal Singh Solanki (in the index; an accused's juvenility claim) is listed only as an acceptable authority. The writer's own note says the same. Mr. Advocate to choose the primary.
- The Constitution Bench in V. Sriharan (the key's authority in N26) is in the index (a different judgment of 2014 by the same name is also there); the 2022 Radheshyam order is not.
- Many "not opened" items can now be read: Madan Lal (N11), Ramesh Kumar (N05), Hridaya Ranjan (N13), Alister Anthony Pareira and Sanjeev Nanda (N22), Laxman and Paparambaka (N23), Kapil Wadhawan (NR1) are in the index; Mr. Advocate can read them through the sheet's document numbers.
- N20: the only case law offered is Mango Ram (2000) and Gurmit Singh (1996), both before the 2013 definition of consent; the key says so. Modern authority may exist and should be added if it does.
- N26 and N29 are Conf G and L on secondary sources; N29 should be G.

## 7. Trigger check (script `trigger_check.py`, Machine Spec v2 as frozen)

- Of the 16 scored questions the writer tagged with an Act: the tagged Act fires under **N1 on 9** and under **N2 on 13**. Neither fires on **N06** (caste abuse), **N11** (Hinglish drug bag) and **N18** (a 17-year-old). These are exactly the lay look-alikes the plain-language anchors are weakest on.
- **One misfire, N13** (NI Act on the general-law twin of N07): this is the case the twin pair is designed to test.
- The 11 general questions and the 3 controls fire nothing.
- Where the arms can differ from B: N1 on 10 of the 27 scored questions, N2 on 14. N1 and N2 differ from each other on only 4 (N02, N14, N15, N21). If N02 and N15 are replaced the comparison of N1 with N2 rests on N14 and N21 plus whatever the replacements fire. **The set will be able to separate N1 from N2 only if the replacements are chosen with that in mind; otherwise expect no difference between them.** [Likely]
- No sign of tailoring: if the questions had been built around the anchors, almost every tagged question would fire. They do not.

## 8. The declaration

- It says the writer drafted the earlier 30, read all eight sheets of the trigger workbook (including my draft Machine Spec) before writing, and ran a trigger check after freezing (in a separate file not sent).
- **The writer's freeze hash is correct:** SHA-256 of `Id<TAB>question text` for all 33 rows, one per line, equals `7a6963d1159963f5611c4df2fe4d9840ce7f37423d360e656e3afec83e1c99a3`. The key sheet is not covered by that hash.
- Missing: the AI-tool line (D1).
- The writer authored the earlier 30 and their keys. The rules allow this (section 3: "may have seen the earlier 30 questions"), but the frozen v1 text (section 2) says "has not seen the sealed or tuning questions". The two texts disagree; the question rules were the ones issued to the writer.

## 9. What follows, in order

1. Owner answers section 2 (items 1 to 4).
2. Writer returns the replacements and a corrected declaration; I recount, re-check duplicates, index coverage and triggers on the new questions.
3. Mr. Advocate reviews the key (the sheet), the writer corrects.
4. Seal: ids fixed, file hash recorded, hand-out guard installed, committed; stage F loader coded, tested and committed; preflight; one search of B, N1-125 and N2-125.
5. Pack for J and S (about 60 chats), two-stage scoring, report. Mr. Advocate reads every passage anyone marks Misleading plus a random 20.

Files: `coverage.py`/`coverage.json`/`coverage_out.txt`, `authorities.py`, `adjudication.py`, `index_status.py`/`index_status.json`, `duplicates.py`/`dups_out.txt`, `trigger_check.py`/`trigger_check.json`, `claims_check.py`/`claims_out.txt`, `recount.json`.
