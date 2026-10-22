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

## 4. The court's monthly list, January 2017 (owner attached `JDMTJan17.pdf`, 2026-10-21) [Certain unless marked]
`ghc/court_lists/JDMTJan17.pdf` is **not a judgment but the court's own list of the month's judgments**: "JUDGMENTS FOR THE MONTH OF JANUARY, 2017", 10 pages, a Word table saved as PDF (made in 2020), text layer, no images: serial, date, case number, parties, subject, judges. 114 judgments. `parse_court_list.py` reads it; `court_lists/JDMTJan17_parsed.csv` is the result (the judges column is approximate: a wrapped surname can land in the respondent column).

Matched with the bucket's catalogue by decision day and case number:
- **82 of the 114 (72%) are in the bucket** (80 on the same day; 2 more under another date); **32 (28%) are not.** The missing ones are almost all criminal or rare case types that the bucket barely holds at all (all years: Crl.A.(J) jail appeals 87, Crl.Pet. 70, Crl.Rev.P. 4, Review.Pet. 2, Revn.Pet. 1, I.A.(Crl.) 12): jail appeals 8 of 9 missing, criminal interlocutory 5 of 5, review petitions 4 of 4, criminal petitions 3 of 3, criminal revisions 3 of 3, revision petitions 3 of 3. The main types are covered (writ petitions 38 of 41, criminal appeals 16 of 16, second appeals, civil revisions, misc first appeals). [Likely] The bucket's Gauhati feed omits much of the court's criminal-side work.
- **The 10 KB size cut is a poor selector.** The 80 listed judgments found in the bucket have a median size of 8.6 KB; only 28 of them (35%) are 10 KB or larger. Of the 65 documents of 10 KB or more (not AB, BA, MC, IA) decided in January 2017, only 28 (43%) are on the court's list.
- Therefore: **use the court's monthly lists as the selector** (fetch exactly the listed judgments from the bucket), and treat the listed judgments missing from the bucket as a separate gap that needs the court's own PDFs.
- The list also gives the subject (for example "Appeals against conviction for offences under IPC"), which separates criminal from civil without reading the text. [Likely, n = 1 month]

Next: the owner finds how many monthly lists exist (earliest month) and downloads them; they are about 0.3 MB each.

## 5. Owner's decisions of 2026-10-21 (later)
- The court's judgments page covers **2010 to 2017** (earliest year 2010): about 96 monthly lists.
- The owner checked the Guwahati High Court's terms on downloading these files and **approved** it (his statement).
- He is collecting the links to the monthly lists with a console snippet and will send them; then the lists, then the judgment files that the bucket lacks (criminal-subject ones first, if he agrees).

## 6. Court copy against bucket copy, 20 judgments (owner downloaded `compare.zip`, 2026-10-21) [Certain]
- All 20 court PDFs have a real text layer (4 to 70 pages, 4,659 to 114,417 characters), none is a scan. Average size about 128 KB.
- The court's copy is the whole document: cause title with the parties, advocates, date of hearing and judgment, the heading (for example "JUDGMENT & ORDER (ORAL)"), then the body.
- The bucket's copy of the same case is the body without the cause title and heading. Its length is a median 91% of the court's (range 57% to 96%); **3 of 20 are materially shorter** (WP(C) 4569/2010: 16 pages against the court's 70; WP(C) 1832/2009: 68%; WP(C) 4972/2006: 79%). Its text also has mid-word line breaks ("appoint-ment" split over two lines; 7.4% of its words are not words of the court's copy; single-letter fragments 36 per 1000 words against 20). Only 68% of 6-word runs are shared between the two copies, because of that.
- Conclusion: the court's PDFs are the better source (complete, cleaner, with the heading that marks a judgment). The bucket is an acceptable fallback for the body text but is sometimes incomplete. Plan: court files first for what the bucket lacks (888 criminal-subject files, then the other 942), then the criminal ones the bucket holds, then the rest as the owner's laptop time allows.

## 7. Owner's decision, 2026-10-22: bucket-first, 888 criminal files by zip

- **Text policy (replaces the "court file is the main text" rule of 2026-10-22 morning):** the open bucket's text is the main text wherever the bucket has the judgment. The court's own file is needed only where the bucket has nothing: the 888 criminal-subject files in `ghc/court_lists/missing_judgments_criminal.csv`. Owner said: "Yes, bucket-first, use the zip route for the 888".
- **How the 888 arrive:** the owner runs `download_missing_criminal.ps1 -Limit 0` on his laptop and uploads the `partNN.zip` files to `ghc/court_judgments/` on this branch (or attaches them in chat). This session cannot reach ghconline.gov.in (connection reset, checked 2026-10-22), so there is no other route and none is attempted.
- **The other 4,738 per-year files (`download_YYYY.ps1`) are not requested.** They would only replace bucket text that already exists; ask the owner again only if a quality problem needs it.
- **Bucket text check (2026-10-22, 400-judgment sample of reasoned ones + all 11,317):** readable; about 88% of words recognisable; no scans, no empty documents; the 2,280 letter-shift repairs are clean. One defect: the stored text is hard-wrapped at 80 columns, which splits some words ("Ke / bang"). A reversible cleaning step (join full-width lines) is needed before any embedding; it lifted recognisable words to about 91% and still leaves some splits (lines of 78 characters), so the real cleaning must be built and tested.
- When the zips arrive: read the PDFs, store text tagged "court" on `claude/ghc-bucket`, set `court_file_received=yes` in `court_lists/by_month`, report counts and flag any scans (no OCR tool).
