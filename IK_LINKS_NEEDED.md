# Indian Kanoon links needed (28 cases)

The checker holds each of these cases from the Supreme Court's own site, so it has no Indian Kanoon (IK) id for them. An id lets me ask IK how many later documents cite the case, for Rs 0.02 per case, and later which of them are Supreme Court judgments we lack.

## How to get a link

1. Go to indiankanoon.org and search the case name (or its citation).
2. Open the **Supreme Court judgment itself**. Check that the parties and the **decision date** match the table below. IK often has several pages for one case (a later order, a different date, a copy), and only one is the judgment. This has gone wrong before: Recourse's link for D.K. Basu points to a 1 August 1997 follow-up order, not the 18 December 1996 judgment.
3. Copy the address. It looks like `https://indiankanoon.org/doc/123456/`; only the number matters.

Send them as one line each, in this form (any order, any number; partial is fine):

```
Mohan Lal v State of Punjab | https://indiankanoon.org/doc/NNNNNN/
```

If a case is not on IK, or you cannot tell which page is the judgment, write `not found` instead of a link. I check every link before using it: one metadata call each (Rs 0.02) compares IK's title and date with the date below, and a mismatch is reported rather than used.

## Priority 1: the four cases on the review sheet (send these first)

| Case | Citation | Decision date | Why it matters |
|---|---|---|---|
| Siddharam Satlingappa Mhetre v State of Maharashtra | (2011) 1 SCC 694 | 2010-12-02 | partly overruled by Sushila Aggarwal (2020), a real partial overruling; the checker shows ADVERSE_SIGNAL |
| G. Sagar Suri and Anr. v State of U.P. and Ors. | (2000) 2 SCC 636 | 2000-01-28 | referred to a larger bench by J. Vedhasingh (2022); whether it was decided is not in our data |
| Mohan Lal v State of Punjab | (2018) 17 SCC 627 | 2018-08-16 | partly overruled by Mukesh Singh (2020); the checker shows ADVERSE_SIGNAL |
| State of Rajasthan v Parmanand | (2014) 5 SCC 345 | 2014-02-28 | criticised on one point by a later judgment; plausible, unconfirmed |

## Priority 2: heavily cited (we hold 20 or more later judgments citing each)

| Case | Citation | Decision date | Later judgments we hold | Status now |
|---|---|---|---|---|
| Gurbaksh Singh Sibbia v State of Punjab | 1980 AIR 1632, (1980) 2 SCC 565 | 1980-04-09 | 61 | NO_ADVERSE_FOUND |
| Noor Aga v State of Punjab | (2008) 16 SCC 417 | 2008-07-09 | 52 | NO_ADVERSE_FOUND |
| Inder Mohan Goswami and Anr. v State of Uttaranchal and Ors. | (2007) 12 SCC 1 | 2007-10-09 | 28 | NO_ADVERSE_FOUND |
| Sushila Aggarwal v State (NCT of Delhi) | (2020) 5 SCC 1 | 2020-01-29 | 22 | NO_ADVERSE_FOUND |
| Karnail Singh v State of Haryana | (2009) 8 SCC 539 | 2009 | 20 | NO_ADVERSE_FOUND |

## Priority 3: the rest

| Case | Citation | Decision date | Later judgments we hold | Status now |
|---|---|---|---|---|
| Hridaya Rangan Pd. Verma and Ors. v State of Bihar and Anr. | (2000) 4 SCC 168 | 2000-03-31 | 19 | NO_ADVERSE_FOUND |
| S.W. Palanitkar and Ors. v State of Bihar and Anr. | (2002) 1 SCC 241 | 2001-10-18 | 15 | NO_ADVERSE_FOUND |
| Vijaysinh Chandubha Jadeja v State of Gujarat | (2011) 1 SCC 609 | 2011 | 15 | NO_ADVERSE_FOUND |
| Mukesh Singh v State (Narcotic Branch of Delhi) | (2020) 10 SCC 120 | 2020-08-31 | 12 | NO_ADVERSE_FOUND |
| Jagrup Singh v State of Haryana | [1981] 3 S.C.R. 839 | 1981-05-07 | 11 | NO_ADVERSE_FOUND |
| Tofan Singh v State of Tamil Nadu | (2021) 4 SCC 1 | 2020-10-29 | 11 | NO_ADVERSE_FOUND |
| Mathai Verghese v State of Kerala | [1987] 1 S.C.R. 317 | 1986-11-19 | 9 | NO_ADVERSE_FOUND |
| Alpic Finance Ltd. v P. Sadasivan and Anr. | (2001) 3 SCC 513 | 2001-02-16 | 5 | NO_ADVERSE_FOUND |
| Union of India v Mohanlal | (2016) 3 SCC 379 | 2016-01-28 | 5 | NO_ADVERSE_FOUND |
| All Cargo Movers (I) Pvt. Ltd. and Ors. v Dhanesh Badarmal Jain and Anr. | (2007) 14 SCC 776 | 2007-10-12 | 4 | NO_ADVERSE_FOUND |
| Union of India v Shiv Shanker Kesari | (2007) 7 SCC 798 | 2007-09-14 | 3 | NO_ADVERSE_FOUND |
| Nanda Gopalan v State of Kerala | [2015] 4 S.C.R. 563 | 2015-04-24 | 1 | INSUFFICIENT |
| Sakharam v State of Madhya Pradesh | [1992] 1 S.C.R. 638 | 1992-02-12 | 1 | INSUFFICIENT |
| State of Gujarat v Haidarali Kalubhai | 1976 AIR 1012, [1976] 3 SCR 303 | 1976-02-03 | 1 | INSUFFICIENT |
| Anwarul Haq v State of Uttar Pradesh | [2005] 3 S.C.R. 917 | 2005-04-26 | 0 | INSUFFICIENT |
| Hori Lal v State of Uttar Pradesh | [2006] Supp. 10 S.C.R. 60 | 2006-12-05 | 0 | INSUFFICIENT |
| Prabhu v State of Madhya Pradesh | [2008] 16 S.C.R. 1095 | 2008-12-03 | 0 | INSUFFICIENT |
| Pravat Chandra Mohanty v State of Odisha | [2021] 4 S.C.R. 407 | 2021-02-11 | 0 | INSUFFICIENT |
| State of Uttar Pradesh v Ram Kishan | [1976] 3 S.C.R. 379 | 1976-02-13 | 0 | INSUFFICIENT |

Cases where the status is INSUFFICIENT are the ones where an IK id would help most: we hold few or no later judgments citing them, so silence there says almost nothing.
