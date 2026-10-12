# Stage F search results (the key is closed; no marks yet)

Run: 2026-10-12T11:16:52Z; index 3c80a26e42; label: stage F, single search | fix test stage F | rules d2f2be58da05 | code 8046790b4c; versions: B, N1-125 named-Act boost x1.25 (precise), N2-125 named-Act boost x1.25 (broad).
Spend: {"rerank_tokens": 600391, "rerank_calls": 29, "embed_tokens": 2105, "embed_calls": 29, "cap_rerank_tokens": 3000000, "dollars_estimate": 0.0303, "prices_per_million": {"rerank-2": 0.05, "voyage-law-2": 0.12}, "rerank_tokens_by_model": {"rerank-3-lite": 600391}}

## 1. In one table

29 questions. **N1-125 changed B's top 5 on 7; N2-125 on 9.** An Act 'fires' when the question's words match the pinned Machine Spec; only then can a finalist differ from B.

| Question | Domain | Act fired (N1) | Act fired (N2) | N1 top 5 vs B | N2 top 5 vs B |
|---|---|---|---|---|---|
| N01 | A | - | - | same | same |
| N02 | A | - | - | same | same |
| N03 | A | - | - | same | same |
| N04 | B | UAPA | UAPA | 2 new | 2 new |
| N05 | B | - | - | same | same |
| N06 | B | - | - | same | same |
| N07 | C | NI Act | NI Act | same | same |
| N08 | C | NI Act | NI Act | same | same |
| N09 | C | NI Act | NI Act | 2 new | 2 new |
| N10 | D | NDPS | NDPS | same | same |
| N11 | D | - | - | same | same |
| N13 | E | NI Act | NI Act | 3 new | 3 new |
| N14 | E | - | IT Act | same | 1 new |
| N15 | F | PWDVA | PWDVA | 4 new | 4 new |
| N16 | F | DPA | DPA | 1 new | 1 new |
| N17 | F | - | - | same | same |
| N18 | G | - | - | same | same |
| N19 | G | JJ Act, POCSO | JJ Act, POCSO | same | same |
| N20 | G | - | - | same | same |
| N21 | H | - | Arms Act | same | 1 new |
| N22 | H | - | - | same | same |
| N23 | H | - | - | same | same |
| N24 | I | PMLA | PMLA | 3 new | 3 new |
| N25 | I | PC Act | PC Act | 1 new | 1 new |
| N26 | J | - | - | same | same |
| N27 | J | - | - | same | same |
| N28 | K | - | - | same | same |
| N29 | K | - | - | same | same |
| N30 | K | - | - | same | same |

## 2. The questions where a finalist changed the top 5 (B | N1-125 | N2-125; passage = page number inside the judgment)

### N04 (domain B)

*Whether, in a case under the UAPA investigated by the State police, an order of a Magistrate extending the period of investigation beyond 90 days under Section 43D(2) defeats the accused's right to default bail under Section 167(2) CrPC.*

| Place | B | N1-125 | N2-125 |
|---|---|---|---|
| 1 | IN THE SUPREME COURT OF INDIA CRIMINAL APPEALLATE JURISDICTION … (), p.40 | NASER BIN ABU BAKR YAFAI versus THE STATE OF MAHARASHTRA & ANR. (2021), p.34 **(changed)** | NASER BIN ABU BAKR YAFAI versus THE STATE OF MAHARASHTRA & ANR. (2021), p.34 **(changed)** |
| 2 | NASER BIN ABU BAKR YAFAI versus THE STATE OF MAHARASHTRA & ANR. (2021), p.34 | NASER BIN ABU BAKR YAFAI versus THE STATE OF MAHARASHTRA & ANR. (2021), p.34 **(changed)** | NASER BIN ABU BAKR YAFAI versus THE STATE OF MAHARASHTRA & ANR. (2021), p.34 **(changed)** |
| 3 | NASER BIN ABU BAKR YAFAI versus THE STATE OF MAHARASHTRA & ANR. (2021), p.34 | BIKRAMJIT SINGH versus THE STATE OF PUNJAB (2020), p.39 **(changed)** | BIKRAMJIT SINGH versus THE STATE OF PUNJAB (2020), p.39 **(changed)** |
| 4 | BIKRAMJIT SINGH versus THE STATE OF PUNJAB (2020), p.39 | JUDGEBIR SINGH @ JASBIR SINGH SAMRA @ JASBIR & ORS. versus NATI… (2023), p.27 **(changed)** | JUDGEBIR SINGH @ JASBIR SINGH SAMRA @ JASBIR & ORS. versus NATI… (2023), p.27 **(changed)** |
| 5 | M. RAVINDRAN versus THE INTELLIGENCE OFFICER, DIRECTORATE OF RE… (2020), p.32 | GAUTAM NAVLAKHA versus NATIONAL INVESTIGATION AGENCY (2021), p.100 **(changed)** | GAUTAM NAVLAKHA versus NATIONAL INVESTIGATION AGENCY (2021), p.100 **(changed)** |

