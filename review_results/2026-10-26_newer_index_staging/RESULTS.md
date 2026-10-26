# The newer wide index (19,236 + 19 judgments: Supreme Court and Gauhati High Court) prepared for STAGING (2026-10-26)

Owner's request (2026-10-26): "test everything in staging web, before we finally deploy it in the main website. Deploy everything that is being built, the index with 19,236 judgements (both supreme court + high court) and all the fixes to the staging web."

**What I could not do:** reach Railway (the sandbox proxy refuses `*.up.railway.app`) or read its variables. So nothing is "deployed" by me: I prepared and pushed code and data so that four variables on the staging `sci-search` service switch it to the newer index; the Recourse branch and `recourse-web` `main` (which staging deploys by itself) are pushed. The owner's steps are `DEPLOY_STAGING.md` Part 4y.

## 1. Corrections to what I said on 2026-10-25
* The newer index is **not Supreme Court only**: 11,683 Supreme Court judgments (10,444 from the first index, 1,239 newer ones from the court's own site, 2017 to 16 Oct 2026) and **7,553 Gauhati High Court judgments** (ghc_post2017 5,830, ghc_bucket 965, ghc_court 758). It holds **no other High Court**.
* It does **not** end on 13 July 2026: newest decisions are 16 Oct 2026 (Supreme Court) and 14 Oct 2026 (Gauhati High Court).
* The "at least 1,144 from 2026" counts both courts (781 of them High Court).
The files that carried these claims are corrected in place (`review_results/2026-10-25_search_index_check/RESULTS.md`, FOLLOW_UPS 2ch, CLAUDE.md).

## 2. What is in the newer index (counted from the shard files, `d8811a910c73b0159bea7bcf3183ea258120db5b`, 2026-10-24)
* 19,236 judgments with passages in the main index (418,286 passages) + 19 judgments in the three hand-made side indexes (2,607 passages) = **19,255 documents, 420,893 passages**. 69,008 files were looked at; 49,765 set aside on purpose (43,546 not criminal law by a keyword test, 3,084 already in the crawl, 1,733 too short, 1,116 duplicates, 286 near-duplicates).
* Court of each document (names table): Supreme Court of India 11,702 (incl. 19 side-index), Gauhati High Court 7,553. Link kinds: court archive PDF 8,113, open Supreme Court bucket 2,348, **High Court bucket 6,795**, High Court's own site 758, Supreme Court's own site 1,239, other 2.
* 19,147 documents have a readable case name; **108 are held back from every page** (name to review), as before.

## 3. What I built (research repo, additive; production's pin, default names table and default side indexes are untouched)
* `names_table/build_names_table.py`: reads the newer documents' own source record (title, date, citation, link, **court**), splits a "X Vs Y" title into parties, cuts a judge's name glued to a party (110 of the 7,553 had one), and adds a `court` to every row (a document with no recorded court is "Court not recorded" and flagged for a person, never labelled as the Supreme Court). New arguments `--sides` and `--index-commit`. Output `names_table/names_table_d8811a9.json.gz` (19,255 rows). Test `test_names_table.py` extended (all pass).
* `review_data/side_index_d8811a9/`: copies of the three side indexes whose `SUPPLEMENT.json` names the newer main index (the service refuses a side index tied to another main index); 0 document clashes.
* `sci_search_service.py`: a **`court` on every result**, `as_of_by_court` in the reply, the newest decision date across courts as `as_of`, and a start-up line that names the judgments and courts. `test_sci_search_service.py` extended (all pass).
* Loader test with the service's own loader, offline (a dummy embedding client):

| | pinned index (what runs today) | newer index |
|---|---|---|
| documents | 10,522 | 19,255 |
| passages | 238,762 | 420,893 |
| courts | Supreme Court 10,522 | Supreme Court 11,702, Gauhati High Court 7,553 |
| newest decision | 2026-07-13 | 2026-10-16 (SC), 2026-10-14 (GHC) |
| disk, index files | 572 MB | 994 MB |
| memory after load / peak | 1,540 / 1,760 MB | 2,543 / 2,989 MB |
| load time here | 107 s | 131 s |

  The pinned index loaded with the NEW service code gives exactly the numbers it had before (the "old index, new code" test), with every result "Supreme Court of India". The numbers above are in `loader_report_pinned_3c80a26.json` and `loader_report_newer_d8811a9.json` (the service's own loader run offline, no key).
* Recourse (branch `register-hooks-and-overlay`, `11c706d` and `16498a9`) and `recourse-web` (`main`, `61bf7f4`): the court is named wherever the wider passages are shown or fed (prompt, passage headings, answer box, PDF/Word, table of authorities, search page, a notice when an answer ties a High Court case to the Supreme Court), the register and the cards are never applied to a High Court judgment, and all of it is word for word the old text when every passage is a Supreme Court one. Tests: Recourse free suite 111 of 111 (new `test_court_labels.py`), `recourse-web` tsc clean, vitest 80, Playwright 37 (new: a mixed Supreme/High Court reply).

## 4. Does the newer index find known judgments as well as the pinned one? (the real search recipe, `compare_old_new.py`)
Same 12 questions as `landmarks.json` (six landmark judgments, each asked in a layman's and a lawyer's words), run through `SearchService.search` (meaning + words + section lookups, rank fusion, Voyage rerank) on each index in turn; success here = the landmark judgment is among the 10 passages returned (a coarser test than the older raw-index one, which also needed the verified paragraph). 21 searches per index, about $0.02 each run. Run twice on the newer index: identical ranks.

| Landmark judgment | words | rank in pinned index (10,522) | rank in newer index (19,255) | other-court passages in the newer top 10 |
|---|---|---|---|---|
| Arnesh Kumar (arrest must be necessary) | lay | 1 | 4 | 0 |
| Arnesh Kumar (arrest must be necessary) | legal | 10 | - | 3 |
| Md Ibrahim (civil dispute dressed as crime) | lay | - | - | 3 |
| Md Ibrahim (civil dispute dressed as crime) | legal | 8 | - | 4 |
| Nanda Gopalan (compromise, grievous hurt) | lay | - | - | 1 |
| Nanda Gopalan (compromise, grievous hurt) | legal | - | - | 0 |
| Rangappa (s.139 presumption) | lay | - | - | 5 |
| Rangappa (s.139 presumption) | legal | 2 | 2 | 3 |
| Jadeja (s.50 NDPS genuine compliance) | lay | - | - | 1 |
| Jadeja (s.50 NDPS genuine compliance) | legal | 3 | 2 | 1 |
| Noor Aga (NDPS reverse burden) | lay | - | - | 6 |
| Noor Aga (NDPS reverse burden) | legal | - | - | 7 |

pinned (3c80a26): landmark judgment in the top 10: 5 of 12; in the top 5: 3; in the top 3: 3. Load 79.3 s. Search spend for the 21 searches: 0.0177 dollars.

newer (d8811a9): landmark judgment in the top 10: 3 of 12; in the top 5: 3; in the top 3: 2. Load 66.1 s. Search spend for the 21 searches: 0.0163 dollars.

### Who took the landmark judgments' places (newer index, `who_displaced.py`)
| Landmark | words | pinned rank | newer rank | in the newer top 10: other-court / newer Supreme Court / first-index Supreme Court passages | rank among Supreme Court passages only |
|---|---|---|---|---|---|
| Arnesh Kumar (arrest must be n | lay | 1 | 4 | 0 / 4 / 6 | 4 |
| Arnesh Kumar (arrest must be n | legal | 10 | - | 3 / 1 / 6 | - |
| Md Ibrahim (civil dispute dres | lay | - | - | 3 / 3 / 4 | - |
| Md Ibrahim (civil dispute dres | legal | 8 | - | 4 / 4 / 2 | - |
| Nanda Gopalan (compromise, gri | lay | - | - | 1 / 1 / 8 | - |
| Nanda Gopalan (compromise, gri | legal | - | - | 0 / 2 / 8 | - |
| Rangappa (s.139 presumption) | lay | - | - | 5 / 0 / 5 | - |
| Rangappa (s.139 presumption) | legal | 2 | 2 | 3 / 0 / 7 | 2 |
| Jadeja (s.50 NDPS genuine comp | lay | - | - | 1 / 0 / 9 | - |
| Jadeja (s.50 NDPS genuine comp | legal | 3 | 2 | 1 / 0 / 9 | 2 |
| Noor Aga (NDPS reverse burden) | lay | - | - | 6 / 0 / 4 | - |
| Noor Aga (NDPS reverse burden) | legal | - | - | 7 / 1 / 2 | - |

All 120 passages of the 12 newer top 10s: other court 34 (28%), newer Supreme Court 16 (13%), first-index Supreme Court 70 (58%).

## 5. What this shows, and what it does not
* **[Certain]** On these 12 questions the newer index returns the landmark judgment in its top 10 for **3** questions; the pinned index for **5**. In the top 5: 3 and 3; in the top 3: 2 and 3. Two questions are lost (Arnesh Kumar in the lawyer's words, Md Ibrahim in the lawyer's words), one slips from rank 1 to 4 (Arnesh Kumar in the layman's words), one improves (Jadeja, 3 to 2).
* **[Certain]** **Gauhati High Court passages fill 28% of the 120 places in the 12 top 10s** and 39% of the places in the 9 spot-check top 10s (0 to 10 of 10 depending on the question; "quashing of an FIR when the parties have settled" returned ten Gauhati High Court passages and no Supreme Court one). Newer Supreme Court judgments (2017 to 2026) take another 13%. Both take places the older Supreme Court judgments held.
* **[Likely]** The mechanism is the same as before: with more judgments of the same kind there are more passages that match a question as well as the landmark does, and the top 10 has the same ten places. It is not a defect of the High Court material itself. **[Guessing]** Whether the landmark cases would be found again if the Supreme Court's passages were always placed first, or if the High Court passages were capped, is untested; it is the obvious next experiment and a design decision for the owner (a Supreme Court decision binds every court in India, a Gauhati High Court decision binds Assam and the north-east and is persuasive elsewhere).
* **Not shown:** that the newer index is more or less accurate overall. Twelve questions prove little; the landmark questions are Claude's earlier choice, not a lawyer's; the nine spot-check questions are Claude's and **nobody has marked any result**. The newer index does add 8,792 judgments and about 3 months of decisions the pinned one lacks, which these 12 questions cannot value.
* **Not tried:** anything with the answer model (no Anthropic key here), anything on Railway, and the High Court material with a lawyer reading the answers.

## 6. Spot-check tables (descriptive only)
| Landmark judgment | words | rank in pinned index (10,522) | rank in newer index (19,255) | other-court passages in the newer top 10 |
|---|---|---|---|---|
| Arnesh Kumar (arrest must be necessary) | lay | 1 | 4 | 0 |
| Arnesh Kumar (arrest must be necessary) | legal | 10 | - | 3 |
| Md Ibrahim (civil dispute dressed as crime) | lay | - | - | 3 |
| Md Ibrahim (civil dispute dressed as crime) | legal | 8 | - | 4 |
| Nanda Gopalan (compromise, grievous hurt) | lay | - | - | 1 |
| Nanda Gopalan (compromise, grievous hurt) | legal | - | - | 0 |
| Rangappa (s.139 presumption) | lay | - | - | 5 |
| Rangappa (s.139 presumption) | legal | 2 | 2 | 3 |
| Jadeja (s.50 NDPS genuine compliance) | lay | - | - | 1 |
| Jadeja (s.50 NDPS genuine compliance) | legal | 3 | 2 | 1 |
| Noor Aga (NDPS reverse burden) | lay | - | - | 6 |
| Noor Aga (NDPS reverse burden) | legal | - | - | 7 |

pinned (3c80a26): landmark judgment in the top 10: 5 of 12; in the top 5: 3; in the top 3: 3. Load 79.3 s. Search spend for the 21 searches: 0.0177 dollars.

newer (d8811a9): landmark judgment in the top 10: 3 of 12; in the top 5: 3; in the top 3: 2. Load 66.1 s. Search spend for the 21 searches: 0.0163 dollars.

Spot-check questions (nobody has marked them): passages of another court in the newer index's top 10, and its top three cases
| Question | other-court passages (of 10) | newer index: first three results (court, case) |
|---|---|---|
| bail in a case under the NDPS Act where the quantity is commercial: what are the twin cond | 2 | SC: Union of India v. Ajay Kumar Singh @ Pappu; SC: State of Punjab v. Sukhwinder Singh @ Gora; SC: State of Punjab v. Sukhwinder Singh @ Gora |
| can anticipatory bail be granted with conditions and for how long does it last | 0 | SC: Sushila Aggarwal and Others v. State (NCT ; SC: Md. Asfak Alam v. The State of Jharkhand &; SC: Sushila Aggarwal and Others v. State (NCT  |
| quashing of an FIR when the parties have settled, the power of the High Court | 10 | GHC: Sukinath Bhowmik and Anr v. The State of A; GHC: Teshi Peter and Anr v. The State of AP; GHC: Tamchi Mongku and 3 Ors v. The State of AP |
| delay in lodging the FIR and its effect on the prosecution case | 5 | SC: Jitender Kumar v. State of Haryana; SC: Jeewan & Ors v. State of Uttarakhand; SC: Ashok Kumar Chaudhary & Ors v. State of Bi |
| when can a dying declaration alone be the basis of a conviction | 3 | SC: Rajendra S/O Ramdas Kolhe v. State of Maha; SC: Krishan v. State of Haryana; SC: Naeem v. State of Uttar Pradesh |
| possession of a firearm without licence under the Arms Act, conviction and sentence | 4 | GHC: Bhakta Chakma v. The State of AP and Anr; SC: Paras Ram v. State of Haryana; GHC: Sultan Uddin v. The State of Assam & Anr |
| default bail when the chargesheet is not filed within 60 or 90 days | 0 | SC: Shaurya Sunil Kumar Singh v. Central Burea; SC: Rakesh Kumar Paul v. State of Assam; SC: Enforcement Directorate, Government of Ind |
| criminal trespass and cheating over a land dispute in Assam | 8 | GHC: Biren Chautal v. The State of Assam; GHC: Renubala Ghosh and Anr v. The State of Ass; SC: Sri Gulam Mustafa v. The State of Karnatak |
| Armed Forces Special Powers Act and the arrest of a civilian | 3 | SC: Balkishan A. Devidayal etc v. State of Mah; SC: Sadhwi Pragyna Singh Thakur v. State of Ma; SC: Balkishan A. Devidayal etc v. State of Mah |

Same spot-check questions on the pinned index (first three results)
| Question | first three results |
|---|---|
| bail in a case under the NDPS Act where the quantity is commercial: what are the twin cond | State of Punjab v. Balraj Singh @ Billa; Nikesh Tarachand Shah v. Union of India & ; The State of Meghalaya v. Lalrintluanga Sa |
| can anticipatory bail be granted with conditions and for how long does it last | Sushila Aggarwal and Others v. State (NCT ; Md. Asfak Alam v. The State of Jharkhand &; Sushila Aggarwal and Others v. State (NCT  |
| quashing of an FIR when the parties have settled, the power of the High Court | Ramji Lal Bairwa & Anr v. State of Rajasth; Social Action Forum for Manav Adhikar and ; J.RAMESH Kamath & Ors v. Mohana Kurup & Or |
| delay in lodging the FIR and its effect on the prosecution case | Ashok Kumar Chaudhary & Ors v. State of Bi; Gurmail Singh v. State of Punjab & Anr; Jeewan & Ors v. State of Uttarakhand |
| when can a dying declaration alone be the basis of a conviction | Rajendra S/O Ramdas Kolhe v. State of Maha; Krishan v. State of Haryana; Naeem v. State of Uttar Pradesh |
| possession of a firearm without licence under the Arms Act, conviction and sentence | Paras Ram v. State of Haryana; Surinder Singh v. State (Union Territory o; Mahendra Singh v. State of West Bengal |
| default bail when the chargesheet is not filed within 60 or 90 days | Shaurya Sunil Kumar Singh v. Central Burea; Rakesh Kumar Paul v. State of Assam; Enforcement Directorate, Government of Ind |
| criminal trespass and cheating over a land dispute in Assam | Sri Gulam Mustafa v. The State of Karnatak; Maguni Charan Pradhan v. State of Orissa; Rajinder & Ors v. State of Haryana |
| Armed Forces Special Powers Act and the arrest of a civilian | Balkishan A. Devidayal etc v. State of Mah; Sadhwi Pragyna Singh Thakur v. State of Ma; Balkishan A. Devidayal etc v. State of Mah |

## 7. Open items and risks (all stated in Part 4y too)
1. Memory about 3 GB and a volume of at least 5 GB on the staging `sci-search` service, or it will not load.
2. **Licence of the High Court copies not read by me.** A web search on 2026-10-26 reported that the registry page lists CC-BY-4.0 (Dattam Labs); I could not open <https://registry.opendata.aws/indian-high-court-judgments/> from the sandbox. The pages say "licence terms to be confirmed" until the owner confirms it.
3. No register or checker card has been computed for any High Court judgment: every High Court passage says "Not checked by us." A High Court decision can be reversed or doubted by the Supreme Court and nothing here would say so.
4. The title list used for "find a case by name" still ends 12 Dec 2025 and holds Supreme Court cases only.
5. The wording "a High Court's decision does not bind courts outside its own territory" is mine; no lawyer has read it.
6. Production's `sci-search` deploys the same research branch, so the new service code (additive) reaches it on its next redeploy; shown above to leave the old index's behaviour unchanged. Its start-up line gains a tail.
7. The Gauhati High Court material is a keyword-selected criminal subset like the Supreme Court's; no other High Court is in the index.

## Files here
`compare_old_new.py` (the runner; needs `VOYAGE_API_KEY`), `compare_pinned_3c80a26.json`, `compare_newer_d8811a9.json`, `compare_newer_d8811a9_rows.json` (the same run with every returned passage kept), `summarize_compare.py`, `who_displaced.py`, `loader_report_pinned_3c80a26.json`, `loader_report_newer_d8811a9.json`.

## 8. First use on staging (owner's PDF "Armed Forces Special Powers Act arrest", 2026-10-26 11:46 IST; FOLLOW_UPS 2cj)
* **Worked:** the staging `sci-search` loaded the newer index (log line in section 3); the lawyer note named the "Gauhati High Court" for both Gauhati cases; the box under the answer, the authorities table and the export all name each passage's court and credit the High Court copies; no passage was called a Supreme Court one; no court-label notice was needed.
* **Found and fixed (Recourse `6d939ca`):** a doubled wider-search label after a long bracket; a false "party's submission" note on the Court's own "We have considered the rival submissions" (General Officer Commanding v. CBI, 2012: the most relevant Supreme Court passage on sanction was told to the reader as a party's submission); a High Court title that starts with the officer's service number was not found in the answer (not labelled by code, listed in the "not checked" sentence).
* **Found, NOT fixed (owner's decision):** the passage credited to Sadhwi Pragyna Singh Thakur v. State of Maharashtra (2011), "paragraph 8", is V.L. Rohlua v. Deputy Commissioner, Aijal ((1970) 2 SCC 908, Constitution Bench), paragraph 8, quoted in paragraph 25 of Sadhwi's judgment (checked in the crawl text of document 38684: "a Constitution Bench of this Court has made following observations in paragraphs 5, 6 and 8 of V.L. Rohlua"). The answer's "Grounds" and the For-the-client row rest on Sadhwi; they belong to Rohlua. The cause is in the index (a chunk that starts inside a quotation and carries the quoted paragraph's number), so it affects the Supreme Court passages as much as the High Court ones.

## 9. Second staging PDF (same question again + the follow-up "is bail possible in this case?"; FOLLOW_UPS 2cl)
* **Worked:** one label per wider-search case; General Officer Commanding v. CBI used correctly (no false "party's submission" note); Major Sowmithri found and labelled; court labels throughout.
* **Quoted-passage rule: partly.** No paragraph number in the text, no ground built on the Sadhwi passage, passage hedged; but the answer still credits Sadhwi ("recorded that ... least possible delay"). One sample.
* **Follow-up retrieval defect (new, mine):** the bail question was answered from BNSS 83, not 480/482/483, because the rewrite of the follow-up carries the Armed Forces words and drowns the bail words. Offline with the real retrieval: the person's words alone return BNSS 139, 480, 488, 482; three plausible rewrites return BNSS 42, 521, 60, 47 (83) and no bail section. Proposed fix (a), awaiting the owner: retrieve on both and merge.
* **Library case labelled as wider search:** Pankaj Bansal, in both tables, with contradictory currency wording.
