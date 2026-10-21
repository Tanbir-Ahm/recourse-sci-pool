# Guwahati High Court judgments up to 2017: findings and plan (2026-10-21)

Owner's aim: add Guwahati (Gauhati) High Court judgments up to 2017 to the library. Nothing here says a decision is good law.

## 1. The court's own site cannot be read from here [Certain]
`https://ghconline.gov.in/index.php/judgments-up-to-2017/` and `https://ghconline.gov.in/JDMTJan17.pdf`: the sandbox's gateway lets the connection out, but the court's server never answers (the tunnel closes after about 12 s; "connection reset by peer"). Not a policy denial from our side. Likely a refusal of non-Indian or cloud addresses [Guessing]. Not retried or worked around. What the court calls "judgments up to 2017", how many links it has and whether the PDFs have a text layer are therefore unknown. The owner can save the index page (HTML) and attach the monthly PDFs.

## 2. The open bucket has Guwahati documents and is reachable [Certain]
`s3://indian-high-court-judgments` (Dattam Labs, registry: CC-BY-4.0, 25 High Courts, updated quarterly; same publisher as the Supreme Court bucket), region ap-south-1, readable over HTTPS with no account. Gauhati High Court is `court=18_6` (benches `asghccis` Assam, `arghccis` Arunachal Pradesh, `azghccis` Mizoram). Keys: `data/pdf/year=YYYY/court=18_6/bench=.../<CNR>_<n>_<date>.pdf`; metadata in `metadata/parquet/...` (title with case number and parties, CNR, decision date, registration date, disposal nature, judge, a snippet).

- **117,328 documents decided 2004 to 2017** (about 30 before 2004): 2007 1,492; 2010 5,190; 2012 16,751; 2013 18,890; 2015 16,090; 2017 14,082. All PDFs together under 0.6 GB.
- **Mostly short orders, not judgments.** Median size 3.7 KB (a page or two). Only **9,892 (8%) are 10 KB or larger** (179 MB) and only **825 (0.7%) are 30 KB or larger**. The metadata's `pdf_exists` flag is wrong (false for every row), and `disposal_nature` is blank for almost all.
- **A 70-document sample of the 10 KB-or-larger ones** (random, seed 7): 23 headed JUDGMENT, 11 ORDER, the rest not identifiable from the heading; none scanned; **26 of 70 (37%) have garbled text** (letters shifted by 29 code points, spaces lost, e.g. `:3&` for "WPC"), all from the Arunachal Pradesh bench files (CNR prefix GAHC04); the Assam bench files read normally. The garbling can probably be repaired by shifting back and restoring the spaces, or by OCR; not tested at scale.

## 3. Proposed plan
A. **Catalogue** of all 117,328 documents (case number and parties, CNR, decision date, bench, size, the bucket link): metadata only, no PDFs.
B. **Fetch and read the 9,892 documents of 10 KB or more** from the bucket (about 180 MB, two workers, polite), store raw text as monthly or yearly shards on a new data branch, flag garbled and judgment-headed ones. Needs the owner's say-so for the new branch.
C. **Decide what to do about the small documents** (107,000 orders; some may be short judgments). Needs the PDFs to classify, about 0.4 GB; a later, owner-decided step.
D. **Repair the Arunachal text** (shift by 29, restore spaces, or OCR) after measuring how many documents it affects.
E. **Cross-check with the court's own list** once the owner supplies the saved page and the monthly PDFs.
F. **Index and checker**: criminal-law filter, no-spend plan first, embedding only with the owner's go-ahead.