### N09 (domain C)

*Whether the statutory demand notice under Section 138 of the NI Act is deemed to be served when it is sent by registered post to the drawer's correct address but returned 'unclaimed'.*

| Place | B | N1-125 | N2-125 |
|---|---|---|---|
| 1 | C.C. ALAVI HAJI v. PALAPETTY MUHAMMED & ANR. (2007), p.6 | C.C. ALAVI HAJI v. PALAPETTY MUHAMMED & ANR. (2007), p.6 | C.C. ALAVI HAJI v. PALAPETTY MUHAMMED & ANR. (2007), p.6 |
| 2 | IN THE SUPREME COURT OF INDIA CRIMINAL APPELLATE JURISDICTION C… (), p.9 | IN THE SUPREME COURT OF INDIA CRIMINAL APPELLATE JURISDICTION C… (), p.9 | IN THE SUPREME COURT OF INDIA CRIMINAL APPELLATE JURISDICTION C… (), p.9 |
| 3 | D. Vinod Shivappa v. Nanda Belliappa (2006), p.6 | C.C. ALAVI HAJI v. PALAPETTY MUHAMMED & ANR. (2007), p.3 **(changed)** | C.C. ALAVI HAJI v. PALAPETTY MUHAMMED & ANR. (2007), p.3 **(changed)** |
| 4 | D. Vinod Shivappa v. Nanda Belliappa (2006), p.5 | IN THE SUPREME COURT OF INDIA CRIMINAL APPELLATE JURISDICTION C… (), p.9 **(changed)** | IN THE SUPREME COURT OF INDIA CRIMINAL APPELLATE JURISDICTION C… (), p.9 **(changed)** |
| 5 | C.C. ALAVI HAJI v. PALAPETTY MUHAMMED & ANR. (2007), p.3 | V. Raja Kumari v. P. Subbarama Naidu & Anr. (2004), p.3 **(changed)** | V. Raja Kumari v. P. Subbarama Naidu & Anr. (2004), p.3 **(changed)** |

### N13 (domain E)

*I borrowed 3 lakhs from a friend for my shop and gave him a signed cheque as security. The shop ran into losses, I couldn't repay on the date we agreed, and the cheque bounced when he deposited it. Now he has also gone to the police and got an FIR registered against me under 420 IPC, saying I cheated him. I paid him interest for many months and I'm ready to repay slowly. Does a bounced cheque and…*

| Place | B | N1-125 | N2-125 |
|---|---|---|---|
| 1 | Veer Prakash Sharma v. Anil Kumar Agarwal & Anr. (2007), p.3 | SRIPATI SINGH (SINCE DECEASED) THROUGH HIS SON GAURAV SINGH ver… (2021), p.10 **(changed)** | SRIPATI SINGH (SINCE DECEASED) THROUGH HIS SON GAURAV SINGH ver… (2021), p.10 **(changed)** |
| 2 | SRIPATI SINGH (SINCE DECEASED) THROUGH HIS SON GAURAV SINGH ver… (2021), p.10 | SRIPATI SINGH (SINCE DECEASED) THROUGH HIS SON GAURAV SINGH ver… (2021), p.17 **(changed)** | SRIPATI SINGH (SINCE DECEASED) THROUGH HIS SON GAURAV SINGH ver… (2021), p.17 **(changed)** |
| 3 | SATISHCHANDRA RATANLAL SHAH versus STATE OF GUJARAT AND ANOTHER (2019), p.7 | SUNIL TODI & ORS. versus STATE OF GUJARAT & ANR. (2021), p.19 **(changed)** | SUNIL TODI & ORS. versus STATE OF GUJARAT & ANR. (2021), p.19 **(changed)** |
| 4 | SRIPATI SINGH (SINCE DECEASED) THROUGH HIS SON GAURAV SINGH ver… (2021), p.17 | SUNIL TODI & ORS. versus STATE OF GUJARAT & ANR. (2021), p.19 **(changed)** | SUNIL TODI & ORS. versus STATE OF GUJARAT & ANR. (2021), p.19 **(changed)** |
| 5 | IN THE SUPREME COURT OF INDIA CRIMINAL APPELLATE JURISDICTION C… (), p.1 | SRIPATI SINGH (SINCE DECEASED) THROUGH HIS SON GAURAV SINGH ver… (2021), p.14 **(changed)** | SRIPATI SINGH (SINCE DECEASED) THROUGH HIS SON GAURAV SINGH ver… (2021), p.14 **(changed)** |

### N14 (domain E)

*In 2023 my brother forwarded an obscene video in a WhatsApp group. The cyber law charge against him was dropped, but police are still pursuing the obscenity charge under the ordinary penal code for the same forward. Can they do that?*

| Place | B | N1-125 | N2-125 |
|---|---|---|---|
| 1 | JAVED AHMAD HAJAM versus STATE OF MAHARASHTRA & ANR. (2024), p.12 | JAVED AHMAD HAJAM versus STATE OF MAHARASHTRA & ANR. (2024), p.12 | GOOGLE INDIA PRIVATE LIMITED versus M/S. VISAKHA INDUSTRIES (2019), p.45 **(changed)** |
| 2 | GOOGLE INDIA PRIVATE LIMITED versus M/S. VISAKHA INDUSTRIES (2019), p.45 | GOOGLE INDIA PRIVATE LIMITED versus M/S. VISAKHA INDUSTRIES (2019), p.45 | GOOGLE INDIA PRIVATE LIMITED versus M/S. VISAKHA INDUSTRIES (2019), p.47 **(changed)** |
| 3 | GOOGLE INDIA PRIVATE LIMITED versus M/S. VISAKHA INDUSTRIES (2019), p.47 | GOOGLE INDIA PRIVATE LIMITED versus M/S. VISAKHA INDUSTRIES (2019), p.47 | IN THE SUPREME COURT OF INDIA CRIMINAL APPELLATE JURISDICTION C… (), p.32 **(changed)** |
| 4 | IN THE SUPREME COURT OF INDIA CRIMINAL APPELLATE JURISDICTION C… (), p.32 | IN THE SUPREME COURT OF INDIA CRIMINAL APPELLATE JURISDICTION C… (), p.32 | THE STATE OF UTTAR PRADESH versus AMAN MITTAL & ANR. (2019), p.14 **(changed)** |
| 5 | THE STATE OF UTTAR PRADESH versus AMAN MITTAL & ANR. (2019), p.14 | THE STATE OF UTTAR PRADESH versus AMAN MITTAL & ANR. (2019), p.14 | APOORVA ARORA & ANR. ETC. versus STATE (GOVT. OF NCT OF DELHI) … (2024), p.33 **(changed)** |

### N15 (domain F)

*After my in-laws forced me out, I filed a domestic violence case, but the court says it will take at least a year to decide. I have no money for rent or food right now. Can the court give me maintenance before the case is fully decided?*

| Place | B | N1-125 | N2-125 |
|---|---|---|---|
| 1 | IN THE SUPREME COURT OF INDIA CIVIL APPELLATE JURISDICTION CIVI… (), p.35 | RAJNESH versus NEHA & ANR. (2020), p.15 **(changed)** | RAJNESH versus NEHA & ANR. (2020), p.15 **(changed)** |
| 2 | RAJNESH versus NEHA & ANR. (2020), p.15 | RAJNESH versus NEHA & ANR. (2020), p.15 **(changed)** | RAJNESH versus NEHA & ANR. (2020), p.15 **(changed)** |
| 3 | SHAHJAHAN versus THE STATE OF UTTAR PRADESH & ANR. R1: THE STAT… (2025), p.9 | RAJNESH versus NEHA & ANR. (2020), p.15 **(changed)** | RAJNESH versus NEHA & ANR. (2020), p.15 **(changed)** |
| 4 | IN THE SUPREME COURT OF INDIA CIVIL APPELLATE JURISDICTION CIVI… (), p.21 | RAJNESH versus NEHA & ANR. (2020), p.15 **(changed)** | RAJNESH versus NEHA & ANR. (2020), p.15 **(changed)** |
| 5 | IN THE SUPREME COURT OF INDIA CIVIL APPELLATE JURISDICTION CIVI… (), p.15 | RAJNESH versus NEHA & ANR. (2020), p.15 **(changed)** | RAJNESH versus NEHA & ANR. (2020), p.15 **(changed)** |

### N16 (domain F)

*Two years after our wedding, my husband's family started saying my father must give 5 lakhs so they can build a second floor on their house. My father had already given gold and a bike at the wedding. When we refused, they stopped talking to me, took away my phone and last month sent me back to my parents' home. My aunt says money asked for building a house is not dowry because it was asked after…*

| Place | B | N1-125 | N2-125 |
|---|---|---|---|
| 1 | STATE OF MADHYA PRADESH versus JOGENDRA & ANR. (2022), p.14 | STATE OF MADHYA PRADESH versus JOGENDRA & ANR. (2022), p.14 | STATE OF MADHYA PRADESH versus JOGENDRA & ANR. (2022), p.14 |
| 2 | ‘ REPORTABLE’ IN THE SUPREME COURT OF INDIA CRIMINAL APPELLATE … (), p.8 | ‘ REPORTABLE’ IN THE SUPREME COURT OF INDIA CRIMINAL APPELLATE … (), p.8 | ‘ REPORTABLE’ IN THE SUPREME COURT OF INDIA CRIMINAL APPELLATE … (), p.8 |
| 3 | STATE OF MADHYA PRADESH versus JOGENDRA & ANR. (2022), p.15 | STATE OF MADHYA PRADESH versus JOGENDRA & ANR. (2022), p.15 | STATE OF MADHYA PRADESH versus JOGENDRA & ANR. (2022), p.15 |
| 4 | PETITIONER: L. V. JADHAV Vs. RESPONDENT: SHANKARRAO ABASAHEB PA… (), p.5 | PETITIONER: L. V. JADHAV Vs. RESPONDENT: SHANKARRAO ABASAHEB PA… (), p.5 | PETITIONER: L. V. JADHAV Vs. RESPONDENT: SHANKARRAO ABASAHEB PA… (), p.5 |
| 5 | Reema Aggarwal v. Anupam and Ors. (2004), p.6 | IN THE SUPREME COURT OF INDIA CRIMINAL APPELLATE JURISDICTION C… (), p.18 **(changed)** | IN THE SUPREME COURT OF INDIA CRIMINAL APPELLATE JURISDICTION C… (), p.18 **(changed)** |

### N21 (domain H)

*After a fight in which my cousin got hurt, police searched our joint family house and found an old pistol in a trunk in the store room. They have booked my 70-year-old father for keeping it, but he says he never knew it was there. Is it enough that it was found in his house?*

| Place | B | N1-125 | N2-125 |
|---|---|---|---|
| 1 | MOHMED RAFIQ ABDUL RAHIM SHAIKH versus THE STATE OF GUJARAT (2018), p.6 | MOHMED RAFIQ ABDUL RAHIM SHAIKH versus THE STATE OF GUJARAT (2018), p.6 | MOHMED RAFIQ ABDUL RAHIM SHAIKH versus THE STATE OF GUJARAT (2018), p.6 |
| 2 |  (), p.50 |  (), p.50 |  (), p.50 |
| 3 | GUNWANTLAL versus THE STATE OF MADHYA PRADESH (1972), p.4 | GUNWANTLAL versus THE STATE OF MADHYA PRADESH (1972), p.4 | GUNWANTLAL versus THE STATE OF MADHYA PRADESH (1972), p.4 |
| 4 | STATE OF RAJASTHAN Vs. v. BHUP RAM (1997), p.3 | STATE OF RAJASTHAN Vs. v. BHUP RAM (1997), p.3 | MOHMED RAFIQ ABDUL RAHIM SHAIKH versus THE STATE OF GUJARAT (2018), p.6 **(changed)** |
| 5 | MOHMED RAFIQ ABDUL RAHIM SHAIKH versus THE STATE OF GUJARAT (2018), p.6 | MOHMED RAFIQ ABDUL RAHIM SHAIKH versus THE STATE OF GUJARAT (2018), p.6 | PETITIONER: GUNWANTILAL Vs. RESPONDENT: THE STATE OF MADHYA PRA… (), p.4 **(changed)** |

### N24 (domain I)

*Whether a Special Court under the PMLA must give the proposed accused an opportunity of being heard under Section 223 BNSS before taking cognizance of a prosecution complaint filed in 2025.*

| Place | B | N1-125 | N2-125 |
|---|---|---|---|
| 1 | KUSHAL KUMAR AGARWAL versus DIRECTORATE OF ENFORCEMENT (2025), p.4 | PARVINDER SINGH versus DIRECTORATE OF ENFORCEMENT (2026), p.16 **(changed)** | PARVINDER SINGH versus DIRECTORATE OF ENFORCEMENT (2026), p.16 **(changed)** |
| 2 | PARVINDER SINGH versus DIRECTORATE OF ENFORCEMENT (2026), p.16 | PARVINDER SINGH versus DIRECTORATE OF ENFORCEMENT (2026), p.20 **(changed)** | PARVINDER SINGH versus DIRECTORATE OF ENFORCEMENT (2026), p.20 **(changed)** |
| 3 | KUSHAL KUMAR AGARWAL versus DIRECTORATE OF ENFORCEMENT (2025), p.4 | PARVINDER SINGH versus DIRECTORATE OF ENFORCEMENT (2026), p.15 **(changed)** | PARVINDER SINGH versus DIRECTORATE OF ENFORCEMENT (2026), p.15 **(changed)** |
| 4 | PARVINDER SINGH versus DIRECTORATE OF ENFORCEMENT (2026), p.20 | PARVINDER SINGH versus DIRECTORATE OF ENFORCEMENT (2026), p.19 **(changed)** | PARVINDER SINGH versus DIRECTORATE OF ENFORCEMENT (2026), p.19 **(changed)** |
| 5 | KUSHAL KUMAR AGARWAL versus DIRECTORATE OF ENFORCEMENT (2025), p.5 | PARVINDER SINGH versus DIRECTORATE OF ENFORCEMENT (2026), p.6 **(changed)** | PARVINDER SINGH versus DIRECTORATE OF ENFORCEMENT (2026), p.6 **(changed)** |

### N25 (domain I)

*My uncle is a clerk in the revenue office and was caught in an anti-corruption trap in 2019 under the Prevention of Corruption Act. The man who complained that my uncle had asked him for 10,000 rupees died before the trial started. The trap witness only saw the money being handed over and did not hear any demand. My uncle says that without the complainant nobody can prove he asked for a bribe. Th…*

| Place | B | N1-125 | N2-125 |
|---|---|---|---|
| 1 | NEERAJ DUTTA versus STATE (GOVT. OF N.C.T. OF DELHI) (2022), p.37 | NEERAJ DUTTA versus STATE (GOVT. OF N.C.T. OF DELHI) (2022), p.37 | NEERAJ DUTTA versus STATE (GOVT. OF N.C.T. OF DELHI) (2022), p.37 |
| 2 | N. VIJAYAKUMAR versus STATE OF TAMIL NADU (2021), p.16 | N. VIJAYAKUMAR versus STATE OF TAMIL NADU (2021), p.16 | N. VIJAYAKUMAR versus STATE OF TAMIL NADU (2021), p.16 |
| 3 | MRS. NEERAJ DUTTA versus STATE (GOVT. OF NCT OF DELHI) (2019), p.6 | MRS. NEERAJ DUTTA versus STATE (GOVT. OF NCT OF DELHI) (2019), p.6 | MRS. NEERAJ DUTTA versus STATE (GOVT. OF NCT OF DELHI) (2019), p.6 |
| 4 | P. SARANGAPANI (DEAD) THR. LR PAKA SAROJA versus STATE OF ANDHR… (2023), p.5 | P. SARANGAPANI (DEAD) THR. LR PAKA SAROJA versus STATE OF ANDHR… (2023), p.5 | P. SARANGAPANI (DEAD) THR. LR PAKA SAROJA versus STATE OF ANDHR… (2023), p.5 |
| 5 | IN THE SUPREME COURT OF INDIA CRIMINAL APPELLATE JURISDICTION C… (), p.9 | NEERAJ DUTTA versus STATE (GOVT. OF N.C.T. OF DELHI) (2022), p.23 **(changed)** | NEERAJ DUTTA versus STATE (GOVT. OF N.C.T. OF DELHI) (2022), p.23 **(changed)** |

## 3. Identical top 5 under all three versions

20 questions: N01, N02, N03, N05, N06, N07, N08, N10, N11, N17, N18, N19, N20, N22, N23, N26, N27, N28, N29, N30. They add nothing to the comparison between versions; they count only toward the floors.

## 4. What goes to J and S

Pooled passages per question: 9 to 11 (total 289), B's top 10 plus each finalist's top 5, shuffled; the pack does not say which version a passage came from.
